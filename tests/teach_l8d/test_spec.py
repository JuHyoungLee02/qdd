"""L8-D spec (docs/stage3/prereg_l8d.md): seeds, heights, plan, OOD guards, gate G-H arithmetic. Pure."""
import numpy as np
import pytest

from harvest.teach_l8d import spec as S


def test_seed_ranges_are_disjoint_and_guarded():
    assert S.TRAIN_SEEDS == range(30000, 35000) and S.GATE_SEEDS == range(35000, 35200)
    assert S.OOD_SEEDS == range(70000, 71000)
    assert S.OOD_SETS["ood_h"] == range(70000, 70100) and S.OOD_SETS["ood_o"] == range(70100, 70300)
    assert S.OOD_SETS["ood_d"] == range(70300, 70500)
    S.check_seed(30001, "train")
    S.check_seed(35001, "gate")
    with pytest.raises(ValueError):
        S.check_seed(20100, "train")  # L8's range
    with pytest.raises(ValueError):
        S.check_seed(5, "train")  # DEV
    with pytest.raises(ValueError):
        S.check_seed(70001, "ood_h")  # needs confirm_ood
    assert S.check_seed(70001, "ood_h", confirm_ood=True) == 70001
    with pytest.raises(ValueError):
        S.check_seed(70301, "ood_h", confirm_ood=True)  # wrong OOD set
    with pytest.raises(ValueError):
        S.check_seed(70001, "train", confirm_ood=True)


def test_train_heights_keep_away_from_every_ood_height():
    tr, outer = S.heights_from_gate(0.76, 0.96)
    ood = S.PT_OOD_H + outer
    assert outer == (0.76, 0.96)
    assert 0.85 in tr
    for h in tr:
        assert all(abs(h - o) >= S.OOD_GAP - 1e-9 for o in ood), h
        assert 0.76 < h < 0.96
    assert tr == tuple(sorted(tr)) and len(tr) >= 6


def test_heights_from_gate_narrow_range():
    tr, outer = S.heights_from_gate(0.80, 0.90)
    assert outer == (0.80, 0.90)
    assert all(0.80 < h < 0.90 for h in tr)


def test_task_and_variant_mix():
    tasks = [S.task_of(s) for s in S.TRAIN_SEEDS[:3000]]
    fr = {t: tasks.count(t) / len(tasks) for t in S.PHASE1_TASKS}
    assert set(tasks) == set(S.PHASE1_TASKS)
    assert abs(fr["mug_tray"] - 0.4) < 0.03 and abs(fr["bottle_tray"] - 0.3) < 0.03
    vs = [S.variant_of(s) for s in S.TRAIN_SEEDS[:3000]]
    assert abs(vs.count("drx") / 3000 - 2 / 3) < 0.03 and set(vs) == {"standard", "drx"}


def test_plan_is_deterministic_and_balanced():
    heights = (0.80, 0.84, 0.85, 0.86, 0.90)
    p = S.plan_train(1200, heights)
    assert p == S.plan_train(1200, heights)
    assert len(p) == 1200 and len({e["seed"] for e in p}) == 1200
    assert all(e["seed"] in S.TRAIN_SEEDS for e in p)
    by_h = {h: sum(e["table_z"] == h for e in p) for h in heights}
    assert max(by_h.values()) - min(by_h.values()) <= 0.25 * 1200 / len(heights)
    b = S.buckets(p)
    assert sum(len(v) for v in b.values()) == 1200
    for (v, h), eps in b.items():
        assert all(e["variant"] == v and e["table_z"] == h for e in eps)


def test_x_plan_and_held_out_tasks():
    from harvest.sim.tasks import X_TASKS
    heights = (0.80, 0.85, 0.90)
    p = S.plan_x(700, heights)
    assert p == S.plan_x(700, heights) and all(e["objset"] == "x" for e in p)
    assert {e["task"] for e in p} == set(S.X_TRAIN_TASKS)
    assert p[0]["seed"] == S.X_TRAIN_START and p[-1]["seed"] < S.TRAIN_SEEDS.stop
    held = set(S.OOD_O_TASKS + S.OOD_T_TASKS)
    assert not held & set(S.X_TRAIN_TASKS) and held <= set(X_TASKS)
    assert set(S.X_TRAIN_TASKS) | held | set(S.X_MULTI_TASKS) == set(X_TASKS)
    # the unseen object o14 is not in any trained task (target, place or extras)
    for t in S.X_TRAIN_TASKS + S.PHASE1_TASKS:
        s = X_TASKS.get(t)
        if s:
            assert "o14" not in (s.target, s.place) + tuple(s.extras)
    rs = list(S.OOD_SETS.values())
    assert all(a.stop <= b.start for a, b in zip(rs, rs[1:])) and rs[-1].stop <= S.OOD_SEEDS.stop


