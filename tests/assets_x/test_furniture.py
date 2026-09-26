"""L8X-assets: parametric furniture kinds, sample_scene and reach / view placement regions (pure)."""
import json

import numpy as np
import pytest

from harvest.sim.assets_x import furniture as FU
from harvest.sim.assets_x import reach as RE

SEEDS = range(40)


@pytest.mark.parametrize("kind", FU.KINDS)
def test_every_kind_samples_valid_scenes(kind):
    for seed in SEEDS:
        sc = FU.sample_scene(kind, seed)
        json.dumps(sc)
        assert sc["kind"] == kind and sc["surfaces"], (kind, seed)
        assert FU.check_keep_out(FU.all_parts(sc)) == []
        for p in FU.all_parts(sc):
            assert min(p["size"]) > 0 and p["static"] and p["prim"] == "cuboid"
            assert p["pos"][2] - p["size"][2] / 2 >= -1e-4  # nothing below the floor (4-digit rounding)
        for s in sc["surfaces"]:
            (x0, x1), (y0, y1) = s["xy_box"]
            assert x1 - x0 >= 0.08 - 1e-9 and y1 - y0 >= 0.08 - 1e-9
            assert s["kind"] in {"table", "counter", "counter_covered", "shelf_tier", "shelf_top", "low_table",
                                 "bin_floor", "stand"}


def test_same_seed_same_scene_and_kinds_differ():
    assert FU.sample_scene("counter", 3) == FU.sample_scene("counter", 3)
    assert FU.sample_scene("counter", 3) != FU.sample_scene("counter", 4)


def _tops(sc, kind):
    return [s["top_z"] for s in sc["surfaces"] if s["kind"] == kind]


def test_heights_in_their_bands():
    for seed in SEEDS:
        assert all(0.72 <= z <= 0.98 for z in _tops(FU.sample_scene("table", seed), "table"))
        assert all(0.86 <= z <= 0.96 for z in _tops(FU.sample_scene("counter", seed), "counter"))
        assert all(0.40 <= z <= 0.62 for z in _tops(FU.sample_scene("low_table", seed), "low_table"))
        sl = FU.sample_scene("shelf_low", seed)
        assert len(_tops(sl, "shelf_top")) >= 1 and all(0.78 <= z <= 0.95 for z in _tops(sl, "shelf_top"))
        assert all(s["covered_above"] is not None for s in sl["surfaces"] if s["kind"] == "shelf_tier")


def test_bin_is_container_and_stand_is_higher_than_its_table():
    for seed in SEEDS:
        b = FU.sample_scene("bin", seed)
        fl = [s for s in b["surfaces"] if s["kind"] == "bin_floor"]
        assert len(fl) == 1 and fl[0]["container"] and fl[0]["rim_z"] > fl[0]["top_z"] + 0.04
        (x0, x1), (y0, y1) = fl[0]["xy_box"]
        assert min(x1 - x0, y1 - y0) >= 0.12 - 0.011  # open fingers fit (diversity plan: inner >= 12 cm)
        st = FU.sample_scene("stand", seed)
        t, s = max(_tops(st, "table")), _tops(st, "stand")
        assert len(s) == 1 and 0.05 - 1e-6 <= s[0] - t <= 0.12 + 1e-6


def test_counter_cabinet_has_open_front_and_covered_back():
    for seed in SEEDS:
        sc = FU.sample_scene("counter_cabinet", seed)
        op, cv = _tops(sc, "counter"), _tops(sc, "counter_covered")
        assert op and cv
        front = max(s["xy_box"][0][1] for s in sc["surfaces"] if s["kind"] == "counter")
        back = min(s["xy_box"][0][0] for s in sc["surfaces"] if s["kind"] == "counter_covered")
        assert front <= back + 1e-6


def fake_probe(z_ok=(0.74, 1.20)):
    xs = [round(0.30 + 0.02 * i, 2) for i in range(17)]
    ys = [-0.40, -0.23, -0.06]
    zs = [round(1.20 - 0.02 * i, 2) for i in range(30)]  # 1.20 .. 0.62
    err = np.full((3, len(xs), len(zs)), 50.0)
    for j, x in enumerate(xs):
        for k, z in enumerate(zs):
            if x <= 0.52 and z_ok[0] <= z <= z_ok[1]:
                err[:, j, k] = 2.0
    # a camera looking down the +x axis from above: sees x in ~[0.3, 0.7]
    R = np.array([[0, -1, 0], [-np.sin(np.pi / 4), 0, -np.cos(np.pi / 4)],
                  [np.cos(np.pi / 4), 0, -np.sin(np.pi / 4)]]).T  # columns = optical x, y, z in world
    cam = {"fx": 300.0, "fy": 300.0, "cx": 336.0, "cy": 188.0, "W": 672, "H": 376, "R": R.tolist(),
           "t": [0.05, 0.0, 1.45]}
    return {"xs": xs, "ys": ys, "zs": zs, "err_mm": err.tolist(), "head_cam": cam, "lift_cmd": None}


def test_reach_model_brackets_and_bands():
    rm = RE.ReachModel(fake_probe())
    assert rm.reach_ok(0.40, -0.20, 0.92, 1.09)
    assert not rm.reach_ok(0.56, -0.20, 0.92, 1.09)  # beyond the reachable x
    assert not rm.reach_ok(0.40, 0.05, 0.92, 1.09)  # outside the probed y band: unknown = no
    assert not rm.reach_ok(0.40, -0.20, 0.60, 0.80)  # below the probed z: no extrapolation


