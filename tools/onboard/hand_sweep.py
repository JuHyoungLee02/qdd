"""(pod, Isaac python: trimesh) Hand sweep: the generic gripper layer's measurement (harvest/l9/hand9.py).

Input = the hand descriptor only (assets9/grippers/hands9.json: fingertip links + opposition) plus the gripper's own
URDF / json (assets9/grippers/<name>.{urdf,json}, already written by tools/l9/v2robot/grippers_v2.py for every L9
gripper). The closing path is swept by FK over the COLLISION meshes; per row:
  - every finger chain (tip + its ancestors below the base link) in frame G,
  - the free gap between the opposing chains at the TCP plane (hand9.hand_gap: z_G in hand9.BANDS, |x_G| < XH),
  - every fingertip's contact point (closest to the opposing side).
Output (one file per gripper, assets9/grippers/gap9/<name>.json): the measured gap table (closed -> open, closed
rows collapsed to gap 0), the old claimed width of each row (for the width self-check), the fingertip contact
points per kept row (overlay), and the derived grasp frame (tcp = fingertip convergence, closing axis, palm normal)
with its error against the json frame G (self-check 4).

usage: hand_sweep.py <name> [<name> ...] [--out-dir D] [--dense 21] [--sample 3000]
       (run from the repo root; PYTHONPATH = repo root)"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools", "l9", "v2robot"))
from urdf_fk import T_of, Urdf  # noqa: E402

from harvest.l9 import hand9 as H  # noqa: E402

VIRTUAL = ("vx", "vy", "vz", "vr", "vp", "vyaw")


def prim_points(prim: dict, n: int = 3000) -> np.ndarray:
    """Surface samples of a URDF primitive (box / cylinder / sphere) in its geometry frame (R1 Pro's finger
    colliders are boxes: the sim collides with the box, not the visual mesh)."""
    rng = np.random.default_rng(0)
    if "box" in prim:
        h = np.array([float(v) for v in prim["box"]["size"].split()]) / 2
        p = rng.uniform(-1, 1, (n, 3))
        k = rng.integers(0, 3, n)
        p[np.arange(n), k] = np.sign(p[np.arange(n), k])
        return p * h
    if "cylinder" in prim:
        r, L = float(prim["cylinder"]["radius"]), float(prim["cylinder"]["length"])
        a = rng.uniform(0, 2 * np.pi, n)
        return np.stack([r * np.cos(a), r * np.sin(a), rng.uniform(-L / 2, L / 2, n)], 1)
    if "sphere" in prim:
        v = rng.normal(size=(n, 3))
        return float(prim["sphere"]["radius"]) * v / np.linalg.norm(v, axis=1, keepdims=True)
    return np.zeros((0, 3))


def link_pts(u: Urdf, link: str, frame: str, q: dict, kind: str = "collision", sample: int = 3000) -> np.ndarray:
    """Mesh AND primitive points of `link` in `frame` (urdf_fk.link_points skips primitives)."""
    P = [u.link_points(link, frame, q, kind=kind, sample=sample)]
    T = u.T_rel(link, frame, q)
    for fn, sc, Tg, prim in u.geoms(link, kind):
        if fn is None and prim:
            v = prim_points(prim, sample)
            v = (Tg[:3, :3] @ v.T).T + Tg[:3, 3]
            P.append((T[:3, :3] @ v.T).T + T[:3, 3])
    return np.concatenate(P)


def chain(u: Urdf, tip: str, base: str) -> list:
    """The finger chain: tip + its ancestors strictly below `base`."""
    out, link = [], tip
    while link != base and link in u.child_joint:
        out.append(link)
        link = u.joints[u.child_joint[link]]["parent"]
    return out[::-1]


def finger_joints(u: Urdf, base: str, tips: list) -> list:
    js = []
    for t in tips:
        for lk in chain(u, t, base):
            jn = u.child_joint[lk]
            if u.joints[jn]["type"] in ("revolute", "continuous", "prismatic") and jn not in VIRTUAL and jn not in js:
                js.append(jn)
    return js


def path_from_table(gj: dict, dense: int) -> tuple:
    """-> (rows [q dict], claimed widths) ordered closed -> open, from the gripper json width_to_joint."""
    wt = gj["width_to_joint"]
    W = np.asarray(wt["width_m"], float)
    if "q_by_joint" in wt:
        J = list(wt["q_by_joint"])
        Q = np.array([wt["q_by_joint"][j] for j in J], float).T
        o = np.argsort(W)
        W, Q = W[o], Q[o]
        rows, claimed = [], []
        for i in range(len(W)):  # the table rows + their midpoints
            rows.append({j: float(Q[i, k]) for k, j in enumerate(J)})
            claimed.append(float(W[i]))
            if i + 1 < len(W):
                rows.append({j: float((Q[i, k] + Q[i + 1, k]) / 2) for k, j in enumerate(J)})
                claimed.append(float((W[i] + W[i + 1]) / 2))
        return rows, claimed
    fj = gj["finger_joints"]
    D = np.asarray(wt["drive_q"], float)
    o = np.argsort(W)
    W, D = W[o], D[o]
    ws = np.linspace(W[0], W[-1], dense)
    rows, claimed = [], []
    for w in ws:
        d = float(np.interp(w, W, D))
        q = {j: d for j in fj["drive"]}
        q.update({j: float(m) * d for j, m in fj.get("followers", {}).items()})
        rows.append(q)
        claimed.append(float(w))
    return rows, claimed


def path_from_limits(u: Urdf, joints: list, groups_fn, dense: int) -> tuple:
    """New robots: every finger joint linearly from its open limit to its closed limit; the closed side of each joint
    = the limit that brings the opposing groups' centroids closer (FK, others at mid-range)."""
    mid = {j: (u.joints[j]["lower"] + u.joints[j]["upper"]) / 2 for j in joints}
    closed, opened = {}, {}
    for j in joints:
        lo, hi = u.joints[j]["lower"], u.joints[j]["upper"]
        d = []
        for v in (lo, hi):
            q = dict(mid, **{j: v})
            A, B = groups_fn(q)
            d.append(float(np.linalg.norm(A.mean(0) - B.mean(0))))
        closed[j], opened[j] = (lo, hi) if d[0] < d[1] else (hi, lo)
    rows = [{j: closed[j] + (opened[j] - closed[j]) * s for j in joints} for s in np.linspace(0, 1, dense)]
    return rows, [None] * len(rows)


