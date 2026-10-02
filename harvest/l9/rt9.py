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
from . import hand9 as H
from . import plan9 as P9
from . import robot9 as R9
from . import v2plan as VP

GRASP_DIR = os.environ.get("L9V2_GRASPS", "/data/harvest/l9v2/grasps")
TESTED_DIR = os.environ.get("L9V2_TESTED", "/data/harvest/l9v2/tested")
GGX_GRASP_DIR = os.environ.get("L9V2_GGX_GRASPS", "")  # opt-in: GraspGenX candidates merged into the cache (_merge_ggx)
GGX_TESTED_DIR = os.environ.get("L9V2_GGX_TESTED", "/data/harvest/l9v2/tested_ggx")
CARRY_INVIEW = os.environ.get("L9_CARRY_INVIEW") == "1"  # opt-in, default off (user order 10-03): among the
# already-computed carry_over z candidates, prefer the one keeping the held object / TCP in the head camera view
VERSION = "l9v2-1"
GRIP_NAME = {"ffw_sg2": "ffw_sg2", "franka_mast": "franka", "r1pro": "r1pro", "g1": "g1"}
EMPTY_M, CONTACT_TOL, CONTACT_TOL_HI, SLIP_GAP, SLIP_MOVE = 0.003, 0.008, 0.020, 0.003, 0.010
LIMIT_MARGIN = 0.01
CMD_DQ = 0.034  # command step cap: the measured arm lags then catches up, 12 of ~120 pilot successes measured
# 0.0401-0.047 rad at a 0.04 command cap (rejected by the <= 0.04 gate); 0.034 x 1.17 stays under 0.04
# L9v2-R1: R1 Pro arm lags its target up to 0.2 rad (kp 1000 / kd 200) and catches up with 0.042-0.050 rad steps
# when the target stops (vL8 10-03, 2 of 8 successes rejected): a smaller command step for that robot (opt-in)
CMD_DQ_BY = {"r1pro": 0.026} if os.environ.get("IR_L9_R1_DQ", "") == "1" else {}
WIDE_KEEP = 0.045
TARGET_CORE = 0.5  # while approaching, the target is an obstacle at half its box: the fingers / palm around a grasp
#                    stay outside the core, the arm cannot pass through the object (smoke 10-02: full box -> no grasp
#                    plannable; no box -> the arm knocked the target off the table)
MAX_FALLBACK = 6
SETTLE_DW, SETTLE_N, SETTLE_MAX_S, WIN_S = 0.001, 3, 0.6, 0.05
REACH_TOL, HOLD_MAX_S = 0.012, 1.5
# L9v2-R1: straight approach from the grasp end + joint-space transit when the forward one fails (opt-in per robot)
REVERSE_APPROACH = {"r1pro": os.environ.get("IR_L9_R1_REVERSE", "1") == "1"}
GRASP_LINKS_CHECK = {"r1pro": os.environ.get("IR_L9_R1_GRASPCHK", "1") == "1"}  # L9v2-R1, see Runtime._valid
PLACE_CHECK = {"r1pro": os.environ.get("IR_L9_R1_PLACECHK", "") == "1"}  # L9v2-R1, see Runtime._place_reach
LIFT_SKIP = {"r1pro": os.environ.get("IR_L9_R1_LIFTSKIP", "") == "1"}  # L9v2-R1, see Runtime.plan
# L9 common executor (opt-in, default off = unchanged; user rule 10-03 03h, audit rows 2-4, 6-8, 11, 21): the R1 / G1
# executor fixes above for EVERY robot, robots differing only by their measured data (robot9 CARRY_CLEAR_RANGE /
# env profile carry_clear_m, TRACK_OVERSHOOT, the sim start pose for the cuRobo locks, the IK ready branch)
COMMON = os.environ.get("L9_COMMON_EXEC") == "1"
CURRENT = None


def on(table: dict, profile: str, common: bool | None = None) -> bool:
    """A per-robot executor switch (REVERSE_APPROACH, GRASP_LINKS_CHECK, PLACE_CHECK, LIFT_SKIP): on for every
    robot under the common executor, else the robot's own entry."""
    return bool(COMMON if common is None else common) or bool(table.get(profile))


def carry_range(profile: str, common: bool | None = None):
    """Carry clearance range (m) or None (default carry height): common executor = every robot's measured / common
    range (robot9.carry_clear_range), else the robot-only V2_CARRY_CLEAR entry."""
    if COMMON if common is None else common:
        return R9.carry_clear_range(profile)
    return getattr(R9, "V2_CARRY_CLEAR", {}).get(profile)


def cmd_dq(profile: str, common: bool | None = None) -> float:
    """Command step cap: common executor = from the robot's measured tracking overshoot, else CMD_DQ_BY / CMD_DQ."""
    if COMMON if common is None else common:
        return R9.cmd_dq_cap(profile, CMD_DQ)
    return CMD_DQ_BY.get(profile, CMD_DQ)


def locks_from_sim(cfg: dict, names, values) -> tuple:
    """cuRobo lock_joints (every joint the planner does not move: the idle arm, head, fingers) set to the sim's own
    start pose (audit 21: G1 idle-arm locks were 0 = forearm over the table while the sim stowed it). Pure; joints
    the sim does not have keep their config value. -> (cfg copy, {joint: (old, new)} for the changed ones)."""
    import copy
    out = copy.deepcopy(cfg)
    lk = out["robot_cfg"]["kinematics"].get("lock_joints") or {}
    sim = {str(n): float(v) for n, v in zip(names, values)}
    changed = {}
    for j in list(lk):
        if j in sim and abs(float(lk[j]) - sim[j]) > 1e-4:
            changed[j] = (float(lk[j]), round(sim[j], 5))
            lk[j] = round(sim[j], 5)
    return out, changed


