"""Pure tests of harvest.l9.curobo9 (no cuRobo): config lookup, frames, approach classes, reach lookup."""
import json
import os

import numpy as np
import pytest

from harvest.l9 import curobo9 as C


def _have(profile, arm):
    return os.path.exists(C.config_path(profile, arm))


@pytest.mark.parametrize("profile,arm", [(p, a) for p, (_, arms) in C.PROFILES.items() for a in arms])
def test_config_frames(profile, arm):
    if not _have(profile, arm):
        pytest.skip("config not built yet")
    k = C.load_config(profile, arm)["robot_cfg"]["kinematics"]
    assert C.tool_frame(profile, arm) == f"{arm}_l9_tcp"
    js = C.arm_joints(profile, arm)
    assert len(js) == 7 and not set(js) & set(k["lock_joints"])
    assert k["base_link"] == {"ffw_sg2": "arm_base_link", "franka_mast": "panda_link0", "r1pro": "torso_link4",
                              "g1": "torso_link"}[profile]
    assert len(k["cspace"]["default_joint_position"]) == len(k["cspace"]["joint_names"])


def test_ffw_joint_order():
    if not _have("ffw_sg2", "right"):
        pytest.skip("config not built yet")
    assert C.arm_joints("ffw_sg2", "right") == [f"arm_r_joint{i}" for i in range(1, 8)]
    assert C.arm_joints("ffw_sg2", "left") == [f"arm_l_joint{i}" for i in range(1, 8)]


def test_with_locks():
    cfg = {"robot_cfg": {"kinematics": {"lock_joints": {"g1": 0.0, "g2": 0.0}}}}
    out = C.with_locks(cfg, {"g1": 0.5})
    assert out["robot_cfg"]["kinematics"]["lock_joints"] == {"g1": 0.5, "g2": 0.0}
    with pytest.raises(ValueError):
        C.with_locks(cfg, {"arm1": 0.1})


def test_approach_class():
    assert C.approach_class((0, 0, -1)) == "top"
    assert C.approach_class((np.sin(np.radians(20)), 0, -np.cos(np.radians(20)))) == "top"
    assert C.approach_class((np.sin(np.radians(45)), 0, -np.cos(np.radians(45)))) == "oblique"
    assert C.approach_class((1, 0, 0), obj_xy_base=(0.5, 0.0)) == "front"
    assert C.approach_class((0, 1, 0), obj_xy_base=(0.5, 0.0)) == "side"
    assert C.approach_class((1, 1.2, 0), obj_xy_base=(0.5, 0.0)) == "side"  # 50 deg off the base->object line


def test_reach_lookup(tmp_path, monkeypatch):
    g = {"x": {"lo": 0.0, "step": 0.1, "n": 2}, "y": {"lo": 0.0, "step": 0.1, "n": 2}, "z": {"lo": 0.0, "step": 0.1, "n": 2}}
    ok = {a: "00000000" for a in C.APPROACHES}
    ok["top"] = "00000001"  # cell (1, 1, 1)
    p = tmp_path / "ffw_sg2_right.json"
    p.write_text(json.dumps({"grid": g, "ok": ok}))
    monkeypatch.setattr(C, "REACH_DIR", str(tmp_path))
    C._REACH.clear()
    assert C.reach_ok("ffw_sg2", "right", (0.1, 0.1, 0.1), "top")
    assert not C.reach_ok("ffw_sg2", "right", (0.1, 0.1, 0.1), "side")
    assert not C.reach_ok("ffw_sg2", "right", (0.0, 0.1, 0.1), "top")
    assert not C.reach_ok("ffw_sg2", "right", (0.5, 0.1, 0.1), "top")  # outside the grid
    C._REACH.clear()


def test_ffw_reach_map_real():
    if not os.path.exists(C.reach_path("ffw_sg2", "right")):
        pytest.skip("reach map not built yet")
    C._REACH.clear()
    assert C.reach_ok("ffw_sg2", "right", (0.45, -0.25, -0.35), "top")  # the v1 top-down work zone
    assert not C.reach_ok("ffw_sg2", "right", (0.85, -0.25, -0.85), "top")  # 1.2 m from the shoulder
    assert not C.reach_ok("ffw_sg2", "right", (2.0, 0.0, 0.0), "top")  # outside the grid
