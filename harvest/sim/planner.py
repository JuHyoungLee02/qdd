"""Oracle scripted planner, DEV perturbations and success predicate (E §1.4).

Pure parts (no Isaac): success_from_history, next_phase (FSM), oracle_answer, decision_points.
OraclePlanner / run_episode use Isaac Lab (DifferentialIKController) and import it lazily (pod only).

FSM (plan T12): approach (TCP 10 cm above the mug top) -> descend -> close -> lift (mug bottom >= h_lift, up to
the carry height) -> carry (over the tray) -> place_descend (until contact_under = in_contact(o3,o5), or the
mug bottom is 3 mm above the tray) -> open -> retreat -> done. Any phase can end in "fail"; FAIL_STAGE maps it
to the reporting stage (approach IK / grasp / lift / carry / place / release).
"""
from __future__ import annotations

import math

import numpy as np

from ..config import CFG

SUCCESS_KEYS = ("on(o3,o5)", "holding(o3)", "upright(o3)")


def _success_now(p: dict) -> bool:
    return p.get("on(o3,o5)") is True and p.get("holding(o3)") is False and p.get("upright(o3)") is True


def success_from_history(hist) -> bool:
    """hist: [(sim_time, predicates)] ascending. True iff the success predicate holds ≥ success_hold_s continuously.
    unknown (None) never counts as satisfied."""
    start = None
    for t, p in hist:
        if _success_now(p):
            start = t if start is None else start
            if t - start >= CFG.success_hold_s - 1e-9:
                return True
        else:
            start = None
    return False


# ---------------------------------------------------------------------------------------------- FSM (pure)
PHASES = ("approach", "descend", "close", "lift", "carry", "place_descend", "open", "retreat", "done")
PHASE_TIMEOUT_S = {"approach": 8.0, "descend": 5.0, "close": 1.5, "lift": 4.0, "carry": 6.0,
                   "place_descend": 5.0, "open": 1.5, "retreat": 3.0}
FAIL_STAGE = {"approach": "approach_ik", "descend": "approach_ik", "close": "grasp", "lift": "lift",
              "carry": "carry", "place_descend": "place", "open": "release", "retreat": "release"}
CLOSE_WAIT_S = 0.6
OPEN_WAIT_S = 0.5


def next_phase(phase: str, s: dict) -> str:
    """s: reached (TCP at the phase goal), t_in_phase, holding (holding(o3)), lift_h (mug bottom above the table,
    m), contact_under (in_contact(o3,o5))."""
    if phase in ("done", "fail"):
        return phase
    if s["t_in_phase"] > PHASE_TIMEOUT_S[phase]:
        return "fail"
    if phase == "approach":
        return "descend" if s["reached"] else phase
    if phase == "descend":
        return "close" if s["reached"] else phase
    if phase == "close":
        if s["t_in_phase"] < CLOSE_WAIT_S:
            return phase
        return "lift" if s["holding"] else "fail"
    if phase in ("lift", "carry", "place_descend") and not s["holding"]:
        return "fail"
    if phase == "lift":
        return "carry" if (s["reached"] and s["lift_h"] >= CFG.h_lift_m) else phase
    if phase == "carry":
        return "place_descend" if s["reached"] else phase
    if phase == "place_descend":
        return "open" if (s["contact_under"] or s["reached"]) else phase
    if phase == "open":
        return "retreat" if s["t_in_phase"] >= OPEN_WAIT_S else phase
    if phase == "retreat":
        return "done" if s["reached"] else phase
    raise ValueError(phase)


# ------------------------------------------------------------------------------------- oracle answers (pure)
MAG_BINS = (("tiny", 0.005), ("small", 0.01), ("medium", 0.02), ("large", 0.04), ("xlarge", 0.08))  # jevcall.MAG
DIR_EPS_M = 0.0025  # below half of the smallest bin a component counts as "no motion"
GRIP_EPS_M = 0.005
_XY8 = ["plus_x", "plus_x_plus_y", "plus_y", "minus_x_plus_y", "minus_x", "minus_x_minus_y", "minus_y",
        "plus_x_minus_y"]