def classify_close(gap: float, w_contact: float) -> str:
    """P2 judgement on the settled gap (thresholds = hypotheses, E-AP1 recalibrates once)."""
    if gap < EMPTY_M:
        return "EMPTY"
    if -CONTACT_TOL <= gap - w_contact <= CONTACT_TOL_HI:  # smoke 10-02: settled gaps run ~1.5 cm over the contact width
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
        self.width = float(w.w_open)  # L9v2-DIAG 9: no pre-shape at the episode start: the hand may start low among
        # objects, fingers closing there jammed on one side and the wrist roll saturated (5.1 Nm, 0.06-0.34 rad steps)
        self.width_after = None
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
        self.width_after = width if Q is not None else None  # pre-open: set when the transit ends at the stand-off
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
            self.width = self.rt.release_width()  # release: pre-open + 1.5 cm (pads must leave the object)
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
                if self.width_after is not None:  # spec 12.12 P1: pre-open at the stand-off
                    self.width, self.width_after = self.width_after, None
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
        self.gtab = H.active_table(profile, arm)  # L9 grip layer (opt-in L9_GRIP_LAYER=1), None = unchanged
        if self.gtab is not None:  # every opening is a measured free gap: the max is the measured one
            self.gr = dict(self.gr, max_open=self.gtab.max_gap)
        self.allow_untested = allow_untested
        self.base_link = C9.base_link(profile, arm)
        self.joints = C9.arm_joints(profile, arm)
        from .plan9_server import PlannerProxy  # cuRobo needs warp >= 1.14; the Isaac app holds warp 1.8.2
        cfg = C9.load_config(profile, arm)
        self.lock_changes = None
        if COMMON:  # audit 21: cuRobo locks = the sim start pose of every non-planned joint
            r0 = world.env.robot
            cfg, self.lock_changes = locks_from_sim(cfg, r0.joint_names, r0.data.default_joint_pos[0].cpu().numpy())
        self.planner = PlannerProxy(cfg, device=device)
        self.curobo = self.planner.version
        self.style = style
        rob = world.env.robot
        self.sim_ids = [rob.joint_names.index(j) for j in self.joints]
        self.arm_ids = list(world.env.arm_ids)
        self.base_idx = rob.body_names.index(self.base_link)
        lim = rob.data.soft_joint_pos_limits[0].cpu().numpy()
        self.q_lo, self.q_hi = lim[self.sim_ids, 0] + LIMIT_MARGIN, lim[self.sim_ids, 1] - LIMIT_MARGIN
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
        self.dead = False
        self._retreat_fail = 0
        self._settle_n = 0
        self._n_dump = 0  # failed-plan dumps per episode (L9V2_DEBUG_DIR)
        self._lift_clear_failed = 0

    def arm_q(self) -> np.ndarray:
        return self.w.env.robot.data.joint_pos[0, self.sim_ids].cpu().numpy().astype(float)

    def plan_start(self) -> np.ndarray:
        """The measured arm state clipped 0.04 rad inside the sim range: cuRobo refuses a start state on a limit
        (smoke 10-02: the L9 preroll pose has arm_r_joint7 = 1.82 = its upper limit -> 'Start or End state in
        collision' for every plan)."""
        q = self.arm_q()
        if self.q_target is not None and np.abs(np.asarray(self.q_target) - q).max() < 0.15:
            # continue from the last COMMANDED joints: the arm rests a few hundredths of a rad off its target (PD +
            # gravity), and restarting from the measured joints made the command jump by that error (pilot 10-02:
            # 22 of 49 episodes had a 0.05-0.16 rad step at a plan start)
            q = np.asarray(self.q_target, float)
        return np.clip(q, self.q_lo + 0.03, self.q_hi - 0.03)

    def T_world_base(self) -> np.ndarray:
        d = self.w.env.robot.data
        return T_of(d.body_pos_w[0, self.base_idx].cpu().numpy(), d.body_quat_w[0, self.base_idx].cpu().numpy())

    def to_base(self, T_world) -> np.ndarray:
        return P9.inv_T(self.T_world_base()) @ np.asarray(T_world, float)

    def tcp_T(self) -> np.ndarray:
        p, q = self.w.pl.tcp_pose()
        return T_of(p, q)

    def release_width(self) -> float:
        """Opening after a release / reopen: the pre-open + 1.5 cm (clipped to the max): at the pre-open alone the
        pads could keep touching a slightly turned object, 'holding' stayed true and the retreat dragged it."""
        if getattr(self, "_release_full", False) or getattr(self, "_last_step", None) == "lower_open":
            return float(self.w.w_open)  # releasing at the place: open fully (pilot 10-02: the object sat within
            # 3-12 mm of the place at the release and ended 40-200 mm away: the pads dragged it on the retreat)
        return float(min(self.w.w_open, self.open_width() + 0.015))

    def open_width(self) -> float:
        return float(self.choice.pre_open) if self.choice is not None else float(self.w.w_open)

    # ------------------------------------------------------------------ obstacles
    def obstacle_boxes(self, exclude=(), shrink: dict | None = None) -> dict:
        from ..sim.scene import OBJ_GEOM
        env = self.w.env
        out = {}
        for k in env.present:
            g = OBJ_GEOM.get(k, {})
            if k in exclude or g.get("shape") in ("marker", "surface") or "half_extents" not in g:
                continue
            c, q = env.object_pose(k)
            f = (shrink or {}).get(k, 1.0)
            out[f"obj_{k}"] = (np.asarray(c, float), [2 * float(v) * f for v in g["half_extents"]], np.asarray(q, float))
        return out

    def refresh_world(self, holding: str | None = None, exclude=(), below_z: float | None = None,
                      shrink: dict | None = None, extra_boxes: dict | None = None) -> None:
        """World cuboids for cuRobo. below_z: drop every cuboid whose top is below below_z + 3 cm (the support the
        held object leaves or reaches: lift-off and placement are vertical moves, and the attached object starting
        or ending on its support is a start / end collision for cuRobo; smoke 10-02, 2 of 8 episodes stuck).
        extra_boxes (L9 bimanual, harvest.l9.bimanual9, opt-in -- default None = unchanged): more cuboids
        {name: (center, full_extents, quat)} merged in after the below_z filter (never dropped by it), e.g. the
        other arm's current TCP box."""
        fs = getattr(self.w, "scene9", {}) or {}
        parts = [p for p in fs.get("furniture", []) if "size" in p and "pos" in p]
        boxes = self.obstacle_boxes(exclude, shrink)
        if below_z is not None:
            lim = below_z + 0.03
            parts = [p for p in parts if float(p["pos"][2]) + float(p["size"][2]) / 2 > lim]
            boxes = {k: v for k, v in boxes.items() if k == f"obj_{holding}" or float(v[0][2]) + v[1][2] / 2 > lim}
        if extra_boxes:
            boxes.update(extra_boxes)
        scene = P9.scene_cuboids(parts, boxes, self.T_world_base(), pad=0.005)
        self.planner.world(scene)
        dbg = os.environ.get("L9V2_DEBUG_DIR")
        if dbg and not getattr(self, "_dumped", False):  # one dump per process: scene + start state (diagnosis)
            import json
            os.makedirs(dbg, exist_ok=True)
            json.dump({"scene": scene, "q": self.arm_q().tolist(), "joints": self.joints,
                       "T_world_base": self.T_world_base().tolist(), "tcp_T": self.tcp_T().tolist(),
                       "parts": parts}, open(os.path.join(dbg, f"scene_{os.getpid()}.json"), "w"), default=str)
            self._dumped = True
        if holding and self.planner.attach(self.arm_q(), [f"obj_{holding}"]) is False:
            self.timeline["attach_fail"] = self.timeline.get("attach_fail", 0) + 1  # planned without the object

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
            ok = tested_mask(r, len(d["w"]))
            d["tested"] = True
        elif not self.allow_untested:
            ok[:] = False
        d["source"] = np.array(["analytic"] * len(d["w"]))
        d["test_ok"] = ok
        if GGX_GRASP_DIR:
            d = self._merge_ggx(d, oid, r if os.path.exists(t) else None)
        self._cand[k] = d
        return d

    def _merge_ggx(self, d: dict, oid: str, r_an) -> dict:
        """Production candidates = analytic antipodal U GraspGenX (L9V2_GGX_GRASPS / L9V2_GGX_TESTED, opt-in): the
        GGX ones only count when they passed the same sim lift/shake test (tested_mask). Adds per candidate:
        ggx_s (own GGX confidence, or the best GGX confidence next to an analytic one, harvest.l9.ggx_cache.ggx_support)
        and slip_mm (sim test slip, NaN untested) for the ggx_v1 label rule."""
        from . import ggx_cache as GC
        K0 = len(d["w"])
        slip = np.full(K0, np.nan)
        if r_an is not None and "slip_mm" in r_an and "idx" in r_an and len(r_an["idx"]) == len(r_an["slip_mm"]):
            ix = np.asarray(r_an["idx"], int)
            slip[ix[ix < K0]] = np.asarray(r_an["slip_mm"], float)[ix < K0]
        f = os.path.join(GGX_GRASP_DIR, self.grip, f"{oid}.npz")
        if not os.path.exists(f):
            print(f"GGXDBG load {oid} grip={self.grip} analytic={K0} ggx_file=missing", flush=True)
            d["ggx_s"], d["slip_mm"] = np.zeros(K0), slip
            return d
        X = dict(np.load(f))
        K1 = len(X["w"])
        okx = np.zeros(K1, bool)
        slx = np.full(K1, np.nan)
        tf = os.path.join(GGX_TESTED_DIR, self.grip, f"{oid}.npz")
        if os.path.exists(tf):
            rx = dict(np.load(tf))
            okx = tested_mask(rx, K1)
            if "slip_mm" in rx and "idx" in rx and len(rx["idx"]) == len(rx["slip_mm"]):
                ix = np.asarray(rx["idx"], int)
                slx[ix[ix < K1]] = np.asarray(rx["slip_mm"], float)[ix < K1]
        sup = GC.ggx_support(d, X) if K1 else np.zeros(K0)
        out = {}
        for key in ("T", "c1", "c2", "w", "a", "score", "pre_open"):
            out[key] = np.concatenate([np.asarray(d[key]), np.asarray(X[key]).reshape((K1,) + np.asarray(d[key]).shape[1:])])
        out["source"] = np.concatenate([d["source"], np.array(["graspgenx"] * K1)])
        out["test_ok"] = np.concatenate([d["test_ok"], okx])
        out["ggx_s"] = np.concatenate([sup, np.asarray(X["score"], float)])
        out["slip_mm"] = np.concatenate([slip, slx])
        for key in d:
            if key not in out:
                out[key] = d[key]
        print(f"GGXDBG load {oid} grip={self.grip} analytic={K0} pass={int(d['test_ok'].sum())} ggx={K1} "
              f"ggx_pass={int(okx.sum())} analytic_with_ggx_support={int((sup > 0).sum())}", flush=True)
        return out

    def _valid(self, k: str, Cw: dict, extra_boxes: dict | None = None) -> tuple:
        """valid mask (test pass, support clearance, neighbour finger clearance at pre_open, reach) + margin.
        extra_boxes: see Runtime.refresh_world (L9 bimanual, opt-in, default None = unchanged)."""
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
        if self.gtab is not None:  # grip layer: only candidates that fit the measured free gap; pre-open >= the
            # contact width + 2 cm of REAL free gap (g1b H5, every robot), clipped to the measured max
            w_c = np.asarray(Cw["w"], float)
            ok &= w_c <= self.gtab.max_gap - G.OPEN_MARGIN
            pre = np.minimum(np.maximum(pre, w_c + H.PRE_CLEAR), self.gtab.max_gap)
        vs = {"candidates": int(len(ok)), "test_ok": int(ok.sum()), "support_ok": 0, "free_ok": 0, "ik_ok": 0}
        for i in np.flatnonzero(ok):
            T = Cw["T"][i]
            if G.lowest_point(T, self.gr, pre[i]) < sup + G.SUPPORT_CLEAR:
                ok[i] = False
                continue
            vs["support_ok"] += 1
            w_free = free_opening(T, self.gr, boxes, float(Cw["w"][i]), pre[i])
            if w_free is None:
                ok[i] = False
            else:
                pre[i] = w_free
                vs["free_ok"] += 1
        Cw["pre_open"] = pre
        margin = np.zeros(len(ok))
        idx = np.flatnonzero(ok)
        if len(idx):
            Tb = np.stack([self.to_base(Cw["T"][i]) for i in idx])
            r_ok, _, m = self.planner.ik(Tb)
            ok[idx] = r_ok
            margin[idx] = m
            idx = np.flatnonzero(ok)
        if len(idx):  # the pre-grasp too, with the target as a full obstacle (the transit checks every link)
            sd = draws_standoff(int(getattr(self.w, "vseed", 0) or 0), len(self.picks))
            Tp = []
            for i in idx:
                T = Cw["T"][i].copy()
                T[:3, 3] = T[:3, 3] - Cw["a"][i] * sd
                Tp.append(self.to_base(T))
            self.refresh_world(below_z=self._bottom_z(k) - 0.02, extra_boxes=extra_boxes)
            r_ok, _, _ = self.planner.ik(np.stack(Tp), contact_links_off=False)
            ok[idx] = r_ok
            idx = np.flatnonzero(ok)
            if len(idx) and on(GRASP_LINKS_CHECK, self.profile):
                # L9v2-R1: the grasp pose with the gripper links checked against everything but the target and its
                # support (replay 10-03: 9 of 11 unplannable straight approaches had the fingers / gripper body in a
                # fixture, holder or bucket wall at the grasp itself; the check above frees those links)
                self.refresh_world(exclude=(k,), below_z=self._bottom_z(k) - 0.02, extra_boxes=extra_boxes)
                r_ok, _, _ = self.planner.ik(np.stack([self.to_base(Cw["T"][i]) for i in idx]), contact_links_off=False)
                ok[idx] = r_ok
                vs["grasp_links_ok"] = int(r_ok.sum())
            self.refresh_world(exclude=(k,), extra_boxes=extra_boxes)
        vs["ik_ok"] = int(ok.sum())
        self._vstats = vs
        return ok, margin

    def _with_flips(self, k: str, C: dict) -> dict:
        """Every robot (opt-in L9V2_GRASP_FLIP=1): add each candidate turned 180 deg about its approach axis (x_G, y_G
        negated, contacts swapped) after the originals. The antipodal sampler keeps ONE of the two closing-axis signs
        per contact pair (grasp9.antipodal_pairs dedup) -- the same grasp for a symmetric pinch, but a different wrist
        angle, and with limited wrist ranges often the reachable one (G1 SKIPDBG 10-03: 66 of 96 'no valid grasp'
        skips had candidates past the support / free-opening checks and every one failed IK). A flip keeps the
        original's physics-test verdict (same contacts and width). Original indices are unchanged."""
        key = (k, "flip")
        if key in self._cand:
            return self._cand[key]
        n = len(C["w"])
        F = {}
        for f, v in C.items():
            if isinstance(v, np.ndarray) and v.ndim >= 1 and len(v) == n:
                F[f] = v
        Tf = C["T"].copy()
        Tf[:, :3, 0] *= -1.0
        Tf[:, :3, 1] *= -1.0
        out = dict(C)
        for f, v in F.items():
            add = {"T": Tf, "c1": C["c2"], "c2": C["c1"]}.get(f, v)
            out[f] = np.concatenate([v, add])
        if "source" in out and len(out["source"]) == 2 * n:
            out["source"] = np.concatenate([np.asarray(C["source"]), np.char.add(np.asarray(C["source"]).astype(str), "_flip")])
        self._cand[key] = out
        return out

    def choose(self, k: str, info: dict, extra_boxes: dict | None = None):
        """extra_boxes: see Runtime.refresh_world (L9 bimanual, opt-in, default None = unchanged)."""
        C = self._load(k)
        if C is not None and len(C["w"]) and (COMMON or os.environ.get("L9V2_GRASP_FLIP") == "1"):
            C = self._with_flips(k, C)
        if C is None or not len(C["w"]):
            self.picks.append({"obj": k, "choice_fail": "no candidate file" if C is None else "no candidates"})
            return None
        c, q = self.w.env.object_pose(k)
        Cw = G.to_world(C, c, q)
        Cw["test_ok"] = C["test_ok"].copy()
        for j in self.failed:
            Cw["test_ok"][j] = False
        self.refresh_world(exclude=(k,), extra_boxes=extra_boxes)
        ok, margin = self._valid(k, Cw, extra_boxes=extra_boxes)
        if on(PLACE_CHECK, self.profile) and ok.any():
            ok = ok & self._place_reach(Cw, ok, k, info)
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
        if gc is None:
            self.picks.append({"obj": k, "choice_fail": "no valid candidate", "valid_stats": getattr(self, "_vstats", None)})
        if gc is not None:
            gc.meta["valid_stats"] = getattr(self, "_vstats", None)
            cr = carry_range(self.profile)
            if cr is not None:  # L9v2-R1: per-episode carry clearance draw (range, robot-specific)
                rng = np.random.default_rng([seed, 913, len(self.picks)])
                gc.carry_clear = float(rng.uniform(*cr))
                gc.meta["carry_clear"] = round(gc.carry_clear, 4)
            self._exec_pose(gc, float(c[2]) - float(he[2]))
            self._g1_open(gc)
            gc.meta.update(obj=k, obj_h=round(2 * float(he[2]), 4), tested=bool(C.get("tested", False)),
                           n_candidates=int(len(C["w"])),
                           n_valid=int(ok.sum()), curobo=self.curobo, grip=self.grip)
            self._Cw, self._ok, self._margin = Cw, ok, margin
        return gc

    def _place_reach(self, Cw: dict, ok, k: str, info: dict) -> np.ndarray:
        """L9v2-R1: keep the grasp candidates whose grip also reaches the PLACE: the put pose (object upright at the
        place, held yaw + one of YAW_TRIES) and the pose above it (carry height) both have IK with this grasp
        (pilot 10-03: carry_over / lower_open 'no collision-free path' loops after a front / side grasp of a target
        that was reachable itself). No place / no candidate passing -> the mask is left unchanged (all True)."""
        from ..astra_motion.harness import obj_height
        from ..teach_l8 import labels as L
        from ..teach_l8d import xlabels as XL
        out = np.ones(len(ok), bool)
        pl = info.get("place")
        idx = np.flatnonzero(ok)
        if pl is None or not len(idx):
            return out
        try:
            st = self.w.status()
            p = np.asarray(st["obj"][pl], float)
        except Exception:  # noqa: BLE001
            return out
        if info.get("place_xy_offset"):
            p = p + np.array([*info["place_xy_offset"], 0.0], float)
        table_z = float(self.w.table_z)
        H = XL.heights(self._live_place(info, table_z), table_z)
        h = obj_height(k)
        c, q_obj = self.w.env.object_pose(k)
        T_obj = T_of(c, q_obj)
        dz = VP.draws(int(getattr(self.w, "vseed", 0) or 0), len(self.picks))["place_dz"]
        yaws = (0.0,) if (info.get("place_pose") or {}).get("kind") == "oriented" else self.YAW_TRIES
        cr = carry_range(self.profile) or (0.05, 0.10)
        Ts, own = [], []
        for i in idx:
            T_og = P9.inv_T(T_obj) @ Cw["T"][i]
            hang = float(Cw["T"][i][2, 3]) - (float(c[2]) - h / 2)
            zc = min(H["carry_base"] + L.CARRY_DZ, H["carry_base"] + max(hang, 0.0) + float(cr[0]))
            for d in yaws:
                T = VP.put_pose(q_obj, p, H["place_top"] + h / 2 + dz, T_og, d)
                Tu = T.copy()
                Tu[2, 3] = max(zc, T[2, 3] + 0.05)
                Ts += [self.to_base(T), self.to_base(Tu)]
                own.append(i)
        try:
            r_ok, _, _ = self.planner.ik(np.stack(Ts))
        except Exception:  # noqa: BLE001
            return out
        good = set()
        for j, i in enumerate(own):
            if r_ok[2 * j] and r_ok[2 * j + 1]:
                good.add(i)
        m = np.zeros(len(ok), bool)
        m[list(good)] = True
        if self._vstats is not None:
            self._vstats["place_ok"] = int(len(good))
        if not good and (self.picks or self.regrasp_n):  # a later pick: keep the old behaviour (no skip mid-episode)
            return out
        return m  # first pick with no grasp that reaches the place: no valid grasp -> scene skipped (reach limit)

    def prechoose(self) -> None:
        """Right after the world reset: render the head (with depth) once, choose the first pick's grasp, and for an
        instructed row append the approach to the episode instruction before the first request is built."""
        import dataclasses
        from ..sim import tasks as T
        self.w.observe(depth=True)
        info = self.w.task_info()
        self._mark("episode", int(getattr(self.w, "vseed", 0) or 0), self.profile, self.arm)
        self.choice, self.choice_key = self.choose(info["tgt"], info), (info["tgt"], info["place"])
        if self.choice is None and os.environ.get("L9V2_SKIP_UNGRASPABLE", "1") == "1":
            from ..teach_l8d.fx import SkipScene  # no valid grasp of the first target in this scene: redraw, do not
            raise SkipScene("v2: no valid grasp of the first target " + str(info["tgt"]))  # fail an episode
        gc = self.choice
        if gc is not None and gc.instructed:
            self.instruction_suffix = VP.instruction_suffix(gc)
            name = self.w.env.task
            if name in T.TASKS:
                t = T.TASKS[name]
                T.TASKS[name] = dataclasses.replace(t, instruction=t.instruction + self.instruction_suffix)
                if name in getattr(T, "X_TASKS", {}):
                    T.X_TASKS[name] = T.TASKS[name]

    G1_CLEAR = 0.02  # g1b H5: free gap at the stand-off = contact width + 2 cm (1 cm each side)

    def _g1_open(self, gc) -> None:
        """g1b H5 (G1 only): pre-open so the REAL free finger gap (robot9.G1_FREE_GAP) clears the object."""
        if self.profile != "g1" or gc is None:
            return
        from . import robot9 as R9
        want = R9.g1_open_for_gap(float(gc.w) + self.G1_CLEAR)
        if want > float(gc.pre_open):
            gc.meta["pre_open_slab"] = round(float(gc.pre_open), 4)
            gc.pre_open = min(want, float(R9.V2["g1"]["grip_max_w"]))
            gc.meta["pre_open_m"] = round(gc.pre_open, 4)

    def _exec_pose(self, gc, support_z: float) -> None:
        """Commanded TCP = the candidate frame moved back along the approach by the pad drop at the contact width:
        the RH-P12-RN pads move on an arc and sit up to 2.8 cm further along the approach when closed (L9v2-GTEST
        finger probe, gtest9.exec_pose); the Isaac test uses the same correction, so execution matches the test."""
        try:
            from . import gtest9 as GT
        except ImportError:
            return
        f = getattr(GT, "exec_pose", None)
        if f is None:
            return
        T0 = gc.T.copy()
        try:
            gc.T = np.asarray(f(T0, gc.w, self.grip, None, support_z, arm=self.arm), float)
        except TypeError:
            gc.T = np.asarray(f(T0, gc.w, self.grip), float)
        gc.meta["pad_drop_m"] = round(float(np.linalg.norm(gc.T[:3, 3] - T0[:3, 3])), 4)
        gc.meta["grasp_cmd_world"] = np.round(gc.T, 5).tolist()

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
                sub = {k: (v[[i]] if isinstance(v, np.ndarray) and len(v) == len(Cw["w"]) else v)
                       for k, v in Cw.items()}
                # the fallback keeps the label fields of a first choice: grasped part, category and the visible
                # grasp-part point from the head image (pilot 10-02: 76 of 427 picks had part None and no point)
                obs = getattr(self.w, "last_obs", None)
                cam = obs.cams.get("head") if obs is not None else None
                depth = (obs.depth or {}).get("head") if obs is not None and getattr(obs, "depth", None) else None
                new = VP.choose(sub, np.ones(1, bool), self._margin[[i]], gc.T[:3, 3], self.T_world_base()[:2, 3], 0,
                                len(self.picks), allow_instruct=False, cam=cam, depth=depth, parts=sub.get("part"),
                                category=gc.meta.get("category") or "", height=float(gc.meta.get("obj_h") or 0.0))
                if new is None:
                    continue
                new.idx = i
                if getattr(gc, "carry_clear", None) is not None:
                    new.carry_clear = gc.carry_clear
                new.meta.update({x: gc.meta.get(x) for x in ("obj", "tested", "n_candidates", "n_valid", "curobo",
                                                           "grip", "valid_set", "label_rule", "rule_step",
                                                           "approach_reason", "instructed_approach", "natural_order",
                                                           "obj_h")})
                self._g1_open(new)
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

    YAW_TRIES = (0.0, 0.5236, -0.5236, 1.0472, -1.0472, 1.5708, -1.5708, 3.1416)

    def _place_yaw(self, st: dict, info: dict, table_z: float, gc) -> float:
        """Yaw offset of the placed object (about the vertical) that makes the put pose and the pose above it
        reachable for this arm (the held orientation is often unreachable at the place: pilot 10-02 carry loops).
        0 first; definitions with an oriented place keep 0."""
        from ..teach_l8d import xlabels as XL
        from ..astra_motion.harness import obj_height
        from ..teach_l8 import labels as L
        if (info.get("place_pose") or {}).get("kind") == "oriented":
            return 0.0
        tg, pl = info["tgt"], info["place"]
        H = XL.heights(info, table_z)
        h = obj_height(tg)
        p = np.asarray(st["obj"][pl], float)
        if info.get("place_xy_offset"):
            p = p + np.array([*info["place_xy_offset"], 0.0], float)
        q_obj = np.asarray(self.w.env.object_pose(tg)[1], float)
        zc = VP.carry_z(H, L.CARRY_DZ, gc, st["tcp"], st["obj"][tg], h, True)
        Ts = []
        for d in self.YAW_TRIES:
            T = VP.put_pose(q_obj, p, H["place_top"] + h / 2 + gc.place_dz, self.held["T_obj_G"], d)
            Tu = T.copy()
            Tu[2, 3] = max(zc, T[2, 3] + 0.05)
            Ts += [self.to_base(T), self.to_base(Tu)]
        try:
            ok, _, _ = self.planner.ik(np.stack(Ts))
        except Exception:  # noqa: BLE001
            return 0.0
        for i, d in enumerate(self.YAW_TRIES):
            if ok[2 * i] and ok[2 * i + 1]:
                self.timeline["place_yaw_delta"] = d
                return d
        self.timeline["place_yaw_delta"] = None
        return 0.0

    def _live_place(self, info: dict, table_z: float) -> dict:
        """The top of an object place from its live pose (oriented box), not table + catalog height: a lying book was
        +22 mm, a second stack level counted from the table (L9v2-DIAG 10). Containers / markers / surfaces unchanged."""
        from ..sim.scene import OBJ_GEOM, SUPPORT_TOP, X_VISUAL_ONLY
        pl = info.get("place")
        g = OBJ_GEOM.get(pl, {})
        if (pl is None or pl in X_VISUAL_ONLY or pl in SUPPORT_TOP or "half_extents" not in g or g.get("inside")
                or g.get("shape") in ("marker", "surface", "openbox") or pl in getattr(self.w.env, "virtual_top", {})
                ):
            return info
        c, q = self.w.env.object_pose(pl)
        top = float(c[2]) + float(np.abs(G.qmat(q)[2]) @ np.asarray(g["half_extents"], float))
        from ..teach_l8 import labels as L
        base = float(info["place_top"]) if "place_top" in info else float(L.place_top(pl, table_z))
        self.timeline.setdefault("live_place_top_dz", round(top - base, 4))
        return dict(info, place_top=top)

    def _carry_cam(self):
        """Head camera for v2plan.carry_over_z (L9_CARRY_INVIEW only; None keeps today's behaviour everywhere
        else, and on any lookup failure -- this is a soft preference, never worth breaking the carry move)."""
        if not CARRY_INVIEW:
            return None
        try:
            return self.w._cam("cam_head", "head")
        except Exception:  # noqa: BLE001
            return None

    def plan(self, st: dict, info: dict, table_z: float, w_open: float):
        info = self._live_place(info, table_z)
        tg = info["tgt"]
        hold = st["pred"].get(f"holding({tg})") is True
        key = (tg, info["place"])
        if self.choice_key != key and not hold:
            if self.failed and self._settle_n < 3 and (
                    float(st["grip_w"]) < min(w_open, self.open_width()) - 0.01 or self.w.env.object_vel(tg) > 0.02):
                # L9v2-DIAG 5: after an EMPTY / WIDE close the object is often still moving (squeezed out); choosing
                # now aims the re-grasp at where it was, not where it settles -> open first, choose once it rests
                self._settle_n += 1
                self.last_label, self._last_step = ("reopen", {"mode": "gripper", "gripper": "open"}), "reopen"
                return "reopen", {"mode": "gripper", "gripper": "open"}
            self._settle_n = 0
            # L9v2-DIAG 3: the task stage moves on right at the release, so an intermediate target never got its
            # retreat; the next target's first move (lift_clear straight up / a transit) dragged or knocked the placed
            # object (multi-step 3 / 42 successes). Retreat from the previous target first while the hand is near it.
            ptg = (self.choice_key or (None,))[0]
            if self.choice is not None and ptg is not None and ptg != tg and not getattr(self, "_retreat_fail", 0):
                r = self._retreat_from(ptg, self.choice, st)
                if r is not None:
                    self.last_label, self._last_step = r, "retreat"
                    return r[0], {k: v for k, v in r[1].items() if k != "quat_wxyz"}
            if self.choice is not None:
                self.picks.append(self.pick_record())
            self.choice, self.choice_key, self.segs, self.held = self.choose(tg, info), key, {}, None
            if self.choice is None and self.failed:  # the re-grasp found no other candidate: the same ones again
                self.failed = set()
                self.choice = self.choose(tg, info)
            self.timeline = {}
        gc = self.choice
        if gc is None:
            return "tipped", None
        if getattr(self, "dead", False):
            return "tipped", None
        if hold and self.held is None:
            T_obj = T_of(*self.w.env.object_pose(tg))
            self.held = {"T_obj_G": P9.inv_T(T_obj) @ self.tcp_T()}
            self.held["yaw_delta"] = self._place_yaw(st, info, table_z, gc)
        elif hold:  # re-measure the grip every call: objects turn in the hand while carried (pilot 10-02: a can held
            T_obj = T_of(*self.w.env.object_pose(tg))  # from the front turned about the closing axis and the put pose
            self.held["T_obj_G"] = P9.inv_T(T_obj) @ self.tcp_T()  # from the lift-time grip tipped it over)
            nf = self.timeline.get("held_move_failed", 0)
            if nf > self.held.get("nf_seen", 0):  # only after a new failed move (keeps a yaw that works)
                self.held["nf_seen"] = nf
                # L9v2-DIAG 7: the yaw chosen at the lift was unreachable with the re-measured grip (the object slid
                # 17 mm in the hand; lower_open 'no collision-free path' 26 times until the call limit) -> choose the
                # place yaw again with the grip as it is now; stop when no yaw works after 4 failed moves
                if nf >= 4 and self.timeline.get("place_yaw_delta", 0) is None:
                    return "tipped", None
                self.held["yaw_delta"] = self._place_yaw(st, info, table_z, gc)
        if not hold:
            self.held = None
        step, cmd = VP.plan(self.status2(st), info, table_z, w_open, gc, self.held, cam=self._carry_cam())
        if step == "lift_clear" and on(LIFT_SKIP, self.profile) and getattr(self, "_lift_clear_failed", 0) and \
                getattr(self, "_last_step", None) == "lift_clear":
            # L9v2-R1: the straight-up clearance move is out of the leaned arm's reach (tall object: target
            # 13 cm higher, 30 identical failed calls in pilot 10-03); the transit to the pre-grasp is collision-
            # checked anyway -> go there directly
            step, cmd = "above_target", {"mode": "eef", "position_m": VP._r(gc.pre), "gripper": "keep",
                                         "quat_wxyz": VP._q(gc.quat)}
            self.timeline["lift_clear_skipped"] = self.timeline.get("lift_clear_skipped", 0) + 1
        if step == "retreat" and getattr(self, "_retreat_fail", 0):
            # the retreat move could not be planned (dbg6: 20 identical retreat calls): the object is placed, stop
            step, cmd = "done", {"mode": "stop"}
        if step == "reopen" and getattr(self, "_last_step", None) == "reopen":
            # the fingers could not open (blocked by the object / a neighbour): back off upward with the gripper
            # open instead of repeating 'reopen' (pilot 10-02: 38 reopens in a row until the call limit)
            tcp = np.asarray(st["tcp"], float)
            step, cmd = "lift_clear", {"mode": "eef", "position_m": [round(float(v), 4) for v in tcp + [0, 0, 0.05]],
                                       "gripper": "open", "quat_wxyz": [round(float(v), 5) for v in
                                                                        self.status2(st)["tcp_quat"]]}
        # a repeated lower_open (still holding after the release): open fully next time (pilot 10-02: pads kept
        # touching a turned object at the pre-open + 1.5 cm, 20+ lower_open calls in a row)
        self._release_full = step == "lower_open" and getattr(self, "_last_step", None) == "lower_open"
        self._last_step = step
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
        q0 = self.plan_start()
        self._mark("step", step, [float(v) for v in pos], hold)
        width = None
        note = None
        if step == "above_target" and gc is not None:
            while gc is not None:
                r = self._guard_grasp(self._approach_plan(q0, gc, tg))
                if r["ok"]:
                    self.segs = r
                    break
                self.timeline.setdefault("fallback_trace", []).append({"family": gc.family, "status": r["status"]})
                gc, n2 = self.next_fallback(gc) if len(self.timeline["fallback_trace"]) < MAX_FALLBACK else (None,
                    f"no plannable grasp after {MAX_FALLBACK} tries ({self.choice.meta.get('family')} first)")
                note = n2
                if gc is not None:
                    gc.meta["fallback_from"] = self.choice.meta.get("family")
                    self.choice = gc
            if gc is None:
                self.dead = True  # no grasp is plannable: the next label ends the episode (no 30-call loop)
                return None, note, None
            width = gc.pre_open
            self.timeline.update(open_set_at="standoff", pre_open_w=round(gc.pre_open, 4))
            return self._resample(self.segs["approach"]), note, width
        if step == "descend_close" and gc is not None:
            Q = self.segs.get("grasp")
            if Q is None or np.abs(Q[0] - q0).max() > 0.08:
                r = self._guard_grasp(self._approach_plan(q0, gc, tg))
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
            c_obj = np.asarray(self.w.env.object_pose(tg)[0], float)
            low = step in ("carry_up", "lower_open", None) or pos[2] < c_obj[2] + 0.05
            # placing next to / between objects (relations): neighbours at 0.8 of their box, else the attached
            # object's spheres + padding + activation distance made every put pose a collision (pilot 10-02)
            near = {k: 0.8 for k in self.w.env.present if k != tg} if step == "lower_open" else None
            self.refresh_world(holding=tg, below_z=min(c_obj[2], pos[2]) if low else None, shrink=near)
        else:
            self.refresh_world(exclude=(tg,) if step in ("retreat",) else ())
        Q0 = None
        if step == "carry_up" and self.segs.get("lift") is not None and np.abs(self.segs["lift"][0] - q0).max() < 0.08:
            Q0 = self.segs["lift"]
            self.segs["lift"] = None
            q0 = Q0[-1]
        if step == "retreat" or (step == "carry_up" and Q0 is None):  # straight out / up: a planned curve swept
            Q = self._guard(self.planner.line(q0, self.to_base(self.tcp_T()), self.to_base(T)))  # the open fingers
            if Q is not None:                                                                # through the object
                self.timeline.setdefault("line_moves", []).append(step)  # carry_up: the curve also turned the
                # wrist 25-60 deg with the object in the hand (L9v2-DIAG note)
        else:
            Q = None
        if Q is None:
            Q = self._guard(self.planner.pose(q0, self.to_base(T)))
        if Q is None and hold:  # pilot 10-02: carry_over failed in 7 of 40 episodes with the object attached
            c_obj = np.asarray(self.w.env.object_pose(tg)[0], float)
            for k, (att, bz) in enumerate(((True, min(c_obj[2], pos[2])), (False, None))):
                self.refresh_world(holding=tg if att else None, below_z=bz, exclude=() if att else (tg,))
                Q = self._guard(self.planner.pose(q0, self.to_base(T)))
                if Q is not None:
                    self.timeline.setdefault("carry_fallback", []).append([step, k])
                    break
        if Q is None and Q0 is None and step in ("lower_open", "retreat", "lift_clear", "carry_up", "carry_over",
                                                  "reopen", None):
            Q = self._guard(self.planner.line(q0, self.to_base(self.tcp_T()), self.to_base(T)))  # short straight moves
            if Q is not None:
                self.timeline.setdefault("line_moves", []).append(step)
        if Q is None and step == "retreat":
            self._retreat_fail = getattr(self, "_retreat_fail", 0) + 1
        if Q is None:
            if Q0 is not None:
                return self._resample(Q0), "lifted a little; the carry path is blocked", None
            if hold:  # L9v2-DIAG 7: the next call chooses the place yaw again
                self.timeline["held_move_failed"] = self.timeline.get("held_move_failed", 0) + 1
            if step == "lift_clear":
                self._lift_clear_failed = getattr(self, "_lift_clear_failed", 0) + 1
            self._dump_fail(step or "move", q0, T)  # L9v2-DIAG 9: carry_up / lift_clear / reopen dumps (R1 Pro)
            return None, "no collision-free path to the target", None
        if Q0 is not None:
            Q = np.concatenate([Q0, Q])
        return self._resample(Q), note, width

    def _approach_plan(self, q0, gc, tg, extra_boxes: dict | None = None) -> dict:
        """Transit to the pre-grasp with EVERY link checked against the full target box (plan_grasp frees the
        gripper links for its whole first leg: the open fingers swept through the target and knocked it over in the
        pilot), then straight lines pre-grasp -> grasp -> lift (IK per waypoint, the target is touched there by
        design). extra_boxes: see Runtime.refresh_world (L9 bimanual, opt-in, default None = unchanged).
        -> {ok, status, approach, grasp, lift}."""
        self.refresh_world(below_z=self._bottom_z(tg) - 0.02, extra_boxes=extra_boxes)  # not the support: padded +
        T_pre = gc.T.copy()                             # activation distance it collided with fingertips 4 mm above
        T_pre[:3, 3] = gc.pre                            # it (pilot)
        Qa = self.planner.pose(q0, self.to_base(T_pre))
        if Qa is None and not on(REVERSE_APPROACH, self.profile):
            self._dump_fail("transit", q0, T_pre)
            return {"ok": False, "status": "transit to the pre-grasp failed", "approach": None, "grasp": None,
                    "lift": None}
        self.refresh_world(exclude=(tg,), below_z=self._bottom_z(tg) - 0.02, extra_boxes=extra_boxes)
        Qg = None if Qa is None else self.planner.line(Qa[-1], self.to_base(T_pre), self.to_base(gc.T), 0.008)
        # the straight approach touches the target by design only
        if Qg is None and on(REVERSE_APPROACH, self.profile):
            # L9v2-R1: walk the straight approach back from a grasp-pose IK branch, then a joint-space transit to
            # its pre-grasp end with the target as a full obstacle (same worlds as the forward path)
            Qr = self.planner.reverse_approach(self.to_base(gc.T), self.to_base(T_pre), 0.008)
            if Qr is not None:
                self.refresh_world(below_z=self._bottom_z(tg) - 0.02, extra_boxes=extra_boxes)
                Qc = self.planner.cspace(q0, Qr[0])
                if Qc is not None:
                    Qa, Qg = Qc, Qr
                    self.timeline["reverse_approach"] = self.timeline.get("reverse_approach", 0) + 1
                self.refresh_world(exclude=(tg,), below_z=self._bottom_z(tg) - 0.02, extra_boxes=extra_boxes)
        if Qa is None:
            self._dump_fail("transit", q0, T_pre)
            return {"ok": False, "status": "transit to the pre-grasp failed", "approach": None, "grasp": None,
                    "lift": None}
        if Qg is None:
            return {"ok": False, "status": "straight approach failed", "approach": None, "grasp": None, "lift": None}
        T_l = gc.T.copy()
        T_l[2, 3] += gc.lift_dz
        Ql = self.planner.line(Qg[-1], self.to_base(gc.T), self.to_base(T_l), 0.008)
        return {"ok": True, "status": "ok", "approach": Qa, "grasp": Qg, "lift": Ql}

    def ready_path(self, pos, quat):
        """L9 common executor (audit 8 + 11): the start of every robot = the largest joint-margin IK branch of its
        ready TCP (pos / quat in the world frame), reached by a collision-checked joint-space plan from the reset
        joints during the preroll (no Cartesian chase of another robot's start TCP). -> (Q resampled or None, margin
        rad or None); None = keep the old preroll."""
        self.refresh_world()
        r = self.planner.ready_ik(self.to_base(T_of(pos, quat)))
        if r is None:
            return None, None
        qr, margin = np.asarray(r[0], float), float(r[1])
        q0 = np.clip(self.arm_q(), self.q_lo + 0.03, self.q_hi - 0.03)
        if np.abs(qr - q0).max() < 1e-3:
            return qr[None].copy(), margin
        Q = self._guard(self.planner.cspace(q0, qr))
        return (None if Q is None else self._resample(Q)), margin

    def _mark(self, *a) -> None:
        """Diagnosis call log marker (L9V2_DEBUG_DIR only; the planner process writes it)."""
        if os.environ.get("L9V2_DEBUG_DIR") and hasattr(self.planner, "mark"):
            try:
                self.planner.mark(*a)
            except Exception:  # noqa: BLE001
                pass

    def _bottom_z(self, k: str) -> float:
        from ..sim.scene import OBJ_GEOM
        c, _ = self.w.env.object_pose(k)
        return float(c[2]) - float(OBJ_GEOM[k]["half_extents"][2])

    def _retreat_from(self, k: str, gc, st: dict):
        """('retreat', cmd) back along the previous grasp's approach (+ up), as v2plan.plan does for the last target,
        while the hand is still within the retreat zone of object k; None once clear (L9v2-DIAG 3)."""
        from ..astra_motion.harness import obj_height
        from ..teach_l8 import labels as L
        tcp = np.asarray(st["tcp"], float)
        c = np.asarray(self.w.env.object_pose(k)[0], float)
        if float(np.linalg.norm(tcp[:2] - c[:2])) >= L.RETREAT_XY + 0.03 or \
                tcp[2] >= c[2] + obj_height(k) / 2 + L.RETREAT_ABOVE:
            return None
        q = np.asarray(self.w.pl.tcp_pose()[1], float)
        away = tcp - VP.retreat_axis(gc, q) * gc.retreat
        tgt = np.array([away[0], away[1], max(away[2], tcp[2]) + 0.04])
        return "retreat", {"mode": "eef", "position_m": [round(float(v), 4) for v in tgt], "gripper": "keep",
                           "quat_wxyz": [round(float(v), 5) for v in q]}

    def _dump_fail(self, what: str, q0, T_world) -> None:
        """L9V2_DEBUG_DIR: the scene, start joints and goal of a failed plan (<= 6 per process) for
        tools/l9/v2_collide_dbg.py."""
        dbg = os.environ.get("L9V2_DEBUG_DIR")
        self._n_dump = getattr(self, "_n_dump", 0)
        if not dbg or self._n_dump >= 2:
            return
        import json
        self._n_dump += 1
        os.makedirs(dbg, exist_ok=True)
        fs = getattr(self.w, "scene9", {}) or {}
        parts = [p for p in fs.get("furniture", []) if "size" in p and "pos" in p]
        scene = P9.scene_cuboids(parts, self.obstacle_boxes(), self.T_world_base(), pad=0.005)
        json.dump({"what": what, "scene": scene, "q": np.asarray(q0).tolist(), "joints": self.joints,
                   "T_world_base": self.T_world_base().tolist(), "tcp_T": np.asarray(T_world).tolist(),
                   "goal_is_tcp_T": True}, open(os.path.join(dbg, f"fail_{os.getpid()}_{getattr(self.w, 'vseed', 0)}_{self._n_dump}.json"), "w"))

    def _guard(self, Q):
        """Reject a plan that leaves the SIM joint range (cuRobo's URDF limits may be wider: smoke 10-02, joint2 at
        -3.17 vs the sim's -3.14 pinned the arm and the wrist jumped 0.25 rad)."""
        if Q is None:
            return None
        Q = np.asarray(Q, float)
        if (Q < self.q_lo).any() or (Q > self.q_hi).any():
            self.timeline["limit_rejects"] = self.timeline.get("limit_rejects", 0) + 1
            return None
        return Q

    def _guard_grasp(self, r: dict) -> dict:
        if r.get("ok") and any(self._guard(r[k]) is None for k in ("approach", "grasp", "lift") if r.get(k) is not None):
            return dict(r, ok=False, status="plan leaves the sim joint range")
        return r

    def _resample(self, Q, slow: float = 1.0) -> np.ndarray:
        s = self.style or {}
        kind = s.get("profile", "minjerk")
        v = float(s.get("v_avg", 0.09) or 0.09)
        return P9.resample(Q, dq_max=cmd_dq(self.profile), kind=kind if kind in P9.PEAK else "minjerk",
                           split=float(s.get("split", 0.7)), slow=slow * max(1.0, 0.09 / v))

    # ------------------------------------------------------------------ gripper events
    def on_grip_cmd(self, action: str, t: float) -> None:
        self.timeline.setdefault("t_close_cmd" if action == "close" else "t_open_cmd", round(t, 3))

    def on_grip_done(self, action: str, t: float, ws: list):
        gc = self.choice
        if action != "close" or gc is None:
            return None
        gap = float(ws[-1][1]) if ws else float(self.w.status()["grip_w"])
        out = classify_close(gap, gc.w)
        tg = (self.choice_key or (None,))[0]
        gap_c = gap  # the reading compared with the contact width
        if self.gtab is not None:
            # grip layer (every robot, 2- or N-finger): EMPTY from the MEASURED free gap vs the measured closed gap
            # (or no fingertip on the target); CONTACT / WIDE from the TCP-plane gap vs the contact width
            env = self.w.env
            gap_c = float(env.gripper_tcp_gap())
            touched = self.w.status().get("gripper_contacts")
            if tg not in getattr(env, "contact", {}):  # no sensor on the target: the gaps alone decide
                touched = None
            out = H.close_verdict(gap, gc.w, self.gtab.closed_gap, touched=touched, target=tg, gap_tcp=gap_c)
            self.timeline["close_judge"] = "grip_layer"
        elif self.profile == "g1":
            # the Dex3-1 width read from index_0 is 2-4 cm under the true gap (GTEST 10-02): no width verdict; the
            # finger contacts decide (no contact data: CONTACT, the micro-lift and the truth holding state decide)
            tg = (self.choice_key or (None,))[0]
            touched = self.w.status().get("gripper_contacts")
            out = "CONTACT" if touched is None or tg in touched else "EMPTY"
            self.timeline["close_judge"] = "contacts"
        self.timeline.update(t_settle=round(t, 3), final_gap=round(gap, 4), outcome_close=out, close_cmd_w=0.0)
        if H.diag():  # A/B counting (L9_GRIP_DIAG=1, both arms): the pinch truth next to the verdict
            ff = self.w.env.finger_forces(tg) if tg is not None and hasattr(self.w.env, "finger_forces") else None
            tb = self.gtab or H.table_for(self.profile, self.arm)
            self.timeline.setdefault("close_truth", []).append(
                {"verdict": out, "gap": round(gap, 4), "gap_c": round(gap_c, 4), "w": round(float(gc.w), 4),
                 "pinched": None if ff is None or tb is None else H.pinched(ff, tb),
                 "touched": tg in (self.w.status().get("gripper_contacts") or ())})
        if out == "CONTACT" or (out == "WIDE" and gap_c < gc.w + WIDE_KEEP):
            # WIDE with a plausible gap: the natural deep grasps often close on a wider section than the planned
            # contacts (pilot 10-02: 13 of 40 picks); the micro-lift (SLIP / SUCCESS) and the truth holding state decide
            self._gap_before = gap
            extra = "" if out == "CONTACT" else ", wider than planned"
            return f"gripper closed on the object (gap {gap * 100:.1f} cm{extra})"
        tcp = np.asarray(self.w.status()["tcp"], float)
        if float(np.linalg.norm(tcp - gc.pos)) > 0.02:  # closed away from the grasp pose (behaviour perturbation /
            self.timeline["close_off_pose"] = self.timeline.get("close_off_pose", 0) + 1  # blocked move): not a
            return f"gripper closed away from the grasp (gap {gap * 100:.1f} cm)"  # verdict on the candidate
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
            style=None, runtime_cls: type = Runtime) -> Runtime:
    """runtime_cls (default Runtime, unchanged behaviour): a Runtime subclass to install instead -- the opt-in
    no-cache live executor (harvest.l9.rtlive9.LiveRuntime, harvest.l9.run9 --live-exec) reuses every hook below
    unchanged and only swaps this one class out."""
    global CURRENT
    rt = runtime_cls(world, profile, arm, device=device, allow_untested=allow_untested, style=style)
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


