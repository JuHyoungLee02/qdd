"""E-SR0 (prereg_sr0): the fixed counterfactual decision set given to the expert (pure parts of tools/sr0/sr0_eval.py)."""
import importlib.util
import os

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("sr0_eval", os.path.join(ROOT, "tools", "sr0", "sr0_eval.py"))
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)

TRUE = {"dir_xy": "plus_x", "dir_z": "none_z", "mag_coarse": "small"}


def test_unit_xy_matches_the_labels_v2_bins():
    from harvest.labels_v2 import dir_xy_label
    for d in E.DIR_XY8:
        u = E.unit_xy(d)
        assert abs(np.linalg.norm(u) - 1) < 1e-12
        assert dir_xy_label([0.03 * u[0], 0.03 * u[1], 0.0]) == d  # 3 cm along the unit vector falls in bin d
    assert np.all(E.unit_xy("none_xy") == 0)


def test_flip_reverses_signs_and_keeps_none():
    assert E.FLIP_XY["plus_x_minus_y"] == "minus_x_plus_y" and E.FLIP_XY["none_xy"] == "none_xy"
    for d in E.DIR_XY8:
        assert np.allclose(E.unit_xy(E.FLIP_XY[d]), -E.unit_xy(d))
    assert E.FLIP_Z == {"up": "down", "down": "up", "none_z": "none_z"}


def test_condition_set_is_fixed_and_changes_one_question_at_a_time():
    preds = {"dir_xy": "minus_y", "dir_z": "up", "mag_coarse": "large"}
    cs = E.condition_set(TRUE, preds, grip=False)
    names = [n for n, _, _ in cs]
    assert names == E.cond_names(grip=False) and len(names) == len(set(names)) == 20
    by = {n: (c, p) for n, c, p in cs}
    assert by["true"] == (TRUE, None) and by["pred"] == (preds, None)
    assert by["flip"][0] == {"dir_xy": "minus_x", "dir_z": "none_z", "mag_coarse": "small"}
    for d in E.DIR_XY9:
        assert by[f"xy:{d}"][0] == {**TRUE, "dir_xy": d}
    for d in E.DIR_Z3:
        assert by[f"z:{d}"][0] == {**TRUE, "dir_z": d}
    for m in E.MAGS:
        assert by[f"mag:{m}"][0] == {**TRUE, "mag_coarse": m}
    assert TRUE == {"dir_xy": "plus_x", "dir_z": "none_z", "mag_coarse": "small"}  # input not modified


def test_condition_set_grip_adds_the_sub_phase_pair_with_true_decisions():
    cs = E.condition_set({**TRUE, "target": "o3", "phase": "continue"}, {}, grip=True)
    by = {n: (c, p) for n, c, p in cs}
    assert len(cs) == 22 and [n for n, _, _ in cs] == E.cond_names(grip=True)
    assert by["pid:close"] == ({**TRUE, "target": "o3", "phase": "continue"}, "close")
    assert by["pid:open"][1] == "open"
    assert by["xy:minus_x"][0]["target"] == "o3"  # other questions keep the true decision


def test_condition_set_needs_the_three_joystick_labels():
    with pytest.raises(ValueError):
        E.condition_set({"dir_xy": "plus_x", "dir_z": "up"}, {}, grip=False)


def test_check_vocab_refuses_a_forced_value_the_checkpoint_does_not_know():
    dec = [f"dir_xy={d}" for d in E.DIR_XY9] + [f"dir_z={d}" for d in E.DIR_Z3] + \
          [f"mag_coarse={m}" for m in E.MAGS]
    E.check_vocab(dec, ["approach"], grip=False)
    with pytest.raises(SystemExit):
        E.check_vocab([x for x in dec if x != "mag_coarse=xlarge"], [], grip=False)
    with pytest.raises(SystemExit):
        E.check_vocab(dec, ["close"], grip=True)  # 'open' missing
    E.check_vocab(dec, ["close", "open"], grip=True)
