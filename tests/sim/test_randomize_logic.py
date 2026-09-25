"""Pure parts of harvest.sim.randomize (no Isaac): 5-axis random (TEST pool) / dr (TRAIN pool) sampling."""
import json
import math

import numpy as np
import pytest

from harvest.sim import randomize as R
from harvest.sim.perturb import P2_LATERAL_M
from harvest.sim.scene import OBJ_GEOM, TABLE_CENTER_XY, TABLE_SIZE, sample_layout

DEV = range(30)
EXTRA = range(3000, 3200)  # in-memory sampling only; outside every reserved split (CAL 500-549 / TEST 1000-1149 /
# TEST-P5 1300-1329 / POOL 2000-2119 / R2_TRAIN 10000-59999), checked by test_extra_seeds_avoid_every_reserved_split
POOLS = R.load_pools()


def _files(pool):
    out = set()
    for ax in ("table_materials", "floor_materials"):
        out |= {m["texture"] for m in pool[ax] if "texture" in m}
    out |= {h["file"] for h in pool["hdr_maps"]}
    out |= {d["usd"] for d in pool["distractors"] if d["kind"] == "mesh"}
    return out


def _names(pool):
    out = []
    for ax in ("table_materials", "floor_materials", "hdr_maps", "distractors", "distractor_colors"):
        out += [m["name"] for m in pool[ax]]
    return out


def _bands_overlap(a, b):
    return any(max(x[0], y[0]) < min(x[1], y[1]) for x in a for y in b)


def test_extra_seeds_avoid_every_reserved_split():
    """R7 cycle-1 N2: the in-memory sampling seeds must not touch CAL / TEST / TEST-P5 / POOL (splits.RANGES) nor
    R2_TRAIN 10000-59999 (canon §66)."""
    from harvest.eval.splits import RANGES
    reserved = [r for k, r in RANGES.items() if k != "dev"] + [range(10000, 60000)]
    assert not any(s in r for s in EXTRA for r in reserved)


# ------------------------------------------------------------------------------------------------ pools
def test_pools_have_both_splits_and_all_axes():
    assert set(POOLS["pools"]) == {"test", "train"}
    assert R.VARIANT_POOL == {"random": "test", "dr": "train"}
    for p in POOLS["pools"].values():
        for ax in ("table_materials", "floor_materials", "hdr_maps", "distractors", "distractor_colors", "light"):
            assert p[ax], ax


def test_pools_disjoint_assets_and_names():
    te, tr = POOLS["pools"]["test"], POOLS["pools"]["train"]
    assert not (_files(te) & _files(tr))
    assert not (set(_names(te)) & set(_names(tr)))
    for p in (te, tr):
        assert len(_names(p)) == len(set(_names(p)))  # unique within a pool too
    # colours of distractors / plain materials are values, not files: they must differ too
    cols = lambda p: {tuple(c["color"]) for c in p["distractor_colors"]} | {
        tuple(m["color"]) for ax in ("table_materials", "floor_materials") for m in p[ax] if "color" in m}
    assert not (cols(te) & cols(tr))


@pytest.mark.parametrize("key", ["key_mult_bands", "dome_mult_bands", "color_temperature_bands_k", "azimuth_bands_deg"])
def test_light_bands_do_not_overlap(key):
    a = POOLS["pools"]["test"]["light"][key]
    b = POOLS["pools"]["train"]["light"][key]
    assert not _bands_overlap(a, b)
    for x in a + b:
        assert x[0] < x[1]


def test_pool_files_are_isaac_bundled_paths():
    for p in POOLS["pools"].values():
        for f in _files(p):
            assert f.startswith("/isaac-sim/extscache/"), f


def test_digest_stable():
    assert R.pools_digest(POOLS) == R.pools_digest(json.loads(json.dumps(POOLS)))
    assert len(R.pools_digest(POOLS)) == 16


# ------------------------------------------------------------------------------------------------ sampling
@pytest.mark.parametrize("variant", ["random", "dr"])
def test_sampling_deterministic_per_seed(variant):
    for s in (0, 7, 29):
        assert R.sample_randomization(s, variant) == R.sample_randomization(s, variant)
    metas = [json.dumps(R.sample_randomization(s, variant), sort_keys=True) for s in DEV]
    assert len(set(metas)) == len(metas)


