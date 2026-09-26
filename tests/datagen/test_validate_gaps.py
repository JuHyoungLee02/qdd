"""validate_episode records every broken R2 file as a structural error instead of passing it or raising
(R7 cycles 31-37 NOTE: N131, N132, N142, N143, N154, N165, N190, N193, N210)."""
import json

import numpy as np
import pytest

from harvest.datagen import episode as E
from harvest.datagen import validate as V

from .test_episode_files import _fake_episode

pytest.importorskip("PIL.Image")

SEED = 3


@pytest.fixture
def folder(tmp_path):
    f = str(tmp_path / "dr" / "bottle_tray" / "P0")
    E.finalize(_fake_episode(f, seed=SEED), f, H=15)  # 23 frames, decisions k 0 / 10 / 20, rows k 0..21
    assert V.validate_episode(f, SEED)["errors"] == []
    return f


def _edit_jsonl(path, k, fn):
    """Apply fn to the item with index k of a JSON-lines file (NaN is written as the JSON token NaN)."""
    items = [json.loads(x) for x in open(path, encoding="utf-8")]
    fn(items[k])
    with open(path, "w", encoding="utf-8") as f:
        for x in items:
            f.write(json.dumps(x) + "\n")


def _lines(folder):
    return f"{folder}/ep{SEED}.jsonl"


def _rows(folder):
    return f"{folder}/rows/ep{SEED}.stageb.jsonl"


def _labs(folder):
    return f"{folder}/rows/ep{SEED}.labels_v2.jsonl"


def _errors(folder):
    rep = V.validate_episode(folder, SEED)
    assert not rep["structural_ok"] and not rep["valid_for_training"], rep["errors"]
    return " | ".join(rep["errors"])


# ---------------------------------------------------------------- N131: decision frames come from is_decision(k)
def test_decision_flag_flip_is_an_error(folder):
    _edit_jsonl(_lines(folder), 20, lambda ln: ln.update(decision=False))
    assert "decision flag" in _errors(folder)


def test_missing_verify_target_at_a_decision_frame_whose_flag_was_flipped(folder):
    def flip(ln):
        ln["decision"] = False
        del ln["verify"]["prev_step"]
    _edit_jsonl(_lines(folder), 20, flip)
    assert "verification target missing at [20]" in _errors(folder)


# ---------------------------------------------------------------- N132 / N210 (2): missing npz arrays
@pytest.mark.parametrize("key", ["grip", "tau", "hold_n"])
def test_missing_npz_array_is_an_error(folder, key):
    p = f"{folder}/ep{SEED}.npz"
    z = dict(np.load(p))
    del z[key]
    np.savez_compressed(p, **z)
    assert f"npz {key}: missing" in _errors(folder)


# ---------------------------------------------------------------- N193: row without k
def test_row_without_k_is_an_error(folder):
    _edit_jsonl(_rows(folder), 7, lambda r: r.pop("k"))
    err = _errors(folder)
    assert "stageb rows are not one per non-terminal frame" in err and "missing field 'k'" in err


# ---------------------------------------------------------------- N142 / N210 (3): frame time
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), "0.1", None, True])
def test_frame_time_not_a_finite_number_is_an_error(folder, bad):
    _edit_jsonl(_lines(folder), 11, lambda ln: ln.update(t=bad))
    assert "frame time not a finite number at [11]" in _errors(folder)


def test_frame_time_not_a_number_on_the_last_frame_is_an_error(folder):
    _edit_jsonl(_lines(folder), 22, lambda ln: ln.update(t="x"))  # the hold_n sum reads the last frame's time
    assert "frame time not a finite number at [22]" in _errors(folder)


