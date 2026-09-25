"""R6 closed: aggregation of closed-loop trials (success / latency / commit stats, paired closed-loop RD)."""
import pytest

from harvest.eval import closed


def _t(variant, cond, seed, ok, t=15.0, p95=0.3, commit=0.8):
    return {"variant": variant, "condition": cond, "seed": seed, "epoch": 0, "success": ok,
            "sim_time": t, "termination": "success" if ok else "time_limit",
            "summary": {"latency_s": {"p50": 0.2, "p95": p95}, "commit_ratio_mean": commit, "calls_delivered": 50,
                        "call_errors": 0, "decisions_per_sim_s": 3.0, "blocked_s": 1.0, "rtf_env": 0.5,
                        "m4": {"epoch": 2}, "astra_calls": 3, "stop_ticks": 0}}


def test_aggregate_per_condition_and_variant():
    tr = [_t("standard", "C5", s, s != 2) for s in range(4)] + [_t("standard", "C2", s, s == 0) for s in range(4)]
    agg = closed.aggregate(tr, n_boot=200)
    c5 = agg["cells"]["C5/standard"]
    assert c5["n"] == 4 and c5["success"]["mean"] == 0.75
    assert c5["time_to_success_s"]["median"] == 15.0
    assert c5["latency_p95_s"]["median"] == 0.3 and c5["commit_ratio"]["mean"] == 0.8
    d = agg["condition_diff"]["C5-C2/standard"]
    assert d["mean"] == 0.5 and d["n_pairs"] == 4


def test_closed_loop_rd_is_paired_by_seed():
    tr = [_t("standard", "C5", s, True) for s in range(4)] + [_t("random", "C5", s, s < 2) for s in range(4)]
    agg = closed.aggregate(tr, n_boot=200)
    rd = agg["rd"]["C5/random"]
    assert rd["sr_std"] == 1.0 and rd["sr_var"] == 0.5
    assert rd["rd"] == pytest.approx(0.5)  # 1 - SR_rnd / SR_std
    assert rd["sr_diff"]["mean"] == 0.5 and rd["n_pairs"] == 4
    lo, hi = rd["rd_ci"]
    assert lo <= 0.5 <= hi


def test_rd_undefined_when_standard_never_succeeds():
    tr = [_t("standard", "C5", s, False) for s in range(3)] + [_t("random", "C5", s, False) for s in range(3)]
    assert closed.aggregate(tr, n_boot=100)["rd"]["C5/random"]["rd"] is None


def test_run_labels_add_the_heartbeat_period_only_when_swept():
    assert closed.run_labels(["C5", "C2"], [5.0]) == [("C5", 5.0, "C5"), ("C2", 5.0, "C2")]
    assert closed.run_labels(["C5"], [0.0, 10.0]) == [("C5", 0.0, "C5|hb0"), ("C5", 10.0, "C5|hb10")]


def test_run_labels_sweep_the_cadence_k0_to_k4():
    """E-M8c (canon §45): the cadence joins the label only when swept; N is swept for K2 only."""
    got = closed.run_labels(["C5"], [5.0, 10.0], ("K1", "K2", "K3"))
    assert got == [("C5", 5.0, "C5|K1", "K1"), ("C5", 5.0, "C5|K2|hb5", "K2"), ("C5", 10.0, "C5|K2|hb10", "K2"),
                   ("C5", 5.0, "C5|K3", "K3")]
    assert closed.run_labels(["C5"], [5.0], ("K4",)) == [("C5", 5.0, "C5", "K4")]


def test_cadence_flags_are_checked(tmp_path):
    import pytest
    with pytest.raises(SystemExit, match="K4 needs --hb-budget"):
        closed.run(closed._args(["--model", "mock", "--out", str(tmp_path / "o"), "--hb-mode", "K4"]))
    with pytest.raises(SystemExit, match="--hb-mode"):
        closed.run(closed._args(["--model", "mock", "--out", str(tmp_path / "o"), "--hb-mode", "K9"]))


def test_worker_spec_carries_the_latest_canary_id(tmp_path, monkeypatch):
    """R7 cycle-1 D2: the outer command reads the model's latest canary id (or "none") and hands it to the workers
    (RuntimeConfig.canary_id -> every call row of the sidecar)."""
    import json

    class _P:
        def __init__(self, *a, **k):
            pass

        def wait(self):
            return 0
    monkeypatch.setattr(closed.subprocess, "Popen", _P)
    root = tmp_path / "canary"
    monkeypatch.setenv("HARVEST_CANARY_ROOT", str(root))
    for expect in ("none", "cn20260924_mock_abc123"):
        if expect != "none":
            root.mkdir()
            json.dump({"id": expect, "date_utc": "2026-09-24"}, open(root / "canary_20260924_mock.json", "w"))
        out = tmp_path / f"o_{expect}"
        with pytest.raises(SystemExit, match="wrote no result"):
            closed.run(closed._args(["--model", "mock", "--out", str(out)]))
        spec = json.load(open(out / "spec_standard.json"))
        assert spec["canary_id"] == expect


def test_worker_flag_alone_routes_to_the_worker(monkeypatch):
    got = []
    monkeypatch.setattr(closed, "run_worker", lambda p: got.append(p))
    closed.main(["--worker", "/x/spec.json"])
    assert got == ["/x/spec.json"]


def test_worker_command_pins_the_isaac_gpu_and_code_path():
    cmd = closed.worker_cmd("/data/harvest/code_r6", "/data/harvest/out/r6/x/spec_standard.json", gpu="1",
                            inst="r6_standard", timeout_s=3600)
    s = " ".join(cmd)
    assert "CUDA_VISIBLE_DEVICES=1" in s and "IR_ROOT=cyclo" in s and "IR_INST=r6_standard" in s
    assert "PYTHONPATH=/data/harvest/code_r6:" in s and "-m harvest.eval.closed --worker" in s
    with pytest.raises(ValueError):
        closed.worker_cmd("/c", "/s.json", gpu="2", inst="x", timeout_s=10)  # GPU 2 never renders
