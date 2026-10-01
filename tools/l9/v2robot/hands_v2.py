"""(pod) Unitree G1 Dex3-1 hand -> parallel-gripper approximation (spec §12.2 G1 row: hypothesis, decided here).

usage: run.sh hand .../hands_v2.py [--out /data/harvest/l9v2robot/out/g1_hand.json]

The Dex3-1 (unitree_ros g1_29dof_with_hand_rev_1_0.urdf, BSD-3) has a thumb (3 joints) opposing index + middle
(2 joints each). All flexion axes are the palm z axis except thumb_0 (palm y), so thumb and fingers curl in the
palm xy plane toward each other. Synergy: q(s) = q_open + s (q_close - q_open), s in [0, 1]:
- q_open = all hand joints 0 (fingers straight along palm +x, thumb along palm +-y: the widest opening);
- q_close = minimises the distance between the thumb distal link and BOTH index and middle distal links (bounded
  L-BFGS over the 7 joints, thumb_0 fixed 0 so the thumb stays in the finger plane).
Per s: contact points = closest point pair thumb_2 <-> (index_1 u middle_1) (surface samples), aperture w(s) = their
distance, closing axis c(s), midpoint m(s). Parallel-gripper model: TCP = m at the narrowest useful width (contact
point when closed on a thin object), closing axis = c averaged over s, approach = component of (TCP - palm origin)
normal to c. Reported deviations (closing-axis spread, midpoint drift) decide whether the model is acceptable."""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from urdf_fk import R_rpy, Urdf  # noqa: E402

URDF = "/data/harvest/l9v2/pylib/curobo/content/assets/robot/g1/g1_29dof_with_hand_rev_1_0.urdf"
PINCH = os.environ.get("G1_PINCH", "index")  # thumb vs index pad (middle follows index); "both" = midpoint
JOINTS = ("thumb_0", "thumb_1", "thumb_2", "index_0", "index_1", "middle_0", "middle_1")


class Hand:
    def __init__(self, u: Urdf, side: str):
        self.u, self.side = u, side
        self.palm = f"{side}_hand_palm_link"
        self.jn = [f"{side}_hand_{j}_joint" for j in JOINTS]
        self.lim = np.array([[u.joints[j]["lower"], u.joints[j]["upper"]] for j in self.jn])
        self.loc = {k: u.link_points(f"{side}_hand_{k}_link", f"{side}_hand_{k}_link", {}, sample=3000)
                    for k in ("thumb_2", "index_1", "middle_1")}

    def cloud(self, k: str, q) -> np.ndarray:
        T = self.u.T_rel(f"{self.side}_hand_{k}_link", self.palm, dict(zip(self.jn, q)))
        return self.loc[k] @ T[:3, :3].T + T[:3, 3]

    def pair(self, q):
        from scipy.spatial import cKDTree
        th = self.cloud("thumb_2", q)
        fi = np.concatenate([self.cloud("index_1", q), self.cloud("middle_1", q)])
        d, i = cKDTree(fi).query(th)
        j = int(np.argmin(d))
        return float(d[j]), th[j], fi[i[j]]

    def one(self, q) -> float:
        from scipy.spatial import cKDTree
        return float(cKDTree(self.cloud("thumb_2", q)).query(self.cloud("index_1", q))[0].min())

    def both(self, q) -> float:
        from scipy.spatial import cKDTree
        th = cKDTree(self.cloud("thumb_2", q))
        return float(th.query(self.cloud("index_1", q))[0].min() + th.query(self.cloud("middle_1", q))[0].min())


