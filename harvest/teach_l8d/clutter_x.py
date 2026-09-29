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


P_DISPLAY, P_STACK = 0.85, 0.85  # b4 rich arrangement (user-log 175): most episodes get a display row and / or a stack
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
    out, discs = [], []
    # the far edge first (a shop row facing the robot), then the left / right edges (rows along x) on small tops
    rows_ = [("y", x1, -1, y0, y1), ("x", y1, -1, x0, x1), ("x", y0, 1, x0, x1)]  # (row axis, edge, inward, span)
    for axis, e, sgn, a0, a1 in rows_:
        if len(out) >= DISPLAY_N[0]:
            break
        t = a0 + 0.01 + float(rng.uniform(0.0, 0.03))
        for k in pick:
            if len(out) >= want or k in {p["id"] for p in out}:
                continue
            r = pool[k]["footprint_r"]
            c = e + sgn * (r + 0.01)  # each product hugs the edge
            while t + 2 * r <= a1 - 0.01:  # slide along the row past blocked spots
                tc = t + r
                x, y = (c, tc) if axis == "y" else (tc, c)
                if _clear(x, y, r, discs, keep):
                    out.append({"id": k, "x": round(x, 4), "y": round(y, 4), "yaw": 0.0, "r": r, "arr": "display"})
                    discs.append((x, y, r))
                    t = tc + r + DISPLAY_GAP
                    break
                t += 0.02
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
    n_want = int(rng.integers(1, 3))
    order = sorted(range(len(pairs)), key=lambda i: (pool[pairs[i][0]]["footprint_r"], float(rng.random())))
    for i in order:  # small bases first: they still fit on small furniture tops
        if sum(p["arr"] == "stack" for p in out) >= n_want:
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
                arrange: bool = False, taken_names: set | None = None) -> tuple:
    """-> (layout + clutter entries, placements). fr: footprint radius of each layout object. surface: a furniture
    scene's work surface (b4, change 12: its xy_box / top_z / covered_above; the layout z is its top) instead of the
    visible L8 table box. arrange (user-log 175): + a display row of products along the far edge (p = P_DISPLAY) and
    products stacked on flat-topped products (p = P_STACK); stacked entries are (x, y, yaw, base id)."""
    from ..sim.assets_x.clutter import sample_clutter
    if taken_names is not None:  # change 18 (audit P2): every object name in the scene is unique
        pool = unique_named(pool, taken_names)
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
        do_display, do_stack = rng.random() < P_DISPLAY, rng.random() < P_STACK
        if do_stack:  # first: a base needs a free spot (small bases first), then the display row, then random clutter
            st = _stack_on(rng, pool, extra, used, s["xy_box"], keep, (cov - s["top_z"]) if cov is not None else 1.0)
            extra = extra + st
            keep = keep + [((p["x"] - p["r"], p["x"] + p["r"]), (p["y"] - p["r"], p["y"] + p["r"])) for p in st]
        if do_display:
            row = _display_row(rng, {k: r for k, r in pool.items() if k not in used}, s["xy_box"], keep, h_max)
            used |= {p["id"] for p in row}
            extra = extra + row
            keep = keep + [((p["x"] - p["r"], p["x"] + p["r"]), (p["y"] - p["r"], p["y"] + p["r"])) for p in row]
    res = sample_clutter(scene, {k: r for k, r in pool.items() if k not in used}, seed, n_range=n_range,
                         keep_free=keep)
    placed = extra + list(res["placements"])
    out = dict(layout)
    for p in placed:
        out[p["id"]] = ((float(p["x"]), float(p["y"]), float(p["yaw"]), p["on"]) if p.get("arr") == "stack"
                        else (float(p["x"]), float(p["y"]), float(p["yaw"])))
    return out, placed


P_CONFUSE = 0.20  # change 16 (user-log 180): ~20 % of b4 episodes get look-alike distractors next to the target


