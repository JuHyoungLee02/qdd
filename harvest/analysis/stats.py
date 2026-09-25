"""Shared statistics (E §1.7): episode-cluster bootstrap, Holm step-down."""
import numpy as np

N_BOOT = 10000  # E-first §1.7 / EVAL §4.2: cluster bootstrap 10,000 draws (canon §72, R7 cycle 7 E1)

# Pre-registered thresholds are compared on unrounded statistics with a float-noise tolerance (canon §74): a statistic
# that equals the threshold in exact arithmetic (e.g. AUROC 0.83 - 0.80, 0.8 - 0.08, ECE |78/100 - 0.75|) must land on
# the side the wording puts the boundary. 1e-12 is far below any gap between distinct count ratios the judgments see.
CMP_EPS = 1e-12


def at_least(x, t) -> bool:
    """x >= t (boundary included)."""
    return x >= t - CMP_EPS


def at_most(x, t) -> bool:
    """x <= t (boundary included)."""
    return x <= t + CMP_EPS


def below(x, t) -> bool:
    """x < t (boundary excluded)."""
    return x < t - CMP_EPS


def above(x, t) -> bool:
    """x > t (boundary excluded)."""
    return x > t + CMP_EPS


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


def cluster_diff_ci(a_by_cluster, b_by_cluster, n=10000, seed=0, level=0.95):
    """CI of mean(a) - mean(b) (item-weighted means) when a and b share cluster ids (e.g. the same episode under two
    scene variants): each draw resamples cluster ids from the union once and uses them for both sides."""
    keys = sorted(set(a_by_cluster) | set(b_by_cluster), key=repr)
    sa = np.array([float(np.sum(a_by_cluster.get(k, []))) for k in keys])
    ca = np.array([len(a_by_cluster.get(k, [])) for k in keys], float)
    sb = np.array([float(np.sum(b_by_cluster.get(k, []))) for k in keys])
    cb = np.array([len(b_by_cluster.get(k, [])) for k in keys], float)
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        pick = rng.choice(len(keys), len(keys), replace=True)
        na, nb = ca[pick].sum(), cb[pick].sum()
        out.append(sa[pick].sum() / na - sb[pick].sum() / nb if na and nb else np.nan)  # empty side: draw dropped
    a = (1 - level) / 2
    return float(np.nanquantile(out, a)), float(np.nanquantile(out, 1 - a))


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


def holm_ci(ci_at, names, alpha=0.05, direction="two-sided"):
    """Holm step-down on bootstrap intervals (E §1.7 "Holm 보정", §2A.6-10): with m hypotheses, step s = 0, 1, ...
    rejects one remaining hypothesis whose two-sided interval at level 1 - alpha / (m - s) excludes 0 and stops at
    the first step where none does. This is Holm on the CI-inversion p-value (p <= alpha / (m - s) exactly when that
    interval excludes 0; the percentile intervals of one set of draws are nested). ci_at(name, level) -> (lo, hi).
    direction "greater" (a pre-registered "하한 > 0" criterion, canon §74): only lower > 0 is a rejection; an interval
    wholly below 0 is not, and does not release the next step's level. Same intervals as two-sided.
    Returns {name: {"reject", "lo", "hi", "level"}} (the interval at the level of the step that decided it)."""
    if direction not in ("two-sided", "greater"):
        raise ValueError(f"holm_ci direction {direction!r}: two-sided | greater")
    rem, m, out = list(names), len(names), {}
    for s in range(m):
        level = 1 - alpha / (m - s)
        cis = {k: ci_at(k, level) for k in rem}
        hit = [k for k in rem if cis[k][0] > 0 or (direction == "two-sided" and cis[k][1] < 0)]
        if not hit:
            break
        k = max(hit, key=lambda x: max(cis[x][0], -cis[x][1]))
        out[k] = {"reject": True, "lo": cis[k][0], "hi": cis[k][1], "level": level}
        rem.remove(k)
    for k in rem:
        lo, hi = cis[k]
        out[k] = {"reject": False, "lo": lo, "hi": hi, "level": level}
    return out


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
