"""L9 v2 external (world-fixed) paired cameras: pure parts (harvest.l9.ext9)."""
import json
import math

import numpy as np
import pytest

from harvest.l9 import ext9 as E
from harvest.l9 import hcam9 as HC

M = np.array([[0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0]])  # world_isaac.WORLD_CONV_TO_OPTICAL


def _ctx(boxes=(), zone=E.ROOM_ZONE):
    ws = [np.array([0.46, -0.23, 0.80]), np.array([0.40, -0.05, 0.80])]
    robot = [np.array([0.10, 0.03, 1.40]), np.array([0.34, -0.25, 1.03])]
    return E.Ctx(look_ws=np.mean(ws, axis=0), robot_pts=robot, ws_pts=ws, boxes=list(boxes), zone=zone,
                 surface_z=0.78)


# ---------------------------------------------------------------- coin
def test_coin_deterministic_and_rate():
    assert [E.coin(s, 0.3) for s in range(50)] == [E.coin(s, 0.3) for s in range(50)]
    rate = np.mean([E.coin(s, 0.3) for s in range(4000)])
    assert 0.27 < rate < 0.33
    assert not any(E.coin(s, 0.0) for s in range(200)) and all(E.coin(s, 1.0) for s in range(200))


def test_coin_independent_of_hcam_coin():
    a = np.array([E.coin(s, 0.5) for s in range(2000)])
    b = np.array([HC.coin(s) == "rand" for s in range(2000)])
    assert abs(np.mean(a == b) - 0.5) < 0.05


def test_n_cams():
    assert {E.n_cams(s, 1) for s in range(100)} == {1}
    two = [E.n_cams(s, 2) for s in range(400)]
    assert set(two) == {1, 2} and 0.35 < np.mean(np.array(two) == 2) < 0.65


# ---------------------------------------------------------------- geometry
def test_look_at_rotation_points_the_axis():
    t, p = np.array([1.5, 0.8, 1.6]), np.array([0.4, -0.2, 0.8])
    R = E.look_at(t, p)
    f = (p - t) / np.linalg.norm(p - t)
    assert np.allclose(R[:, 0], f) and abs(R[2, 1]) < 1e-9  # no roll: camera left stays horizontal
    assert np.allclose(R.T @ R, np.eye(3)) and np.linalg.det(R) > 0
    assert R[2, 2] > 0  # camera up has a positive world z


def test_project_matches_head_convention():
    t, p = np.array([1.5, 0.0, 1.5]), np.array([0.5, 0.0, 0.8])
    R = E.look_at(t, p)
    u, v, z = E.project(R, t, E.K_of(70.0), p)
    assert z > 0 and u == pytest.approx(E.W / 2) and v == pytest.approx(E.H / 2)
    # optical R recorded in cams.json = world-convention R @ WORLD_CONV_TO_OPTICAL
    Ro = E.optical(R)
    assert np.allclose(Ro, R @ M)


def test_ray_box_blocking():
    box = {"pos": [1.0, 0.0, 0.5], "size": [0.2, 0.2, 1.0], "yaw": 0.0}
    assert E.ray_blocked(np.array([2.0, 0.0, 0.5]), np.array([0.0, 0.0, 0.5]), [box])
    assert not E.ray_blocked(np.array([2.0, 0.0, 1.5]), np.array([0.0, 0.0, 1.5]), [box])
    rot = dict(box, yaw=math.pi / 4)
    assert E.ray_blocked(np.array([1.0, 1.0, 0.5]), np.array([1.0, -1.0, 0.5]), [rot])
    assert not E.ray_blocked(np.array([1.2, 1.0, 0.5]), np.array([1.2, -1.0, 0.5]), [rot])  # 0.2 off centre


def test_inside_box_margin():
    box = {"pos": [1.0, 0.0, 0.4], "size": [0.6, 0.6, 0.8], "yaw": 0.0}
    assert E.inside_any(np.array([1.0, 0.0, 0.5]), [box], 0.1)
    assert E.inside_any(np.array([1.35, 0.0, 0.5]), [box], 0.1)
    assert not E.inside_any(np.array([1.5, 0.0, 0.5]), [box], 0.1)
    assert not E.inside_any(np.array([1.0, 0.0, 1.6]), [box], 0.1)


# ---------------------------------------------------------------- draws
@pytest.mark.parametrize("seed", range(40))
def test_draw_sees_workspace_and_robot(seed):
    c = _ctx()
    d = E.draw(seed, 0, c)
    assert d is not None
    R, t, K = E.pose_of(d)
    for p in c.ws_pts + c.robot_pts:
        u, v, z = E.project(R, t, K, p)
        assert z > 0.3
        assert E.MARGIN * E.W <= u <= (1 - E.MARGIN) * E.W and E.MARGIN * E.H <= v <= (1 - E.MARGIN) * E.H
    (x0, x1), (y0, y1) = E.ROOM_ZONE
    assert x0 <= t[0] <= x1 and y0 <= t[1] <= y1
    assert d["kind"] in E.KINDS and E.HFOV[0] <= d["hfov"] <= E.HFOV[1]
    assert E.H_RANGE[d["kind"]][0] <= t[2] <= E.H_RANGE[d["kind"]][1]
    assert not E.inside_any(t, [E.robot_box()], 0.0)
    json.dumps(d)  # meta-safe


