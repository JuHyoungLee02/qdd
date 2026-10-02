"""tools/onboard/grip_check.py on the committed gap tables: items (1)-(3) pass for every gripper, item (4) frame
passes for the parallel grippers (the G1 Dex3-1 frame flag is a reported finding, handed to the G1 team)."""
import pytest

from harvest.l9 import hand9 as H
from tools.onboard import grip_check as GC


@pytest.mark.parametrize("profile,arm", sorted(H.GRIPPER_JSON))
def test_items_1_to_3_pass(profile, arm):
    r = GC.run(profile, arm)
    by = {c["name"]: c for c in r["checks"]}
    for n in ("grip1_gap_table", "grip2_open_empty", "grip3_any_finger"):
        assert by[n]["ok"], (profile, arm, by[n]["detail"])


@pytest.mark.parametrize("profile,arm", [("ffw_sg2", "right"), ("franka_mast", "right"), ("r1pro", "left")])
def test_frame_parallel_grippers(profile, arm):
    by = {c["name"]: c for c in GC.run(profile, arm)["checks"]}
    assert by["grip4_frame"]["ok"], by["grip4_frame"]["detail"]


def test_torso_item():
    eps = {"episodes": [{"lift_joint": [0.0] * 4}, {"lift_joint": [-0.05] * 4}], "ranges": {"lift_joint": [-0.1, 0.0]}}
    by = {c["name"]: c for c in GC.run("ffw_sg2", "right", torso=eps)["checks"]}
    assert by["grip6_torso"]["ok"]
