"""Articulated put-in tasks A / C: pure layout / predicates (harvest.teach_l8d.xart)."""
import numpy as np

from harvest.teach_l8d import xart as XA

DRAWER = {"surfaces": [
    {"top_z": 0.996, "free_box": [[-1.08, -0.67], [-0.41, -0.30]], "area": 0.045, "covered_above": None,
     "container": True, "rim_z": 1.064},
    {"top_z": 0.996, "free_box": [[0.09, 0.50], [-0.25, -0.09]], "area": 0.066, "covered_above": 1.076,
     "container": True, "rim_z": 1.107},
    {"top_z": 1.107, "free_box": [[-1.29, 1.29], [-0.30, 0.49]], "area": 2.038, "covered_above": None,
     "container": False, "rim_z": None}]}
BOX = {"collider_size": [0.45, 0.55, 0.25],
       "surfaces": [{"top_z": 0.009, "free_box": [[-0.12, 0.11], [-0.14, 0.14]], "area": 0.064,
                     "covered_above": None, "container": True, "rim_z": 0.189}]}
OBJ = {"footprint_r": 0.03, "height": 0.085}


def test_drawer_layout_puts_the_exposed_inside_at_the_target_and_the_object_on_the_top():
    ts = XA.target_surface(DRAWER, "A")
    assert ts["covered_above"] is None and ts["container"]
    lay = XA.layout("A", DRAWER, OBJ, 49150)
    (x0, x1), (y0, y1) = lay["place_box"]
    assert abs((x0 + x1) / 2 - XA.TARGET_XY[0]) < 1e-6 and abs((y0 + y1) / 2 - XA.TARGET_XY[1]) <= 0.02 + 1e-6
    front = lay["pos"][0] + DRAWER["surfaces"][2]["free_box"][1][0]
    assert front + XA.TOP_BEHIND[0] - 1e-6 <= lay["obj_xy"][0] <= front + XA.TOP_BEHIND[1] + 1e-6 <= 0.65
    assert lay["obj_z"] == 1.107 and lay["floor"] == 0.996 and 0.996 <= lay["work_z"] <= 0.996 + 0.047
    assert -0.5 <= lay["lift"] <= 0.0 and XA.layout("A", DRAWER, OBJ, 49150) == lay


def test_box_layout_on_the_stand_and_the_carry_over_the_rim():
    lay = XA.layout("C", BOX, OBJ, 49151)
    assert abs(lay["floor"] - (XA.STAND_TOP + 0.009)) < 1e-6 and abs(lay["rim"] - (XA.STAND_TOP + 0.189)) < 1e-6
    assert lay["obj_z"] == XA.STAND_TOP and XA.fits(OBJ, [[0, 0.23], [0, 0.28]])
    assert not XA.fits({"footprint_r": 0.12}, [[0, 0.23], [0, 0.28]])


def test_predicates():
    lay = XA.layout("C", BOX, OBJ, 49151)
    c = np.array([*lay["place_xy"], lay["floor"] + 0.04])
    p = XA.preds(c, lay["floor"] + 0.002, 3.0, c + [0, 0, 0.3], 0.107, 0.107, lay)
    assert p["on(t,p)"] and not p["holding(t)"] and p["upright(t)"]
    p = XA.preds(c, lay["floor"] + 0.002, 3.0, c + [0, 0, 0.02], 0.05, 0.107, lay)
    assert p["holding(t)"] and not p["on(t,p)"]
    p = XA.preds(c + [0.5, 0, 0], lay["floor"], 3.0, c + [0, 0, 0.3], 0.107, 0.107, lay)
    assert not p["on(t,p)"]
    assert XA.parse(XA.task_id("A", "Dresser_219_1", "gsor_x")) == ("A", "Dresser_219_1", "gsor_x")


def test_pick_room_every_episode():
    rooms = {"FloorPlan1": {}, "FloorPlan2": {}, "FloorPlan3": {}}
    assert XA.pick_room({}, 1) is None
    picks = [XA.pick_room(rooms, s) for s in range(20)]
    assert all(p in rooms for p in picks) and picks == [XA.pick_room(rooms, s) for s in range(20)]
    assert len(set(picks)) > 1