def test_draw_deterministic_and_varies():
    c = _ctx()
    a, b = E.draw(7, 0, c), E.draw(7, 0, c)
    assert a == b
    poses = {tuple(E.draw(s, 0, c)["pos"]) for s in range(30)}
    assert len(poses) == 30
    kinds = {E.draw(s, 0, c)["kind"] for s in range(200)}
    assert kinds == set(E.KINDS)
    assert E.draw(7, 1, c) != a  # a redraw is a new pose


def test_second_camera_differs_in_azimuth():
    c = _ctx()
    for s in range(30):
        a = E.draw(s, 0, c, cam=0)
        b = E.draw(s, 0, c, cam=1, avoid=[a])
        if b is None:
            continue
        assert E.az_gap(a["az"], b["az"]) >= E.MIN_AZ_GAP - 1e-9


def test_draw_avoids_furniture_and_blocked_views():
    # a tall cabinet in front of the workspace: every drawn camera is outside it and sees past it
    cab = {"pos": [1.05, -0.15, 0.9], "size": [0.3, 1.2, 1.8], "yaw": 0.0}
    c = _ctx(boxes=[cab])
    n = 0
    for s in range(30):
        d = E.draw(s, 0, c)
        if d is None:
            continue
        n += 1
        R, t, K = E.pose_of(d)
        assert not E.inside_any(t, [cab], E.BOX_MARGIN)
        for p in c.ws_pts + c.robot_pts:
            assert not E.ray_blocked(t, p, [cab])
    assert n >= 20


def test_no_room_zone_allows_far_cameras():
    c = _ctx(zone=None)
    assert all(E.draw(s, 0, c) is not None for s in range(20))


# ---------------------------------------------------------------- rendered check (depth)
def test_depth_check_rejects_a_wall_in_front():
    c = _ctx()
    d = E.draw(3, 0, c)
    R, t, K = E.pose_of(d)
    pts = c.ws_pts + c.robot_pts
    far = np.full((E.H, E.W), 10.0, np.float32)
    ok, why = E.depth_ok(far, R, t, K, pts)
    assert ok, why
    wall = np.full((E.H, E.W), 0.2, np.float32)
    ok, why = E.depth_ok(wall, R, t, K, pts)
    assert not ok and why.startswith("near")
    # something 0.5 m in front of one point only: that point is occluded
    occ = far.copy()
    u, v, _ = E.project(R, t, K, pts[0])
    occ[int(v) - 6:int(v) + 7, int(u) - 6:int(u) + 7] = 0.5
    ok, why = E.depth_ok(occ, R, t, K, pts)
    assert not ok and why.startswith("occluded")


# ---------------------------------------------------------------- records / text
def test_record_and_camera_line():
    c = _ctx()
    d = E.draw(5, 0, c)
    rec = E.record("ext0", d)
    assert rec["view"] == "external" and rec["W"] == E.W and rec["H"] == E.H
    assert np.allclose(np.asarray(rec["K"]), E.K_of(d["hfov"]))
    R, t, _ = E.pose_of(d)
    assert np.allclose(rec["R"], E.optical(R)) and np.allclose(rec["t"], t)
    line = E.line(rec, "l9/ffw_sg2")
    assert line.startswith("camera: external, 672x376 px, fx ")
    assert "above the floor" in line and "pitch" in line and line.endswith("source: l9/ffw_sg2/external")
    # the head line still reads "camera: head"
    head = HC.line(rec, "l9/ffw_sg2")
    assert head.startswith("camera: head")


DMIN = ("POINT, THEN ACT (you never compute target coordinates)\n"
        "- You POINT in image 1 (the head camera) at the thing the gripper should go to, and choose a height. Code "
        "measures the rest from the head camera's depth and its calibration: x.\n\n"
        "CAMERAS (directions are unit vectors in the robot frame)\n"
        "- Image 1: head camera, fixed on the robot head, 672x376 px at (0.10, 0.03, 1.38) m, looking along "
        "(+0.55, +0.06, -0.83); image right = (+0.03, -1.00, -0.05), image down = (-0.83, +0.00, -0.55).\n"
        "- Image 2: RIGHT wrist camera, moves with the right hand and looks down between the fingers; its pose now "
        "is under NOW.\n\n"
        "HEAD IMAGE OVERLAY (drawn by code from the camera calibration and the robot's own joint angles)\n"
        "- White ring with a black outline: the TCP now. Nothing else is drawn; the wrist image has no drawing.\n\n"
        "- The head view alone can make the fingers look as if they hold an object when they do not: verify.\n"
        "NOW\n- TCP at (0.3, 0.2, 1.0) m.\n"
        "NOTE: the TCP is outside the head image this time: no ring is drawn.\nReturn JSON only")


