"""E-SR0 verdict (prereg_sr0 §5): per-snapshot scoring, chance from shuffled decisions, rule boundaries, input checks."""
import importlib.util
import json
import os

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, *rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


V = _load("sr0_verdict", ("tools", "sr0", "sr0_verdict.py"))
E = _load("sr0_eval_v", ("tools", "sr0", "sr0_eval.py"))
LAB = {"dir_xy": "plus_x", "dir_z": "none_z", "mag_coarse": "small"}


def _snap(key="k0", follow=True, lab=LAB, grip=False, amp=0.01, base=(0.004, 0.0, 0.0)):
    """A snapshot record: follow = the chunk moves along every forced decision; else it always moves along `base`."""
    c = {}
    for n in E.cond_names(grip):
        d = np.array(base, float)
        if follow:
            com = {**lab}
            if n.startswith("xy:"):
                com["dir_xy"] = n[3:]
            elif n.startswith("z:"):
                com["dir_z"] = n[2:]
            elif n.startswith("mag:"):
                com["mag_coarse"] = n[4:]
            elif n == "flip":
                com = {**lab, "dir_xy": E.FLIP_XY[lab["dir_xy"]], "dir_z": E.FLIP_Z[lab["dir_z"]]}
            s = amp * (1 + E.MAGS.index(com["mag_coarse"]))
            u = E.unit_xy(com["dir_xy"])
            d = np.array([s * u[0], s * u[1], {"up": s, "down": -s, "none_z": 0.0}[com["dir_z"]]])
        g1 = 0.0
        if n == "pid:open":
            g1 = 1.0 if follow else 0.0
        c[n] = [float(d[0]), float(d[1]), float(d[2]), 0.5, g1, 0.01 if n != "flip" else 0.02]
    return {"event": "snap", "key": key, "labels": dict(lab), "preds": dict(lab), "disp_gt": [0.01, 0.0, 0.0],
            "c": c}


def test_follower_scores_one_and_chance_is_about_three_eighths():
    st = V.snap_stats(_snap(), grip=False)
    assert st["xy_pairs"] == 7 and st["xy_hits"] == 7  # plus_x is the true bin: 7 counterfactual directions
    # each forced displacement matches its own direction and its two 45-degree neighbours: 3 of 8 labels
    assert abs(st["xy_chance"] / st["xy_pairs"] - 3 / 8) < 1e-12
    assert abs(st["xy_cos"] / st["xy_pairs"] - 1) < 1e-12
    assert st["z_pairs"] == 2 and st["z_hits"] == 2 and abs(st["z_chance"] / st["z_pairs"] - 0.5) < 1e-12
    assert abs(st["rho"] - 1) < 1e-12 and st["true_ok"] is True and st["gt_ok"] is True


def test_ignorer_scores_at_the_chance_of_its_fixed_direction():
    st = V.snap_stats(_snap(follow=False), grip=False)
    # always +x: hits only the counterfactuals within 60 deg of +x (plus_x_plus_y, plus_x_minus_y)
    assert st["xy_hits"] == 2 and st["xy_pairs"] == 7
    assert st["z_hits"] == 0  # no vertical motion: neither up nor down is followed
    assert np.isnan(st["rho"])  # all magnitudes equal: undefined, excluded from the mean


def test_tiny_displacement_fails():
    s = _snap(follow=False, base=(0.00005, 0.0, 0.0))
    st = V.snap_stats(s, grip=False)
    assert st["xy_hits"] == 0 and st["xy_chance"] == 0


def test_none_true_label_makes_all_eight_counterfactual_and_no_true_baseline():
    lab = {"dir_xy": "none_xy", "dir_z": "up", "mag_coarse": "tiny"}
    st = V.snap_stats(_snap(lab=lab), grip=False)
    assert st["xy_pairs"] == 8 and st["xy_hits"] == 8 and st["true_ok"] is None
    assert st["z_pairs"] == 1  # only 'down' is counterfactual


