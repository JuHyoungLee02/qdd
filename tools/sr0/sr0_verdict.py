"""E-SR0 verdict (docs/stage3/prereg_sr0.md §5, fixed before the main runs; not edited after results).

  python tools/sr0/sr0_verdict.py --se2e S1.jsonl S2.jsonl --n-se2e 1799 --r2 C0.jsonl --n-r2 1200 --out JSON

Per snapshot (sr0_eval 'snap' records):
  xy adherence    counterfactual pairs (d in the 8 directions, d != the label's dir_xy): hit = |disp_xy| >= 0.1 mm
                  and cos(disp_xy of the chunk under xy:d, unit(d)) > 0.5; mean cosine (0 when |disp_xy| < 0.1 mm)
  xy chance       the same pairs scored against shuffled decisions: for the chunk under xy:d, the mean hit rate over
                  all 8 direction labels (= the expected hit rate when forced labels are randomly permuted)
  z adherence     counterfactual d in {up, down} != the label's dir_z: hit = disp_z >= 0.1 mm (up) / <= -0.1 mm
                  (down) under z:d; chance = mean over both labels
  magnitude       Spearman rho (average ranks) of the bin index (tiny .. xlarge) and |disp| under mag:<m>; NaN when
                  all equal (left out of the mean); chance 0 (random permutation of the bins)
  gripper (R2)    diff = openness(last target | pid:open) - openness(last target | pid:close); hit = diff >= 0.1,
                  reverse = diff <= -0.1, chance = (hit + reverse) / 2
  true baseline   label dir_xy != none_xy: the chunk under 'true' (and the recorded action, disp_gt) matches it
  MSE             normalized chunk MSE vs the recorded action under true / pred / flip
Rule (CMP_EPS 1e-12), datasets = se2e (motion_s1 + motion_s2 pooled, pairs summed) and r2 (E-MA2 c0):
  WEAK     if A_xy < 0.6 in either dataset            -> fix the conditioning before coupling (follow-up E-SR1b)
  PARTIAL  elif A_z < 0.6 or mean rho < 0.5 in either  -> direction follows; the failing axis goes to the follow-up
  FOLLOWS  otherwise
Bootstrap (outside the rule): snapshots resampled 10,000 times (seed 0; se2e seeds paired by key), 95 % percentile.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", ".."))
sys.path.insert(0, _HERE)

from sr0_eval import DIR_XY8, MAGS, cond_names, unit_xy  # noqa: E402

EPS = 1e-12
MIN_DISP_M = 1e-4
A_MIN, RHO_MIN, GRIP_MIN = 0.6, 0.5, 0.1


def cos_xy(d, u) -> float:
    n = math.hypot(d[0], d[1])
    return 0.0 if n < MIN_DISP_M else (d[0] * u[0] + d[1] * u[1]) / n


def match_xy(d, name) -> bool:
    return bool(math.hypot(d[0], d[1]) >= MIN_DISP_M and cos_xy(d, unit_xy(name)) > 0.5)


def match_z(d, name) -> bool:
    return bool(d[2] >= MIN_DISP_M if name == "up" else d[2] <= -MIN_DISP_M)


def _ranks(x):
    x = np.asarray(x, float)
    o = np.argsort(x, kind="stable")
    r = np.empty(len(x))
    r[o] = np.arange(len(x), dtype=float)
    for v in np.unique(x):
        m = x == v
        r[m] = r[m].mean()
    return r


def spearman(a, b) -> float:
    ra, rb = _ranks(a), _ranks(b)
    if np.all(rb == rb[0]) or np.all(ra == ra[0]):
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def snap_stats(s: dict, grip: bool) -> dict:
    c, lab = s["c"], s["labels"]
    txy, tz = lab["dir_xy"], lab["dir_z"]
    st = {"key": s["key"], "xy_pairs": 0, "xy_hits": 0, "xy_chance": 0.0, "xy_cos": 0.0, "z_pairs": 0, "z_hits": 0,
          "z_chance": 0.0, "by_dir": {}}
    for d in DIR_XY8:
        if d == txy:
            continue
        disp = c[f"xy:{d}"][:3]
        h = match_xy(disp, d)
        st["xy_pairs"] += 1
        st["xy_hits"] += h
        st["xy_chance"] += float(np.mean([match_xy(disp, e) for e in DIR_XY8]))
        st["xy_cos"] += cos_xy(disp, unit_xy(d))
        st["by_dir"][d] = bool(h)
    for d in ("up", "down"):
        if d == tz:
            continue
        disp = c[f"z:{d}"][:3]
        st["z_pairs"] += 1
        st["z_hits"] += match_z(disp, d)
        st["z_chance"] += float(np.mean([match_z(disp, e) for e in ("up", "down")]))
    st["rho"] = spearman(np.arange(len(MAGS)), [np.linalg.norm(c[f"mag:{m}"][:3]) for m in MAGS])
    st["mag_ratio"] = float(np.linalg.norm(c["mag:xlarge"][:3]) / max(np.linalg.norm(c["mag:tiny"][:3]), 1e-9))
    st["true_ok"] = None if txy == "none_xy" else match_xy(c["true"][:3], txy)
    st["gt_ok"] = None if txy == "none_xy" else match_xy(s["disp_gt"], txy)
    xy = np.array([c[f"xy:{d}"][:2] for d in DIR_XY8])
    st["sens_mm"] = float(1000 * np.mean(np.linalg.norm(xy - xy.mean(0), axis=1)))
    st["amp_mm"] = float(1000 * math.hypot(*c["true"][:2]))
    st["mse_true"], st["mse_pred"], st["mse_flip"] = c["true"][5], c["pred"][5], c["flip"][5]
    st["pred_is_label"] = all(s["preds"].get(q) == lab.get(q) for q in ("dir_xy", "dir_z", "mag_coarse"))
    st["lab_mag"] = lab["mag_coarse"]
    st["lab_xy_none"] = txy == "none_xy"
    if grip:
        diff = c["pid:open"][4] - c["pid:close"][4]
        st["grip_diff"] = float(diff)
        st["grip_hit"] = bool(diff >= GRIP_MIN - EPS)
        st["grip_rev"] = bool(diff <= -GRIP_MIN + EPS)
    return st


def pool(runs: list, idx) -> dict:
    """Aggregate over runs (lists of snap_stats aligned by position) and snapshot indices idx."""
    sel = [r[i] for r in runs for i in idx]
    sm = lambda k: float(sum(x[k] for x in sel))  # noqa: E731
    xp, zp = sm("xy_pairs"), sm("z_pairs")
    rho = [x["rho"] for x in sel if not math.isnan(x["rho"])]
    tr = [x["true_ok"] for x in sel if x["true_ok"] is not None]
    gt = [x["gt_ok"] for x in sel if x["gt_ok"] is not None]
    out = {"xy_pairs": int(xp), "a_xy": sm("xy_hits") / xp if xp else float("nan"),
           "chance_xy": sm("xy_chance") / xp if xp else float("nan"),
           "mean_cos_xy": sm("xy_cos") / xp if xp else float("nan"),
           "z_pairs": int(zp), "a_z": sm("z_hits") / zp if zp else float("nan"),
           "chance_z": sm("z_chance") / zp if zp else float("nan"),
           "rho_mean": float(np.mean(rho)) if rho else float("nan"), "rho_n": len(rho),
           "rho_perfect": float(np.mean([r > 1 - 1e-9 for r in rho])) if rho else float("nan"),
           "mag_ratio_median": float(np.median([x["mag_ratio"] for x in sel])),
           "true_rate": float(np.mean(tr)) if tr else float("nan"), "true_n": len(tr),
           "gt_rate": float(np.mean(gt)) if gt else float("nan"),
           "sens_mm_median": float(np.median([x["sens_mm"] for x in sel])),
           "amp_mm_median": float(np.median([x["amp_mm"] for x in sel])),
           "mse_true": float(np.mean([x["mse_true"] for x in sel])),
           "mse_pred": float(np.mean([x["mse_pred"] for x in sel])),
           "mse_flip": float(np.mean([x["mse_flip"] for x in sel])),
           "pred_is_label": float(np.mean([x["pred_is_label"] for x in sel])), "n_snap": len(sel)}
    out["mse_pred_rel"] = out["mse_pred"] / out["mse_true"] - 1
    out["mse_flip_rel"] = out["mse_flip"] / out["mse_true"] - 1
    if sel and "grip_diff" in sel[0]:
        out["grip_hit"] = float(np.mean([x["grip_hit"] for x in sel]))
        out["grip_rev"] = float(np.mean([x["grip_rev"] for x in sel]))
        out["grip_chance"] = (out["grip_hit"] + out["grip_rev"]) / 2
        out["grip_diff_median"] = float(np.median([x["grip_diff"] for x in sel]))
    return out


BOOT_METRICS = ("a_xy", "chance_xy", "mean_cos_xy", "a_z", "rho_mean")


def boot_ci(runs: list, n_boot: int = 10000, seed: int = 0) -> dict:
    """{metric: [2.5 %, 97.5 %]} of BOOT_METRICS; snapshots resampled with the same indices in every run (paired)."""
    arr = {k: np.array([[x[k] for x in r] for r in runs], float)
           for k in ("xy_pairs", "xy_hits", "xy_chance", "xy_cos", "z_pairs", "z_hits", "rho")}
    rng = np.random.default_rng(seed)
    n = arr["xy_pairs"].shape[1]
    v = {m: [] for m in BOOT_METRICS}
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        s = {k: a[:, idx] for k, a in arr.items()}
        xp, zp = s["xy_pairs"].sum(), s["z_pairs"].sum()
        v["a_xy"].append(s["xy_hits"].sum() / xp)
        v["chance_xy"].append(s["xy_chance"].sum() / xp)
        v["mean_cos_xy"].append(s["xy_cos"].sum() / xp)
        v["a_z"].append(s["z_hits"].sum() / zp if zp else np.nan)
        v["rho_mean"].append(np.nanmean(s["rho"]) if np.any(~np.isnan(s["rho"])) else np.nan)
    return {m: [float(np.nanquantile(x, 0.025)), float(np.nanquantile(x, 0.975))] for m, x in v.items()}


def decide(a_xy: dict, a_z: dict, rho: dict) -> dict:
    weak = {k: v < A_MIN - EPS for k, v in a_xy.items()}
    zlow = {k: v < A_MIN - EPS for k, v in a_z.items()}
    rlow = {k: v < RHO_MIN - EPS for k, v in rho.items()}
    if any(weak.values()):
        v = "WEAK"
    elif any(zlow.values()) or any(rlow.values()):
        v = "PARTIAL"
    else:
        v = "FOLLOWS"
    return {"verdict": v, "xy_below_0.6": weak, "z_below_0.6": zlow, "rho_below_0.5": rlow}


def load(path: str, n_expect: int, grip: bool) -> list:
    """'snap' records in file order; checks: summary present with n = n_expect = records, no 'skip', unique snapshot ids, every
    condition present, finite values."""
    want = set(cond_names(grip))
    snaps, summ, skips = [], None, 0
    for x in open(path, encoding="utf-8"):
        r = json.loads(x)
        ev = r.get("event")
        if ev == "summary":
            summ = r
        elif ev == "skip":
            skips += 1
        elif ev == "snap":
            snaps.append(r)
    keys = [s["id"] for s in snaps]  # the sample id: R2 stage-B keys repeat across folders (prereg §8 change 1)
    if summ is None or summ.get("n") != n_expect or len(snaps) != n_expect or skips:
        raise SystemExit(f"{path}: {len(snaps)} snaps, {skips} skips, summary n {summ and summ.get('n')} "
                         f"!= expected {n_expect}")
    if len(set(keys)) != len(keys):
        raise SystemExit(f"{path}: duplicate snapshot ids")
    for s in snaps:
        if set(s["c"]) != want:
            raise SystemExit(f"{path} {s['key']}: conditions {sorted(set(s['c']) ^ want)} differ")
        if not all(math.isfinite(v) for vals in s["c"].values() for v in vals) or \
                not all(math.isfinite(v) for v in s["disp_gt"]):
            raise SystemExit(f"{path} {s['key']}: non-finite value")
    return snaps


def breakdown(runs: list) -> dict:
    """Outside the rule: A_xy by label magnitude bin, by label none_xy / not, and per forced direction."""
    sel = [x for r in runs for x in r]
    out = {"by_label_mag": {}, "by_label_xy_none": {}, "by_forced_dir": {}}
    for m in MAGS:
        xs = [x for x in sel if x["lab_mag"] == m]
        p = sum(x["xy_pairs"] for x in xs)
        out["by_label_mag"][m] = {"n_snap": len(xs), "a_xy": sum(x["xy_hits"] for x in xs) / p if p else None}
    for b in (False, True):
        xs = [x for x in sel if x["lab_xy_none"] == b]
        p = sum(x["xy_pairs"] for x in xs)
        out["by_label_xy_none"][str(b)] = {"n_snap": len(xs), "a_xy": sum(x["xy_hits"] for x in xs) / p if p else None}
    for d in DIR_XY8:
        h = [x["by_dir"][d] for x in sel if d in x["by_dir"]]
        out["by_forced_dir"][d] = {"n": len(h), "a_xy": float(np.mean(h)) if h else None}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--se2e", nargs=2, required=True, help="motion_s1 and motion_s2 sr0_eval outputs")
    ap.add_argument("--n-se2e", type=int, default=1799)
    ap.add_argument("--r2", required=True, help="E-MA2 c0 sr0_eval output (--grip)")
    ap.add_argument("--n-r2", type=int, default=1200)
    ap.add_argument("--out", required=True)
    ap.add_argument("--boot", type=int, default=10000)
    a = ap.parse_args(argv)
    s1, s2 = (load(p, a.n_se2e, False) for p in a.se2e)
    if [x["id"] for x in s1] != [x["id"] for x in s2]:
        raise SystemExit("se2e: the two seeds are not on the same snapshots in the same order")
    r2 = load(a.r2, a.n_r2, True)
    st = {"se2e_s1": [snap_stats(x, False) for x in s1], "se2e_s2": [snap_stats(x, False) for x in s2],
          "r2_c0": [snap_stats(x, True) for x in r2]}
    runs = {"se2e": [st["se2e_s1"], st["se2e_s2"]], "r2": [st["r2_c0"]]}
    res = {k: pool(v, np.arange(len(v[0]))) for k, v in runs.items()}
    per_run = {k: pool([v], np.arange(len(v))) for k, v in st.items()}
    out = {"n": {"se2e": a.n_se2e, "r2": a.n_r2}, "inputs": {"se2e": a.se2e, "r2": a.r2}, "pooled": res,
           "per_run": per_run,
           **decide({k: r["a_xy"] for k, r in res.items()}, {k: r["a_z"] for k, r in res.items()},
                    {k: r["rho_mean"] for k, r in res.items()})}
    out["ci95"] = {k: boot_ci(v, a.boot, 0) for k, v in runs.items()}
    out["breakdown"] = {k: breakdown(v) for k, v in runs.items()}
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps({k: out[k] for k in ("verdict", "xy_below_0.6", "z_below_0.6", "rho_below_0.5")}, indent=1))


if __name__ == "__main__":
    main()
