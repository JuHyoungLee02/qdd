"""E-SR1c (prereg_sr1c): branch samples joined to their source snapshot, leak / authority checks, the CLI options and
the prompt marker (pure parts of harvest/train/sr1c.py)."""
import json

import numpy as np
import pytest

from harvest.train import sr1c as S
from harvest.train import stageb_data as D


def _src(split="train", phase="approach"):
    return {"key": "P0_ep10001_k30", "split": split, "items": [{"question": "dir_xy"}],
            "context": {"text": "ctx", "images": [["head camera:", "dr/mug_tray/P0/img/ep10001/f0030_cam_head.jpg"]]},
            "committed": {"dir_xy": "plus_y", "dir_z": "down", "mag_coarse": "xlarge", "target": "o3",
                          "phase": "continue"},
            "skill_id": "pick", "phase_id": phase, "proprio": {"q": [0.0] * 7}, "action_exec": [[0.0] * 8] * 15,
            "action_script": [[0.0] * 8] * 15, "valid": [1] * 15,
            "aux": {"reg": {"g2tgt_dist": 0.3}, "cls": {}}, "H": 15, "verify": {"x": 1}, "arm": "right",
            "proprio_mask": None, "grip_src": "sim_width_m", "hz": 30}


def _branch(task="mug_tray", variant="dr", kind="P0", seed=10001, k=30):
    acts = [[0.1] * 7 + [0.107]] * 15
    return {"seed": seed, "kind": kind, "k": k, "hz": 30, "H": 15, "arm": "right", "skill_id": "pick",
            "phase_id": "approach", "task": task, "variant": variant, "action_exec": acts, "action_script": acts,
            "valid": [1] * 15, "aux": {"reg": {}, "cls": {}}, "verify": None,
            "committed": {"dir_xy": "minus_x", "dir_z": "up", "mag_coarse": "tiny"}, "decision": False,
            "branch": {"src": {"seed": seed, "kind": kind, "k": k}, "disp": [-0.0035, 0, 0.0035]}}


def test_branch_sample_keeps_the_observation_and_replaces_decision_and_target():
    src = _src()
    b = S.branch_sample(src, _branch(), 2)
    assert b["context"] is src["context"] and b["proprio"] is src["proprio"]
    assert b["items"] == [] and b["verify"] is None and b["aux"] == {"reg": {}, "cls": {}}
    assert b["committed"] == {"dir_xy": "minus_x", "dir_z": "up", "mag_coarse": "tiny", "target": "o3",
                              "phase": "continue"}
    assert np.allclose(np.asarray(b["action_exec"])[:, 7], 1.0)  # 0.107 m pad gap -> openness 1
    assert b["action_exec"] == b["action_script"] and b["valid"] == [1] * 15
    assert b["key"] == "P0_ep10001_k30_br2" and b["branch"] is True
    assert src["items"] and src["committed"]["dir_xy"] == "plus_y"  # source untouched


def test_join_refuses_eval_split_sources_and_non_far_sources():
    with pytest.raises(ValueError, match="split"):
        S.branch_sample(_src(split="val"), _branch(), 0)
    with pytest.raises(ValueError, match="authority"):
        S.branch_sample(_src(phase="descend"), _branch(), 0)


def test_join_all_by_sample_id():
    src = _src()
    by = {"dr/mug_tray/P0/ep10001/k30": src}
    out, st = S.join_branches(by, [_branch(), _branch()])
    assert len(out) == 2 and st == {"n_rows": 2, "joined": 2, "missing": 0, "sources": 1}
    out, st = S.join_branches(by, [_branch(k=40)])
    assert st["missing"] == 1 and out == []


def test_options_defaults_and_marker():
    pytest.importorskip("torch")  # the parser extends stageb_train (torch)
    ap = S.build_parser()
    a = ap.parse_args(["train", "--run", "x", "--ma2", "c0"])
    assert a.cf_branch == "" and a.cf_frac == 0.0 and a.dec_cond == "none"
    assert not S.on(a)
    a = ap.parse_args(["train", "--run", "x", "--ma2", "c0", "--cf-branch", "/b", "--cf-frac", "0.5",
                       "--dec-cond", "adaln@v1"])
    assert S.on(a)
    m = S.mark_prompt_config({"camera": ["c"], "sha": "old"}, a)
    assert m["sr1c"] == S.SR1C_VER and m["sr1c_cf_frac"] == 0.5 and m["sr1c_dec_cond"] == "adaln@v1"
    assert m["sha"] != "old" and set(m["sr1c_files_sha"]) == set(S.SR1C_FILES)


def test_install_refuses_other_recipes():
    pytest.importorskip("torch")
    ap = S.build_parser()
    a = ap.parse_args(["train", "--run", "x", "--ma2", "c1", "--cf-branch", "/b", "--cf-frac", "0.5"])
    with pytest.raises(SystemExit):
        S.install(object(), a)
    a = ap.parse_args(["train", "--run", "x", "--ma2", "c0", "--cf-frac", "0.5"])
    with pytest.raises(SystemExit):
        S.install(object(), a)  # a fraction without branches
    from harvest.train import stageb_train as T
    before = (T._load_data, T.prompt_config, T.new_model)
    S.install(T, ap.parse_args(["train", "--run", "x", "--ma2", "c0"]))  # options off: stageb_train untouched
    assert (T._load_data, T.prompt_config, T.new_model) == before
