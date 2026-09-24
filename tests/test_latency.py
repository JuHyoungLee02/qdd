import json
import math

from harvest.analysis.latency import (censored_quantile, determinism, judge_e0, records_to_rows,
                                      votes_per_step)


def test_censored_p95_counts_failures_as_inf():
    assert censored_quantile([0.3] * 94 + [None] * 6, 0.95) == math.inf
    assert censored_quantile([0.3] * 96 + [None] * 4, 0.95) == 0.3
    assert censored_quantile([0.1] * 100, 0.95) == 0.1
    assert censored_quantile([0.1] * 94 + [2.5] * 6, 0.95) == math.inf


def _rows(lat, size="S1", N=1, slot="02", site="pod", ok=True, n=300):
    return [{"size": size, "N": N, "slot": slot, "site": site, "lat": lat, "ok": ok} for _ in range(n)]


def test_case_boundaries():
    for lat, case in [(0.10, "a"), (0.25, "b"), (0.6, "c"), (1.5, "d"), (2.5, "e")]:
        assert judge_e0(_rows(lat) + _rows(lat, size="S3"))["case"] == case


def test_failure_rate_over_2pct_is_case_e():
    rows = _rows(0.3, n=290) + _rows(None, ok=False, n=10) + _rows(0.3, size="S3")
    assert judge_e0(rows)["case"] == "e"


def test_nmax_formula_and_concurrency_penalty():
    rows = _rows(0.6) + _rows(0.6, size="S3") + _rows(0.6, N=3)
    assert judge_e0(rows)["N_max"] == math.ceil(0.6 / 0.33) + 1
    rows = _rows(0.6) + _rows(0.6, size="S3") + _rows(0.6, N=2) + _rows(0.9, N=3)
    assert judge_e0(rows)["N_max"] == 2


def test_pc_site_excluded_from_design_values():
    rows = _rows(0.3) + _rows(0.3, size="S3") + _rows(1.9, site="pc")
    assert judge_e0(rows)["d_p95_S1"] == 0.3


def test_worst_slot_note():
    rows = _rows(0.3, slot="02") + _rows(0.6, slot="10", n=10) + _rows(0.3, size="S3")
    assert any("block-randomize" in n for n in judge_e0(rows)["notes"])


def test_votes_per_step():
    assert votes_per_step(0.2) >= 2
    assert votes_per_step(1.4) < 2


def test_determinism_flip():
    same = {"j0": ["up"] * 5, "j1": ["down"] * 5}
    assert determinism(same)["flip"] == 0.0
    moved = {"j0": ["up", "up", "down", "up", "up"], "j1": ["down"] * 5}
    assert determinism(moved)["flip"] == 0.5


def test_records_to_rows(tmp_path):
    p = tmp_path / "s.jsonl"
    lines = [{"kind": "header"},
             {"kind": "call", "t_send": 1.0, "t_done": 1.4, "http_status": 200, "error": None,
              "meta": {"size": "S1", "N": 2, "slot": "KST02", "site": "pod", "phase": "closed"}},
             {"kind": "call", "t_send": 1.0, "t_done": 3.0, "http_status": 429, "error": "http_429",
              "meta": {"size": "S1", "N": 2, "slot": "KST02", "site": "pod", "phase": "closed"}}]
    p.write_text("\n".join(json.dumps(l) for l in lines), encoding="utf-8")
    rows = records_to_rows(p)
    assert len(rows) == 2 and rows[0]["lat"] == 0.4 and rows[0]["ok"] and rows[1]["lat"] is None