def test_view_band_matches_the_head_camera():
    lo, hi = S.view_band(0.85)
    assert 0.35 <= lo <= 0.37 and hi >= 0.60
    lo2, _ = S.view_band(0.95)
    lo3, _ = S.view_band(0.74)
    assert lo2 > lo and lo3 > lo  # both directions shrink the view band's near edge


def test_live_camera_dict_projects_like_the_constants():
    from harvest.train.r2_ma2 import HEAD_K, HEAD_POS, HEAD_R
    fwd, left, up = HEAD_R[:, 0], HEAD_R[:, 1], HEAD_R[:, 2]
    cam = {"fx": HEAD_K["fx"], "fy": HEAD_K["fy"], "cx": HEAD_K["cx"], "cy": HEAD_K["cy"], "W": 672, "H": 376,
           "R": np.stack([-left, -up, fwd], 1).tolist(), "t": HEAD_POS.tolist()}
    P = [[0.42, -0.2, 0.85], [0.5, -0.35, 0.95]]
    assert np.allclose(S.project(P, cam), S.project(P), atol=1e-6)
    assert S.view_band(0.88, cam) == S.view_band(0.88)


def test_gate_verdict():
    reach = {"xs": [0.40, 0.42, 0.44, 0.46, 0.48, 0.50], "ok": {"0.850": [True] * 5 + [False]}}
    g = S.gate_h(0.85, (0.36, 0.80), (0.36, 0.48), n_clean=10, n_success=9)
    assert g["pass"] and g["ws_x"] == (0.36, 0.48) and g["width"] == pytest.approx(0.12)
    g = S.gate_h(0.95, (0.435, 0.80), (0.36, 0.52), n_clean=10, n_success=9)
    assert g["pass"] and g["ws_x"] == (0.435, 0.52)
    g = S.gate_h(0.95, (0.435, 0.80), (0.36, 0.50), n_clean=10, n_success=9)
    assert not g["pass"] and g["reason"] == "width"  # 6.5 cm
    g = S.gate_h(0.74, (0.41, 0.80), (0.36, 0.46), n_clean=10, n_success=10)
    assert not g["pass"] and g["reason"] == "width"
    g = S.gate_h(0.85, (0.36, 0.80), (0.36, 0.48), n_clean=10, n_success=7)
    assert not g["pass"] and g["reason"] == "truth"
    assert reach  # shape documented in gate json


def test_reach_band_from_columns():
    xs = [0.40, 0.42, 0.44, 0.46, 0.48, 0.50]
    zs = [0.80, 0.85, 0.90]
    err = np.zeros((3, len(xs), len(zs)))  # (y, x, z) mm
    err[:, 5, 0] = 20.0  # x 0.50 unreachable at z 0.80
    lo, hi = S.reach_band(xs, zs, err, z_need=(0.80, 0.90))
    assert (lo, hi) == (0.40, 0.48)
    lo, hi = S.reach_band(xs, zs, err, z_need=(0.85, 0.90))
    assert (lo, hi) == (0.40, 0.50)


def test_median3_drops_single_step_transients_only():
    e = np.array([1, 1, 200, 1, 1, 30, 40, 1], float)
    m = S.median3(e)
    assert m[2] == 1 and m[5] >= 30 and m[6] >= 30
    zs = [0.80, 0.82, 0.84, 0.86, 0.88, 0.90, 0.92, 0.94]
    err = np.ones((1, 2, 8))
    err[0, 0] = e
    assert S.reach_band([0.40, 0.42], zs, err, z_need=(0.80, 0.86)) == (0.40, 0.42)
    assert S.reach_band([0.40, 0.42], zs, err, z_need=(0.80, 0.92)) == (0.42, 0.42)
