"""E-SR1c far-segment counterfactual branches (docs/stage3/prereg_sr1c.md §2; research doc
decision_adherence_0p8_2026-09-26.md §2 D2, §6). CPU only, numpy.

A branch = the SAME observation as an R2 stage-B snapshot (frames, proprio) with a FORCED joystick decision
(dir_xy, dir_z, mag_coarse) and a target chunk that moves the end effector straight along that decision:
  base target q_b = the snapshot's first recorded target (action_exec[0], so the command stream stays continuous and
  the arm's gravity-sag offset of the recorded targets is kept); p_b, R_b = FK(q_b) (URDF, arm_base_link = table axes)
  target k = DLS IK (lambda 0.05 as the planner) of p_b + (k / (H - 1)) * disp with orientation R_b, joint step per
  tick capped at MAX_DQ_TICK (planner MAX_DQ_RAD 0.04 per 50 ms at 30 Hz), joint limits from the URDF
  disp = m_c * unit(u_xy + u_z), m_c = the magnitude bin's value (0.5 / 1 / 2 / 4 / 8 cm) capped by the planner's
  fast TCP speed over the chunk (V_CAP * (H - 1) / hz); gripper target = the snapshot's first target, held.
FK(last) - FK(first) = disp, i.e. the E-SR0 chunk displacement definition.
Filters (predicted fingertip path = the snapshot's measured finger midpoint + the FK displacement of the targets,
table frame): IK residual (position <= 2 mm, orientation <= 2 deg), pad bottom (finger midpoint - PAD_BELOW_M)
>= table + 5 mm, the gripper box clear of every object box but the held one (+5 mm), a held object's bottom >= table
+ 5 mm and clear of the other objects, the end point outside the near zone (stage distance >= 5 cm).
"""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET

import numpy as np

from .se2e_data import _axis_rot

DIR_XY8 = ("plus_x", "plus_x_plus_y", "plus_y", "minus_x_plus_y", "minus_x", "minus_x_minus_y", "minus_y",
           "plus_x_minus_y")
_SGN = {"plus_x": (1, 0), "plus_x_plus_y": (1, 1), "plus_y": (0, 1), "minus_x_plus_y": (-1, 1), "minus_x": (-1, 0),
        "minus_x_minus_y": (-1, -1), "minus_y": (0, -1), "plus_x_minus_y": (1, -1), "none_xy": (0, 0)}
DIR_Z3 = ("up", "down", "none_z")
MAG_M = {"tiny": 0.005, "small": 0.01, "medium": 0.02, "large": 0.04, "xlarge": 0.08}  # = sim.planner.MAG_BINS
HZ = 30
V_CAP = 0.20            # m/s = sim.planner.V_FAST
MAX_DQ_TICK = 0.04 * (1.0 / HZ) / 0.05  # planner MAX_DQ_RAD per 50 ms, scaled to one 30 Hz tick
LAMBDA = 0.05           # planner DLS lambda_val
IK_ITERS = 8
POS_TOL_M, ROT_TOL_DEG = 0.002, 2.0
PAD_BELOW_M = 0.027     # pad bottom below the finger midpoint (pads cover 45 mm, midpoint 18 mm below the top)
TABLE_MARGIN_M = 0.005
BOX_MARGIN_M = 0.005
GRIP_HALF = np.array([0.06, 0.02])   # gripper footprint half size: along the finger-opening axis (x) and y [assumption]
GRIP_UP_M = 0.04                     # gripper body above the finger midpoint considered [assumption]
NEAR_END_M = 0.05


# ------------------------------------------------------------------------------------------ kinematics
def joint_limits(urdf: str, arm: str = "right") -> np.ndarray:
    """(7, 2) lower / upper of arm_{r|l}_joint1..7 (missing limit -> +-pi)."""
    root = ET.fromstring(urdf) if urdf.lstrip().startswith("<") else ET.parse(urdf).getroot()
    out = np.tile([-math.pi, math.pi], (7, 1)).astype(float)
    for j in root.findall("joint"):
        n = j.get("name", "")
        pre = f"arm_{arm[0]}_joint"
        if n.startswith(pre) and n[len(pre):].isdigit():
            L = j.find("limit")
            if L is not None:
                out[int(n[len(pre):]) - 1] = [float(L.get("lower")), float(L.get("upper"))]
    return out


