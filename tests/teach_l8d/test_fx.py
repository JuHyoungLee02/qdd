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
    assert fx.ws_from_region([[0.36, 0.56], [-0.40, -0.32]]) == ((0.36, 0.56), (-0.40, -0.32))  # bin kind strip
    with pytest.raises(fx.SkipScene):
        fx.ws_from_region([[0.36, 0.48], [-0.39, -0.31]])  # diagonal 0.144 < 0.20


def test_two_surfaces_and_virtual_surface_contacts():
    from harvest.sim import tasks as T
    sc = _scene([{"surface": "s0", "region": [[0.40, 0.52], [-0.40, -0.06]]},
                 {"surface": "s1", "region": [[0.42, 0.50], [-0.28, -0.20]]}])
    a, ra, b, rb = fx.choose_two_surfaces(sc)
    assert a["id"] == "s0" and b["id"] == "s1" and b["top_z"] > a["top_z"]
    with pytest.raises(fx.SkipScene):
        fx.choose_two_surfaces(_scene([{"surface": "s0", "region": [[0.40, 0.52], [-0.40, -0.06]]}]))
    # table frame: surface o19 top 0.08 above the table, box 8 x 8 cm around (0.46, -0.24)
    pos = {"o19": [0.46, -0.24, 0.079], "o3": [0.47, -0.25, 0.08 + 0.0475], "o8": [0.40, -0.10, 0.05]}
    bottom = {"o19": 0.078, "o3": 0.0801, "o8": 0.0}
    c = T.surface_contacts(pos, bottom, "o19", (0.04, 0.04))
    assert c == {frozenset({"o3", "o19"})}
    bottom["o3"] = 0.09
    assert not T.surface_contacts(pos, bottom, "o19", (0.04, 0.04))


def test_mesh_kind_subsets():
    import os

    from harvest.sim.assets_x import furniture as FU
    d = os.path.join(os.path.dirname(fx.__file__), "..", "sim", "assets_x")
    m = fx.load_mesh_assets(d)
    kinds = FU.mesh_kinds(m)
    assert "cyclo_basket" in kinds and "cyclo_work_table" in kinds and any(k.startswith("thor_") for k in kinds)
    assert fx.is_mesh_kind("cyclo_basket") and fx.is_mesh_kind("thor_table") and not fx.is_mesh_kind("low_table")
    sub = fx.mesh_subset(m, "cyclo_basket", "train")
    assert sub and all(a["category"] == "basket" for a in sub.values())
    for seed in range(35060, 35070):  # pure scene sampling with the subset only
        sc = FU.sample_scene("cyclo_basket", seed, mesh_assets=sub)
        assert any(s.get("container") for s in sc["surfaces"])
        sc2 = FU.sample_scene("cyclo_work_table", seed, mesh_assets=fx.mesh_subset(m, "cyclo_work_table", "train"))
        assert sc2["surfaces"]


def test_choose_container():
    box = {"id": "s2", "kind": "bin_floor", "top_z": 0.87, "container": True,
           "xy_box": [[0.45, 0.58], [-0.20, -0.07]]}
    sc = _scene([{"surface": "s0", "region": [[0.40, 0.52], [-0.40, -0.06]]},
                 {"surface": "s2", "region": [[0.47, 0.56], [-0.18, -0.09]]}])
    sc["surfaces"].append(box)
    a, ra, b, rb = fx.choose_container(sc)
    assert a["id"] == "s0" and b["id"] == "s2"
    with pytest.raises(fx.SkipScene):
        fx.choose_container(_scene([{"surface": "s0", "region": [[0.40, 0.52], [-0.40, -0.06]]}]))


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
