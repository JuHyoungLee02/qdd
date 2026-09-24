"""E-M4b-meas metrics (pure numpy): balanced accuracy (episode-cluster bootstrap on confusion counts), temperature
scaling, split conformal sets for a binary predicate, set metrics, and the M7 critic helpers (persistence, episode
FWER threshold by conformal max-score, first alarm, fixed-window detection)."""
from __future__ import annotations

import math

import numpy as np


def counts(y, yhat) -> np.ndarray:
    """[tp, fn, tn, fp]."""
    y, h = np.asarray(y, bool), np.asarray(yhat, bool)
    return np.array([(y & h).sum(), (y & ~h).sum(), (~y & ~h).sum(), (~y & h).sum()], float)


def ba_from_counts(c) -> float:
    c = np.asarray(c, float)
    tp, fn, tn, fp = c[..., 0], c[..., 1], c[..., 2], c[..., 3]
    with np.errstate(invalid="ignore", divide="ignore"):
        r = 0.5 * (tp / (tp + fn) + tn / (tn + fp))
    return float(r) if np.ndim(r) == 0 else r


def balanced_accuracy(y, yhat):
    v = ba_from_counts(counts(y, yhat))
    return None if math.isnan(v) else v


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.asarray(z, float)))


def fit_temperature(logits, y) -> float:
    """T > 0 minimizing the binary NLL of sigmoid(logits / T) (log-grid, then golden refinement)."""
    z, y = np.asarray(logits, float), np.asarray(y, float)

    def nll(T):
        p = np.clip(_sigmoid(z / T), 1e-7, 1 - 1e-7)
        return float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())
    grid = np.exp(np.linspace(np.log(0.05), np.log(50), 200))
    i = int(np.argmin([nll(T) for T in grid]))
    a, b = grid[max(i - 1, 0)], grid[min(i + 1, len(grid) - 1)]
    g = (math.sqrt(5) - 1) / 2
    for _ in range(60):
        c, d = b - g * (b - a), a + g * (b - a)
        if nll(c) < nll(d):
            b = d
        else:
            a = c
    return float((a + b) / 2)


def nonconf(p_true, y) -> np.ndarray:
    """Nonconformity = 1 - probability given to the true label."""
    p, y = np.asarray(p_true, float), np.asarray(y, int)
    return np.where(y == 1, 1 - p, p)


def conformal_qhat(scores, alpha: float) -> float:
    """Split conformal quantile: the ceil((n+1)(1-alpha))-th smallest score (1.0 = trivial set when n is too small)."""
    s = np.sort(np.asarray(scores, float))
    k = math.ceil((len(s) + 1) * (1 - alpha))
    return 1.0 if k > len(s) else float(s[k - 1])


def set_of(p_true: float, qhat: float) -> str:
    has1, has0 = (1 - p_true) <= qhat, p_true <= qhat
    return "unknown" if has1 and has0 else ("true" if has1 else ("false" if has0 else "empty"))


def set_metrics(y, sets) -> dict:
    y = np.asarray(y, int)
    s = np.asarray(sets)
    cov = ((s == "unknown") | ((s == "true") & (y == 1)) | ((s == "false") & (y == 0))).mean()
    single = np.isin(s, ["true", "false"])
    f = s == "false"
    return {"n": int(len(y)), "coverage": float(cov), "singleton": float(single.mean()),
            "unknown": float((s == "unknown").mean()), "empty": float((s == "empty").mean()),
            "false_precision": float((y[f] == 0).mean()) if f.any() else None, "n_false": int(f.sum())}


def _boot_pick(E, n, seed):
    return np.random.default_rng(seed).integers(0, E, size=(n, E))


def boot_ba_ci(c, n=2000, seed=0, level=0.95):
    """c: [episodes, predicates, 4] confusion counts. CI of the mean over predicates of the pooled BA."""
    c = np.asarray(c, float)
    pick = _boot_pick(c.shape[0], n, seed)
    tot = c[pick].sum(1)  # [n, P, 4]
    ba = np.nanmean(ba_from_counts(tot), axis=-1)
    a = (1 - level) / 2
    return float(np.nanquantile(ba, a)), float(np.nanquantile(ba, 1 - a))


def boot_ba_diff_ci(ca, cb, n=2000, seed=0, level=0.95):
    """Paired (same episodes) CI of meanBA(a) - meanBA(b)."""
    ca, cb = np.asarray(ca, float), np.asarray(cb, float)
    pick = _boot_pick(ca.shape[0], n, seed)
    d = np.nanmean(ba_from_counts(ca[pick].sum(1)), -1) - np.nanmean(ba_from_counts(cb[pick].sum(1)), -1)
    a = (1 - level) / 2
    return float(np.nanquantile(d, a)), float(np.nanquantile(d, 1 - a))


# ------------------------------------------------------------------------------------------ critic
def persist(scores, k: int) -> np.ndarray:
    """Persistence filter: min of the last k scores (the channel must stay high for k consecutive snapshots)."""
    s = np.asarray(scores, float)
    return np.array([s[max(0, i - k + 1):i + 1].min() for i in range(len(s))])


def fwer_threshold(ep_max_scores, alpha: float) -> float:
    """Episode-level conformal threshold on non-failure calibration episodes: alarm when score > threshold, so a new
    exchangeable non-failure episode alarms with probability <= alpha (n too small -> the max)."""
    s = np.sort(np.asarray(ep_max_scores, float))
    k = math.ceil((len(s) + 1) * (1 - alpha))
    return float(s[min(k, len(s)) - 1])


def first_alarm(times, scores, thr: float):
    for t, s in zip(times, scores):
        if s > thr:
            return float(t)
    return None


def detected(t_alarm, onset: float, tau: float = 2.0) -> bool:
    """Fixed-window recall (canon §23): the FIRST alarm falls in [onset, onset + tau]."""
    return t_alarm is not None and onset - 1e-9 <= t_alarm <= onset + tau + 1e-9