def sweep(name: str, dense: int = 21, sample: int = 3000) -> dict:
    d = H.descriptor(name)
    gj = json.load(open(os.path.join(H.DIR, f"{name}.json"), encoding="utf-8"))
    u = Urdf(os.path.join(H.DIR, f"{name}.urdf"))
    base = gj["base_link"]
    T_bG = T_of(gj["tcp_in_base"]["xyz"], gj["tcp_in_base"]["rpy"])
    chains = {t: chain(u, t, base) for t in d["tips"]}


    def pts(link, q):
        P = link_pts(u, link, base, q, sample=sample)
        return H.to_G(P, T_bG)

    def groups(q):
        return {t: np.concatenate([pts(lk, q) for lk in chains[t]]) for t in d["tips"]}

    if d.get("path", "table") == "table":
        rows, claimed = path_from_table(gj, dense)
    else:
        js = finger_joints(u, base, d["tips"])

        def gfn(q):
            g = groups(q)
            A, B = d["opposition"][0]
            return np.concatenate([g[t] for t in A]), np.concatenate([g[t] for t in B])
        rows, claimed = path_from_limits(u, js, gfn, dense)
    gaps, gtcp, contacts, zr, front = [], [], [], [], []
    for q in rows:
        g = groups(q)
        front.append(float(min(v[:, 2].min() for v in g.values())))  # deepest finger point along the approach
        gaps.append(H.hand_gap(g, d["opposition"]))
        gtcp.append(H.hand_gap(g, d["opposition"], bands=H.TCP_BAND))
        tips = {t: pts(t, q) for t in d["tips"]}
        tp = H.tip_points(tips, d["opposition"])
        contacts.append({t: v[0].tolist() for t, v in tp.items()})
        zr.append([v[1] for v in tp.values()])
    order_ok = H.path_order_ok(rows, gaps)
    ki, kgap = H.rekey(rows, gaps)
    krows = [rows[i] for i in ki]
    palm = H.to_G(link_pts(u, base, base, {}, sample=sample), T_bG)
    # convergence at the narrowest open row (the collapsed closed row may overlap), axes at the half-open row
    i_mid = ki[int(np.argmin([abs(g - kgap[-1] / 2) for g in kgap]))]
    c_closed = {t: np.asarray(v) for t, v in contacts[ki[1]].items()}
    c_open = {t: np.asarray(v) for t, v in contacts[i_mid].items()}
    fr = H.derived_frame(c_closed, c_open, d["opposition"], palm, z_open=zr[i_mid])
    fc = H.frame_check(fr)
    joints = list(krows[0])
    claimed_k = [claimed[i] for i in ki]
    diffs = [abs(c - g) for c, g in zip(claimed, gaps) if c is not None and np.isfinite(g) and g > H.CLOSED_TOL]
    return {
        "name": name, "joints": joints, "q": [[round(r[j], 6) for j in joints] for r in krows], "gap_m": kgap,
        "gap_tcp_m": [0.0] + [round(max(float(gtcp[i]), 0.0), 5) if np.isfinite(gtcp[i]) else kgap[n + 1]
                              for n, i in enumerate(ki[1:])],
        "claimed_m": [None if c is None else round(c, 5) for c in claimed_k],
        "contacts_G": [{t: [round(x, 5) for x in v] for t, v in contacts[i].items()} for i in ki],
        "tip_front_G": [round(front[i], 5) for i in ki],
        "frame_G": {k: [round(float(x), 5) for x in v] for k, v in fr.items()}, "frame_check": fc,
        "sweep": [{"claimed_m": None if c is None else round(c, 5),
                   "gap_m": None if not np.isfinite(g) else round(float(g), 5),
                   "gap_tcp_m": None if not np.isfinite(t) else round(float(t), 5)}
                  for c, g, t in zip(claimed, gaps, gtcp)],
        "path_monotonic": order_ok, "worst_claimed_diff_mm": round(max(diffs) * 1e3, 2) if diffs else None,
        "max_gap_m": kgap[-1], "old_max_opening_m": gj.get("max_opening_m"),
        "method": {"tool": "tools/onboard/hand_sweep.py", "mesh": "collision", "bands_G_m": H.BANDS, "xh_m": H.XH,
                   "closed_tol_m": H.CLOSED_TOL, "chains": chains, "opposition": d["opposition"],
                   "path": d.get("path", "table"), "sample": sample},
    }


