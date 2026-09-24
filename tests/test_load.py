import threading
import time

from harvest.clients.jev import CallRecord
from harvest.load.closed_loop import closed_loop
from harvest.load.open_loop import open_loop
from harvest.load.payloads import fixed, make
from harvest.load.rate import RateLimiter


def fake_call_factory(delay):
    lock = threading.Lock()
    state = {"now": 0, "peak": 0}

    def call(req, meta):
        with lock:
            state["now"] += 1
            state["peak"] = max(state["peak"], state["now"])
        t0 = time.monotonic()
        time.sleep(delay)
        with lock:
            state["now"] -= 1
        return CallRecord(t_send=t0, t_first_byte=t0 + delay, t_done=time.monotonic(), http_status=200, meta=meta)
    return call, state


def test_closed_loop_keeps_n_inflight():
    call, st = fake_call_factory(0.05)
    recs = closed_loop(call, lambda i: {"i": i}, n_inflight=4, n_total=40, meta={"size": "S1"})
    assert len(recs) == 40 and st["peak"] == 4
    assert all(r.meta["N"] == 4 and r.meta["size"] == "S1" for r in recs)


def test_open_loop_skips_when_cap_reached():
    call, st = fake_call_factory(0.5)
    recs, skipped = open_loop(call, lambda i: {"i": i}, T_c=0.05, duration_s=1.0, n_cap=2, meta={})
    assert st["peak"] <= 2 and skipped > 0 and len(recs) >= 2


def test_rate_limiter_caps_rps():
    rl = RateLimiter(rps=50)
    t0 = time.monotonic()
    for _ in range(26):
        rl.wait()
    assert time.monotonic() - t0 >= 0.45


def test_payload_sizes_and_cache_busting():
    a, b = make("S1", 1), make("S1", 2)
    assert a["state"] != b["state"] and set(a["questions"]) == set(b["questions"])
    assert len(make("X8", 0)["state"]) > 4 * len(make("S1", 0)["state"])
    assert len(make("S3", 0)["questions"]) > len(make("S1", 0)["questions"])
    assert fixed(3) == fixed(3) and fixed(3) != fixed(4)


def test_run_session_writes_header_curl_and_all_phases(tmp_path):
    import json
    from harvest.load.session import run_session
    call, _ = fake_call_factory(0.001)
    out = tmp_path / "s.jsonl"
    run_session(call, out, slot="KST02", site="pod", sizes=("S1", "S3"), ns=(1, 2), per_cell=4,
                x8_ns=(1,), open_sizes=("S1",), open_Tcs=(0.05,), open_dur_s=0.2, det_n=3,
                curl_fn=lambda: {"time_total": 0.1}, curl_n=2, prereg={"x": "h"})
    rows = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["kind"] == "header" and rows[0]["prereg"] == {"x": "h"} and rows[0]["site"] == "pod"
    kinds = [r["kind"] for r in rows]
    assert kinds.count("curl") == 2
    calls = [r for r in rows if r["kind"] == "call"]
    closed = [r for r in calls if r["meta"]["phase"] == "closed"]
    assert len(closed) == 2 * 2 * 4 + 4  # sizes × ns × per_cell + X8
    assert any(r["meta"]["phase"] == "open" for r in calls)
    det = [r for r in calls if r["meta"]["phase"] == "determinism"]
    assert len(det) == 3 and all(r["meta"]["slot"] == "KST02" for r in det)
