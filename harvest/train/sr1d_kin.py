"""E-SR1d real-data (S-E2E) counterfactual branches and the distance proxy of the authority a (docs/stage3/
prereg_sr1d.md). CPU only, numpy. There is no simulator and no object pose in the real recordings, so

  authority a   comes from the recorded gripper (hindsight, privileged -- used for strata and branch eligibility only):
                closed = gripper joint > GRIP_CLOSED; an EVENT is a change of that state (close = grasp, open =
                release); its EVENT POINT is the arm's end effector (URDF FK of the measured joints, arm_base_link) at
                that frame. d(k) = distance from the end effector at k to the event points of the previous and the next
                event of the same arm (the nearer one). Contact proxy = the gripper moving (|backward difference| x fps
                > GRIP_MOVE) or within CONTACT_WIN frames of an event. a = 0 on contact, else sr1c_authority.ramp(d)
                (5 / 10 cm); no event of that arm in the episode -> None (stratum 'unknown').
  branch chunk  = sr1c_branch's construction (straight, constant speed, orientation held, DLS IK from the snapshot's
                first recorded target) with the joint step per 10 Hz tick capped per joint by the recorded p99.9
                (the data's velocity limit) and the URDF joint limits (a joint may stay where the base target is,
                never move further out).
  validity      (no physics check exists): IK residual; the predicted end-effector path (measured end effector +
                FK displacement of the targets) above the episode floor (lowest recorded end-effector height of the
                episode, both arms = an upper bound of the table plane) and, when the gripper is closed, above the
                height of the grasp event (a held object is not pushed below where it rested); inside the recorded
                workspace box of that dataset / arm (+ margin: torso / reach proxy); >= ARM_MIN_M from the other arm's
                recorded end effector; per-tick end-effector speed <= the recorded p99.9; the end point >= 5 cm from
                the event points (no counterfactual ends in the contact zone).
"""
from __future__ import annotations

import numpy as np

from . import sr1c_branch as B
from .sr1c_authority import FAR_M, NEAR_M, ramp, stratum  # noqa: F401  (re-exported for the tools)

HZ = 10
GRIP_CLOSED = 0.5        # gripper joint (0 open .. ~1.1 closed; bimodal, design probe)
GRIP_MOVE = 0.2          # gripper joint units / s (~ openness 0.18 / s = the motion-line gripper boundary)
CONTACT_WIN = 3          # frames = 0.3 s
ENVELOPE_Q = (0.5, 99.5)
ENVELOPE_MARGIN_M = 0.02
ARM_MIN_M = 0.08
SPEED_Q = 99.9
CAP_Q = 99.0
NEAR_END_M = 0.05
POS_TOL_M, ROT_TOL_DEG = B.POS_TOL_M, B.ROT_TOL_DEG
LAMBDA, IK_ITERS = B.LAMBDA, 10


# ------------------------------------------------------------------------------------------ authority proxy
def gripper_events(g, thr: float = GRIP_CLOSED) -> list:
    """[(frame, 'close' | 'open')]: the first frame of each new closed / open state (closed = g > thr)."""
    c = np.asarray(g, float) > thr
    idx = np.nonzero(c[1:] != c[:-1])[0] + 1
    return [(int(i), "close" if c[i] else "open") for i in idx]


def contact_mask(g, events, fps: float = HZ, win: int = CONTACT_WIN, move: float = GRIP_MOVE) -> np.ndarray:
    """Per frame: gripper moving (causal |g[k] - g[k-1]| * fps > move) or within win frames of an event."""
    g = np.asarray(g, float)
    v = np.zeros(len(g))
    v[1:] = np.abs(np.diff(g)) * fps
    m = v > move
    for i, _ in events:
        m[max(0, i - win):i + win + 1] = True
    return m


def event_points(events, k: int) -> list:
    """Frames of the previous (<= k) and next (> k) event."""
    prev = [i for i, _ in events if i <= k]
    nxt = [i for i, _ in events if i > k]
    return ([prev[-1]] if prev else []) + ([nxt[0]] if nxt else [])


def event_distance(ee, events, k: int):
    """min distance (m) from ee[k] to the previous / next event points; None without events."""
    pts = event_points(events, k)
    if not pts:
        return None
    ee = np.asarray(ee, float)
    return float(min(np.linalg.norm(ee[k] - ee[i]) for i in pts))


def authority_proxy(d, contact: bool):
    if contact:
        return 0.0
    if d is None:
        return None
    return 0.0 if d <= NEAR_M else ramp(d)


