"""Plan 2026-09-26 final whole-branch review (controller ruling FF): I4 contained worker / stream errors, M1
veto_on_changed log, M3 realized offset in the summary, M5 per-request state pruning. MockTransport / scripted mocks
only; no network, no paid call."""
import json

import httpx
import numpy as np
import pytest

from harvest.clients.astra import AstraClient
from harvest.couple.cost import CostLedger, PriceTable
from harvest.couple.driver import CoupleDriver, TickView
from harvest.couple.mock import ScriptedCoupleAstra, answer
from harvest.couple.params import CoupleParams

TEST = PriceTable("test", "2026-09-26", 2.0, 0.5, 8.0, 1400.0, "unit test")
FR = {c: np.full((12, 16, 3), 40, np.uint8) for c in ("cam_head", "cam_wrist_left", "cam_wrist_right")}
INP = [{"role": "user", "content": "hi"}]


# ------------------------------------------------------------------------------------------------ client (I4)
def _client(body: bytes):
    t = httpx.MockTransport(lambda r: httpx.Response(200, content=body, headers={"content-type": "text/event-stream"}))
    return AstraClient("k", "m-1", transport=t)


def test_non_json_data_line_is_a_bad_response_not_an_exception():
    body = (b'data: {"type":"response.output_text.delta","delta":"x"}\n\ndata: {not json\n\n'
            b'data: {"type":"response.completed","response":{"model":"m-1","usage":{"input_tokens":3,'
            b'"output_tokens":2}}}\n\n')
    rec = _client(body).call(INP, "low", 10, {})
    assert rec.error == "bad_response" and rec.usage["output_tokens"] == 2  # the usage still recorded (billing)


def test_done_marker_is_not_an_error():
    body = (b'data: {"type":"response.completed","response":{"model":"m-1","usage":{"input_tokens":3}}}\n\n'
            b'data: [DONE]\n\n')
    assert _client(body).call(INP, "low", 10, {}).error is None


def test_stream_error_is_recorded_with_its_type():
    class _Bad(httpx.BaseTransport):
        def handle_request(self, request):
            class _S(httpx.SyncByteStream):
                def __iter__(self):
                    raise httpx.StreamConsumed()
            return httpx.Response(200, stream=_S())
    rec = AstraClient("k", "m", transport=_Bad()).call(INP, "low", 10, {})
    assert rec.error == "StreamConsumed"


# ------------------------------------------------------------------------------------------------ driver
class MiniQueue:
    def __init__(self):
        self.items = []

    def submit(self, now, fn, lat, meta):
        self.items.append((now + (lat or 0.0), fn(), meta, now))

    def due(self, now):
        out = [x for x in self.items if x[0] <= now + 1e-9]
        self.items = [x for x in self.items if x[0] > now + 1e-9]
        return [{**res, "meta": meta, "t_send": ts, "t_deliver": td} for td, res, meta, ts in out]


def _t1(t1, now):
    return t1(now) if callable(t1) else (t1 or {})


def _run(astra, seconds, p=None, ledger=None, tip=None, t1=None, gate_at=None):
    p = p or CoupleParams(request_mode="F0")
    q = MiniQueue()
    drv = CoupleDriver(p, astra, ledger or CostLedger(None, 0.0, PriceTable.free()), q.submit, "task")
    for i in range(int(round(seconds * 100))):
        now = round(i * 0.01, 6)
        for r in q.due(now):
            drv.on_delivery(r, now, _t1(t1, now))
        if gate_at is not None and now >= gate_at:
            drv.irrev_allowed("close", now, {"gripper_open": True}, True)
        tp = np.array([1.0, 0.0, 0.0]) if tip is None else tip(now, drv)
        drv.tick(TickView(now=now, dt=0.01, tcp_p=tp, phase="approach", stage="S1", near=False,
                          committed={"dir_xy": "plus_x", "dir_z": "none_z", "mag_coarse": "small"}, frames=FR,
                          t1=_t1(t1, now)))
    return drv


class _Raises:
    model = "mock:raises"
    synthetic_latency = 2.0

    def __init__(self):
        self.calls = 0

    def call(self, inp, effort, max_output_tokens, meta):
        self.calls += 1
        raise RuntimeError("boom in the call")


