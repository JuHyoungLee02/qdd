"""L9 v2 runtime (pod): real grasps + cuRobo motion inside the L8S/L9 collection loop (spec §12.4-12.5, §12.8,
§12.12). Process-level opt-in: install(world, profile, arm) -> world.rt. Nothing changes for worlds without rt.

Hooks (all guarded by `world.rt`):
  teach_l8d.xlabels.plan   -> Runtime.plan: the v2 truth plan (v2plan.plan) with the episode's GraspChoice
  teach_pt.collect.pt_command -> point label of the grasp steps = visible grasp point + approach + rot bin
  Episode.make_exec        -> TrajExec: every move is a cuRobo trajectory (plan_grasp / plan_pose), resampled to
                              <= 0.04 rad per control step with the motion9 timing style; the gripper pre-shapes to
                              pre_open at the stand-off (P1), closes to 0 under the effort cap, settles, judges
                              EMPTY / CONTACT / WIDE and after the micro-lift SLIP / SUCCESS (P2)
  episode.outcome          -> history lines carry the executor's notes (fallbacks, grip judgements)
  world.step / world.reset -> joint-target mode while a trajectory runs; per-episode state + instructed rows
The candidate cache: /data/harvest/l9v2/grasps/<grip>/<obj>.npz (grasp9) and, when present, the Isaac lift + shake
results /data/harvest/l9v2/tested/<grip>/<obj>.npz (only passing candidates are valid; without a test file the
object is not used unless allow_untested)."""
from __future__ import annotations

import math
import os
import types

import numpy as np

from . import grasp9 as G
from . import plan9 as P9
from . import v2plan as VP

GRASP_DIR = os.environ.get("L9V2_GRASPS", "/data/harvest/l9v2/grasps")
TESTED_DIR = os.environ.get("L9V2_TESTED", "/data/harvest/l9v2/tested")
VERSION = "l9v2-1"
GRIP_NAME = {"ffw_sg2": "ffw_sg2", "franka_mast": "franka"}
EMPTY_M, CONTACT_TOL, SLIP_GAP, SLIP_MOVE = 0.003, 0.008, 0.003, 0.010
SETTLE_DW, SETTLE_N, SETTLE_MAX_S, WIN_S = 0.001, 3, 0.6, 0.05
REACH_TOL, HOLD_MAX_S = 0.012, 1.5
CURRENT = None


def classify_close(gap: float, w_contact: float) -> str:
    """P2 judgement on the settled gap (thresholds = hypotheses, E-AP1 recalibrates once)."""
    if gap < EMPTY_M:
        return "EMPTY"
    if abs(gap - w_contact) <= CONTACT_TOL:
        return "CONTACT"
    return "WIDE"


def classify_lift(gap_before: float, gap_after: float, rel_move: float) -> str:
    return "SLIP" if (abs(gap_after - gap_before) > SLIP_GAP or rel_move > SLIP_MOVE) else "SUCCESS"


def T_of(p, q) -> np.ndarray:
    T = np.eye(4)
    T[:3, :3], T[:3, 3] = G.qmat(q), np.asarray(p, float)
    return T


