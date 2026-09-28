"""b4 realistic scenes (prereg_l8d change 12): variant drf = look randomization for furniture scenes (HDR dome,
key light type / colour temperature / pose from the train_x pool; no L8 table / floor slab / pool distractors), real
clutter on the work surface of a furniture scene."""
import hashlib
import json

import pytest

from harvest.sim import randomize as R
from harvest.sim.tasks import layout_for
from harvest.teach_l8d import clutter_x as CX


def test_drf_samples_light_and_hdr_only():
    lay = layout_for(36001, "mug_tray", "task")
    m = R.sample_randomization(36001, "drf", lay)
    assert m["variant"] == "drf" and m["pool"] == "train_x" and m["pools_digest"]
    assert m["table_material"] is None and m["floor_material"] is None and m["distractors"] == []
    assert m["hdr"]["file"] and m["light"]["type"] in R.LIGHT_TYPES
    assert m == R.sample_randomization(36001, "drf", lay)
    assert m["hdr"] != R.sample_randomization(36002, "drf", lay)["hdr"] or \
        m["light"] != R.sample_randomization(36002, "drf", lay)["light"]
    assert R.check_train_variant("drf") == "drf" and not R.validate_meta(m)


def test_other_variants_unchanged():
    h = hashlib.sha256()
    for v in ("dr", "drx", "random", "randx"):
        for s in (30001, 31777, 36123):
            h.update(json.dumps(R.sample_randomization(s, v, layout_for(s, "mug_tray", "task")), sort_keys=True)
                     .encode())
    assert h.hexdigest()[:16] == "50422935f3bb841f"  # snapshot before change 12


def test_clutter_on_a_furniture_surface():
    rows = CX.load_real()
    pool = CX.pool_for(rows, "drf|0.000|shelf", n=30)
    surf = {"id": "s1", "top_z": 0.91, "xy_box": [[0.30, 0.70], [-0.55, 0.15]], "covered_above": 1.05}
    ws = ((0.40, 0.52), (-0.40, -0.10))
    lay = {"o3": (0.45, -0.20, 0.0), "o5": (0.48, -0.33, 0.0)}
    fr = {"o3": 0.032, "o5": 0.114}
    for seed in range(36400, 36410):
        out, placed = CX.add_clutter(dict(lay), seed, pool, ws, fr, surface=surf)
        for p in placed:
            r = pool[p["id"]]["footprint_r"]
            assert 0.30 + r <= p["x"] <= 0.70 - r and -0.55 + r <= p["y"] <= 0.15 - r
            assert pool[p["id"]]["height"] + 0.05 <= 1.05 - 0.91 + 1e-9  # fits under the shelf above
    with pytest.raises(ValueError):
        CX.add_clutter(dict(lay), 1, pool, ws, fr, surface={"id": "x"})


def test_drf_rows_allowed_in_train():
    from harvest.teach_l8d import dataset as D
    D.check_row({"seed": 36900, "variant": "drf", "task": "mug_tray"}, "train")


def test_b4_seed_block():
    from harvest.teach_l8d import spec as S
    assert S.check_seed(40000, "train") == 40000 and S.is_train_seed(49999) and not S.is_train_seed(50000)
    assert not S.is_train_seed(39999)


