import numpy as np
import pytest

from harvest.couple.cost import CostLedger, PriceTable
from harvest.couple.driver import CoupleDriver, TickView
from harvest.couple.mock import ScriptedCoupleAstra, answer
from harvest.couple.params import CoupleParams
from harvest.couple.twolayer import committed_vector

TEST = PriceTable("test", "2026-09-26", 2.0, 0.5, 8.0, 1400.0, "unit test")
FR = {c: np.full((12, 16, 3), 40, np.uint8) for c in ("cam_head", "cam_wrist_left", "cam_wrist_right")}
CAMS = {c: {"K": [[20, 0, 8], [0, 20, 6], [0, 0, 1]], "R": [[0, 0, 1], [-1, 0, 0], [0, -1, 0]], "t": [0, 0, 0],
            "W": 16, "H": 12} for c in FR}


class MiniQueue:
    """The runtime DeliveryQueue contract, synchronously: fn runs at submit, delivered at send + latency."""

    def __init__(self):
        self.items = []

    def submit(self, now, fn, lat, meta):
        self.items.append((now + (lat or 0.0), fn(), meta, now))

    def due(self, now):
        out = [x for x in self.items if x[0] <= now + 1e-9]
        self.items = [x for x in self.items if x[0] > now + 1e-9]
        return [{**res, "meta": meta, "t_send": ts, "t_deliver": td} for td, res, meta, ts in out]


def _run(astra, seconds, p=None, ledger=None, frames=FR, cams=CAMS, t1=None, flag_at=None, auth=None):
    """auth: None (TickView default, a = 1) or a callable(now) -> (a, source)."""
    p = p or CoupleParams(request_mode="F0")
    q = MiniQueue()
    ledger = ledger or CostLedger(None, 0.0, PriceTable.free())
    drv = CoupleDriver(p, astra, ledger, q.submit, "Put the red mug on the blue tray.")
    steps = []
    for i in range(int(round(seconds * 100))):
        now = round(i * 0.01, 6)
        for r in q.due(now):
            drv.on_delivery(r, now, t1 or {})
        if flag_at is not None and abs(now - flag_at) < 1e-9:
            drv.flag("m7_critic_alarm", now)
        a, src = auth(now) if auth is not None else (None, None)
        out = drv.tick(TickView(now=now, dt=0.01, tcp_p=np.array([1.0, 0.0, 0.0]), phase="approach", stage="S1",
                                near=False, committed={"dir_xy": "plus_x", "dir_z": "none_z", "mag_coarse": "small"},
                                frames=frames, cams=cams, t1=t1 or {}, authority=a, authority_src=src))
        steps.append(out.step6)
    return drv, np.array(steps), q


def test_serial_cadence_one_in_flight():
    ast = ScriptedCoupleAstra([answer("continue")], latency_s=3.0)
    drv, steps, _ = _run(ast, 10.0)
    assert [r["t"] for r in drv.log if r["type"] == "send"] == [0.0, 3.0, 6.0, 9.0]
    s = drv.summary()
    assert s["max_inflight"] == 1 and s["answers"] == 3 and np.abs(steps).sum() == 0.0
    assert ast.calls[0]["req"]["cameras"] == ["cam_head", "cam_wrist_left", "cam_wrist_right"]
    assert set(ast.calls[0]["req"]["trace_uv"]) <= {"cam_head", "cam_wrist_left", "cam_wrist_right"}


def test_two_agreeing_edits_move_the_full_delta():
    ed = answer("edit", execution="failed", intent="misaligned", dp=(0.0, 0.0, 0.02))
    drv, steps, _ = _run(ScriptedCoupleAstra([ed, ed, answer("continue")], latency_s=3.0), 13.0)
    assert steps[:, 2].sum() == pytest.approx(0.02, abs=2e-4)
    layers = [r["layer"] for r in drv.log if r["type"] == "answer"]
    assert layers[:2] == ["apply", "confirm"]