# ---------------------------------------------------------------------------------------------- executor
class TrajExec:
    """MinJerkExec interface (go_to / move_by / grip / tick / busy / target / goal_quat / width) over joint
    trajectories planned by the runtime."""

    def __init__(self, rt, st):
        w = rt.w
        self.rt, self.dt, self.table_z = rt, w.dt, w.table_z
        self.cmd = np.asarray(st["tcp"], float).copy()
        self.target = self.cmd.copy()
        self.w_open, self.w_close = w.w_open, w.w_close
        self.width = rt.open_width()
        self.goal_quat = np.asarray(getattr(w, "quat0", (1.0, 0, 0, 0)), float)
        self.Q, self.i, self.after = None, 0, None
        self.hold_t = None
        self.pending_grip = None
        self.wait = None  # (action, t0, widths list)
        self._last_tcp, self._still = None, 0

    @property
    def busy(self) -> bool:
        return bool(self.Q is not None or self.hold_t is not None or self.wait is not None
                    or self.pending_grip is not None)

    def go_to(self, pos, grip: str, t: float) -> list:
        self.target = np.asarray(pos, float).copy()
        Q, note, width = self.rt.motion_for(self.target, grip)
        if width is not None:
            self.width = width
        if Q is None:
            return [{"t": round(t, 3), "event": "timeout", "err_mm": 999.0, "note": note or "no collision-free path",
                     "note_only": True}]
        self.Q, self.i, self.after, self.hold_t = Q, 0, grip, None
        self._note = note
        return []

    def move_by(self, delta, grip: str, t: float, tcp) -> list:
        return self.go_to(np.asarray(tcp, float) + np.asarray(delta, float), grip, t)

    def grip(self, action: str, t: float) -> None:
        self.pending_grip = action

    def _act(self, action: str, t: float, tcp) -> list:
        if action == "close":
            self.width = 0.0
        else:
            self.width = self.rt.open_width()
        self.wait = (action, t, [])
        self.rt.on_grip_cmd(action, t)
        return [{"t": round(t, 3), "event": action, "tcp": np.round(np.asarray(tcp, float), 4).tolist()}]

    def tick(self, t: float, tcp):
        tcp = np.asarray(tcp, float)
        ev = []
        if self.wait is not None:
            action, t0, ws = self.wait
            st = self.rt.w.status()
            ws.append((t, float(st["grip_w"])))
            done = t - t0 >= (SETTLE_MAX_S if action == "close" else 0.5)
            if action == "close" and len(ws) > 1:
                # settled: width change < 1 mm per 50 ms for 3 windows in a row
                k = max(1, int(round(WIN_S / self.dt)))
                if len(ws) > k * SETTLE_N:
                    d = [abs(ws[-1 - j * k][1] - ws[-1 - (j + 1) * k][1]) for j in range(SETTLE_N)]
                    done = done or all(x < SETTLE_DW for x in d)
            if done:
                self.wait = None
                ev.append({"t": round(t, 3), "event": "gripper_done", "action": action})
                note = self.rt.on_grip_done(action, t, ws)
                if note:
                    ev.append({"t": round(t, 3), "event": "reach", "err_mm": 0.0, "note": note, "note_only": True})
            return self.cmd.copy(), self.width, ev
        if self.pending_grip is not None:
            a = self.pending_grip
            self.pending_grip = None
            return self.cmd.copy(), self.width, self._act(a, t, tcp)
        if self.Q is not None:
            self.rt.q_target = self.Q[self.i]
            self.i += 1
            if self.i >= len(self.Q):
                self.Q, self.hold_t = None, t
            return self.cmd.copy(), self.width, ev
        if self.hold_t is not None:  # trajectory sent: wait for the arm to arrive / stop
            err = float(np.linalg.norm(tcp - self.target))
            moved = float(np.linalg.norm(tcp - self._last_tcp)) if self._last_tcp is not None else 1.0
            self._last_tcp = tcp.copy()
            self._still = self._still + 1 if moved < 3e-4 else 0
            if err < REACH_TOL or self._still >= 4 or t - self.hold_t > HOLD_MAX_S:
                kind = "reach" if err < REACH_TOL else ("settled" if err <= 0.03 else "timeout")
                e = {"t": round(t, 3), "event": kind, "err_mm": round(err * 1e3, 1)}
                if getattr(self, "_note", None):
                    e["note"] = self._note
                ev.append(e)
                self.hold_t, self._still, self._note = None, 0, None
                self.rt.on_move_done(t)
                if self.after in ("open", "close"):
                    ev += self._act(self.after, t, tcp)
        return self.cmd.copy(), self.width, ev