def has_candidates(profile: str, k: str, untested: bool = False, min_pass: int | None = None) -> bool:
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
    K = int(np.load(os.path.join(GRASP_DIR, g, f"{k}.npz"))["w"].shape[0])
    mp = int(os.environ.get("L9V2_MIN_PASS", "15")) if min_pass is None else min_pass  # few valid -> SkipScene often
    return int(tested_mask(dict(np.load(t)), K).sum()) >= mp


def tested_mask(r: dict, K: int) -> np.ndarray:
    """Per-candidate pass mask (K) from a tested npz: 'pass' of length K (grasp_test >= v2), or 'pass'/'shake_ok' of
    the tested subset scattered by 'idx'; untested candidates are not valid."""
    key = os.environ.get("L9V2_PASS_KEY", "pass_shake")  # catalog friction = the sim friction; mu 0.4 = stress test
    p = np.asarray(r.get(key, r.get("pass", r.get("shake_ok", np.zeros(0)))), bool)
    if key == "pass_shake" and key not in r and "shake_ok" in r and "idx" in r and len(r["shake_ok"]) == len(r["idx"]):
        p = np.asarray(r["shake_ok"], bool)  # older chunks: the tested subset by idx
    if len(p) == K:
        return p
    out = np.zeros(K, bool)
    idx = np.asarray(r.get("idx", np.zeros(0)), int)
    if len(idx) == len(p) and len(idx):
        out[idx[idx < K]] = p[idx < K]
    return out


def draws_standoff(seed: int, k: int) -> float:
    return VP.draws(seed, k)["standoff"]