def test_stale_edit_is_not_applied():
    # controller ruling P2: stale default is now 15 s (canon §86 supplement); latency 16 s > stale_edit_s,
    # run 18 s so the run window (default timeout_s 20 s > 16 s) still lets the answer arrive and be gated stale.
    ed = answer("edit", execution="failed", dp=(0.0, 0.0, 0.02))
    drv, steps, _ = _run(ScriptedCoupleAstra([ed], latency_s=16.0), 18.0)
    assert np.abs(steps).sum() == 0.0 and {r["gate"] for r in drv.log if "gate" in r} == {"stale"}


def test_events_ride_on_the_next_request():
    ast = ScriptedCoupleAstra([answer("continue")], latency_s=3.0)
    _run(ast, 7.0, flag_at=1.0)
    assert [c["req"]["events"] for c in ast.calls] == [[], ["m7_critic_alarm"], []]


def test_budget_stop_holds_further_sends(tmp_path):
    led = CostLedger(str(tmp_path / "l.jsonl"), 60.0, TEST)  # 80 % = 48 KRW; one call ~18 KRW at these test prices
    ast = ScriptedCoupleAstra([answer("continue")], latency_s=1.0, usage={"input_tokens": 3000, "output_tokens": 900})
    drv, _, _ = _run(ast, 10.0, ledger=led)
    s = drv.summary()
    assert s["budget_excluded"] and 1 <= s["calls_sent"] < 10
    assert any(r["type"] == "hold_send" and r["why"] == "budget" for r in drv.log)


def test_late_answer_after_timeout_is_ignored_and_charged_once(tmp_path):
    led = CostLedger(str(tmp_path / "l.jsonl"), 1000.0, TEST)
    ed = answer("edit", execution="failed", dp=(0.0, 0.0, 0.02))
    ast = ScriptedCoupleAstra([ed], latency_s=20.0, usage={"input_tokens": 3000, "output_tokens": 900})
    drv, steps, _ = _run(ast, 21.0, p=CoupleParams(request_mode="F0", timeout_s=15.0), ledger=led)
    late = [r for r in drv.log if r.get("late")]
    assert len(late) == 1 and late[0]["no"] == 1 and np.abs(steps).sum() == 0.0
    rows = [r for r in open(tmp_path / "l.jsonl", encoding="utf-8")]
    assert len(rows) == 1  # request 1 charged once (at its late arrival); request 2 still reserved
    drv.close()
    assert len([r for r in open(tmp_path / "l.jsonl", encoding="utf-8")]) == 2


def test_no_frames_no_cams_sends_text_only():
    ast = ScriptedCoupleAstra([answer("continue", views=())], latency_s=3.0)
    drv, _, _ = _run(ast, 4.0, frames={}, cams=None)
    req = ast.calls[0]["req"]
    assert req["cameras"] == [] and req["trace_uv"] == {}
    assert drv.summary()["answers"] == 1 and drv.log[0]["overlay"] == []


def test_irrev_gate_and_mismatch_event():
    bad = answer("continue", intent="misaligned")
    drv, _, _ = _run(ScriptedCoupleAstra([bad], latency_s=1.0), 2.0)
    t1 = {"gripper_open": True}
    assert drv.irrev_allowed("close", 2.0, t1, True) is False
    drv.irrev_allowed("close", 3.05, t1, True)
    assert any(e["event"] == "layer_mismatch" for e in drv.events)


# ---------------------------------------------------------------------------------------------------------
# Task 9 controller ruling C2: chunk-level adherence (canon §84 supplement 4). committed_vector({"dir_xy":
# "none_xy", "dir_z": "up", "mag_coarse": "small"}) == (0, 0, 1): used below as a decision that agrees with a
# positive-z offset, so a chunk_vec pointed the other way isolates the chunk (not the decision) as the driver
# of the fast check and the adherence log.
UP = {"dir_xy": "none_xy", "dir_z": "up", "mag_coarse": "small"}


def _driver_with_active_offset(contra_steps=3):
    p = CoupleParams(request_mode="F0", contra_steps=contra_steps)
    drv = CoupleDriver(p, ScriptedCoupleAstra([answer("continue")], latency_s=3.0),
                       CostLedger(None, 0.0, PriceTable.free()), lambda *a, **k: None, "task")
    drv.offset.command(1, np.array([0.0, 0.0, 0.02, 0.0, 0.0, 0.0]), 1.0, 0.0, 5.0)
    assert drv.offset.active
    assert drv.offset.direction() == pytest.approx([0.0, 0.0, 1.0])
    assert committed_vector(UP) == pytest.approx([0.0, 0.0, 1.0])
    return drv


