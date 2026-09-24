# tests/test_stereo_metrics.py
import numpy as np
from harvest.stereo.pipeline import centroid_3d, stability, flip_rate

def test_centroid_backprojects_center():
    K = np.array([[500, 0, 50], [0, 500, 50], [0, 0, 1.0]])
    depth = np.full((100, 100), 1.0); mask = np.zeros((100, 100), bool); mask[45:56, 45:56] = True
    c = centroid_3d(depth, mask, K)
    assert np.allclose(c, [0, 0, 1.0], atol=1e-3)

def test_stability_mm():
    cs = [np.array([0, 0, 1.0]) + np.array([0.001 * (i % 2), 0, 0]) for i in range(10)]
    s = stability(cs)
    assert 0.9 <= s["median_jitter_mm"] <= 1.1

def test_flip_rate_ignores_unknown():
    assert flip_rate([True, True, None, False, False]) == 1 / 3

def test_rank_tracks_persistence_times_confidence():
    from harvest.stereo.pipeline import rank_tracks
    frames = {0: {1: 0.9, 2: 0.6}, 1: {1: 0.9, 2: 0.6, 3: 0.95}, 2: {2: 0.6}}
    # sums: 1 -> 1.8, 2 -> 1.8, 3 -> 0.95 ; tie broken by smaller id
    assert rank_tracks(frames, 2) == [1, 2]
    assert rank_tracks(frames, 5) == [1, 2, 3]
    assert rank_tracks({}, 3) == []

def test_intrinsics_from_fx_center_principal_point():
    from harvest.stereo.pipeline import intrinsics_from_fx
    K = intrinsics_from_fx(672, 376, 367.0)
    assert np.allclose(K, [[367.0, 0, 336.0], [0, 367.0, 188.0], [0, 0, 1.0]])

def test_cli_fx_default_is_zed_mini_vga_and_old_value_selectable():
    from harvest.cli_e3st import build_parser
    for cmd in ("run", "aggregate", "depth"):
        assert build_parser().parse_args([cmd]).fx == 367.0  # ZED Mini VGA 85 deg (canon §47)
    assert build_parser().parse_args(["run", "--fx", "272.1"]).fx == 272.1  # old 102 deg nominal

def test_depth_scales_with_fx_only_z_changes_in_backprojection():
    from harvest.stereo.pipeline import disparity_to_depth, intrinsics_from_fx
    d = np.full((376, 672), 20.0, np.float32); m = np.zeros((376, 672), bool); m[100:110, 500:510] = True
    c = {fx: centroid_3d(disparity_to_depth(d, fx, 0.063), m, intrinsics_from_fx(672, 376, fx)) for fx in (272.1, 367.0)}
    assert np.isclose(c[367.0][2] / c[272.1][2], 367.0 / 272.1, rtol=1e-5)  # z = fx B / d
    assert np.allclose(c[367.0][:2], c[272.1][:2], rtol=1e-5)               # x = (u - cx) B / d: fx-free

def test_mask_cache_roundtrip(tmp_path):
    from harvest.cli_e3st import load_masks, save_masks
    rng = np.random.default_rng(0)
    masks = {f: {} for f in range(4)}
    masks[1][0] = rng.random((6, 8)) > 0.5; masks[2][3] = rng.random((6, 8)) > 0.5
    labels = {0: {"cat": "bottle", "det_score": 0.9}, 3: {"cat": "box", "det_score": 0.5}}
    fn = str(tmp_path / "m.npz")
    save_masks(fn, 1, labels, masks, 4, 6, 8)
    start, lab2, m2 = load_masks(fn)
    assert start == 1 and lab2 == labels
    assert np.array_equal(m2[1][0], masks[1][0]) and np.array_equal(m2[2][3], masks[2][3])
    assert not m2[0][0].any() and not m2[1][3].any()  # absent -> empty mask (same as missing for the metrics)
    save_masks(fn, None, {}, {}, 4, 6, 8)
    assert load_masks(fn)[0] is None
