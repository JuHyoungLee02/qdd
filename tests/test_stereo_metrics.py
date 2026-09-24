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
