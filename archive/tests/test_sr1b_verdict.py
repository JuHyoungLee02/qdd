"""E-SR1b (prereg_sr1b): verdict rule (adoption A_xy >= 0.8 with bootstrap lower bound > chance + 0.1 and the
non-inferiority conditions), pooling over seeds with the sr0 metric functions, decision accuracy, input checks."""
import importlib.util
import json
import os

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("sr1b_verdict", os.path.join(ROOT, "tools", "sr1b", "sr1b_verdict.py"))
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)
E0 = V.E0

LAB = {"dir_xy": "plus_x", "dir_z": "none_z", "mag_coarse": "small", "target": "o3", "phase": "reach"}


def snap(i, follow: bool, preds=None, mse_pred=0.02):
    c = {}
    for n in E0.cond_names(True):
        d = [0.01, 0.0, 0.0]
        if n.startswith("xy:") and follow and n != "xy:none_xy":
            u = E0.unit_xy(n[3:])
            d = [0.01 * u[0], 0.01 * u[1], 0.0]
        if n == "z:up":
            d = [0.01, 0.0, 0.002]
        if n == "z:down":
            d = [0.01, 0.0, -0.002]
        if n.startswith("mag:"):
            d = [0.002 * (1 + E0.MAGS.index(n[4:])), 0.0, 0.0]
        grip = 0.8 if n == "pid:open" else 0.2
        c[n] = d + [0.5, grip, mse_pred if n == "pred" else 0.02]
    p = preds or {q: LAB[q] for q in LAB}
    return {"event": "snap", "i": i, "id": f"v/t/P0/ep{i}/k3", "key": f"P0_ep{i}_k3", "arm": "right", "labels": LAB,
            "preds": p, "targets": {q: [LAB[q]] for q in LAB}, "disp_gt": [0.01, 0.0, 0.0], "c": c, "w": 1.0,
            "near": i % 2 == 1, "dist_m": 0.03 if i % 2 else 0.2, "grip_gt": [0.9, 0.9]}


def write(path, snaps):
    with open(path, "w") as f:
        for s in snaps:
            f.write(json.dumps(s) + "\n")
        f.write(json.dumps({"event": "summary", "n": len(snaps)}) + "\n")
    return str(path)


def base_cell(**kw):
    c = {"a_xy": 0.8, "chance_xy": 0.35, "lb": 0.45 + 1e-9, "dec_acc": 0.94, "mse_pred": 0.021,
         "p_xy": 0.8, "p_chance": 0.2, "p_lb": 0.3 + 1e-9, "grip_acc": 0.9}
    c.update(kw)
    return c


BASE = {"dec_acc": 0.95, "mse_pred": 0.02, "grip_acc": 0.9}


def test_checks_boundaries():
    r = V.checks(base_cell(dec_acc=0.94), BASE, w=1.0, lat_ratio=None)  # dec diff -0.01 exactly, mse +5 % exactly
    assert r["all"] and r["target"] and r["lb"] and r["dec"] and r["mse"] and r["lat"]
    assert not V.checks(base_cell(a_xy=0.8 - 1e-9), BASE, 1.0, None)["all"]
    assert not V.checks(base_cell(lb=0.45), BASE, 1.0, None)["lb"]  # strictly greater than chance + 0.1
    assert not V.checks(base_cell(dec_acc=0.9399), BASE, 1.0, None)["dec"]
    assert not V.checks(base_cell(mse_pred=0.02101), BASE, 1.0, None)["mse"]


def test_checks_plausible_metric_uses_its_own_keys():
    assert V.checks(base_cell(a_xy=0.1, lb=0.0), BASE, 1.0, None, metric="p_xy")["all"]
    assert not V.checks(base_cell(p_xy=0.79), BASE, 1.0, None, metric="p_xy")["target"]
    assert not V.checks(base_cell(p_lb=0.3), BASE, 1.0, None, metric="p_xy")["lb"]
    with pytest.raises(ValueError):
        V.checks(base_cell(), BASE, 1.0, None, metric="x")


def test_checks_latency_only_for_cfg():
    assert V.checks(base_cell(), BASE, 1.0, 0.5)["lat"]  # w = 1: no extra expert pass, latency not required
    assert V.checks(base_cell(), BASE, 2.0, 0.10)["lat"]
    assert not V.checks(base_cell(), BASE, 2.0, 0.1001)["lat"]
    with pytest.raises(ValueError):
        V.checks(base_cell(), BASE, 2.0, None)


