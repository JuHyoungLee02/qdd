"""JCR sim-truth labels (docs/stage3/jcr_design.md §4, §0-2). Pure numpy; computed from privileged sim state only --
never from a learned policy -- so it relabels ANY state, including JCR's own rollouts (NOW.md §1-0d).

Labels (change 3): JCR learns 'P' = go to the true task point (its own intention); the code composes the executed motion
by the envelope rule (mode_chunk: A hard clip / B, C priority blend with the upper's attraction). Rule A below:
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


MODES = ("A", "B", "C")  # A hard clip, B priority blend (wide residual bound), C priority blend + 3 cm bound
# Priority blend (change 3, geometric-fabrics / Policy-Decorator style; NOW.md §1-0e): the code composes the executed
# motion u = (1 - w) u_JCR + w u_att, u_att = V_MAX tanh(ALPHA d) e_goal (attraction to the upper's destination),
# w(d) = w_min + (1 - w_min) exp(-(d / rho)^2) (shape 'gauss'; 'p4' = w_min + (1 - w_min) / (1 + (d / rho)^4), the
# old form, for the sweep), d = |x - goal|: far from the destination the attraction keeps at least w_min (the upper's
# authority never vanishes), near it the attraction dominates (the end point is the upper's destination unless JCR
# pushes). Residual bound (Policy Decorator): |x - x_att| <= A_eff, A_eff ramping from eps to A over t_ramp after the
# command. Deviation only when needed (IDA): w halved while an obstacle / contact / anomaly signal is on (lower=True).
# Stage (adapter kappa) moves w_min and rho: w_min * s, rho * (0.5 + 0.5 s), s = kappa / 0.9.
ALPHA = 1.0 / 0.02
V_BLEND = 0.12
PRIO = {"shape": "gauss", "rho": 0.03, "w_min": 0.2, "w_max": 0.7, "A": 0.10, "eps": 0.01,
        "t_ramp": 1.0}  # provisional (sweep)
# w_max (added, change 3 note): the literal w(0) = 1 makes the destination a fixed point where u = u_att = 0 and JCR can
# never correct there (checked: 0 mm correction for every rho x w_min); w(d) = w_min + (w_max - w_min) f(d / rho).
MODE_PRIO = {"B": PRIO, "C": dict(PRIO, A=0.03)}
KAPPA_REF = 0.9


def prio_w(d: float, shape: str, rho: float, w_min: float, w_max: float = 1.0) -> float:
    x = float(d) / max(float(rho), 1e-9)
    f = np.exp(-x * x) if shape == "gauss" else 1.0 / (1.0 + x ** 4)
    return float(w_min + (max(w_max, w_min) - w_min) * f)


def stage_prio(prm: dict, kappa: float):
    s = min(max(float(kappa) / KAPPA_REF, 0.0), 1.0)
    return prm["rho"] * (0.5 + 0.5 * s), prm["w_min"] * s


def u_att(x, g) -> np.ndarray:
    x = np.asarray(x, float)
    t = via_above(x, g) - x
    n = float(np.linalg.norm(t))
    return np.zeros(3) if n < 1e-12 else V_MAX * np.tanh(ALPHA * n) * t / n


def blend_rows(p0, v0, rows_jcr, goal, prm: dict, kappa: float = KAPPA_REF, age: float = 0.0,
               lower: bool = False) -> np.ndarray:
    """Executed TCP rows from JCR's rows (its own intended motion) and the attraction to the upper's destination."""
    g = np.asarray(goal, float)
    rho, w_min = stage_prio(prm, kappa)
    x = xa = np.asarray(p0, float)
    u_prev = ua_prev = np.asarray(v0, float)
    prev_j = x
    out = []
    for k, rj in enumerate(np.asarray(rows_jcr, float)):
        uj = (rj - prev_j) / DT
        prev_j = rj
        w = prio_w(np.linalg.norm(x - g), prm["shape"], rho, w_min, prm.get("w_max", 1.0)) * (0.5 if lower else 1.0)
        u = (1.0 - w) * uj + w * u_att(x, g)
        ua = u_att(xa, g)
        for vv, vp in ((u, u_prev), (ua, ua_prev)):  # acceleration / speed limits on both rollouts
            dv = vv - vp
            n = float(np.linalg.norm(dv))
            if n > A_MAX * DT:
                vv[:] = vp + dv * (A_MAX * DT / n)
            n = float(np.linalg.norm(vv))
            if n > V_BLEND:
                vv *= V_BLEND / n
        x, xa = x + DT * u, xa + DT * ua
        u_prev, ua_prev = u, ua
        a_eff = prm["eps"] + (prm["A"] - prm["eps"]) * min(1.0, (age + (k + 1) * DT) / max(prm["t_ramp"], 1e-9))
        r = x - xa
        n = float(np.linalg.norm(r))
        if n > a_eff:
            x = xa + r * (a_eff / n)
        out.append(x.copy())
    return np.array(out)


def mismatch(p_true, goal, r: float = R_GOAL) -> bool:
    return float(np.linalg.norm(np.asarray(p_true, float) - np.asarray(goal, float))) > r


def mode_chunk(mode: str, p_cmd, v, p_true, goal, kappa: float = KAPPA_REF, age: float = 0.0, stop: bool = False,
               lower: bool = False, prm: dict | None = None, r: float = R_GOAL) -> np.ndarray:
    """Executed truth rows of an envelope rule. 'P' = JCR's own label (straight to the true point), 'S' = scripted
    (to the command), 'A' = hard clip (project_ball r), 'B' / 'C' = priority blend of the P rows."""
    if mode == "P":
        return smooth_chunk(p_cmd, v, p_true, stop=stop)[0]
    if mode == "S":
        return smooth_chunk(p_cmd, v, goal, stop=stop)[0]
    if mode in ("A", "A1", "A2"):
        rr = {"A": r, "A1": 0.01, "A2": 0.02}[mode]
        return smooth_chunk(p_cmd, v, project_ball(p_true, goal, rr)[0], stop=stop)[0]
    if stop:
        return smooth_chunk(p_cmd, v, p_cmd, stop=True)[0]
    P = smooth_chunk(p_cmd, v, p_true)[0]
    return blend_rows(p_cmd, v, P, goal, prm or MODE_PRIO[mode], kappa, age, lower)


CLEAR_XY_M = 0.02  # lateral distance above which the truth path first goes over the target (no sideways sweep)
CLEAR_Z_M = 0.05


def via_above(p_cmd, c) -> np.ndarray:
    """The point the truth motion heads for now: c itself when within CLEAR_XY_M laterally, else c raised to at least
    CLEAR_Z_M above it (and never lower than the current commanded height) -- a low sideways move would sweep the
    object (smoke d1 dr s20100 knocked the mug over)."""
    p, c = np.asarray(p_cmd, float), np.asarray(c, float)
    if float(np.linalg.norm(c[:2] - p[:2])) <= CLEAR_XY_M:
        return c.copy()
    return np.array([c[0], c[1], max(c[2] + CLEAR_Z_M, p[2])])


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
    """-> (P [H, 3] commanded TCP rows for the next H ticks, velocity after row 0). The target of every row is
    via_above(row, c): over the target first, then down."""
    p, v = np.asarray(p_cmd, float), np.asarray(v_prev, float)
    rows, v0 = [], None
    for k in range(H):
        p, v = step(p, v, via_above(p, c), stop)
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
