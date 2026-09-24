"""M4 measure() source table + M7 critic (canon §61, §64): world <- V1h (conformal, empty = unknown), robot T1 <- proprio
code rules (hard), critic alarm = V1h only."""
import json
import math

import pytest

from harvest.runtime import measure as MS


def _logit(p):
    return math.log(p / (1 - p))


def test_source_table_per_canon_64():
    for p in ("gripper_open", "holding_t", "lifted_holding"):
        assert MS.SOURCE_TABLE[p] == ("proprio", "T1")
    for p in ("on_tp", "contact_tp", "lifted_t", "near_tp", "above_tp", "contact_stall"):
        assert MS.SOURCE_TABLE[p] == ("v1h", "T2")  # contact_stall = T2 (PC2 list excludes it)


def test_proprio_rules_registered_thresholds():
    r = MS.ProprioRules()
    assert r.eval(0.107, 0.05, 0.02) == {"gripper_open": True, "holding_t": False, "lifted_holding": False}
    assert r.eval(0.064, 3.0, 0.05) == {"gripper_open": False, "holding_t": True, "lifted_holding": False}
    assert r.eval(0.064, 3.0, 0.20) == {"gripper_open": False, "holding_t": True, "lifted_holding": True}
    assert r.eval(0.049, 3.0, 0.20)["holding_t"] is False  # closed on nothing (below the band)
    assert r.eval(0.064, 0.5, 0.20)["holding_t"] is False  # no grip effort
    assert r.eval(0.064, -3.0, 0.20)["holding_t"] is True  # effort sign does not matter (|effort|)


def test_conformal_value_empty_and_both_are_unknown():
    assert MS.conformal_value(0.99, 0.05) is True
    assert MS.conformal_value(0.01, 0.05) is False
    assert MS.conformal_value(0.5, 0.6) is None  # both labels in the set
    assert MS.conformal_value(0.5, 0.1) is None  # empty set -> unknown (canon §64 decision)


def test_measure_sources_and_unknown_without_head():
    cal = MS.VerifyCal.default()
    m = MS.measure({"width": 0.064, "grip_effort": 2.0, "tcp_z": 0.2}, None, cal)
    assert m["holding_t"]["value"] is True and m["holding_t"]["tier"] == "T1" and m["holding_t"]["source"] == "proprio"
    assert m["on_tp"]["value"] is None and m["on_tp"]["source"] == "v1h"  # no head output -> unknown
    lg = {p: _logit(0.02) for p in MS.PREDS}
    lg["on_tp"] = _logit(0.98)
    m = MS.measure(None, lg, cal)
    assert m["on_tp"]["value"] is True and m["contact_tp"]["value"] is False
    assert m["holding_t"]["value"] is None  # robot side never taken from the head (T1 = proprio code)
    assert abs(m["on_tp"]["p"] - 0.98) < 1e-6


def test_temperature_applied():
    cal = MS.VerifyCal(T={p: 2.0 for p in MS.PREDS}, qhat={p: 0.1 for p in MS.PREDS}, critic_thr=None)
    p = MS.v1h_probs({"on_tp": 4.0}, cal)["on_tp"]
    assert abs(p - 1 / (1 + math.exp(-2.0))) < 1e-9


def test_expected_check_t1_contradict_t2_deviate_unknown_ok():
    cal = MS.VerifyCal.default()
    lg = {p: _logit(0.02) for p in MS.PREDS}
    # lift expects holding & not open: an empty close (proprio) -> T1 false -> CONTRADICT (hard)
    m = MS.measure({"width": 0.045, "grip_effort": 0.1, "tcp_z": 0.1}, lg, cal)
    c = MS.expected_check("lift", m)
    assert c["outcome"] == "CONTRADICT" and "holding_t" in c["t1_false"] and c["hard"]
    # carry with holding (T1 ok) but the head says the mug is not lifted -> T2 false -> DEVIATE (soft only)
    m = MS.measure({"width": 0.064, "grip_effort": 2.0, "tcp_z": 0.2}, lg, cal)
    c = MS.expected_check("carry", m)
    assert c["outcome"] == "DEVIATE" and c["t2_false"] == ["lifted_t"] and not c["hard"]
    # no head output: world side unknown never contradicts
    m = MS.measure({"width": 0.064, "grip_effort": 2.0, "tcp_z": 0.2}, None, cal)
    c = MS.expected_check("carry", m)
    assert c["outcome"] == "OK" and "lifted_t" in c["unknown"]
    # OR entry of place_descend: above or contact
    lg2 = dict(lg, above_tp=_logit(0.97))
    m = MS.measure({"width": 0.064, "grip_effort": 2.0, "tcp_z": 0.2}, lg2, cal)
    assert MS.expected_check("place_descend", m)["outcome"] == "OK"
    assert MS.expected_check("close", m)["outcome"] == "OK"  # transition phases expect nothing


