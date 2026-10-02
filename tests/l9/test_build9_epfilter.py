"""build9.episode_filter (user 10-03): a KEY_OCC_ROBOTS episode with a key call (above_target / descend_close /
lower_open) >= 50 % occluded is dropped whole; non-key calls never drop it; arms are balanced per robot."""
import json
import os

from harvest.l9 import build9 as B9


def _ep(tmp, name, robot, arm, td, rows):
    d = os.path.join(str(tmp), name)
    os.makedirs(d)
    json.dump({"robot": robot, "arm": arm, "task_id": td}, open(os.path.join(d, "meta.json"), "w"))
    with open(os.path.join(d, "labels.jsonl"), "w") as f:
        for i, (step, occ) in enumerate(rows):
            f.write(json.dumps({"call": i, "step": step, "occ": occ}) + "\n")
    return d


def test_key_occlusion_steps(tmp_path):
    a = _ep(tmp_path, "a", "franka_mast", "right", "t", [("above_target", 0.1), ("lower_open", 0.5)])
    b = _ep(tmp_path, "b", "franka_mast", "right", "t", [("carry_up", 0.9), ("descend_close", 0.49)])
    c = _ep(tmp_path, "c", "franka_mast", "right", "t", [("tipped", None), ("descend_close", 0.7)])
    assert B9.key_occlusion(a)["key"] == "place"
    assert B9.key_occlusion(b) is None  # carry is not a key call; 0.49 < OCC_MAX
    assert B9.key_occlusion(c)["key"] == "grasp"


def test_filter_franka_only_and_arm_balance(tmp_path):
    occ = [("above_target", 0.8)]
    ok = [("above_target", 0.0)]
    eps = [_ep(tmp_path, "f1", "franka_mast", "right", "t1", occ),
           _ep(tmp_path, "f2", "franka_mast", "right", "t1", ok),
           _ep(tmp_path, "w1", "ffw_sg2", "left", "t1", occ),  # not a KEY_OCC robot: kept
           _ep(tmp_path, "w2", "ffw_sg2", "right", "t1", ok),
           _ep(tmp_path, "w3", "ffw_sg2", "right", "t2", ok),
           _ep(tmp_path, "w4", "ffw_sg2", "right", "t2", ok)]
    kept, rep = B9.episode_filter(eps)
    names = sorted(os.path.basename(d) for d in kept)
    assert "f1" not in names and "f2" in names and "w1" in names
    assert rep["key_occ"] == {"franka_mast": {"approach": 1}}
    w = rep["robots"]["ffw_sg2"]
    assert w["raw"] == {"left": 1, "right": 3} and w["after_balance"] == {"left": 1, "right": 1}
    assert w["need"] == {"left": 2}
    f = rep["robots"]["franka_mast"]
    assert f["raw"] == {"right": 2} and f["after_occ"] == {"right": 1} and f["need"] == {}
    # thinning takes the definition where the longer arm leads most (t2: 2 right vs 0 left) first
    assert sum(1 for n in names if n in ("w3", "w4")) == 0 and "w2" in names