def solve(side: str, u: Urdf, w_ref: float = 0.03, ang_max: float = 10.0, drift_max: float = 0.01) -> dict:
    """Parallel-pinch synergy (fingers move together: index_k = middle_k, thumb_0 = 0):
    1) close: minimise the thumb_2 <-> index_1 + middle_1 distances -> fixed pad points on the three distal links;
    2) reference pinch at w_ref -> closing axis c_ref, midpoint m_ref;
    3) for each width w (continuation from w_ref down to 0 and up to the limit): minimise
       (|Pf - Pt| - w)^2 + 0.01 (1 - (c . c_ref)^2) + 4 |m - m_ref|^2  -> width <-> joint table.
    A width is usable while |gap error| < 2 mm, axis deviation < ang_max and midpoint drift < drift_max."""
    from scipy.optimize import minimize
    h = Hand(u, side)
    lim = h.lim
    bx = [tuple(lim[1]), tuple(lim[2]), tuple(lim[3]), tuple(lim[4])]  # thumb_1, thumb_2, finger_0, finger_1

    def qv(x):
        return np.array([0.0, x[0], x[1], x[2], x[3], x[2], x[3]])

    best = None
    rng = np.random.default_rng(3)
    for _ in range(16):
        x0 = np.array([rng.uniform(lo, hi) for lo, hi in bx])
        r = minimize(lambda x: h.both(qv(x)) if PINCH != "index" else h.one(qv(x)), x0, method="L-BFGS-B",
                     bounds=bx, options={"maxiter": 200})
        if best is None or r.fun < best.fun:
            best = r
    qc = qv(best.x)
    from scipy.spatial import cKDTree
    th = h.cloud("thumb_2", qc)
    fi = {k: h.cloud(k, qc) for k in ("index_1", "middle_1")}
    if PINCH == "index":
        it = int(np.argmin(cKDTree(fi["index_1"]).query(th)[0]))
    else:
        it = int(np.argmin(np.minimum(cKDTree(fi["index_1"]).query(th)[0], cKDTree(fi["middle_1"]).query(th)[0])))
    loc = {"thumb_2": h.loc["thumb_2"][it]}
    for k in ("index_1", "middle_1"):
        loc[k] = h.loc[k][int(np.argmin(cKDTree(th).query(fi[k])[0]))]

    def pads(q):
        out = {}
        for k, p in loc.items():
            T = u.T_rel(f"{side}_hand_{k}_link", h.palm, dict(zip(h.jn, q)))
            out[k] = T[:3, :3] @ p + T[:3, 3]
        pt, pf = out["thumb_2"], (out["index_1"] if PINCH == "index" else (out["index_1"] + out["middle_1"]) / 2)
        return pt, pf

    def geom(x):
        pt, pf = pads(qv(x))
        d = pf - pt
        n = np.linalg.norm(d)
        return n, d / max(n, 1e-9), (pt + pf) / 2

    # reference pinch at w_ref
    ref = None
    for _ in range(16):
        x0 = np.array([rng.uniform(lo, hi) for lo, hi in bx])
        r = minimize(lambda x: (geom(x)[0] - w_ref) ** 2 + 1e-4 * np.sum((x - best.x) ** 2), x0, method="L-BFGS-B",
                     bounds=bx)
        if ref is None or r.fun < ref.fun:
            ref = r
    _, c_ref, m_ref = geom(ref.x)

    def fit(w, x0):
        f = lambda x: ((geom(x)[0] - w) ** 2 + 0.01 * (1 - float(geom(x)[1] @ c_ref) ** 2)  # noqa: E731
                       + 4.0 * float(np.sum((geom(x)[2] - m_ref) ** 2)))
        starts = [x0, best.x, ref.x] + [best.x + t * (ref.x - best.x) for t in (0.25, 0.5, 0.75, 1.5)]
        rs = [minimize(f, np.clip(s, [b[0] for b in bx], [b[1] for b in bx]), method="L-BFGS-B", bounds=bx)
              for s in starts]
        return min(rs, key=lambda r: r.fun).x

    rows = {}
    for seq in (np.arange(w_ref, -1e-9, -0.005), np.arange(w_ref, 0.2, 0.005)):
        x = ref.x.copy()
        for w in seq:
            x = fit(float(w), x)
            n, c, m = geom(x)
            ang = math.degrees(math.acos(min(1.0, abs(float(c @ c_ref)))))
            rows[round(float(w), 3)] = {"target": round(float(w), 3), "width": round(float(n), 4),
                                        "axis_dev_deg": round(ang, 1),
                                        "mid_drift_m": round(float(np.linalg.norm(m - m_ref)), 4),
                                        "q": [round(float(v), 4) for v in qv(x)]}
            rows[round(float(w), 3)]["ok"] = bool(abs(n - w) < 0.002 and ang < ang_max and
                                                  rows[round(float(w), 3)]["mid_drift_m"] < drift_max)
    table = [rows[k] for k in sorted(rows)]
    usable = [r for r in table if r["ok"]]
    max_w = max((r["width"] for r in usable), default=0.0)
    # usable band = the contiguous run of ok rows that contains the reference width
    i0 = [k for k, r in enumerate(table) if r["target"] == round(w_ref, 3)][0]
    lo_i, hi_i = i0, i0
    while lo_i > 0 and table[lo_i - 1]["ok"]:
        lo_i -= 1
    while hi_i < len(table) - 1 and table[hi_i + 1]["ok"]:
        hi_i += 1
    cont = table[lo_i:hi_i + 1] if table[i0]["ok"] else []
    a = m_ref - c_ref * float(m_ref @ c_ref)
    a = a / np.linalg.norm(a)
    z = -a
    y = c_ref - z * float(c_ref @ z)
    y /= np.linalg.norm(y)
    R = np.column_stack([np.cross(y, z), y, z])
    q_open = cont[-1]["q"] if cont else qv(ref.x).tolist()
    return {"side": side, "joints": h.jn, "close_residual_m": round(float(best.fun), 4),
            "pad_points_local": {k: v.round(5).tolist() for k, v in loc.items()},
            "reference_width_m": w_ref, "closing_axis_palm": c_ref.round(4).tolist(),
            "tcp_xyz": m_ref.round(5).tolist(), "approach_palm": a.round(4).tolist(),
            "tcp_rpy": [round(float(v), 6) for v in R_rpy(R)], "table": table,
            "max_opening_parallel_m": round(float(cont[-1]["width"]) if cont else 0.0, 4),
            "min_opening_parallel_m": round(float(cont[0]["width"]) if cont else 0.0, 4),
            "max_opening_any_m": round(float(max_w), 4),
            "open_q": dict(zip(h.jn, q_open)), "criteria": {"gap_err_m": 0.002, "axis_deg": ang_max,
                                                             "mid_drift_m": drift_max}}


