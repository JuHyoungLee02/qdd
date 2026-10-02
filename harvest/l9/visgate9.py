"""L9 v2 build-time visibility gate (owner order 2026-10-02, phase rule 10-03): the VLM must never be asked to
point at something it cannot see, and a training row is only as good as the ONE object its step's command actually
points at (approach: the target -- not yet held; everything else: the place -- the target is in hand and excluded,
same convention as teach_l8d.collect._occ) being visible in the image that row shows. A row is dropped when that
point is (i) outside the image / its centre inside the MARGIN border, (ii) too small to resolve (apparent
footprint radius under MIN_RADIUS_PX), or (iii) more than OCC_MAX of its top face hidden behind something nearer
along the camera's own rendered depth.

Reuses teach_l8d.clutter_x.occlusion (the same 50 % rule already production-tested on L8D) instead of a new
occlusion metric. No instance / segmentation masks are saved per call (an ego call dir holds the RGB images,
head_depth.npz and cams.json only; a third-person call dir adds external<k>_depth.npz / external_cams.json --
tp9.py) -- "hidden behind the robot" and "hidden behind another object" cannot be told apart from depth alone, so
this checks TOTAL occlusion (whichever is nearer occludes). The cheapest add for new episodes would be a second,
robot-hidden depth pass per call, diffed against the normal one, to isolate robot-caused occlusion; that is a
harvest-side change and is NOT made here (L9 spec freeze, L9_PRINCIPLES.md §0) -- flag for the owner, not applied.

Pure functions only (no file I/O, no simulator): callers (build9.py) load the camera (astra_motion.geometry.Cam),
the depth array and the OBJ_GEOM record and pass them in."""
from __future__ import annotations

import math

MARGIN = 0.05  # image border share (= world9._head_sees's default)
OCC_MAX = 0.5  # share of the object's top-face grid hidden behind something nearer (= teach_l8d.clutter_x.OCC_MAX)
# MIN_RADIUS_PX: apparent footprint radius (px) below which an object cannot be resolved. Data-derived (2026-10-02,
# tools/l9/vis_report.py over an L9 v2 sample of pilot1/pilotF/pilotR/pilotG, >=500 episodes/robot where available):
# among in-border, unoccluded target/place points, the 1st percentile of radius_px was ~9-11 px per robot (head
# W=672 H=376, D435-class ~69 deg hfov, workspace 0.4-0.9 m away); 6 px sits below that whole population (keeps the
# drop rate on normal calls near 0) while still catching genuinely degenerate projections (e.g. a far clutter/place
# point near the camera's depth limit). See the per-robot percentiles the sample run printed for the exact numbers.
MIN_RADIUS_PX = 6.0


def obj_half_xy_top(geom: dict, centre) -> tuple:
    """(half_xy for the occlusion grid, top_z) of an OBJ_GEOM record at its recorded centre -- same recipe as
    teach_l8d.collect._occ: 0.6x the smaller of the half extents' x/y, top = centre z + half height (markers /
    virtual surfaces have no real height: top stays at the recorded z)."""
    he = geom.get("half_extents") or (float(geom.get("radius", 0.03)),) * 3
    top = float(centre[2]) + (float(he[2]) if geom.get("shape") not in ("marker", "surface") else 0.0)
    return 0.6 * min(float(he[0]), float(he[1])), top


def point_radius_px(cam, centre, footprint_r: float) -> tuple:
    """(u, v, z, radius_px) of an object's centre projected into cam: radius_px = its real footprint radius at the
    point's own depth (pinhole, cam.fx/fy average). z <= 0 (behind the camera) or a non-finite projection ->
    radius_px is None."""
    from ..astra_motion.geometry import project
    u, v, z = project(cam, centre)
    if not (z > 0 and math.isfinite(u) and math.isfinite(v)):
        return u, v, z, None
    return u, v, z, float(footprint_r) * (float(cam.fx) + float(cam.fy)) / 2.0 / z