def oracle_answer(p_now, p_next, w_now: float, w_next: float) -> dict:
    """The planner's own motion over one decision step as D-zoom answers (M3 §4.2 option keys)."""
    d = np.asarray(p_next, float) - np.asarray(p_now, float)
    h = math.hypot(d[0], d[1])
    if h < DIR_EPS_M:
        dxy = "none_xy"
    else:
        dxy = _XY8[int(round(math.atan2(d[1], d[0]) / (math.pi / 4))) % 8]
    dz = "none_z" if abs(d[2]) < DIR_EPS_M else ("up" if d[2] > 0 else "down")
    n = float(np.linalg.norm(d))
    logs = [abs(math.log(max(n, 1e-6)) - math.log(v)) for _, v in MAG_BINS]
    mag = MAG_BINS[int(np.argmin(logs))][0] if n >= DIR_EPS_M else "tiny"
    grip = "close" if w_next < w_now - GRIP_EPS_M else ("open" if w_next > w_now + GRIP_EPS_M else "keep")
    return {"dir_xy": dxy, "dir_z": dz, "mag_coarse": mag, "grip": grip}


def decision_points(planner_or_history, T_c: float = CFG.T_c):
    """[(t, ds_id, oracle_answer)] every T_c from the planner's command history [(t, cmd_pos, cmd_w, phase)]:
    the answer is the planner's commanded TCP motion over [t, t + T_c] (table frame) and the gripper change."""
    hist = getattr(planner_or_history, "history", planner_or_history)
    if not hist:
        return []
    ts = np.array([h[0] for h in hist])
    P = np.array([np.asarray(h[1], float) for h in hist])

    def pos(t):
        return np.array([np.interp(t, ts, P[:, i]) for i in range(3)])

    def last(t, i):
        j = int(np.searchsorted(ts, t + 1e-9, side="right")) - 1
        return hist[max(j, 0)][i]

    out, k = [], 0
    while True:
        t = ts[0] + k * T_c
        if t + T_c > ts[-1] + 1e-9:
            break
        a = oracle_answer(pos(t), pos(t + T_c), last(t, 2), last(t + T_c, 2))
        a["phase"] = last(t, 3)
        out.append((t, f"ds{k}", a))
        k += 1
    return out


# ------------------------------------------------------------------------------------------ Isaac (pod only)
GRASP_BELOW_TOP_M = 0.018  # pad centre 1.8 cm below the mug top: the gripper body sits ~23 mm above the pad
# centre (measured: descend stalled at 22.8 mm with 35 mm), so deeper grasps hit the rim; pads cover the top 45 mm
APPROACH_ABOVE_TOP_M = 0.10  # "머그 위 10 cm"
CARRY_TCP_Z = 0.20  # table frame; mug bottom ~0.12 m, above every distractor (tallest 0.10 m)
PLACE_CLEAR_M = 0.003
V_FAST, V_SLOW = 0.20, 0.06  # m/s TCP command speed
V_LIFT = 0.08  # slower lift: the top-rim grasp slips when jerked (P0 seed 24, P1 lift failures)
W_MAX = 1.5  # rad/s orientation command rate
REACH_TOL_M = 0.006  # descend / place
REACH_TOL_FAST_M = 0.015  # approach / lift / carry / retreat
GRIP_SQUEEZE_M = 0.014  # v1 0.012. v2 (copied gains: master 100, slaves 2) sweep on DEV 0-29 (CPU physics), P0 / P1
# successes: 0.004 11/12, 0.012 29/27, 0.014 30/28, 0.016 30/28, 0.024 25/22 -- too little squeeze lets the weak
# slave finger open (grasp fail, width 80-86 mm), too much makes the mug slip out in carry/place (width ~70 mm)
MAX_DQ_RAD = 0.04  # per 50 ms env step (0.8 rad/s); seed-2 lift without it threw the TCP 0.3 m upward
HOLD_DEBOUNCE = 3  # env steps of holding == False before the FSM sees it
TOP_DOWN_YAW = math.pi / 2  # link7 z up, fingers close along world x. IK study (seed 0 scene, 9 targets
# x 0.36-0.48 / y -0.40..-0.06 at 16 cm): yaw pi/2 reached 9/9 (<= 1.9 mm, 1.1 deg); yaw 0 hit joint limits at
# y = -0.06 (220 mm error, 7/9 ok); yaw -pi/2 2/9 ok; yaw pi 4/9 ok.


def _quat_mul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return np.array([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2])


def _quat_rot(q, v):
    w, x, y, z = q
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                  [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                  [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])
    return R @ np.asarray(v, float)


