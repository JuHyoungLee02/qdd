"""L9 v2 diagnosis: numpy URDF forward kinematics + joint-log replay of an episode (no Isaac, no cuRobo).
usage: python tools/l9/diag/urdf_fk.py <urdf> <base link> <tool link> <episode dir> [--rows i,j,...] [--every N]
Prints, per logged control step, the tool pose in the base frame (position, z axis = -approach, y axis = closing),
the commanded-vs-measured joint error (arm_target_torque_vel[:, :7] vs Q) and the applied torque / effort cap ratio.
Joint values are read from joints.npz (names, Q); joints not in the log stay 0."""
import json
import math
import os
import sys
import xml.etree.ElementTree as ET

import numpy as np


def rpy_R(r, p, y):
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    return np.array([[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
                     [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
                     [-sp, cp * sr, cp * cr]])


def axis_R(a, t):
    a = np.asarray(a, float) / np.linalg.norm(a)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(t) * K + (1 - math.cos(t)) * K @ K


def chain(urdf: str, base: str, tool: str) -> list:
    root = ET.parse(urdf).getroot()
    by_child = {}
    for j in root.iter("joint"):
        o = j.find("origin")
        xyz = [float(v) for v in (o.get("xyz", "0 0 0") if o is not None else "0 0 0").split()]
        rpy = [float(v) for v in (o.get("rpy", "0 0 0") if o is not None else "0 0 0").split()]
        ax = j.find("axis")
        by_child[j.find("child").get("link")] = {
            "name": j.get("name"), "type": j.get("type"), "parent": j.find("parent").get("link"), "xyz": xyz,
            "rpy": rpy, "axis": [float(v) for v in ax.get("xyz").split()] if ax is not None else [0, 0, 1]}
    out, link = [], tool
    while link != base:
        j = by_child[link]
        out.append(j)
        link = j["parent"]
    return out[::-1]


def fk(ch: list, q: dict) -> np.ndarray:
    T = np.eye(4)
    for j in ch:
        A = np.eye(4)
        A[:3, :3], A[:3, 3] = rpy_R(*j["rpy"]), j["xyz"]
        T = T @ A
        if j["type"] in ("revolute", "continuous"):
            B = np.eye(4)
            B[:3, :3] = axis_R(j["axis"], q.get(j["name"], 0.0))
            T = T @ B
        elif j["type"] == "prismatic":
            B = np.eye(4)
            B[:3, 3] = np.asarray(j["axis"], float) * q.get(j["name"], 0.0)
            T = T @ B
    return T


def link_points(urdf: str, base: str, tool: str, names: list, qv) -> None:
    """--q mode: every link origin of the chain base -> tool for the joint vector qv (names order), base frame."""
    ch = chain(urdf, base, tool)
    q = {n: float(v) for n, v in zip(names, qv)}
    for k in range(1, len(ch) + 1):
        T = fk(ch[:k], q)
        print(f"  {ch[k - 1]['name']:24s} -> origin {np.round(T[:3, 3], 3).tolist()}")


def main():
    urdf, base, tool, ep = sys.argv[1:5]
    if ep == "--q":  # urdf_fk.py <urdf> <base> <tool> --q <comma joint values> [names comma]
        qv = [float(v) for v in sys.argv[5].split(",")]
        names = sys.argv[6].split(",") if len(sys.argv) > 6 else [f"panda_joint{i}" for i in range(1, 8)]
        link_points(urdf, base, tool, names, qv)
        return
    ch = chain(urdf, base, tool)
    d = np.load(os.path.join(ep, "joints.npz"), allow_pickle=True)
    names, Q = [str(n) for n in d["names"]], d["q" if "q" in d.files else "Q"]
    B = d["base"] if "base" in d.files and len(d["base"]) == len(Q) else None
    every = int(sys.argv[sys.argv.index("--every") + 1]) if "--every" in sys.argv else 10
    rows = [int(v) for v in sys.argv[sys.argv.index("--rows") + 1].split(",")] if "--rows" in sys.argv else \
        list(range(0, len(Q), every))
    atv = d["arm_target_torque_vel"] if "arm_target_torque_vel" in d.files else None
    eff = d["arm_kd_effort"][2] if "arm_kd_effort" in d.files else None
    for i in rows:
        q = {n: float(v) for n, v in zip(names, Q[i])}
        T = fk(ch, q)
        if B is not None:  # world = root pose (x, y, z, yaw) @ base-frame FK
            W = np.eye(4)
            W[:3, :3], W[:3, 3] = axis_R([0, 0, 1], float(B[i, 3])), B[i, :3]
            T = W @ T
        s = f"{i:4d} t {i * float(d['dt']):6.2f} p {np.round(T[:3, 3], 4).tolist()} z {np.round(T[:3, 2], 3).tolist()} " \
            f"y {np.round(T[:3, 1], 3).tolist()}"
        if atv is not None and atv.shape[1] >= 21:
            tgt, tau, ctau = atv[i, :7], atv[i, 7:14], atv[i, 14:21]
            s += f" |tgt-q|max {np.abs(tgt - Q[i, :7]).max():.3f}"
            if eff is not None:
                s += f" tau/cap {np.round(np.abs(tau) / eff, 2).tolist()} sat {int((np.abs(ctau) > eff + 1e-3).sum())}"
        print(s)


if __name__ == "__main__":
    main()
