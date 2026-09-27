"""boost1b (prereg_boost1b.md): the memory is a base-frame point cloud re-rendered (z-buffer) into the CURRENT head
camera, and a scene-change check (median |live - memory| depth over unoccluded pixels in a window around the pointed
pixel) drops the memory above the threshold; the perturbation episode applies its disturbance once, after the lift."""
import numpy as np

from harvest.teach_strip8 import boost as B

from astra_motion.fakeworld import look_at

TZ = 0.85


def plane_depth(cam, z_plane=TZ, box=None):
    """z-depth of the table plane (+ an optional raised box (x0, x1, y0, y1, h)) seen by cam (ray casting)."""
    iu, iv = np.meshgrid(np.arange(cam.W) + 0.5, np.arange(cam.H) + 0.5)
    d = np.stack([(iu - cam.cx) / cam.fx, (iv - cam.cy) / cam.fy, np.ones_like(iu)], -1)
    dw = d @ np.asarray(cam.R).T
    t = np.asarray(cam.t)
    s = (z_plane - t[2]) / dw[..., 2]
    if box is not None:
        x0, x1, y0, y1, h = box
        s2 = (z_plane + h - t[2]) / dw[..., 2]
        p2 = t + dw * s2[..., None]
        inb = (p2[..., 0] >= x0) & (p2[..., 0] <= x1) & (p2[..., 1] >= y0) & (p2[..., 1] <= y1)
        s = np.where(inb, s2, s)
    return s  # z-depth = s (d has unit z)


def test_rerender_same_and_moved_camera():
    A = look_at((0.08, 0.02, 1.55), (0.45, -0.15, TZ), "head", 672, 376, 367.0)
    dA = plane_depth(A, box=(0.40, 0.58, -0.25, -0.11, 0.015))
    M = B.PointMemory()
    M.capture(A, dA, tcp=[0.3, 0.0, 1.1], plane=TZ)
    same = M.render(A)
    ok = np.isfinite(same)
    assert ok.mean() > 0.97 and np.nanmax(np.abs(same - dA)[ok]) < 1e-3
    Bc = look_at((0.08, 0.02, 1.40), (0.45, -0.15, TZ - 0.0), "head", 672, 376, 367.0)  # lift 15 cm lower
    truth = plane_depth(Bc, box=(0.40, 0.58, -0.25, -0.11, 0.015))
    r = M.render(Bc)
    ok = np.isfinite(r)
    assert ok.mean() > 0.9 and np.median(np.abs(r - truth)[ok]) < 0.003
    old = np.abs(dA - truth)  # the boost1 image memory in the moved camera is wrong by centimetres
    assert np.median(old) > 0.05


def test_scene_change_check():
    A = look_at((0.08, 0.02, 1.55), (0.45, -0.15, TZ), "head", 672, 376, 367.0)
    mem = plane_depth(A, box=(0.40, 0.58, -0.25, -0.11, 0.015))
    M = B.PointMemory()
    M.capture(A, mem, tcp=[0.3, 0.0, 1.1], plane=TZ)
    tray_px = B.px_of(A, [0.49, -0.18, TZ + 0.015])
    ok, info = M.check(A, mem, tray_px, tcp=[0.2, 0.3, 1.2])
    assert ok and info["stat_mm"] < 1 and info["n"] >= 50
    raised = plane_depth(A, box=(0.40, 0.58, -0.25, -0.11, 0.045))  # the tray area 3 cm higher: a changed scene
    ok, info = M.check(A, raised, tray_px, tcp=[0.2, 0.3, 1.2])
    assert not ok and info["stat_mm"] > B.CHANGE_MM
    n_far = M.check(A, mem, tray_px, tcp=[0.2, 0.3, 1.2])[1]["n"]
    ok, info = M.check(A, mem, tray_px, tcp=[0.49, -0.18, TZ + 0.05])  # points near the TCP excluded
    assert info["n"] < 0.8 * n_far and ok
    far = B.px_of(A, [2.5, 1.5, TZ])  # a window outside the image: too few pixels -> keep (unverified)
    ok, info = M.check(A, mem, far, tcp=[0.2, 0.3, 1.2])
    assert ok and info.get("unverified")


def test_draws_in_range():
    for s in range(50):
        t = B.draw_perturb("tray", s)
        assert 0.03 <= t["mag_m"] <= 0.08 and abs(np.hypot(*t["dxy"]) - t["mag_m"]) < 1e-3
        assert -0.20 <= B.draw_perturb("lift", s)["delta"] <= -0.10
        assert abs(abs(B.draw_perturb("head", s)["delta"]) - np.deg2rad(5)) < 1e-4
    assert B.draw_perturb("tray", 7) == B.draw_perturb("tray", 7)


def test_perturb_episode_once_after_lift_and_points_memory():
    from harvest.astra_solo.pt_truth import PtTruth

    from astra_solo.test_pt_episode import PadWorld

    class Rob:
        joint_names = ["lift_joint", "head_joint1"]

    class Env:
        def __init__(self):
            self.calls, self.robot = [], Rob()

        def object_pose(self, k):
            return np.array([0.5, -0.2, 0.86]), np.array([1.0, 0, 0, 0])

        def write_object_pose(self, k, pos, quat):
            self.calls.append((k, list(pos)))

    class W(PadWorld):
        pass

    w = W()
    w.env = Env()
    m = PtTruth(w)
    ep = B.PerturbEpisode(w, m, 3, "mug_tray", None, perturb="tray", mem_points=True, fix_loop=True)
    m.ep = ep
    res = ep.run()
    assert res["success"], res["end_reason"]
    assert len(w.env.calls) == 1 and w.env.calls[0][0] == ep.info["place"]
    assert res["boost"]["perturb"]["kind"] == "tray" and res["boost"]["mem_points"]
    assert res["boost"]["n_memory_resolves"] > 0 and all(c["kept"] for c in res["boost"]["mem_checks"])


def test_moved_tray_is_detected_by_window():
    A = look_at((0.08, 0.02, 1.55), (0.45, -0.15, TZ), "head", 672, 376, 367.0)
    mem = plane_depth(A, box=(0.40, 0.58, -0.25, -0.11, 0.015))
    M = B.PointMemory()
    M.capture(A, mem, tcp=[0.3, 0.0, 1.1], plane=TZ)
    moved = plane_depth(A, box=(0.40 + 0.07, 0.58 + 0.07, -0.25, -0.11, 0.015))  # tray moved 7 cm
    px = B.px_of(A, [0.49 + 0.07, -0.18, TZ + 0.015])  # the model points at the tray where it is now
    ok, info = M.check(A, moved, px, tcp=[0.2, 0.3, 1.2])
    assert not ok, info