def confuser_ids(rows: dict, target: str, n: int = 2, split: str = "train") -> list:
    """Real objects that look like the target: same colour word, height within 3 cm, footprint within 35 %."""
    t = rows.get(target)
    if not t or not t.get("colour"):
        return []
    c = [k for k, r in rows.items() if k != target and r.get("split") == split and r.get("stable")
         and r.get("colour") == t["colour"] and abs(r["height"] - t["height"]) <= 0.03
         and abs(r["footprint_r"] - t["footprint_r"]) <= 0.35 * t["footprint_r"] and r["height"] <= MAX_H + 1e-9]
    c.sort(key=lambda k: (abs(rows[k]["footprint_r"] - t["footprint_r"]), k))
    return c[:n]


def add_confusers(layout: dict, seed: int, target: str, place: str, pool: dict, fr: dict, box,
                  taken_names: set | None = None) -> tuple:
    """With p = P_CONFUSE (seeded): 1-2 look-alikes of the target (confuser_ids, registered in the pool) 8-16 cm from
    it, inside the surface box, clear of every layout object and of the place. -> (layout, ids)."""
    import math

    import numpy as np
    rng = np.random.default_rng([int(seed), 97, 302])
    if rng.random() >= P_CONFUSE or target not in layout:
        return layout, []
    cand = [k for k in confuser_ids(pool, target) if k in pool and k not in layout]
    if taken_names is not None:  # look-alikes must have their own names (audit P2)
        cand = [k for k in cand if not any(names_clash(name_of(pool[k]), s) for s in taken_names)]
    (x0, x1), (y0, y1) = box
    out, ids = dict(layout), []
    m = layout[target]
    for k in cand[:int(rng.integers(1, 3))]:
        r = pool[k]["footprint_r"]
        d0 = max(0.08, r + fr.get(target, 0.05) + 0.02)  # the ring starts where the two footprints clear
        for _ in range(2000):
            a, d = float(rng.uniform(-math.pi, math.pi)), float(rng.uniform(d0, d0 + 0.08))
            q = (m[0] + d * math.cos(a), m[1] + d * math.sin(a))
            if not (x0 + r <= q[0] <= x1 - r and y0 + r <= q[1] <= y1 - r):
                continue
            if place in out and math.dist(q, out[place][:2]) < r + fr.get(place, 0.1) + 0.04:
                continue
            if all(math.dist(q, v[:2]) >= r + fr.get(j, pool.get(j, {}).get("footprint_r", 0.05)) + 0.02
                   for j, v in out.items() if j != place):
                out[k] = (q[0], q[1], float(rng.uniform(-math.pi, math.pi)))
                ids.append(k)
                if taken_names is not None:
                    taken_names.add(name_of(pool[k]))
                break
    return out, ids


def name_of(row: dict) -> str:
    """The name an instruction / prompt uses for a real object (lower case, single spaces)."""
    return " ".join(str(row.get("task_name") or row.get("name") or "").lower().split())


def names_clash(a: str, b: str) -> bool:
    """Two names clash when equal or when one's words are a subset of the other's ("white bottle" / "small white
    bottle": an instruction naming the shorter one would not pick one object; audit 2)."""
    wa, wb = set(a.split()), set(b.split())
    return bool(wa and wb) and (wa <= wb or wb <= wa)


def unique_named(pool: dict, taken: set) -> dict:
    """Pool entries whose name clashes with no taken name and no earlier (sorted) entry (names_clash)."""
    out, seen = {}, set(taken)
    for k in sorted(pool):
        n = name_of(pool[k])
        if n and not any(names_clash(n, s) for s in seen):
            out[k] = pool[k]
            seen.add(n)
    return out


HEAD_TILT0 = 0.785  # rad, 45 deg: the real robot's head pitch (head_joint1)
HEAD_P = 0.17  # share drawn (user-log 181: ~15 % applied; a few fall back after the in-view check, change 19)
HEAD_PAN_MAX, HEAD_TILT_MAX = 0.2618, 0.1745  # +-15 deg pan (head_joint2), +-10 deg tilt (user); the roll is never moved


