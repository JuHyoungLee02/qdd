from harvest.analysis.stats import cluster_bootstrap_ci, holm


def test_bootstrap_ci_contains_mean():
    lo, hi = cluster_bootstrap_ci({f"e{i}": [i % 2] * 5 for i in range(40)}, lambda xs: sum(xs) / len(xs), n=2000)
    assert lo < 0.5 < hi


def test_holm_step_down():
    r = holm({"a": 0.001, "b": 0.04, "c": 0.03})
    assert r == {"a": True, "c": False, "b": False}
