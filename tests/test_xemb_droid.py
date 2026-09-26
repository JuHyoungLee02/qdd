import numpy as np

from tools.xemb.src_droid import names_of, tilt_deg_euler


def test_names_put_in():
    assert names_of("Put the blue block in the green bowl") == ("blue block", "green bowl")
    assert names_of("Put the orange cup onto the windowsill.") == ("orange cup", "windowsill")
    assert names_of("Pick up the longer upright white container from the table and put it in the orange plastic bag") \
        == ("longer upright white container", "orange plastic bag")
    assert names_of("Pick the marker and put it in the plastic box") == ("marker", "plastic box")


def test_names_reject_non_pick_place():
    assert names_of("Move the tile letter s to the left") is None
    assert names_of("Close the open drawer") is None
    assert names_of("Use the white cloth to wipe the table") is None
    assert names_of("") is None


def test_tilt_topdown():
    # DROID euler xyz; roll pi = gripper z pointing straight down
    assert tilt_deg_euler([np.pi, 0, 0]) < 1e-6
    assert abs(tilt_deg_euler([np.pi, 0.5, 0]) - np.degrees(0.5)) < 1e-6