@pytest.mark.parametrize("mount", ["fixed on the robot head", "fixed on a mast on the robot's stand"])
def test_external_text(mount):
    rec = E.record("ext0", E.draw(5, 0, _ctx()))
    t = DMIN.replace("fixed on the robot head", mount)
    out = E.external_text(t, rec, tcp_drawn=True)
    assert "head camera" not in out and "head image" not in out.lower() and "head view" not in out
    assert "- Image 1: external camera, fixed in the room (not on the robot), 672x376 px at (" in out
    assert "(the external camera)" in out and "the external camera's depth" in out
    assert "IMAGE 1 OVERLAY" in out and "NOTE" not in out
    assert out.count("- Image 2: RIGHT wrist camera") == 1
    out2 = E.external_text(t, rec, tcp_drawn=False)
    assert "NOTE: the TCP is outside image 1 this time: no ring is drawn." in out2
    with pytest.raises(ValueError):
        E.external_text("no cameras block", rec, tcp_drawn=True)


def test_external_answer_swaps_only_the_point():
    a = {"assessment": {"x": 1}, "command": {"mode": "point", "point_2d": [500, 400], "height": "grasp",
                                             "gripper": "close", "hand": "right"}, "reason": "r"}
    out = json.loads(E.external_answer(json.dumps(a), [120, 640]))
    assert out["command"]["point_2d"] == [120, 640] and out["command"]["hand"] == "right"
    assert out["assessment"] == a["assessment"] and out["reason"] == "r"
    lift = {"command": {"mode": "point", "height": "lift", "gripper": "keep"}}
    assert json.loads(E.external_answer(json.dumps(lift), None)) == lift
    with pytest.raises(ValueError):
        E.external_answer(json.dumps(a), None)


# ---------------------------------------------------------------- same 3D target in the external view
def _head_rec():
    R = E.look_at(np.array([0.05, 0.0, 1.40]), np.array([0.5, 0.0, 0.8]))
    K = E.K_of(85.0)
    return {"name": "head", "W": E.W, "H": E.H, "fx": K[0, 0], "fy": K[1, 1], "cx": K[0, 2], "cy": K[1, 2],
            "R": E.optical(R).tolist(), "t": [0.05, 0.0, 1.40]}


def _plane_depth(rec, z_plane):
    """z-depth image of the horizontal plane z = z_plane seen by camera rec."""
    Ro, t = np.asarray(rec["R"], float), np.asarray(rec["t"], float)
    u, v = np.meshgrid(np.arange(E.W) + 0.5, np.arange(E.H) + 0.5)
    rays = np.stack([(u - rec["cx"]) / rec["fx"], (v - rec["cy"]) / rec["fy"], np.ones_like(u)], -1) @ Ro.T
    s = (z_plane - t[2]) / rays[..., 2]  # world ray scale -> optical z = s (ray optical z component = 1)
    return np.where(s > 0, s, np.inf).astype(np.float32)


def test_back_project_then_external_point():
    head = _head_rec()
    hd = _plane_depth(head, 0.8)
    p = np.array([0.55, -0.10, 0.8])
    Rh = np.asarray(head["R"]) @ E.M_OPT.T
    u, v, _ = E.project(Rh, np.asarray(head["t"]), E.K_of(85.0), p)
    pt = [u / E.W * 1000, v / E.H * 1000]
    P = E.back_project(head, hd, pt)
    assert np.allclose(P, p, atol=0.005)
    ext = E.record("ext0", E.draw(2, 0, _ctx()))
    ed = _plane_depth(ext, 0.8)
    q, info = E.external_point(head, hd, pt, ext, ed)
    Re = np.asarray(ext["R"]) @ E.M_OPT.T
    ue, ve, _ = E.project(Re, np.asarray(ext["t"]), np.asarray(ext["K"]), p)
    assert q is not None and abs(q[0] - ue / E.W * 1000) <= 3 and abs(q[1] - ve / E.H * 1000) <= 3, info
    blocked = ed.copy()
    blocked[int(ve) - 3:int(ve) + 4, int(ue) - 3:int(ue) + 4] = 0.4  # something in front of it in the external view
    q2, info2 = E.external_point(head, hd, pt, ext, blocked)
    assert q2 is None and info2["why"] == "hidden"


def test_depth_mm_roundtrip(tmp_path):
    d = np.array([[0.4567, np.inf, 12.3456], [0.0, np.nan, 70.0]], np.float32)
    mm = E.depth_to_mm(d)
    assert mm.dtype == np.uint16 and mm.tolist() == [[457, 0, 12346], [0, 0, 0]]
    p = tmp_path / "x.npz"
    np.savez_compressed(p, depth_mm=mm)
    back = E.load_depth(str(p))
    assert back[0, 0] == pytest.approx(0.457) and np.isinf(back[0, 1]) and np.isinf(back[1, 2])
    np.savez_compressed(tmp_path / "f.npz", depth=d)  # float form (head_depth.npz style) still loads
    assert E.load_depth(str(tmp_path / "f.npz"))[0, 2] == pytest.approx(12.3456)


def test_external_answer_keeps_a_null_point():
    a = {"command": {"mode": "point", "point_2d": None, "height": "lift", "gripper": "keep"}}
    assert json.loads(E.external_answer(json.dumps(a), None)) == a
