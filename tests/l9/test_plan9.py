import math

import numpy as np

from harvest.l9 import plan9 as P


def test_resample_bounds_and_ends():
    rng = np.random.default_rng(0)
    for kind in ("minjerk", "two_phase"):
        for _ in range(20):
            Q = np.cumsum(rng.normal(0, 0.05, (30, 7)), 0)
            out = P.resample(Q, kind=kind)
            assert P.max_step(out) <= P.DQ_MAX + 1e-9
            assert np.allclose(out[0], Q[0]) and np.allclose(out[-1], Q[-1])


def test_resample_slow_stretches():
    Q = np.linspace(np.zeros(7), np.full(7, 1.0), 10)
    assert len(P.resample(Q, slow=2.0)) > 1.8 * len(P.resample(Q))


def test_scene_cuboids_base_frame():
    parts = [{"id": "t", "prim": "cuboid", "pos": [0.6, 0.0, 0.7], "size": [0.5, 1.0, 0.04], "yaw": 0.3, "role": "top"},
             {"id": "w", "prim": "cuboid", "pos": [2, 0, 1], "size": [0.1, 4, 2], "yaw": 0.0, "role": "room_wall"}]
    Tb = np.eye(4)
    Tb[:3, 3] = [0.0, -0.2, 0.9]
    s = P.scene_cuboids(parts, {"o1": ([0.5, -0.1, 0.78], [0.04, 0.04, 0.1], [1, 0, 0, 0])}, Tb)["cuboid"]
    assert set(s) == {"part_t", "o1"}
    assert np.allclose(s["part_t"]["pose"][:3], [0.6, 0.2, -0.2])
    q = s["part_t"]["pose"][3:]
    assert abs(2 * math.atan2(q[3], q[0]) - 0.3) < 1e-6