def head_pose(seed: int, attempt: int = 0) -> dict:
    """Head joints of an L8S episode: default (tilt 0.785, pan 0) or, with p = HEAD_P, a small pose drawn from
    normals truncated at the limits (sd = limit / 2, so most poses stay near the default). attempt > 0: a redraw
    after the in-view check failed, with the range halved per attempt (pilot 2: 2 of 5 draws failed the check)."""
    import numpy as np
    rng = np.random.default_rng([int(seed), 17, 1])
    if rng.random() >= HEAD_P:
        return {"tilt": HEAD_TILT0, "pan": 0.0, "random": False}
    if attempt:
        rng = np.random.default_rng([int(seed), 17, 1, int(attempt)])
    sc = 0.5 ** int(attempt)

    def tn(lim):
        while True:
            v = float(rng.normal(0.0, lim / 2))
            if abs(v) <= lim:
                return v
    return {"tilt": round(HEAD_TILT0 + tn(HEAD_TILT_MAX * sc), 4), "pan": round(tn(HEAD_PAN_MAX * sc), 4),
            "random": True, "attempt": int(attempt)}


ISO0 = 14.0  # film ISO at exposure 1.0 (change-17 calibration: ISO 100 / 50 / 25 -> 32-60 % saturated, 12 -> 0.1 %)
DARK_MEAN = 45.0  # too dark below this mean pixel value
SAT_MAX = 0.10  # audit P1: at most 10 % saturated pixels in the first head frame


GREEN_WORDS = ("moss", "grass", "lichen", "algae", "leaf", "leaves", "forest", "green", "plant", "garden", "jungle", "ivy")


def material_ok(mid: str, rec: dict) -> bool:
    """L8S pilot: no mossy / grassy (green) Poly Haven materials on furniture, floors or walls."""
    words = " ".join([mid] + list(rec.get("categories") or []) + list(rec.get("tags") or [])).lower()
    return not any(w in words for w in GREEN_WORDS)


OCC_MAX = 0.5  # audit 2: a point target hidden for >= 50 % of its footprint samples is occluded
OCC_TOL = 0.03  # m: a depth pixel nearer than the expected depth by more than this hides the sample


def occlusion(cam, depth, centre, half_xy: float, top_z: float, n: int = 5) -> float:
    """Share of an object's visible samples (a grid over its top face at top_z, n x n, radius half_xy) whose
    head-depth pixel is nearer than the sample's own optical depth by > OCC_TOL (something in front of it)."""
    import numpy as np
    from ..astra_motion import geometry as G
    d = np.asarray(depth, float)
    H, W = d.shape[:2]
    hid = tot = 0
    for a in np.linspace(-half_xy, half_xy, n):
        for b in np.linspace(-half_xy, half_xy, n):
            u, v, z = G.project(cam, (centre[0] + a, centre[1] + b, top_z))
            if not (z > 0 and 0 <= u < W and 0 <= v < H):
                continue
            tot += 1
            dz = d[int(v), int(u)]
            hid += bool(np.isfinite(dz) and dz < z - OCC_TOL)
    return 1.0 if tot == 0 else hid / tot


ARM_START = (0.34, -0.25, 0.25)  # change 26: = the INIT_R_ARM TCP (change 21 0.22, -0.42, 0.30 and 24 0.15, -0.42, 0.40 pushed joint1 off its target leaving the start); right TCP start (x, y, z above the work surface), above / right of the
# head camera's view of the work area (main35_recipe.md; the first-frame occlusion check still applies)
if os.environ.get("L8S_ARM_START"):  # change 26 diagnosis only (candidate start poses); unset in production
    ARM_START = tuple(float(v) for v in os.environ["L8S_ARM_START"].split(","))
ARM_DQ = 0.035  # rad per env step for the L8S arm command (measured steps stay <= 0.04 incl. PD overshoot)
ARM_BAND = 0.03  # change 26: L8S arm command within this of the measured joints (no stored error snapping free)
ARM_VMAX_STEP = 0.038  # change 24: right-arm joint speed cap per env step (PhysX max joint velocity = this / dt)
