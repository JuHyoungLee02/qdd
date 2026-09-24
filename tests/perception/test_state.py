import numpy as np
import pytest

from harvest.labels_v2 import code_rule_v2, labels
from harvest.perception.state import (estimate_contacts, estimate_predicates, est_line, geometry_block_flags,
                                      s1_text)

HE = {"o3": [0.032, 0.032, 0.0475], "o5": [0.09, 0.07, 0.0075]}
S1_TXT = ("t_state: f0 (t=0.00s)  contract: c1  stage: S1 \"pick up mug o3\"\nrobot: gripper=open arm=still\n"
          "objects:\n  o3 mug red | on(table) | upright\n  o5 tray blue | on(table) | upright\n"
          "facts: gripper_open=yes holding(o3)=no lifted(o3)=no upright(o3)=yes upright(o5)=yes\n"
          "stage S1: exit=holding(o3) lifted(o3) invariants= elapsed=normal\nchanges (last 3s): ")
MUG, TRAY = [0.428, -0.382, 0.0475], [0.477, -0.174, 0.0075]


def _line(grip, w=0.107, effort=0.08, o3=MUG, phase="approach", gopen=True, hold=False):
    pred = {"gripper_open": gopen, "holding(o3)": hold, "lifted(o3)": False, "on(o3,o5)": False,
            "upright(o3)": True, "upright(o5)": True}
    objs = {"o3": {"pos": list(o3), "quat": [1, 0, 0, 0], "he": HE["o3"]},
            "o5": {"pos": list(TRAY), "quat": [1, 0, 0, 0], "he": HE["o5"]}}
    raw = {"objs": objs, "grip": {"w": w, "effort": effort, "pos": list(grip)}, "contacts": [], "support": {}}
    return {"seed": 0, "kind": "P0", "k": 0, "t": 0.0, "phase": phase, "text_state": S1_TXT, "pred": pred,
            "state": {"present": ["o3", "o5"], "planner": {"t_phase0": 0.0}, "obs": {"pred": pred, "raw": raw}}}


def test_contacts_from_geometry():
    pos = {"o3": np.array([0.4, 0.0, 0.0475 + 0.015 + 0.004]), "o5": np.array([0.41, 0.01, 0.0075])}
    c = estimate_contacts(pos, HE, grip_pos=np.array([0.4, 0.0, 0.25]))
    assert frozenset({"o3", "o5"}) in c and not any("gripper" in x for x in c)
    c = estimate_contacts(pos, HE, grip_pos=pos["o3"] + [0, 0, 0.02])
    assert frozenset({"gripper", "o3"}) in c
    # grasped mug in the sim: fingertip midpoint 4.1-4.3 cm from the mug centre (DEV 0 P0 k10-k22)
    c = estimate_contacts(pos, HE, grip_pos=pos["o3"] + [0.012, 0.0, 0.041])
    assert frozenset({"gripper", "o3"}) in c
    c = estimate_contacts(pos, HE, grip_pos=pos["o3"] + [0.0, 0.0, 0.09])
    assert frozenset({"gripper", "o3"}) not in c
    pos["o3"] = np.array([0.6, 0.0, 0.0475])  # beside the tray, not on it
    assert frozenset({"o3", "o5"}) not in estimate_contacts(pos, HE, grip_pos=np.array([0, 0, 1.0]))


def test_estimate_predicates_holding_and_table_support():
    est = {"o3": {"pos": np.array(MUG) + [0, 0, 0.006], "occluded": False, "id_uncertain": False},
           "o5": {"pos": np.array(TRAY), "occluded": False, "id_uncertain": False}}
    grip = {"w": 0.064, "effort": 5.0, "pos": np.array(MUG) + [0, 0, 0.03]}
    pred, support, _ = estimate_predicates(est, grip, HE)
    assert pred["holding(o3)"] is True and pred["gripper_open"] is False
    assert support["o3"] == "table" and pred["lifted(o3)"] is False  # 6 mm above: inside the table tolerance
    est["o3"]["id_uncertain"] = True
    pred, _, _ = estimate_predicates(est, grip, HE)
    assert pred["holding(o3)"] is None and pred["near(o3,o5)"] is None


def test_est_line_with_true_positions_reproduces_truth_labels():
    ln = _line(grip=[0.334, -0.247, 0.244])
    est = {k: {"pos": np.array(ln["state"]["obs"]["raw"]["objs"][k]["pos"]), "occluded": False,
               "id_uncertain": False} for k in ("o3", "o5")}
    e = est_line(ln, est)
    txt = s1_text(e)
    got = code_rule_v2(txt)
    want = labels(ln)
    for q in ("dir_xy", "dir_z", "mag_coarse", "target", "phase_choice"):
        assert got[q] == want[q], q
    assert "gripper=open" in e["text_state"] and "arm=still" in e["text_state"]


def test_est_line_moves_object_and_flags_it():
    ln = _line(grip=[0.334, -0.247, 0.244])
    est = {"o3": {"pos": np.array(MUG) + [0.01, 0, 0], "occluded": True, "id_uncertain": False},
           "o5": {"pos": np.array(TRAY), "occluded": False, "id_uncertain": False}}
    e = est_line(ln, est)
    assert e["state"]["obs"]["raw"]["objs"]["o3"]["pos"][0] == pytest.approx(MUG[0] + 0.01)
    assert ln["state"]["obs"]["raw"]["objs"]["o3"]["pos"][0] == pytest.approx(MUG[0])  # input untouched
    blk = geometry_block_flags(e)
    o3 = [x for x in blk.split("\n") if x.startswith("  o3")][0]
    assert o3.endswith(" occluded") and "dx=+10.4" in o3
    assert "holding(o3)=unknown" in e["text_state"]
    code_rule_v2(s1_text(e))  # still parses


def test_est_line_drops_never_seen_object():
    ln = _line(grip=[0.334, -0.247, 0.244])
    est = {"o3": {"pos": None, "occluded": True, "id_uncertain": False},
           "o5": {"pos": np.array(TRAY), "occluded": False, "id_uncertain": False}}
    e = est_line(ln, est)
    assert e["state"]["present"] == ["o5"]
    assert "  o3" not in geometry_block_flags(e)