def _slerp_step(q0, q1, max_angle):
    q0, q1 = np.asarray(q0, float), np.asarray(q1, float)
    d = float(np.dot(q0, q1))
    if d < 0:
        q1, d = -q1, -d
    ang = 2 * math.acos(min(1.0, d))
    if ang <= max_angle or ang < 1e-6:
        return q1
    f = max_angle / ang
    th = math.acos(min(1.0, d))
    q = (math.sin((1 - f) * th) * q0 + math.sin(f * th) * q1) / math.sin(th)
    return q / np.linalg.norm(q)


class OraclePlanner:
    """Scripted top-down pick-and-place on oracle state; step() -> 8-D target (7 arm joints + gripper width)."""

    def __init__(self, env):
        import torch
        from isaaclab.controllers import DifferentialIKController, DifferentialIKControllerCfg

        from ..predicates import PredicateState
        from .scene import GRIP_MAX_W, OBJ_GEOM

        self.env, self.torch = env, torch
        self.ik = DifferentialIKController(
            DifferentialIKControllerCfg(command_type="pose", use_relative_mode=False, ik_method="dls",
                                        ik_params={"lambda_val": 0.05}), num_envs=1, device=env.env.device)
        self.mug_h = OBJ_GEOM["o3"]["height"]
        self.tray_h = OBJ_GEOM["o5"]["size"][2]
        self.w_open = GRIP_MAX_W
        # squeeze target: mug diameter minus GRIP_SQUEEZE_M (PD then presses with ~stiffness x error, not the
        # effort limit; full-close targets drove the fingers 14 mm into the mug and PhysX threw the arm)
        self.w_close = max(0.0, 2 * OBJ_GEOM["o3"]["radius"] - GRIP_SQUEEZE_M)
        self.ps = PredicateState()
        self.phase, self.t_phase0 = "approach", env.sim_time
        p, q = self.tcp_pose()
        self.cmd_pos, self.cmd_quat, self.cmd_w = p, q, GRIP_MAX_W
        self.goal_quat = np.array([math.cos(TOP_DOWN_YAW / 2), 0, 0, math.sin(TOP_DOWN_YAW / 2)])
        self.history = []  # (t, cmd_pos table frame, cmd_w, phase)
        self.phase_log = [(env.sim_time, "approach")]
        self.pred, self.objs, self.grip = {}, {}, None
        self._not_hold = 0
        self.fail_stage, self.fail_info = None, {}
        self.retreat_z = None
        self.near_target = False
        self.grasp_rel = None  # mug centre - TCP at the end of close

    # ---- geometry
    def tcp_pose(self):
        p, q = self.env.ee_pose()
        return p + _quat_rot(q, (0, 0, -self.env.tcp_offset)), q

    def _mug(self):
        return self.env.object_pose("o3")[0]

    def _goal(self):
        z0 = self.env.table_top_z
        mug = self._mug()
        tray = self.env.object_pose("o5")[0]
        ph = self.phase
        if ph == "approach":
            return np.array([mug[0], mug[1], z0 + self.mug_h + APPROACH_ABOVE_TOP_M]), V_FAST
        if ph == "descend":
            return np.array([mug[0], mug[1], z0 + self.mug_h - GRASP_BELOW_TOP_M]), V_SLOW
        if ph in ("close", "open", "done"):
            return self.cmd_pos.copy(), V_SLOW
        if ph == "lift":
            return np.array([self.cmd_pos[0], self.cmd_pos[1], z0 + CARRY_TCP_Z]), V_LIFT
        if ph == "carry":
            return np.array([tray[0], tray[1], z0 + CARRY_TCP_Z]), V_FAST
        if ph == "place_descend":
            tcp, _ = self.tcp_pose()
            mug_bottom = mug[2] - self.mug_h / 2
            tray_top = tray[2] + self.tray_h / 2
            return np.array([tray[0], tray[1], tcp[2] - (mug_bottom - tray_top) + PLACE_CLEAR_M]), V_SLOW
        if ph == "retreat":
            return np.array([self.cmd_pos[0], self.cmd_pos[1], self.retreat_z]), V_FAST
        raise ValueError(ph)

    # ---- one control step
    def observe(self):
        from .oracle_state import oracle_objects
        objs, grip, contacts, support = oracle_objects(self.env)
        self.pred = self.ps.update(objs, grip, contacts, support)
        self.objs, self.grip, self.contacts = objs, grip, contacts
        self.near_target = bool(np.linalg.norm(grip.pos - objs["o3"].pos) < CFG.near_in_m)
        return self.pred

    def step(self) -> np.ndarray:
        env, t = self.env, self.env.sim_time
        if not self.pred:
            self.observe()
        p = self.pred
        hold_now = p.get("holding(o3)") is True
        self._not_hold = 0 if hold_now else self._not_hold + 1
        mug = self.objs["o3"]
        goal, _ = self._goal()
        tcp, _ = self.tcp_pose()
        tol = REACH_TOL_M if self.phase in ("descend", "place_descend") else REACH_TOL_FAST_M
        sig = dict(reached=bool(np.linalg.norm(goal - tcp) < tol and np.linalg.norm(goal - self.cmd_pos) < 1e-4),
                   t_in_phase=t - self.t_phase0, holding=self._not_hold < HOLD_DEBOUNCE,
                   lift_h=float(mug.pos[2] - mug.half_extents[2]), contact_under=p.get("in_contact(o3,o5)") is True)
        new = next_phase(self.phase, sig)
        if new != self.phase:
            if new == "fail":
                self._record_fail(sig, goal, tcp)
            else:
                if self.phase == "close":
                    self.grasp_rel = (self._mug() - tcp).tolist()
                if new == "retreat":
                    self.retreat_z = tcp[2] + 0.10
                if new == "carry":
                    env.carry_start_xy = self._mug()[:2].copy()
            self.phase, self.t_phase0 = new, t
            self.phase_log.append((t, new))
        # command
        if self.phase not in ("fail",):
            goal, v = self._goal()
            d = goal - self.cmd_pos
            n = float(np.linalg.norm(d))
            step = v * env.step_dt
            self.cmd_pos = goal if n <= step else self.cmd_pos + d * (step / n)
            self.cmd_quat = _slerp_step(self.cmd_quat, self.goal_quat, W_MAX * env.step_dt)
            if self.phase in ("close", "lift", "carry", "place_descend"):
                self.cmd_w = self.w_close
            elif self.phase in ("open", "retreat", "done", "approach", "descend"):
                self.cmd_w = self.w_open
        from .oracle_state import to_table_frame
        self.history.append((t, to_table_frame(self.cmd_pos, env.table_top_z), self.cmd_w, self.phase))
        q_des = self._ik(self.cmd_pos, self.cmd_quat)
        return np.concatenate([q_des, [self.cmd_w]]).astype(np.float32)

    def _ik(self, pos_w, quat_w):
        torch, env = self.torch, self.env
        r = env.robot
        dev = env.env.device
        jac = r.root_physx_view.get_jacobians()[:, env.ee_idx - 1, :, :][:, :, env.arm_ids].clone()  # fixed base
        ee_p, ee_q = r.data.body_pos_w[:, env.ee_idx], r.data.body_quat_w[:, env.ee_idx]
        off = torch.tensor([[0.0, 0.0, -env.tcp_offset]], device=dev)
        from isaaclab.utils.math import quat_apply, skew_symmetric_matrix
        r_off = quat_apply(ee_q, off)
        tcp_p = ee_p + r_off
        jac[:, 0:3, :] -= torch.bmm(skew_symmetric_matrix(r_off), jac[:, 3:6, :])
        cmd = torch.tensor([[*pos_w, *quat_w]], dtype=torch.float32, device=dev)
        self.ik.set_command(cmd)
        q = r.data.joint_pos[:, env.arm_ids]
        q_des = self.ik.compute(tcp_p, ee_q, jac, q)
        dq = (q_des - q).clamp(-MAX_DQ_RAD, MAX_DQ_RAD)  # no jumps: DLS near singular poses can ask for big steps
        return (q + dq + self._gravity_offset())[0].cpu().numpy()

    def _gravity_offset(self):
        """Static gravity sag of the PD arm, added to the joint target (v2 robot: links have gravity, arm stiffness
        600/600/200). At rest K (q_target - q) = gravity-compensation torque, so q_target = q_wanted + c / K.
        Without it the TCP sat 21-26 mm below the command and the approach swept the open fingers into the mug
        (v2 P0 seeds 0-2). Zero when the robot has no gravity (v1)."""
        r, ids = self.env.robot, self.env.arm_ids
        c = r.root_physx_view.get_gravity_compensation_forces()[:, ids]  # fixed base: (1, num_dofs)
        return c / r.data.joint_stiffness[:, ids]

    def _record_fail(self, sig, goal, tcp):
        ph = self.phase
        self.fail_stage = FAIL_STAGE.get(ph, "release")
        mug = self._mug()
        info = {"phase": ph, "t_in_phase": round(sig["t_in_phase"], 2),
                "tcp_goal_err_mm": round(float(np.linalg.norm(goal - tcp)) * 1e3, 1),
                "mug_tcp_xy_mm": round(float(np.linalg.norm((mug - tcp)[:2])) * 1e3, 1),
                "mug_tcp_z_mm": round(float((mug - tcp)[2]) * 1e3, 1),
                "width_mm": round(self.env.gripper_width() * 1e3, 1),
                "lift_h_mm": round(sig["lift_h"] * 1e3, 1), "holding": sig["holding"]}
        self.fail_info = info


