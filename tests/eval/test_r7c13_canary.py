"""R7 cycle 13 D2 / D3 (+ the Isaac worker env).

D2: the canary baseline is the first day of the same fixed set AND the same question_id@vN set (E §1.8 :136-140
"고정 스냅샷 × 고정 `question_id@vN` 소수 세트 … 기준일과 비교", "기준일 = 카나리 세트를 처음 돌린 날"; §3.7-7
:345-346 a version change (serializer included) turns the gate off and recalibrates; canon §77 "카나리 기준일(질문
id·프롬프트가 바뀜 → 새 기준일)"): a ser-A-min-2 canary never compares against a ser-A-min-1 day; the first canary
of a new version is the new baseline day.
D3: after a drift_suspect canary the J5 gate stays off until a calibration fitted on / after that canary's day exists
(E §1.8 :139 "표류 의심 → … E1 보정 부분을 다시 돌린 뒤에 게이트를 재사용", §3.7-8 :347 "판정 7대로 끄고
재보정한다"); a later clean canary alone does not re-enable it. Canon §79."""
import json

import pytest

from harvest.eval import canary as K
from harvest.eval import closed


@pytest.fixture
def croot(tmp_path, monkeypatch):
    root = tmp_path / "canary"
    root.mkdir()
    monkeypatch.setenv("HARVEST_CANARY_ROOT", str(root))
    monkeypatch.setenv("HARVEST_QID_REGISTRY", str(tmp_path / "qid.json"))
    return root


# ------------------------------------------------------------------------------------------ D2 baseline version
def _today_run(croot, dev_dirs):
    K.main(["build-set", "--data", dev_dirs["P0"], "--seeds", "0-2", "--n", "4", "--name", "t1"])
    r = K.main(["--model", "mock", "--set", "t1", "--repeats", "2"])
    return json.load(open(croot / f"canary_{r['date_utc'].replace('-', '')}_mock.json", encoding="utf-8"))


def _old(croot, d, date, qids, cid):
    x = dict(d, id=cid, date_utc=date, question_ids=qids, answers={k: ["zzz"] * 2 for k in d["answers"]})
    if qids is None:
        x.pop("question_ids")
    json.dump(x, open(croot / f"canary_{date.replace('-', '')}_mock.json", "w", encoding="utf-8"))


def test_a_new_question_id_version_is_a_new_baseline_day(dev_dirs, croot):
    d = _today_run(croot, dev_dirs)
    old_qids = {q: "02e56df7dd80@v1" for q in d["question_ids"]}  # e.g. the ser-A-min-1 ids
    _old(croot, d, "2026-09-01", old_qids, "cn20260901_mock_aaaaaa")
    r = K.main(["--model", "mock", "--set", "t1", "--repeats", "2", "--force"])
    assert r["baseline"] is None and r["compare"] is None and r["drift_suspect"] is None


def test_a_canary_without_question_ids_is_never_a_baseline(dev_dirs, croot):
    d = _today_run(croot, dev_dirs)
    _old(croot, d, "2026-09-01", None, "cn20260901_mock_aaaaaa")
    r = K.main(["--model", "mock", "--set", "t1", "--repeats", "2", "--force"])
    assert r["baseline"] is None


def test_the_baseline_is_the_first_day_of_the_same_version(dev_dirs, croot):
    d = _today_run(croot, dev_dirs)
    _old(croot, d, "2026-09-01", {q: "02e56df7dd80@v1" for q in d["question_ids"]}, "cn20260901_mock_aaaaaa")
    _old(croot, d, "2026-09-02", d["question_ids"], "cn20260902_mock_bbbbbb")
    _old(croot, d, "2026-09-03", d["question_ids"], "cn20260903_mock_cccccc")
    r = K.main(["--model", "mock", "--set", "t1", "--repeats", "2", "--force"])
    assert r["baseline"]["id"] == "cn20260902_mock_bbbbbb"
    assert r["compare"]["mismatch"] == 1.0 and r["drift_suspect"] is True


def test_select_baseline_pure():
    runs = [{"id": "a", "set": {"set_sha": "S"}, "question_ids": {"dir_z": "x@v1"}},
            {"id": "b", "set": {"set_sha": "S"}, "question_ids": {"dir_z": "y@v2"}},
            {"id": "c", "set": {"set_sha": "T"}, "question_ids": {"dir_z": "y@v2"}},
            {"id": "d", "set": {"set_sha": "S"}, "question_ids": {"dir_z": "y@v2"}}]
    assert K.select_baseline(runs, "S", {"dir_z": "y@v2"})["id"] == "b"
    assert K.select_baseline(runs, "S", {"dir_z": "x@v1"})["id"] == "a"
    assert K.select_baseline(runs, "S", {"dir_z": "z@v3"}) is None
    assert K.select_baseline(runs, "T", {"dir_z": "x@v1"}) is None


