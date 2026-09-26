"""E-NOV0 pure helpers (docs/stage3/prereg_nov0.md): split, reference selection, pooling, k-NN novelty, AUROC,
bootstrap, thresholds, error targets."""
import importlib.util
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, *rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


L = _load("nov0_lib", ("tools", "nov0", "nov0_lib.py"))


def _recs(n_seed=40, ks=(0, 10, 20), variants=("standard", "dr"), tasks=("bottle_tray", "mug_tray")):
    out = []
    for v in variants:
        for t in tasks:
            for s in range(10000, 10000 + n_seed):
                for k in ks:
                    out.append({"id": f"{v}/{t}/P0/ep{s}/k{k}", "split": "val" if s % 20 == 0 else "train"})
    return out


# ------------------------------------------------------------------------------------------ ids and split
def test_parse_id_fields():
    d = L.parse_id("dr/mug_tray/P1/ep10600/k30")
    assert d == {"variant": "dr", "task": "mug_tray", "kind": "P1", "seed": 10600, "k": 30,
                 "ep": "dr/mug_tray/P1/ep10600"}


def test_part_of_is_deterministic_and_about_cal_frac():
    parts = [L.part_of(s) for s in range(10000, 12000)]
    assert parts == [L.part_of(s) for s in range(10000, 12000)]
    frac = parts.count("cal") / len(parts)
    assert abs(frac - L.CAL_FRAC) < 0.03
    assert set(parts) == {"cal", "mem"}


def test_select_memory_calibration_eval_disjoint_and_stratified():
    recs = _recs()
    sel = L.select(recs, n_mem=20, n_cal=5, seed=0)
    ids = {k: set(v) for k, v in sel.items()}
    assert not (ids["mem"] & ids["cal"]) and not (ids["mem"] & ids["eval"]) and not (ids["cal"] & ids["eval"])
    assert ids["eval"] == {r["id"] for r in recs if r["split"] == "val"}
    seeds = {k: {L.parse_id(i)["seed"] for i in v} for k, v in ids.items()}
    assert not (seeds["mem"] & seeds["cal"])  # partition by scene seed, shared across variants / tasks
    assert all(L.part_of(s) == "mem" for s in seeds["mem"]) and all(L.part_of(s) == "cal" for s in seeds["cal"])
    for v in ("standard", "dr"):
        for t in ("bottle_tray", "mug_tray"):
            assert sum(i.startswith(f"{v}/{t}/") for i in sel["mem"]) == 20
            assert sum(i.startswith(f"{v}/{t}/") for i in sel["cal"]) <= 5
    assert sel == L.select(list(reversed(recs)), n_mem=20, n_cal=5, seed=0)  # input order does not matter


def test_select_takes_all_when_stratum_is_small():
    recs = _recs(n_seed=5)
    sel = L.select(recs, n_mem=10_000, n_cal=10_000, seed=0)
    fit = [r["id"] for r in recs if r["split"] == "train"]
    assert sorted(sel["mem"] + sel["cal"]) == sorted(fit)


# ------------------------------------------------------------------------------------------ pooling
def test_pool_vis_head_mean_and_wrist_mean():
    # two samples: sample 0 head (2 patches) + wrist (1), sample 1 head (1) + two wrists (1, 1)
    P = np.array([[1, 0], [3, 0], [0, 5], [2, 2], [0, 1], [0, 3]], float)
    out = L.pool_vis(P, counts=[2, 1, 1, 1, 1], n_img=[2, 3])
    assert out.shape == (2, 4)
    np.testing.assert_allclose(out[0], [2, 0, 0, 5])
    np.testing.assert_allclose(out[1], [2, 2, 0, 2])  # wrists pooled over all wrist patches


def test_pool_vis_rejects_count_mismatch():
    with pytest.raises(ValueError):
        L.pool_vis(np.zeros((5, 2)), counts=[2, 2], n_img=[2])
    with pytest.raises(ValueError):
        L.pool_vis(np.zeros((4, 2)), counts=[2, 2], n_img=[3])


# ------------------------------------------------------------------------------------------ k-NN novelty
def test_cl2n_centres_then_unit_norm():
    X = np.array([[1.0, 2.0], [3.0, 2.0]])
    Z = L.cl2n(X, X.mean(0))
    np.testing.assert_allclose(Z, [[-1, 0], [1, 0]])
    Z2 = L.cl2n(np.zeros((1, 3)), np.zeros(3))  # zero vector stays finite
    assert np.isfinite(Z2).all()