def _c(v, ok, ni=True):
    return {"a_xy": v, "p_xy": v, "checks": {"a_xy": {"all": ok, "ni": ni}, "p_xy": {"all": ok, "ni": ni}}}


def test_choose_prefers_highest_value_then_smaller_w():
    cells = {("A", 1.0): _c(0.5, False), ("A", 2.0): _c(0.85, True), ("A", 3.0): _c(0.85, True),
             ("B", 1.0): _c(0.82, True), ("A02", 1.0): _c(0.99, True)}
    for m in ("a_xy", "p_xy"):
        r = V.choose(cells, m)
        assert r["verdict"] == "ADOPT" and r["adopt"] == ["A", 2.0]  # A02 is outside the rule


def test_choose_without_a_pass_reports_the_best_non_inferior_cell():
    cells = {("A", 1.0): _c(0.5, False), ("A", 8.0): _c(0.9, False, ni=False), ("B", 1.0): _c(0.6, False)}
    r = V.choose(cells, "a_xy")
    assert r["verdict"] == "NOT_REACHED" and r["adopt"] is None and r["best"] == ["B", 1.0]
    r2 = V.choose({("A", 8.0): _c(0.9, False, ni=False)}, "a_xy")
    assert r2["best"] == ["A", 8.0] and r2["best_is_non_inferior"] is False


def _plaus_snap(mode):
    """disp_gt along plus_x (reference r = plus_x); neighbours plus_x_plus_y / plus_x_minus_y."""
    s = snap(0, True)
    for d in E0.DIR_XY9:
        if mode == "follow" and d != "none_xy":
            u = E0.unit_xy(d)
            s["c"][f"xy:{d}"][:3] = [0.01 * u[0], 0.01 * u[1], 0.0]
        elif mode == "ignore":
            s["c"][f"xy:{d}"][:3] = [0.01, 0.0, 0.0]
        elif mode == "nudge":  # 1 mm toward the edit, still nearer the reference
            u = E0.unit_xy(d) if d != "none_xy" else np.zeros(2)
            s["c"][f"xy:{d}"][:3] = [0.01 + 0.001 * (u[0] - 1) / 0.765, 0.001 * u[1] / 0.765, 0.0]
    return s


def test_plausible_edit_stats():
    f = V.plaus_stats(_plaus_snap("follow"))
    assert f["p_pairs"] == 2 and f["p_hits"] == 2 and f["p_chance"] == pytest.approx(1.0)
    assert f["p_shift_hits"] == 2 and f["p_shift_mm"] > 0 and f["p_abs"] == 2
    ig = V.plaus_stats(_plaus_snap("ignore"))
    assert ig["p_hits"] == 0 and ig["p_chance"] == 0 and ig["p_shift_hits"] == 0 and ig["p_abs"] == 2
    nu = V.plaus_stats(_plaus_snap("nudge"))
    assert nu["p_hits"] == 0 and nu["p_shift_hits"] == 2 and nu["p_shift_mm"] == pytest.approx(2.0, abs=0.05)
    s = _plaus_snap("follow")
    s["disp_gt"] = [0.0015, 0.0, 0.0]  # recorded chunk below XY_MIN_M: no reference direction
    assert V.plaus_stats(s)["p_pairs"] == 0


def test_dec_counts():
    s1 = snap(0, True)
    s2 = snap(1, True, preds={**{q: LAB[q] for q in LAB}, "dir_xy": "minus_x"})
    assert V.dec_counts([s1, s2]) == (9, 10)


def test_cell_pools_seeds_with_the_sr0_metric(tmp_path):
    n = 4
    f1 = write(tmp_path / "s0.jsonl", [snap(i, True) for i in range(n)])
    f2 = write(tmp_path / "s1.jsonl", [snap(i, False) for i in range(n)])
    c = V.cell([f1, f2], n, boot=200)
    s = [E0_stats(x) for x in (True, False)]
    assert c["a_xy"] == pytest.approx((s[0] + s[1]) / 2)
    assert c["a_xy"] == pytest.approx(0.5 * (1.0 + 2 / 7))  # following: 7/7; constant +x: only plus_x_* hit 2 of 7
    assert c["n_seeds"] == 2 and c["dec_acc"] == 1.0 and c["mse_pred"] == pytest.approx(0.02)
    assert c["lb"] <= c["a_xy"] <= c["ub"]
    assert c["p_pairs"] == 2 * 2 * n and c["p_xy"] == pytest.approx(0.5)  # follow: all hits; constant +x: none
    assert c["p_lb"] <= c["p_xy"] <= c["p_ub"]
    assert set(c["per_seed"]) == {"0", "1"} and c["per_seed"]["0"]["p_xy"] == 1.0


