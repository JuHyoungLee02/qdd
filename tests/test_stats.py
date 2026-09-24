from harvest.analysis.stats import cluster_bootstrap_ci, holm


def test_bootstrap_ci_contains_mean():
    lo, hi = cluster_bootstrap_ci({f"e{i}": [i % 2] * 5 for i in range(40)}, lambda xs: sum(xs) / len(xs), n=2000)
    assert lo < 0.5 < hi


def test_holm_step_down():
    r = holm({"a": 0.001, "b": 0.04, "c": 0.03})
    assert r == {"a": True, "c": False, "b": False}


def test_ece_perfectly_calibrated_is_zero_and_overconfident_is_positive():
    from harvest.analysis.stats import ece
    # bin [0.8, 0.866..): 5 items at p=0.8, 4 correct -> gap 0
    assert ece([0.8] * 5, [1, 1, 1, 1, 0], bins=15) == 0.0
    # all p=1.0 (last bin includes 1.0), half correct -> gap 0.5
    assert abs(ece([1.0] * 4, [1, 0, 1, 0], bins=15) - 0.5) < 1e-12
    # two bins weighted by count: 2 items p=0.1 all wrong (gap 0.1), 2 items p=0.9 all right (gap 0.1)
    assert abs(ece([0.1, 0.1, 0.9, 0.9], [0, 0, 1, 1], bins=15) - 0.1) < 1e-12


def test_auroc_basic_and_ties():
    from harvest.analysis.stats import auroc
    assert auroc([0.9, 0.8, 0.2, 0.1], [1, 1, 0, 0]) == 1.0
    assert auroc([0.1, 0.2, 0.8, 0.9], [1, 1, 0, 0]) == 0.0
    assert auroc([0.5, 0.5], [1, 0]) == 0.5  # ties count one half
    assert auroc([0.5, 0.7], [1, 1]) is None  # one class only


def test_cluster_mean_ci_equals_generic_bootstrap_of_the_mean():
    import numpy as np
    from harvest.analysis.stats import cluster_bootstrap_ci, cluster_mean_ci
    rng = np.random.default_rng(3)
    by = {i: list(rng.integers(0, 2, rng.integers(1, 9))) for i in range(12)}
    slow = cluster_bootstrap_ci(by, lambda v: float(np.mean(v)), n=500)
    fast = cluster_mean_ci(by, n=500)
    assert abs(slow[0] - fast[0]) < 1e-12 and abs(slow[1] - fast[1]) < 1e-12


def test_cluster_diff_ci_joint_resampling():
    from harvest.analysis.stats import cluster_diff_ci
    a = {c: [1, 1] for c in range(10)}
    b = {c: [0, 0] for c in range(10)}
    assert cluster_diff_ci(a, b, n=200) == (1.0, 1.0)
    assert cluster_diff_ci(a, a, n=200) == (0.0, 0.0)
    # same clusters drawn for both sides: a cluster-level shared effect cancels in the difference
    a2 = {c: [c % 2, 1] for c in range(10)}
    b2 = {c: [c % 2, 0] for c in range(10)}
    lo, hi = cluster_diff_ci(a2, b2, n=500)
    assert abs(lo - 0.5) < 1e-12 and abs(hi - 0.5) < 1e-12
    # clusters present on one side only still enter that side's mean (union of cluster ids)
    lo, hi = cluster_diff_ci({0: [1], 1: [1]}, {0: [0], 2: [0]}, n=300)
    assert lo == hi == 1.0
