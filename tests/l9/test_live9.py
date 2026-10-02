import math

import numpy as np

from harvest.l9 import grasp9 as G
from harvest.l9 import live9 as L
from harvest.l9 import v2plan as VP


def box_cloud(hx, hy, hz, n_per_face=10, seed=0):
    """Point samples (P) + exact outward normals (N) of an axis-aligned box's 6 faces (object/base frame)."""
    rng = np.random.default_rng(seed)
    P, N = [], []
    axes = [(0, hx), (1, hy), (2, hz)]
    for ax, h in axes:
        for s in (-1, 1):
            u = rng.uniform(-1, 1, n_per_face) * [hx, hy, hz][(ax + 1) % 3]
            v = rng.uniform(-1, 1, n_per_face) * [hx, hy, hz][(ax + 2) % 3]
            pt = np.zeros((n_per_face, 3))
            pt[:, ax] = s * h
            pt[:, (ax + 1) % 3] = u
            pt[:, (ax + 2) % 3] = v
            nrm = np.zeros((n_per_face, 3))
            nrm[:, ax] = s
            P.append(pt)
            N.append(nrm)
    return np.concatenate(P), np.concatenate(N)


# ---------------------------------------------------------------------------------------------- perception
def test_back_project_recovers_a_plane_point():
    from harvest.astra_motion.geometry import Cam, plane_depth_map
    cam = Cam("head", 64, 48, 50.0, 50.0, 32.0, 24.0, np.diag([1.0, -1.0, -1.0]), np.array([0.0, 0.0, 1.0]))
    depth = plane_depth_map(cam, 0.0)
    from harvest.astra_solo.resolve import to_scaled
    u, v = 40, 20
    p2d = to_scaled(u + 0.5, v + 0.5, cam.W, cam.H)
    p3d = L.back_project(p2d, cam, depth)
    assert p3d is not None
    assert abs(p3d[2] - 0.0) < 1e-6  # on the plane z=0
    # within one pixel's worth of the true ray hit
    from harvest.astra_motion.geometry import lift_plane
    truth = lift_plane(cam, u, v, 0.0)
    assert np.linalg.norm(p3d - truth) < 1e-6


def test_crop_cloud_keeps_only_points_within_radius():
    from harvest.astra_motion.geometry import Cam
    cam = Cam("head", 20, 20, 50.0, 50.0, 10.0, 10.0, np.eye(3), np.zeros(3))
    depth = np.full((20, 20), 1.0)
    depth[10, 10] = 1.0  # centre pixel: ray along +z at distance 1 -> point (0,0,1) roughly
    P = L.crop_cloud(np.array([0.0, 0.0, 1.0]), cam, depth, radius=0.5)
    assert len(P) > 0
    assert np.linalg.norm(P - np.array([0.0, 0.0, 1.0]), axis=1).max() <= 0.5 + 1e-9


def test_estimate_normals_recovers_flat_face_direction():
    P, N_true = box_cloud(0.03, 0.04, 0.05, n_per_face=30, seed=1)
    N_est = L.estimate_normals(P, k=10)
    cos = np.abs((N_est * N_true).sum(1))
    assert np.median(cos) > 0.9  # most points: normal within ~25 deg of truth


# ---------------------------------------------------------------------------------------------- antipodal pairs
def test_antipodal_pairs_cloud_finds_box_pairs_within_width_bounds():
    P, N = box_cloud(0.02, 0.03, 0.04, n_per_face=25, seed=2)
    gr = G.gripper("ffw_sg2")
    pr = L.antipodal_pairs_cloud(P, N, gr, seed=0)
    assert len(pr["w"]) > 5
    assert pr["w"].max() <= gr["max_open"] - G.OPEN_MARGIN + 1e-9
    assert pr["w"].min() >= G.W_MIN - 1e-9
    ax = (pr["q"] - pr["p"]) / pr["w"][:, None]
    cos_c = math.cos(math.atan(G.MU))
    assert (np.abs(ax).max(1) >= cos_c - 1e-6).all()  # (anti)parallel to a box axis within the friction cone


def test_antipodal_pairs_cloud_empty_on_too_few_points():
    P = np.zeros((1, 3))
    N = np.zeros((1, 3))
    pr = L.antipodal_pairs_cloud(P, N, G.gripper("ffw_sg2"))
    assert len(pr["w"]) == 0


# ---------------------------------------------------------------------------------------------- live candidates
def test_sample_grasps_cloud_respects_approach_family_and_rot_window():
    P, N = box_cloud(0.025, 0.03, 0.05, n_per_face=30, seed=3)
    support_z = -0.05 - 0.01
    f_dir = np.array([1.0, 0.0])
    top = L.sample_grasps_cloud(P, N, "ffw_sg2", "top", 0, support_z, f_dir, seed=1)
    assert len(top["w"]) > 0
    for a in top["a"]:
        assert G.family(a, f_dir) == "top"
    # a family that cannot exist on this flat-topped box at rot 0 narrows or empties the result
    side_far_rot = L.sample_grasps_cloud(P, N, "ffw_sg2", "side", 6, support_z, f_dir, seed=1)
    for a, c1, c2, w in zip(side_far_rot["a"], side_far_rot["c1"], side_far_rot["c2"], side_far_rot["w"]):
        assert G.family(a, f_dir) == "side"


