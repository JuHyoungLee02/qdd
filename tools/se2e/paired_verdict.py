"""Paired two-seed comparison against the reused motion-confirm baseline (prereg_cam3 §5, prereg_ma3 §5; the
prereg_ma1b §5 procedure generalized to any treatment arm name).

Runs: none_s1, <arm>_s1, none_s2, <arm>_s2 (none_s<s> = motion_s<s>, same seed = same data order). Effect of seed s
= metric(<arm>_s) - metric(none_s); POOLED = mean over the two seeds. Snapshot-cluster bootstrap: N_BOOT draws with
SEED, the same resampled snapshots for all four runs, pooled effect per draw, 95 % percentile interval.
Input checks (02-pitfalls P25): same snapshot keys in every run, the expected snapshot count, no duplicate
(key, question) item or duplicate chunk key, item records reproduce the run's summary.
"""
from __future__ import annotations

import json

import numpy as np

from temporal_verdict import CMP_EPS, load_items, metrics  # noqa: F401  (CMP_EPS re-exported)

SEEDS = ("s1", "s2")
SOURCES = ("RB1", "RB2")
STRATA = ("all", "transition", "steady")
N_BOOT, SEED = 10_000, 0


def run_names(arm):
    return ("none_s1", f"{arm}_s1", "none_s2", f"{arm}_s2")


def ge(x, t):
    return x >= t - CMP_EPS * max(1.0, abs(t))


def le(x, t):
    return x <= t + CMP_EPS * max(1.0, abs(t))


def load_runs(paths: dict, flags: dict, arm: str, n_snap: int = 1799):
    """(items per run, metrics per run incl. per_source). Asserts the input checks."""
    if set(paths) != set(run_names(arm)):
        raise SystemExit(f"runs {sorted(paths)} != {run_names(arm)}")
    items, m = {}, {}
    for c in run_names(arm):
        items[c], summ = load_items(paths[c])
        pairs = [(r["key"], r["question"]) for r in items[c]]
        assert len(pairs) == len(set(pairs)), f"{c}: duplicate (key, question) items"
        m[c] = metrics(items[c], flags)
        if summ is not None and summ.get("dec_acc") is not None:
            assert abs(m[c]["all"]["acc"] - summ["dec_acc"]) < 1e-9, c
            assert abs(m[c]["all"]["nll"] - summ["dec"]) < 1e-5, c
        m[c]["per_source"] = {s: metrics([r for r in items[c] if r["key"].split("_")[0] == s], flags)["all"]
                              for s in SOURCES}
        m[c]["summary"] = summ
    ks = {c: sorted({r["key"] for r in items[c]}) for c in items}
    first = ks[run_names(arm)[0]]
    assert all(v == first for v in ks.values()), "runs evaluated on different val keys"
    assert len(first) == n_snap, f"{len(first)} snapshots != {n_snap}"
    return items, m


def effects(m, arm, key="acc"):
    per = {s: {st: m[f"{arm}_{s}"][st][key] - m[f"none_{s}"][st][key] for st in STRATA} for s in SEEDS}
    pooled = {st: float(np.mean([per[s][st] for s in SEEDS])) for st in STRATA}
    spread = {st: per["s2"][st] - per["s1"][st] for st in STRATA}
    return per, pooled, spread


def source_effects(m, arm):
    return {s: float(np.mean([m[f"{arm}_{sd}"]["per_source"][s]["acc"] - m[f"none_{sd}"]["per_source"][s]["acc"]
                              for sd in SEEDS])) for s in SOURCES}


def bootstrap_acc(items, flags, arm, n_boot=N_BOOT, seed=SEED):
    R = run_names(arm)
    keys = sorted({r["key"] for r in items[R[0]]})
    idx = {k: i for i, k in enumerate(keys)}
    acc = {c: np.zeros(len(keys)) for c in R}
    cnt = np.zeros(len(keys))
    for c in R:
        for r in items[c]:
            acc[c][idx[r["key"]]] += r["correct"]
    for r in items[R[0]]:
        cnt[idx[r["key"]]] += 1
    trans = np.array([flags[k]["transition"] for k in keys])
    rng = np.random.default_rng(seed)
    out = {}
    for name, mask in (("all", np.ones(len(keys), bool)), ("transition", trans), ("steady", ~trans)):
        ks = np.flatnonzero(mask)
        draws = []
        for _ in range(n_boot):
            b = rng.choice(ks, len(ks), replace=True)
            a = {c: acc[c][b].sum() / cnt[b].sum() for c in R}
            draws.append(0.5 * ((a[R[1]] - a[R[0]]) + (a[R[3]] - a[R[2]])))
        out[name] = [float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))]
    return out


def load_chunks(path) -> dict:
    """{key: chunk record} of a tools/ma3/chunk_eval.py output (duplicate keys refused)."""
    out = {}
    for x in open(path):
        r = json.loads(x)
        if r.get("event") == "chunk":
            assert r["key"] not in out, f"{path}: duplicate chunk key {r['key']}"
            out[r["key"]] = r
    return out


def rel_reduction(chunks: dict, arm: str, field: str = "mse_n", n_boot=N_BOOT, seed=SEED):
    """Relative reduction of the mean per-snapshot error: r_s = 1 - mean(<arm>_s) / mean(none_s); pooled = mean
    over seeds; snapshot-cluster bootstrap of the pooled value (same draws for the four runs)."""
    R = run_names(arm)
    keys = sorted(chunks[R[0]])
    assert all(sorted(chunks[c]) == keys for c in R), "chunk records on different val keys"
    v = {c: np.array([chunks[c][k][field] for k in keys], float) for c in R}

    def red(ix=None):
        g = (lambda x: x) if ix is None else (lambda x: x[ix])
        return {s: 1.0 - g(v[f"{arm}_{s}"]).mean() / g(v[f"none_{s}"]).mean() for s in SEEDS}
    per = {s: float(x) for s, x in red().items()}
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(n_boot):
        b = rng.choice(len(keys), len(keys), replace=True)
        d = red(b)
        draws.append(0.5 * (d["s1"] + d["s2"]))
    return {"per_seed": per, "pooled": float(np.mean(list(per.values()))), "spread": per["s2"] - per["s1"],
            "boot_95": [float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))],
            "means": {c: float(v[c].mean()) for c in R}, "n": len(keys)}
