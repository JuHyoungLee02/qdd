"""E-SR1e design diagnostics D2-D4 on the existing E-SR1d evaluation files (CPU only, no model; docs/stage3/prereg_sr1e.md
§0.3). Outside any verdict: they choose the E-SR1e arms.

  D2  where the far-segment misses are: per forced-direction pair, miss = too small (|chunk xy| < 0.1 mm) or wrong
      direction (cos <= 0.5); cosine distribution; hit rate by label magnitude, by the proxy distance d, by stratum.
  D3  episode structure: per-episode far A_xy (C1, both seeds pooled) spread; A_xy of val episodes whose task text also
      occurs in a TRAIN episode vs not; by the number of TRAIN episodes with the same task; by dataset.
  D4  label / proxy noise: far A_xy by proxy sensitivity agreement (all alt strata agree vs not) and by 'holding'.

  python tools/sr1e/diag_val.py --logs /data/harvest/logs/sr1d --rows /data/harvest/data/se2e_c1/conv --out D.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import sys
from collections import defaultdict

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("sr0_verdict", os.path.join(_HERE, "..", "sr0", "sr0_verdict.py"))
V0 = importlib.util.module_from_spec(_spec)
sys.path.insert(0, os.path.join(_HERE, "..", "sr0"))
_spec.loader.exec_module(V0)


def snaps(path):
    return [json.loads(x) for x in open(path, encoding="utf-8") if '"event": "snap"' in x]


def ep_of(key):
    kind, ep, _ = key.split("_")
    return kind, int(ep[2:])


def pair_rows(s):
    """[(dir, hit, too_small, cos)] for the far forced-direction pairs of one snapshot."""
    out = []
    for d in V0.DIR_XY8:
        if d == s["labels"]["dir_xy"]:
            continue
        disp = s["c"][f"xy:{d}"][:3]
        n = math.hypot(disp[0], disp[1])
        out.append((d, bool(V0.match_xy(disp, d)), n < V0.MIN_DISP_M, float(V0.cos_xy(disp, V0.unit_xy(d))), n))
    return out


def rate(xs):
    return round(float(np.mean(xs)), 4) if len(xs) else None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", default="/data/harvest/logs/sr1d")
    ap.add_argument("--rows", default="/data/harvest/data/se2e_c1/conv")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    task, split = {}, {}
    for kind in ("RB1", "RB2"):
        for x in open(os.path.join(a.rows, f"{kind}.stageb.jsonl"), encoding="utf-8"):
            r = json.loads(x)
            task[(kind, r["seed"])] = r.get("task", "")
            split[(kind, r["seed"])] = r["split"]
    tr_tasks = defaultdict(int)
    for ep, t in task.items():
        if split[ep] == "train":
            tr_tasks[t] += 1
    out = {"n_train_eps": sum(1 for e in split if split[e] == "train"),
           "n_val_eps": sum(1 for e in split if split[e] == "val"),
           "n_train_tasks": len(tr_tasks)}
    for arm in ("c0", "c1"):
        runs = [snaps(os.path.join(a.logs, f"eval_{arm}_s{s}.jsonl")) for s in (1, 2)]
        far = [[s for s in r if s["stratum"] == "far"] for r in runs]
        rows = [(s, p) for r in far for s in r for p in pair_rows(s)]
        hits = [p[1] for _, p in rows]
        miss = [p for _, p in rows if not p[1]]
        res = {"pairs": len(rows), "a_xy": rate(hits),
               "miss_too_small": rate([p[2] for p in miss]), "miss_n": len(miss),
               "cos_q": {q: round(float(np.percentile([p[3] for _, p in rows], q)), 3) for q in (10, 25, 50, 75, 90)},
               "chunk_xy_mm_q": {q: round(1e3 * float(np.percentile([p[4] for _, p in rows], q)), 2)
                                 for q in (10, 50, 90)}}
        res["by_label_mag"] = {m: rate([p[1] for s, p in rows if s["labels"]["mag_coarse"] == m])
                               for m in sorted({s["labels"]["mag_coarse"] for s, _ in rows})}
        dq = np.quantile([s["d"] for s, _ in rows if s["d"] is not None], [0.25, 0.5, 0.75])
        bins = [-1, *dq, 1e9]
        res["by_d_quartile"] = {f"q{i + 1}": rate([p[1] for s, p in rows if s["d"] is not None
                                                   and bins[i] < s["d"] <= bins[i + 1]]) for i in range(4)}
        res["d_quartile_edges_m"] = [round(float(x), 4) for x in dq]
        res["by_holding"] = {str(h): rate([p[1] for s, p in rows if bool(s["holding"]) == h]) for h in (False, True)}
        agree = lambda s: all(v == "far" for v in (s.get("alt") or {}).values())  # noqa: E731
        res["by_alt_agree"] = {str(g): rate([p[1] for s, p in rows if agree(s) == g]) for g in (True, False)}
        res["by_alt_agree_n"] = {str(g): sum(1 for s, _ in rows if agree(s) == g) // 7 for g in (True, False)}
        # episodes (both seeds pooled)
        ep = defaultdict(list)
        for s, p in rows:
            ep[ep_of(s["key"])].append(p[1])
        ea = {e: float(np.mean(v)) for e, v in ep.items()}
        vals = np.array(list(ea.values()))
        res["episodes"] = {"n": len(ea), "q": {q: round(float(np.percentile(vals, q)), 3) for q in (10, 25, 50, 75, 90)},
                           "share_ge_0.8": rate(vals >= 0.8), "share_le_0.34": rate(vals <= 0.34)}
        seen = {e: tr_tasks.get(task[e], 0) for e in ea}
        res["task_seen"] = {"seen_eps": sum(1 for e in seen if seen[e] > 0), "unseen_eps": sum(1 for e in seen if seen[e] == 0),
                            "a_xy_seen": rate([p[1] for s, p in rows if seen[ep_of(s["key"])] > 0]),
                            "a_xy_unseen": rate([p[1] for s, p in rows if seen[ep_of(s["key"])] == 0])}
        grp = {"0": lambda n: n == 0, "1-4": lambda n: 1 <= n <= 4, "5-19": lambda n: 5 <= n <= 19,
               ">=20": lambda n: n >= 20}
        res["by_task_train_eps"] = {g: {"n_eps": sum(1 for e in seen if f(seen[e])),
                                        "a_xy": rate([p[1] for s, p in rows if f(seen[ep_of(s["key"])])])}
                                    for g, f in grp.items()}
        res["by_kind"] = {k: rate([p[1] for s, p in rows if s["key"].startswith(k)]) for k in ("RB1", "RB2")}
        # seed agreement per snapshot (is a snapshot's success reproducible across seeds?)
        if arm == "c1":
            by = [{s["key"]: np.mean([p[1] for p in pair_rows(s)]) for s in r} for r in far]
            ks = sorted(set(by[0]) & set(by[1]))
            res["seed_corr_snapshot"] = round(float(np.corrcoef([by[0][k] for k in ks], [by[1][k] for k in ks])[0, 1]), 3)
        out[arm] = res
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
