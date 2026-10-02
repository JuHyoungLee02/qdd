"""L9 v2 environment families (spec §12.3): >= 14 families (8 v1 + new), v1 scenes unchanged, ground slab, props."""
import hashlib
import json
import os

import pytest

from harvest.l9 import reach9 as R9
from harvest.l9 import scene9 as S

V1 = ("shelf_front", "dining", "living_low", "kitchen", "entrance", "office", "store", "workbench")
NEW_ROLES = ("ground", "prop", "fixture")


@pytest.fixture(scope="module")
def rm():
    return R9.load_default()


def test_family_count_and_v1_codes():
    assert len(S.FAMILIES) >= 22 and all(len(r) >= 5 for _, r in S.FAMILIES.values())
    assert len(S.all_rules()) >= 110
    assert S.FAMILY_NAMES[:8] == V1  # v1 seeds (FAMILY_CODE) unchanged
    assert all(S.FAMILY_CODE[f] == i + 1 for i, f in enumerate(V1))


def test_room_kinds_cover_every_family():
    assert set(S.ROOM_KINDS) == set(S.FAMILIES)
    for f in S.OUTDOOR:
        assert f in S.FAMILIES and S.ROOM_KINDS[f] == ()


def _gold_lift(sc, rm):
    """The lift the v1 parts / nodes alone give (= the v1 sampler's lift)."""
    sc2 = dict(sc, parts_s=[p for p in sc["parts_s"] if p["role"] not in NEW_ROLES],
               nodes=[n for n in sc["nodes"] if not n.get("fixture")])
    return round(float(S.choose_lift(sc2, rm)[0]), 4)


def test_v1_scenes_unchanged(rm):
    gold = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "scene9_v1_golden.json")))
    for key, h in gold.items():
        f, r, arm = key.split("/")
        sc = S.sample(f, r, 11, arm, rm)
        furn = [{k: v for k, v in p.items() if k != "mat_hint"} for p in sc["furniture"] if p["role"] not in NEW_ROLES]
        nodes = [{k: v for k, v in n.items() if k not in NEW_NODE_KEYS + ("group",)} for n in sc["nodes"] if not n.get("fixture")]
        k = json.dumps([furn, nodes, _gold_lift(sc, rm), sc["robot_pose"]], sort_keys=True)
        assert hashlib.sha256(k.encode()).hexdigest()[:16] == h, key


def test_ground_slab_and_props(rm):
    dens, ground = set(), 0
    for i, (f, r) in enumerate(S.all_rules()):
        sc = S.sample(f, r, 40 + i, "right" if i % 2 else "left", rm)
        assert sc["params"]["density"] in S.DENSITY
        dens.add(sc["params"]["density"])
        g = [p for p in sc["furniture"] if p["role"] == "ground"]
        assert len(g) <= 1
        if g:
            ground += 1
            assert g[0]["pos"][2] + g[0]["size"][2] / 2 <= 0.0
        assert len(sc["parts_s"]) <= S.N_SLOTS
        props = [p for p in sc["parts_s"] if p["role"] == "prop"]
        assert len(props) <= S.DENSITY[sc["params"]["density"]][1]
    assert dens == set(S.DENSITY) and ground >= 0.9 * len(S.all_rules())


def test_new_family_heights(rm):
    for f in S.FAMILY_NAMES[8:]:
        for r in S.FAMILIES[f][1]:
            sc = S.sample(f, r, 3, "right", rm)
            for n in S.usable_nodes(sc):
                assert 0.38 <= n["top_z"] <= 1.10, (f, r, n)


NEW_NODE_KEYS = ("width", "depth", "clear_above", "approach", "place_class")


def test_fixture_places_and_annotations(rm):
    kinds, classes, approach = set(), set(), set()
    for i, (f, r) in enumerate(S.all_rules()):
        for arm in ("right", "left"):
            sc = S.sample(f, r, 900 + i, arm, rm)
            assert set(sc["params"]["fixtures"]) <= set(S.FIXTURES)
            for n in sc["nodes"]:
                assert all(k in n for k in NEW_NODE_KEYS), n
                assert n["approach"] in ("top", "front") and n["clear_above"] > 0
                classes.add(n["place_class"])
                approach.add(n["approach"])
                if n.get("fixture"):
                    kinds.add(n["kind"])
                if n["kind"] == "compartment":
                    assert n["approach"] == "front"
                    assert not n.get("fixture") or (n["place_class"] == "high" and len(n["opening"]) == 2)
                if n["kind"] == "shelf_low":
                    assert n["approach"] == "front" and n["place_class"] == "low"
                if n["kind"] == "slope":
                    assert 8 <= n["tilt_deg"] <= 20
            for p in sc["parts_s"]:
                if "pitch" in p:
                    assert p["role"] == "fixture" and abs(p["pitch"]) < 0.4
    assert {"shelf_high", "compartment", "shelf_low", "gap", "slope"} <= kinds
    assert classes == {"low", "desk", "high"} and approach == {"top", "front"}


def test_heldout_family_split():
    tr, ho = S.all_rules("train"), S.all_rules("heldout")
    assert ho and not {f for f, _ in tr} & set(S.HELDOUT_FAMILIES) and {f for f, _ in ho} == set(S.HELDOUT_FAMILIES)
    assert len(tr) + len(ho) == len(S.all_rules())


def test_high_share_env_lever(rm, monkeypatch):
    """L9_HIGH_SHARE (owner 10-03: place_height band "high" was 0.42 % of rendered steps) raises how often a scene
    offers a HIGH_FIXTURES node, off by default (unset env -> high_share() == 0, same draw as before: the first
    `rng.random()` branch below is untouched), without collapsing to a single shelf type."""
    monkeypatch.delenv("L9_HIGH_SHARE", raising=False)
    assert S.high_share() == 0.0
    f, r = "shelf_front", "stepped2"

    def frac(n=150, seed0=50000):
        hi, kinds = 0, set()
        for i in range(n):
            sc = S.sample(f, r, seed0 + i, "right", rm)
            got = set(sc["params"]["fixtures"]) & set(S.HIGH_FIXTURES)
            if got:
                hi += 1
                kinds |= got
        return hi / n, kinds

    base, _ = frac()
    monkeypatch.setenv("L9_HIGH_SHARE", "0.9")
    assert S.high_share() == pytest.approx(0.9)
    boosted, kinds = frac()
    assert boosted > base + 0.4  # well above the un-boosted draw
    assert kinds == set(S.HIGH_FIXTURES)  # both shelf types still appear (diversity, no collapse to one kind)


def test_material_hints(rm):
    seen = set()
    for f in ("kitchen", "lab_bench", "laundry", "warehouse_rack", "office"):
        for r in S.FAMILIES[f][1]:
            sc = S.sample(f, r, 5, "right", rm)
            for p in sc["parts_s"]:
                if p["role"] == "prop":
                    assert p["mat_hint"] == "paper"
                seen.add(p.get("mat_hint"))
    assert {"metal", "stone", "plastic", "wood", "paper"} <= seen