def test_standard_is_unrandomized():
    m = R.sample_randomization(3, "standard")
    assert m["variant"] == "standard" and m["pool"] is None
    for ax in ("table_material", "floor_material", "light", "hdr", "distractors"):
        assert m.get(ax) is None


def test_unknown_variant_refused():
    with pytest.raises(ValueError):
        R.sample_randomization(0, "test")


@pytest.mark.parametrize("variant", ["random", "dr"])
def test_sampled_values_come_from_own_pool(variant):
    pool = POOLS["pools"][R.VARIANT_POOL[variant]]
    names = set(_names(pool))
    L = pool["light"]
    within = lambda v, bands: any(a <= v <= b for a, b in bands)
    seen = {"table": set(), "floor": set(), "hdr": set(), "dist": set(), "type": set()}
    for s in list(DEV) + list(EXTRA):
        m = R.sample_randomization(s, variant)
        assert m["pool"] == R.VARIANT_POOL[variant]
        assert m["table_material"]["name"] in names and m["floor_material"]["name"] in names
        assert m["hdr"]["name"] in names
        assert within(m["hdr"]["intensity_mult"], L["dome_mult_bands"])
        lt = m["light"]
        assert lt["type"] in POOLS["common"]["light_types"]
        assert within(lt["intensity_mult"], L["key_mult_bands"])
        assert within(lt["color_temperature_k"], L["color_temperature_bands_k"])
        az = math.degrees(math.atan2(lt["pos"][1] - POOLS["common"]["light_target"][1],
                                     lt["pos"][0] - POOLS["common"]["light_target"][0]))
        assert within(round(az, 6), L["azimuth_bands_deg"]) or within(round(az - 360, 6), L["azimuth_bands_deg"]) \
            or within(round(az + 360, 6), L["azimuth_bands_deg"])
        for d in m["distractors"]:
            assert d["name"] in names
            if d.get("color") is not None:
                assert d["color"] in names
        seen["table"].add(m["table_material"]["name"])
        seen["floor"].add(m["floor_material"]["name"])
        seen["hdr"].add(m["hdr"]["name"])
        seen["type"].add(lt["type"])
        seen["dist"] |= {d["name"] for d in m["distractors"]}
    # every pool entry gets used over 230 seeds
    assert seen["table"] == {x["name"] for x in pool["table_materials"]}
    assert seen["floor"] == {x["name"] for x in pool["floor_materials"]}
    assert seen["hdr"] == {x["name"] for x in pool["hdr_maps"]}
    assert seen["dist"] == {x["name"] for x in pool["distractors"]}
    assert seen["type"] == set(POOLS["common"]["light_types"])


def test_random_and_dr_differ_for_same_seed():
    for s in DEV:
        a, b = R.sample_randomization(s, "random"), R.sample_randomization(s, "dr")
        assert a["table_material"]["name"] != b["table_material"]["name"]
        assert a["hdr"]["name"] != b["hdr"]["name"]


# ------------------------------------------------------------------------------------------------ placement
def _seg_dist(p, a, b):
    p, a, b = map(np.asarray, (p, a, b))
    u = b - a
    t = np.clip(np.dot(p - a, u) / np.dot(u, u), 0.0, 1.0)
    return float(np.linalg.norm(p - (a + t * u)))


