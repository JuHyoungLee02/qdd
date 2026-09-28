"""b3 cluttered table scenes (prereg_l8d change 11), pure part: real objects (helper L8X-assets objects_real.json,
GSO + THOR, objv-compatible rows) scattered on the table around the task layout with clutter.sample_clutter.

A process registers a fixed pool of objects (mesh prims must exist before make_env): pool_for(rows, bucket key, n).
Per episode add_clutter puts 5-12 of them on the visible table outside the workspace box (+ MARGIN) and clear of
every layout object; the layout entries are canonical (x, y, yaw) like the Objaverse targets."""
from __future__ import annotations

import hashlib
import os

MAX_H = 0.14  # tallest clutter object (the carry height is ~10 cm above the tallest target)
TABLE_BOX = ((0.30, 0.78), (-0.56, 0.30))  # visible part of the L8 table (robot frame)
MARGIN = 0.04  # around the workspace box (target / place / finger sweep)
LAYOUT_GAP = 0.02
TABLE = "objects_real.json"


def load_real(path: str | None = None) -> dict:
    import json
    p = path or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sim", "assets_x", TABLE)
    return json.load(open(p))["objects"]


def pool_for(rows: dict, key: str, n: int = 30, split: str = "train", exclude=(), n_base: int = 0) -> dict:
    """n objects for one process, chosen by a stable hash of (key, id): train split, stable, height <= MAX_H."""
    ok = [k for k, r in rows.items() if r.get("split") == split and r.get("stable") and r["height"] <= MAX_H + 1e-9
          and r.get("clutter_ok", True) and k not in set(exclude)]
    ok.sort(key=lambda k: hashlib.sha256(f"l8x-clutter:{key}:{k}".encode()).hexdigest())
    if not n_base:
        return {k: rows[k] for k in ok[:n]}
    base = [k for k in ok if rows[k].get("top_surface")][:n_base]  # stacking bases (flat top, helper table)
    goods = [k for k in ok if k not in set(base) and _shelf_good(rows[k])][:n_base]  # display-row products
    rest = [k for k in ok if k not in set(base) | set(goods)][:max(0, n - len(base) - len(goods))]
    return {k: rows[k] for k in base + goods + rest}


def _shelf_good(r: dict) -> bool:
    """A product that stands in a shop row: upright and compact (footprint radius <= 5 cm)."""
    return r.get("pose") == "upright" and r["footprint_r"] <= 0.05


P_DISPLAY, P_STACK = 0.75, 0.75  # b4 rich arrangement (user-log 175): most episodes get a display row and / or a stack
DISPLAY_N = (3, 6)
DISPLAY_GAP = 0.012


def _clear(x, y, r, discs, keep) -> bool:
    import math
    if any(math.hypot(x - a, y - b) < r + q + GAP_X for a, b, q in discs):
        return False
    for (kx0, kx1), (ky0, ky1) in keep:
        dx, dy = max(kx0 - x, 0.0, x - kx1), max(ky0 - y, 0.0, y - ky1)
        if math.hypot(dx, dy) < r + GAP_X:
            return False
    return True


GAP_X = 0.015  # = clutter.GAP


def _display_row(rng, pool: dict, box, keep, h_max: float) -> list:
    """A shop-shelf row: 3-6 products side by side along the far edge of the surface, facing the robot."""
    (x0, x1), (y0, y1) = box
    ids = [k for k in sorted(pool) if pool[k]["height"] <= h_max and _shelf_good(pool[k])]
    if len(ids) < DISPLAY_N[0]:
        return []
    want = int(rng.integers(DISPLAY_N[0], DISPLAY_N[1] + 1))
    pick = [ids[int(i)] for i in rng.permutation(len(ids))]
    rmax = max(pool[k]["footprint_r"] for k in pick)
    x = x1 - rmax - 0.01
    y = y0 + 0.01 + float(rng.uniform(0.0, 0.05))
    out, discs = [], []
    for k in pick:
        if len(out) >= want:
            break
        r = pool[k]["footprint_r"]
        while y + 2 * r <= y1 - 0.01:  # slide along the row past blocked spots
            yc = y + r
            if _clear(x, yc, r, discs, keep):
                out.append({"id": k, "x": round(x, 4), "y": round(yc, 4), "yaw": 0.0, "r": r, "arr": "display"})
                discs.append((x, yc, r))
                y = yc + r + DISPLAY_GAP
                break
            y += 0.02
    return out


