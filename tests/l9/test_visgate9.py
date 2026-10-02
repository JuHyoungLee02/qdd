"""L9 v2 build-time visibility gate: pure parts (harvest.l9.visgate9). Owner order 2026-10-02: never a training row
whose target / place is out of frame, too small to resolve, or mostly occluded."""
import numpy as np

from harvest.astra_motion.geometry import Cam
from harvest.l9 import visgate9 as VG

W, H = 100, 80
FX = FY = 500.0


def _cam(name="t"):
    return Cam(name=name, W=W, H=H, fx=FX, fy=FY, cx=W / 2, cy=H / 2, R=np.eye(3), t=np.zeros(3))


CUBOID = {"half_extents": (0.03, 0.03, 0.02), "shape": "cuboid", "footprint_r": 0.05}


def _flat_depth(value: float) -> np.ndarray:
    return np.full((H, W), value, dtype=float)


# ---------------------------------------------------------------- point_radius_px / in_border
def test_point_radius_px_centre_and_scale():
    u, v, z, r = VG.point_radius_px(_cam(), (0.0, 0.0, 1.0), 0.05)
    assert z == 1.0 and u == W / 2 and v == H / 2
    assert r == 500.0 * 0.05 / 1.0  # pinhole: radius_px = footprint_r * fx / z (fx == fy here)


def test_point_radius_px_behind_camera_is_none():
    u, v, z, r = VG.point_radius_px(_cam(), (0.0, 0.0, -1.0), 0.05)
    assert z <= 0 and r is None


def test_in_border_margin():
    assert VG.in_border(50, 40, 1.0, W, H, margin=0.05)
    assert not VG.in_border(4, 40, 1.0, W, H, margin=0.05)  # left of the 5 % border
    assert not VG.in_border(50, 3, 1.0, W, H, margin=0.05)  # above the 5 % border
    assert not VG.in_border(50, 40, -1.0, W, H, margin=0.05)  # behind the camera


# ---------------------------------------------------------------- point_visible
def test_point_visible_ok_when_centred_sized_and_clear():
    depth = _flat_depth(5.0)  # nothing nearer than the point anywhere: unoccluded
    ok, reason = VG.point_visible(_cam(), depth, CUBOID, (0.0, 0.0, 1.0))
    assert (ok, reason) == (True, "ok")


def test_point_visible_out_of_frame():
    depth = _flat_depth(5.0)
    ok, reason = VG.point_visible(_cam(), depth, CUBOID, (-0.2, 0.0, 1.0))  # u ~= -50: left of the image
    assert (ok, reason) == (False, "out_of_frame")


def test_point_visible_too_small():
    depth = _flat_depth(5.0)
    tiny = dict(CUBOID, footprint_r=0.005)  # 5 mm footprint at z=2 m -> radius_px = 1.25 < MIN_RADIUS_PX
    ok, reason = VG.point_visible(_cam(), depth, tiny, (0.0, 0.0, 2.0))
    assert (ok, reason) == (False, "too_small")


def test_point_visible_occluded():
    depth = _flat_depth(0.5)  # the whole image reads nearer than the object's top (1.02 m): fully hidden
    ok, reason = VG.point_visible(_cam(), depth, CUBOID, (0.0, 0.0, 1.0))
    assert (ok, reason) == (False, "occluded")


def test_point_visible_occlusion_threshold_is_the_shared_l8d_rule():
    assert VG.OCC_MAX == 0.5


# ---------------------------------------------------------------- row_visible
def test_row_visible_drops_on_first_failing_point():
    depth = _flat_depth(5.0)
    points = [("tgt", CUBOID, (-0.2, 0.0, 1.0)), ("place", CUBOID, (0.0, 0.0, 1.0))]
    ok, reason, role = VG.row_visible(_cam(), depth, points)
    assert (ok, reason, role) == (False, "out_of_frame", "tgt")


def test_row_visible_place_ignores_its_own_rim():
    # the occluder surface sits almost exactly where the place point's own top is (dz close to z): a destination's
    # own near rim, not an external occluder -- must not drop the row (teach_l8d.collect._occ's container_boxes
    # convention, replicated rotation-invariantly with footprint_r since there is no live env / yaw at build time).
    depth = _flat_depth(0.98)  # object top z = 1.02 (centre 1.0 + half height 0.02): dz < z - OCC_TOL, but the
    points = [("place", CUBOID, (0.0, 0.0, 1.0))]  # back-projected hit still lands within the place's own footprint
    ok, reason, role = VG.row_visible(_cam(), depth, points)
    assert (ok, reason, role) == (True, "ok", None)


def test_row_visible_place_still_drops_for_a_real_occluder():
    depth = _flat_depth(0.5)  # far nearer than the object's own rim: a real occluder, not the container's own wall
    points = [("place", CUBOID, (0.0, 0.0, 1.0))]
    ok, reason, role = VG.row_visible(_cam(), depth, points)
    assert (ok, reason, role) == (False, "occluded", "place")


def test_row_visible_tgt_has_no_self_ignore():
    # the same near-rim depth that is excused for "place" still counts against "tgt" (only a destination's own
    # rim is exempt -- a target is never exempted from its own occluder check)
    depth = _flat_depth(0.98)
    points = [("tgt", CUBOID, (0.0, 0.0, 1.0))]
    ok, reason, role = VG.row_visible(_cam(), depth, points)
    assert (ok, reason, role) == (False, "occluded", "tgt")


def test_row_visible_ok_when_every_point_passes():
    depth = _flat_depth(5.0)
    points = [("tgt", CUBOID, (0.0, 0.0, 1.0)), ("place", CUBOID, (0.01, 0.0, 1.0))]
    ok, reason, role = VG.row_visible(_cam(), depth, points)
    assert (ok, reason, role) == (True, "ok", None)


# ---------------------------------------------------------------- obj_half_xy_top
def test_obj_half_xy_top_markers_keep_their_recorded_z():
    marker = {"shape": "marker", "half_extents": (0.04, 0.04, 0.001), "radius": 0.04}
    half_xy, top = VG.obj_half_xy_top(marker, (0.1, 0.2, 0.78))
    assert top == 0.78  # no height added for a marker / virtual surface
    assert half_xy == 0.6 * 0.04


def test_obj_half_xy_top_adds_half_height_for_real_objects():
    half_xy, top = VG.obj_half_xy_top(CUBOID, (0.1, 0.2, 0.78))
    assert top == 0.78 + 0.02
    assert half_xy == 0.6 * 0.03
