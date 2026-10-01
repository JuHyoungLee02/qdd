import math

import numpy as np

from harvest.l9 import grasp9 as G


def box_mesh(hx, hy, hz):
    V = np.array([[x, y, z] for x in (-hx, hx) for y in (-hy, hy) for z in (-hz, hz)], float)
    F = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1],
                  [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]], int)
    return V, F


def test_cup_and_bowl_meshes_closed():
    for V, F in (G.cup_mesh(0.03, 0.004, 0.09), G.cup_mesh(0.08, 0.005, 0.06)):
        o = np.array([[0.0, 0.0, 0.0]])
        for d in ([1, 0, 0], [0, 1, 0], [0.3, 0.4, 0.0]):
            t = G.ray_hits(o, np.array([d], float) / np.linalg.norm(d), V, F)[0]
            assert len(t) == 2  # inner wall then outer wall from the hollow inside


def test_box_pairs_are_antipodal_and_fit():
    V, F = box_mesh(0.02, 0.03, 0.04)
    gr = G.gripper("ffw_sg2")
    P = G.antipodal_pairs(V, F, gr, n=1500, seed=0)
    assert len(P["w"]) > 50
    assert P["w"].max() <= gr["max_open"] - G.OPEN_MARGIN + 1e-9 and P["w"].min() >= G.W_MIN
    ax = (P["q"] - P["p"]) / P["w"][:, None]
    # every pair closes across two opposite box faces: the axis is (anti)parallel to a box axis within the cone
    assert (np.abs(ax).max(1) >= math.cos(math.atan(G.MU)) - 1e-6).all()


def test_box_has_top_centre_and_side_candidates_none_from_below():
    V, F = box_mesh(0.02, 0.025, 0.05)
    C = G.sample_grasps(V, F, "ffw_sg2", seed=1, n_surface=2500)
    a = C["a"]
    assert (a[:, 2] <= G.BELOW_Z + 1e-9).all()  # never from below
    top = a[:, 2] < -math.cos(math.radians(25))
    assert top.any() and (~top).any()
    m = (C["c1"] + C["c2"]) / 2
    assert np.hypot(m[top, 0], m[top, 1]).min() < 0.01
    # the fingertips of every candidate stay above the support (object bottom = -hz)
    for T in C["T"][:200]:
        assert G.lowest_point(T, C["gripper"], 0.0) > -0.05 + G.SUPPORT_CLEAR - 1e-9


def test_cup_outer_and_rim_grasps():
    V, F = G.cup_mesh(0.03, 0.004, 0.09)  # 6 cm wide cup: outer grasp fits the 10.7 cm gripper
    C = G.sample_grasps(V, F, "ffw_sg2", seed=2, n_surface=4000)
    w = C["w"]
    assert ((w > 0.055) & (w < 0.065)).any()  # both outer walls
    assert (w < 0.008).any()  # wall pinch at the rim
    rim = w < 0.008
    m = (C["c1"] + C["c2"]) / 2
    assert (m[rim, 2] > 0.045 - G.gripper("ffw_sg2")["finger_len"]).all()  # pinch reachable from the rim


def test_wide_bowl_only_rim():
    V, F = G.cup_mesh(0.08, 0.005, 0.06)  # 16 cm bowl > 10.7 cm max opening
    C = G.sample_grasps(V, F, "ffw_sg2", seed=3, n_surface=4000)
    assert len(C["w"]) > 0 and (C["w"] < 0.012).all()


def test_franka_narrower():
    V, F = box_mesh(0.045, 0.045, 0.04)  # 9 cm cube: too wide for Franka (8 cm), fine for AI Worker
    assert len(G.sample_grasps(V, F, "franka", seed=0, n_surface=1500)["w"]) == 0
    assert len(G.sample_grasps(V, F, "ffw_sg2", seed=0, n_surface=1500)["w"]) > 0


def test_family_classes():
    f = np.array([1.0, 0.0, 0.0])
    assert G.family(np.array([0, 0, -1.0]), f) == "top"
    assert G.family(np.array([math.sin(0.7), 0, -math.cos(0.7)]), f) == "oblique"
    assert G.family(np.array([1.0, 0.1, -0.1]), f) == "front"
    assert G.family(np.array([0.1, 1.0, 0.0]), f) == "side"