def test_knn_score_self_query_is_zero_and_orders_novelty():
    rng = np.random.default_rng(0)
    M = L.cl2n(rng.normal(size=(200, 16)), np.zeros(16))
    assert np.allclose(L.knn_score(M[:10], M, k=1), 0.0, atol=1e-6)
    far = L.cl2n(-M[:1] + 0.0, np.zeros(16))  # the antipode of a memory point
    near = M[:1]
    s = L.knn_score(np.vstack([near, far]), M, k=5)
    assert s[1] > s[0]


def test_knn_score_mean_of_k_cosine_distances():
    M = np.array([[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0]])
    q = np.array([[1.0, 0.0]])
    np.testing.assert_allclose(L.knn_score(q, M, k=2), [(0.0 + 1.0) / 2])
    np.testing.assert_allclose(L.knn_score(q, M, k=3, chunk=1), [(0.0 + 1.0 + 2.0) / 3])


# ------------------------------------------------------------------------------------------ AUROC and bootstrap
def test_auroc_equals_pairwise_definition_with_ties():
    from harvest.analysis.stats import auroc as brute
    rng = np.random.default_rng(1)
    s = rng.integers(0, 6, 300).astype(float)
    y = rng.random(300) < 0.3
    assert L.auroc(s, y) == pytest.approx(brute(s, y), abs=1e-12)
    assert L.auroc(np.array([1.0, 2.0]), np.array([False, True])) == 1.0
    assert L.auroc(np.array([1.0, 2.0]), np.array([True, True])) is None


def test_auroc_ci_contains_point_and_is_reproducible():
    rng = np.random.default_rng(2)
    cl = np.repeat(np.arange(60), 10)
    y = rng.random(600) < 0.3
    s = y * 1.0 + rng.normal(size=600)
    lo, hi = L.auroc_ci(s, y, cl, n=300, seed=0)
    a = L.auroc(s, y)
    assert lo < a < hi
    assert (lo, hi) == L.auroc_ci(s, y, cl, n=300, seed=0)


def test_auroc_ci_stratified_keeps_both_classes():
    cl = np.repeat(np.arange(20), 5)
    y = cl >= 18  # only two positive clusters: plain resampling can miss them, stratified never does
    s = y * 1.0 + np.linspace(0, 0.1, 100)
    lo, hi = L.auroc_ci(s, y, cl, n=200, seed=0, stratify=True)
    assert lo == hi == 1.0


# ------------------------------------------------------------------------------------------ thresholds
def test_thr_for_recall_reaches_recall_with_fewest_flags():
    s = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
    pos = np.array([0, 0, 1, 0, 1, 0, 1, 0, 1, 1], bool)
    tau = L.thr_for_recall(s, pos, 0.8)
    call, catch = L.call_catch(s, pos, tau, strict=False)
    assert catch >= 0.8 and tau == pytest.approx(0.5)
    assert call == pytest.approx(0.6)


def test_call_catch_strict_uses_greater_than():
    s = np.array([0.0, 1.0, 1.0, 2.0])
    pos = np.array([0, 1, 0, 1], bool)
    assert L.call_catch(s, pos, 1.0, strict=True) == (0.25, 0.5)
    assert L.call_catch(s, pos, 1.0, strict=False) == (0.75, 1.0)


def test_crossfit_two_halves_by_cluster():
    rng = np.random.default_rng(3)
    cl = np.repeat(np.arange(100), 20)
    y = rng.random(2000) < 0.3
    s = y * 2.0 + rng.normal(size=2000)
    r = L.crossfit(s, y, cl, recall=0.9)
    assert set(r) == {"recall", "call", "folds"} and len(r["folds"]) == 2
    assert 0.8 < r["recall"] < 1.0 and 0 < r["call"] < 1


def test_noise_index_ref_positions_first_then_rest_in_order():
    ev = ["a", "b", "c", "d", "e"]
    idx = L.noise_index(["d", "b"], ev)
    assert idx == {"d": 0, "b": 1, "a": 2, "c": 3, "e": 4}
    with pytest.raises(ValueError):
        L.noise_index(["x"], ev)  # a reference id outside the eval split


def test_large_error_union_of_decision_error_and_top_decile_mse():
    mse = np.arange(100, dtype=float)
    dec = np.zeros(100, bool)
    dec[:5] = True
    big, thr = L.large_error(dec, mse, q=0.9)
    assert thr == pytest.approx(np.quantile(mse, 0.9))
    assert big.sum() == 5 + (mse >= thr).sum()
    assert big[:5].all() and big[-1]