def _stack_on(rng, pool: dict, placed: list, used: set, box, keep, h_room: float) -> list:
    """1-2 products standing on other products (base_ok / stack_top_ok of the helper's stacking rules). A base is an
    already placed product, else a base product put on a free spot of the surface first."""
    from .xnew import base_ok, stack_top_ok
    (x0, x1), (y0, y1) = box
    pairs = [(b, t) for b in sorted(pool) for t in sorted(pool) if b != t and pool[b].get("top_surface")
             and t not in used and stack_top_ok(pool[t]) and base_ok(pool[b], pool[t])
             and pool[b]["height"] + pool[t]["height"] + 0.05 <= h_room]
    out = []
    discs = [(p["x"], p["y"], p["r"]) for p in placed]
    by_id = {p["id"]: p for p in placed}
    for i in rng.permutation(len(pairs)):
        if len(out) >= int(rng.integers(1, 3)):
            break
        b, t = pairs[int(i)]
        if t in used or (b in used and b not in by_id):
            continue
        if b not in by_id:  # put the base on a free spot first
            r = pool[b]["footprint_r"]
            for _ in range(200):
                x, y = float(rng.uniform(x0 + r + 0.01, x1 - r - 0.01)), float(rng.uniform(y0 + r + 0.01, y1 - r - 0.01))
                if _clear(x, y, r, discs, keep):
                    by_id[b] = {"id": b, "x": round(x, 4), "y": round(y, 4), "yaw": 0.0, "r": r, "arr": "base"}
                    out.append(by_id[b])
                    discs.append((x, y, r))
                    used.add(b)
                    break
            else:
                continue
        p = by_id[b]
        used.add(t)
        out.append({"id": t, "x": p["x"], "y": p["y"], "yaw": p["yaw"], "r": pool[t]["footprint_r"], "arr": "stack",
                    "on": b})
    return out


def add_clutter(layout: dict, seed: int, pool: dict, ws, fr: dict, n_range=(5, 12), surface: dict | None = None,
                arrange: bool = False) -> tuple:
    """-> (layout + clutter entries, placements). fr: footprint radius of each layout object. surface: a furniture
    scene's work surface (b4, change 12: its xy_box / top_z / covered_above; the layout z is its top) instead of the
    visible L8 table box. arrange (user-log 175): + a display row of products along the far edge (p = P_DISPLAY) and
    products stacked on flat-topped products (p = P_STACK); stacked entries are (x, y, yaw, base id)."""
    from ..sim.assets_x.clutter import sample_clutter
    if surface is None:
        (x0, x1), (y0, y1) = TABLE_BOX
        s = {"id": "table", "top_z": 0.0, "xy_box": [[x0, x1], [y0, y1]]}
    else:
        if "xy_box" not in surface or "top_z" not in surface:
            raise ValueError(f"surface {surface.get('id')}: needs xy_box and top_z")
        (x0, x1), (y0, y1) = surface["xy_box"]
        s = {k: surface[k] for k in ("id", "top_z", "xy_box", "covered_above") if surface.get(k) is not None}
    scene = {"surfaces": [dict(s, area=(x1 - x0) * (y1 - y0))]}
    keep = [((ws[0][0] - MARGIN, ws[0][1] + MARGIN), (ws[1][0] - MARGIN, ws[1][1] + MARGIN))]
    for k, v in layout.items():
        r = fr[k] + LAYOUT_GAP
        keep.append(((v[0] - r, v[0] + r), (v[1] - r, v[1] + r)))
    extra, used = [], set(layout)
    if arrange:
        import numpy as np
        rng = np.random.default_rng([int(seed), 97, 301])
        cov = s.get("covered_above")
        h_max = min(MAX_H, (cov - s["top_z"] - 0.05) if cov is not None else MAX_H)
        if rng.random() < P_DISPLAY:
            extra = _display_row(rng, {k: r for k, r in pool.items() if k not in used}, s["xy_box"], keep, h_max)
            used |= {p["id"] for p in extra}
            keep = keep + [((p["x"] - p["r"], p["x"] + p["r"]), (p["y"] - p["r"], p["y"] + p["r"])) for p in extra]
        if rng.random() < P_STACK:  # before the random clutter: a base needs a free spot
            st = _stack_on(rng, pool, extra, used, s["xy_box"], keep, (cov - s["top_z"]) if cov is not None else 1.0)
            extra = extra + st
            keep = keep + [((p["x"] - p["r"], p["x"] + p["r"]), (p["y"] - p["r"], p["y"] + p["r"])) for p in st]
    res = sample_clutter(scene, {k: r for k, r in pool.items() if k not in used}, seed, n_range=n_range,
                         keep_free=keep)
    placed = extra + list(res["placements"])
    out = dict(layout)
    for p in placed:
        out[p["id"]] = ((float(p["x"]), float(p["y"]), float(p["yaw"]), p["on"]) if p.get("arr") == "stack"
                        else (float(p["x"]), float(p["y"]), float(p["yaw"])))
    return out, placed
