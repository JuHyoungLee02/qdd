import numpy as np
import pytest

from harvest.couple.offset import OffsetApplier
from harvest.couple.params import CoupleParams

DT = 0.01


def _run(ap, t0, t1, trace=None):
    t = t0
    while t < t1 - 1e-9:
        s = ap.step(t, DT)
        if trace is not None:
            trace.append((t, s.copy(), ap.v.copy()))
        t = round(t + DT, 6)
    return t


def _check_limits(ap, p):
    assert ap.v_seen <= p.v_max + 1e-9 and ap.a_seen <= p.a_max + 1e-6


def test_single_answer_ramps_to_half_of_the_edit_within_its_window():
    p = CoupleParams()
    ap = OffsetApplier(p)
    ap.command(1, [0.04, 0, 0, 0, 0, 0], 0.5, 0.0, 2.0)
    tr = []
    _run(ap, 0.0, 3.0, tr)
    np.testing.assert_allclose(ap.applied[:3], [0.02, 0, 0], atol=2e-5)
    assert sum(s[0] for t, s, _ in tr if t < 1.0) == pytest.approx(0.01, abs=1e-3)  # linear ramp
    _check_limits(ap, p)
    assert not ap.active


def test_confirmation_adds_the_other_half():
    p = CoupleParams()
    ap = OffsetApplier(p)
    ap.command(1, [0, 0, 0.04, 0, 0, 0], 0.5, 0.0, 2.0)
    _run(ap, 0.0, 1.0)
    ap.command(1, [0, 0, 0.04, 0, 0, 0], 1.0, 1.0, 2.0)
    _run(ap, 1.0, 4.0)
    np.testing.assert_allclose(ap.applied[:3], [0, 0, 0.04], atol=5e-5)
    _check_limits(ap, p)


def test_window_is_clamped_to_1_3_s():
    ap = OffsetApplier(CoupleParams())
    ap.command(1, [0.01, 0, 0, 0, 0, 0], 1.0, 0.0, 0.2)
    assert ap.t_end == pytest.approx(1.0)
    ap.command(2, [0.01, 0, 0, 0, 0, 0], 1.0, 0.0, 9.0)
    assert ap.t_end == pytest.approx(3.0)


def test_reset_brakes_smoothly_without_a_jump():
    p = CoupleParams()
    ap = OffsetApplier(p)
    ap.command(1, [0.05, 0, 0, 0, 0, 0], 1.0, 0.0, 1.0)
    _run(ap, 0.0, 0.5)
    v0 = float(np.linalg.norm(ap.v[:3]))
    ap.reset(0.5, "flip")
    tr = []
    _run(ap, 0.5, 1.5, tr)
    speeds = [float(np.linalg.norm(v[:3])) for _, _, v in tr]
    assert v0 > 0.02 and speeds[-1] == 0.0
    assert all(b <= a + 1e-12 for a, b in zip(speeds, speeds[1:]))
    _check_limits(ap, p)


def test_rate_limit_leaves_a_rest_that_decays_and_is_dropped():
    p = CoupleParams(v_max=0.02)
    ap = OffsetApplier(p)
    ap.command(1, [0.05, 0, 0, 0, 0, 0], 1.0, 0.0, 1.0)
    _run(ap, 0.0, 3.0)
    assert ap.applied[0] < 0.05 - 0.02 and ap.dropped[0] > 0.0
    assert ap.v_seen <= 0.02 + 1e-9 and not ap.active


def test_scale_remaining_and_rotation():
    p = CoupleParams()
    ap = OffsetApplier(p)
    ap.command(1, [0.02, 0, 0, 0, 0, 0.2], 1.0, 0.0, 2.0)
    ap.scale_remaining(0.5, 0.0, "vla_contra")
    _run(ap, 0.0, 3.0)
    np.testing.assert_allclose(ap.applied, [0.01, 0, 0, 0, 0, 0.1], atol=5e-5)
    assert ap.stats()["scaled"] == 1 and ap.state_json()["weight"] == 1.0