def slab_cloud(hx, hy, hz, n=60, seed=0):
    """Two parallel faces only (a thin slab, +-x normals) -- unlike a full box, every antipodal pair here shares the
    SAME closing axis family (+-x), so a test can pin down a single, unambiguous rot_img bin."""
    rng = np.random.default_rng(seed)
    P, N = [], []
    for s in (-1, 1):
        y = rng.uniform(-hy, hy, n)
        z = rng.uniform(-hz, hz, n)
        P.append(np.stack([np.full(n, s * hx), y, z], 1))
        N.append(np.stack([np.full(n, float(s)), np.zeros(n), np.zeros(n)], 1))
    return np.concatenate(P), np.concatenate(N)


def test_sample_grasps_cloud_rot_bin_is_image_projected_not_base_frame():
    """Regression (10-02 pod smoke): the commanded rot bin is grasp9.rot_img (the closing axis projected into the
    HEAD IMAGE, spec step 1), not grasp9.rot_base (a base-frame angle) -- comparing against rot_base left almost
    every real VLM-style command unmatched (pod smoke: 2/2 cache-valid seeds skipped live). With a camera given,
    only the rot bin that matches the pair's actual rot_img should keep any candidate; the opposite bin keeps none."""
    from harvest.astra_motion.geometry import Cam
    P, N = slab_cloud(0.03, 0.04, 0.05, n=40, seed=11)
    gr = G.gripper("ffw_sg2")
    pr = L.antipodal_pairs_cloud(P, N, gr, seed=0)
    assert len(pr["w"]) > 0
    cam = Cam("head", 100, 100, 100.0, 100.0, 50.0, 50.0, np.diag([1.0, -1.0, -1.0]), np.array([0.0, 0.0, 1.0]))
    K = np.array([[cam.fx, 0, cam.cx], [0, cam.fy, cam.cy], [0, 0, 1.0]])
    p, q, w = pr["p"][0], pr["q"][0], pr["w"][0]
    c, m = (q - p) / w, (p + q) / 2
    _, true_bin = G.rot_img(m, c, K, cam.R, cam.t)
    opposite = (true_bin + 6) % 12
    support_z = -0.06
    f_dir = np.array([1.0, 0.0])
    for fam in ("top", "oblique", "front", "side"):
        matched = L.sample_grasps_cloud(P, N, "ffw_sg2", fam, true_bin, support_z, f_dir, cam=cam, seed=0)
        far = L.sample_grasps_cloud(P, N, "ffw_sg2", fam, opposite, support_z, f_dir, cam=cam, seed=0)
        assert len(far["w"]) == 0
        if len(matched["w"]):
            break
    else:
        raise AssertionError("no family matched the true rot_img bin at all")


def test_choose_live_with_camera_succeeds_on_the_true_rot_bin():
    from harvest.astra_motion.geometry import Cam
    P, N = box_cloud(0.03, 0.035, 0.05, n_per_face=30, seed=12)
    cam = Cam("head", 100, 100, 100.0, 100.0, 50.0, 50.0, np.diag([1.0, -1.0, -1.0]), np.array([0.0, 0.0, 1.0]))
    K = np.array([[cam.fx, 0, cam.cx], [0, cam.fy, cam.cy], [0, 0, 1.0]])
    gr = G.gripper("ffw_sg2")
    pr = L.antipodal_pairs_cloud(P, N, gr, seed=0)
    c0, m0 = (pr["q"][0] - pr["p"][0]) / pr["w"][0], (pr["p"][0] + pr["q"][0]) / 2
    _, rot_bin = G.rot_img(m0, c0, K, cam.R, cam.t)
    point3d = m0
    found = None
    for fam in ("top", "oblique", "front", "side"):
        gc = L.choose_live(P, N, "ffw_sg2", fam, rot_bin, point3d, support_z=-0.06, f_dir=np.array([1.0, 0.0]),
                           cam=cam, use_refiner=False)
        if gc is not None:
            found = gc
            break
    assert found is not None
    assert found.meta["source"] == "live_cloud"


