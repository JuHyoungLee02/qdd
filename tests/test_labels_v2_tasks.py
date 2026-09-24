"""labels_v2 on the R2 tasks (target / place from the line's task; default = mug o3 -> tray o5)."""
import numpy as np
import pytest

from harvest.labels_v2 import delta, labels

BOTTLE, TRAY = (0.42, -0.30, 0.05), (0.46, -0.12, 0.0075)
BOX, MARK = (0.40, -0.25, 0.035), (0.45, -0.10, 0.001)


def _line(task, tgt, place, tpos, ppos, the, phe, grip, phase, gopen=True, hold=False, lifted=False, on=False):
    pred = {"gripper_open": gopen, f"holding({tgt})": hold, f"lifted({tgt})": lifted, f"on({tgt},{place})": on}
    objs = {tgt: {"pos": list(tpos), "he": list(the)}, place: {"pos": list(ppos), "he": list(phe)},
            "o3": {"pos": [0.5, 0.0, 0.0475], "he": [0.032, 0.032, 0.0475]}}
    return {"seed": 0, "kind": "P0", "k": 0, "task": task, "ds_id": "ds0", "phase": phase, "pred": pred,
            "state": {"present": sorted(objs, key=lambda k: int(k[1:])),
                      "obs": {"pred": pred, "raw": {"objs": objs, "grip": {"pos": list(grip)}}}}}


def test_bottle_approach_uses_the_bottle_height_and_targets_the_bottle():
    ln = _line("bottle_tray", "o8", "o5", BOTTLE, TRAY, (0.025, 0.025, 0.05), (0.09, 0.07, 0.0075),
               grip=(0.30, -0.30, 0.25), phase="approach")
    M, d = delta(ln)
    assert M == "approach"
    np.testing.assert_allclose(d, [0.12, 0.0, 0.05 + 0.05 + 0.10 - 0.25], atol=1e-12)
    lab = labels(ln)
    assert lab["target"] == "o8" and lab["dir_xy"] == "plus_x" and lab["dir_z"] == "down"


def test_bottle_carry_goes_to_the_tray_and_mug_is_ignored():
    ln = _line("bottle_tray", "o8", "o5", (0.30, -0.30, 0.15), TRAY, (0.025, 0.025, 0.05), (0.09, 0.07, 0.0075),
               grip=(0.30, -0.30, 0.182), phase="carry", gopen=False, hold=True, lifted=True)
    M, d = delta(ln)
    assert M == "carry"
    np.testing.assert_allclose(d, [0.16, 0.18, 0.20 - 0.182], atol=1e-12)
    lab = labels(ln)
    assert lab["target"] == "o5" and lab["phase_choice"] == "continue"


def test_box_place_on_marker_lands_on_the_table():
    grip = (0.45, -0.10, 0.10)
    box = (0.45, -0.10, 0.08)  # box bottom 4.5 cm above the table
    ln = _line("box_marker", "o9", "o11", box, MARK, (0.025, 0.025, 0.035), (0.04, 0.04, 0.001),
               grip=grip, phase="place_descend", gopen=False, hold=True, lifted=True)
    M, d = delta(ln)
    assert M == "place"
    gap = (0.08 - 0.035) - (0.001 + 0.001)
    np.testing.assert_allclose(d, [0.0, 0.0, -gap + 0.003], atol=1e-12)
    assert labels(ln)["target"] == "o11"


def test_phase_hold_and_next_use_the_task_predicates():
    ln = _line("box_marker", "o9", "o11", BOX, MARK, (0.025, 0.025, 0.035), (0.04, 0.04, 0.001),
               grip=(0.45, -0.10, 0.10), phase="carry", gopen=False, hold=False)
    assert labels(ln)["phase_choice"] == "hold"  # closed_empty (not holding the box)
    ln = _line("bottle_tray", "o8", "o5", (0.30, -0.30, 0.15), TRAY, (0.025, 0.025, 0.05), (0.09, 0.07, 0.0075),
               grip=(0.30, -0.30, 0.18), phase="lift", gopen=False, hold=True, lifted=True)
    assert labels(ln)["phase_choice"] == "next"  # S1 exit holding(o8) lifted(o8)


def test_unknown_task_is_refused():
    ln = _line("stack", "o8", "o5", BOTTLE, TRAY, (0.025, 0.025, 0.05), (0.09, 0.07, 0.0075),
               grip=(0.3, -0.3, 0.25), phase="approach")
    with pytest.raises(ValueError):
        labels(ln)
