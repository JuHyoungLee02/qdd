"""Synthetic-action stage-B rows from pool snapshots (pre-R7 tiny checkpoint): contract-valid, verify targets = the
E-M4b test predicates, action = held snapshot command, flagged synthetic."""
import numpy as np

from harvest.train import stageb_data as D
from harvest.train.stageb_poolrows import ARM_IDS, pool_row


def _line():
    raw = {"objs": {"o3": {"pos": [0.42, -0.33, 0.0475], "quat": [1, 0, 0, 0], "he": [0.032, 0.032, 0.0475]},
                    "o5": {"pos": [0.39, -0.15, 0.0075], "quat": [1, 0, 0, 0], "he": [0.09, 0.07, 0.0075]}},
           "grip": {"w": 0.1069, "effort": 0.08, "pos": [0.33, -0.25, 0.23]}, "contacts": [], "support": {}}
    pred = {"on(o3,o5)": False, "in_contact(o3,o5)": False, "above(o3,o5)": False, "near(o3,o5)": False,
            "holding(o3)": False, "lifted(o3)": False, "gripper_open": True, "upright(o3)": True}
    return {"seed": 2000, "kind": "P1", "k": 1, "split": "fit", "phase": "approach", "pred": pred,
            "state": {"present": ["o3", "o5"], "obs": {"raw": raw, "pred": pred}}}


def test_pool_row_contract_and_targets():
    z = {k: np.arange(3 * 31, dtype=float).reshape(3, 31) for k in ("joint_pos", "joint_vel", "joint_effort_target")}
    z["action"] = np.tile(np.arange(8, dtype=float), (3, 1))
    r = pool_row(_line(), z, H=15)
    D.check_row(r)
    assert r["synthetic_actions"] and r["action_exec"] == [list(map(float, range(8)))] * 15
    assert r["proprio"]["q"] == [31.0 + i for i in ARM_IDS]
    assert r["verify"]["truth"]["gripper_open"] is True and r["verify"]["truth"]["on_tp"] is False
    assert set(r["verify"]["truth"]) == set(D.VERIFY_PREDS)
    y, m = D.verify_vecs(r["verify"]["truth"])
    assert m.sum() == len(D.VERIFY_PREDS) and y[D.VERIFY_PREDS.index("gripper_open")] == 1.0
    assert r["skill_id"] == "pick" and r["aux"]["cls"]["gripper_open"] == 1
