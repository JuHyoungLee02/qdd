"""R6 commands end to end with --model mock on synthetic DEV folders (no GPU): outputs, guards, metadata."""
import json
import os

import pytest

from harvest.eval import e05


def test_e05_mock_end_to_end(dev_dirs, tmp_path):
    out = str(tmp_path / "out")
    e05.main(["--model", "mock", "--out", out, "--data", f"{dev_dirs['P0']},{dev_dirs['P1']}", "--split", "dev",
              "--blocks", "2", "--n-boot", "200"])
    r = json.load(open(os.path.join(out, "e05.json")))
    assert r["meta"]["command"] == "e05" and r["meta"]["seeds"] == {"P0": [0, 1, 2], "P1": [0, 1]}
    assert r["meta"]["prompt_config"]["sha"] and "code_sha" in r["meta"]
    res = r["result"]
    assert res["n_snapshots"] == 5 * 8 and res["n_episodes"] == 5
    assert res["flip"]["pooled"]["success"]["mean"] == 0.0  # the code rule is constant on these lines
    assert res["rules"]["pooled"]["newest"]["mean"] == 1.0
    assert res["judgments"]["claim"] == "narrow_to_b"
    assert os.path.exists(os.path.join(out, "e05.md")) and os.path.exists(os.path.join(out, "calls.jsonl"))
    n_calls = sum(1 for _ in open(os.path.join(out, "calls.jsonl")))
    assert n_calls == 40 * (3 + 4 + 2 * 2)  # K=3 same-time + A1-A4 + 2 blocks x 2 repeats
    # resumable: a second run makes no new calls
    e05.main(["--model", "mock", "--out", out, "--data", f"{dev_dirs['P0']},{dev_dirs['P1']}", "--split", "dev",
              "--blocks", "2", "--n-boot", "200"])
    assert sum(1 for _ in open(os.path.join(out, "calls.jsonl"))) == n_calls


def test_calib_mock_writes_runtime_file(dev_dirs, tmp_path, monkeypatch):
    from harvest.eval import calib
    from harvest.runtime.calibration import Calibration
    out = str(tmp_path / "cal")
    monkeypatch.setenv("HARVEST_QID_REGISTRY", str(tmp_path / "reg.json"))
    calib.main(["--model", "mock", "--out", out, "--fit-data", dev_dirs["P0"], "--fit-split", "dev",
                "--heldout", dev_dirs["P1"], "--heldout-split", "dev", "--n-boot", "100"])
    r = json.load(open(os.path.join(out, "calib.json")))
    assert set(r["result"]["questions"]) == {"dir_xy", "dir_z", "mag_coarse", "target", "phase"}
    assert r["meta"]["n_T_episodes"] + r["meta"]["n_J5_episodes"] == 3
    c = Calibration.load(os.path.join(out, "calibration.json"), fingerprint="mock",
                         question_ids=r["meta"]["question_ids"])
    assert "dir_z" in c.q and c.q["dir_z"]["n_fit_j5"] > 0


def test_calib_refuses_test_heldout_without_env(dev_dirs, tmp_path, monkeypatch):
    from harvest.eval import calib
    monkeypatch.delenv("HARVEST_ALLOW_SPLIT", raising=False)
    with pytest.raises(SystemExit, match="HARVEST_ALLOW_SPLIT"):
        calib.main(["--model", "mock", "--out", str(tmp_path / "c"), "--fit-data", dev_dirs["P0"], "--fit-split",
                    "cal", "--heldout", dev_dirs["P1"], "--heldout-split", "dev"])


def test_rd_mock_pairs_variants_and_compares(dev_dirs, tmp_path):
    from harvest.eval import rd
    from .conftest import write_episodes
    rnd = tmp_path / "gen" / "random"
    write_episodes(str(rnd / "P0"), [0, 1, 2], "P0")
    out = str(tmp_path / "rd")
    rd.main(["--model", "mock", "--out", out, "--variants", f"standard={dev_dirs['root']},random={rnd}",
             "--split", "dev", "--n-boot", "100"])
    r = json.load(open(os.path.join(out, "rd.json")))["result"]["offline"]
    assert r["RD"]["random"]["pooled"]["n_paired"] == 3 * 8 * 5  # only P0 exists in both
    assert r["RD"]["random"]["pooled"]["drop"]["mean"] == 0.0
    out2 = str(tmp_path / "rd2")
    rd.main(["--model", "mock", "--out", out2, "--variants", f"standard={dev_dirs['root']},random={rnd}",
             "--split", "dev", "--n-boot", "100", "--compare", out])
    r2 = json.load(open(os.path.join(out2, "rd.json")))["result"]
    assert r2["dRD"]["random"]["mean"] == 0.0


def test_e05_refuses_protected_split_without_env(dev_dirs, tmp_path, monkeypatch):
    monkeypatch.delenv("HARVEST_ALLOW_SPLIT", raising=False)
    with pytest.raises(SystemExit, match="HARVEST_ALLOW_SPLIT"):
        e05.main(["--model", "mock", "--out", str(tmp_path / "o"), "--data", dev_dirs["P0"], "--split", "test"])


def test_e05_refuses_dev_data_declared_as_pool(dev_dirs, tmp_path):
    with pytest.raises(SystemExit, match="not in split pool"):
        e05.main(["--model", "mock", "--out", str(tmp_path / "o"), "--data", dev_dirs["P0"], "--split", "pool"])