def episode_strata(g, ee, thr: float = GRIP_CLOSED, win: int = CONTACT_WIN, fps: float = HZ) -> list:
    """[(d, contact, a, stratum)] per frame of one arm."""
    ev = gripper_events(g, thr)
    cm = contact_mask(g, ev, fps, win)
    out = []
    for k in range(len(g)):
        d = event_distance(ee, ev, k)
        a = authority_proxy(d, bool(cm[k]))
        out.append((d, bool(cm[k]), a, stratum(a)))
    return out


def grasp_height(g, ee, k: int, thr: float = GRIP_CLOSED):
    """End-effector z at the close event that started the current closed state (None when open at k)."""
    if not float(g[k]) > thr:
        return None
    ev = [i for i, e in gripper_events(g, thr) if e == "close" and i <= k]
    return float(np.asarray(ee, float)[ev[-1] if ev else 0, 2])


# ------------------------------------------------------------------------------------------ branch chunk
def ik_chunk(chain, limits, q_base, disp, dq_max, H: int = 5, iters: int = IK_ITERS):
    """(Q [H, 7], info) as sr1c_branch.ik_chunk with a per-joint per-tick step cap dq_max (7,)."""
    q_base = np.asarray(q_base, float)
    dq_max = np.asarray(dq_max, float)
    limits = np.stack([np.minimum(limits[:, 0], q_base), np.maximum(limits[:, 1], q_base)], 1)
    p0, R0 = B.fk_pose(chain, q_base[None])
    Q = np.zeros((H, 7))
    Q[0] = q_base
    pe, re = [0.0], [0.0]
    for k in range(1, H):
        goal = p0[0] + (k / (H - 1)) * np.asarray(disp, float)
        q = Q[k - 1].copy()
        for _ in range(iters):
            p, R = B.fk_pose(chain, q[None])
            e = np.concatenate([goal - p[0], B.rotvec(R0[0] @ R[0].T)])
            if float(np.abs(e).max()) < 1e-7:
                break
            J = B.jacobian(chain, q[None])[0]
            q = q + J.T @ np.linalg.solve(J @ J.T + LAMBDA ** 2 * np.eye(6), e)
            q = Q[k - 1] + np.clip(q - Q[k - 1], -dq_max, dq_max)
            q = np.clip(q, limits[:, 0], limits[:, 1])
        Q[k] = q
        p, R = B.fk_pose(chain, q[None])
        pe.append(float(np.linalg.norm(goal - p[0])))
        re.append(float(np.degrees(np.linalg.norm(B.rotvec(R0[0] @ R[0].T)))))
    info = {"pos_err_max_m": max(pe), "rot_err_max_deg": max(re)}
    info["ok"] = info["pos_err_max_m"] <= POS_TOL_M and info["rot_err_max_deg"] <= ROT_TOL_DEG
    return Q, info


def cap_disp(disp, cap_m: float):
    n = float(np.linalg.norm(disp))
    if n <= cap_m or n == 0:
        return np.asarray(disp, float), 1.0
    return np.asarray(disp, float) * (cap_m / n), cap_m / n


def dir_err_deg(disp_fk, forced) -> float:
    """Angle (deg) between the FK displacement of the chunk and the forced 3-D direction."""
    a, b = np.asarray(disp_fk, float), np.asarray(forced, float)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 180.0
    return float(np.degrees(np.arccos(np.clip(a @ b / (na * nb), -1.0, 1.0))))


def validity(path, floor_z: float, hold_z, env_lo, env_hi, other_path, speed_max: float, end_dist):
    """First failing check name or None. path [H, 3] = predicted end-effector path (arm_base_link)."""
    path = np.asarray(path, float)
    if float(path[:, 2].min()) < floor_z:
        return "table"
    if hold_z is not None and float(path[:, 2].min()) < hold_z:
        return "held_table"
    if np.any(path < np.asarray(env_lo) - ENVELOPE_MARGIN_M) or np.any(path > np.asarray(env_hi) + ENVELOPE_MARGIN_M):
        return "envelope"
    if other_path is not None:
        o = np.asarray(other_path, float)
        if float(np.linalg.norm(path - o, axis=1).min()) < ARM_MIN_M:
            return "other_arm"
    if float(np.linalg.norm(np.diff(path, axis=0), axis=1).max()) > speed_max:
        return "speed"
    if end_dist is not None and end_dist < NEAR_END_M:
        return "near_end"
    return None
