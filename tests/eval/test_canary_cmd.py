"""Daily canary command (canon §28 매일 카나리, E-first §1.8; R7 cycle-1 D2): fixed DEV snapshots x fixed
question_id@vN, result file with an id, latest-id lookup used by the runtime / eval logs."""
import json
import os

import pytest

from harvest.eval import canary as K


@pytest.fixture
def croot(tmp_path, monkeypatch):
    root = tmp_path / "canary"
    monkeypatch.setenv("HARVEST_CANARY_ROOT", str(root))
    monkeypatch.setenv("HARVEST_QID_REGISTRY", str(tmp_path / "qid.json"))
    return root


def test_build_set_copies_fixed_dev_snapshots(dev_dirs, croot):
    m = K.main(["build-set", "--data", dev_dirs["P0"], "--seeds", "0-2", "--n", "4", "--name", "t1"])
    d = croot / "sets" / "t1"
    lines = [json.loads(x) for x in open(d / "lines.jsonl", encoding="utf-8")]
    assert len(lines) == 4 == m["n"] and all(ln["decision"] for ln in lines)
    for ln in lines:  # frames copied into the set (fixed even if the source changes)
        for p in ln["images"].values():
            assert os.path.isfile(d / p) and not os.path.isabs(p)
    assert m["set_sha"] and m["split"] == "dev"
    with pytest.raises(SystemExit):  # a set is immutable
        K.main(["build-set", "--data", dev_dirs["P0"], "--seeds", "0-2", "--n", "4", "--name", "t1"])


def test_build_set_refuses_reserved_seeds(dev_dirs, croot, tmp_path, monkeypatch):
    from .conftest import write_episodes
    monkeypatch.delenv("HARVEST_ALLOW_SPLIT", raising=False)
    cal = str(tmp_path / "cal" / "P0")
    write_episodes(cal, [500], "P0")
    with pytest.raises(SystemExit):
        K.main(["build-set", "--data", cal, "--seeds", "500", "--n", "2", "--name", "bad"])


def test_mock_canary_writes_an_id_and_compares_with_the_baseline_day(dev_dirs, croot):
    K.main(["build-set", "--data", dev_dirs["P0"], "--seeds", "0-2", "--n", "4", "--name", "t1"])
    assert K.latest_canary("mock")["id"] == "none"
    r = K.main(["--model", "mock", "--set", "t1", "--repeats", "2"])
    f = croot / f"canary_{r['date_utc'].replace('-', '')}_mock.json"
    d = json.load(open(f, encoding="utf-8"))
    assert d["id"] == r["id"] and d["id"].startswith("cn") and d["model"]["fingerprint"] == "mock"
    assert len(d["answers"]) == 4 * 5 and all(len(v) == 2 for v in d["answers"].values())
    assert d["floor"] == 0.0 and d["baseline"] is None and set(d["question_ids"]) == set(K.QUESTIONS)
    assert K.latest_canary("mock")["id"] == d["id"]
    with pytest.raises(SystemExit):  # one canary per model and day unless --force
        K.main(["--model", "mock", "--set", "t1"])
    # an older day with different answers becomes the baseline; the drift test runs against it
    old = dict(d, id="cn20260901_mock_aaaaaa", date_utc="2026-09-01",
               answers={k: ["zzz"] * 2 for k in d["answers"]})
    json.dump(old, open(croot / "canary_20260901_mock.json", "w", encoding="utf-8"))
    r2 = K.main(["--model", "mock", "--set", "t1", "--repeats", "2", "--force"])
    assert r2["baseline"]["id"] == "cn20260901_mock_aaaaaa"
    assert r2["compare"]["mismatch"] == 1.0 and r2["drift_suspect"] is True
    assert K.latest_canary("mock")["id"] == r2["id"]  # the newest day wins
    assert K.latest_canary(None)["id"] == "none"


def test_eval_run_meta_records_the_canary(dev_dirs, croot):
    from harvest.eval import common as C
    m = C.run_meta("x", {"kind": "mock", "path": None, "spec": "mock"})
    assert m["canary"]["id"] == "none"
    K.main(["build-set", "--data", dev_dirs["P0"], "--seeds", "0-2", "--n", "2", "--name", "t1"])
    r = K.main(["--model", "mock", "--set", "t1"])
    assert C.run_meta("x", {"kind": "mock", "path": None, "spec": "mock"})["canary"]["id"] == r["id"]
