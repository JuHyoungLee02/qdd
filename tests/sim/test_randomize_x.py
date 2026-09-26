"""L8-D wider randomization (docs/stage3/prereg_l8d.md): variants 'drx' (TRAIN_X pool, training) and 'randx' (TEST_X
pool, OOD-D evaluation only) from their own pool file, so the original pools (and their digest, and every 'random' /
'dr' sample) stay byte-identical."""
import json

import numpy as np
import pytest

from harvest.sim import randomize as R
from harvest.sim.scene import sample_layout

BASE = R.load_pools()
X = R.load_pools(R.POOLS_X_PATH)
BASE_DIGEST = "see test_base_pools_unchanged"


def _names(pool):
    out = []
    for ax in ("table_materials", "floor_materials", "hdr_maps", "distractors", "distractor_colors"):
        out += [m["name"] for m in pool[ax]]
    return out


def _files(pool):
    out = set()
    for ax in ("table_materials", "floor_materials"):
        out |= {m["texture"] for m in pool[ax] if m.get("texture")}
    out |= {h["file"] for h in pool["hdr_maps"]}
    out |= {d["usd"] for d in pool["distractors"] if d["kind"] == "mesh"}
    return out


def _cols(p):
    return {tuple(c["color"]) for c in p["distractor_colors"]} | {
        tuple(m["color"]) for ax in ("table_materials", "floor_materials") for m in p[ax] if "color" in m}


def _overlap(a, b):
    return any(max(x[0], y[0]) < min(x[1], y[1]) for x in a for y in b)


def test_variants_and_pools():
    assert R.VARIANT_POOL == {"random": "test", "dr": "train"}  # unchanged
    assert R.X_VARIANT_POOL == {"drx": "train_x", "randx": "test_x"}
    assert set(X["pools"]) == {"train_x", "test_x"}
    assert R.pool_name("drx") == "train_x" and R.pool_name("dr") == "train" and R.pool_name("standard") is None
    for v in ("drx", "randx"):
        R.check_variant(v)
    R.check_train_variant("drx")
    with pytest.raises(ValueError):
        R.check_train_variant("randx")


def test_train_x_is_disjoint_from_every_test_pool():
    trx, tex = X["pools"]["train_x"], X["pools"]["test_x"]
    te = BASE["pools"]["test"]
    for a in (trx,):
        for b in (te, tex):
            assert not (_files(a) & _files(b))
            assert not (set(_names(a)) & set(_names(b)))
            assert not (_cols(a) & _cols(b))
            for key in ("key_mult_bands", "dome_mult_bands", "color_temperature_bands_k", "azimuth_bands_deg"):
                assert not _overlap(a["light"][key], b["light"][key]), key
    for p in (trx, tex):
        assert len(_names(p)) == len(set(_names(p)))


def test_train_x_is_wider_than_train():
    tr, trx = BASE["pools"]["train"], X["pools"]["train_x"]
    for ax in ("table_materials", "floor_materials", "distractor_colors"):
        assert set(m["name"] for m in tr[ax]) < set(m["name"] for m in trx[ax]), ax
        assert len(trx[ax]) >= len(tr[ax]) + 4, ax
    assert [d["name"] for d in trx["distractors"]] == [d["name"] for d in tr["distractors"]]
    for key in ("key_mult_bands", "color_temperature_bands_k"):
        lo = min(b[0] for b in trx["light"][key])
        hi = max(b[1] for b in trx["light"][key])
        assert lo < min(b[0] for b in tr["light"][key]) and hi > max(b[1] for b in tr["light"][key])
    assert trx["n_distractors"] == [0, 6]
    assert X["pools"]["test_x"]["n_distractors"][1] >= 3


def test_base_pools_and_samples_unchanged():
    """The original file is not touched: dr / random sampling (incl. pools_digest) is what it was."""
    m = R.sample_randomization(5, "dr")
    assert m["pools_digest"] == R.pools_digest(BASE)
    assert m["pool"] == "train"
    n = [len(R.sample_randomization(s, "dr")["distractors"]) for s in range(30)]
    assert min(n) >= 1 and max(n) <= 3  # common n_distractors [1, 3]


def test_drx_sampling_uses_x_pool_and_counts_0_to_6():
    trx = X["pools"]["train_x"]
    seen = []
    for s in range(30000, 30200):
        m = R.sample_randomization(s, "drx")
        assert m["pool"] == "train_x" and m["variant"] == "drx"
        assert m["pools_digest"] == R.pools_digest(X)
        assert m["table_material"]["name"] in {t["name"] for t in trx["table_materials"]}
        assert not R.validate_meta(m)
        seen.append(len(m["distractors"]) + len(m.get("distractors_dropped", [])))
    assert min(seen) == 0 and max(seen) == 6
    assert R.sample_randomization(30001, "drx") == R.sample_randomization(30001, "drx")


def test_randx_is_test_assets_only():
    te = BASE["pools"]["test"]
    names = {d["name"] for d in te["distractors"]}
    for s in range(70300, 70330):
        m = R.sample_randomization(s, "randx")
        assert m["pool"] == "test_x"
        assert {d["name"] for d in m["distractors"]} <= names


def test_distractor_spawn_z_follows_the_table():
    d = {"half_height": 0.03}
    assert R.distractor_spawn_z(d, 0.85) == pytest.approx(0.85 + 0.031)
    assert R.distractor_spawn_z(d, 0.92) == pytest.approx(0.92 + 0.031)


def test_drx_keepout_with_workspace_layout():
    lay = sample_layout(30007)
    m = R.sample_randomization(30007, "drx", lay)
    for d in m["distractors"]:
        assert R.placement_ok(d["xy"], d["footprint_r"], lay, [e for e in m["distractors"] if e is not d],
                              X["common"])