# ------------------------------------------------------------------------------------------ D3 J5 after drift
def _can(croot, date, drift, fp="mock"):
    json.dump({"id": f"cn{date.replace('-', '')}", "date_utc": date, "drift_suspect": drift},
              open(croot / f"canary_{date.replace('-', '')}_{fp}.json", "w", encoding="utf-8"))


def _cal(tmp_path, utc):
    p = tmp_path / f"cal_{(utc or 'none').replace(':', '')}.json"
    p.write_text(json.dumps({"format": "x", **({"utc": utc} if utc else {})}))
    return str(p)


def test_drift_day_then_clean_day_without_recalibration_keeps_j5_off(croot, tmp_path):
    _can(croot, "2026-09-20", None)
    _can(croot, "2026-09-21", True)
    _can(croot, "2026-09-22", False)
    can = K.latest_canary("mock")
    assert can["id"] == "cn20260922" and can["last_drift"]["id"] == "cn20260921"
    al, note = closed.j5_after_canary(0.1, _cal(tmp_path, "2026-09-20T12:00:00Z"), can)
    assert al is None and "cn20260921" in note


@pytest.mark.parametrize("utc", ["2026-09-21T13:00:00Z", "2026-09-22T08:00:00Z"])
def test_recalibration_after_the_drift_canary_turns_j5_back_on(croot, tmp_path, utc):
    _can(croot, "2026-09-20", None)
    _can(croot, "2026-09-21", True)
    _can(croot, "2026-09-22", False)
    assert closed.j5_after_canary(0.1, _cal(tmp_path, utc), K.latest_canary("mock")) == (0.1, None)


def test_no_drift_ever_keeps_j5(croot, tmp_path):
    _can(croot, "2026-09-20", None)
    _can(croot, "2026-09-21", False)
    can = K.latest_canary("mock")
    assert can["last_drift"] is None
    assert closed.j5_after_canary(0.1, _cal(tmp_path, "2026-09-01T00:00:00Z"), can) == (0.1, None)


def test_a_drift_of_another_model_does_not_count(croot, tmp_path):
    _can(croot, "2026-09-21", True, fp="otherfp")
    _can(croot, "2026-09-22", False)
    assert closed.j5_after_canary(0.1, _cal(tmp_path, "2026-09-20T00:00:00Z"), K.latest_canary("mock")) == (0.1, None)


@pytest.mark.parametrize("utc,on", [("2026-09-24T23:59:59Z", False), ("2026-09-25T00:00:00Z", True),
                                    ("2026-09-25T11:00:00Z", True), (None, False)])
def test_same_day_boundaries_unchanged(croot, tmp_path, utc, on):
    _can(croot, "2026-09-24", False)
    _can(croot, "2026-09-25", True)
    al, _ = closed.j5_after_canary(0.1, _cal(tmp_path, utc), K.latest_canary("mock"))
    assert (al == 0.1) is on


def test_closed_run_spec_keeps_j5_off_after_a_clean_day(croot, tmp_path, monkeypatch):
    class _P:
        def __init__(self, *a, **k):
            pass

        def wait(self):
            return 0
    monkeypatch.setattr(closed.subprocess, "Popen", _P)
    _can(croot, "2026-09-21", True)
    _can(croot, "2026-09-22", False)
    cal = _cal(tmp_path, "2026-09-20T00:00:00Z")
    out = tmp_path / "o"
    with pytest.raises(SystemExit, match="wrote no result"):
        closed.run(closed._args(["--model", "mock", "--out", str(out), "--calibration", cal, "--j5-alpha", "0.1"]))
    spec = json.load(open(out / "spec_standard.json"))
    assert spec["j5_alpha"] is None and "cn20260921" in spec["j5_canary_gate"]


# ------------------------------------------------------------------------------------------ Isaac worker env
def test_worker_env_has_passive_omp_wait():
    cmd = closed.worker_cmd("/data/harvest/tmp/code", "/data/x/spec.json", "1", "inst", 600)
    inner = cmd[cmd.index("./ir_run.sh"):]
    assert "OMP_WAIT_POLICY=PASSIVE" in inner
    assert inner.index("OMP_WAIT_POLICY=PASSIVE") < inner.index("/isaac-sim/python.sh")