def test_expected_check_scope_t1_only_and_t2_only():
    """The runtime checks the robot side at the step end (T1 only) and the world side on the next head output (T2
    only): predicates outside the given scope are skipped, never read."""
    cal = MS.VerifyCal.default()
    lg = {p: _logit(0.02) for p in MS.PREDS}
    m = MS.measure({"width": 0.045, "grip_effort": 0.1, "tcp_z": 0.1}, lg, cal)
    t1 = {p: v for p, v in m.items() if v["tier"] == "T1"}
    t2 = {p: v for p, v in m.items() if v["tier"] == "T2"}
    assert MS.expected_check("carry", t1)["t1_false"] == ["holding_t", "lifted_holding"]
    c = MS.expected_check("carry", t2)
    assert c["t1_false"] == [] and c["t2_false"] == ["lifted_t"] and c["outcome"] == "DEVIATE"


def test_critic_v1h_only_with_persistence():
    cal = MS.VerifyCal(T={p: 1.0 for p in MS.PREDS}, qhat={p: 0.1 for p in MS.PREDS}, critic_thr=0.9)
    cr = MS.Critic(cal)
    ok = {p: _logit(0.02) for p in MS.PREDS}
    ok.update(holding_t=_logit(0.98), lifted_holding=_logit(0.98), lifted_t=_logit(0.98))
    bad = dict(ok, holding_t=_logit(0.01), lifted_holding=_logit(0.01))  # dropped mug during carry
    assert cr.update(1.0, "carry", ok)["alarm"] is False
    r = cr.update(1.33, "carry", bad)
    assert r["alarm"] is False and r["raw"] > 0.9  # one snapshot only: persistence 2
    r = cr.update(1.66, "carry", bad)
    assert r["alarm"] is True and r["score"] > 0.9
    assert cr.alarms == [1.66]


def test_critic_without_threshold_never_alarms_and_says_so():
    cr = MS.Critic(MS.VerifyCal.default())
    bad = {p: _logit(0.01) for p in MS.PREDS}
    for t in (0.0, 0.33, 0.66):
        r = cr.update(t, "carry", bad)
    assert r["alarm"] is False and r["thr"] is None and r["score"] > 0.9


def test_hard_channel_t1_two_ticks():
    h = MS.HardChannel()
    empty = MS.measure({"width": 0.04, "grip_effort": 0.0, "tcp_z": 0.2}, None, MS.VerifyCal.default())
    assert h.update(1.0, "carry", empty) is None
    ev = h.update(1.33, "carry", empty)
    assert ev is not None and ev["preds"] == ["holding_t", "lifted_holding"] and ev["t"] == 1.33
    assert h.update(1.66, "carry", empty) is None  # one event per episode of violation
    held = MS.measure({"width": 0.064, "grip_effort": 2.0, "tcp_z": 0.2}, None, MS.VerifyCal.default())
    assert h.update(2.0, "carry", held) is None


def test_cal_json_roundtrip_and_m4b_import(tmp_path):
    res = {"m4b": {"V1h_temperature": {p: 1.1 for p in MS.PREDS},
                   "V1h": {"per_pred": {p: {"qhat": 0.05} for p in MS.PREDS}},
                   "P_params": {"th_w": 0.0805, "th_lo": 0.0501, "th_hi": 0.08, "th_I": 1.14, "th_z": 0.124}},
           "critic": {"V1h": {"thr": {"v1h": 0.947}, "alpha_per_channel": 0.05}}}
    f = tmp_path / "results.json"
    f.write_text(json.dumps(res))
    cal = MS.VerifyCal.from_m4b_results(str(f), head="m4b/v1h")
    assert cal.calibrated and cal.critic_thr == 0.947 and cal.qhat["on_tp"] == 0.05 and cal.T["on_tp"] == 1.1
    out = tmp_path / "cal.json"
    cal.save(str(out))
    c2 = MS.VerifyCal.load(str(out))
    assert c2.T == cal.T and c2.qhat == cal.qhat and c2.critic_thr == cal.critic_thr and c2.head == "m4b/v1h"
    r = MS.ProprioRules.from_m4b_results(str(f))
    assert r.th_I == 1.14


def test_default_cal_is_flagged_uncalibrated():
    c = MS.VerifyCal.default()
    assert not c.calibrated and c.critic_thr is None
    with pytest.raises(ValueError):
        MS.VerifyCal(T={}, qhat={}, critic_thr=None, alpha=0.1).check()