# ---------------------------------------------------------------------------------------------- runtime
class Runtime:
    def __init__(self, world, profile: str, arm: str, device: str = "cuda:0", allow_untested: bool = False,
                 style: dict | None = None):
        from . import curobo9 as C9
        self.w, self.profile, self.arm = world, profile, arm
        self.grip = GRIP_NAME.get(profile, profile)
        self.gr = G.gripper(self.grip)
        self.allow_untested = allow_untested
        self.base_link = C9.base_link(profile, arm)
        self.joints = C9.arm_joints(profile, arm)
        from .plan9_server import PlannerProxy  # cuRobo needs warp >= 1.14; the Isaac app holds warp 1.8.2
        self.planner = PlannerProxy(C9.load_config(profile, arm), device=device)
        self.curobo = self.planner.version
        self.style = style
        rob = world.env.robot
        self.sim_ids = [rob.joint_names.index(j) for j in self.joints]
        self.arm_ids = list(world.env.arm_ids)
        self.base_idx = rob.body_names.index(self.base_link)
        self._cand = {}
        self.q_target = None
        self.reset_episode()

    # ------------------------------------------------------------------ episode state
    def reset_episode(self):
        self.choice, self.choice_key, self.held = None, None, None
        self.segs, self.last_label = {}, None
        self.q_target = None
        self.picks, self.failed = [], set()
        self.regrasp_n, self.timeline = 0, {}
        self.instruction_suffix = ""

    def arm_q(self) -> np.ndarray:
        return self.w.env.robot.data.joint_pos[0, self.sim_ids].cpu().numpy().astype(float)

    def T_world_base(self) -> np.ndarray:
        d = self.w.env.robot.data
        return T_of(d.body_pos_w[0, self.base_idx].cpu().numpy(), d.body_quat_w[0, self.base_idx].cpu().numpy())

    def to_base(self, T_world) -> np.ndarray:
        return P9.inv_T(self.T_world_base()) @ np.asarray(T_world, float)

    def tcp_T(self) -> np.ndarray:
        p, q = self.w.pl.tcp_pose()
        return T_of(p, q)

    def open_width(self) -> float:
        return float(self.choice.pre_open) if self.choice is not None else float(self.w.w_open)

    # ------------------------------------------------------------------ obstacles
    def obstacle_boxes(self, exclude=()) -> dict:
        from ..sim.scene import OBJ_GEOM
        env = self.w.env
        out = {}
        for k in env.present:
            g = OBJ_GEOM.get(k, {})
            if k in exclude or g.get("shape") in ("marker", "surface") or "half_extents" not in g:
                continue
            c, q = env.object_pose(k)
            out[f"obj_{k}"] = (np.asarray(c, float), [2 * float(v) for v in g["half_extents"]], np.asarray(q, float))
        return out

    def refresh_world(self, holding: str | None = None, exclude=()) -> None:
        fs = getattr(self.w, "scene9", {}) or {}
        parts = [p for p in fs.get("furniture", []) if "size" in p and "pos" in p]
        self.planner.world(P9.scene_cuboids(parts, self.obstacle_boxes(exclude), self.T_world_base(), pad=0.005))
        if holding:
            self.planner.attach(self.arm_q(), [f"obj_{holding}"])

    # ------------------------------------------------------------------ candidates and the grasp choice
    def _load(self, k: str):
        if k in self._cand:
            return self._cand[k]
        from ..sim.scene import OBJ_GEOM
        oid = OBJ_GEOM.get(k, {}).get("catalog_id") or k
        f = os.path.join(GRASP_DIR, self.grip, f"{oid}.npz")
        if not os.path.exists(f):
            self._cand[k] = None
            return None
        d = dict(np.load(f))
        ok = np.ones(len(d["w"]), bool)
        t = os.path.join(TESTED_DIR, self.grip, f"{oid}.npz")
        if os.path.exists(t):
            r = dict(np.load(t))
            ok = np.asarray(r.get("pass", r.get("shake_ok", ok)), bool)
            d["tested"] = True
        elif not self.allow_untested:
            ok[:] = False
        d["source"] = np.array(["analytic"] * len(d["w"]))
        d["test_ok"] = ok
        self._cand[k] = d
        return d

    def _valid(self, k: str, Cw: dict) -> tuple:
        """valid mask (test pass, support clearance, neighbour finger clearance at pre_open, reach) + margin."""
        from ..sim.scene import OBJ_GEOM
        ok = np.asarray(Cw["test_ok"], bool).copy()
        g = OBJ_GEOM[k]
        c, _ = self.w.env.object_pose(k)
        sup = float(c[2]) - float(g["half_extents"][2])
        nb = self.obstacle_boxes(exclude=(k,))
        fs = getattr(self.w, "scene9", {}) or {}
        parts = [p for p in fs.get("furniture", []) if "size" in p and "pos" in p and p.get("role") != "room_wall"]
        bl = [(np.asarray(v[0]), np.asarray(v[1]) / 2, G.qmat(v[2])) for v in nb.values()]
        bl += [(np.asarray(p["pos"], float), np.asarray(p["size"], float) / 2,
                G.qmat(G.yaw_quat(float(p.get("yaw", 0.0))))) for p in parts]
        boxes = (np.array([b[0] for b in bl]).reshape(-1, 3), np.array([b[1] for b in bl]).reshape(-1, 3),
                 np.array([b[2] for b in bl]).reshape(-1, 3, 3))
        pre = np.asarray(Cw["pre_open"], float).copy()
        for i in np.flatnonzero(ok):
            T = Cw["T"][i]
            if G.lowest_point(T, self.gr, pre[i]) < sup + G.SUPPORT_CLEAR:
                ok[i] = False
                continue
            w_free = free_opening(T, self.gr, boxes, float(Cw["w"][i]), pre[i])
            if w_free is None:
                ok[i] = False
            else:
                pre[i] = w_free
        Cw["pre_open"] = pre
        margin = np.zeros(len(ok))
        idx = np.flatnonzero(ok)
        if len(idx):
            Tb = np.stack([self.to_base(Cw["T"][i]) for i in idx])
            r_ok, _, m = self.planner.ik(Tb)
            ok[idx] = r_ok
            margin[idx] = m
        return ok, margin

    def choose(self, k: str, info: dict):
        C = self._load(k)
        if C is None or not len(C["w"]):
            return None
        c, q = self.w.env.object_pose(k)
        Cw = G.to_world(C, c, q)
        Cw["test_ok"] = C["test_ok"].copy()
        for j in self.failed:
            Cw["test_ok"][j] = False
        self.refresh_world(exclude=(k,))
        ok, margin = self._valid(k, Cw)
        obs = getattr(self.w, "last_obs", None)
        cam = obs.cams.get("head") if obs is not None else None
        depth = (obs.depth or {}).get("head") if obs is not None and getattr(obs, "depth", None) else None
        seed = int(getattr(self.w, "vseed", 0) or 0)
        robot_xy = self.T_world_base()[:2, 3]
        from ..sim.scene import OBJ_GEOM
        g = OBJ_GEOM.get(k, {})
        he = np.asarray(g.get("half_extents", (0.03, 0.03, 0.05)), float)
        cat = f"{g.get('category', '')} {g.get('name', '')}".lower()
        hollow = bool(g.get("inside")) or any(x in cat for x in ("cup", "mug", "bowl", "glass", "vase", "pot", "jar",
                                                                 "basket", "bucket", "pitcher"))
        elong = float(max(he[:2])) > 2.5 * float(min(he[:2]))
        parts = np.array([G.part_of(C["c1"][i], C["c2"][i], float(C["w"][i]), he, hollow, elong)
                          for i in range(len(C["w"]))])
        Cw["part"] = parts
        gc = VP.choose(Cw, ok, margin, c, robot_xy, seed, len(self.picks), constraint=info.get("constraint"),
                       cam=cam, depth=depth, allow_instruct=(len(self.picks) == 0 and not self.regrasp_n),
                       parts=parts, category=cat, height=2 * float(he[2]))
        if gc is not None:
            gc.meta.update(obj=k, tested=bool(C.get("tested", False)), n_candidates=int(len(C["w"])),
                           n_valid=int(ok.sum()), curobo=self.curobo, grip=self.grip)
            self._Cw, self._ok, self._margin = Cw, ok, margin
        return gc

    def prechoose(self) -> None:
        """Right after the world reset: render the head (with depth) once, choose the first pick's grasp, and for an
        instructed row append the approach to the episode instruction before the first request is built."""
        import dataclasses
        from ..sim import tasks as T
        self.w.observe(depth=True)
        info = self.w.task_info()
        self.choice, self.choice_key = self.choose(info["tgt"], info), (info["tgt"], info["place"])
        gc = self.choice
        if gc is not None and gc.instructed:
            self.instruction_suffix = VP.instruction_suffix(gc)
            name = self.w.env.task
            if name in T.TASKS:
                t = T.TASKS[name]
                T.TASKS[name] = dataclasses.replace(t, instruction=t.instruction + self.instruction_suffix)
                if name in getattr(T, "X_TASKS", {}):
                    T.X_TASKS[name] = T.TASKS[name]

    def next_fallback(self, gc):
        """Fallback order (spec §12.8): same family rot +-1, +-2 bins -> neighbour families -> None."""
        if not hasattr(self, "_Cw"):
            return None, None
        Cw, ok = self._Cw, self._ok.copy()
        ok[gc.idx] = False
        self._ok = ok
        c = (Cw["c2"] - Cw["c1"]) / np.maximum(Cw["w"], 1e-9)[:, None]
        rb = np.array([G.rot_base(a, cc)[1] for a, cc in zip(Cw["a"], c)])
        f_dir = gc.T[:2, 3] - self.T_world_base()[:2, 3]
        fam = np.array([G.family(a, f_dir) for a in Cw["a"]])
        b0 = int(gc.meta.get("rot_bin_base", 0))
        for f, b in G.fallback_order(gc.family, b0)[1:]:
            m = ok & (fam == f) & ((rb == b) if b is not None else True)
            idx = np.flatnonzero(m)
            if len(idx):
                i = int(idx[np.argmax(self._margin[idx])])
                new = VP.choose({k: (v[[i]] if isinstance(v, np.ndarray) and len(v) == len(Cw["w"]) else v)
                                 for k, v in Cw.items()}, np.ones(1, bool), self._margin[[i]],
                                gc.T[:3, 3], self.T_world_base()[:2, 3], 0, len(self.picks), allow_instruct=False)
                if new is None:
                    continue
                new.idx = i
                new.meta.update({x: gc.meta.get(x) for x in ("obj", "tested", "n_candidates", "n_valid", "curobo",
                                                           "grip", "valid_set", "label_rule", "rule_step",
                                                           "approach_reason", "instructed_approach")})
                note = (f"{gc.family} approach out of reach -> {new.family}, rot bin {b0} -> "
                        f"{new.meta.get('rot_bin_base')}")
                return new, note
        return None, f"no reachable grasp of the target in any approach ({gc.family} first)"

    # ------------------------------------------------------------------ truth plan (xlabels.plan hook)
    def status2(self, st: dict) -> dict:
        env = self.w.env
        p, q = self.w.pl.tcp_pose()
        return dict(st, tcp_quat=np.asarray(q, float), obj_quat={k: np.asarray(env.object_pose(k)[1], float)
                                                                 for k in st["obj"]})

    def plan(self, st: dict, info: dict, table_z: float, w_open: float):
        tg = info["tgt"]
        hold = st["pred"].get(f"holding({tg})") is True
        key = (tg, info["place"])
        if self.choice_key != key and not hold:
            if self.choice is not None:
                self.picks.append(self.pick_record())
            self.choice, self.choice_key, self.segs, self.held = self.choose(tg, info), key, {}, None
            self.timeline = {}
        gc = self.choice
        if gc is None:
            return "tipped", None
        if hold and self.held is None:
            T_obj = T_of(*self.w.env.object_pose(tg))
            self.held = {"T_obj_G": P9.inv_T(T_obj) @ self.tcp_T()}
        if not hold:
            self.held = None
        step, cmd = VP.plan(self.status2(st), info, table_z, w_open, gc, self.held)
        self.last_label = (step, cmd)
        if cmd is None:
            return step, None
        return step, {k: v for k, v in cmd.items() if k != "quat_wxyz"}

    # ------------------------------------------------------------------ motion (TrajExec.go_to)
    def motion_for(self, pos, grip: str):
        lab = self.last_label
        if lab is not None and lab[1] is not None and lab[1].get("position_m") is not None and \
                float(np.linalg.norm(np.asarray(lab[1]["position_m"]) - pos)) < 0.003:
            step, cmd = lab
        else:
            step, cmd = None, None
        gc = self.choice
        tg = (self.choice_key or (None,))[0]
        st = self.w.status()
        hold = tg is not None and st["pred"].get(f"holding({tg})") is True
        q0 = self.arm_q()
        width = None
        note = None
        if step == "above_target" and gc is not None:
            self.refresh_world(exclude=(tg,))  # gripper vs target: grasp9 swept check; arm vs the rest: cuRobo
            while gc is not None:
                r = self.planner.grasp(q0, self.to_base(gc.T), gc.standoff, gc.lift_dz)
                if r["ok"]:
                    self.segs = r
                    break
                self.timeline.setdefault("fallback_trace", []).append({"family": gc.family, "status": r["status"]})
                gc, n2 = self.next_fallback(gc)
                note = n2
                if gc is not None:
                    gc.meta["fallback_from"] = self.choice.meta.get("family")
                    self.choice = gc
            if gc is None:
                return None, note, None
            width = gc.pre_open
            self.timeline.update(open_set_at="standoff", pre_open_w=round(gc.pre_open, 4))
            return self._resample(self.segs["approach"]), note, width
        if step == "descend_close" and gc is not None:
            Q = self.segs.get("grasp")
            if Q is None or np.abs(Q[0] - q0).max() > 0.08:
                self.refresh_world(exclude=(tg,))
                r = self.planner.grasp(q0, self.to_base(gc.T), gc.standoff, gc.lift_dz)
                if not r["ok"]:
                    return None, "the grasp pose is out of reach from here", None
                self.segs = r
                Q = np.concatenate([r["approach"], r["grasp"]])
            n = len(Q)
            cut = max(1, int(n * 0.6))  # the final part of the straight approach at half speed (A2)
            return np.concatenate([self._resample(Q[:cut + 1])[:-1], self._resample(Q[cut:], slow=2.0)]), None, None
        quat = np.asarray(cmd["quat_wxyz"], float) if cmd is not None and "quat_wxyz" in cmd else \
            np.asarray(self.w.pl.tcp_pose()[1], float)
        T = T_of(pos, quat)
        if hold:
            self.refresh_world(holding=tg)
        else:
            self.refresh_world(exclude=(tg,) if step in ("retreat",) else ())
        Q0 = None
        if step == "carry_up" and self.segs.get("lift") is not None and np.abs(self.segs["lift"][0] - q0).max() < 0.08:
            Q0 = self.segs["lift"]
            self.segs["lift"] = None
            q0 = Q0[-1]
        Q = self.planner.pose(q0, self.to_base(T))
        if Q is None and Q0 is None and step in ("lower_open", "retreat", "lift_clear", "carry_up", "reopen", None):
            Q = self.planner.line(q0, self.to_base(self.tcp_T()), self.to_base(T))  # short straight moves near contact
            if Q is not None:
                self.timeline.setdefault("line_moves", []).append(step)
        if Q is None:
            if Q0 is not None:
                return self._resample(Q0), "lifted a little; the carry path is blocked", None
            return None, "no collision-free path to the target", None
        if Q0 is not None:
            Q = np.concatenate([Q0, Q])
        return self._resample(Q), note, width

    def _resample(self, Q, slow: float = 1.0) -> np.ndarray:
        s = self.style or {}
        kind = s.get("profile", "minjerk")
        v = float(s.get("v_avg", 0.09) or 0.09)
        return P9.resample(Q, kind=kind if kind in P9.PEAK else "minjerk", split=float(s.get("split", 0.7)),
                           slow=slow * max(1.0, 0.09 / v))

    # ------------------------------------------------------------------ gripper events
    def on_grip_cmd(self, action: str, t: float) -> None:
        self.timeline.setdefault("t_close_cmd" if action == "close" else "t_open_cmd", round(t, 3))

    def on_grip_done(self, action: str, t: float, ws: list):
        gc = self.choice
        if action != "close" or gc is None:
            return None
        gap = float(ws[-1][1]) if ws else float(self.w.status()["grip_w"])
        out = classify_close(gap, gc.w)
        self.timeline.update(t_settle=round(t, 3), final_gap=round(gap, 4), outcome_close=out, close_cmd_w=0.0)
        if out == "CONTACT":
            self._gap_before = gap
            return f"gripper closed on the object (gap {gap * 100:.1f} cm)"
        self.failed.add(gc.idx)
        self.regrasp_n += 1
        self.timeline.setdefault("regrasp_trace", []).append({"outcome": out, "gap": round(gap, 4), "idx": gc.idx})
        self.choice_key = None if self.regrasp_n <= 1 else self.choice_key  # one re-grasp with the next candidate
        if self.regrasp_n > 1:
            self.choice = None
        what = "nothing between the fingers" if out == "EMPTY" else "the gap does not match the object"
        return f"grasp check: {what} (gap {gap * 100:.1f} cm); reopen and try another grasp"

    def on_move_done(self, t: float) -> None:
        gc = self.choice
        if gc is None or "outcome_close" not in self.timeline or "outcome_lift" in self.timeline:
            return
        tg = (self.choice_key or (None,))[0]
        st = self.w.status()
        if tg is None or st["pred"].get(f"holding({tg})") is not True or self.held is None:
            return
        T_obj = T_of(*self.w.env.object_pose(tg))
        rel = P9.inv_T(T_obj) @ self.tcp_T()
        move = float(np.linalg.norm(rel[:3, 3] - self.held["T_obj_G"][:3, 3]))
        out = classify_lift(getattr(self, "_gap_before", 0.0), float(st["grip_w"]), move)
        self.timeline.update(outcome_lift=out, gap_after_microlift=round(float(st["grip_w"]), 4),
                             slip_mm=round(move * 1e3, 1))

    # ------------------------------------------------------------------ records
    def pick_record(self) -> dict:
        gc = self.choice
        rec = {"timeline": dict(self.timeline), "regrasp_n": self.regrasp_n}
        if gc is not None:
            rec.update(gc.meta)
            rec.update(standoff=round(gc.standoff, 4), place_dz=round(gc.place_dz, 4), retreat=round(gc.retreat, 4),
                       lift_dz=round(gc.lift_dz, 4), pre_open_w=round(gc.pre_open, 4), w_contact=round(gc.w, 4),
                       legacy_close_w=round(max(gc.w - 0.014, 0.0), 4), collision_checked_w=round(gc.pre_open, 4))
        return rec

    def episode_meta(self) -> dict:
        picks = list(self.picks) + ([self.pick_record()] if self.choice is not None or self.timeline else [])
        return {"grasp_label_version": "v2", "motion_version": VERSION, "planner": f"cuRobo {self.curobo}",
                "label_origin": "l9v2", "robot_profile": self.profile, "arm": self.arm,
                "gripper": {k: self.gr.get(k) for k in ("name", "max_open", "pad_len", "finger_w", "tip", "source")},
                "picks": picks, "instruction_suffix": self.instruction_suffix}