@pytest.mark.parametrize("variant", ["random", "dr"])
def test_distractors_respect_keepout(variant):
    c = POOLS["common"]
    x0, x1 = TABLE_CENTER_XY[0] - TABLE_SIZE[0] / 2, TABLE_CENTER_XY[0] + TABLE_SIZE[0] / 2
    y0, y1 = TABLE_CENTER_XY[1] - TABLE_SIZE[1] / 2, TABLE_CENTER_XY[1] + TABLE_SIZE[1] / 2
    r10 = OBJ_GEOM["o10"]["footprint_r"]
    counts = set()
    for s in list(DEV) + list(EXTRA):
        L = sample_layout(s)
        m = R.sample_randomization(s, variant)
        ds = m["distractors"]
        counts.add(len(ds))
        assert c["n_distractors"][0] <= len(ds) <= c["n_distractors"][1], s
        mug, tray = L["o3"][:2], L["o5"][:2]
        for i, d in enumerate(ds):
            x, y = d["xy"]
            r = d["footprint_r"]
            assert 0 < d["height"] <= c["mesh_fit_max_z_m"] + 1e-9
            assert x0 + r <= x <= x1 - r and y0 + r <= y <= y1 - r  # on the table
            assert c["place_x"][0] <= x <= c["place_x"][1] and c["place_y"][0] <= y <= c["place_y"][1]
            # planner path + P2 spawn band (perturb geometry): mug->tray segment, lateral P2_LATERAL_M[1] + o10
            assert _seg_dist((x, y), mug, tray) >= P2_LATERAL_M[1] + r10 + r + c["keepout_margin_m"] - 1e-9, s
            for k, p in L.items():  # mug, tray and the standard distractors o8/o9
                assert math.dist((x, y), p[:2]) >= OBJ_GEOM[k]["footprint_r"] + r + c["object_clearance_m"] - 1e-9
            for e in ds[:i]:
                assert math.dist((x, y), e["xy"]) >= e["footprint_r"] + r + c["distractor_clearance_m"] - 1e-9
    assert counts == {1, 2, 3}


def test_mesh_fit_dims():
    c = POOLS["common"]
    for p in POOLS["pools"].values():
        for d in p["distractors"]:
            g = R.distractor_geom(d, POOLS)
            assert max(g["dims"][0], g["dims"][1]) <= c["mesh_fit_max_xy_m"] + 1e-9
            assert g["dims"][2] <= c["mesh_fit_max_z_m"] + 1e-9
            assert g["footprint_r"] == pytest.approx(math.hypot(g["dims"][0], g["dims"][1]) / 2) \
                if d["kind"] in ("mesh", "cuboid") else g["footprint_r"] == pytest.approx(d["radius"])
            assert g["half_height"] == pytest.approx(g["dims"][2] / 2)


# ------------------------------------------------------------------------------------------------ metadata
@pytest.mark.parametrize("variant", ["standard", "random", "dr"])
def test_metadata_schema(variant):
    m = R.sample_randomization(5, variant)
    json.dumps(m)  # serializable
    assert R.validate_meta(m) == []
    assert m["schema"] == R.META_SCHEMA and m["seed"] == 5 and m["variant"] == variant
    assert m["pools_digest"] == (R.pools_digest(POOLS) if variant != "standard" else None)
    if variant != "standard":
        assert set(m) >= {"table_material", "floor_material", "light", "hdr", "distractors"}
        assert set(m["light"]) >= {"type", "intensity", "intensity_mult", "color_temperature_k", "pos",
                                   "elevation_deg", "azimuth_deg", "distance_m"}
        assert set(m["hdr"]) >= {"name", "file", "intensity", "intensity_mult", "rotation_deg"}
        for d in m["distractors"]:
            assert set(d) >= {"name", "kind", "xy", "yaw", "footprint_r", "height", "half_height", "color"}


def test_validate_meta_flags_problems():
    m = R.sample_randomization(5, "random")
    bad = dict(m)
    del bad["hdr"]
    assert R.validate_meta(bad)
    bad = dict(m, variant="dr")  # pool/variant mismatch
    assert R.validate_meta(bad)


def test_training_refuses_random_variant():
    R.check_train_variant("standard")
    R.check_train_variant("dr")
    with pytest.raises(ValueError):
        R.check_train_variant("random")


# ------------------------------------------------------------------------------------------------ light pose
def test_look_at_quat_points_minus_z_at_target():
    for pos in ((1.5, 0.3, 2.0), (0.2, -1.0, 1.4), (0.5, -0.1, 3.0)):
        q = R.look_at_quat(pos, (0.5, -0.1, 0.85))
        w, x, y, z = q
        assert abs(w * w + x * x + y * y + z * z - 1) < 1e-9
        v = np.array([0.0, 0.0, -1.0])
        qv = np.array([x, y, z])
        rot = v + 2 * np.cross(qv, np.cross(qv, v) + w * v)
        d = np.array((0.5, -0.1, 0.85)) - np.array(pos)
        assert np.allclose(rot, d / np.linalg.norm(d), atol=1e-9)