def fk_pose(chain, q):
    """(p [N,3], R [N,3,3]) of the end effector in the base link (se2e_data.load_arm_chain chain)."""
    q = np.asarray(q, float).reshape(-1, 7)
    n = len(q)
    R = np.broadcast_to(np.eye(3), (n, 3, 3)).copy()
    p = np.zeros((n, 3))
    i = 0
    for typ, xyz, Ro, axis in chain:
        p = p + R @ xyz
        R = R @ Ro
        if typ in ("revolute", "continuous"):
            R = R @ _axis_rot(axis, q[:, i])
            i += 1
    return p, R


def jacobian(chain, q):
    """Geometric Jacobian [N, 6, 7] (linear; angular) of the end effector in the base link."""
    q = np.asarray(q, float).reshape(-1, 7)
    n = len(q)
    R = np.broadcast_to(np.eye(3), (n, 3, 3)).copy()
    p = np.zeros((n, 3))
    axes, origins = [], []
    i = 0
    for typ, xyz, Ro, axis in chain:
        p = p + R @ xyz
        R = R @ Ro
        if typ in ("revolute", "continuous"):
            a = np.asarray(axis, float) / np.linalg.norm(axis)
            axes.append(R @ a)
            origins.append(p.copy())
            R = R @ _axis_rot(axis, q[:, i])
            i += 1
    J = np.zeros((n, 6, 7))
    for j, (z, o) in enumerate(zip(axes, origins)):
        J[:, :3, j] = np.cross(z, p - o)
        J[:, 3:, j] = z
    return J


def rotvec(R) -> np.ndarray:
    """Axis-angle vector of rotation matrices [..., 3, 3]."""
    R = np.asarray(R, float)
    c = np.clip((np.trace(R, axis1=-2, axis2=-1) - 1) / 2, -1.0, 1.0)
    th = np.arccos(c)
    v = np.stack([R[..., 2, 1] - R[..., 1, 2], R[..., 0, 2] - R[..., 2, 0], R[..., 1, 0] - R[..., 0, 1]], -1)
    s = np.sin(th)
    f = np.where(s > 1e-9, th / (2 * np.where(s > 1e-9, s, 1.0)), 0.5)
    return v * f[..., None]


def ik_chunk(chain, limits, q_base, disp, H: int = 15, iters: int = IK_ITERS):
    """(Q [H, 7], info): target k tracks p_b + k / (H - 1) * disp with orientation R_b (see module doc)."""
    q_base = np.asarray(q_base, float)
    # the sim robot's recorded targets can sit outside the URDF range (R2 joint 7 at 1.80 > 1.58): a joint may stay
    # where the base target is, but never move further out
    limits = np.stack([np.minimum(limits[:, 0], q_base), np.maximum(limits[:, 1], q_base)], 1)
    p0, R0 = fk_pose(chain, q_base[None])
    Q = np.zeros((H, 7))
    Q[0] = q_base
    pe, re = [0.0], [0.0]
    for k in range(1, H):
        goal = p0[0] + (k / (H - 1)) * np.asarray(disp, float)
        q = Q[k - 1].copy()
        for _ in range(iters):
            p, R = fk_pose(chain, q[None])
            e = np.concatenate([goal - p[0], rotvec(R0[0] @ R[0].T)])
            if float(np.abs(e).max()) < 1e-7:
                break
            J = jacobian(chain, q[None])[0]
            dq = J.T @ np.linalg.solve(J @ J.T + LAMBDA ** 2 * np.eye(6), e)
            q = q + dq
            q = Q[k - 1] + np.clip(q - Q[k - 1], -MAX_DQ_TICK, MAX_DQ_TICK)
            q = np.clip(q, limits[:, 0], limits[:, 1])
        Q[k] = q
        p, R = fk_pose(chain, q[None])
        pe.append(float(np.linalg.norm(goal - p[0])))
        re.append(float(np.degrees(np.linalg.norm(rotvec(R0[0] @ R[0].T)))))
    info = {"pos_err_max_m": max(pe), "rot_err_max_deg": max(re)}
    info["ok"] = info["pos_err_max_m"] <= POS_TOL_M and info["rot_err_max_deg"] <= ROT_TOL_DEG
    return Q, info


