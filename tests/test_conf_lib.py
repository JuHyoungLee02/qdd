"""E-CONF pure helpers (docs/stage3/prereg_conf.md): decision-confidence scores, calibration-split fits, held-out
selection, joint bootstrap, runtime-use simulation."""
import importlib.util
import math
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, *rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


L = _load("conf_lib", ("tools", "conf", "conf_lib.py"))


def _q(lp, target, pred=None):
    return {"lp": lp, "target": target, "pred": pred or max(lp, key=lp.get)}


def _rec(m1, m2, ok1=True, ok2=True, mse=0.01, disp=0.001, ep="e0", t=0.0):
    a = {"x": 0.0, "y": -m1}
    b = {"u": 0.0, "v": -m2, "w": -m2 - 1.0}
    return {"id": f"{ep}/{t}", "ep": ep, "t": t, "mse": mse, "disp": disp,
            "q": {"qa": _q(a, ["x"] if ok1 else ["y"]), "qb": _q(b, ["u"] if ok2 else ["v"])}}


# ------------------------------------------------------------------------------------------ margins
def test_margin_is_top1_minus_top2():
    assert L.margin({"a": -0.1, "b": -2.1, "c": -5.0}) == pytest.approx(2.0)


def test_margin_single_option_is_large():
    assert L.margin({"a": -0.3}) == 99.0


def test_snap_conf_min_and_argmin():
    c = L.snap_conf(_rec(3.0, 0.5)["q"])
    assert c["min"] == pytest.approx(0.5) and c["argmin"] == "qb"
    assert c["margins"] == {"qa": pytest.approx(3.0), "qb": pytest.approx(0.5)}


def test_dec_error_any_question_wrong():
    assert not L.dec_error(_rec(1, 1))
    assert L.dec_error(_rec(1, 1, ok2=False))


def test_empty_target_counts_as_wrong_like_nov0():
    r = _rec(1, 1)
    r["q"]["qa"]["target"] = []
    assert L.dec_error(r)


def test_large_error_uses_given_threshold():
    y = L.large_error([False, True, False], [0.1, 0.0, 0.5], 0.5)
    assert y.tolist() == [False, True, True]


# ------------------------------------------------------------------------------------------ fits and scores
def _cal(n=400, seed=0):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        m1, m2 = rng.exponential(2.0), rng.exponential(1.0)
        ok1 = rng.random() < 1 / (1 + math.exp(-2 * m1))
        ok2 = rng.random() < 1 / (1 + math.exp(-2 * m2))
        mse = float(rng.exponential(0.02) * (1 + 3 * (m2 < 0.3)))
        out.append(_rec(m1, m2, ok1, ok2, mse, disp=float(rng.exponential(0.01)), ep=f"e{i // 10}", t=0.33 * (i % 10)))
    return out


def test_fit_has_every_part_and_q90_threshold():
    cal = _cal()
    f = L.fit(cal)
    assert set(f) >= {"qs", "mse_thr", "temps", "qhat", "lr", "lr_flow", "platt", "tau90"}
    assert f["qs"] == ["qa", "qb"]
    assert f["mse_thr"] == pytest.approx(float(np.quantile([r["mse"] for r in cal], 0.9)))
    assert all(t > 0 for t in f["temps"].values())
    assert set(f["tau90"]) == set(L.SCORES)


def test_base_risk_is_minus_min_margin():
    f = L.fit(_cal())
    r = _rec(3.0, 0.5)
    assert L.risk(r, "base", f) == pytest.approx(-0.5)


def test_temp_min_divides_margins_by_temperature():
    f = L.fit(_cal())
    f["temps"] = {"qa": 2.0, "qb": 0.25}
    r = _rec(3.0, 0.5)
    assert L.risk(r, "temp_min", f) == pytest.approx(-min(3.0 / 2.0, 0.5 / 0.25))


