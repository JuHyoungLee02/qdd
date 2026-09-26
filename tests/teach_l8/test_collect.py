"""Collection on the kinematic fake world: the runtime Episode drives the robot (so prompts and history lines are
byte-for-byte the runtime ones), the collector labels every call with the truth command, clean episodes succeed,
perturbed ones visit recovery states whose labels still validate, and seeds are split (DEV never trained)."""
import json
import os

import numpy as np
import pytest

from harvest.astra_solo import schema as SC
from harvest.teach_l8 import collect as C

from astra_motion.fakeworld import FakeWorld


def _rows(d):
    return [json.loads(x) for x in open(os.path.join(d, "labels.jsonl"))]


def test_clean_episode_succeeds_and_labels_every_call(tmp_path):
    d = str(tmp_path / "ep")
    meta = C.collect_episode(FakeWorld(), seed=10001, task="mug_tray", variant="standard", out_dir=d, p=0.0)
    assert meta["success"] and meta["n_rows"] == meta["n_calls"]
    rows = _rows(d)
    assert [r["exec_kind"] for r in rows] == ["clean"] * len(rows)
    assert rows[0]["status"] == "not_started" and rows[0]["step"] == "above_target"
    for r in rows:
        assert SC.validate(r["answer"])[1] == []
        cdir = os.path.join(d, "calls", f"c{r['call']:03d}")
        assert os.path.exists(os.path.join(cdir, "prompt.txt"))
        assert os.path.exists(os.path.join(cdir, "img1_head_camera.png"))
        assert set(r["gt"]) >= {"tgt", "place", "tcp", "others"}
    p2 = open(os.path.join(d, "calls", "c001", "prompt.txt"), encoding="utf-8").read()
    assert "1: eef to (" in p2 and "Call 2 of at most 40" in p2
    assert "Next: " not in p2 and "ground truth" not in p2  # no label text leaks into the request


def test_perturbed_episode_visits_recovery_states(tmp_path):
    kinds, steps = set(), set()
    for s in range(10002, 10008):
        d = str(tmp_path / f"e{s}")
        C.collect_episode(FakeWorld(), seed=s, task="mug_tray", variant="standard", out_dir=d, p=0.6,
                          max_perturb=4, stop_calls=25)
        for r in _rows(d):
            kinds.add(r["exec_kind"])
            steps.add(r["step"])
            assert SC.validate(r["answer"])[1] == []
            assert r["prev_kind"] in C.PREV_KINDS
    assert len(kinds - {"clean"}) >= 4 and steps & {"reopen", "lift_clear"}


def test_perturbation_cap(tmp_path):
    d = str(tmp_path / "ep")
    C.collect_episode(FakeWorld(), seed=10009, task="mug_tray", variant="standard", out_dir=d, p=1.0, max_perturb=2,
                      stop_calls=12)
    assert sum(r["exec_kind"] != "clean" for r in _rows(d)) == 2


def test_seed_split_and_task_mix():
    assert C.check_seed(0, "dev") == 0 and C.check_seed(19, "dev") == 19
    with pytest.raises(ValueError):
        C.check_seed(20, "dev")
    with pytest.raises(ValueError):
        C.check_seed(5, "train")
    with pytest.raises(ValueError):
        C.check_seed(1000, "train")
    assert C.check_seed(20000, "train") == 20000
    assert C.task_of(3, "dev") == "mug_tray"
    got = [C.task_of(s, "train") for s in range(20000, 20100)]
    assert got.count("mug_tray") == 60 and got.count("bottle_tray") == 20 and got.count("mug_marker") == 20


def test_other_task_on_fake_world(tmp_path):
    d = str(tmp_path / "b")
    meta = C.collect_episode(FakeWorld(), seed=10003, task="bottle_tray", variant="standard", out_dir=d, p=0.0)
    assert meta["success"] and "green bottle" in open(os.path.join(d, "calls", "c000", "prompt.txt"),
                                                        encoding="utf-8").read()
    assert np.isfinite(_rows(d)[0]["gt"]["tgt"]).all()
