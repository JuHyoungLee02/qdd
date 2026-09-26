import json

import pytest

from harvest.couple.cost import CostLedger, PriceTable, estimate_input_tokens

TEST = PriceTable(model="test", date="2026-09-26", usd_per_mtok_input=2.0, usd_per_mtok_cached_input=0.5,
                  usd_per_mtok_output=8.0, krw_per_usd=1400.0, source="unit test (not a real price)")


def test_price_math_counts_cached_input_separately():
    u = {"input_tokens": 3000, "input_tokens_details": {"cached_tokens": 1000}, "output_tokens": 800}
    assert TEST.krw(u) == pytest.approx((2000 * 2.0 + 1000 * 0.5 + 800 * 8.0) / 1e6 * 1400.0)
    assert TEST.krw_upper(3000, 1200) == pytest.approx((3000 * 2.0 + 1200 * 8.0) / 1e6 * 1400.0)
    assert estimate_input_tokens(2500, ["cam_head", "cam_wrist_right", "cam_wrist_left"]) == 2500 + 302 + 2 * 152


def test_load_refuses_incomplete_tables(tmp_path):
    p = tmp_path / "prices.json"
    p.write_text(json.dumps({"model": "gpt-6-astra", "date": "2026-09-26", "usd_per_mtok_input": 1.0}))
    with pytest.raises(ValueError, match="lacks"):
        PriceTable.load(str(p))
    d = {f: 1.0 for f in ("usd_per_mtok_input", "usd_per_mtok_cached_input", "usd_per_mtok_output", "krw_per_usd")}
    p.write_text(json.dumps({**d, "model": "gpt-6-astra", "date": "26/09/2026", "source": "x"}))
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        PriceTable.load(str(p))
    p.write_text(json.dumps({**d, "model": "gpt-6-astra", "date": "2026-09-26", "source": "x"}))
    assert PriceTable.load(str(p)).usd_per_mtok_output == 1.0


def test_reservations_block_at_80_percent_and_charges_stop(tmp_path):
    L = CostLedger(str(tmp_path / "l.jsonl"), 100.0, TEST)
    L.reserve("e1:1", 50.0)
    assert L.can_send(30.0) and not L.can_send(31.0)
    L.charge("e1:1", None)  # no usage reported -> the reservation is charged
    assert L.spent == pytest.approx(50.0) and not L.stopped
    L.reserve("e1:2", 30.0)
    L.charge("e1:2", {"input_tokens": 0, "output_tokens": 3000})  # 33.6 KRW -> 83.6 >= 80
    assert L.stopped and not L.can_send(0.0)


def test_two_ledgers_on_one_file_see_each_other(tmp_path):
    f = str(tmp_path / "shared.jsonl")
    A, B = CostLedger(f, 100.0, TEST, run_id="standard"), CostLedger(f, 100.0, TEST, run_id="dr")
    A.reserve("a:1", 70.0)
    A.charge("a:1", None)
    assert B.can_send(10.0) and not B.can_send(10.1)
    B.reserve("b:1", 10.0)
    B.charge("b:1", None)
    assert A.can_send(0.0) is False and A.stopped


def test_finalize_charges_unanswered_reservations_by_prefix(tmp_path):
    L = CostLedger(str(tmp_path / "l.jsonl"), 100.0, TEST)
    L.reserve("e1:5", 4.0)
    L.reserve("e2:1", 3.0)
    L.finalize(prefix="e1:")
    assert L.spent == pytest.approx(4.0) and list(L.reserved) == ["e2:1"]
    rows = [json.loads(x) for x in open(tmp_path / "l.jsonl", encoding="utf-8")]
    assert rows[-1]["kind"] == "unanswered" and rows[-1]["key"] == "e1:5"


def test_t21_no_usage_api_error_costs_zero_and_releases_the_reservation(tmp_path):
    """D1 (P108): the API reported an error and no usage -> it did not bill: row kind no_usage, cost 0. A missing usage
    without an API error (client timeout, transport error) stays at the reservation (no_usage_reserved)."""
    f = str(tmp_path / "l.jsonl")
    L = CostLedger(f, 100.0, TEST)
    L.reserve("e1:1", 13.6)
    assert L.charge("e1:1", None, {"error": "insufficient_quota"}, api_error=True) == 0.0
    assert L.reserved == {} and L.spent == 0.0
    L.reserve("e1:2", 13.6)
    assert L.charge("e1:2", None, {"error": "timeout"}) == pytest.approx(13.6)
    kinds = [(json.loads(x)["kind"], json.loads(x)["cost_krw"]) for x in open(f, encoding="utf-8")]
    assert kinds == [("no_usage", 0.0), ("no_usage_reserved", 13.6)]


def test_t21_unanswered_counted_separately_and_still_in_the_80_percent_stop(tmp_path):
    """B7: the conservative reservation charge of never-answered requests stays (the stop counts it), but state()
    reports it apart from the answered spend."""
    f = str(tmp_path / "l.jsonl")
    L = CostLedger(f, 100.0, TEST)
    L.reserve("e1:1", 30.0)
    L.charge("e1:1", {"input_tokens": 0, "output_tokens": 1000})  # 11.2 KRW billed
    L.reserve("e1:2", 70.0)
    L.finalize(prefix="e1:")
    st = CostLedger(f, 100.0, TEST).state()  # another process reading the same file
    assert st["unanswered_n"] == 1 and st["unanswered_krw"] == pytest.approx(70.0)
    assert st["answered_krw"] == pytest.approx(11.2) and st["spent_krw"] == pytest.approx(81.2)
    assert st["stopped"] is True and st["fatal"] is None


def test_t21_fatal_row_is_shared_through_the_file(tmp_path):
    f = str(tmp_path / "l.jsonl")
    A, B = CostLedger(f, 100.0, TEST), CostLedger(f, 100.0, TEST)
    A.mark_fatal("insufficient_quota", "You exceeded your current quota")
    A.mark_fatal("insufficient_quota")  # once only
    B.refresh()
    assert A.fatal == B.fatal == "insufficient_quota" and B.spent == 0.0
    assert [json.loads(x)["kind"] for x in open(f, encoding="utf-8")] == ["fatal"]
    M = CostLedger(None, 0.0, PriceTable.free())  # in-memory ledger (mock / local model)
    M.mark_fatal("insufficient_quota")
    assert M.fatal == "insufficient_quota" and M.state()["fatal"] == "insufficient_quota"


def test_free_prices_never_stop_and_priced_needs_a_budget():
    L = CostLedger(None, 0.0, PriceTable.free())
    L.reserve("k", L.prices.krw_upper(5000, 1200))
    assert L.can_send(1e9) and L.charge("k", {"input_tokens": 5000, "output_tokens": 900}) == 0.0
    with pytest.raises(ValueError, match="budget"):
        CostLedger(None, 0.0, TEST)