def test_placement_regions_reach_view_and_cover():
    rm = RE.ReachModel(fake_probe())
    sc = FU.sample_scene("table", 0, reach=rm)
    pr = sc["placement_regions"]
    assert len(pr) == len(sc["surfaces"])
    top = sc["surfaces"][0]["top_z"]
    if top + 0.24 <= 1.20:
        r = next(p for p in pr if p["region"] is not None)
        (x0, x1), (y0, y1) = r["region"]
        assert x1 <= 0.52 + 0.011 and y0 >= -0.40 - 1e-9 and y1 <= -0.06 + 1e-9
    lo = FU.sample_scene("low_table", 1, reach=rm, lift=None)  # the default lift can not reach 0.42-0.62
    assert all(p["region"] is None and p["reason"] == "reach" for p in lo["placement_regions"])
    sh = FU.sample_scene("shelf_tall", 2, reach=rm, lift=None)
    cov = [p for p, s in zip(sh["placement_regions"], sh["surfaces"]) if s["kind"] == "shelf_tier"]
    assert cov and all(p["reason"] == "covered" for p in cov)


def test_mesh_kind_places_a_licensed_piece_facing_the_robot():
    tbl = {"Desk_1": {"category": "table", "top_kind": "table", "dst": "/x/Desk_1_static.usda",
                      "collider_size": [1.2, 0.6, 0.76], "origin_offset": [0, 0, 0], "split": "train",
                      "license": "CC BY 4.0", "source": "t",
                      "surfaces": [{"top_z": 0.76, "free_box": [[-0.6, 0.6], [-0.3, 0.3]], "area": 0.72,
                                    "covered_above": None, "clearance": None, "rim_z": None, "container": False}]}}
    assert FU.mesh_kinds(tbl) == ("thor_table",)
    sc = FU.sample_scene("thor_table", 5, mesh_assets=tbl)
    p = sc["furniture"][0]
    assert p["usd"] == "/x/Desk_1_static.usda" and p["license"] == "CC BY 4.0"
    assert p["size"][0] == pytest.approx(0.6) and p["size"][1] == pytest.approx(1.2)  # yaw -90: long side along y
    (x0, x1), (y0, y1) = sc["surfaces"][0]["xy_box"]
    assert x0 == pytest.approx(p["pos"][0] - 0.3, abs=1e-3) and y1 - y0 == pytest.approx(1.2, abs=1e-3)
    assert sc["surfaces"][0]["top_z"] == pytest.approx(0.76) and FU.check_keep_out(FU.all_parts(sc)) == []
    with pytest.raises(ValueError):
        FU.sample_scene("thor_table", 5, mesh_assets=tbl, split="ood")


def test_lift_shifts_reach_and_camera_and_auto_lift_reaches_low_tables():
    rm = RE.ReachModel(fake_probe())
    lo = rm.at_lift(-0.4993)
    assert lo.zs.min() == pytest.approx(rm.zs.min() - 0.4, abs=1e-9)
    assert lo.cam["t"][2] == pytest.approx(rm.cam["t"][2] - 0.4, abs=1e-9)
    assert lo.reach_ok(0.40, -0.20, 0.52, 0.69) and not rm.reach_ok(0.40, -0.20, 0.52, 0.69)
    with pytest.raises(ValueError):
        rm.at_lift(0.1)
    for seed in range(5):
        sc = FU.sample_scene("low_table", seed, reach=rm)
        assert sc["lift"] < RE.LIFT_DEFAULT and any(p["region"] for p in sc["placement_regions"])
        assert RE.LIFT_LIMITS[0] <= sc["lift"] <= RE.LIFT_LIMITS[1]
    t = FU.sample_scene("table", 1, reach=rm)
    if any(p["region"] for p in FU.sample_scene("table", 1, reach=rm, lift=None)["placement_regions"]):
        assert t["lift"] == RE.LIFT_DEFAULT  # ties keep the default lift


def test_kind_split_holds_out_two_kinds_never_the_table():
    assert len(FU.OOD_S_KINDS) == 2 and "table" not in FU.OOD_S_KINDS
    assert FU.sample_scene(FU.OOD_S_KINDS[0], 0)["kind_split"] == "ood"
    assert FU.sample_scene("table", 0)["kind_split"] == "train"


def test_repo_assets_table_is_licensed_and_samples():
    import os
    p = os.path.join(os.path.dirname(FU.__file__), "assets_table.json")
    tbl = json.load(open(p))
    assert "behavior_1k_assets" in tbl["inventory"]["excluded"]
    assets = tbl["assets"]
    assert len(assets) >= 200 and all(a["license"] == "CC BY 4.0" for a in assets.values())
    ood = sum(a["split"] == "ood" for a in assets.values()) / len(assets)
    assert 0.1 < ood < 0.3
    for kind in FU.mesh_kinds(assets):
        for seed in range(3):
            sc = FU.sample_scene(kind, seed, mesh_assets=assets)
            assert FU.check_keep_out(FU.all_parts(sc)) == [] and sc["furniture"][0]["usd"].endswith("_static.usda")
