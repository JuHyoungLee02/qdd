"""E-SR1d (prereg_sr1d): S-E2E branch samples joined to their source sample, split / stratum / check refusals, CLI
options and the no-op default (pure parts of harvest/train/sr1d.py)."""
import numpy as np
import pytest

from harvest.train import sr1d as S


def _src(split="train"):
    return {"key": "RB1_ep3_k10", "split": split, "items": [{"question": "dir_xy"}],
            "context": {"text": "ctx\nmotion: arm=slow gripper=still", "images": []},
            "committed": {"dir_xy": "plus_y", "dir_z": "down", "mag_coarse": "xlarge"},
            "skill_id": "teleop", "phase_id": "na", "proprio": {"q": [0.0] * 7}, "action_exec": [[0.0] * 8] * 5,
            "action_script": [[0.0] * 8] * 5, "valid": [1] * 5, "aux": {"reg": {}, "cls": {}}, "H": 5,
            "verify": None, "arm": "right", "grip_src": "RB1", "hz": 10}


def _branch(stratum="far", a=1.0, ok=True, kind="RB1", seed=3, k=10):
    acts = [[0.1] * 7 + [1.10]] * 5
    return {"seed": seed, "kind": kind, "k": k, "hz": 10, "H": 5, "arm": "right", "action_exec": acts,
            "action_script": acts, "valid": [1] * 5, "committed": {"dir_xy": "minus_x", "dir_z": "up",
                                                                   "mag_coarse": "tiny"},
            "branch": {"ok": ok, "stratum": stratum, "a": a}}


def test_branch_sample_keeps_the_observation_and_replaces_decision_and_target():
    src = _src()
    b = S.branch_sample(src, _branch(), 1)
    assert b["context"] is src["context"] and b["proprio"] is src["proprio"]
    assert b["items"] == [] and b["branch"] is True and b["key"] == "RB1_ep3_k10_br1"
    assert b["committed"] == {"dir_xy": "minus_x", "dir_z": "up", "mag_coarse": "tiny"}
    assert np.allclose(np.asarray(b["action_exec"])[:, 7], 0.0)  # RB1 joint 1.10 = closed -> openness 0
    assert src["committed"]["dir_xy"] == "plus_y" and src["items"]


def test_branch_sample_refusals():
    with pytest.raises(ValueError, match="split"):
        S.branch_sample(_src("val"), _branch(), 0)
    with pytest.raises(ValueError, match="stratum"):
        S.branch_sample(_src(), _branch(stratum="near", a=0.0), 0)
    with pytest.raises(ValueError, match="kinematic"):
        S.branch_sample(_src(), _branch(ok=False), 0)
    assert S.branch_sample(_src(), _branch(stratum="near", a=0.0), 0, mode="all")["branch"] is True


def test_join_counts_missing_and_numbers_branches_per_source():
    by = {"RB1_ep3_k10": _src()}
    out, st = S.join_branches(by, [_branch(), _branch(), _branch(seed=4)])
    assert st == {"n_rows": 3, "joined": 2, "missing": 1, "sources": 1}
    assert [b["key"] for b in out] == ["RB1_ep3_k10_br0", "RB1_ep3_k10_br1"]


def test_options_default_off_and_parse():
    pytest.importorskip("torch")
    ap = S.build_parser()
    a = ap.parse_args(["train", "--run", "x"])
    assert not S.on(a) and a.sr1d_mode == "far"
    a = ap.parse_args(["train", "--run", "x", "--sr1d-branch", "d", "--sr1d-frac", "0.5", "--sr1d-mode", "all"])
    assert S.on(a) and a.sr1d_frac == 0.5


def test_install_refuses_non_se2e_or_no_motion_line():
    pytest.importorskip("torch")
    from harvest.train import stageb_train as TR
    ap = S.build_parser()
    a = ap.parse_args(["train", "--run", "x", "--sr1d-branch", "d", "--sr1d-frac", "0.5"])
    with pytest.raises(SystemExit):
        S.install(TR, a)  # --data r2 default
    a = ap.parse_args(["train", "--run", "x", "--data", "se2e", "--state", "IMG", "--sr1d-branch", "d",
                       "--sr1d-frac", "0.5"])
    with pytest.raises(SystemExit):
        S.install(TR, a)  # no motion line
    a = ap.parse_args(["train", "--run", "x"])
    before = (TR._load_data, TR.prompt_config_t, TR.new_model)
    S.install(TR, a)
    assert (TR._load_data, TR.prompt_config_t, TR.new_model) == before