# ---------------------------------------------------------------- N143 / N154 / N190: row and label key fields
@pytest.mark.parametrize("field,value,msg", [
    ("seed", SEED + 1, "seed 4 != episode 3"),
    ("kind", "P1", "kind 'P1' != episode 'P0'"),
    ("task", "mug_tray", "task 'mug_tray' != episode 'bottle_tray'"),
    ("phase_id", None, "phase_id None != frame phase 'approach'"),
    ("phase_id", "descend", "phase_id 'descend' != frame phase 'approach'"),
    ("skill_id", "r7c35_skill", "skill_id 'r7c35_skill' != 'pick'"),
])
def test_row_field_that_disagrees_with_the_episode_is_an_error(folder, field, value, msg):
    _edit_jsonl(_rows(folder), 5, lambda r: r.update({field: value}))
    assert f"row k5: {msg}" in _errors(folder)


@pytest.mark.parametrize("field,value,msg", [
    ("seed", SEED + 1, "seed 4 != episode 3"),
    ("kind", "P1", "kind 'P1' != episode 'P0'"),
    ("task", "mug_tray", "task 'mug_tray' != episode 'bottle_tray'"),
])
def test_label_row_field_that_disagrees_with_the_episode_is_an_error(folder, field, value, msg):
    _edit_jsonl(_labs(folder), 1, lambda r: r.update({field: value}))
    assert f"labels_v2 k10: {msg}" in _errors(folder)


# ---------------------------------------------------------------- N165: aux values, executed actions
@pytest.mark.parametrize("group,name,value", [("reg", "g2tgt_dx", float("nan")), ("reg", "g2tgt_dx", "0.1"),
                                              ("cls", "gripper_open", 2), ("cls", "gripper_open", float("nan"))])
def test_bad_aux_value_is_an_error(folder, group, name, value):
    _edit_jsonl(_rows(folder), 9, lambda r: r["aux"][group].update({name: value}))
    assert f"row k9: aux.{group}.{name}" in _errors(folder)


@pytest.mark.parametrize("key", ["action_exec", "action_script"])
def test_row_action_that_disagrees_with_the_npz_actions_is_an_error(folder, key):
    def big(r):
        r[key][3][2] = 1e6
    _edit_jsonl(_rows(folder), 4, big)
    assert f"row k4: {key} != npz action" in _errors(folder)


# ---------------------------------------------------------------- boundaries accepted before (R7 cycle 37 controls)
@pytest.mark.parametrize("where,field,value", [("rows", "H", 15.0), ("rows", "k", 5.0), ("lines", "k", 5.0)])
def test_integral_floats_accepted_before_still_pass(folder, where, field, value):
    _edit_jsonl(_rows(folder) if where == "rows" else _lines(folder), 5, lambda x: x.update({field: value}))
    assert V.validate_episode(folder, SEED)["errors"] == []


def test_empty_aux_extra_label_field_and_extra_proprio_key_still_pass(folder):
    _edit_jsonl(_rows(folder), 6, lambda r: r.update(aux={}))
    _edit_jsonl(_rows(folder), 7, lambda r: r["proprio"].update(extra=[float("nan")]))
    _edit_jsonl(_labs(folder), 2, lambda x: x.update(r7_extra="x"))
    assert V.validate_episode(folder, SEED)["errors"] == []


def test_row_with_null_k_and_null_phase_is_an_error_not_an_exception(folder):
    _edit_jsonl(_rows(folder), 5, lambda r: r.update(k=None, phase_id=None, skill_id="place"))
    assert "stageb rows are not one per non-terminal frame" in _errors(folder)


# ---------------------------------------------------------------- N210 (1): proprio values finite
@pytest.mark.parametrize("key", ["q", "qd", "tau", "grip"])
def test_non_finite_proprio_is_an_error(folder, key):
    def nan(r):
        r["proprio"][key][0] = float("nan")
    _edit_jsonl(_rows(folder), 12, nan)
    assert f"row k12: proprio.{key} not finite" in _errors(folder)


def test_non_numeric_proprio_is_an_error(folder):
    def s(r):
        r["proprio"]["q"][0] = "x"
    _edit_jsonl(_rows(folder), 12, s)
    assert "row k12: proprio.q not finite" in _errors(folder)
