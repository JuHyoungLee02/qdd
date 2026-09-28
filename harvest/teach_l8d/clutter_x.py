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


def pool_for(rows: dict, key: str, n: int = 30, split: str = "train", exclude=()) -> dict:
    """n objects for one process, chosen by a stable hash of (key, id): train split, stable, height <= MAX_H."""
    ok = [k for k, r in rows.items() if r.get("split") == split and r.get("stable") and r["height"] <= MAX_H + 1e-9
          and r.get("clutter_ok", True) and k not in set(exclude)]
    ok.sort(key=lambda k: hashlib.sha256(f"l8x-clutter:{key}:{k}".encode()).hexdigest())
    return {k: rows[k] for k in ok[:n]}


def add_clutter(layout: dict, seed: int, pool: dict, ws, fr: dict, n_range=(5, 12)) -> tuple:
    """-> (layout + clutter entries, placements). fr: footprint radius of each layout object."""
    from ..sim.assets_x.clutter import sample_clutter
    (x0, x1), (y0, y1) = TABLE_BOX
    scene = {"surfaces": [{"id": "table", "top_z": 0.0, "xy_box": [[x0, x1], [y0, y1]],
                           "area": (x1 - x0) * (y1 - y0)}]}
    keep = [((ws[0][0] - MARGIN, ws[0][1] + MARGIN), (ws[1][0] - MARGIN, ws[1][1] + MARGIN))]
    for k, v in layout.items():
        r = fr[k] + LAYOUT_GAP
        keep.append(((v[0] - r, v[0] + r), (v[1] - r, v[1] + r)))
    res = sample_clutter(scene, {k: r for k, r in pool.items() if k not in layout}, seed, n_range=n_range,
                         keep_free=keep)
    out = dict(layout)
    for p in res["placements"]:
        out[p["id"]] = (float(p["x"]), float(p["y"]), float(p["yaw"]))
    return out, res["placements"]
