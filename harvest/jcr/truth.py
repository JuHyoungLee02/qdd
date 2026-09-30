"""JCR sim-truth labels (docs/stage3/jcr_design.md §4, §0-2). Pure numpy; computed from privileged sim state only --
never from a learned policy -- so it relabels ANY state, including JCR's own rollouts (NOW.md §1-0d).

One rule for both jobs of the joystick (follow + fine correction inside the envelope):
  c* = the true task point (what a noise-free command would resolve to, moved with the target object since the command)
       projected onto the envelope ball of radius r around the commanded goal. Outside the ball: follow to the
       boundary and flag cmd_mismatch (never ignore the command -- the commander keeps authority).
Arm label = a smooth TCP chunk (H rows at 20 Hz) from the current commanded TCP to c*, speed <= V_MAX, acceleration
<= A_MAX, discrete-time braking so it arrives without overshoot; IK (joint step <= 0.04 rad/tick) is the world's.
stop=True (unrecoverable state): decelerate to rest at A_MAX, then hold."""
from __future__ import annotations

import numpy as np

H = 10  # rows per chunk (0.5 s)
DT = 0.05  # s, 20 Hz control tick (world.dt)
V_MAX = 0.08  # m/s = the scripted executor's average speed (astra_motion.executor.V_TCP)
A_MAX = 0.32  # m/s^2 = astra_motion.executor.A_MAX
R_GOAL = 0.03  # m, envelope ball around the commanded goal
REACH_M = 0.008  # = astra_motion.executor.REACH_TOL_M
MOVED_M = 0.02  # target displaced this far since the command while not held -> target_moved
DROP_Z = 0.05  # target this far below the table top -> off the table (= harness.Monitor off_table)
ANOMALIES = ("unexpected_contact", "target_moved", "dropped", "cmd_mismatch", "unrecoverable")


def project_ball(p_true, goal, r: float = R_GOAL):
    """-> (c*, mismatch). c* = p_true if within r of goal, else the ball point nearest to it."""
    p, g = np.asarray(p_true, float), np.asarray(goal, float)
    d = p - g
    n = float(np.linalg.norm(d))
    if n <= r + 1e-12:
        return p.copy(), False
    return g + d * (r / n), True


MODES = ("A", "B", "C")  # A hard envelope, B pull only, C pull + hard envelope (user 10-01, NOW.md §1-0e)
RHO_STRONG, RHO_WEAK = 0.02, 0.07  # B / C: correction scale at pull strength kappa = 1 / 0


def pull_weight(dist: float, kappa: float) -> float:
    """Share of the discrepancy d = p_true - goal the JCR corrects: ~1 for |d| << rho, ~0 for |d| >> rho, rho shrinking
    with the pull strength kappa (strong near grasp / place, weak while carrying)."""
    k = min(max(float(kappa), 0.0), 1.0)
    rho = RHO_STRONG * k + RHO_WEAK * (1.0 - k)
    return 1.0 / (1.0 + (float(dist) / rho) ** 4)


def target_point(mode: str, p_true, goal, kappa: float = 1.0, r: float = R_GOAL):
    """-> (c*, mismatch). A: project_ball(p_true, goal, r). B: goal + w * d (w = pull_weight), no hard wall; mismatch
    when the pull keeps less than half of the correction (w < 0.5). C: the B point projected onto the r ball."""
    p, g = np.asarray(p_true, float), np.asarray(goal, float)
    if mode == "A":
        return project_ball(p, g, r)
    d = p - g
    n = float(np.linalg.norm(d))
    w = pull_weight(n, kappa)
    c = g + w * d
    mis = w < 0.5 and n > 1e-9
    if mode == "C":
        c, hit = project_ball(c, g, r)
        mis = mis or hit
    return c, mis


def _v_brake(dist: float) -> float:
    """Largest speed from which discrete braking at A_MAX (speed drops A_MAX*DT per tick) stops within dist."""
    u = A_MAX * DT * DT
    # n = fewest ticks whose braking staircase (speeds n, n-1, ..., 1 x A_MAX*DT) covers dist; this tick takes the
    # part of dist the staircase after it (n-1 ... 1) does not cover
    n = int(np.ceil((np.sqrt(1.0 + 8.0 * dist / u) - 1.0) / 2.0 - 1e-12))
    return max(dist - u * n * (n - 1) / 2.0, 0.0) / DT


def step(p, v, c, stop: bool = False):
    """One 20 Hz tick of the truth motion -> (p_next, v_next)."""
    p, v, c = np.asarray(p, float), np.asarray(v, float), np.asarray(c, float)
    if stop:
        s = float(np.linalg.norm(v))
        if s <= A_MAX * DT + 1e-12:
            return p.copy(), np.zeros(3)
        v2 = v * (s - A_MAX * DT) / s
        return p + v2 * DT, v2
    d = c - p
    dist = float(np.linalg.norm(d))
    if dist < 1e-9:
        return c.copy(), np.zeros(3)
    v_des = min(V_MAX, _v_brake(dist), dist / DT) * d / dist
    dv = v_des - v
    n = float(np.linalg.norm(dv))
    if n > A_MAX * DT:
        dv = dv * (A_MAX * DT / n)
    v2 = v + dv
    s = v2 * DT
    if float(np.linalg.norm(s)) >= dist or float(np.dot(c - (p + s), d)) <= 0.0:
        return c.copy(), np.zeros(3)
    return p + s, v2


def smooth_chunk(p_cmd, v_prev, c, H: int = H, stop: bool = False):
    """-> (P [H, 3] commanded TCP rows for the next H ticks, velocity after row 0)."""
    p, v = np.asarray(p_cmd, float), np.asarray(v_prev, float)
    rows, v0 = [], None
    for k in range(H):
        p, v = step(p, v, c, stop)
        rows.append(p)
        if k == 0:
            v0 = v
    return np.array(rows), v0


def grip_event(allow, tcp, c, reach: float = REACH_M) -> str:
    """keep | close | open: the commander-allowed gripper action, at arrival at c* only."""
    if allow in ("close", "open") and float(np.linalg.norm(np.asarray(tcp, float) - np.asarray(c, float))) < reach:
        return allow
    return "keep"


PAD_EMPTY_M = 0.003  # pads within this of the closed width = nothing between them


def anomaly_kinds(touched, tgt: str, holding: bool, was_holding: bool, grip_cmd_closed: bool, tgt_shift_m: float,
                  mismatch: bool, tgt_z: float, table_z: float, upright: bool, pads_empty: bool = False) -> set:
    """Anomaly kinds true at this tick (privileged). dropped = the object was held since the last close, the gripper
    is still commanded closed and the pads have closed on nothing (pads_empty; the holding predicate alone flickers
    while carrying -- smoke d0 dr s20000). unrecoverable = physically evident (off the table, tipped and not held);
    the counterfactual-rollout definition (§0-2, N >= 3) is a stage-2 part."""
    out = set()
    if set(touched) - {tgt}:
        out.add("unexpected_contact")
    if was_holding and grip_cmd_closed and pads_empty and not holding:
        out.add("dropped")
    if not holding and tgt_shift_m > MOVED_M:
        out.add("target_moved")
    if mismatch:
        out.add("cmd_mismatch")
    if tgt_z < table_z - DROP_Z or (not upright and not holding):
        out.add("unrecoverable")
    return out
