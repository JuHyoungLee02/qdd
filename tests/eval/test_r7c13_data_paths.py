"""R7 cycle 13 N5: e05 / rd / calib given a --data path that does not exist (or holds no episodes) fail (rc != 0)
instead of running on 0 episodes (E05_DONE insufficient_data / RD_DONE n 0 / CALIB_DONE with rc 0 before). Plus
the E0.5 output names the question_id@vN of each per-question FLIP_TH (J4; D1). Canon §79."""
import json
import os

import pytest

from harvest.eval import calib, common, e05, rd


def test_load_episodes_refuses_a_missing_folder(tmp_path):
    with pytest.raises(SystemExit, match="not found"):
        common.load_episodes([str(tmp_path / "nope")], "dev")


def test_load_episodes_refuses_a_folder_without_episodes(tmp_path):
    (tmp_path / "empty").mkdir()
    with pytest.raises(SystemExit, match="no episode"):
        common.load_episodes([str(tmp_path / "empty")], "dev")


def test_load_episodes_refuses_no_folder():
    with pytest.raises(SystemExit, match="no episode folder"):
        common.load_episodes([], "dev")


def test_e05_missing_data_fails(dev_dirs, tmp_path):
    with pytest.raises(SystemExit):
        e05.main(["--model", "mock", "--out", str(tmp_path / "o"), "--data", "no/such/P0", "--split", "dev"])


def test_rd_missing_variant_folder_fails(dev_dirs, tmp_path):
    with pytest.raises(SystemExit):
        rd.main(["--model", "mock", "--out", str(tmp_path / "o"), "--variants",
                 f"standard={dev_dirs['root']},random=no/such/dir", "--split", "dev", "--episodes", "1"])


def test_calib_missing_heldout_fails(dev_dirs, tmp_path, monkeypatch):
    monkeypatch.setenv("HARVEST_QID_REGISTRY", str(tmp_path / "qid.json"))
    with pytest.raises(SystemExit):
        calib.main(["--model", "mock", "--out", str(tmp_path / "o"), "--fit-data", dev_dirs["P0"],
                    "--fit-split", "dev", "--heldout", "no/such/P1", "--heldout-split", "dev"])


def test_e05_output_names_the_question_ids(dev_dirs, tmp_path, monkeypatch):
    monkeypatch.setenv("HARVEST_QID_REGISTRY", "x")  # records the original state, restored after the test
    monkeypatch.delenv("HARVEST_QID_REGISTRY")
    monkeypatch.chdir(tmp_path)  # the registry goes to the run folder (as calib / canary), never the cwd default
    out = str(tmp_path / "o")
    e05.main(["--model", "mock", "--out", out, "--data", f"{dev_dirs['P0']},{dev_dirs['P1']}", "--split", "dev",
              "--n-boot", "50"])
    r = json.load(open(os.path.join(out, "e05.json"), encoding="utf-8"))["result"]
    qids = r["c_flip"]["question_ids"]
    assert set(qids) == set(common.QUESTIONS) and all("@v" in v for v in qids.values())
    assert os.path.exists(os.path.join(out, "qid_registry.json")) and not (tmp_path / "docs").exists()
