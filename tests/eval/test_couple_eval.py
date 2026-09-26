import json
from types import SimpleNamespace

import pytest

from harvest.couple.cost import PriceTable
from harvest.eval import couple as CP
from harvest.eval.closed import aggregate

TEST = PriceTable("test", "2026-09-26", 2.0, 0.5, 8.0, 1400.0, "unit test")


def test_arms_labels_and_configs():
    assert CP.parse_arms("off,serial") == ["off", "serial"]
    with pytest.raises(SystemExit, match="couple"):
        CP.parse_arms("serial,stagger")
    assert CP.arm_config("off") == {"couple": "off"}
    assert CP.arm_config("serial_pause", 3.0) == {"couple": "serial", "couple_params": {"phase_pause_s": 3.0}}
    assert CP.arm_config("serial", min_interval_s=4.2) == {"couple": "serial", "couple_params": {"min_interval_s": 4.2}}
    assert CP.couple_label("C5", "serial", ["off"]) == "C5" and CP.couple_label("C5", "serial", ["off", "serial"]) == "C5|cp-serial"


def test_paid_runs_need_prices_budget_ledger_and_approval():
    base = dict(couple_prices="p.json", couple_budget_krw=25000.0, couple_ledger="/data/x.jsonl", approval="prereg_couple.md §0 self-check")
    CP.check_paid(SimpleNamespace(**base))
    for k, v in (("approval", ""), ("couple_prices", ""), ("couple_budget_krw", 0.0), ("couple_ledger", "")):
        with pytest.raises(SystemExit):
            CP.check_paid(SimpleNamespace(**{**base, k: v}))


def test_mock_stream_client_answers_in_both_modes():
    from harvest.couple.params import CoupleParams
    from harvest.couple.prompt import build_input
    from harvest.couple.schema import parse_answer
    c, mode = CP.stream_client({"astra": "mock", "couple_upper": "astra"})
    for m in ("F0", "F1"):
        rec = c.call(build_input({"request_no": 1, "mode": m}, {}, CoupleParams(request_mode=m), "t"), "low", 10, {})
        assert parse_answer(rec.output_text, m, (), 1, 0.0, 1.0).command == "continue"
    assert mode == "mock"


def test_estimate_serial_and_pause():
    e = CP.estimate(TEST, episodes=40, episode_s=60.0, latency_s=4.0, in_tokens=3500, out_tokens=1000)
    per = TEST.krw({"input_tokens": 3500, "output_tokens": 1000})
    assert e["calls"] == pytest.approx(600.0) and e["krw"] == pytest.approx(600 * per)
    p = CP.estimate(TEST, 40, 60.0, 4.0, 3500, 1000, phase_pause_s=8.0, dense_frac=0.3)
    assert p["calls"] == pytest.approx(40 * (0.3 * 60 / 4 + 0.7 * 60 / 8))


def _trial(cond, seed, ok, excluded=False, cost=10.0):
    c = {"calls_sent": 12, "latency_s": {"p50": 4.0, "p95": 6.0}, "answer_age_s": {"p50": 4.1}, "cost_krw": cost,
         "timeouts": 0, "schema_errors": 0, "gates": {"ok": 10}, "layer": {"apply": 1}, "irrev": {},
         "events": {}, "max_outstanding": 1, "budget_excluded": excluded}
    return {"variant": "standard", "condition": cond, "seed": seed, "epoch": 0, "success": ok, "sim_time": 30.0,
            "termination": "success" if ok else None, "summary": {"couple": c if "serial" in cond else None}}


def test_aggregate_excludes_budget_stopped_episodes_and_pairs_the_arms():
    trials = [_trial("C5|cp-off", s, s % 2 == 0) for s in range(6)]
    trials += [_trial("C5|cp-serial", s, True) for s in range(5)] + [_trial("C5|cp-serial", 5, False, excluded=True)]
    res = aggregate(trials, n_boot=200)
    assert res["couple_budget_excluded"] == 1
    d = res["couple_diff"]["C5|cp-serial - C5|cp-off/standard"]
    assert d["n_pairs"] == 5 and d["mean"] == pytest.approx(0.4)
    cell = res["cells"]["C5|cp-serial/standard"]["couple"]
    assert cell["episodes"] == 5 and cell["cost_krw_total"] == pytest.approx(50.0)


def test_estimate_cli(tmp_path, capsys):
    f = tmp_path / "prices.json"
    f.write_text(json.dumps({"model": "test", "date": "2026-09-26", "usd_per_mtok_input": 2.0,
                             "usd_per_mtok_cached_input": 0.5, "usd_per_mtok_output": 8.0, "krw_per_usd": 1400.0,
                             "source": "unit test"}))
    CP.main(["estimate", "--prices", str(f), "--episodes", "40", "--episode-s", "60", "--latency-s", "4",
             "--in-tokens", "3500", "--out-tokens", "1000"])
    out = json.loads(capsys.readouterr().out)
    assert out["calls"] == pytest.approx(600.0) and out["price_date"] == "2026-09-26"


def _trial_adh(cond, seed, ok, n, follow_rate):
    """Controller ruling C4: couple_cell() also pools driver.summary()['adherence'] at chunk level."""
    c = {"calls_sent": 12, "latency_s": {"p50": 4.0, "p95": 6.0}, "answer_age_s": {"p50": 4.1}, "cost_krw": 10.0,
         "timeouts": 0, "schema_errors": 0, "gates": {"ok": 10}, "layer": {"apply": 1}, "irrev": {},
         "events": {}, "max_outstanding": 1, "budget_excluded": False,
         "adherence": {"chunk_vs_offset": {"n": n, "follow_rate": follow_rate},
                       "chunk_vs_decision": {"n": n, "follow_rate": follow_rate}}}
    return {"variant": "standard", "condition": cond, "seed": seed, "epoch": 0, "success": ok, "sim_time": 30.0,
            "termination": "success" if ok else None, "summary": {"couple": c}}


def test_couple_cell_pools_chunk_level_adherence():
    from harvest.eval.couple import couple_cell
    summaries = [_trial_adh("C5|cp-serial", 0, True, 10, 0.8)["summary"],
                 _trial_adh("C5|cp-serial", 1, True, 5, 0.4)["summary"],
                 _trial_adh("C5|cp-serial", 2, True, 0, None)["summary"]]
    cell = couple_cell(summaries)
    # pooled: (10*0.8 + 5*0.4) / (10+5) = 10/15
    assert cell["adherence"]["chunk_vs_offset"]["n"] == 15
    assert cell["adherence"]["chunk_vs_offset"]["follow_rate"] == pytest.approx(10 / 15, abs=1e-4)
    assert cell["adherence"]["chunk_vs_decision"]["n"] == 15
    assert cell["adherence"]["chunk_vs_decision"]["follow_rate"] == pytest.approx(10 / 15, abs=1e-4)


def test_couple_cell_adherence_none_when_all_n_zero_or_missing():
    from harvest.eval.couple import couple_cell
    summaries = [_trial("C5|cp-serial", 0, True)["summary"]]  # no "adherence" key at all
    cell = couple_cell(summaries)
    assert cell["adherence"]["chunk_vs_offset"] == {"n": 0, "follow_rate": None}
    assert cell["adherence"]["chunk_vs_decision"] == {"n": 0, "follow_rate": None}
