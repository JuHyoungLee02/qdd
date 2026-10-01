"""L9 v2 task layer: v1 unchanged (golden), >= 200 sourced definitions in >= 15 families, robot gripper width as a
parameter, step info (scene constraint, place pose / approach / height, done predicates, recovery), instructed
approach rows (~20 %), allocation over 4 robots, plan v2 rows and the task diversity tool."""
import json
import os
from collections import Counter

import numpy as np
import pytest

from harvest.l9 import alloc9 as AL
from harvest.l9 import assets9 as A9
from harvest.l9 import reach9 as R9
from harvest.l9 import scene9 as S9
from harvest.l9 import task9 as T9
from harvest.l9 import task9v2 as V2

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "task9_v1_golden.json")


@pytest.fixture(scope="module")
def rm():
    return R9.load_default()


def _js(x):
    return json.loads(json.dumps(x, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))


# ------------------------------------------------------------------------------------------------ v1 unchanged
def test_v1_registry_unchanged():
    c = T9.definition_count()
    assert len(T9.DEFS) == 108 and len(c) == 9
    assert all(T9.get_def(k) is T9.DEFS[k] for k in T9.DEFS)


def test_v1_golden_instantiate_unchanged(rm):
    cases = json.load(open(FIX))
    assert len(cases) >= 12
    for c in cases:
        pool = A9.pool_for(c["pool"])
        ep = T9.instantiate(T9.DEFS[c["def"]], c["scene"], pool, c["seed"], rm, tries=8)
        assert ep is not None, c["def"]
        T9.add_clutter(ep, c["scene"], pool, c["seed"], rm)
        assert _js(ep) == c["ep"], c["def"]


# ------------------------------------------------------------------------------------------------ registry
def test_v2_registry_size_families_sources():
    D = V2.DEFS_V2
    fam = Counter(d.family for d in D.values())
    assert len(D) >= 200, len(D)
    assert len(fam) >= 15 and all(v >= 6 for v in fam.values()), fam
    assert set(T9.DEFS) <= set(D) and len(V2.NEW) == len(D) - len(T9.DEFS)
    for k, d in D.items():
        assert len(d.templates) >= 5, k
        assert T9.dep_order(d.objs)
        for a, dst in d.steps:
            assert a in d.objs and (dst in d.objs or dst in d.dst), (k, dst)
        src = V2.SOURCES[k]
        assert src and all(s[0] in V2.SOURCE_REFS for s in src), k
        for cap in d.extra.get("requires", ()):
            assert cap in V2.CAPS_ALL, (k, cap)
    for k in V2.NEW:
        assert k not in T9.DEFS and V2.SOURCES[k][0][0] != "v1"
        assert T9.get_def(k) is D[k]  # collect9.draw looks definitions up through task9.get_def


def test_new_families_and_low_share_families():
    fam = Counter(d.family for d in V2.NEW.values())
    for f in ("shelf", "select", "tall", "hollow", "pose", "kitchen", "tidy", "transfer", "recovery"):
        assert fam[f] >= 6, (f, fam)
    multi = [d for d in V2.DEFS_V2.values() if len(d.steps) >= 2]
    assert len(multi) >= 60


def test_l8s_coverage_table():
    # owner 10-02 03h: the next training uses L9 v2 only -> every L8S task kind maps to L9 v2 definitions
    from harvest.sim import tasks as TS
    kinds = set(TS.OBJV_TASK_KINDS) | {"marker", "stand", "stand_then_place", "confuser_attribute", "multi_step",
                                        "open_container", "stack", "push", "ring_peg", "open_drawer_box"}
    assert kinds <= set(V2.L8S_COVERAGE), kinds - set(V2.L8S_COVERAGE)
    for kind, ids in V2.L8S_COVERAGE.items():
        assert ids and all(k in V2.DEFS_V2 for k in ids), kind
    assert any(V2.runnable(V2.DEFS_V2[k]) for k in V2.L8S_COVERAGE["left"])
    push = [d for d in V2.NEW.values() if d.family == "push"]
    assert len(push) >= 4 and all("exec:push" in d.extra["requires"] for d in push)


def test_recovery_candidate_every_definition_share():
    picks = [V2.recovery_candidate(s, "rel_left", 2) for s in range(4000)]
    share = sum(p is not None for p in picks) / len(picks)
    assert 0.12 <= share <= 0.18
    p = next(x for x in picks if x)
    assert p["step"] in (0, 1) and p["kind"] in ("off_target", "tilted") and p["teach"] is False


