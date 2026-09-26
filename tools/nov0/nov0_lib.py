"""E-NOV0 pure helpers (docs/stage3/prereg_nov0.md). numpy only (no torch) so the verdict runs anywhere.

  ids / split   parse_id (R2 sample id <variant>/<task>/<kind>/ep<seed>/k<k>), part_of (fit scene seed -> memory or
                calibration part, salted hash), select (memory / calibration samples per (variant, task) + the whole
                eval split)
  pooling       pool_vis (vision tower patches -> [head mean ; wrist mean] per sample)
  novelty       cl2n (centre with the reference mean, unit norm), knn_score (mean cosine distance to the k nearest
                reference rows)
  statistics    auroc (rank form, ties 1/2), auroc_ci (episode-cluster bootstrap, optional class-stratified),
                thr_for_recall / call_catch / crossfit (gating operating points), large_error (error target)
"""
from __future__ import annotations

import hashlib
import math
import random
import re

import numpy as np

PART_SALT = "nov0part@v1"
CAL_FRAC = 0.15
_ID = re.compile(r"^([^/]+)/([^/]+)/(P\d+)/ep(\d+)/k(\d+)$")


# ------------------------------------------------------------------------------------------ ids and split
def parse_id(sid: str) -> dict:
    m = _ID.match(sid)
    if not m:
        raise ValueError(f"not an R2 sample id: {sid!r}")
    v, t, kind, seed, k = m.groups()
    return {"variant": v, "task": t, "kind": kind, "seed": int(seed), "k": int(k), "ep": f"{v}/{t}/{kind}/ep{seed}"}


def part_of(seed: int, frac: float = CAL_FRAC, salt: str = PART_SALT) -> str:
    """'cal' or 'mem' for a fit scene seed (the same seed in every variant / task lands in the same part)."""
    h = int(hashlib.sha256(f"{salt}|{int(seed)}".encode()).hexdigest()[:8], 16)
    return "cal" if h / 0x100000000 < frac else "mem"


def select(recs, n_mem: int, n_cal: int, seed: int = 0) -> dict:
    """recs: [{'id', 'split' ('train' = fit, 'val' = eval)}]. Returns {'mem', 'cal', 'eval'}: sorted id lists;
    mem / cal = a seeded sample of n_mem / n_cal fit ids per (variant, task) from the memory / calibration seeds
    (all of them when fewer), eval = every eval-split id."""
    fit, ev = {}, []
    for r in sorted(recs, key=lambda r: r["id"]):
        if r["split"] == "val":
            ev.append(r["id"])
            continue
        if r["split"] != "train":
            raise ValueError(f"{r['id']}: split {r['split']!r}")
        d = parse_id(r["id"])
        fit.setdefault((d["variant"], d["task"], part_of(d["seed"])), []).append(r["id"])
    rng = random.Random(seed)
    out = {"mem": [], "cal": [], "eval": ev}
    for key in sorted(fit):
        ids, part = fit[key], key[2]
        n = n_mem if part == "mem" else n_cal
        out[part] += ids if len(ids) <= n else rng.sample(ids, n)
    out["mem"], out["cal"] = sorted(out["mem"]), sorted(out["cal"])
    return out


def noise_index(ref_ids, eval_ids) -> dict:
    """Flow-noise index per eval id: position in ref_ids (E-MA2 eval set, E-SR0 numbering) for those ids, then
    len(ref_ids) + position among the remaining eval ids (their given order)."""
    ev = set(eval_ids)
    miss = [i for i in ref_ids if i not in ev]
    if miss:
        raise ValueError(f"{len(miss)} reference ids are not in the eval split")
    out = {i: n for n, i in enumerate(ref_ids)}
    for i in eval_ids:
        if i not in out:
            out[i] = len(out)
    return out


# ------------------------------------------------------------------------------------------ pooling
def pool_vis(patches, counts, n_img) -> np.ndarray:
    """patches [sum(counts), D] (vision tower output, images in sample order); counts = patches per image;
    n_img = images per sample (first = head, rest = wrists). Returns [n_samples, 2D] = [head mean ; mean over all
    wrist patches]."""
    P = np.asarray(patches, float)
    if sum(counts) != P.shape[0]:
        raise ValueError(f"patch count {P.shape[0]} != sum(counts) {sum(counts)}")
    if sum(n_img) != len(counts):
        raise ValueError(f"{len(counts)} images for n_img {list(n_img)}")
    edges = np.concatenate([[0], np.cumsum(counts)]).astype(int)
    out, j = [], 0
    for n in n_img:
        if n < 2:
            raise ValueError("a sample needs a head and at least one wrist image")
        head = P[edges[j]:edges[j + 1]].mean(0)
        wrist = P[edges[j + 1]:edges[j + n]].mean(0)
        out.append(np.concatenate([head, wrist]))
        j += n
    return np.stack(out)


# ------------------------------------------------------------------------------------------ novelty
def cl2n(X, mu) -> np.ndarray:
    Z = np.asarray(X, np.float64) - np.asarray(mu, np.float64)
    n = np.linalg.norm(Z, axis=1, keepdims=True)
    return Z / np.maximum(n, 1e-12)