def diag(name: str, sample: int = 3000) -> None:
    """Per link point counts / extents and the per-5-mm-slice gap along z_G at the closed, middle and open rows."""
    d = H.descriptor(name)
    gj = json.load(open(os.path.join(H.DIR, f"{name}.json"), encoding="utf-8"))
    u = Urdf(os.path.join(H.DIR, f"{name}.urdf"))
    base = gj["base_link"]
    T_bG = T_of(gj["tcp_in_base"]["xyz"], gj["tcp_in_base"]["rpy"])
    rows, claimed = path_from_table(gj, 21)
    A, B = d["opposition"][0]
    for i in (0, len(rows) // 2, len(rows) - 1):
        q = rows[i]
        print(f"{name} row {i} claimed {claimed[i]}")
        side = {}
        for s, tips in (("A", A), ("B", B)):
            P = []
            for t in tips:
                for lk in chain(u, t, base):
                    p = H.to_G(link_pts(u, lk, base, q, sample=sample), T_bG)
                    print(f"  {s} {lk}: n={len(p)}" + (f" z[{p[:, 2].min() * 1e3:.1f},{p[:, 2].max() * 1e3:.1f}] "
                                                       f"y[{p[:, 1].min() * 1e3:.1f},{p[:, 1].max() * 1e3:.1f}]"
                                                       if len(p) else ""))
                    P.append(p)
            side[s] = np.concatenate(P) if P else np.zeros((0, 3))
        sl = [(z / 1e3, (z + 5) / 1e3) for z in range(-45, 25, 5)]
        print("  slice gaps mm:", [(round(lo * 1e3), None if not np.isfinite(g := H.opposed_gap(side["A"], side["B"],
                                    ((lo, hi),))) else round(g * 1e3, 1)) for lo, hi in sl])


def main():
    if sys.argv[1:2] == ["diag"]:
        for n in sys.argv[2:]:
            diag(n)
        return
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="+")
    ap.add_argument("--out-dir", default=H.GAP_DIR)
    ap.add_argument("--dense", type=int, default=21)
    ap.add_argument("--sample", type=int, default=3000)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    names = list(H.descriptors()) if a.names == ["all"] else a.names
    for n in names:
        r = sweep(n, a.dense, a.sample)
        json.dump(r, open(os.path.join(a.out_dir, f"{n}.json"), "w"), indent=1)
        print(f"{n}: max gap {r['max_gap_m'] * 1e3:.1f} mm (old max_opening {r['old_max_opening_m']}), rows "
              f"{len(r['gap_m'])}, worst claimed diff {r['worst_claimed_diff_mm']} mm, path monotonic "
              f"{r['path_monotonic']}, frame {r['frame_check']}")
        print("  sweep claimed->measured mm:", [(None if s['claimed_m'] is None else round(s['claimed_m'] * 1e3, 1),
                                                 None if s['gap_m'] is None else round(s['gap_m'] * 1e3, 1))
                                                for s in r["sweep"]])


if __name__ == "__main__":
    main()