def test_grip_pair():
    st = V.snap_stats(_snap(grip=True), grip=True)
    assert st["grip_hit"] is True and st["grip_rev"] is False
    st = V.snap_stats(_snap(grip=True, follow=False), grip=True)
    assert st["grip_hit"] is False and st["grip_rev"] is False


def test_spearman_average_ranks():
    assert abs(V.spearman([0, 1, 2, 3, 4], [1, 2, 3, 4, 5]) - 1) < 1e-12
    assert abs(V.spearman([0, 1, 2, 3, 4], [5, 4, 3, 2, 1]) + 1) < 1e-12
    assert np.isnan(V.spearman([0, 1, 2, 3, 4], [1, 1, 1, 1, 1]))
    r = V.spearman([0, 1, 2, 3, 4], [1, 1, 2, 3, 4])  # ties get average ranks
    assert 0.9 < r < 1.0


@pytest.mark.parametrize("axy,az,rho,want", [
    ({"se2e": 0.6, "r2": 0.6}, {"se2e": 0.6, "r2": 0.6}, {"se2e": 0.5, "r2": 0.5}, "FOLLOWS"),
    ({"se2e": 0.5999, "r2": 0.9}, {"se2e": 0.9, "r2": 0.9}, {"se2e": 0.9, "r2": 0.9}, "WEAK"),
    ({"se2e": 0.9, "r2": 0.5999}, {"se2e": 0.9, "r2": 0.9}, {"se2e": 0.9, "r2": 0.9}, "WEAK"),
    ({"se2e": 0.9, "r2": 0.9}, {"se2e": 0.5999, "r2": 0.9}, {"se2e": 0.9, "r2": 0.9}, "PARTIAL"),
    ({"se2e": 0.9, "r2": 0.9}, {"se2e": 0.9, "r2": 0.9}, {"se2e": 0.9, "r2": 0.4999}, "PARTIAL"),
])
def test_rule_boundaries(axy, az, rho, want):
    assert V.decide(axy, az, rho)["verdict"] == want


def test_pool_and_bootstrap_are_paired_by_key(tmp_path):
    a = [V.snap_stats(_snap(key=f"k{i}", follow=i % 2 == 0), grip=False) for i in range(6)]
    p = V.pool([a, a], np.arange(6))
    assert p["xy_pairs"] == 2 * 42 and abs(p["a_xy"] - (3 * 7 + 3 * 2) / 42) < 1e-12
    ci = V.boot_ci([a, a], n_boot=200, seed=0)
    assert ci["a_xy"][0] <= p["a_xy"] <= ci["a_xy"][1] and set(ci) == set(V.BOOT_METRICS)
    assert V.boot_ci([a, a], n_boot=200, seed=0) == ci  # seeded


def _write(path, snaps, n=None, ckpt="x"):
    with open(path, "w") as f:
        for s in snaps:
            f.write(json.dumps(s) + "\n")
        f.write(json.dumps({"event": "summary", "ckpt": ckpt, "n": len(snaps) if n is None else n,
                            "grip": "pid:open" in snaps[0]["c"]}) + "\n")


def test_load_checks_count_duplicates_and_conditions(tmp_path):
    p = tmp_path / "a.jsonl"
    _write(p, [_snap("a"), _snap("b")])
    assert [s["key"] for s in V.load(str(p), n_expect=2, grip=False)] == ["a", "b"]
    with pytest.raises(SystemExit):
        V.load(str(p), n_expect=3, grip=False)
    _write(p, [_snap("a"), _snap("a")])
    with pytest.raises(SystemExit):
        V.load(str(p), n_expect=2, grip=False)
    s = _snap("a")
    del s["c"]["mag:large"]
    _write(p, [s, _snap("b")])
    with pytest.raises(SystemExit):
        V.load(str(p), n_expect=2, grip=False)
    s = _snap("a")
    s["c"]["true"][0] = float("nan")
    _write(p, [s, _snap("b")])
    with pytest.raises(SystemExit):
        V.load(str(p), n_expect=2, grip=False)