def knn_score(Q, M, k: int = 10, chunk: int = 1024) -> np.ndarray:
    """Mean cosine distance (1 - cos) of each unit row of Q to its k nearest unit rows of M."""
    Q, M = np.asarray(Q, np.float64), np.asarray(M, np.float64)
    if not 1 <= k <= len(M):
        raise ValueError(f"k {k} for {len(M)} reference rows")
    out = np.empty(len(Q))
    for a in range(0, len(Q), chunk):
        d = 1.0 - Q[a:a + chunk] @ M.T
        part = np.partition(d, k - 1, axis=1)[:, :k]
        out[a:a + chunk] = np.clip(part, 0.0, None).mean(1)
    return out


# ------------------------------------------------------------------------------------------ statistics
def _fast_auroc(s, y):
    npos = int(y.sum())
    nneg = len(y) - npos
    if npos == 0 or nneg == 0:
        return None
    o = np.argsort(s, kind="mergesort")
    _, first, cnt = np.unique(s[o], return_index=True, return_counts=True)
    ranks = np.empty(len(s))
    ranks[o] = np.repeat(first + (cnt - 1) / 2.0 + 1.0, cnt)  # average ranks of tied groups
    return float((ranks[y].sum() - npos * (npos + 1) / 2.0) / (npos * nneg))


def auroc(score, label):
    """P(score of a positive > score of a negative), ties 1/2 (Mann-Whitney). None when a class is missing."""
    return _fast_auroc(np.asarray(score, float), np.asarray(label, bool))


def auroc_ci(score, label, cluster, n: int = 10000, seed: int = 0, level: float = 0.95, stratify: bool = False):
    """Percentile interval of the AUROC over episode-cluster bootstrap draws. stratify: resample the positive-only and
    the negative-only clusters separately (shift tests, where every cluster is one class). Draws missing a class are
    dropped."""
    s, y, c = np.asarray(score, float), np.asarray(label, bool), np.asarray(cluster)
    keys, inv = np.unique(c, return_inverse=True)
    idx = [np.flatnonzero(inv == j) for j in range(len(keys))]
    rng = np.random.default_rng(seed)
    if stratify:
        pure = [bool(y[i].all()) or not y[i].any() for i in idx]
        if not all(pure):
            raise ValueError("stratify: clusters must be single-class")
        groups = [[j for j in range(len(idx)) if y[idx[j]][0]], [j for j in range(len(idx)) if not y[idx[j]][0]]]
    else:
        groups = [list(range(len(idx)))]
    out = []
    for _ in range(n):
        pick = np.concatenate([np.asarray(g)[rng.integers(0, len(g), len(g))] for g in groups if g])
        ii = np.concatenate([idx[j] for j in pick])
        a = _fast_auroc(s[ii], y[ii])
        if a is not None:
            out.append(a)
    a = (1 - level) / 2
    return float(np.quantile(out, a)), float(np.quantile(out, 1 - a))


def thr_for_recall(score, pos, recall: float) -> float:
    """Largest tau with recall(score >= tau) >= recall."""
    s, y = np.asarray(score, float), np.asarray(pos, bool)
    ps = np.sort(s[y])[::-1]
    if len(ps) == 0:
        raise ValueError("no positives")
    need = max(1, math.ceil(recall * len(ps) - 1e-9))
    return float(ps[need - 1])


def call_catch(score, pos, tau: float, strict: bool = True):
    """(call rate = flagged share of all, catch = flagged share of positives); flag = score > tau (strict) or >=."""
    s, y = np.asarray(score, float), np.asarray(pos, bool)
    f = s > tau if strict else s >= tau
    return float(f.mean()), float(f[y].mean()) if y.any() else float("nan")


def crossfit(score, pos, cluster, recall: float = 0.9, salt: str = "nov0xfit@v1") -> dict:
    """Two episode halves (salted hash of the cluster id): the recall threshold fitted on one half is applied to the
    other. Returns mean held-out recall and call rate and the per-fold values."""
    s, y, c = np.asarray(score, float), np.asarray(pos, bool), np.asarray(cluster).astype(str)
    half = np.array([int(hashlib.sha256(f"{salt}|{x}".encode()).hexdigest()[:8], 16) % 2 for x in c])
    folds = []
    for a in (0, 1):
        fit, test = half == a, half != a
        tau = thr_for_recall(s[fit], y[fit], recall)
        call, catch = call_catch(s[test], y[test], tau, strict=False)
        folds.append({"fit_half": a, "tau": tau, "call": call, "recall": catch, "n_test": int(test.sum())})
    return {"recall": float(np.mean([f["recall"] for f in folds])), "call": float(np.mean([f["call"] for f in folds])),
            "folds": folds}


def large_error(dec_err, mse, q: float = 0.9):
    """(large-error flag = any decision wrong OR chunk MSE >= the q quantile of these MSEs, that threshold)."""
    m = np.asarray(mse, float)
    thr = float(np.quantile(m, q))
    return np.asarray(dec_err, bool) | (m >= thr), thr