def test_worker_exception_becomes_a_record_and_the_run_goes_on(tmp_path):
    f = str(tmp_path / "l.jsonl")
    led = CostLedger(f, 1000.0, TEST)
    ast = _Raises()
    drv = _run(ast, 5.0, ledger=led)
    ans = [r for r in drv.log if r["type"] == "answer"]
    assert ast.calls == 3 and len(ans) == 2  # the stream keeps sending after each failure
    assert all(r["error"] == "worker_error:RuntimeError" and "boom" in r["error_message"] for r in ans)
    assert drv.stream.fail_streak == 2 and drv.summary()["api_errors"] == 2
    rows = [json.loads(x) for x in open(f, encoding="utf-8")]
    sends = [r["est_krw"] for r in drv.log if r["type"] == "send"]
    assert [r["kind"] for r in rows] == ["no_usage_reserved"] * 2  # billing unknown -> the reservation
    assert rows[0]["cost_krw"] == pytest.approx(sends[0], abs=1e-4)


def test_jpeg_failure_in_the_worker_is_contained(monkeypatch):
    def bad_jpeg(img, q=90):
        raise OSError("encoder")
    monkeypatch.setattr("harvest.couple.driver.jpeg_bytes", bad_jpeg)
    ast = ScriptedCoupleAstra([answer("continue")], latency_s=2.0)
    drv = _run(ast, 3.0)
    ans = [r for r in drv.log if r["type"] == "answer"]
    assert ans and ans[0]["error"] == "worker_error:OSError" and ast.calls == []
    assert None not in drv.blobs


# ------------------------------------------------------------------------------------------------ M1
def test_veto_on_a_changed_answer_is_logged_and_counted():
    """A fresh misaligned answer whose reconcile verdict is changed (the T1 gripper state changed since its t_state)
    still vetoes the close (no behaviour change); the veto is logged as veto_on_changed once per answer and kind."""
    ast = ScriptedCoupleAstra([answer("continue", intent="misaligned")], latency_s=1.0)
    p = CoupleParams(request_mode="F0")
    drv = _run(ast, 1.5, p=p, t1=lambda now: {"gripper_open": now < 0.5}, gate_at=1.0)
    rec = [r for r in drv.log if r["type"] == "reconcile"]
    assert rec and rec[0]["verdict"] == "changed"
    v = [r for r in drv.log if r["type"] == "veto_on_changed"]
    assert len(v) == 1 and v[0]["why"] == "astra_misaligned" and v[0]["no"] == 1
    assert drv.summary()["veto_on_changed"] == 1


# ------------------------------------------------------------------------------------------------ M3
def test_summary_reports_the_realized_offset_next_to_applied():
    ed = answer("edit", execution="failed", dp=(0.0, 0.02, 0.0))
    p = CoupleParams(request_mode="F0", reconcile_apply=False, contra_steps=10 ** 6)

    def tip(now, drv):  # the tip follows the applied offset exactly
        return np.array([1.0, 0.0, 0.0]) + drv.offset.applied[:3]
    drv = _run(ScriptedCoupleAstra([ed, ed, answer("continue")], latency_s=2.0), 12.0, p=p, tip=tip)
    off = drv.summary()["offset"]
    assert off["applied_m"][1] == pytest.approx(0.02, abs=2e-3)
    r = off["realized"]
    assert r["n"] >= 3 and r["applied_m"] > 0.015
    assert r["along_m"] == pytest.approx(r["applied_m"], abs=1e-4)


# ------------------------------------------------------------------------------------------------ M5
def test_per_request_state_is_pruned():
    drv = _run(ScriptedCoupleAstra([answer("continue")], latency_s=2.0), 10.0)
    assert set(drv._sent_state) <= {drv.stream.n_sent}  # only the request still in flight
    assert set(drv._tip_at) <= {drv.last.request_no, drv.stream.n_sent}
    drv = _run(_Raises(), 10.0)
    assert set(drv._sent_state) <= {drv.stream.n_sent} and set(drv._tip_at) <= {drv.stream.n_sent}
    p = CoupleParams(request_mode="F0", timeout_s=1.0)
    drv = _run(ScriptedCoupleAstra([answer("continue")], latency_s=5.0), 12.0, p=p)  # timeouts + late answers
    assert drv.stream.counts["timeouts"] >= 2
    assert set(drv._sent_state) <= {drv.stream.n_sent} and set(drv._tip_at) <= {drv.stream.n_sent}