def test_rich_arrangement_display_and_stack():
    from harvest.teach_l8d import xnew as XN
    rows = CX.load_real()
    pool = CX.pool_for(rows, "drf|0.000|thor_low_table", n=40, n_base=12)
    assert sum(1 for r in pool.values() if r.get("top_surface")) >= 12
    surf = {"id": "s1", "top_z": 0.46, "xy_box": [[0.30, 0.75], [-0.55, 0.20]]}
    ws = ((0.38, 0.52), (-0.40, -0.10))
    lay = {"o5": (0.48, -0.33, 0.0)}
    fr = {"o5": 0.114}
    rich = 0
    for seed in range(40000, 40040):
        out, placed = CX.add_clutter(dict(lay), seed, pool, ws, fr, surface=surf, arrange=True)
        kinds = {p.get("arr") for p in placed}
        rich += bool(kinds & {"display", "stack"})
        for p in placed:
            if p.get("arr") == "stack":
                base = out[p["id"]][3]
                assert base in out and XN.base_ok(rows[base], rows[p["id"]]) and XN.stack_top_ok(rows[p["id"]])
                assert out[p["id"]][:2] == out[base][:2]
            else:
                r = pool[p["id"]]["footprint_r"]
                assert 0.30 + r <= p["x"] <= 0.75 - r and -0.55 + r <= p["y"] <= 0.20 - r
                assert not (0.34 - r < p["x"] < 0.56 + r and -0.44 - r < p["y"] < -0.06 + r)
    assert rich >= 30  # most episodes (user-log 175)


def test_drf_lighting_range_change14():
    lay = layout_for(40001, "mug_tray", "task")
    ms = [R.sample_randomization(s, "drf", lay) for s in range(40000, 40200)]
    ex = [m["lighting"]["exposure"] for m in ms]
    assert min(ex) >= R.DRF_EXPOSURE[0] - 1e-9 and max(ex) <= R.DRF_EXPOSURE[1] + 1e-9 and max(ex) - min(ex) > 0.4
    n = [1 + len(m["lighting"]["fills"]) for m in ms]
    assert set(n) == {1, 2, 3}
    assert 0.05 < sum(any(f["tinted"] for f in m["lighting"]["fills"]) or m["lighting"]["key_tint"] is not None for m in ms) / 200 < 0.5
    for m in ms:
        assert R.DRF_SOFT[0] - 1e-9 <= m["lighting"]["key_radius_scale"] <= R.DRF_SOFT[1] + 1e-9
        for f in m["lighting"]["fills"]:
            assert 0 < f["intensity"] <= m["light"]["intensity"] + 1e-6 and len(f["pos"]) == 3 and len(f["color"]) == 3
        assert not R.validate_meta(m)
    assert R.sample_randomization(40000, "drf", lay) == ms[0]


def test_exposure_frame_stats():
    import importlib.util
    import numpy as np
    sp = importlib.util.spec_from_file_location("exposure", "tools/teach_l8d/exposure.py")
    E = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(E)
    white = np.full((10, 10, 3), 255)
    dark = np.full((10, 10, 3), 20)
    mid = np.full((10, 10, 3), 128)
    assert E.frame_stats(white)["over"] and not E.frame_stats(white)["dark"]
    assert E.frame_stats(dark)["dark"] and not E.frame_stats(mid)["over"] and not E.frame_stats(mid)["dark"]


def test_basket_task_change14():
    from harvest.sim import objv as OV
    from harvest.sim import tasks as T
    k = sorted(k for k, r in CX.load_real().items() if r["split"] == "train" and r.get("task_target_ok"))[0]
    OV.register_for_tasks([f"ov_basket__{k}"])
    s = T.TASKS[f"ov_basket__{k}"]
    assert s.target == k and s.place == "o20" and "basket" in s.instruction


def test_relational_real_tasks_change15():
    from harvest.sim import objv as OV
    from harvest.sim import tasks as T
    k = sorted(k for k, r in CX.load_real().items() if r["split"] == "train" and r.get("task_target_ok"))[3]
    OV.register_for_tasks([f"ov_left__{k}"])
    t = f"ov_left__{k}"
    assert T.TASKS[t].place == "o17" and T.X_REL[t] == ("o8", "o17", 0.10)
    for seed in range(40000, 40010):
        lay = T.x_task_layout(seed, t, ws=((0.37, 0.52), (-0.40, -0.06)))
        assert {k, "o8", "o17"} <= set(lay) and abs(lay["o17"][1] - lay["o8"][1] - 0.10) < 1e-9