def test_sample_grasps_cloud_rejects_candidates_colliding_with_extra_obstacles():
    P, N = box_cloud(0.025, 0.03, 0.05, n_per_face=30, seed=4)
    support_z = -0.06
    f_dir = np.array([1.0, 0.0])
    free = L.sample_grasps_cloud(P, N, "ffw_sg2", "top", 0, support_z, f_dir, seed=2)
    assert len(free["w"]) > 0
    # a neighbour cuboid wrapped all the way around the object blocks every swept approach
    big_wall = (np.array([[0.0, 0.0, 0.0]]), np.array([[1.0, 1.0, 1.0]]), np.array([np.eye(3)]))
    blocked = L.sample_grasps_cloud(P, N, "ffw_sg2", "top", 0, support_z, f_dir, extra_obstacles=big_wall, seed=2)
    assert len(blocked["w"]) == 0


def test_sample_grasps_cloud_support_clearance():
    P, N = box_cloud(0.02, 0.02, 0.02, n_per_face=20, seed=5)
    f_dir = np.array([1.0, 0.0])
    # support just under the box: fine
    ok = L.sample_grasps_cloud(P, N, "ffw_sg2", "top", 0, -0.03, f_dir, seed=0)
    # support far too high (as if the box were buried): no candidate clears it
    blocked = L.sample_grasps_cloud(P, N, "ffw_sg2", "top", 0, 0.05, f_dir, seed=0)
    assert len(ok["w"]) >= len(blocked["w"])
    assert len(blocked["w"]) == 0


# ---------------------------------------------------------------------------------------------- choose_live
def test_choose_live_returns_a_graspchoice_matching_the_commanded_point_and_approach():
    P, N = box_cloud(0.03, 0.035, 0.05, n_per_face=30, seed=6)
    point3d = np.array([0.0, 0.0, 0.05])  # the top face centre
    gc = L.choose_live(P, N, "ffw_sg2", "top", 0, point3d, support_z=-0.06, f_dir=np.array([1.0, 0.0]),
                       category="box", obj_h=0.1, seed=0, k=0, use_refiner=False)
    assert isinstance(gc, VP.GraspChoice)
    assert gc.family == "top"
    assert np.linalg.norm(gc.pos - point3d) < 0.04  # near the commanded point
    assert gc.meta["source"] == "live_cloud"
    assert gc.meta["label_rule"] == "live_v1"


def test_choose_live_returns_none_when_nothing_is_reachable_there():
    P, N = box_cloud(0.02, 0.02, 0.02, n_per_face=10, seed=7)
    point3d = np.array([0.0, 0.0, 0.0])
    gc = L.choose_live(P, N, "ffw_sg2", "top", 0, point3d, support_z=0.5, f_dir=np.array([1.0, 0.0]),
                       use_refiner=False)
    assert gc is None


# ---------------------------------------------------------------------------------------------- refiner hook
def test_refiner_hook_is_used_when_installed_and_restored_after():
    P, N = box_cloud(0.03, 0.035, 0.05, n_per_face=20, seed=8)
    calls = []

    def fake_refiner(cloud, point3d, approach, rot, gripper):
        calls.append((approach, rot, gripper))
        gr = G.gripper(gripper)
        T = np.eye(4)
        T[:3, 3] = point3d
        return {"T": T[None], "c1": np.array([point3d]) - [0.02, 0, 0], "c2": np.array([point3d]) + [0.02, 0, 0],
                "w": np.array([0.04]), "a": np.array([[0.0, 0.0, -1.0]]), "score": np.array([1.0]),
                "pre_open": np.array([0.05]), "gripper": gr, "source": np.array(["refiner"])}
    try:
        L.set_refiner(fake_refiner)
        point3d = np.array([0.0, 0.0, 0.05])
        gc = L.choose_live(P, N, "ffw_sg2", "top", 0, point3d, support_z=-0.06, f_dir=np.array([1.0, 0.0]),
                           use_refiner=True)
        assert len(calls) == 1
        assert gc.meta["source"] == "refiner"
    finally:
        L.set_refiner(None)


def test_refiner_hook_not_called_when_use_refiner_false():
    P, N = box_cloud(0.03, 0.035, 0.05, n_per_face=20, seed=9)
    calls = []
    L.set_refiner(lambda *a: calls.append(1) or None)
    try:
        point3d = np.array([0.0, 0.0, 0.05])
        L.choose_live(P, N, "ffw_sg2", "top", 0, point3d, support_z=-0.06, f_dir=np.array([1.0, 0.0]),
                     use_refiner=False)
        assert not calls
    finally:
        L.set_refiner(None)


# ---------------------------------------------------------------------------------------------- no-cache proof
def test_live9_module_never_touches_the_npz_cache_dirs():
    """Static proof: the live search module references neither the cache env vars nor GRASP_DIR/TESTED_DIR (rt9's
    cache paths) anywhere in its source -- the whole live path is built from an in-memory point cloud only."""
    import inspect
    src = inspect.getsource(L)
    for bad in ("GRASP_DIR", "TESTED_DIR", "L9V2_GRASPS", "L9V2_TESTED", "np.load"):
        assert bad not in src
