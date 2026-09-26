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


def ws_from_region(region) -> tuple:
    from ..sim.scene import check_ws
    try:
        return check_ws((tuple(region[0]), tuple(region[1])))
    except ValueError as ex:
        raise SkipScene(f"region {region}: {ex}") from ex


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
