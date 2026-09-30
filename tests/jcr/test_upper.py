import numpy as np

from harvest.jcr import upper as U

DIST = {"approach_xy_mm": [2.0, 4.0, 30.0], "carry_xy_mm": [10.0, 12.0], "grasp_z_mm": [-2.0, 2.0, 5.0],
        "action_err": {"keep": 0.0, "close": 1.0, "open": 0.0}, "latency_s": [1.5, 2.0]}


def test_same_seed_same_noise():
    a = U.sample_cmd_noise(np.random.default_rng(3), DIST, "approach", "grasp", "close")
    b = U.sample_cmd_noise(np.random.default_rng(3), DIST, "approach", "grasp", "close")
    assert a == b


def test_magnitudes_come_from_the_distribution():
    rng = np.random.default_rng(0)
    for _ in range(50):
        n = U.sample_cmd_noise(rng, DIST, "approach", "grasp", "keep")
        xy = np.hypot(*n["dxyz"][:2]) * 1e3
        assert min(abs(xy - v) for v in DIST["approach_xy_mm"]) < 1e-6
        assert min(abs(n["dxyz"][2] * 1e3 - v) for v in DIST["grasp_z_mm"]) < 1e-6
        assert n["delay_s"] in DIST["latency_s"]


def test_lift_has_no_point_noise_and_scale_zero_is_clean():
    n = U.sample_cmd_noise(np.random.default_rng(1), DIST, "lift", "lift", "keep")
    assert n["dxyz"] == [0.0, 0.0, 0.0]
    n = U.sample_cmd_noise(np.random.default_rng(1), DIST, "approach", "above", "keep", scale=0.0)
    assert n["dxyz"] == [0.0, 0.0, 0.0] and n["grip"] == "keep"


def test_intent_error_flips_gripper_with_measured_rate():
    n = U.sample_cmd_noise(np.random.default_rng(2), DIST, "approach", "grasp", "close")
    assert n["grip"] == "keep" and n["intent_err"]
    n = U.sample_cmd_noise(np.random.default_rng(2), DIST, "approach", "above", "keep")
    assert n["grip"] == "keep" and not n["intent_err"]
