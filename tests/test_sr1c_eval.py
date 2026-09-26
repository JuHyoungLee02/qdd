"""E-SR1c (prereg_sr1c §3): plausible-edit / stress conditions and snapshot strata of tools/sr1c/sr1c_eval.py."""
import importlib.util
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("sr1c_eval", os.path.join(ROOT, "tools", "sr1c", "sr1c_eval.py"))
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)
LAB = {"dir_xy": "plus_x", "dir_z": "down", "mag_coarse": "xlarge", "target": "o3", "phase": "continue"}


def test_edits_rotate_the_recorded_motion_and_keep_other_labels():
    es = {n: (c, info) for n, c, p, info in E.edit_conditions(LAB, [0.02, 0.0, -0.01])}
    assert list(es) == [f"edit:{t}" for t in E.EDIT_DEG]
    c, info = es["edit:90"]
    assert c["dir_xy"] == "plus_y" and c["mag_coarse"] == "medium" and np.allclose(info[:2], [0.0, 0.02])
    assert c["dir_z"] == "down" and c["target"] == "o3" and c["phase"] == "continue"
    assert es["edit:180"][0]["dir_xy"] == "minus_x"
    assert es["edit:-90"][0]["dir_xy"] == "minus_y"
    assert es["edit:45"][0]["dir_xy"] == "plus_x_plus_y" and es["edit:-45"][0]["dir_xy"] == "plus_x_minus_y"
    assert es["edit:30"][0]["dir_xy"] == "plus_x_plus_y"  # 30 deg is nearer the diagonal sector than +x


def test_edit_length_is_clipped_to_one_to_five_cm_and_small_motion_has_no_edit():
    es = {n: (c, info) for n, c, p, info in E.edit_conditions(LAB, [0.10, 0.0, 0.0])}
    assert np.isclose(np.hypot(*es["edit:45"][1][:2]), 0.05) and es["edit:45"][0]["mag_coarse"] == "large"
    es = {n: (c, info) for n, c, p, info in E.edit_conditions(LAB, [0.006, 0.0, 0.0])}
    assert np.isclose(np.hypot(*es["edit:90"][1][:2]), 0.01) and es["edit:90"][0]["mag_coarse"] == "small"
    assert E.edit_conditions(LAB, [0.003, 0.003, 0.05]) == []


def test_snapshot_strata_from_the_row_aux():
    s = {"aux": {"reg": {"g2tgt_dist": 0.3}, "cls": {}}, "phase_id": "approach"}
    m = E.snap_meta(s)
    assert m["a_priv"] == 1.0 and m["stratum"] == "far" and m["dist_priv"] == 0.3
    s = {"aux": {"reg": {"g2tgt_dist": 0.3}, "cls": {}}, "phase_id": "descend"}
    assert E.snap_meta(s)["stratum"] == "near"
