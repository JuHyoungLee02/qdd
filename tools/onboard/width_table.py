"""(pod, trimesh) Generic gripper width table: measure the REAL free gap at the TCP plane from the collision mesh via
FK, instead of trusting a pad-tip / tip-to-tip shortcut.

Onboarding tool (A), design doc docs/research/embodiment_onboarding_2026-10-03.md §3.3/§4.1 step 4. Lesson: an
earlier G1 width table measured tip-to-tip distance on the Dex3-1 three-finger hand and was 30-45 mm off the real
pinch gap (the thumb tip and the index/middle tips are not at the same height, so tip-to-tip != the gap the pads
actually leave at the TCP plane). The fix (assets9/grippers/g1_*.json) is a per-posture FK measurement. This script
generalizes that single idea -- nearest-mesh-point distance between fingers, in a slab around the TCP plane -- into
one small, robot-agnostic check any new hand runs through. It reuses tools/l9/v2robot/urdf_fk.Urdf (the same FK
build_curobo9.py / robots_v2.py already use) and the same nearest-point idea as robots_v2.pad_gap (generalized from
"distal half of a flat parallel pad" to "slab around the measured TCP z", which also works on multi-finger hands and
does not assume the fingers are a symmetric parallel pair). No new geometry algorithm; no learned model.

Two subcommands:
  generate <urdf> <parent> <f1,f2[,f3...]> <ax,ay,az> <tcp_link> <joint:lo:hi,...> [--n 20] [--kind collision]
      -> a fresh table for a simple gripper: every listed joint swept together, lo..hi in `n` steps. Use this for a
         new 2-finger parallel gripper (the common, simple case) -- no hand-authored synergy table needed.
  verify <urdf> <parent> <f1,f2[,f3...]> <ax,ay,az> <tcp_link> <table.json>
      -> re-measures every row of an EXISTING width_to_joint table (any finger count, e.g. a hand-authored synergy
         table for a multi-finger hand) and reports claimed vs independently-measured gap -- this is self-check 4
         (selfcheck.py): width table monotonic and matching the mesh gap.
`tcp_link` must already be in the prepared URDF (a fixed child of `parent`, written by robots_v2.write_prepared /
build_curobo9.py): its position in `parent` gives the TCP-plane offset along the approach axis; it does not depend
on q, so it is read once with q={}.

usage: width_table.py generate|verify <urdf> <parent> <fingers> <approach> <tcp_link> <rest...> [--kind K] [--out F]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "l9", "v2robot"))
from urdf_fk import Urdf  # noqa: E402


def tcp_z_in_parent(u: Urdf, parent: str, tcp_link: str, approach: np.ndarray) -> float:
    """Signed offset (m) of `tcp_link` from `parent`'s origin along `approach` (tcp_link is a fixed child: q-free)."""
    t = u.T_rel(tcp_link, parent, {})[:3, 3]
    return float(t @ approach)


