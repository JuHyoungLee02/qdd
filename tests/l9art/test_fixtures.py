import math

import numpy as np
import pytest

from harvest.l9art import fixtures as FX


@pytest.mark.parametrize("fam", FX.FAMILIES)
def test_sample_all_seeds(fam):
    for s in range(40):
        sp = FX.sample(fam, s)
        assert sp["joints"] and sp["handles"]
        for jn, J in sp["joints"].items():
            assert J["link"] in sp["links"] and J["hi"] > J["lo"]
            assert abs(np.linalg.norm(J["axis"]) - 1) < 1e-6
        for ln, h in sp["handles"].items():
            assert h["joint"] in sp["joints"] and h["link"] == ln and h["words"]
        txt = FX.usda(sp)
        assert txt.count("{") == txt.count("}")
        assert txt.count("PhysicsCollisionAPI") >= len(sp["base"])


def test_sample_deterministic():
    assert FX.sample("drawer", 7) == FX.sample("drawer", 7)
    assert FX.sample("drawer", 7) != FX.sample("drawer", 8)


def test_drawer_handle_moves_towards_robot():
    sp = FX.sample("drawer", 3)
    ln = next(iter(sp["handles"]))
    j = sp["handles"][ln]["joint"]
    T = FX.T_of(np.eye(3), (0.6, -0.1, 0.75))
    a = FX.handle_frame(sp, ln, T)["gc"]
    b = FX.handle_frame(sp, ln, T, {j: 0.2})["gc"]
    assert np.allclose(b - a, [-0.2, 0, 0], atol=1e-9)


def test_door_opens_towards_robot():
    for s in range(20):
        sp = FX.sample("door", s)
        T = np.eye(4)
        a = FX.handle_frame(sp, "door", T)["gc"]
        b = FX.handle_frame(sp, "door", T, {"door_0": math.radians(80)})["gc"]
        assert b[0] < a[0] - 0.1  # the free edge swings out (-x)
        o, ax = FX.joint_world(sp, "door_0", T)
        assert abs(np.linalg.norm(b - o) - np.linalg.norm(a - o)) < 1e-9


def test_slide_moves_across():
    sp = FX.sample("slide", 1)
    a = FX.handle_frame(sp, "slide", np.eye(4))["gc"]
    b = FX.handle_frame(sp, "slide", np.eye(4), {"sld_0": 0.1})["gc"]
    assert abs(abs(b[1] - a[1]) - 0.1) < 1e-9 and abs(b[0] - a[0]) < 1e-9


def test_knob_mark_turns_clockwise_from_front():
    for s in range(30):
        sp = FX.sample("knob", s)
        ln = next(iter(sp["handles"]))
        h = sp["handles"][ln]
        if h["face"] != "front":
            continue
        a = FX.handle_frame(sp, ln, np.eye(4))["mark"]
        b = FX.handle_frame(sp, ln, np.eye(4), {h["joint"]: math.radians(90)})["mark"]
        o = np.asarray(sp["joints"][h["joint"]]["origin"])
        # seen from the robot (looking +x): image right = -y, up = +z; clockwise 90 deg maps left (+y) -> up (+z)
        assert (a - o)[1] > 0 and (b - o)[2] > 0.5 * abs((a - o)[1])
        return
    pytest.skip("no front knob in the seeds")


def test_button_pressed_moves_in():
    sp = FX.sample("button", 2)
    ln = next(iter(sp["handles"]))
    h = sp["handles"][ln]
    a = FX.handle_frame(sp, ln, np.eye(4))["gc"]
    b = FX.handle_frame(sp, ln, np.eye(4), {h["joint"]: 0.01})["gc"]
    assert np.allclose(b - a, -0.01 * np.asarray(h["fn"]), atol=1e-9)


def test_boxes_world_and_quat():
    sp = FX.sample("panel", 5)
    bw = FX.boxes_world(sp, FX.T_of(FX.rot_axis([0, 0, 1], 0.3), (0.5, 0, 0.7)))
    assert all(abs(np.linalg.norm(q) - 1) < 1e-6 for _, _, q in bw.values())
    assert np.allclose(FX.qmat(FX.quat_x_to([0, -1, 0])) @ [1, 0, 0], [0, -1, 0])
    assert np.allclose(FX.qmat(FX.quat_x_to([-1, 0, 0])) @ [1, 0, 0], [-1, 0, 0])