def test_temp_joint_is_neg_log_prob_all_top1():
    f = L.fit(_cal())
    f["temps"] = {"qa": 1.0, "qb": 1.0}
    r = _rec(1.0, 1.0)
    pa = 1 / (1 + math.exp(-1.0))
    pb = math.exp(0) / (math.exp(0) + math.exp(-1) + math.exp(-2))
    assert L.risk(r, "temp_joint", f) == pytest.approx(-math.log(pa) - math.log(pb))


def test_conf_set_size_counts_extra_options():
    f = L.fit(_cal())
    f["temps"] = {"qa": 1.0, "qb": 1.0}
    f["qhat"] = {"qa": 0.99, "qb": 0.01}
    r = _rec(0.1, 5.0)
    assert L.risk(r, "conf_set", f) == pytest.approx(1.0)  # qa keeps both options, qb only the top one


def test_conf_set_infinite_qhat_keeps_all_options():
    f = L.fit(_cal())
    f["qhat"] = {"qa": float("inf"), "qb": float("inf")}
    assert L.risk(_rec(1, 1), "conf_set", f) == pytest.approx(1 + 2)


def test_flow_risk_is_log_dispersion():
    f = L.fit(_cal())
    assert L.risk(_rec(1, 1, disp=0.01), "flow", f) == pytest.approx(math.log(0.01 + 1e-12))


def test_lr_risk_is_probability_and_orders_low_margin_higher():
    f = L.fit(_cal(2000))
    lo, hi = L.risk(_rec(0.05, 0.05), "lr", f), L.risk(_rec(6.0, 6.0), "lr", f)
    assert 0 < hi < lo < 1


def test_missing_question_feature_is_clip():
    f = L.fit(_cal())
    r = _rec(1.0, 1.0)
    del r["q"]["qb"]
    x = L.features(r, f)
    assert x[1] == L.CLIP and x[2] == pytest.approx(1.0)  # [qa, qb, min]


def test_logreg_recovers_direction():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(3000, 2))
    y = rng.random(3000) < 1 / (1 + np.exp(-(2 * X[:, 0] - 1 * X[:, 1])))
    m = L.logreg_fit(X, y, l2=1.0)
    w = np.asarray(m["w"]) / np.asarray(m["sd"])
    assert w[0] > 1.5 and -1.5 < w[1] < -0.5


def test_platt_is_monotone_in_base_risk():
    f = L.fit(_cal())
    a, b = L.platt_prob(f, -2.0), L.platt_prob(f, -0.1)
    assert 0 < a < b < 1


def test_scores_array_order():
    f = L.fit(_cal())
    recs = [_rec(3, 3), _rec(0.2, 0.2)]
    s = L.scores(recs, f)
    assert set(s) == set(L.SCORES) and s["base"].tolist() == [-3.0, -0.2]


# ------------------------------------------------------------------------------------------ held-out selection
def _eps():
    out = []
    for v in ("standard", "dr"):
        for s in range(10000, 10010):
            out.append({"variant": v, "task": "bottle_tray", "kind": "P0", "seed": s, "valid": s % 3 == 0})
            out.append({"variant": v, "task": "mug_tray", "kind": "P0", "seed": s, "valid": s != 10001})
    return out


def test_select_heldout_only_invalid_and_capped():
    sel = L.select_heldout(_eps(), cap=4, seed=0)
    bt = [x for x in sel if x[1] == "bottle_tray"]
    assert all(x[3] % 3 != 0 for x in sel if x[1] == "bottle_tray")
    assert len([x for x in bt if x[0] == "standard"]) == 4 and len([x for x in bt if x[0] == "dr"]) == 4
    assert [x for x in sel if x[1] == "mug_tray"] == [("dr", "mug_tray", "P0", 10001), ("standard", "mug_tray", "P0", 10001)]
    assert sel == sorted(sel)
    assert L.select_heldout(_eps(), cap=4, seed=0) == sel