def slab_points(u: Urdf, link: str, parent: str, q: dict, approach: np.ndarray, tcp_z: float, half: float = 0.01,
                kind: str = "collision", sample: int = 6000) -> np.ndarray:
    """Mesh points of `link` (in `parent` frame) within `half` of the TCP plane along `approach`; if the posture puts
    no point that close (e.g. the finger is far open), falls back to the nearest 5% of points to the plane so the
    measurement degrades gracefully instead of silently returning nothing."""
    p = u.link_points(link, parent, q, kind=kind, sample=sample)
    if len(p) == 0:
        return p
    d = p @ approach
    m = np.abs(d - tcp_z) <= half
    if not m.any():
        order = np.argsort(np.abs(d - tcp_z))
        m = np.zeros(len(p), bool)
        m[order[: max(50, len(p) // 20)]] = True
    return p[m]


def real_gap(pa: np.ndarray, pb: np.ndarray) -> float | None:
    """Nearest-point Euclidean distance between two point clouds (m), or None if either is empty."""
    if len(pa) == 0 or len(pb) == 0:
        return None
    d = np.linalg.norm(pa[:, None, :] - pb[None, :, :], axis=-1)
    return float(d.min())


def measured_gap(u: Urdf, parent: str, fingers: list, q: dict, approach: np.ndarray, tcp_z: float,
                 kind: str = "collision", half: float = 0.01) -> float | None:
    """The tightest pairwise gap among all fingers at the TCP plane -- generalizes to 2-finger (one pair) and
    multi-finger (e.g. 3-finger pinch: the binding pair) hands the same way."""
    pts = [slab_points(u, f, parent, q, approach, tcp_z, half=half, kind=kind) for f in fingers]
    best = None
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            g = real_gap(pts[i], pts[j])
            if g is not None and (best is None or g < best):
                best = g
    return best


def generate(u: Urdf, parent: str, fingers: list, approach: np.ndarray, tcp_z: float, joint_ranges: dict, n: int,
            kind: str, half: float = 0.01) -> list:
    rows = []
    for k in range(n):
        s = k / (n - 1) if n > 1 else 0.0
        q = {j: lo + (hi - lo) * s for j, (lo, hi) in joint_ranges.items()}
        g = measured_gap(u, parent, fingers, q, approach, tcp_z, kind=kind, half=half)
        rows.append({"q": q, "width_m": round(g, 5) if g is not None else None})
    return rows


def rows_to_q(table: dict, wtj: dict, i: int) -> dict:
    """One row of q_by_joint (G1-style synergy table) or drive_q + finger_joints.drive/followers (R1 Pro-style:
    a single driven joint + a multiplier per follower, no <mimic> in the floating URDF)."""
    if "q_by_joint" in wtj:
        return {j: wtj["q_by_joint"][j][i] for j in wtj["q_by_joint"]}
    fj = table["finger_joints"]
    qd = wtj["drive_q"][i]
    q = {j: qd for j in fj["drive"]}
    q.update({j: m * qd for j, m in fj.get("followers", {}).items()})
    return q


def verify(u: Urdf, parent: str, fingers: list, approach: np.ndarray, tcp_z: float, table: dict, kind: str,
          half: float = 0.01) -> list:
    wtj = table.get("width_to_joint", table)
    width_m = wtj["width_m"]
    out = []
    for i, claimed in enumerate(width_m):
        q = rows_to_q(table, wtj, i)
        measured = measured_gap(u, parent, fingers, q, approach, tcp_z, kind=kind, half=half)
        out.append({"i": i, "claimed_mm": round(claimed * 1e3, 2),
                    "measured_mm": round(measured * 1e3, 2) if measured is not None else None,
                    "diff_mm": round((claimed - measured) * 1e3, 2) if measured is not None else None})
    return out


def monotonic_check(width_m: list) -> tuple:
    """-> (ok, detail). Strictly increasing (the design doc's other half of self-check 4)."""
    bad = [i for i in range(1, len(width_m)) if width_m[i] <= width_m[i - 1]]
    return (not bad), f"{len(width_m)} rows, non-increasing at indices {bad[:5]}" if bad else f"{len(width_m)} rows, strictly increasing"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("generate", "verify"))
    ap.add_argument("urdf")
    ap.add_argument("parent")
    ap.add_argument("fingers", help="comma-separated link names")
    ap.add_argument("approach", help="comma-separated xyz, e.g. 0,0,-1")
    ap.add_argument("tcp_link")
    ap.add_argument("rest", nargs="+", help="generate: joint:lo:hi,...  [--n 20] | verify: table.json")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--kind", default="collision")
    ap.add_argument("--half", type=float, default=0.01, help="slab half-width around the TCP plane (m)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    u = Urdf(a.urdf)
    fingers = a.fingers.split(",")
    approach = np.array([float(v) for v in a.approach.split(",")], float)
    approach /= np.linalg.norm(approach)
    tcp_z = tcp_z_in_parent(u, a.parent, a.tcp_link, approach)

    if a.mode == "generate":
        joint_ranges = {}
        for tok in a.rest[0].split(","):
            j, lo, hi = tok.split(":")
            joint_ranges[j] = (float(lo), float(hi))
        rows = generate(u, a.parent, fingers, approach, tcp_z, joint_ranges, a.n, a.kind, half=a.half)
        width_m = [r["width_m"] for r in rows if r["width_m"] is not None]
        ok, detail = monotonic_check(width_m)
        out = {"mode": "generate", "tcp_z_in_parent": round(tcp_z, 5), "rows": rows,
              "monotonic_ok": ok, "monotonic_detail": detail}
    else:
        table = json.load(open(a.rest[0]))
        rows = verify(u, a.parent, fingers, approach, tcp_z, table, a.kind, half=a.half)
        wtj = table.get("width_to_joint", table)
        ok, detail = monotonic_check(wtj["width_m"])
        worst = max((abs(r["diff_mm"]) for r in rows if r["diff_mm"] is not None), default=0.0)
        out = {"mode": "verify", "tcp_z_in_parent": round(tcp_z, 5), "rows": rows, "monotonic_ok": ok,
              "monotonic_detail": detail, "worst_abs_diff_mm": round(worst, 2)}
    print(json.dumps(out, indent=1))
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
