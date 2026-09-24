"""P: proprioceptive code rules for the robot-side predicates (pure)."""
import numpy as np
import pytest

from harvest.m4b import prules as P


def test_fit_threshold_up_and_down():
    x = np.array([0.1, 0.2, 0.3, 0.7, 0.8, 0.9])
    y = np.array([0, 0, 0, 1, 1, 1])
    th = P.fit_threshold(x, y, +1)
    assert 0.3 < th <= 0.7
    th2 = P.fit_threshold(-x, y, -1)
    assert -0.7 <= th2 < -0.3


def _feats(n=400, seed=0):
    rng = np.random.default_rng(seed)
    w = rng.uniform(0.03, 0.107, n)
    g = rng.uniform(0, 5, n)
    z = rng.uniform(0.0, 0.3, n)
    r = rng.uniform(0, 10, n)
    return {"width": w, "grip_tau": g, "tcp_z": z, "tau_res": r}


def _truth(f):
    op = f["width"] >= 0.08
    hold = (f["width"] > 0.055) & (f["width"] < 0.08) & (f["grip_tau"] >= 2.0)
    return {"gripper_open": op, "holding_t": hold, "lifted_holding": hold & (f["tcp_z"] >= 0.12),
            "contact_stall": op & (f["tau_res"] >= 6.0)}


def test_fit_and_apply_recovers_rules():
    f = _feats()
    t = _truth(f)
    par = P.fit(f, t)
    f2 = _feats(seed=1)
    t2 = _truth(f2)
    out = P.apply(f2, par)
    for k in P.ROBOT:
        acc = (out[k] == t2[k]).mean()
        assert acc > 0.95, (k, acc)


def test_scores_are_probability_like_and_agree_with_rule():
    f = _feats()
    par = P.fit(f, _truth(f))
    out = P.apply(f, par)
    sc = P.scores(f, par)
    for k in P.ROBOT:
        assert ((sc[k] >= 0) & (sc[k] <= 1)).all()
        assert ((sc[k] >= 0.5) == out[k]).mean() > 0.99


def test_noisy_effort_is_deterministic():
    tau = np.ones((5, 7))
    lim = np.full(7, 10.0)
    a = P.noisy(tau, lim, seed=3)
    b = P.noisy(tau, lim, seed=3)
    assert np.array_equal(a, b) and not np.array_equal(a, tau)
    assert np.std(P.noisy(np.zeros((20000, 7)), lim, seed=0)) == pytest.approx(0.2, rel=0.05)
