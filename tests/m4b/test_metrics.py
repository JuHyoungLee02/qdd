"""E-M4b-meas metrics (pure): balanced accuracy, temperature, conformal sets, episode bootstrap, critic FWER/recall."""
import math

import numpy as np
import pytest

from harvest.m4b import metrics as M


def test_balanced_accuracy():
    y = [1, 1, 0, 0, 0, 0]
    assert M.balanced_accuracy(y, [1, 0, 0, 0, 0, 0]) == pytest.approx(0.75)
    assert M.balanced_accuracy(y, [0] * 6) == pytest.approx(0.5)  # majority answer = 0.5 by definition
    assert M.balanced_accuracy([1, 1], [1, 0]) is None  # one class missing


def test_counts_and_ba_from_counts():
    c = M.counts([1, 1, 0, 0], [1, 0, 0, 1])  # tp fn tn fp
    assert c.tolist() == [1, 1, 1, 1]
    assert M.ba_from_counts(np.array([3, 1, 4, 0])) == pytest.approx((0.75 + 1.0) / 2)
    assert math.isnan(M.ba_from_counts(np.array([0, 0, 4, 0])))


def test_temperature_recovers_scale():
    rng = np.random.default_rng(0)
    z = rng.normal(0, 2, 20000)
    y = (rng.random(20000) < 1 / (1 + np.exp(-z))).astype(int)
    T = M.fit_temperature(3.0 * z, y)  # logits 3x too sharp -> T ~ 3
    assert T == pytest.approx(3.0, rel=0.08)


def test_conformal_sets_binary():
    q = M.conformal_qhat([0.1, 0.2, 0.3, 0.4], alpha=0.25)  # ceil(5*0.75)=4th smallest -> 0.4
    assert q == pytest.approx(0.4)
    assert M.conformal_qhat([0.1, 0.2], alpha=0.05) == 1.0  # too few calibration points -> trivial set
    assert M.set_of(0.9, 0.4) == "true"  # 1-0.9 <= 0.4, 0.9 > 0.4
    assert M.set_of(0.1, 0.4) == "false"
    assert M.set_of(0.5, 0.6) == "unknown"
    assert M.set_of(0.5, 0.3) == "empty"


def test_nonconformity_scores():
    assert M.nonconf([0.9, 0.2], [1, 0]).tolist() == pytest.approx([0.1, 0.2])


def test_set_metrics():
    y = [1, 0, 1, 0]
    sets = ["true", "false", "unknown", "true"]
    m = M.set_metrics(y, sets)
    assert m["coverage"] == pytest.approx(0.75)
    assert m["singleton"] == pytest.approx(0.75)
    assert m["unknown"] == pytest.approx(0.25)
    assert m["false_precision"] == pytest.approx(1.0)


def test_episode_bootstrap_ba_and_paired_diff():
    rng = np.random.default_rng(1)
    E = 30
    ca = np.zeros((E, 4))
    cb = np.zeros((E, 4))
    for e in range(E):
        y = rng.integers(0, 2, 50)
        ca[e] = M.counts(y, y)  # perfect
        cb[e] = M.counts(y, np.zeros(50, int))  # majority -> BA 0.5
    lo, hi = M.boot_ba_ci(ca[:, None, :], n=500)
    assert lo == pytest.approx(1.0) and hi == pytest.approx(1.0)
    dlo, dhi = M.boot_ba_diff_ci(ca[:, None, :], cb[:, None, :], n=500)
    assert dlo == pytest.approx(0.5) and dhi == pytest.approx(0.5)


def test_persist_min_of_last_k():
    assert M.persist([0.1, 0.9, 0.8, 0.2, 0.95], 2).tolist() == pytest.approx([0.1, 0.1, 0.8, 0.2, 0.2])


def test_fwer_threshold_and_first_alarm():
    th = M.fwer_threshold([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], alpha=0.2)
    assert th == pytest.approx(0.9)  # ceil(11 * 0.8) = 9th smallest
    assert M.fwer_threshold([0.3, 0.5], alpha=0.05) == pytest.approx(0.5)  # n too small -> the max
    assert M.first_alarm([0.0, 0.33, 0.66], [0.1, 0.95, 0.99], 0.9) == pytest.approx(0.33)
    assert M.first_alarm([0.0, 0.33], [0.1, 0.2], 0.9) is None


def test_fixed_window_detection():
    assert M.detected(1.2, onset=1.0, tau=2.0) is True
    assert M.detected(3.1, onset=1.0, tau=2.0) is False
    assert M.detected(0.5, onset=1.0, tau=2.0) is False  # first alarm before onset = false intervention
    assert M.detected(None, onset=1.0, tau=2.0) is False
