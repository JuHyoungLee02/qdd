"""Shared statistics (E §1.7): episode-cluster bootstrap, Holm step-down."""
import numpy as np


def cluster_bootstrap_ci(values_by_cluster, stat, n=10000, seed=0, level=0.95):
    keys = list(values_by_cluster)
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        pick = rng.choice(len(keys), len(keys), replace=True)
        out.append(stat([v for j in pick for v in values_by_cluster[keys[j]]]))
    a = (1 - level) / 2
    return float(np.quantile(out, a)), float(np.quantile(out, 1 - a))


def holm(pvals, alpha=0.05):
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, res, stop = len(items), {}, False
    for i, (k, p) in enumerate(items):
        if stop or p > alpha / (m - i):
            stop = True
            res[k] = False
        else:
            res[k] = True
    return res