def test_templates_fill_without_missing_keys():
    for k, d in V2.DEFS_V2.items():
        keys = set(d.objs) | set(d.dst)
        ok = keys | {n + s for n in keys for s in ("col", "noun", "surf", "side")} | {"Msurf"}
        for t in d.templates:
            import string
            for _, f, _, _ in string.Formatter().parse(t):
                assert f is None or f in ok, (k, t, f)


# ------------------------------------------------------------------------------------------------ gripper width
def test_grip_max_of_robots():
    assert V2.grip_max_of("ffw_sg2") == pytest.approx(0.107)
    assert V2.grip_max_of("franka_mast") == pytest.approx(0.08) == V2.grip_max_of("franka")
    for r in ("r1pro", "g1"):
        assert 0.04 <= V2.grip_max_of(r) <= 0.12


def test_fits_and_finger_clear_take_grip_max():
    cont = {"inside": {"place_kind": "into", "opening_min_side": 0.11, "rim_z": 0.08, "inner_floor_z": 0.01}}
    obj = {"footprint_r": 0.03, "height": 0.09}
    assert T9.fits_into(obj, cont) == T9.fits_into(obj, cont, 0.107)
    d = np.array([0.10, 0.0])
    assert not T9.finger_clear(d, 0.03) and T9.finger_clear(d, 0.03, 0.06)


def test_instantiate_respects_grip_max(rm):
    d = V2.DEFS_V2["rel_left"]
    got = 0
    for s in range(30):
        sc = S9.sample("workbench", "crates", 500 + s, ("right", "left")[s % 2], rm)
        pool = A9.pool_for(s)
        ep = T9.instantiate(d, sc, pool, 500 + s, rm, tries=10, grip_max=0.08, v2=True)
        if ep is None:
            continue
        got += 1
        a = ep["steps"][0][0]
        assert float(pool[a].get("grasp_width") or 0) <= 0.08 - T9.GRIP_MARGIN + 1e-9
    assert got >= 5


# ------------------------------------------------------------------------------------------------ step info
def test_v2_step_info_done_and_constraints(rm):
    seen = 0
    for name in ("rel_left", "sel_colour_in", "tr_out_of_basket", "tidy_pack_lunch", "rcv_rel_left_off"):
        d = V2.DEFS_V2[name]
        for s in range(40):
            f, r = (("workbench", "crates"), ("dining", "seats2"), ("store", "crate_table"))[s % 3]
            try:
                sc = S9.sample(f, r, 900 + s, ("right", "left")[s % 2], rm)
            except RuntimeError:
                continue
            ep = T9.instantiate(d, sc, A9.pool_for(s), 900 + s, rm, tries=10, v2=True)
            if ep is None:
                continue
            seen += 1
            si = ep["step_info"]
            assert len(si) == len(ep["steps"])
            for i, x in enumerate(si):
                assert x["constraint"] in V2.CONSTRAINTS + (None,)
                assert x["place_pose"]["kind"] in V2.PLACE_POSES
                assert x["place_approach"] in ("top", "front", "side")
                assert x["place_height"]["band"] in V2.HEIGHT_BANDS
                assert x["done"]["pred"] in V2.DONE_PREDS and x["done"]["text"]
            assert ep["done"]["all_of"] and ep["done"]["text"]
            m = ep["instr_meta"]
            assert m["base"] and ep["instruction"] == m["wrapped"] and m["approach"] is None
            assert m["approach_candidate"] in (None,) + V2.APPROACHES
            before = ep["instruction"]
            V2.apply_approach(ep, "side")
            assert ep["instruction"] != before and m["wrapped"] in ep["instruction"] and "side" in ep["instruction"]
            assert m["approach"] == "side" and m["approach_reason"] == "instructed"
            if name.startswith("rcv_"):
                assert any(x.get("recovery") for x in si)
            break
    assert seen >= 4


