"""Stereo-like depth noise (track D): error growth with range, geometric occlusion band, low-texture and range holes."""
import numpy as np
import pytest

from harvest.teach_l8d import depth_noise as N

FX = 367.0


def test_sigma_grows_with_range_squared():
    s1 = N.sigma_z(0.5, FX, 0.063, 0.2)
    s2 = N.sigma_z(1.0, FX, 0.063, 0.2)
    assert s2 == pytest.approx(4 * s1) and s2 == pytest.approx(1.0 * 0.2 / (FX * 0.063))


def test_noise_std_matches_the_model():
    z = np.full((200, 300), 1.2)
    out, info = N.stereo_noise(z, None, FX, "zed_mini", seed=1)
    good = np.isfinite(out)
    assert good.mean() > 0.99
    assert np.std(out[good] - 1.2) == pytest.approx(N.sigma_z(1.2, FX, 0.063, 0.2), rel=0.05)
    assert info["preset"] == "zed_mini" and info["frac_occluded"] == 0


def test_occlusion_band_left_of_a_near_object():
    z = np.full((20, 300), 1.0)
    z[:, 100:150] = 0.5
    occ = N.occlusion_mask(z, FX, 0.063)
    band = FX * 0.063 * (1 / 0.5 - 1 / 1.0)  # disparity step, px
    cols = np.where(occ[0])[0]
    assert cols.min() >= 100 - int(np.ceil(band)) - 1 and cols.max() < 100
    assert abs(len(cols) - band) <= 1.5
    assert not occ[:, 150:].any() and not occ[:, 100:150].any()


def test_low_texture_and_range_holes_are_deterministic():
    z = np.full((60, 80), 0.9)
    z[:, :10] = 20.0  # beyond the ZED Mini far limit
    rgb = np.zeros((60, 80, 3), np.uint8)
    rgb[:, 40:] = (np.random.default_rng(0).random((60, 40, 3)) * 255).astype(np.uint8)  # textured half
    a, ia = N.stereo_noise(z, rgb, FX, seed=5)
    b, _ = N.stereo_noise(z, rgb, FX, seed=5)
    assert np.array_equal(np.isnan(a), np.isnan(b)) and np.allclose(np.nan_to_num(a), np.nan_to_num(b))
    assert np.isnan(a[:, :10]).all()
    flat = np.isnan(a[:, 12:38]).mean()
    tex = np.isnan(a[:, 45:75]).mean()
    assert 0.3 < flat < 0.7 and tex < 0.05
    assert ia["frac_range"] > 0 and ia["frac_lowtex"] > 0
    assert set(N.ASSUMPTIONS) and N.PRESETS["zed_mini"]["baseline_m"] == 0.063