def mug_tray_metrics(env) -> dict:
    from .scene import OBJ_GEOM
    from ..predicates import _tilt_deg
    m, mq = env.object_pose("o3")
    t, _ = env.object_pose("o5")
    he = OBJ_GEOM["o5"]["half_extents"]
    dx, dy = m[0] - t[0], m[1] - t[1]
    return {"mug_tray_xy_mm": round(math.hypot(dx, dy) * 1e3, 1),
            "mug_outside_tray_mm": round(max(abs(dx) - he[0], abs(dy) - he[1], 0.0) * 1e3, 1),
            "mug_tilt_deg": round(_tilt_deg(mq), 1),
            "mug_z_table_mm": round((m[2] - env.table_top_z) * 1e3, 1)}


def run_episode(env, kind: str = "P0", seed: int | None = None, limit_s: float = CFG.episode_limit_s,
                done_grace_s: float = 3.0, on_step=None) -> dict:
    """One episode: reset (one state write + settle), arm the DEV perturbation, run the oracle planner until
    success (1 s hold), failure, off-table drop or the 60 s limit."""
    import time

    from .perturb import apply_pending, perturb

    seed = env.seed if seed is None else seed
    env.reset()
    perturb(env, kind, seed)
    pl = OraclePlanner(env)
    hist, events = [], []
    res = {"seed": seed, "kind": kind, "success": False, "stage": None, "info": {}}
    t_wall = time.perf_counter()
    t_done = None
    while True:
        t = env.sim_time
        pred = pl.observe()
        hist.append((t, pred))
        if pl.objs["o3"].pos[2] < -0.05:
            res.update(stage=FAIL_STAGE.get(pl.phase, "release"), info={"reason": "off_table", "phase": pl.phase})
            break
        if success_from_history(hist):
            res["success"] = True
            break
        if pl.phase == "fail":
            res.update(stage=pl.fail_stage, info=pl.fail_info)
            break
        if pl.phase == "done":
            t_done = t if t_done is None else t_done
            if t - t_done > done_grace_s:
                res.update(stage="release", info={"reason": "no_success_after_done",
                                                  **{k: pred.get(k) for k in SUCCESS_KEYS}})
                break
        if t >= limit_s:
            res.update(stage=FAIL_STAGE.get(pl.phase, "release"), info={"reason": "time_limit", "phase": pl.phase})
            break
        q = pl.step()
        ev = apply_pending(env, t, pl.near_target, pl.phase)
        if ev:
            events.append(ev)
        env.step(q)
        if on_step:
            on_step(env, pl)
    res["sim_time_s"] = round(env.sim_time, 2)
    res["wall_s"] = round(time.perf_counter() - t_wall, 2)
    res["rtf"] = round(env.sim_time / max(res["wall_s"], 1e-6), 3)
    res["phases"] = [(round(a, 2), b) for a, b in pl.phase_log]
    res["events"] = events
    res["grasp_rel_mm"] = [round(v * 1e3, 1) for v in pl.grasp_rel] if pl.grasp_rel else None
    res.update(mug_tray_metrics(env))
    res["n_decision_points"] = len(decision_points(pl))
    randomization_meta(env, res)
    res["planner"] = pl
    return res


def randomization_meta(env, res: dict) -> None:
    """Episode metadata: the variant's sampled 5 axes (randomize.py) and, for random/dr, how far each tabletop
    distractor sat from its sampled pose after settling and moved during the episode (collision check)."""
    meta = getattr(env, "randomization", None)
    res["variant"] = getattr(env, "variant", "standard")
    res["randomization"] = meta
    if meta and meta.get("distractors") and getattr(env, "rand_settle", None) is not None:
        from .randomize import distractor_report
        res["rand_settle"] = env.rand_settle
        res["rand_moved"] = distractor_report(env, env.rand_settle_pos)