def test_confusers_change16():
    rows = CX.load_real()
    tgt = next(k for k, r in sorted(rows.items()) if r["split"] == "train" and r.get("task_target_ok") and CX.confuser_ids(rows, k))
    cids = CX.confuser_ids(rows, tgt)
    assert all(rows[c]["colour"] == rows[tgt]["colour"] for c in cids)
    pool = {k: rows[k] for k in cids + [tgt]}
    lay = {tgt: (0.45, -0.20, 0.0), "o5": (0.45, -0.38, 0.0)}
    hits = 0
    for seed in range(40000, 40200):
        out, ids = CX.add_confusers(dict(lay), seed, tgt, "o5", pool, {tgt: rows[tgt]["footprint_r"], "o5": 0.114}, [[0.30, 0.70], [-0.55, 0.15]])
        hits += bool(ids)
        import math
        for k in ids:
            assert rows[k]["footprint_r"] + rows[tgt]["footprint_r"] + 0.02 - 1e-9 <= math.dist(out[k][:2], lay[tgt][:2]) <= 0.08 + max(0.08, rows[k]["footprint_r"] + rows[tgt]["footprint_r"] + 0.02) + 1e-9
    assert 0.1 <= hits / 200 <= 0.3


def test_front_behind_between_change18():
    import math
    from harvest.sim import objv as OV
    from harvest.sim import tasks as T
    k = sorted(k for k, r in CX.load_real().items() if r["split"] == "train" and r.get("task_target_ok"))[5]
    OV.register_for_tasks([f"ov_front__{k}", f"ov_behind__{k}", f"ov_between__{k}"])
    ws = ((0.37, 0.55), (-0.42, -0.04))
    for seed in range(40000, 40010):
        f = T.x_task_layout(seed, f"ov_front__{k}", ws=ws)
        assert abs(f["o27"][0] - f["o8"][0] + 0.10) < 1e-9 and ws[0][0] <= f["o27"][0] <= ws[0][1]
        b = T.x_task_layout(seed, f"ov_behind__{k}", ws=ws)
        assert abs(b["o28"][0] - b["o8"][0] - 0.10) < 1e-9
        w = T.x_task_layout(seed, f"ov_between__{k}", ws=ws)
        mid = ((w["o8"][0] + w["o9"][0]) / 2, (w["o8"][1] + w["o9"][1]) / 2)
        assert math.dist(mid, w["o29"][:2]) < 1e-9 and 0.20 - 1e-9 <= math.dist(w["o8"][:2], w["o9"][:2]) <= 0.26 + 1e-9
        assert math.dist(w[k][:2], w["o29"][:2]) >= 0.12 - 1e-9


def test_unique_names_change18():
    rows = CX.load_real()
    pool = CX.pool_for(rows, "drf|0.000|thor_table", n=60, n_base=12)
    banned = CX.name_of(next(iter(pool.values())))
    surf = {"id": "s1", "top_z": 0.46, "xy_box": [[0.30, 0.75], [-0.55, 0.20]]}
    for seed in range(40000, 40020):
        out, placed = CX.add_clutter({"o5": (0.48, -0.33, 0.0)}, seed, pool, ((0.38, 0.52), (-0.40, -0.10)), {"o5": 0.114}, surface=surf, arrange=True, taken_names={banned})
        names = [CX.name_of(pool[p["id"]]) for p in placed]
        assert banned not in names and len(names) == len(set(names))


def test_head_pose_change17():
    hs = [CX.head_pose(s) for s in range(40000, 42000)]
    r = [h for h in hs if h["random"]]
    assert 0.12 <= len(r) / len(hs) <= 0.18
    assert all(h["tilt"] == 0.785 and h["pan"] == 0.0 for h in hs if not h["random"])
    assert all(abs(h["pan"]) <= CX.HEAD_PAN_MAX and abs(h["tilt"] - 0.785) <= CX.HEAD_TILT_MAX for h in r)