def test_constraint_rules():
    tall = {"height": 0.20, "footprint_r": 0.03, "l9cat": "bottle"}
    bowl = {"height": 0.08, "footprint_r": 0.11, "l9cat": "bowl", "grasp_width": 0.16, "role9": "container"}
    mug = {"height": 0.10, "footprint_r": 0.08, "l9cat": "mug", "grasp_width": 0.08, "handle_ratio": 2.2,
           "role9": "container"}
    box = {"height": 0.085, "footprint_r": 0.05, "l9cat": "box", "grasp_width": 0.05}
    shelf = {"kind": "shelf", "top_z": 1.2}
    top = {"kind": "top", "top_z": 0.8}
    assert V2.constraints_of(tall, top, 0.107)[0] == "tall"
    assert V2.constraints_of(bowl, top, 0.107)[0] == "wide_hollow"
    assert V2.constraints_of(mug, top, 0.107)[0] == "handle"  # fits the AI Worker: the handle decides
    assert V2.constraints_of(mug, top, 0.08)[0] == "wide_hollow"  # wider than Franka - 2 cm: rim grasp
    assert V2.constraints_of(box, shelf, 0.107)[0] == "blocked_above"
    assert V2.constraints_of(box, top, 0.107) == []
    assert V2.height_band(0.40) == "low" and V2.height_band(1.45) == "above_eye"


def test_benchmark_instructions_never_verbatim():
    assert V2.bench_clash("Put the bowl on the plate.") and V2.bench_clash("put  the BOWL on the plate")
    assert not V2.bench_clash("Put the red bowl on the plate.")
    d = V2.DEFS_V2["hol_bowl_on_plate"]
    fmt = {"A": "bowl", "H": "plate", "Msurf": "table"}
    ep = {"instruction": "Put the bowl on the plate.", "template": 0}
    text, clash = V2.avoid_bench(d, ep, fmt)
    assert clash and not V2.bench_clash(text) and ep["template"] != 0 and "bowl" in text


def test_instructed_approach_share_and_text():
    picks = [V2.instructed_approach(s, "rel_left", None) for s in range(4000)]
    share = sum(p is not None for p in picks) / len(picks)
    assert 0.17 <= share <= 0.23
    assert set(p for p in picks if p) == {"top", "oblique", "front", "side"}
    bl = [V2.instructed_approach(s, "shelf_take_out", "blocked_above") for s in range(2000)]
    assert "top" not in set(bl)
    assert V2.instructed_approach(7, "x", None) == V2.instructed_approach(7, "x", None)
    for a, ts in V2.APPROACH_TEXT.items():
        assert len(ts) >= 4 and all("{X}" in t for t in ts)


def test_collect_draw_passes_robot_width_and_v2(rm):
    from harvest.l9 import collect9 as C9
    row = {"seed": 910003, "arm": "right", "family": "workbench", "rule": "crates", "def": "sel_colour_in",
           "robot": "franka_mast", "grip_max": 0.08, "v2": True}
    sc, ep, *_ = C9.draw(row, A9.pool_for(4), rm, None)
    assert ep["task_v2"] and len(ep["step_info"]) == len(ep["steps"])
    pool = A9.pool_for(4)
    for a, _, _ in ep["steps"]:
        assert float(pool[a].get("grasp_width") or 0) <= 0.08 - T9.GRIP_MARGIN + 1e-9


# ------------------------------------------------------------------------------------------------ allocation
def test_allocation_totals_and_floors():
    defs = {k: d.family for k, d in V2.DEFS_V2.items() if not d.extra.get("requires")}
    al = AL.allocate(defs, total=15000, min_per_def=60)
    tot = sum(sum(v.values()) for v in al.values())
    assert tot == 15000
    per_def = {k: sum(v.values()) for k, v in al.items()}
    assert min(per_def.values()) >= 60
    rob = Counter()
    for v in al.values():
        rob.update(v)
    assert abs(rob["ffw_sg2"] - 6000) <= 2 and all(abs(rob[r] - 3000) <= 2 for r in ("franka_mast", "r1pro", "g1"))
    for r in AL.ROBOT_SHARE:  # every robot covers every family
        fams = {defs[k] for k, v in al.items() if v.get(r, 0) > 0}
        assert fams == set(defs.values())
    mean = lambda f: np.mean([per_def[k] for k in per_def if defs[k] == f and len(V2.DEFS_V2[k].steps) == 1])  # noqa: E731
    # owner 10-02 03h: relation / put_in no longer reduced (L9 v2 alone replaces L8S); new families still more
    assert abs(mean("relation") - mean("arrange")) <= 2 and mean("put_in") < mean("select")
    assert AL.allocate(defs, total=15000, min_per_def=60) == al  # deterministic


def test_allocation_exclusion_moves_to_other_robots():
    defs = {"a": "select", "b": "relation", "c": "tidy"}
    al = AL.allocate(defs, total=600, min_per_def=60, exclude={("franka_mast", "a")})
    assert al["a"].get("franka_mast", 0) == 0 and sum(al["a"].values()) >= 60
    assert sum(sum(v.values()) for v in al.values()) == 600