def test_layout_unseen_needs_every_variant_invalid():
    eps = _eps()
    eps.append({"variant": "dr", "task": "mug_tray", "kind": "P0", "seed": 10020, "valid": False})
    eps.append({"variant": "standard", "task": "mug_tray", "kind": "P0", "seed": 10020, "valid": True})
    assert L.layout_unseen(("dr", "mug_tray", "P0", 10001), eps)
    assert not L.layout_unseen(("dr", "mug_tray", "P0", 10020), eps)


# ------------------------------------------------------------------------------------------ splits and bootstrap
def test_half_of_is_stable_and_balanced():
    h = [L.half_of(f"RB1_ep{i}") for i in range(400)]
    assert set(h) == {0, 1} and 150 < sum(h) < 250
    assert L.half_of("RB1_ep7") == L.half_of("RB1_ep7")


def test_joint_draws_average_units_and_share_draws():
    rng = np.random.default_rng(0)
    n = 600
    cl = np.repeat(np.arange(60), 10)
    y1 = rng.random(n) < 0.3
    y2 = rng.random(n) < 0.3
    s1 = y1 + rng.normal(0, 1, n)
    s2 = y2 + rng.normal(0, 1, n)
    d = L.joint_auroc_draws({"s": [s1, s2]}, [y1, y2], cl, n_boot=200, seed=0)
    assert d["s"].shape == (200,)
    pt = L.joint_auroc({"s": [s1, s2]}, [y1, y2])["s"]
    assert pt == pytest.approx((L.auroc(s1, y1) + L.auroc(s2, y2)) / 2)
    assert np.quantile(d["s"], 0.025) < pt < np.quantile(d["s"], 0.975)


def test_reduction90_in_sample():
    s = np.array([5, 4, 3, 2, 1, 0], float)
    y = np.array([1, 1, 1, 0, 0, 0], bool)
    assert L.reduction90(s, y) == pytest.approx(0.5)


# ------------------------------------------------------------------------------------------ flow dispersion
def test_dispersion_mean_variance_over_valid_steps():
    Z = np.zeros((2, 3, 2))
    Z[1, 0, :] = 2.0  # step 0: values 0 and 2 -> variance 1 per dim
    Z[1, 2, :] = 10.0  # step 2 invalid
    assert L.dispersion(Z, [1, 1, 0]) == pytest.approx((1 + 1 + 0 + 0) / 4)


def test_extra_noise_seeds_are_distinct_from_primary():
    s = L.noise_seeds(7, 4)
    assert s[0] == 7 and len(set(s)) == 5 and s[1] == 1_000_003 + 7


# ------------------------------------------------------------------------------------------ runtime use
def test_runtime_sim_rates_and_conservative_time():
    # one episode, decisions every 0.5 s over 10 s (20 decisions), flags at t = 1.0 and t = 1.5 and t = 7.0
    ts = [0.5 * i for i in range(20)]
    fl = [t in (1.0, 1.5, 7.0) for t in ts]
    r = L.runtime_sim({"e": list(zip(ts, fl))}, lat_s=4.0)
    assert r["decisions_per_min"] == pytest.approx(120.0)
    assert r["flag_rate_per_min"] == pytest.approx(120.0 * 3 / 20)
    # intervals [0,4) [4,8) [8,10): flags in 1st and 2nd -> 2/3
    assert r["priority_frac"] == pytest.approx(2 / 3)
    assert r["priority_per_min"] == pytest.approx(2 / 3 * 60 / 4.0)
    # canon §95: conservative from the flag until the prioritised request's answer (sent at the next boundary,
    # answered one latency later): flag 1.0 -> [1, 8), flag 7.0 -> [7, 12) clipped to 10 -> one bout [1, 10)
    assert r["conservative_frac"] == pytest.approx(0.9)
    assert r["bout_median_s"] == pytest.approx(9.0)


def test_runtime_sim_single_flag_bout():
    ts = [0.5 * i for i in range(40)]
    r = L.runtime_sim({"e": [(t, t == 1.0) for t in ts]}, lat_s=4.0)
    assert r["conservative_frac"] == pytest.approx(7.0 / 20.0)
    assert r["bout_median_s"] == pytest.approx(7.0) and r["n_bouts"] == 1
