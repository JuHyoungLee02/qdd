"""L8-X furniture scenes in the generator (pure part; the scene API is harvest.sim.assets_x, helper L8X-assets).

One episode = one furniture scene (sample_scene(kind, seed, reach, lift="auto")): the task happens on ONE support
surface of it -- the usable surface (a placement region at the scene's lift) with the largest region; that surface's
top is the episode's table height (prompt table line, truth heights, executor box, object spawn z) and its region is
the layout box. Layout objects whose footprint leaves the surface's box are dropped (they would fall off); a scene
whose best region is narrower than the layout needs (scene.check_ws) is skipped (SkipScene, logged)."""
from __future__ import annotations

import math


class SkipScene(Exception):
    pass


MESH_TABLES = ("assets_table.json", "assets_cyclo.json", "assets_ph.json")  # harvest/sim/assets_x (helper L8X-assets;
# assets_ph = Poly Haven display fixtures, tag "ph", change 17)
B4_ASSETS = "docs/stage3/l8x_b4_assets.json"  # helper's L8S lists (pieces passing the per-piece gate, fixtures)


def passed_pieces(mesh: dict) -> dict:
    """L8S: the mesh pieces of the helper's gate lists (furniture_pieces.pass + display_fixtures.fixtures); cyclo_lab
    pieces (gated as a kind in change 7) stay."""
    import json
    import os
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), B4_ASSETS)
    a = json.load(open(p))
    fix = a["display_fixtures"]["fixtures"]
    ok = set(a["furniture_pieces"]["pass"]) | set(fix if isinstance(fix, list) else fix.keys())
    return {n: m for n, m in mesh.items() if n in ok or m.get("tag") == "cyclo"}


def load_mesh_assets(directory: str) -> dict:
    """The helper's licensed mesh tables merged: {name: asset} (THOR + cyclo_lab)."""
    import json
    import os
    out = {}
    for f in MESH_TABLES:
        p = os.path.join(directory, f)
        if os.path.exists(p):
            out.update(json.load(open(p))["assets"])
    return out


def is_mesh_kind(kind: str) -> bool:
    return "_" in kind and kind.split("_", 1)[0] in ("thor", "cyclo", "ph")


def mesh_subset(mesh_assets: dict, kind: str, split: str) -> dict:
    """Only the pieces a process with this kind / split can draw (loading every piece as a prim is heavy)."""
    tag, cat = kind.split("_", 1)
    return {n: a for n, a in mesh_assets.items()
            if a.get("tag", "thor") == tag and a["category"] == cat and a["split"] == split}


ROOMS_TABLE = "rooms_ithor.json"
ROOM_OOD_SHARE = 0.2