def test_world_transform_and_rot_bins():
    V, F = box_mesh(0.02, 0.025, 0.05)
    C = G.sample_grasps(V, F, "ffw_sg2", seed=1, n_surface=1500)
    pose = (np.array([0.5, -0.2, 0.8]), G.yaw_quat(0.4))
    W = G.to_world(C, *pose)
    k = 0
    assert np.allclose(W["c1"][k], pose[0] + G.qmat(pose[1]) @ C["c1"][k], atol=1e-9)
    assert np.allclose(np.linalg.det(W["T"][k][:3, :3]), 1.0)
    # rot bin: the closing axis projected into an image; 12 bins over 0..180
    K = np.array([[400.0, 0, 336], [0, 400.0, 188], [0, 0, 1]])
    R_cw = np.eye(3)  # camera = world (optical z forward)
    for ang in (0, 14, 16, 89, 179, 181):
        c = np.array([math.cos(math.radians(ang)), math.sin(math.radians(ang)), 0.0])
        deg, b = G.rot_img(np.array([0, 0, 1.0]), c, K, R_cw, np.zeros(3))
        assert 0 <= b <= 11 and 0 <= deg < 180
        assert b == int(((ang % 180) // 15))


def test_select_label_deterministic_rule():
    fam = np.array(["top", "top", "oblique", "side", "front"])
    centre_d = np.array([0.004, 0.03, 0.01, 0.02, 0.0])
    robot_d = np.array([0.40, 0.30, 0.35, 0.33, 0.31])
    margin = np.array([0.2, 0.5, 0.3, 0.3, 0.3])
    ok = np.array([True, True, True, True, True])
    i, step, why = G.select_label(fam, centre_d, robot_d, margin, ok, constraint=None)
    assert (i, step, why) == (0, 0, "default")  # top-centre valid -> that one
    ok0 = ok.copy(); ok0[0] = False
    i, step, why = G.select_label(fam, centre_d, robot_d, margin, ok0, constraint=None)
    assert fam[i] == "top" and step == 2  # no top-centre: family order default (top first), robot side first
    i, step, why = G.select_label(fam, centre_d, robot_d, margin, ok, constraint="blocked_above")
    assert fam[i] in ("front", "side") and step == 1 and why == "scene_constraint:blocked_above"
    i, step, why = G.select_label(fam, centre_d, robot_d, margin, ok, constraint=None, instructed="side")
    assert fam[i] == "side" and why == "instructed"
    i, step, why = G.select_label(fam, centre_d, robot_d, margin, np.zeros(5, bool), constraint=None)
    assert i is None


def test_fallback_order():
    order = G.fallback_order("side", 4)
    assert order[:5] == [("side", 4), ("side", 3), ("side", 5), ("side", 2), ("side", 6)]
    fams = [f for f, _ in order]
    assert fams.index("oblique") < fams.index("top")  # neighbour family by angle: side -> front/oblique before top


def test_obb_overlap():
    R = np.eye(3)
    C2 = np.array([[0.0, 0, 0], [0.25, 0, 0], [0.15, 0.15, 0], [0.0, 0.2, 0]])
    H2 = np.full((4, 3), 0.1)
    rz = G.qmat(G.yaw_quat(math.pi / 4))
    R2 = np.stack([np.eye(3), np.eye(3), rz, np.eye(3)])
    got = G.obb_overlap([0, 0, 0], [0.1, 0.1, 0.1], R, C2, H2, R2)
    # same box / 0.25 apart on x (gap) / rotated 45 deg at (0.15, 0.15): corner reaches 0.15 - 0.141 = 0.009 < 0.1 /
    # touching face at 0.2
    assert got.tolist() == [True, False, True, True]


def test_natural_order_and_select():
    assert G.natural_order("plastic bottle", 0.2)[0] == ("side", "body")
    assert G.natural_order("ceramic bowl", 0.06)[0] == ("top", "rim")
    assert G.natural_order("cardboard box", 0.08)[0] == ("top", "body")
    assert G.natural_order("cardboard box", 0.20)[0][0] in ("side", "front")  # tall -> from the side
    assert all(f in ("front", "side") for f, _ in G.natural_order("apple", 0.08, "blocked_above"))
    assert G.natural_order("coaster", 0.01)[0] == ("top", "edge")
    fam = np.array(["top", "side", "side", "oblique"])
    part = np.array(["body", "body", "body", "body"])
    rd = np.array([0.4, 0.42, 0.30, 0.35])
    ok = np.ones(4, bool)
    i, step, r = G.select_natural(fam, part, rd, np.ones(4), ok, G.natural_order("bottle", 0.2))
    assert i == 2 and step == 0  # side body, robot side first
    i, step, r = G.select_natural(fam, part, rd, np.ones(4), ok, G.natural_order("bottle", 0.2), instructed="top")
    assert i == 0 and step == 2


def test_part_of():
    he = (0.04, 0.04, 0.05)
    assert G.part_of([0.036, 0, 0.04], [0.04, 0, 0.04], 0.004, he, True, False) == "rim"
    assert G.part_of([-0.04, 0, 0.0], [0.04, 0, 0.0], 0.08, he, True, False) == "body"
    assert G.part_of([0.08, -0.01, 0], [0.08, 0.01, 0], 0.02, (0.1, 0.015, 0.01), False, True) in ("edge", "handle")
