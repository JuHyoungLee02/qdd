"""R7 cycle 12 N6: a daily canary "drift suspect" turns the J5 gate off until E1 calibration is re-run (E §3.7 judgment
8 :347 "매일 카나리가 '표류 의심'을 내면 판정 7대로 끄고 재보정한다", §1.8 :139 "E1 보정 부분을 다시 돌린 뒤에 게이트를
재사용"). Canon §77."""
import json

import pytest

from harvest.eval import closed


def _cal(tmp_path, utc):
    p = tmp_path / f"cal_{utc[:10]}.json"
    p.write_text(json.dumps({"format": "x", "utc": utc}))
    return str(p)


def test_drift_suspect_turns_j5_off_when_the_calibration_predates_the_canary(tmp_path):
    can = {"id": "cn1", "date_utc": "2026-09-25", "drift_suspect": True}
    al, note = closed.j5_after_canary(0.1, _cal(tmp_path, "2026-09-24T10:00:00Z"), can)
    assert al is None and "cn1" in note and "drift" in note


def test_recalibrated_after_the_canary_keeps_the_gate(tmp_path):
    can = {"id": "cn1", "date_utc": "2026-09-25", "drift_suspect": True}
    assert closed.j5_after_canary(0.1, _cal(tmp_path, "2026-09-25T11:00:00Z"), can) == (0.1, None)


@pytest.mark.parametrize("can", [{"id": "cn1", "date_utc": "2026-09-25", "drift_suspect": False},
                                 {"id": "cn1", "date_utc": "2026-09-25", "drift_suspect": None},
                                 {"id": "none", "reason": "no canary"}])
def test_no_drift_keeps_the_gate(tmp_path, can):
    assert closed.j5_after_canary(0.1, _cal(tmp_path, "2026-09-20T00:00:00Z"), can) == (0.1, None)


def test_gate_already_off_or_no_calibration_is_unchanged(tmp_path):
    can = {"id": "cn1", "date_utc": "2026-09-25", "drift_suspect": True}
    assert closed.j5_after_canary(None, _cal(tmp_path, "2026-09-20T00:00:00Z"), can) == (None, None)
    assert closed.j5_after_canary(0.1, "", can) == (0.1, None)


def test_worker_spec_carries_the_effective_alpha(tmp_path, monkeypatch):
    class _P:
        def __init__(self, *a, **k):
            pass

        def wait(self):
            return 0
    monkeypatch.setattr(closed.subprocess, "Popen", _P)
    root = tmp_path / "canary"
    root.mkdir()
    monkeypatch.setenv("HARVEST_CANARY_ROOT", str(root))
    json.dump({"id": "cnX", "date_utc": "2026-09-25", "drift_suspect": True},
              open(root / "canary_20260925_mock.json", "w"))
    cal = _cal(tmp_path, "2026-09-24T00:00:00Z")
    out = tmp_path / "o"
    with pytest.raises(SystemExit, match="wrote no result"):
        closed.run(closed._args(["--model", "mock", "--out", str(out), "--calibration", cal, "--j5-alpha", "0.1"]))
    spec = json.load(open(out / "spec_standard.json"))
    assert spec["j5_alpha"] is None and "cnX" in spec["j5_canary_gate"]