def room_split(name: str) -> str:
    """iTHOR rooms held out for OOD-S by name hash (20 %); the rest may appear in training scenes."""
    import hashlib
    u = int(hashlib.sha256(("l8x-room:" + name).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return "ood" if u < ROOM_OOD_SHARE else "train"


def rooms_of(directory: str, split: str) -> dict:
    import json
    import os
    rooms = json.load(open(os.path.join(directory, ROOMS_TABLE)))["rooms"]
    return {n: r for n, r in rooms.items() if room_split(n) == split}


def choose_surface(scene: dict) -> tuple:
    """-> (surface dict, region [[x0, x1], [y0, y1]]) of the usable surface with the largest region area."""
    by_id = {s["id"]: s for s in scene["surfaces"]}
    best = None
    for p in scene.get("placement_regions") or []:
        r = p.get("region")
        if r is None or p["surface"] not in by_id:
            continue
        area = (r[0][1] - r[0][0]) * (r[1][1] - r[1][0])
        if best is None or area > best[0]:
            best = (area, by_id[p["surface"]], [list(r[0]), list(r[1])])
    if best is None:
        raise SkipScene(f"{scene['kind']} seed {scene['seed']}: no usable surface at lift {scene.get('lift')}")
    return best[1], best[2]


def choose_two_surfaces(scene: dict, min_rise: float = 0.02) -> tuple:
    """Cross-surface task: -> (lower surface A, its region, higher surface B, its region); A = the usable surface
    with the largest region among those that have a usable surface at least min_rise higher; B = the largest such
    higher one. SkipScene when the scene has no such pair."""
    by_id = {s["id"]: s for s in scene["surfaces"]}
    regs = []
    for p in scene.get("placement_regions") or []:
        r = p.get("region")
        if r is not None and p["surface"] in by_id:
            regs.append((by_id[p["surface"]], [list(r[0]), list(r[1])],
                         (r[0][1] - r[0][0]) * (r[1][1] - r[1][0])))
    best = None
    for a, ra, area_a in regs:
        ups = [(b, rb, ab) for b, rb, ab in regs if b["top_z"] >= a["top_z"] + min_rise]
        if not ups:
            continue
        b, rb, ab = max(ups, key=lambda t: t[2])
        if best is None or area_a > best[0]:
            best = (area_a, a, ra, b, rb)
    if best is None:
        raise SkipScene(f"{scene['kind']} seed {scene['seed']}: no pair of usable surfaces {min_rise} m apart")
    return best[1:]


MIN_DIAG = 0.20  # target and place need >= 0.16 m apart (task_layout): a narrower box cannot hold a layout


def choose_container(scene: dict) -> tuple:
    """Container task: -> (work surface A, region, container surface B, region); B = a usable container surface
    (surface["container"]), A = the largest usable non-container surface. SkipScene if either is missing."""
    by_id = {s["id"]: s for s in scene["surfaces"]}
    regs = []
    for p in scene.get("placement_regions") or []:
        r = p.get("region")
        if r is not None and p["surface"] in by_id:
            regs.append((by_id[p["surface"]], [list(r[0]), list(r[1])], (r[0][1] - r[0][0]) * (r[1][1] - r[1][0])))
    boxes = [t for t in regs if t[0].get("container")]
    work = [t for t in regs if not t[0].get("container")]
    if not boxes or not work:
        raise SkipScene(f"{scene['kind']} seed {scene['seed']}: no usable container + work surface")
    a = max(work, key=lambda t: t[2])
    b = max(boxes, key=lambda t: t[2])
    return a[0], a[1], b[0], b[1]


LIFT_TOL_M = 0.04  # the lift joint sags ~2.6 cm under load; more = the lift was not applied


def check_lift(set_q: float, measured_q: float, tol: float = LIFT_TOL_M) -> None:
    """After reset: a scene whose measured lift is off by more than tol is skipped (reason kept), not fatal."""
    if abs(measured_q - set_q) > tol:
        raise SkipScene(f"lift not applied: set {set_q:+.4f}, measured {measured_q:+.4f}")


def ws_from_region(region) -> tuple:
    from ..sim.scene import check_ws
    try:
        ws = check_ws((tuple(region[0]), tuple(region[1])))
    except ValueError as ex:
        raise SkipScene(f"region {region}: {ex}") from ex
    (x0, x1), (y0, y1) = ws
    if math.hypot(x1 - x0, y1 - y0) < MIN_DIAG:
        raise SkipScene(f"region {region}: diagonal < {MIN_DIAG} m")
    return ws


def on_surface(xy, footprint_r: float, surface: dict, margin: float = 0.01) -> bool:
    (x0, x1), (y0, y1) = surface["xy_box"]
    return (x0 + footprint_r + margin <= xy[0] <= x1 - footprint_r - margin
            and y0 + footprint_r + margin <= xy[1] <= y1 - footprint_r - margin)


def filter_layout(layout: dict, surface: dict, keep=()) -> tuple:
    """Drop layout objects (not in keep) whose footprint is not on the surface -> (layout, dropped ids). Objects
    in keep (target, place, steps) must be on it, else SkipScene."""
    from ..sim.scene import OBJ_GEOM, X_VISUAL_ONLY
    out, dropped = {}, []
    for k, v in layout.items():
        if k in ("o19", "o20"):  # the place surface itself (a different surface, set by the runner)
            out[k] = v
            continue
        fr = 0.0 if k in X_VISUAL_ONLY else OBJ_GEOM[k]["footprint_r"]
        if on_surface(v[:2], min(fr, 0.06), surface):
            out[k] = v
        elif k in keep:
            raise SkipScene(f"task object {k} at {tuple(round(c, 3) for c in v[:2])} is off the surface")
        else:
            dropped.append(k)
    return out, dropped


def summary(scene: dict, surface: dict, region, dropped) -> dict:
    return {"kind": scene["kind"], "kind_split": scene.get("kind_split"), "seed": scene["seed"],
            "lift": scene.get("lift"), "surface": {k: surface[k] for k in ("id", "kind", "top_z", "xy_box")
                                                   if k in surface},
            "region": region, "n_parts": len(scene["furniture"]) + len(scene["walls"]), "dropped": dropped,
            "params": scene.get("params")}


assert math.isfinite(0.0)
