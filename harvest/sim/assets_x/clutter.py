"""Cluttered scenes (pure): 5-12 real objects on the furniture tops of a sample_scene, no overlap, no tipping.

Only objects whose Isaac settle check passed (stable True) are used, each in its checked resting pose (upright or
lying); their footprint discs (footprint_r + GAP) never overlap each other, any keep-free box (the task's target /
place region, given by the caller) or a surface edge (centre >= footprint_r + EDGE inside the surface box). Open
surfaces or covered ones with >= MIN_CLEAR and >= object height + 5 cm of room (shelf tiers hold clutter too);
container floors only when allow_bins.
Positions are rejection-sampled per seed (np.random.default_rng([seed, 97, 300])); a scene that cannot hold n objects
gets as many as fit and reports the shortfall.
"""
from __future__ import annotations

import math

import numpy as np

GAP = 0.015
EDGE = 0.01
MIN_CLEAR = 0.25
TRIES = 400
SETTLE_TILT_MAX = 5.0  # clutter uses only objects that settled within 5 deg (k1: 10-deg passes tipped later)


def _free(x, y, r, placed, keep_free):
    for p in placed:
        if math.hypot(x - p["x"], y - p["y"]) < r + p["r"] + GAP:
            return False
    for (x0, x1), (y0, y1) in keep_free:
        dx = max(x0 - x, 0.0, x - x1)
        dy = max(y0 - y, 0.0, y - y1)
        if math.hypot(dx, dy) < r + GAP:
            return False
    return True


def sample_clutter(scene: dict, objects: dict, seed: int, n_range=(5, 12), keep_free=(), allow_bins=False,
                   split: str = "train") -> dict:
    """-> {n_target, n_placed, placements [{id, surface, x, y, top_z, yaw, z_root, pose, task_name}], shortfall}.
    z_root = surface top + root_above_bottom (then rotate by spawn_quat_wxyz and yaw about z)."""
    rng = np.random.default_rng([int(seed), 97, 300])
    surfs = [s for s in scene["surfaces"] if (s.get("covered_above") is None or
                                               s["covered_above"] - s["top_z"] >= MIN_CLEAR)
             and (allow_bins or not s.get("container"))]
    pool = sorted(k for k, o in objects.items() if o.get("stable") and o.get("split") == split
                  and (o.get("settle") or {}).get("tilt_deg", 0.0) <= SETTLE_TILT_MAX and o.get("clutter_ok", True))
    n = int(rng.integers(n_range[0], n_range[1] + 1))
    out = {"n_target": n, "placements": []}
    if not surfs or not pool:
        out.update(n_placed=0, shortfall=n)
        return out
    area = np.array([max(s["area"], 1e-6) for s in surfs])
    placed = []
    order = rng.permutation(len(pool))
    for oi in order:
        if len(placed) >= n:
            break
        k = pool[int(oi)]
        o = objects[k]
        r = float(o["footprint_r"])
        for _ in range(TRIES // 10):
            s = surfs[int(rng.choice(len(surfs), p=area / area.sum()))]
            (x0, x1), (y0, y1) = s["xy_box"]
            if x1 - x0 < 2 * (r + EDGE) or y1 - y0 < 2 * (r + EDGE) or (
                    s.get("covered_above") is not None and s["covered_above"] - s["top_z"] < o["height"] + 0.05):
                continue
            x = float(rng.uniform(x0 + r + EDGE, x1 - r - EDGE))
            y = float(rng.uniform(y0 + r + EDGE, y1 - r - EDGE))
            if _free(x, y, r, placed, keep_free):
                placed.append({"id": k, "surface": s["id"], "x": round(x, 4), "y": round(y, 4), "r": r,
                               "top_z": s["top_z"], "yaw": round(float(rng.uniform(-math.pi, math.pi)), 4),
                               "z_root": round(s["top_z"] + o["root_above_bottom"], 4), "pose": o.get("pose"),
                               "task_name": o.get("task_name")})
                break
    out["placements"] = placed
    out.update(n_placed=len(placed), shortfall=max(0, n - len(placed)))
    return out


def overlaps(placements) -> list:
    """Pairs of placements whose footprint discs overlap (a check for tests / generated scenes)."""
    bad = []
    for i, a in enumerate(placements):
        for b in placements[i + 1:]:
            if math.hypot(a["x"] - b["x"], a["y"] - b["y"]) < a["r"] + b["r"] + GAP - 1e-9:
                bad.append((a["id"], b["id"]))
    return bad
