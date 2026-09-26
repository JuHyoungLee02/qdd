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


# ---- Task 17 (canon §84 supplement 8): authority a scales the commanded velocity BEFORE the rate/accel limits
def _run_a(ap, t0, t1, a_of, trace=None):
    t = t0
    while t < t1 - 1e-9:
        s = ap.step(t, DT, authority=a_of(t))
        if trace is not None:
            trace.append((t, s.copy(), ap.v.copy()))
        t = round(t + DT, 6)
    return t


def test_authority_zero_for_the_whole_window_applies_nothing():
    ap = OffsetApplier(CoupleParams())
    ap.command(1, [0.02, 0.0, 0.01, 0.0, 0.0, 0.1], 1.0, 0.0, 2.0)
    tr = []
    _run_a(ap, 0.0, 4.0, lambda t: 0.0, tr)
    assert all(not np.any(s) for _, s, _ in tr)  # exactly zero every tick
    assert np.all(ap.applied == 0.0) and not ap.active and ap.dropped[0] == pytest.approx(0.02)


def test_authority_drop_brakes_within_the_accel_limit_and_resumes_smoothly():
    p = CoupleParams()
    ap = OffsetApplier(p)
    ap.command(1, [0.06, 0, 0, 0, 0, 0], 1.0, 0.0, 3.0)
    tr = []
    _run_a(ap, 0.0, 4.0, lambda t: 0.0 if 0.8 <= t < 1.4 else 1.0, tr)  # a drops immediately, comes back at once
    v = [float(np.linalg.norm(x[:3])) for _, _, x in tr]
    acc = [abs(b - a) / DT for a, b in zip(v, v[1:]) if b > 0.0]  # b = 0: the landing tick (lands on the rest)
    assert max(acc) <= p.a_max + 1e-6 and ap.a_seen <= p.a_max + 1e-6 and ap.v_seen <= p.v_max + 1e-9
    assert v[int(0.8 / DT)] < v[int(0.8 / DT) - 1]  # it brakes (no one-tick stop, no jump)
    assert v[int(1.3 / DT)] == 0.0  # stopped inside the a = 0 span
    np.testing.assert_allclose(ap.applied[:3], [0.06, 0, 0], atol=1e-4)  # the plan was kept, it resumed


@pytest.mark.parametrize("axis,vec,vmax_name,amax_name", [
    (0, [0.5, 0, 0, 0, 0, 0], "v_max", "a_max"),  # translation: bound v^2 / (2 a_max) <= 1 cm
    (5, [0, 0, 0, 0, 0, 5.0], "w_max", "alpha_max"),  # rotation: bound w^2 / (2 alpha_max) <= 0.1875 rad
])
def test_authority_drop_just_before_the_window_end_travels_at_most_the_braking_bound(axis, vec, vmax_name, amax_name):
    # F17: a -> 0 at t_end - 0.05 s; the post-window decay (|v| / decay_s, gentler than a_max) must not stretch the
    # travel at a = 0 beyond the a_max braking distance
    p = CoupleParams()
    ap = OffsetApplier(p)
    ap.command(1, vec, 1.0, 0.0, 3.0)
    t = _run_a(ap, 0.0, 3.0 - 0.05, lambda t: 1.0)
    sl = slice(0, 3) if axis < 3 else slice(3, 6)
    v0 = float(np.linalg.norm(ap.v[sl]))
    x0 = float(ap.applied[axis])
    _run_a(ap, t, 6.0, lambda t: 0.0)
    assert v0 > 0.9 * getattr(p, vmax_name)
    assert float(ap.applied[axis]) - x0 <= v0 ** 2 / (2.0 * getattr(p, amax_name)) + 1e-9
    assert not ap.active


def test_authority_half_caps_the_speed_at_half():
    p = CoupleParams()
    ap = OffsetApplier(p)
    ap.command(1, [0.2, 0, 0, 0, 0, 0], 1.0, 0.0, 3.0)
    _run_a(ap, 0.0, 3.0, lambda t: 0.5)
    assert ap.v_seen <= 0.5 * p.v_max + 1e-9 and ap.v_seen > 0.45 * p.v_max


def test_stats_report_absolute_sums_next_to_the_signed_net():
    ap = OffsetApplier(CoupleParams())
    ap.command(1, [0.02, 0, 0, 0, 0, 0.1], 1.0, 0.0, 1.0)
    _run(ap, 0.0, 2.0)
    ap.command(2, [-0.02, 0, 0, 0, 0, -0.1], 1.0, 2.0, 1.0)
    _run(ap, 2.0, 4.0)
    s = ap.stats()
    assert s["applied_m"][0] == pytest.approx(0.0, abs=1e-4) and s["applied_abs_m"][0] == pytest.approx(0.04, abs=1e-4)
    assert s["applied_abs_rad"][2] == pytest.approx(0.2, abs=1e-3) and s["applied_abs_m"][1] == 0.0
