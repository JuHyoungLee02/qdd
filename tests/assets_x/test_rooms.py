"""L8X-assets: room background placement (pure)."""

from harvest.sim.assets_x import rooms as RO
from harvest.sim.assets_x import surfaces as S


def room():
    parts = [S.box_mesh((0, 0, -0.1), (5.0, 4.0, 0.0)),  # floor
             S.box_mesh((0, 0, 0), (0.1, 4.0, 2.6)), S.box_mesh((4.9, 0, 0), (5.0, 4.0, 2.6)),
             S.box_mesh((0, 0, 0), (5.0, 0.1, 2.6)), S.box_mesh((0, 3.9, 0), (5.0, 4.0, 2.6)),
             S.box_mesh((0.1, 0.1, 0), (1.5, 1.0, 0.9)),  # counter in a corner
             S.box_mesh((2.0, 2.5, 0.4), (2.8, 3.2, 0.75))]  # a table (floating top: legs omitted)
    return S.merge_meshes(parts)


def test_room_pose_puts_the_zone_in_clear_floor():
    P, F = room()
    pose = RO.room_pose(P, F)
    assert pose is not None and pose["margin"] >= 0
    assert RO.zone_is_clear(P, F, pose)
    bad = dict(pose, pos=[pose["pos"][0] + 2.5, pose["pos"][1], pose["pos"][2]])  # shifted: walls in the zone
    assert not RO.zone_is_clear(P, F, bad)


def test_no_pose_in_a_tiny_room():
    parts = [S.box_mesh((0, 0, -0.1), (1.0, 1.0, 0.0)), S.box_mesh((0, 0, 0), (0.1, 1.0, 2.6))]
    P, F = S.merge_meshes(parts)
    assert RO.room_pose(P, F) is None


def test_occupancy_marks_floor_and_furniture():
    P, F = room()
    x0, y0, nx, ny, open_, fz = RO.occupancy(P, F)
    assert abs(fz) < 1e-6
    i, j = int((0.5 - x0) / S.RES), int((0.5 - y0) / S.RES)  # under the counter
    assert not open_[i, j]
    i, j = int((3.5 - x0) / S.RES), int((1.5 - y0) / S.RES)  # open floor
    assert open_[i, j]


def test_floor_from_the_render_mesh_when_colliders_have_none():
    P, F = room()
    Pc, Fc = S.merge_meshes([S.box_mesh((0, 0, 0), (0.1, 4.0, 2.6)), S.box_mesh((4.9, 0, 0), (5.0, 4.0, 2.6)),
                             S.box_mesh((0.1, 0.1, 0), (1.5, 1.0, 0.9))])  # colliders: no floor
    assert RO.room_pose(Pc, Fc) is None
    pose = RO.room_pose(Pc, Fc, render=(P, F))
    assert pose is not None and RO.zone_is_clear(Pc, Fc, pose, render=(P, F))