# ------------------------------------------------------------------------------------------ decisions
def direction(dir_xy: str, dir_z: str) -> np.ndarray:
    v = np.array([*_SGN[dir_xy], {"up": 1, "down": -1, "none_z": 0}[dir_z]], float)
    if abs(v[0]) + abs(v[1]) > 0:
        v[:2] /= np.linalg.norm(v[:2])
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def forced_decisions(label_xy: str, rng, K: int = 4) -> list:
    """K forced decisions: dir_xy = K distinct of the 8 directions without the label; dir_z uniform over 3; mag
    uniform over 5 (the rng draws in this order)."""
    pool = [d for d in DIR_XY8 if d != label_xy]
    xs = [pool[i] for i in rng.choice(len(pool), size=K, replace=False)]
    zs = [DIR_Z3[i] for i in rng.integers(0, 3, size=K)]
    ms = [list(MAG_M)[i] for i in rng.integers(0, 5, size=K)]
    return [{"dir_xy": x, "dir_z": z, "mag_coarse": m} for x, z, m in zip(xs, zs, ms)]


def cap_disp(disp, H: int = 15, hz: int = HZ):
    """(disp capped to the planner fast TCP speed over the chunk, applied scale)."""
    lim = V_CAP * (H - 1) / hz
    n = float(np.linalg.norm(disp))
    if n <= lim or n == 0:
        return np.asarray(disp, float), 1.0
    return np.asarray(disp, float) * (lim / n), lim / n


# ------------------------------------------------------------------------------------------ filters
def table_ok(path_table) -> bool:
    """Pad bottom (finger midpoint - PAD_BELOW_M) >= table + TABLE_MARGIN_M along the path (table frame, z up)."""
    return bool(np.min(np.asarray(path_table, float)[:, 2]) - PAD_BELOW_M >= TABLE_MARGIN_M)


def gripper_hits_box(tcp, box, margin: float = BOX_MARGIN_M) -> bool:
    """Axis-aligned overlap of the gripper box (around the finger midpoint) and an object box (+ margin)."""
    tcp = np.asarray(tcp, float)
    lo = np.array([tcp[0] - GRIP_HALF[0], tcp[1] - GRIP_HALF[1], tcp[2] - PAD_BELOW_M])
    hi = np.array([tcp[0] + GRIP_HALF[0], tcp[1] + GRIP_HALF[1], tcp[2] + GRIP_UP_M])
    blo, bhi = box["center"] - box["half"] - margin, box["center"] + box["half"] + margin
    return bool(np.all(lo < bhi) and np.all(hi > blo))


def boxes_overlap(a, b, margin: float = BOX_MARGIN_M) -> bool:
    return bool(np.all(np.abs(a["center"] - b["center"]) < a["half"] + b["half"] + margin))


def obj_box(pos_table, quat_wxyz, geom: dict) -> dict:
    """Conservative axis-aligned box of an object (cylinder: radius; cuboid: footprint circle for any yaw)."""
    he = np.asarray(geom["half_extents"], float)
    r = geom.get("footprint_r", max(he[0], he[1]))
    return {"center": np.asarray(pos_table, float), "half": np.array([r, r, he[2]])}


# ------------------------------------------------------------------------------------------ rows
def branch_row(row: dict, forced: dict, Q, info: dict) -> dict:
    """A stage-B row for the branch: forced committed decision (target / phase come from the labels at load time),
    action_exec = action_script = the IK chunk with the snapshot's first gripper target held, all steps valid,
    aux / verify empty (no aux, no verification, no decision loss -- the sample has no items)."""
    g = float(row["action_exec"][0][7])
    acts = [[round(float(v), 6) for v in q] + [g] for q in np.asarray(Q, float)]
    keep = ("seed", "kind", "k", "hz", "H", "arm", "skill_id", "phase_id", "proprio", "task", "variant")
    out = {k: row[k] for k in keep if k in row}
    out.update(action_exec=acts, action_script=[list(a) for a in acts], valid=[1] * len(acts),
               aux={"reg": {}, "cls": {}}, verify=None, committed=dict(forced), decision=False,
               branch={"src": {"seed": row["seed"], "kind": row["kind"], "k": row["k"]}, **info})
    return out