def in_border(u, v, z, W: int, H: int, margin: float = MARGIN) -> bool:
    return bool(z > 0 and math.isfinite(u) and math.isfinite(v) and margin * W <= u <= (1 - margin) * W
                and margin * H <= v <= (1 - margin) * H)


def point_visible(cam, depth, geom: dict, centre, margin: float = MARGIN, min_radius_px: float = MIN_RADIUS_PX,
                  occ_max: float = OCC_MAX, ignore: tuple = (), occ_override: float | None = None) -> tuple:
    """-> (ok, reason) of one object centre in one rendered view (cam = astra_motion.geometry.Cam, depth = its
    z-depth array, geom = SC.OBJ_GEOM[k]). reason is one of "out_of_frame", "too_small", "occluded", "ok". ignore
    (teach_l8d.clutter_x.occlusion's convention) = [(centre, half_extents, yaw), ...] surfaces that do not count as
    occluders (e.g. a destination's own rim -- see row_visible). occ_override (owner order 10-03): use this
    occlusion share instead of recomputing one (e.g. labels.jsonl's own "occ", already measured live at collection
    time with the real container box / yaw -- strictly more accurate than the build-time footprint_r approximation)
    -- border / size are still checked against this view's own cam / depth."""
    from ..teach_l8d.clutter_x import occlusion
    footprint_r = float(geom.get("footprint_r") or geom.get("radius") or 0.03)
    u, v, z, r_px = point_radius_px(cam, centre, footprint_r)
    if not in_border(u, v, z, cam.W, cam.H, margin):
        return False, "out_of_frame"
    if r_px is None or r_px < min_radius_px:
        return False, "too_small"
    half_xy, top_z = obj_half_xy_top(geom, centre)
    occ = float(occ_override) if occ_override is not None else occlusion(cam, depth, centre[:2], half_xy, top_z,
                                                                         ignore=ignore)
    if occ >= occ_max:
        return False, "occluded"
    return True, "ok"


def _place_self_ignore(geom: dict, centre) -> list:
    """[(centre, half_extents, 0.0)] approximating a "place" destination's own near rim/wall (teach_l8d.collect._occ
    excludes it via container_boxes(env, ...), which needs a live env; here the yaw is unknown, so the box uses
    footprint_r (= hypot of the true half extents) on both x and y -- a square that contains the true box at ANY
    yaw, rotation-invariant and conservative). Without this, a container's own near edge reads as "occluding" its
    own opening and the gate drops a correctly-labelled placement."""
    fr = float(geom.get("footprint_r") or geom.get("radius") or 0.03)
    he = geom.get("half_extents") or (fr, fr, 0.03)
    return [(tuple(float(v) for v in centre), (fr, fr, max(float(he[2]), 0.001)), 0.0)]


def row_visible(cam, depth, points: list, margin: float = MARGIN, min_radius_px: float = MIN_RADIUS_PX,
               occ_max: float = OCC_MAX) -> tuple:
    """points = [(role, geom, centre), ...] or [(role, geom, centre, occ_override), ...] -- normally ONE entry (the
    point that row's command actually points at: owner order 10-03, see build9._vis_point), kept as a list for
    tests / a multi-point caller. -> (ok, reason, role) of the first point that fails, else (True, "ok", None).
    role == "place" (no occ_override): its own rim does not count as an occluder of its own opening
    (_place_self_ignore)."""
    for item in points:
        role, geom, centre = item[0], item[1], item[2]
        occ_override = item[3] if len(item) > 3 else None
        ignore = _place_self_ignore(geom, centre) if (role == "place" and occ_override is None) else ()
        ok, reason = point_visible(cam, depth, geom, centre, margin, min_radius_px, occ_max, ignore=ignore,
                                   occ_override=occ_override)
        if not ok:
            return False, reason, role
    return True, "ok", None