def test_fused_chunk_vec_drives_the_fast_check_not_the_decision():
    drv = _driver_with_active_offset(contra_steps=3)
    chunk_oppose = np.array([0.0, 0.0, -0.01])  # opposes the offset even though the decision (UP) agrees with it
    for i in range(3):
        drv.on_step(UP, "FOLLOW", float(i), chunk_vec=chunk_oppose)
    assert any(e["event"] == "offset_contradicted" for e in drv.events)
    rows = [r for r in drv.log if r["type"] == "adherence"]
    assert len(rows) == 3 and all(r["src"] == "chunk" for r in rows)
    assert all(r["cos_vs_offset"] == pytest.approx(-1.0) for r in rows)
    # the decision (UP) itself agreed with the offset the whole time -- it is the executed chunk that
    # contradicted it, proving the fast check reads chunk_vec, not committed_vector(committed)
    assert all(r["cos_chunk_vs_decision"] == pytest.approx(-1.0) for r in rows)


def test_summary_adherence_rates_from_logged_rows():
    drv = _driver_with_active_offset(contra_steps=100)  # high threshold: no offset_contradicted mid-sequence
    agree, oppose = np.array([0.0, 0.0, 0.01]), np.array([0.0, 0.0, -0.01])
    for i, v in enumerate((agree, agree, oppose, agree)):
        drv.on_step(UP, "FOLLOW", float(i), chunk_vec=v)
    s = drv.summary()["adherence"]
    assert s["chunk_vs_offset"] == {"n": 4, "follow_rate": 0.75}
    assert s["chunk_vs_decision"] == {"n": 4, "follow_rate": 0.75}


def test_modular_call_without_chunk_vec_logs_decision_src():
    drv = _driver_with_active_offset(contra_steps=3)
    drv.on_step(UP, "FOLLOW", 0.0)  # modular backend: no chunk_vec
    row = [r for r in drv.log if r["type"] == "adherence"][-1]
    assert row["src"] == "decision"
    assert row["cos_chunk_vs_decision"] is None and row["follows_decision"] is None
    assert row["cos_vs_offset"] == pytest.approx(1.0) and row["follows_offset"] is True


# ---- Task 17 (canon §84 supplement 8): authority a on the offset
ED2 = answer("edit", execution="failed", intent="misaligned", dp=(0.0, 0.0, 0.02))


def test_authority_zero_makes_the_edit_have_no_effect_and_is_logged_sparsely():
    drv, steps, _ = _run(ScriptedCoupleAstra([ED2, ED2, answer("continue")], latency_s=3.0), 13.0,
                         auth=lambda now: (0.0, "rule"))
    assert not np.any(steps) and [r["layer"] for r in drv.log if r["type"] == "answer"][:2] == ["apply", "confirm"]
    rows = [r for r in drv.log if r["type"] == "authority"]
    assert len(rows) == 1 and rows[0]["a"] == 0.0 and rows[0]["src"] == "rule"
    s = drv.summary()["authority"]
    assert s["share"] == {"a0": 1.0, "band": 0.0, "a1": 0.0} and s["seconds"] == pytest.approx(13.0)


def test_authority_none_is_one_and_band_is_counted():
    drv, steps, _ = _run(ScriptedCoupleAstra([ED2, ED2, answer("continue")], latency_s=3.0), 13.0)
    assert steps[:, 2].sum() == pytest.approx(0.02, abs=2e-4)  # as before (TickView default: a = 1)
    assert drv.summary()["authority"]["share"]["a1"] == 1.0
    drv2, _, _ = _run(ScriptedCoupleAstra([answer("continue")], latency_s=3.0), 4.0,
                      auth=lambda now: (1.0 if now < 1.0 else 0.5 if now < 3.0 else 0.0, "aux"))
    s = drv2.summary()["authority"]
    assert s["share"] == {"a0": 0.25, "band": 0.5, "a1": 0.25}
    assert [(r["t"], r["a"]) for r in drv2.log if r["type"] == "authority"] == [(0.0, 1.0), (1.0, 0.5), (3.0, 0.0)]