def free_opening(T, gr: dict, boxes, w: float, pre: float):
    """P1: the widest opening <= pre (5 mm steps, >= w + 0.5 cm) at which the two finger slabs and the palm, swept
    back to the stand-off, overlap no neighbour box (SAT); None when blocked. boxes = (C (N,3), H (N,3), R (N,3,3))."""
    C, H, Rb = boxes
    if len(C) == 0:
        return float(pre)
    R, t = T[:3, :3], T[:3, 3]

    def blocked(bx):
        for c, h in bx:
            if G.obb_overlap(R @ c + t, h, R, C, H, Rb).any():
                return True
        return False
    if blocked(G.boxes(gr, float(pre), G.STANDOFF)[2:]):  # the palm does not depend on the opening
        return None
    for ow in np.arange(pre, w + 0.005 - 1e-9, -0.005):
        if not blocked(G.boxes(gr, float(ow), G.STANDOFF)[:2]):
            return float(ow)
    return None


# ---------------------------------------------------------------------------------------------- install
def install(world, profile: str = "ffw_sg2", arm: str = "right", device: str = "cuda:0", allow_untested=False,
            style=None) -> Runtime:
    global CURRENT
    rt = Runtime(world, profile, arm, device=device, allow_untested=allow_untested, style=style)
    world.rt = rt
    CURRENT = rt
    from ..teach_l8d import xlabels as XL
    from ..teach_pt import collect as TPC
    from ..astra_solo import episode as E
    from ..astra_solo import pt_episode as PE
    if not getattr(XL.plan, "_v2", False):
        orig_plan = XL.plan

        def plan(st, info, table_z, w_open):
            r = CURRENT
            if r is None or getattr(r.w, "rt", None) is not r or info.get("kind") == "push":
                return orig_plan(st, info, table_z, w_open)
            return r.plan(st, info, table_z, w_open)
        plan._v2 = True
        XL.plan = plan
    if not getattr(TPC.pt_command, "_v2", False):
        orig_pt = TPC.pt_command

        def pt_command(step, cmd, st, info, head, depth, table_z):
            c, m = orig_pt(step, cmd, st, info, head, depth, table_z)
            r = CURRENT
            if r is None or c is None or r.choice is None or step not in ("above_target", "descend_close"):
                return c, m
            gm = r.choice.meta
            c = dict(c, approach=r.choice.family, rot=gm.get("rot_bin_img"))
            if gm.get("point") is not None:
                c["point_2d"] = gm["point"]
            return c, dict(m or {}, v2_point_src=gm.get("point_src"))
        pt_command._v2 = True
        TPC.pt_command = pt_command
    if not getattr(E.Episode.make_exec, "_v2", False):
        orig_mk = E.Episode.make_exec

        def make_exec(self, st):
            r = getattr(self.w, "rt", None)
            return TrajExec(r, st) if r is not None else orig_mk(self, st)
        make_exec._v2 = True
        E.Episode.make_exec = make_exec
    if not getattr(E.outcome, "_v2", False):
        orig_out = E.outcome

        def outcome(e):
            if e.get("note_only"):
                return e["note"]
            s = orig_out(e)
            return f"{s}; {e['note']}" if e.get("note") else s
        outcome._v2 = True
        E.outcome = outcome
        PE.outcome = outcome
    orig_step, orig_reset = world.step, world.reset

    def step(self, cmd_pos, width: float, quat=None):
        r = self.rt
        if r is None or r.q_target is None:
            return orig_step(cmd_pos, width, quat)
        env = self.env
        g = self.pl._gravity_offset()[0].cpu().numpy()
        q = env.robot.data.joint_pos[0, r.arm_ids].cpu().numpy().copy()
        for j, sid in enumerate(r.sim_ids):
            q[r.arm_ids.index(sid)] = r.q_target[j]
        env.step(np.concatenate([q + g, [float(width)]]).astype(np.float32))
        self._st = None
        self._log_step()
        if hasattr(self, "_jlog"):
            self._jlog.append(env.robot.data.joint_pos[0].cpu().numpy().copy())

    def reset(self, seed, task=None):
        out = orig_reset(seed, task) if task is not None else orig_reset(seed)
        self.rt.reset_episode()
        self.rt.prechoose()
        return out
    world.step = types.MethodType(step, world)
    world.reset = types.MethodType(reset, world)
    return rt


def has_candidates(profile: str, k: str, untested: bool = False, min_pass: int = 8) -> bool:
    """A target is usable by v2 when its candidate cache exists and (unless untested) its Isaac test file has at
    least min_pass passing candidates (spec §12.4)."""
    g = GRIP_NAME.get(profile, profile)
    if not os.path.exists(os.path.join(GRASP_DIR, g, f"{k}.npz")):
        return False
    if untested:
        return True
    t = os.path.join(TESTED_DIR, g, f"{k}.npz")
    if not os.path.exists(t):
        return False
    r = np.load(t)
    ok = r["pass"] if "pass" in r.files else (r["shake_ok"] if "shake_ok" in r.files else None)
    return ok is not None and int(np.asarray(ok, bool).sum()) >= min_pass
