"""L8-X furniture in the generator (pure): surface choice, layout filter, plan selection per process."""
import pytest

from harvest.teach_l8d import fx
from harvest.teach_l8d.run_collect import select_plan, vdir

SURF = {"id": "s0", "kind": "counter", "top_z": 0.91, "xy_box": [[0.30, 0.70], [-0.50, 0.10]]}
SURF2 = {"id": "s1", "kind": "stand", "top_z": 0.99, "xy_box": [[0.40, 0.52], [-0.30, -0.18]]}


def _scene(regions):
    return {"kind": "counter", "seed": 3, "lift": -0.0993, "surfaces": [SURF, SURF2], "furniture": [], "walls": [],
            "placement_regions": regions}


def test_choose_the_largest_usable_region():
    sc = _scene([{"surface": "s0", "region": [[0.40, 0.52], [-0.40, -0.06]]},
                 {"surface": "s1", "region": [[0.42, 0.50], [-0.28, -0.20]]}])
    s, r = fx.choose_surface(sc)
    assert s["id"] == "s0" and r == [[0.40, 0.52], [-0.40, -0.06]]
    assert fx.ws_from_region(r) == ((0.40, 0.52), (-0.40, -0.06))
    with pytest.raises(fx.SkipScene):
        fx.choose_surface(_scene([{"surface": "s0", "region": None}]))
    with pytest.raises(fx.SkipScene):
        fx.ws_from_region([[0.40, 0.45], [-0.40, -0.06]])  # narrower than 8 cm


def test_filter_layout_drops_off_surface_extras_and_keeps_task_objects():
    lay = {"o3": (0.45, -0.2, 0.0), "o5": (0.50, -0.35, 0.0), "o8": (0.72, -0.1, 0.0), "o9": (0.5, 0.0, 0.3)}
    out, dropped = fx.filter_layout(lay, SURF, keep={"o3", "o5"})
    assert set(out) == {"o3", "o5", "o9"} and dropped == ["o8"]
    with pytest.raises(fx.SkipScene):
        fx.filter_layout({"o3": (0.69, -0.2, 0.0), "o5": (0.5, -0.3, 0.0)}, SURF, keep={"o3", "o5"})


def test_select_plan_by_objset_lift_and_furniture():
    plan = [{"seed": 1, "split": "train", "variant": "standard", "table_z": 0.48, "lift": -0.4693, "task": "mug_tray"},
            {"seed": 2, "split": "train", "variant": "standard", "table_z": 0.48, "lift": -0.4693, "task": "mug_bin",
             "objset": "x"},
            {"seed": 3, "split": "train", "variant": "standard", "table_z": 0.85, "task": "mug_tray"},
            {"seed": 4, "split": "train", "variant": "standard", "table_z": 0.0, "furniture": "counter",
             "task": "mug_tray"}]
    assert [e["seed"] for e in select_plan(plan, "standard", 0.48, "train", None, -0.4693)] == [1]
    assert [e["seed"] for e in select_plan(plan, "standard", 0.48, "train", "x", -0.4693)] == [2]
    assert [e["seed"] for e in select_plan(plan, "standard", 0.85, "train")] == [3]
    assert [e["seed"] for e in select_plan(plan, "standard", 0.0, "train", furniture="counter")] == [4]
    assert vdir("standard", 0.0, None, "counter") == "standard_fx_counter"
    assert vdir("standard", 0.48, -0.4693) == "standard_tz0.480_lift-0.469"
