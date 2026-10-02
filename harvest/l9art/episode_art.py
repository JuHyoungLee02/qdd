"""(pod) One articulated episode: observe -> truth label (format v3) -> behaviour command (label + DART-style offsets
on pre-poses) -> cuRobo / Cartesian-follower execution -> measured history; calls/, labels.jsonl, meta.json,
joints.npz, frames for review. The arm is driven in joint-target mode (commanded step <= 0.034 rad, as rt9.CMD_DQ);
harvest.l9 is used read-only (PlannerProxy, plan9.resample / scene_cuboids, grasp9 gripper models, world9)."""
from __future__ import annotations

import json
import math
import os
import time

import numpy as np

from . import fixtures as FX
from . import prompts_art as PA
from . import skills as SK
from . import world_art as WA

CMD_DQ = 0.034
CMD_DQ_CONTACT = 0.02  # [가설] contact moves (follower, push, press): measured steps reached 0.047-0.072 at 0.034
MAX_CALLS = 24
REACH_TOL, HOLD_MAX_S = 0.012, 1.5
CLOSE_S, OPEN_S = 0.6, 0.5
EMPTY_GAP = 0.004  # pad gap after a close below this = nothing between the pads
LOST_M = 0.03  # follower: hand-to-grasp-point distance above this = the grasp / contact is lost
STALL_SEG = 2
PERTURB = (0.01, 0.025)
VIDEO_EVERY = 6
VERSION = "l9art-1"
PUSH_MODE = {"franka_mast": "v2"}


class Halt(Exception):
    pass


class Exec:
    """Joint-target execution + cuRobo planning for one (robot, arm) process."""

    def __init__(self, world, profile: str, arm: str, device: str = "cuda:0"):
        from ..l9 import curobo9 as C9
        from ..l9 import grasp9 as G
        from ..l9.plan9_server import PlannerProxy
        from ..l9.rt9 import GRIP_NAME
        self.w, self.profile, self.arm = world, profile, arm
        self.gr = G.gripper(GRIP_NAME.get(profile, profile))
        self.joints = C9.arm_joints(profile, arm)
        self.base_link = C9.base_link(profile, arm)
        self.planner = PlannerProxy(C9.load_config(profile, arm), device=device)
        rob = world.env.robot
        self.sim_ids = [rob.joint_names.index(j) for j in self.joints]
        self.arm_ids = list(world.env.arm_ids)
        self.base_idx = rob.body_names.index(self.base_link)
        lim = rob.data.soft_joint_pos_limits[0].cpu().numpy()
        self.q_lo, self.q_hi = lim[self.sim_ids, 0] + 0.01, lim[self.sim_ids, 1] - 0.01
        self.q_target, self.width = None, float(world.w_open)
        self.frames, self.video, self._k = [], False, 0
        self.stats = {"plan_fail": 0, "limit_rejects": 0}

    # ---------------------------------------------------------------- state
    def reset(self):
        self.q_target, self.width = None, float(self.w.w_open)
        self.frames, self._k = [], 0

    def arm_q(self):
        return self.w.env.robot.data.joint_pos[0, self.sim_ids].cpu().numpy().astype(float)

    def plan_start(self):
        q = self.arm_q()
        if self.q_target is not None and np.abs(np.asarray(self.q_target) - q).max() < 0.15:
            q = np.asarray(self.q_target, float)
        return np.clip(q, self.q_lo + 0.03, self.q_hi - 0.03)

    def T_world_base(self):
        d = self.w.env.robot.data
        o = self.w.env.scene.env_origins[0].cpu().numpy()
        return FX.T_of(FX.qmat(d.body_quat_w[0, self.base_idx].cpu().numpy()), d.body_pos_w[0, self.base_idx].cpu().numpy() - o)

    def to_base(self, T):
        from ..l9.plan9 import inv_T
        return inv_T(self.T_world_base()) @ np.asarray(T, float)

    def tcp_T(self):
        p, q = self.w.pl.tcp_pose()
        return FX.T_of(FX.qmat(q), p)

    def grip_w(self) -> float:
        return float(self.w.env.gripper_width())

    # ---------------------------------------------------------------- stepping
    def step(self):
        env = self.w.env
        q = env.robot.data.joint_pos[0, self.arm_ids].cpu().numpy().copy()
        if self.q_target is not None:
            for j, sid in enumerate(self.sim_ids):
                q[self.arm_ids.index(sid)] = self.q_target[j]
        g = self.w.pl._gravity_offset()[0].cpu().numpy()
        env.step(np.concatenate([q + g, [float(self.width)]]).astype(np.float32))
        self.w._st = None
        self.w._log_step()
        if hasattr(self.w, "_jlog"):
            self.w._jlog.append(env.robot.data.joint_pos[0].cpu().numpy().copy())
        self._k += 1
        if self.video and self._k % VIDEO_EVERY == 0:
            fr = self.w.frame()
            self.frames.append((fr["head"], fr["wrist"]))

    def hold(self, seconds: float):
        if self.q_target is None:
            self.q_target = self.arm_q()
        for _ in range(max(1, int(round(seconds / self.w.dt)))):
            self.step()

    def run(self, Q, slow: float = 1.0, target=None, dq: float = CMD_DQ) -> dict:
        """Execute a joint path (resampled to <= CMD_DQ per step), then wait for the arm to arrive."""
        from ..l9.plan9 import resample
        Q = np.asarray(Q, float)
        if (Q < self.q_lo).any() or (Q > self.q_hi).any():
            self.stats["limit_rejects"] += 1
            return {"ok": False, "why": "plan leaves the joint range"}
        Q = resample(np.concatenate([[self.plan_start()], Q]), dq_max=dq, slow=slow)
        for q in Q[1:]:
            self.q_target = q
            self.step()
        T_goal = target
        t0, last, still = 0.0, None, 0
        err = 0.0
        while t0 < HOLD_MAX_S:
            self.step()
            t0 += self.w.dt
            p = self.tcp_T()[:3, 3]
            err = float(np.linalg.norm(p - T_goal[:3, 3])) if T_goal is not None else 0.0
            moved = 1.0 if last is None else float(np.linalg.norm(p - last))
            last = p
            still = still + 1 if moved < 3e-4 else 0
            if err < REACH_TOL or still >= 4:
                break
        return {"ok": True, "err_mm": round(err * 1e3, 1)}

    def set_gripper(self, w: float, close: bool) -> float:
        self.width = 0.0 if close else float(w)
        ws = []
        n = int(round((CLOSE_S if close else OPEN_S) / self.w.dt))
        for i in range(n):
            self.step()
            ws.append(self.grip_w())
            if close and i > 8 and abs(ws[-1] - ws[-6]) < 0.0005:
                break
        return self.grip_w()

    # ---------------------------------------------------------------- planning
    def set_world(self, spec, T_WF, q, objects: dict, skip_links=(), skip_prefix=(), skip_objs=()):
        from ..l9.plan9 import scene_cuboids
        from ..sim.scene import OBJ_GEOM
        fs = getattr(self.w, "scene9", {}) or {}
        parts = [p for p in fs.get("furniture", []) if "size" in p and "pos" in p]
        boxes = FX.boxes_world(spec, T_WF, q, skip_links=skip_links, skip_prefix=skip_prefix) if spec else {}
        env = self.w.env
        for k in env.present:
            g = OBJ_GEOM.get(k, {})
            if k in skip_objs or g.get("shape") in ("marker", "surface") or "half_extents" not in g:
                continue
            c, qq = env.object_pose(k)
            boxes[f"obj_{k}"] = (np.asarray(c, float), [2 * float(v) for v in g["half_extents"]], np.asarray(qq, float))
        self.planner.world(scene_cuboids(parts, boxes, self.T_world_base(), pad=0.005))

    def plan_pose(self, T):
        Q = self.planner.pose(self.plan_start(), self.to_base(T))
        if Q is None:
            self.stats["plan_fail"] += 1
        return Q

    def plan_line(self, T, check: bool = False, step_m: float = 0.008):
        Q = self.planner.line(self.plan_start(), self.to_base(self.tcp_T()), self.to_base(T), step_m, check)
        return Q

    def move(self, T, mode: str = "pose", slow: float = 1.0, dq: float = CMD_DQ) -> dict:
        Q = self.plan_pose(T) if mode == "pose" else self.plan_line(T)
        if Q is None and mode == "pose":
            Q = self.plan_line(T, check=True)
        if Q is None and mode == "line":  # a straight move with no continuous IK (another elbow branch): a planned
            Q = self.plan_pose(T)  # move in the current world (Franka pilot: presses and grasps stopped at the pre-pose)
        if Q is None:
            return {"ok": False, "why": "no path"}
        return self.run(Q, slow=slow, target=T, dq=dq)


