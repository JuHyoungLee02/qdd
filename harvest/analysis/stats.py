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


def cluster_mean_ci(values_by_cluster, n=10000, seed=0, level=0.95):
    """Same draws and result as cluster_bootstrap_ci(values_by_cluster, mean), computed from per-cluster sums."""
    keys = list(values_by_cluster)
    s = np.array([float(np.sum(values_by_cluster[k])) for k in keys])
    c = np.array([len(values_by_cluster[k]) for k in keys], float)
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        pick = rng.choice(len(keys), len(keys), replace=True)
        out.append(s[pick].sum() / c[pick].sum())
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


def ece(p, correct, bins=15):
    """Expected calibration error: equal-width bins on [0, 1] (1.0 in the last bin), count-weighted |acc - conf|."""
    p, c = np.asarray(p, float), np.asarray(correct, float)
    idx = np.minimum((p * bins).astype(int), bins - 1)
    out = 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            out += m.sum() / len(p) * abs(c[m].mean() - p[m].mean())
    return float(out)


def auroc(score, label):
    """P(score of a positive > score of a negative), ties count 1/2. None when one class is missing."""
    s, y = np.asarray(score, float), np.asarray(label, bool)
    pos, neg = s[y], s[~y]
    if len(pos) == 0 or len(neg) == 0:
        return None
    gt = (pos[:, None] > neg[None, :]).sum()
    eq = (pos[:, None] == neg[None, :]).sum()
    return float((gt + 0.5 * eq) / (len(pos) * len(neg)))
