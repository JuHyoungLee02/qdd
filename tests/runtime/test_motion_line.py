import numpy as np
import pytest

from harvest.runtime.core import OursRuntime, RuntimeConfig
from harvest.runtime.models import MockFusedModel
from harvest.runtime.motion import MOTION_VER, MotionTracker, bin_line
from harvest.serialize import MOTION_UNKNOWN, SERIALIZER_VERSION, with_motion_last_step

from .fakeworld import FakeWorld

BINS = {"version": "se2e-motion@v1", "arm_speed": [0.218, 0.607], "grip_rate": 0.176}


def test_serializer_version_and_line_order():
    assert SERIALIZER_VERSION == "ser-A-min-3"
    s = with_motion_last_step("t_state: 1\nrobot: gripper=open", "motion: arm=slow gripper=still", "OK")
    assert s.split("\n")[-2:] == ["motion: arm=slow gripper=still", "last_step: OK"]
    with pytest.raises(ValueError, match="motion"):
        with_motion_last_step("x", "motion: arm=quick gripper=still", "OK")


def test_tracker_matches_the_training_rule():
    T = pytest.importorskip("harvest.train.se2e_temporal")
    assert T.MOTION_VER == MOTION_VER and T.MOTION_UNKNOWN == MOTION_UNKNOWN
    for qd, gr in (([0.1] * 7, 0.0), ([0.2, 0, 0, 0, 0, 0, 0], -0.05), ([0.5, 0.4, 0, 0, 0, 0, 0], 0.05)):
        row = {"motion_src": {"qd_bwd": qd, "grip_rate_bwd": gr}}
        m = MotionTracker(BINS, window_s=0.1)
        m.add(0.0, np.zeros(7), 0.05)
        m.add(0.1, np.asarray(qd) * 0.1, 0.05 + gr * 0.1)
        assert m.line() == T.motion_line(row, BINS)


def test_tracker_start_and_no_bins():
    m = MotionTracker(BINS, window_s=0.1)
    m.add(0.0, np.zeros(7), 0.1)
    assert m.line() == "motion: arm=still gripper=still"  # like training row k = 0 (zero backward difference)
    assert MotionTracker(None).line() == MOTION_UNKNOWN
    assert bin_line(0.7, -0.2, BINS) == "motion: arm=fast gripper=closing"
    with pytest.raises(ValueError, match="version"):
        MotionTracker({"version": "other", "arm_speed": [0, 1], "grip_rate": 1})


def test_fused_request_state_and_context_carry_the_motion_line():
    rt = OursRuntime(RuntimeConfig(backend="fused", clock="simlat", motion_bins=BINS), MockFusedModel(latency_s=0.3))
    rt.reset()
    w = FakeWorld()
    for _ in range(50):
        a, _ = rt.act(w.obs())
        w.step(a)
    ctx = rt._decision_ctx(rt.t_last, *rt._m1_last[:4], w.obs())
    lines = ctx["req"]["state"].split("\n")
    assert lines[-1].startswith("last_step: ") and lines[-2].startswith("motion: arm=")
    assert ctx["ctx_text"].split("\n")[-1] == lines[-2]
    rt.close()