def E0_stats(follow):
    st = V.V0.snap_stats(snap(0, follow), True)
    return st["xy_hits"] / st["xy_pairs"]


def test_cell_input_checks(tmp_path):
    f1 = write(tmp_path / "s0.jsonl", [snap(i, True) for i in range(3)])
    f2 = write(tmp_path / "s1.jsonl", [snap(i, True) for i in (0, 2, 1)])
    with pytest.raises(SystemExit):
        V.cell([f1, f2], 3, boot=10)  # different snapshot order
    with pytest.raises(SystemExit):
        V.cell([f1], 4, boot=10)  # count
    bad = snap(0, True)
    del bad["targets"]
    f3 = write(tmp_path / "s3.jsonl", [bad, snap(1, True), snap(2, True)])
    with pytest.raises(SystemExit):
        V.cell([f3], 3, boot=10)
    with pytest.raises(SystemExit):
        V.cell([f1], 3, boot=10, ids_ref=["x", "y", "z"])


def test_grip_stats():
    s = snap(0, True)  # recorded open -> open, pred chunk last openness 0.2 (closed)
    assert V.grip_stats(s) == {"grip_ok": False, "evt": False, "evt_ok": None}
    s["c"]["pred"][4] = 0.7
    assert V.grip_stats(s)["grip_ok"] is True
    s["grip_gt"] = [0.9, 0.1]  # recorded close inside the chunk
    assert V.grip_stats(s) == {"grip_ok": False, "evt": True, "evt_ok": False}
    s["c"]["pred"][4] = 0.3
    assert V.grip_stats(s) == {"grip_ok": True, "evt": True, "evt_ok": True}


def test_strata_and_grip_in_cell(tmp_path):
    n = 4  # odd i near
    f1 = write(tmp_path / "s0.jsonl", [snap(i, i % 2 == 0) for i in range(n)])
    c = V.cell([f1], n, boot=50)
    assert c["strata"]["free"]["n_snap"] == 2 and c["strata"]["near"]["n_snap"] == 2
    assert c["strata"]["free"]["a_xy"] == 1.0 and c["strata"]["near"]["a_xy"] == pytest.approx(2 / 7)
    assert c["strata"]["free"]["p_xy"] == 1.0 and c["strata"]["near"]["p_xy"] == 0.0
    assert c["strata"]["unknown"]["n_snap"] == 0
    assert c["grip_acc"] == 0.0 and c["grip_evt_n"] == 0


def test_distance_cfg_merges_by_the_near_flag(tmp_path):
    n = 4
    w1 = V.load_runs([write(tmp_path / "w1.jsonl", [snap(i, False) for i in range(n)])], n)
    w3 = V.load_runs([write(tmp_path / "w3.jsonl", [snap(i, True) for i in range(n)])], n)
    w1[0][2]["near"] = None  # unknown distance -> w = 1 (conservative)
    m = V.dcfg_runs(w3, w1)
    assert [x is w3[0][i] for i, x in enumerate(m[0])] == [True, False, False, False]
    assert V.DCFG == ((3.0, 1.0), (5.0, 1.0))


def test_checks_grip_non_inferiority():
    b = {**BASE, "grip_acc": 0.9}
    assert V.checks(base_cell(grip_acc=0.89), b, 1.0, None)["grip"]
    assert not V.checks(base_cell(grip_acc=0.8899), b, 1.0, None)["all"]


def test_rule_constants_fixed_before_results():
    assert (V.A_MIN, V.LB_MARGIN, V.DEC_MIN, V.MSE_MAX, V.LAT_MAX) == (0.8, 0.1, -0.01, 0.05, 0.10)
    assert V.RULE_ARMS == ("A", "B", "AB")
    assert np.isclose(V.EPS, 1e-12)
