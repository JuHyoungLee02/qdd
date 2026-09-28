"""prereg_limits.md change 3 (noise fix): (1) the scene-change allowance grows with the stereo noise model
(sigma_z = z^2 sigma_d / (fx B)), (2) the held object's projected region (a cylinder under the TCP) is left out of
the comparison, (3) 'above' targets are the per-axis median of the last 3 'above' calls of the same holding phase."""
import numpy as np

from harvest.teach_l8d.depth_noise import PRESETS, stereo_noise
from harvest.teach_strip8 import boost as B

from astra_motion.fakeworld import look_at
from teach_strip8.test_boost1b import TZ, plane_depth

ZED = (PRESETS["zed_mini"]["baseline_m"], PRESETS["zed_mini"]["sigma_d_px"])


def noisy(cam, d, k, seed):
    return stereo_noise(d, None, cam.fx, "zed_mini", seed=seed, sigma_d_px=ZED[1] * k)[0]


def test_noise_scaled_threshold_keeps_unchanged_scene_and_catches_change():
    A = look_at((0.08, 0.02, 1.55), (0.45, -0.15, TZ), "head", 672, 376, 367.0)
    clean = plane_depth(A, box=(0.40, 0.58, -0.25, -0.11, 0.015))
    M = B.PointMemory()
    M.capture(A, noisy(A, clean, 1, 1), tcp=[0.2, 0.3, 1.2], plane=TZ)
    px = B.px_of(A, [0.49, -0.18, TZ + 0.015])
    live = noisy(A, clean, 1, 2)
    ok_old, _ = M.check(A, live, px, tcp=[0.2, 0.3, 1.2])
    ok_new, info = M.check(A, live, px, tcp=[0.2, 0.3, 1.2], sigma=(ZED[0], ZED[1] * 1))
    assert not ok_old and ok_new, info  # the fixed 7 mm drops a noisy but unchanged scene; the scaled one keeps it
    raised = noisy(A, plane_depth(A, box=(0.40, 0.58, -0.25, -0.11, 0.045)), 1, 3)
    ok, info = M.check(A, raised, px, tcp=[0.2, 0.3, 1.2], sigma=(ZED[0], ZED[1] * 1))
    assert not ok, info  # a 3 cm change is still caught at 1x
    ok0, _ = M.check(A, clean, px, tcp=[0.2, 0.3, 1.2], sigma=(ZED[0], 0.0))  # sigma 0 = the old rule
    assert ok0 == M.check(A, clean, px, tcp=[0.2, 0.3, 1.2])[0]


def test_held_projection_excluded():
    A = look_at((0.08, 0.02, 1.55), (0.45, -0.15, TZ), "head", 672, 376, 367.0)
    mem = plane_depth(A)
    M = B.PointMemory()
    M.capture(A, mem, tcp=[0.2, 0.3, 1.3], plane=TZ)
    tcp = [0.49, -0.18, TZ + 0.30]
    px = B.px_of(A, [0.49, -0.18, TZ])
    # a long held object: a 12 cm box hanging 0.26 m under the TCP (its lower part is > 15 cm from the TCP)
    live = plane_depth(A)
    hang = plane_depth(A, box=(0.43, 0.55, -0.24, -0.12, 0.04))  # its 12 cm bottom face, 4 cm above the table
    live = np.where(np.abs(hang - live) > 1e-6, hang, live)
    ok_old, i_old = M.check(A, live, px, tcp=tcp)
    ok_new, i_new = M.check(A, live, px, tcp=tcp, held=(0.09, 0.28, 0.03))
    assert not ok_old and ok_new, (i_old, i_new)
    assert i_new.get("n_held_px", 0) > 0


def test_above_median_of_last_three():
    s = B.AboveSmoother()
    assert s.push(1, False, [0.0, 0.0, 1.0]) == [0.0, 0.0, 1.0]
    assert s.push(1, False, [0.0, 0.0, 1.0]) == [0.0, 0.0, 1.0]  # the same call twice (probe + execute) counts once
    assert s.push(2, False, [0.04, 0.0, 0.9]) == [0.02, 0.0, 0.95]
    assert s.push(3, False, [0.0, 0.01, 1.0]) == [0.0, 0.0, 1.0]
    assert s.push(4, False, [0.1, 0.1, 0.8]) == [0.04, 0.01, 0.9]  # calls 2..4
    assert s.push(5, True, [0.3, 0.3, 1.1]) == [0.3, 0.3, 1.1]  # a new holding phase starts over


def test_parse_nf_and_episode():
    from harvest.astra_solo.pt_truth import PtTruth
    from harvest.teach_strip8.run_limits import nfix_of, parse

    from astra_solo.test_pt_episode import PadWorld
    assert parse("noise:1:nf") == (("noise", 1.0), False, "v1") and nfix_of("noise:1:nf") and not nfix_of("noise:1")
    assert nfix_of("none:nf") and parse("none:nf") == (None, False, "v1")
    w = PadWorld()
    m = PtTruth(w)
    ep = B.LimitEpisode(w, m, 3, "mug_tray", None, mem_points=True, fix_loop=True, stop_calls=16, nfix=True)
    m.ep = ep
    r = ep.run()
    assert r["success"], r["end_reason"]
    assert r["limits"]["nfix"] is True and "above_smoothed" in r["limits"]