# ================================================================================================ episode
class ArtEpisode:
    def __init__(self, world, ex: Exec, row: dict, built: dict, spec: dict | None, prog: dict, out_dir: str,
                 p: float = 0.15, video: bool = False):
        self.w, self.ex, self.row, self.b, self.spec, self.prog = world, ex, row, built, spec, prog
        self.out_dir, self.p, self.video = out_dir, p, video
        self.rng = np.random.default_rng([int(row["seed"]), 515])
        self.draw = SK.grasp_draw(self.rng)
        self.rows, self.history, self.calls = [], [], 0
        self.stage_i, self.sub = 0, "start"
        self.rel = None  # T_link_tcp of the current grasp / contact
        self.done_stages, self.fail_counts = [], {}
        self.events = []
        self.end_reason = None
        self.press_peak = {}
        self.knob_goal = None
        self._push = None
        self.regrasp = False
        # pilots 10-02: re-aimed pushes won on Franka (0.62 / far 0.58), lost on the AI Worker (0 / 6 vs 0.56)
        self.push_mode = PUSH_MODE.get(ex.profile, "v1")

    # ---------------------------------------------------------------- geometry of now
    def T_WF(self):
        return WA.T_WF_now(self.w)

    def q(self):
        return WA.joints(self.w) if self.spec is not None else {}

    def stage(self):
        return self.prog["stages"][self.stage_i] if self.stage_i < len(self.prog["stages"]) else None

    def joint_of(self, st):
        return self.spec["handles"][st["link"]]["joint"]

    def hf(self, st, q=None):
        return FX.handle_frame(self.spec, st["link"], self.T_WF(), self.q() if q is None else q)

    def precheck(self) -> str | None:
        """cuRobo IK (world = table + fixture body + objects, moving parts off) of every stage's pre-pose, contact /
        grasp pose and end-of-motion pose, from the start state; -> the first unreachable one or None (smoke 10-02:
        a drawer handle whose pre-pose was reachable but not the grasp 10 cm further in looped 'could not move in')."""
        if self.spec is not None:
            self.ex.set_world(self.spec, self.T_WF(), self.q(), {}, skip_links=tuple(self.spec["links"]))
        else:
            self.ex.set_world(None, None, {}, {})
        q = dict(self.q())
        names, Ts = [], []
        for i, st in enumerate(self.prog["stages"]):
            k = st["kind"]
            if k in ("pull", "rotate"):
                hf = self.hf(st, q)
                g = SK.handle_grasp(hf, self.ex.gr, self.draw)
                jn = self.joint_of(st)
                qg = dict(q, **{jn: st["goal"]})
                T0 = self.T_WF() @ FX.link_T(self.spec, st["link"], q)
                T1 = self.T_WF() @ FX.link_T(self.spec, st["link"], qg)
                Ts += [g["T_pre"], g["T"], T1 @ np.linalg.inv(T0) @ g["T"]]
                names += [f"{i}:{k}:pre", f"{i}:{k}:grasp", f"{i}:{k}:end"]
                q = qg
            elif k == "push":
                jn = self.joint_of(st)
                qg = dict(q, **{jn: st["goal"]})
                c0, c1 = self.push_contact(st, q), self.push_contact(st, qg)
                Ts += [c0["T_pre"], c0["T"], c1["T"]]
                names += [f"{i}:push:pre", f"{i}:push:contact", f"{i}:push:end"]
                q = qg
            elif k == "press":
                J = self.spec["joints"][self.joint_of(st)]
                pp = SK.press_pose(self.hf(st, q), J["hi"], self.ex.gr, self.draw)
                Ts += [pp["T_pre"], pp["T_in"]]
                names += [f"{i}:press:pre", f"{i}:press:in"]
            elif k == "slide":
                pl = self.push_plan()
                Ts += [pl["T_pre_high"], pl["T_pre"], pl["T_goal"]]
                names += [f"{i}:slide:high", f"{i}:slide:pre", f"{i}:slide:goal"]
            elif k == "pick" and self.prog["def"] != "drawer_take_close":
                g = self.obj_grasp()
                Ts += [g["T_pre"], g["T"]]
                names += [f"{i}:pick:pre", f"{i}:pick:grasp"]
        if not Ts:
            return None
        ok = self.ex.planner.ik(np.stack([self.ex.to_base(T) for T in Ts]))[0]
        bad = [n for n, o in zip(names, ok) if not bool(o)]
        self.precheck_result = {"n": len(Ts), "bad": bad}
        return ",".join(bad) if bad else None

    def unseen(self, cam, margin: int = 30) -> str | None:
        """Every point the labels need (each part at its start and goal, a pushed object and its goal) inside the head
        image with a margin (0-1000 units); -> the first missing one or None."""
        def ok(p):
            px = SK.to_px(cam, p)
            return px is not None and margin <= px[0] <= 1000 - margin and margin <= px[1] <= 1000 - margin
        q = self.q()
        for st in self.prog["stages"]:
            if st.get("link"):
                hf = self.hf(st, q)
                if not ok(hf["gc"]):
                    return f"{st['link']} at start"
                if st.get("goal") is not None:
                    jn = self.joint_of(st)
                    qg = dict(q, **{jn: st["goal"]})
                    hg = self.hf(st, qg)
                    if not ok(hg["mark"] if st["kind"] == "rotate" else hg["gc"]):
                        return f"{st['link']} at goal"
                    q = qg
            elif st["kind"] == "slide":
                plan = self.push_plan()
                c = np.asarray(self.w.env.object_pose(self.b["tgt"])[0], float)
                if not ok(c) or not ok(np.array([plan["goal_xy"][0], plan["goal_xy"][1], c[2]])):
                    return "pushed object or its goal"
        return None

    # ---------------------------------------------------------------- labels
    def label(self, obs) -> dict:
        """The truth command for the current state (v3) + 3D targets for the executor."""
        st = self.stage()
        cam = obs.cams["head"]
        if st is None:
            return {"cmd": {"mode": "stop"}, "sub": "stop", "skill": None}
        kind, skill = st["kind"], st["skill"]
        sub = self.sub
        out = {"skill": skill, "sub": sub, "stage": self.stage_i}
        if kind in ("pull", "rotate"):
            hf = self.hf(st)
            g = SK.handle_grasp(hf, self.ex.gr, self.draw)
            if sub in ("start", "above"):
                cmd = self._pt(cam, skill, g["p"], "above", "open", g)
                out.update(cmd=cmd, T=g["T_pre"], open_w=g["open_w"], next="grasp", g=g)
            elif sub == "grasp":
                cmd = self._pt(cam, skill, g["p"], "grasp", "close", g)
                out.update(cmd=cmd, T=g["T"], next="move", g=g)
            elif sub == "move":
                jn = self.joint_of(st)
                qg = dict(self.q(), **{jn: st["goal"]})
                hg = self.hf(st, qg)
                end = hg["mark"] if kind == "rotate" else hg["gc"]
                now = hf["mark"] if kind == "rotate" else hf["gc"]
                cmd = self._pt(cam, skill, hf["gc"], "grasp", "keep", g, p2=end)
                if kind == "rotate":
                    cmd["point_2d"] = SK.to_px(cam, hf["gc"])
                cmd.update(self.axis_fields(cam, st))  # the joint axis in the answer (user principle: no code-only decisions)
                out.update(cmd=cmd, goal=st["goal"], next="release", now=now)
            elif sub == "release":
                out.update(cmd={"mode": "gripper", "gripper": "open", "skill": skill}, next="retreat")
            else:  # retreat
                d = -np.asarray(self.tcp_a()) * 0.10
                out.update(cmd={"mode": "edit", "delta_m": [round(float(v), 3) for v in d], "gripper": "keep",
                                "skill": skill}, next="start" if self.regrasp else "done")
            return out
        if kind == "push":
            hf = self.hf(st)
            c = self.push_contact(st)
            if sub in ("start",) and self.ex.grip_w() > 0.01:
                out.update(cmd={"mode": "gripper", "gripper": "close", "skill": skill}, next="above")
            elif sub in ("start", "above"):
                cmd = self._pt(cam, skill, c["point"], "above", "keep", c)
                out.update(cmd=cmd, T=c["T_pre"], next="move", c=c)
            elif sub == "move":
                jn = self.joint_of(st)
                qg = dict(self.q(), **{jn: st["goal"]})
                end = self.push_contact(st, qg)["point"]
                cmd = self._pt(cam, skill, c["point"], "grasp", "keep", c, p2=end)
                cmd.update(self.axis_fields(cam, st))
                out.update(cmd=cmd, goal=st["goal"], T=c["T"], next="retreat", c=c)
            else:
                d = -np.asarray(self.tcp_a()) * 0.10
                out.update(cmd={"mode": "edit", "delta_m": [round(float(v), 3) for v in d], "gripper": "keep",
                                "skill": skill}, next="done")
            return out
        if kind == "press":
            hf = self.hf(st)
            J = self.spec["joints"][self.joint_of(st)]
            pp = SK.press_pose(hf, J["hi"], self.ex.gr, self.draw)
            if sub == "start" and self.ex.grip_w() > 0.01:
                out.update(cmd={"mode": "gripper", "gripper": "close", "skill": skill}, next="above")
            elif sub in ("start", "above"):
                cmd = self._pt(cam, skill, hf["gc"], "above", "keep", pp)
                out.update(cmd=cmd, T=pp["T_pre"], next="press", c=pp)
            else:  # press (in and back out to the pre-pose)
                cmd = self._pt(cam, skill, hf["gc"], "grasp", "keep", pp)
                out.update(cmd=cmd, T=pp["T_in"], T_back=pp["T_pre"], next="done", c=pp)
            return out
        if kind == "slide":
            k = self.b["tgt"]
            plan = self.push_plan()
            if sub == "start" and self.ex.grip_w() > 0.01:
                out.update(cmd={"mode": "gripper", "gripper": "close", "skill": skill}, next="above")
            elif sub in ("start", "above"):
                c_obj = np.asarray(self.w.env.object_pose(k)[0], float)
                cmd = self._pt(cam, skill, c_obj, "above", "keep", plan, p_ref=plan["T_pre"][:3, 3])
                out.update(cmd=cmd, T=plan["T_pre"], T_high=plan["T_pre_high"], next="move", c=plan)
            elif sub == "move":
                c_obj = np.asarray(self.w.env.object_pose(k)[0], float)
                g3 = np.array([plan["goal_xy"][0], plan["goal_xy"][1], c_obj[2]])
                cmd = self._pt(cam, skill, c_obj, "grasp", "keep", plan, p2=g3, p_ref=plan["T_pre"][:3, 3])
                out.update(cmd=cmd, T=plan["T_goal"], next="retreat", c=plan)
            else:
                out.update(cmd={"mode": "edit", "delta_m": [0.0, 0.0, 0.10], "gripper": "keep", "skill": skill},
                           next="done")
            return out
        if kind == "pick":
            g = self.obj_grasp()
            if sub in ("start", "above"):
                cmd = self._pt(cam, skill, g["p"], "above", "open", g)
                out.update(cmd=cmd, T=g["T_pre"], open_w=g["open_w"], next="grasp", g=g)
            elif sub == "grasp":
                cmd = self._pt(cam, skill, g["p"], "grasp", "close", g)
                out.update(cmd=cmd, T=g["T"], next="lift", g=g)
            else:  # lift
                out.update(cmd={"mode": "point", "skill": skill, "point_2d": None, "height": "lift", "gripper": "keep",
                                "hand": self.ex.arm}, next="done", lift=0.12)
            return out
        if kind == "place":
            sp = self.place_spot()
            if sub in ("start", "above"):
                cmd = self._pt(cam, skill, sp["p"], "above", "keep", {})
                out.update(cmd=cmd, T=sp["T_above"], next="place", sp=sp)
            elif sub == "place":
                cmd = self._pt(cam, skill, sp["p"], "place", "open", {})
                out.update(cmd=cmd, T=sp["T"], next="retreat", sp=sp)
            else:
                out.update(cmd={"mode": "edit", "delta_m": [0.0, 0.0, 0.10], "gripper": "keep", "skill": skill},
                           next="done")
            return out
        raise ValueError(kind)

    # ---------------------------------------------------------------- pick / place (combos)
    def obj_grasp(self) -> dict:
        """Top / oblique grasp across the object's shorter horizontal side (L9 targets are top-grasp tested)."""
        from ..sim.scene import OBJ_GEOM
        k = self.b["tgt"]
        c, qo = self.w.env.object_pose(k)
        c = np.asarray(c, float)
        he = np.asarray(OBJ_GEOM[k]["half_extents"], float)
        R = FX.qmat(qo)
        ax = R[:, 0] if he[0] <= he[1] else R[:, 1]  # shorter side: the closing axis
        ax = np.array([ax[0], ax[1], 0.0])
        ax = ax / max(np.linalg.norm(ax), 1e-9)
        a = np.array([0.0, 0.0, -1.0])
        tilt = 0.5 * self.draw["pitch"]  # up to 15 deg towards the robot (natural spread)
        toward = np.array([-c[0], -c[1], 0.0])
        toward /= max(np.linalg.norm(toward), 1e-9)
        a = SK._tilt(a, np.cross(toward, [0, 0, 1.0]), -tilt)
        h = 2 * he[2]
        p = np.array([c[0], c[1], c[2] + he[2] - min(0.02, 0.4 * h)])
        Rg = SK.frame_of(a, ax if not self.draw["flip"] else -ax)
        w = float(min(self.ex.gr["max_open"], 2 * min(he[0], he[1]) + 0.03))
        pt = p - a * SK.pad_offset(self.ex.gr)  # pad centre on the grasp point
        return {"T": SK.T_pose(Rg, pt), "T_pre": SK.T_pose(Rg, pt + self.draw["standoff"] * Rg[:, 2]), "a": a,
                "c": Rg[:, 1], "p": p, "open_w": w}

    def place_spot(self) -> dict:
        """Where the held object goes: IN = the exposed front part of the open drawer floor, TABLE = the free table
        spot of the scene; the TCP keeps its height above the object's bottom (measured at the grasp)."""
        from ..sim.scene import OBJ_GEOM
        st = self.stage()
        k = self.b["tgt"]
        he = np.asarray(OBJ_GEOM[k]["half_extents"], float)
        if st["ref"] == "IN":
            ln = next(s["link"] for s in self.prog["stages"] if s.get("link"))
            jn = self.joint_of({"link": ln})
            qd = self.q()[jn]
            it = self.spec["interior"][ln]
            xl = float(np.clip((qd - 0.02) / 2, he.max() + 0.02, max(he.max() + 0.02, qd - he.max() - 0.03)))
            T = WA.link_world(self.w, ln)
            p = T[:3, :3] @ np.array([xl, 0.0, it["floor_c"][2]]) + T[:3, 3]
        else:
            xy = self.b["spot_xy"]
            p = np.array([xy[0], xy[1], float(self.b["tz"])])
        d = getattr(self, "_held_dz", 2 * he[2] - 0.02)
        key = (self.stage_i, st["ref"])
        if getattr(self, "_place_cache", (None,))[0] != key:  # choose once per stage: the first IK-feasible hand yaw
            R0 = self.ex.tcp_T()[:3, :3]  # / spot shift (pilot 10-02: the held hand's pose above the drawer had no IK)
            cands = []
            for yaw in (0.0, 0.5, -0.5, 1.0, -1.0, 1.57, -1.57):
                for dxy in ((0, 0), (0.02, 0), (-0.02, 0), (0, 0.03), (0, -0.03)):
                    Rz = FX.rot_axis([0, 0, 1.0], yaw)
                    cands.append((Rz @ R0, np.array([dxy[0], dxy[1], 0.0])))
            Ts = [SK.T_pose(R, p + sh + np.array([0, 0, d + 0.10])) for R, sh in cands]
            try:
                self.set_world(None)
                ok = self.ex.planner.ik(np.stack([self.ex.to_base(T) for T in Ts]))[0]
                i = int(np.argmax(ok)) if bool(np.any(ok)) else 0
            except Exception:  # noqa: BLE001
                i = 0
            self._place_cache = (key, cands[i])
        R, sh = self._place_cache[1]
        p = p + sh
        Tp = SK.T_pose(R, p + np.array([0, 0, d + 0.012]))
        Ta = SK.T_pose(R, p + np.array([0, 0, d + 0.10]))
        return {"p": p, "T": Tp, "T_above": Ta}

    def axis_fields(self, cam, st) -> dict:
        return SK.axis_fields(cam, self.spec, st["link"], self.T_WF(), self.q(), float(st["goal"]))

    def tcp_a(self):
        return -self.ex.tcp_T()[:3, 2]  # approach = -z_G

    def push_contact(self, st, q=None) -> dict:
        """Contact for a push along the joint: drawers / doors: the front panel beside the handle; sliding doors: the
        handle bar's side (pushed sideways)."""
        sp = self.spec
        J = sp["joints"][self.joint_of(st)]
        h = sp["handles"][st["link"]]
        T = self.T_WF() @ FX.link_T(sp, st["link"], self.q() if q is None else q)
        R = T[:3, :3]
        if J["kind"] == "slide":
            ax = R @ np.asarray(J["axis"], float)  # open direction; closing pushes along -ax
            gc = R @ np.asarray(h["gc"]) + T[:3, 3]
            point = gc + ax * (float(h.get("thick", 0.012)) / 2)
            c = SK.contact_push(point, -ax, self.ex.gr, self.draw, c_hint=[0, 0, 1.0])
        else:
            gc = np.asarray(h["gc"], float)
            if J["kind"] == "door":  # outer face (link x = 0) near the free edge, 7 cm above / below the handle
                Hh = float(sp["dims"]["H"]) / 2
                z = gc[2] - 0.07 if gc[2] - 0.07 > -Hh + 0.03 else gc[2] + 0.07
                loc = np.array([0.0, gc[1], z])
            else:  # drawer front panel beside the handle
                W = sp["dims"]["W"]
                off = 0.5 * float(h.get("length") or 0.04) + 0.035
                yy = gc[1] - off if gc[1] - off > -W / 2 + 0.03 else gc[1] + off
                loc = np.array([-0.018, yy, gc[2]])
            point = R @ loc + T[:3, 3]
            c = SK.contact_push(point, R @ np.array([1.0, 0, 0]), self.ex.gr, self.draw)
        c["point"] = point
        return c

    def push_plan(self):
        from ..sim.scene import OBJ_GEOM
        k = self.b["tgt"]
        if getattr(self, "_push", None) is None:
            c_obj = np.asarray(self.w.env.object_pose(k)[0], float)
            words = self.prog["words"]
            dist = float(words.get("DIST", 10)) / 100.0
            dmap = {"left": [0, 1.0], "right": [0, -1.0], "back": [1.0, 0], None: [1.0, 0]}
            d = np.array(dmap.get(words.get("DIR"), [1.0, 0]) + [0.0])
            if self.prog["judge"].get("dir") == "away":
                d = np.array([1.0, 0, 0])
            he = OBJ_GEOM[k]["half_extents"]
            self._push = {"c0": c_obj, "d": d, "dist": dist, "half": he}
        P = self._push
        c_now = np.asarray(self.w.env.object_pose(k)[0], float)
        rem = P["dist"] - float((c_now - P["c0"])[:2] @ P["d"][:2])
        if self.push_mode == "v2":
            q_now = self.w.env.object_pose(k)[1]
            ext = float(np.abs(FX.qmat(q_now).T @ np.asarray(P["d"], float)) @ np.asarray(P["half"], float))
            plan = SK.push_plan_v2(c_now, (ext, ext, P["half"][2]), float(self.b["tz"]), P["d"], max(0.0, rem),
                                   self.ex.gr, self.draw)
        else:
            plan = SK.push_plan(c_now, P["half"], float(self.b["tz"]), P["d"], max(0.0, rem), self.ex.gr, self.draw)
        plan["goal_xy"] = P["c0"][:2] + P["d"][:2] * P["dist"]
        return plan

    def _pt(self, cam, skill, p, height, grip, g, p2=None, p_ref=None) -> dict:
        self._p3 = np.asarray(p, float)  # the pointed 3D point (occlusion check in run)
        cmd = {"mode": "point", "skill": skill, "point_2d": SK.to_px(cam, p), "height": height, "gripper": grip,
               "hand": self.ex.arm}
        a, c = g.get("a"), g.get("c")
        if a is not None:
            cmd["approach"] = SK.approach_family(a, p if p_ref is None else p_ref)
            if c is not None:
                cmd["rot"] = SK.rot_bin(cam, p, c)[1]
        if p2 is not None:
            cmd["point2"] = SK.to_px(cam, p2)
        return cmd

    # ---------------------------------------------------------------- behaviour + execution
    def execute(self, lab: dict) -> str:
        """Run the label's command (behaviour = label + DART-style offset on pre-poses); -> outcome text."""
        cmd = lab["cmd"]
        m = cmd["mode"]
        ex = self.ex
        sub = lab["sub"]
        st = self.stage()
        kind = None if st is None else st["kind"]
        if m == "stop":
            raise Halt("stop")
        if m == "gripper":
            wo = self.w.w_open
            if cmd["gripper"] == "open" and kind in ("pull", "rotate"):  # let go of a handle: open a little only
                wo = min(self.w.w_open, ex.grip_w() + 0.03)  # (smoke: wide pads pushed a sliding door back 2 cm)
            w = ex.set_gripper(wo if cmd["gripper"] == "open" else 0.0, cmd["gripper"] == "close")
            if cmd["gripper"] == "open":
                self.rel = None
            self.sub = lab["next"]
            return f"gripper {cmd['gripper']}: pad gap {w * 100:.1f} cm"
        if m == "edit":
            T = ex.tcp_T()
            T[:3, 3] += np.asarray(cmd["delta_m"], float)
            self.set_world(st, skip_all_links=True)
            r = ex.move(T, "line")
            if not r["ok"]:
                r = ex.move(T, "pose")
            self.sub = lab["next"]
            if lab["next"] == "start":  # regrasp recovery: a new grasp draw on the same stage
                self.regrasp = False
                self.draw = SK.grasp_draw(self.rng)
            if lab["next"] == "done":
                self.finish_stage()
            return "moved back" if r["ok"] else f"retreat failed ({r.get('why')})"
        # point commands
        if sub in ("start", "above"):
            T = np.asarray(lab.get("T_high", lab["T"]), float).copy()
            kind_p = "clean"
            if self.p > 0 and self.rng.random() < self.p:
                off = self.rng.normal(size=3)
                off *= self.rng.uniform(*PERTURB) / np.linalg.norm(off)
                T[:3, 3] += off
                kind_p = "perturb_xyz"
            lab["exec_kind"] = kind_p
            self.set_world(None)  # the target part stays an obstacle on the way to the pre-pose (smoke: the hand hit a dial, wrist 0.25 rad jump)
            if lab.get("open_w") is not None:
                ex.width = float(lab["open_w"])
            if kind == "place":  # carrying: plan with the held object attached, else without (as rt9)
                ex.planner.attach(ex.plan_start(), [f"obj_{self.b['tgt']}"])
            r = ex.move(T, "pose")
            if not r["ok"] and kind == "place":  # no attach, the held object out of the world (combo pilot: the
                self.set_world(st, skip_held=True)  # fingers around it made every carry start 'in collision')
                r = ex.move(T, "pose")
            if not r["ok"]:
                self.bump("approach_fail")
                try:  # stagewise: reach (IK with the world) or path (collision on the way)?
                    ok_ik = bool(ex.planner.ik(np.asarray([ex.to_base(T)]))[0][0])
                    hits = ex.planner._call("start_hits", ex.plan_start())  # start state inside the world?
                except Exception:  # noqa: BLE001
                    ok_ik, hits = None, None
                self.events.append({"call": self.calls, "approach_fail": True, "ik_ok": ok_ik, "start_hits": hits,
                                    "T": np.round(T, 4).tolist()})
                return f"no collision-free path to the pre-pose (pose reachable: {ok_ik})"
            if "T_high" in lab:  # push objects: down to the low pre-pose next to the object
                r = ex.move(np.asarray(lab["T"], float), "line")
            self.sub = lab["next"]
            return f"reached the pre-pose (error {r.get('err_mm', 0):.0f} mm)"
        if sub == "grasp":
            if kind in ("pull", "rotate"):
                self.set_world(st)  # the grasped part is not an obstacle for the move in (line fallback = planned move)
            r = ex.move(np.asarray(lab["T"], float), "line", slow=1.6)
            if not r["ok"]:
                self.bump("approach_fail")
                self.sub = "above"
                return "could not move in to the handle"
            w = ex.set_gripper(0.0, True)
            if w < EMPTY_GAP:
                self.bump("grasp_fail")
                ex.set_gripper(lab.get("open_w") or self.w.w_open, False)
                ex.move(np.asarray(lab["T"], float) @ FX.T_of(np.eye(3), (0, 0, 0.08)), "line")
                self.sub = "above"
                return f"closed on nothing (pad gap {w * 100:.1f} cm); reopened and backed off"
            if kind == "pick":
                from ..sim.scene import OBJ_GEOM
                k = self.b["tgt"]
                c = np.asarray(self.w.env.object_pose(k)[0], float)
                self._held_dz = float(ex.tcp_T()[2, 3] - (c[2] - OBJ_GEOM[k]["half_extents"][2]))
                self.sub = lab["next"]
                return f"closed on the {self.prog['words'].get('O', 'object')} (pad gap {w * 100:.1f} cm)"
            self.rel = np.linalg.inv(WA.link_world(self.w, st["link"])) @ ex.tcp_T()
            self.sub = lab["next"]
            return f"closed on the handle (pad gap {w * 100:.1f} cm)"
        if sub == "lift":
            T = ex.tcp_T()
            T[:3, 3] += np.array([0.0, 0.0, float(lab.get("lift", 0.12))])
            ex.move(T, "line")
            k = self.b["tgt"]
            c = np.asarray(self.w.env.object_pose(k)[0], float)
            if float(np.linalg.norm(c - ex.tcp_T()[:3, 3])) > 0.12 or ex.grip_w() < EMPTY_GAP:
                self.bump("lift_drop")
                ex.set_gripper(self.w.w_open, False)
                self.sub = "above"
                return "the object did not come up with the gripper; reopened"
            self.finish_stage()
            return f"lifted the {self.prog['words'].get('O', 'object')}"
        if sub == "place":
            ex.move(np.asarray(lab["T"], float), "line", slow=1.6)
            ex.set_gripper(self.w.w_open, False)
            try:
                ex.planner.detach()
            except Exception:  # noqa: BLE001
                pass
            self.sub = lab["next"]
            return "lowered and released"
        if sub == "move":
            if kind in ("pull", "rotate"):
                return self.follow(st, lab, grasped=True)
            if kind == "push":
                r = ex.move(np.asarray(lab["T"], float), "line", slow=1.6)  # in to the contact
                self.rel = np.linalg.inv(WA.link_world(self.w, st["link"])) @ ex.tcp_T()
                return self.follow(st, lab, grasped=False)
            if kind == "slide":
                return self.push_object(lab)
        if sub == "press":
            jn = self.joint_of(st)
            self.set_world(st)  # the pressed button is not an obstacle
            r = ex.move(np.asarray(lab["T"], float), "line", slow=2.0, dq=CMD_DQ_CONTACT)
            peak = max(self.press_peak.get(jn, 0.0), self.q().get(jn, 0.0))
            ex.hold(0.3)
            peak = max(peak, self.q().get(jn, 0.0))
            self.press_peak[jn] = peak
            ex.move(np.asarray(lab["T_back"], float), "line")
            J = self.spec["joints"][jn]
            if peak >= self.prog["judge"].get("press_share", 0.6) * J["hi"]:
                self.finish_stage()
                return f"pressed {peak * 1000:.1f} mm of {J['hi'] * 1000:.0f} mm and backed off"
            self.bump("press_short")
            self.sub = "above"
            return f"pressed only {peak * 1000:.1f} mm of {J['hi'] * 1000:.0f} mm"
        raise ValueError(sub)

    def bump(self, k):
        self.fail_counts[k] = self.fail_counts.get(k, 0) + 1

    def finish_stage(self):
        self.done_stages.append(self.stage_i)
        self.stage_i += 1
        self.sub = "start"
        self.rel = None

    def set_world(self, st, skip_all_links: bool = False, skip_held: bool = False):
        so = (self.b["tgt"],) if skip_held else ()  # the held object is not an obstacle of its own carry
        if self.spec is None:
            self.ex.set_world(None, None, {}, {}, skip_objs=so)
            return
        q = self.q()
        if skip_all_links:
            self.ex.set_world(self.spec, self.T_WF(), q, {}, skip_links=tuple(self.spec["links"]), skip_objs=so)
        elif st is not None and st.get("link"):
            self.ex.set_world(self.spec, self.T_WF(), q, {}, skip_links=(st["link"],), skip_objs=so)
        else:
            self.ex.set_world(self.spec, self.T_WF(), q, {}, skip_objs=so)

    def follow(self, st, lab, grasped: bool) -> str:
        """Small Cartesian follower: plan short straight hand moves that keep the grasp / contact relation to the
        link at the next joint value (from the MEASURED value each segment) until the goal, a stall or a lost grip."""
        ex, sp = self.ex, self.spec
        jn = self.joint_of(st)
        J = sp["joints"][jn]
        goal = float(lab["goal"])
        step = SK.follow_step(J["kind"])
        tol = 0.01 * J["hi"] if J["type"] == "prismatic" else math.radians(3.0)
        stall, q_prev = 0, self.q()[jn]
        a = self.tcp_a()
        why = None
        for _ in range(60):
            qn = self.q()[jn]
            if abs(qn - goal) <= tol:
                why = "reached"
                break
            T_link = WA.link_world(self.w, st["link"])
            hand_err = float(np.linalg.norm((T_link @ self.rel)[:3, 3] - ex.tcp_T()[:3, 3]))
            if hand_err > LOST_M:
                why = "lost"
                break
            q_next = SK.next_value(qn, goal, step)
            q_all = dict(self.q(), **{jn: q_next})
            T_link_next = self.T_WF() @ FX.link_T(sp, st["link"], q_all)
            T = SK.follow_target(T_link_next, self.rel, 0.0 if grasped else SK.PUSH_IN, a)
            Q = ex.plan_line(T, check=False, step_m=0.006)
            if Q is None:
                why = "ik"
                break
            ex.run(Q, slow=1.3, target=T, dq=CMD_DQ_CONTACT)
            qm = self.q()[jn]
            if abs(qm - q_prev) < 0.15 * step:
                stall += 1
                if stall >= STALL_SEG:
                    why = "stall"
                    break
            else:
                stall = 0
            q_prev = qm
        qn = self.q()[jn]
        unit = (lambda v: f"{v * 100:.1f} cm") if J["type"] == "prismatic" else (lambda v: f"{math.degrees(v):.0f} deg")
        accept = 0.04 * J["hi"] if J["type"] == "prismatic" or J["kind"] == "door" else math.radians(6.0)
        if why == "reached" or abs(qn - goal) <= max(tol, accept if why in ("stall", "ik") else tol):  # near the goal at the arm's reach: done (smoke 10-02: 14.8 of 15.4 cm looped)
            self.sub = lab["next"] if grasped else "retreat"
            return f"moved along the joint to {unit(qn)} (goal {unit(goal)})"
        self.bump({"lost": "axis_slip", "stall": "axis_stall", "ik": "axis_unreachable"}.get(why, "axis_short"))
        if grasped and why == "lost":
            self.sub = "above"
            ex.set_gripper(self.w.w_open, False)
            return f"lost the handle at {unit(qn)} (goal {unit(goal)}); reopened"
        if grasped:
            self.sub, self.regrasp = "release", True  # recovery: let go, back off, grasp again further along
        else:
            self.sub = "above"
        return f"stopped at {unit(qn)} (goal {unit(goal)}): {why}"

    def push_object(self, lab) -> str:
        if self.push_mode == "v2":
            return self.push_object_v2(lab)
        ex = self.ex
        k = self.b["tgt"]
        for _ in range(12):
            plan = self.push_plan()
            c_obj = np.asarray(self.w.env.object_pose(k)[0], float)
            rem = float(np.linalg.norm(plan["goal_xy"] - c_obj[:2]))
            if rem <= 0.012:
                break
            T = plan["T_goal"].copy()
            p0 = ex.tcp_T()[:3, 3]
            seg = min(0.03, float(np.linalg.norm(T[:3, 3] - p0)))
            d = T[:3, 3] - p0
            if np.linalg.norm(d) < 1e-4:
                break
            T[:3, 3] = p0 + d / np.linalg.norm(d) * seg
            Q = ex.plan_line(T, check=False, step_m=0.006)
            if Q is None:
                self.bump("push_unreachable")
                break
            ex.run(Q, slow=1.4, target=T, dq=CMD_DQ_CONTACT)
        c_obj = np.asarray(self.w.env.object_pose(k)[0], float)
        err = float(np.linalg.norm(self._push["c0"][:2] + self._push["d"][:2] * self._push["dist"] - c_obj[:2]))
        self.sub = "retreat"
        return f"pushed; object {err * 100:.1f} cm from the goal"

    def push_object_v2(self, lab) -> str:
        ex = self.ex
        k = self.b["tgt"]
        from ..sim.scene import OBJ_GEOM
        he = np.asarray(OBJ_GEOM[k]["half_extents"], float)
        fw = float(ex.gr.get("finger_t", 0.012))
        R0 = ex.tcp_T()[:3, :3]
        z0 = float(ex.tcp_T()[2, 3])
        goal = self._push["c0"][:2] + self._push["d"][:2] * self._push["dist"]
        for _ in range(16):  # re-aimed pushes: the hand goes behind the object on the object -> goal line each 2.5 cm
            c_obj, q_obj = self.w.env.object_pose(k)
            c_obj = np.asarray(c_obj, float)
            v = goal - c_obj[:2]
            rem = float(np.linalg.norm(v))
            if rem <= 0.010:
                break
            dvec = v / rem
            Ro = FX.qmat(q_obj)
            d3 = np.array([dvec[0], dvec[1], 0.0])
            ext = float(np.abs(Ro.T @ d3) @ he)  # the object's extent along the push direction (its yaw)
            step = min(0.025, rem)
            hand = c_obj[:2] + dvec * (step - ext - fw - 0.004)
            T = SK.T_pose(R0, np.array([hand[0], hand[1], z0]))
            Q = ex.plan_line(T, check=False, step_m=0.006)
            if Q is None:
                self.bump("push_unreachable")
                break
            ex.run(Q, slow=1.4, target=T, dq=CMD_DQ_CONTACT)
        c_obj = np.asarray(self.w.env.object_pose(k)[0], float)
        err = float(np.linalg.norm(self._push["c0"][:2] + self._push["d"][:2] * self._push["dist"] - c_obj[:2]))
        self.sub = "retreat"
        return f"pushed; object {err * 100:.1f} cm from the goal"

    # ---------------------------------------------------------------- loop
    def run(self) -> dict:
        from ..astra_solo import nd as ND
        from ..astra_solo.overlay import png_bytes
        w = self.w
        t0 = time.perf_counter()
        sim_t0 = float(w.env.sim_time)
        self.ex.video = self.video
        static = None
        last_note = None
        for i in range(1, MAX_CALLS + 1):
            obs = w.observe(depth=True)
            lab = self.label(obs)
            self.calls = i
            if static is None:
                static = PA.static(self)
            text = static + PA.now(self, obs, i, MAX_CALLS)
            ans = PA.answer(self, lab, last_note)
            d = os.path.join(self.out_dir, "calls", f"c{i:03d}")
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "prompt_v3.txt"), "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            ring, _ = ND.ring_overlay(obs.rgb["head"], obs.cams["head"], obs.tcp)
            for name, img in (("img1_head_camera.png", obs.rgb["head"]), ("img1_head_ring.png", ring),
                              ("img2_right_wrist_camera.png", obs.rgb["wrist"])):
                with open(os.path.join(d, name), "wb") as f:
                    f.write(png_bytes(np.asarray(img)))
            with open(os.path.join(d, "cams.json"), "w") as f:
                json.dump({k: c.to_json() for k, c in obs.cams.items()}, f)
            if hasattr(w, "other_wrist_save"):
                w.other_wrist_save(d)
            if obs.depth and obs.depth.get("head") is not None:
                np.savez_compressed(os.path.join(d, "head_depth.npz"), depth=np.asarray(obs.depth["head"], np.float32))
            row = {"call": i, "stage": lab.get("stage"), "sub": lab["sub"], "skill": lab.get("skill"),
                   "answer": ans, "command": lab["cmd"], "joints": {k: round(v, 5) for k, v in self.q().items()},
                   "tcp": [round(float(v), 4) for v in self.ex.tcp_T()[:3, 3]], "grip_w": round(self.ex.grip_w(), 4),
                   "occ": SK.occluded(obs.cams["head"], (obs.depth or {}).get("head"), getattr(self, "_p3", None))
                   if lab["cmd"].get("mode") == "point" and lab["cmd"].get("point_2d") is not None else None,
                   "drop": None if lab["cmd"].get("mode") != "point" or lab["cmd"].get("point_2d") is not None
                   else "not_visible"}
            try:
                note = self.execute(lab)
            except Halt:
                row["exec_kind"] = "clean"
                row["outcome"] = "stop"
                self.rows.append(row)
                with open(os.path.join(d, "reply.txt"), "w") as f:
                    f.write(json.dumps(lab["cmd"]))
                self.end_reason = "stop"
                break
            row["exec_kind"] = lab.get("exec_kind", "clean")
            row["outcome"] = note
            self.rows.append(row)
            with open(os.path.join(d, "reply.txt"), "w") as f:
                f.write(json.dumps(lab["cmd"]))
            last_note = note
            self.history.append(f"{i}: {PA.describe(lab['cmd'])} -> {note}")
            if sum(self.fail_counts.values()) >= 6:
                self.end_reason = "too_many_failures"
                break
        else:
            self.end_reason = "call_cap"
        self.ex.hold(1.0)
        res = self.judge()
        return {"success": res["ok"], "judge": res, "end_reason": self.end_reason, "n_calls": self.calls,
                "wall_s": round(time.perf_counter() - t0, 1), "sim_t": round(float(w.env.sim_time) - sim_t0, 2),
                "fail_counts": dict(self.fail_counts), "events": self.events[:12], "push_mode": self.push_mode, "draw": {k: (round(v, 4) if isinstance(v, float) else v)
                                                               for k, v in self.draw.items()}}

    def judge(self) -> dict:
        prog, sp = self.prog, self.spec
        out = {"stages": []}
        ok = self.stage_i >= len(prog["stages"]) and self.end_reason == "stop"
        q = self.q()
        for st in prog["stages"]:
            if st["kind"] in ("pull", "push", "rotate"):
                jn = self.joint_of(st)
                J = dict(sp["joints"][jn])
                goal = st["goal"]
                jj = dict(prog["judge"])
                if st["kind"] == "rotate":
                    jj = {"tol_deg": jj.get("tol_deg", 15.0)}
                elif prog["combo"]:
                    jj = {"max_share": jj["max_share"]} if st["kind"] == "push" else {"min_share": 0.75}
                r = SK.judge_joint(J, q[jn], jj, goal)
            elif st["kind"] == "press":
                jn = self.joint_of(st)
                J = sp["joints"][jn]
                pk = self.press_peak.get(jn, 0.0)
                r = {"ok": pk >= prog["judge"].get("press_share", 0.6) * J["hi"], "peak_mm": round(pk * 1000, 2)}
            elif st["kind"] == "slide":
                from ..predicates import _tilt_deg
                k = self.b["tgt"]
                c, qq = self.w.env.object_pose(k)
                P = self._push or {}
                goal = P["c0"][:2] + P["d"][:2] * P["dist"] if P else c[:2]
                r = SK.judge_push(P.get("c0", c)[:2], np.asarray(c)[:2], goal, float(_tilt_deg(np.asarray(qq))), prog["judge"])
            elif st["kind"] == "pick":
                r = {"ok": prog["stages"].index(st) in self.done_stages}
            elif st["kind"] == "place":
                from ..sim.scene import OBJ_GEOM
                k = self.b["tgt"]
                c = np.asarray(self.w.env.object_pose(k)[0], float)
                he = np.asarray(OBJ_GEOM[k]["half_extents"], float)
                if st["ref"] == "IN":
                    ln = next(s["link"] for s in prog["stages"] if s.get("link"))
                    T = WA.link_world(self.w, ln)
                    cl = T[:3, :3].T @ (c - T[:3, 3])
                    it = sp["interior"][ln]
                    fz = float(it["floor_c"][2])
                    inside = (0.0 <= cl[0] <= sp["dims"]["D"]) and abs(cl[1]) <= sp["dims"]["W"] / 2 - 0.01 and \
                        fz - 0.01 <= cl[2] - he[2] <= fz + 0.03
                    r = {"ok": bool(inside), "obj_in_drawer_link": [round(float(v), 4) for v in cl]}
                else:
                    Tf = self.T_WF()
                    cf = Tf[:3, :3].T @ (c - Tf[:3, 3])
                    on_table = abs(c[2] - he[2] - float(self.b["tz"])) <= 0.015
                    out_fx = cf[0] < -0.01 or abs(cf[1]) > sp["dims"]["W"] / 2
                    r = {"ok": bool(on_table and out_fx), "bottom_dz": round(float(c[2] - he[2] - self.b["tz"]), 4)}
            else:
                r = {"ok": False, "why": "stage kind not judged"}
            out["stages"].append(dict(r, kind=st["kind"]))
            ok = ok and r["ok"]
        if prog["combo"] and len(prog["stages"]) > 1 and prog["stages"][0]["kind"] == "rotate":
            pass
        out["ok"] = bool(ok)
        return out