def mirror(r: dict) -> dict:
    """Left hand = the right-hand result mirrored in the palm xz plane (the URDF hands are mirror images: left joint
    limits are the negated right ones; thumb_0 turns about y and stays 0)."""
    def mq(qd):
        return {k.replace("right_", "left_"): (0.0 if "thumb_0" in k else -float(v)) for k, v in qd.items()}
    M = np.diag([1.0, -1.0, 1.0])
    a = M @ np.array(r["approach_palm"])
    c = M @ np.array(r["closing_axis_palm"])
    z = -a
    y = c - z * float(c @ z)
    y /= np.linalg.norm(y)
    R = np.column_stack([np.cross(y, z), y, z])
    out = dict(r)
    out.update({"side": "left", "joints": [j.replace("right_", "left_") for j in r["joints"]],
                "pad_points_local": {k: (M @ np.array(v)).round(5).tolist() for k, v in r["pad_points_local"].items()},
                "closing_axis_palm": c.round(4).tolist(), "approach_palm": a.round(4).tolist(),
                "tcp_xyz": (M @ np.array(r["tcp_xyz"])).round(5).tolist(),
                "tcp_rpy": [round(float(v), 6) for v in R_rpy(R)], "open_q": mq(r["open_q"]),
                "table": [dict(t, q=[0.0 if i == 0 else -v for i, v in enumerate(t["q"])]) for t in r["table"]],
                "note": "mirrored from the right hand (independent left solve fell into a worse local minimum)"})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/data/harvest/l9v2robot/out/g1_hand.json")
    a = ap.parse_args()
    u = Urdf(URDF)
    r = solve("right", u)
    out = {"pinch": PINCH, "right": r, "left": mirror(r)}
    for side in ("right", "left"):
        r = out[side]
        print(side, json.dumps({k: r[k] for k in ("min_opening_parallel_m", "max_opening_parallel_m", "close_residual_m",
                                                  "closing_axis_palm", "approach_palm", "tcp_xyz", "tcp_rpy")}))
        print("  open_q", r["open_q"])
    json.dump(out, open(a.out, "w"), indent=1)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
