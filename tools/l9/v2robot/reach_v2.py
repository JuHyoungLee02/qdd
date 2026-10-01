"""(pod, cuRobo v0.8.0) L9 v2 reach map per (profile, arm) (spec §12.2: built once per robot; scene placement uses it).

usage: run.sh reach .../reach_v2.py <profile> <arm> [--step 0.05] [--out DIR]

Grid of TCP positions in the config base frame (curobo9.base_link). Per cell, TCP orientations from the 4 approach
classes (curobo9.approach_class with the base->cell horizontal direction):
  top      tilt 0 deg x wrist 0..165 step 15 (12) + tilt 15 deg x 4 azimuths x wrist {0, 90}
  oblique  tilt {35, 50, 60} x 6 azimuths (f-90, f-45, f, f+45, f+90, f+180) x wrist {0, 90}
  front / side  tilt {75, 90} x 12 azimuths (every 30 deg from f) x wrist {0, 90}; |azimuth - f| < 45 = front
(f = azimuth of the cell seen from the base origin; wrist = rotation of the closing axis about the approach.)
Batched IK (self-collision on, no world, num_seeds 24); a cell is reachable for a class if any of its poses solved.
JSON: grid {x,y,z: lo, step, n}, ok {class: '0'/'1' string in x-major, then y, then z order}, rates."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import time

import numpy as np
import torch

from harvest.l9 import curobo9 as C

BOXES = {  # base-frame TCP boxes (m): x, y (right arm; mirrored for left), z
    "ffw_sg2": ((0.05, 0.85), (-0.75, 0.35), (-0.85, 0.10)),
    "franka_mast": ((-0.10, 0.90), (-0.70, 0.70), (-0.20, 0.70)),
    "r1pro": ((0.00, 0.85), (-0.80, 0.40), (-0.95, 0.40)),
    "g1": ((0.00, 0.70), (-0.65, 0.35), (-0.65, 0.40)),
}
OUT_DEFAULT = "/data/harvest/l9v2robot/out/reach_v2"


def tcp_R(tilt_deg: float, az: float, wrist_deg: float) -> np.ndarray:
    th = math.radians(tilt_deg)
    a = np.array([math.sin(th) * math.cos(az), math.sin(th) * math.sin(az), -math.cos(th)])
    z = -a
    yref = np.array([-math.sin(az), math.cos(az), 0.0])  # horizontal, normal to the approach azimuth
    yref = yref - z * (yref @ z)
    yref /= np.linalg.norm(yref)
    w = math.radians(wrist_deg)
    y = yref * math.cos(w) + np.cross(z, yref) * math.sin(w)
    return np.column_stack([np.cross(y, z), y, z])


def quat(R) -> list:
    w = math.sqrt(max(0.0, 1 + R[0, 0] + R[1, 1] + R[2, 2])) / 2
    x = math.copysign(math.sqrt(max(0.0, 1 + R[0, 0] - R[1, 1] - R[2, 2])) / 2, R[2, 1] - R[1, 2])
    y = math.copysign(math.sqrt(max(0.0, 1 - R[0, 0] + R[1, 1] - R[2, 2])) / 2, R[0, 2] - R[2, 0])
    z = math.copysign(math.sqrt(max(0.0, 1 - R[0, 0] - R[1, 1] + R[2, 2])) / 2, R[1, 0] - R[0, 1])
    return [w, x, y, z]


def cell_poses(x: float, y: float) -> list:
    """[(class, quat)] for a cell at base-frame (x, y)."""
    f = math.atan2(y, x) if abs(x) + abs(y) > 1e-6 else 0.0
    out = []
    for w in range(0, 180, 15):
        out.append(tcp_R(0.0, 0.0, w))
    for k in range(4):
        for w in (0, 90):
            out.append(tcp_R(15.0, f + k * math.pi / 2, w))
    for t in (35.0, 50.0, 60.0):
        for d in (-90, -45, 0, 45, 90, 180):
            for w in (0, 90):
                out.append(tcp_R(t, f + math.radians(d), w))
    for t in (75.0, 90.0):
        for d in range(-150, 181, 30):
            for w in (0, 90):
                out.append(tcp_R(t, f + math.radians(d), w))
    res = []
    for R in out:
        a = -R[:, 2]
        res.append((C.approach_class(a, (x, y)), quat(R)))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("profile", choices=sorted(C.PROFILES))
    ap.add_argument("arm")
    ap.add_argument("--step", type=float, default=0.05)
    ap.add_argument("--batch", type=int, default=2048)
    ap.add_argument("--out", default=OUT_DEFAULT)
    a = ap.parse_args()
    from curobo.types import GoalToolPose, Pose
    (x0, x1), (y0, y1), (z0, z1) = BOXES[a.profile]
    if a.arm == "left":
        y0, y1 = -y1, -y0
    axes = {}
    for k, (lo, hi) in zip("xyz", ((x0, x1), (y0, y1), (z0, z1))):
        n = int(round((hi - lo) / a.step)) + 1
        axes[k] = {"lo": round(lo, 4), "step": a.step, "n": n}
    xs = [axes["x"]["lo"] + i * a.step for i in range(axes["x"]["n"])]
    ys = [axes["y"]["lo"] + i * a.step for i in range(axes["y"]["n"])]
    zs = [axes["z"]["lo"] + i * a.step for i in range(axes["z"]["n"])]
    ncell = len(xs) * len(ys) * len(zs)
    pos, qts, cls, cid = [], [], [], []
    ci = 0
    for x in xs:
        for y in ys:
            cp = cell_poses(x, y)
            for z in zs:
                for c, q in cp:
                    pos.append((x, y, z))
                    qts.append(q)
                    cls.append(c)
                    cid.append(ci)
                ci += 1
    pos, qts = np.array(pos, np.float32), np.array(qts, np.float32)
    cls, cid = np.array(cls), np.array(cid)
    print(f"{a.profile} {a.arm}: {ncell} cells, {len(pos)} poses", flush=True)
    ik = C.make_ik(a.profile, a.arm, num_seeds=24, max_batch_size=a.batch)
    tf = C.tool_frame(a.profile, a.arm)
    ok = np.zeros(len(pos), bool)
    t0 = time.time()
    for s in range(0, len(pos), a.batch):
        e = min(len(pos), s + a.batch)
        P = np.zeros((a.batch, 3), np.float32)
        Q = np.tile(np.array([[1, 0, 0, 0]], np.float32), (a.batch, 1))
        P[: e - s], Q[: e - s] = pos[s:e], qts[s:e]
        r = ik.solve_pose(GoalToolPose.from_poses({tf: Pose(position=torch.tensor(P, device="cuda"),
                                                              quaternion=torch.tensor(Q, device="cuda"))},
                                                  num_goalset=1))
        ok[s:e] = r.success.view(-1).cpu().numpy()[: e - s]
        if (s // a.batch) % 20 == 0:
            print(f"  {e}/{len(pos)} poses, {time.time() - t0:.0f} s, pose success so far {ok[:e].mean():.3f}",
                  flush=True)
    grid_ok, rates = {}, {}
    for c in C.APPROACHES:
        m = np.zeros(ncell, bool)
        sel = cls == c
        np.logical_or.at(m, cid[sel], ok[sel])
        grid_ok[c] = "".join("1" if v else "0" for v in m)
        rates[c] = {"cells_reachable": round(float(m.mean()), 4), "poses_solved": round(float(ok[sel].mean()), 4),
                    "n_poses": int(sel.sum())}
    cfgp = C.config_path(a.profile, a.arm)
    out = {"profile": a.profile, "arm": a.arm, "base_link": C.base_link(a.profile, a.arm), "tool_frame": tf,
           "curobo": C.CUROBO_VERSION, "config": os.path.basename(cfgp),
           "config_sha256": hashlib.sha256(open(cfgp, "rb").read()).hexdigest()[:16],
           "grid": axes, "order": "x-major, then y, then z", "ok": grid_ok, "rates": rates,
           "method": __doc__.split("\n\n")[1], "seconds": round(time.time() - t0, 1)}
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, f"{a.profile}_{a.arm}.json")
    json.dump(out, open(path, "w"))
    print("rates", json.dumps(rates))
    print("wrote", path)


if __name__ == "__main__":
    main()