def test_holdout_definitions():
    defs = {k: d.family for k, d in V2.DEFS_V2.items() if not d.extra.get("requires")}
    ho = AL.holdout_defs(defs)
    assert ho == AL.holdout_defs(defs) and 0.03 * len(defs) <= len(ho) <= 0.06 * len(defs)
    assert len({defs[k] for k in ho}) == len(ho)  # one per family at most
    al = AL.allocate(defs, total=15000, min_per_def=60, holdout=ho)
    assert all(sum(al[k].values()) == 60 for k in ho) and sum(sum(v.values()) for v in al.values()) == 15000
    pairs = {k: [("workbench", "crates")] for k in al}
    rows = AL.plan_rows({k: al[k] for k in ho[:1] + ["rel_left"]}, pairs, holdout=ho)
    assert {r["split"] for r in rows if r["def"] == ho[0]} == {"holdout"}
    assert {r["split"] for r in rows if r["def"] == "rel_left"} == {"train"}


def test_plan_rows_v2():
    defs = {k: V2.DEFS_V2[k] for k in ("rel_left", "sel_colour_in", "tidy_pack_lunch")}
    pairs = {k: [("workbench", "crates"), ("dining", "seats2")] for k in defs}
    al = AL.allocate({k: d.family for k, d in defs.items()}, total=300, min_per_def=60)
    rows = AL.plan_rows(al, pairs, start=3000000, yields={"rel_left": 0.8})
    assert len({r["seed"] for r in rows}) == len(rows)
    by = Counter((r["def"], r["robot"]) for r in rows)
    assert by[("rel_left", "ffw_sg2")] == int(np.ceil(al["rel_left"]["ffw_sg2"] / 0.8))
    assert by[("tidy_pack_lunch", "g1")] == int(np.ceil(al["tidy_pack_lunch"]["g1"] / AL.DEFAULT_YIELD))
    for r in rows:
        assert r["v2"] and r["grip_max"] == pytest.approx(V2.grip_max_of(r["robot"]))
        assert r["arm"] in AL.ROBOT_ARMS[r["robot"]]
    assert {r["arm"] for r in rows if r["robot"] == "franka_mast"} == {"right"}
    ffw = [r["arm"] for r in rows if r["robot"] == "ffw_sg2"]
    assert ffw.count("right") >= 0.5 * len(ffw) and ffw.count("left") > 0  # L8S workhorse: right >= half
    ch = AL.jobs_v2(rows, 10)
    for c in ch:
        assert len({(r["robot"], r["arm"]) for r in c}) == 1


# ------------------------------------------------------------------------------------------------ diversity tool
def test_task_diversity_on_plan(tmp_path):
    import importlib.util
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tools", "l9",
                     "task_diversity.py")
    spec = importlib.util.spec_from_file_location("task_diversity", p)
    TD = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(TD)
    defs = {k: d.family for k, d in V2.DEFS_V2.items() if not d.extra.get("requires")}
    al = AL.allocate(defs, total=15000, min_per_def=60)
    rep = TD.from_alloc(al)
    assert rep["n_defs"] == len(defs) and rep["n_families"] == len(set(defs.values()))
    assert rep["episodes"]["total"] == 15000 and rep["episodes"]["per_def_min"] >= 60
    assert rep["template_capacity"] > 5 * len(defs)
    for k in ("place_pose_planned", "approach_planned", "height_planned", "post_grasp_steps", "n_steps",
              "robot_family_cover"):
        assert rep[k], k
    metas = [{"task_id": "rel_left", "task_family": "relation", "instruction": "Put the a left of the b.",
              "robot": "ffw_sg2", "n_steps": 1,
              "step_info": [{"place_pose": {"kind": "upright"}, "place_approach": "top", "constraint": None,
                             "place_height": {"band": "mid"}, "recovery": None}],
              "instr_meta": {"approach": None}},
             {"task_id": "rel_left", "task_family": "relation", "instruction": "Put the c left of the b.",
              "robot": "g1", "n_steps": 1, "step_info": None, "instr_meta": None}]
    for i, m in enumerate(metas):
        d = tmp_path / f"e{i}"
        d.mkdir()
        (d / "meta.json").write_text(json.dumps(dict(m, success=True)))
    rep2 = TD.from_metas(str(tmp_path))
    assert rep2["unique_instructions"] == 2 and rep2["n_defs"] == 1
