"""Operation T fair head-to-head inputs (user-log 143/144): once the L8-X train set is frozen, build equal-budget
training files so T1+T4 and C' are compared under the same conditions (same base rows, same total T, same steps).

  h2h_base.jsonl   T base rows (L8-X only; the reference arm)
  h2h_t1t4.jsonl   T - N base rows + N T1+T4 rows (our robot family: RB2 T4-camera projected EE points (0-1000),
                   RB2 camera-info C', RB2 tracked points / traces; RB3 T4 rows when present)
  h2h_cp.jsonl     T - N base rows + N C' rows (MolmoBot Franka top-down C', DROID real Franka C', RoboTwin C',
                   RB2 camera-unknown C')
  h2h_ob.jsonl     prereg_open8 O-B on the new base: T - 3,250 base rows + 3,250 E-OPEN8 rows
  h2h_ob_clean     the same, E-OPEN8 rows with fallback names ('the object' / 'the target') removed first
The base rows removed are the SAME in h2h_t1t4 / h2h_cp (one stratified draw by `step`, seed 0), so the two arms
differ only in the added pack. Pack rows are L8-loader rows (kind 'aux', xprompt inline).
usage (pod): python -m xemb.prep_h2h BASE_TRAIN_JSONL OUT_DIR [N]
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

from .packs import _rows, _take, base_take, to_n1000
from .prep_open8_train import as_l8

T = 6521
X = "/data/harvest/out/xemb_proto"


def strat_take(rows, n, key="step", seed=0):
    """n rows drawn proportionally per `key` (largest remainder), random within a stratum; order = input order."""
    rng = np.random.default_rng(seed)
    groups = {}
    for i, r in enumerate(rows):
        groups.setdefault(r.get(key), []).append(i)
    ks = sorted(groups, key=str)
    quota = {k: n * len(groups[k]) / len(rows) for k in ks}
    take = {k: int(np.floor(quota[k])) for k in ks}
    for k in sorted(ks, key=lambda k: -(quota[k] - take[k]))[: n - sum(take.values())]:
        take[k] += 1
    keep = []
    for k in ks:
        keep += [groups[k][i] for i in rng.permutation(len(groups[k]))[: take[k]]]
    return [rows[i] for i in sorted(keep)]


def pack_t1t4(n, rng, x=X):
    s = [("rb2t4/records_P.jsonl", ["ee_point"], 0.45, True), ("rb2t4/records_C.jsonl", None, 0.35, False),
         ("rb2t4/records_P.jsonl", ["ee_point_detected", "ee_trace"], 0.20, True)]
    return _mix(s, n, rng, x, lambda r: "camera: unknown" not in r["prompt"])


def pack_cp(n, rng, x=X):
    s = [("mbfranka/records_C.jsonl", None, 0.35, False), ("droid/records_C.jsonl", None, 0.20, False),
         ("robotwin2/records_C.jsonl", None, 0.10, False), ("rb2t4/records_C.jsonl", None, 0.35, False)]
    return _mix(s, n, rng, x, lambda r: "rb2" not in r.get("source", "") or "camera: unknown" in r["prompt"])


def generic_name(r) -> bool:
    """Fallback names ('the object' / 'the target') when the source had no referral: the O-A leak row carried one."""
    return "the object" in r["answer"] or "the target" in r["answer"]


def alloc(sizes, fracs, n):
    """Quota per stream = round(n * frac), capped by the pool; the shortfall goes to streams with rows left, in order."""
    q = [min(s, int(round(n * f))) for s, f in zip(sizes, fracs)]
    q[-1] = min(sizes[-1], max(0, n - sum(q[:-1])))
    for j in range(len(q)):
        extra = min(sizes[j] - q[j], n - sum(q))
        q[j] += max(0, extra)
    return q


def _mix(spec, n, rng, x, keep):
    pools = [[r for r in _rows(os.path.join(x, path), kinds) if keep(r) and not generic_name(r)]
             for path, kinds, _, _ in spec]
    q = alloc([len(p) for p in pools], [s[2] for s in spec], n)
    out = []
    for (_, _, _, px), pool, k in zip(spec, pools, q):
        out += [as_l8(to_n1000(r) if px else r) for r in _take(pool, k, rng)]
    return out


def _write(path, rows, rng):
    with open(path, "w", encoding="utf-8") as f:
        for i in rng.permutation(len(rows)):
            f.write(json.dumps(rows[i]) + "\n")


def main(base_train, out, n=2000, open8="/data/harvest/out/xemb/open8/train_oa.jsonl"):
    os.makedirs(out, exist_ok=True)
    base = [json.loads(line) for line in open(base_train, encoding="utf-8")]
    base = strat_take(base, T) if len(base) > T else base
    kept = strat_take(base, base_take(T, [n]))
    rng = np.random.default_rng(0)
    t1t4, cp = pack_t1t4(n, rng), pack_cp(n, rng)
    oa = [json.loads(line) for line in open(open8, encoding="utf-8")]
    kept_ob = strat_take(base, base_take(T, [3250]))
    ob = kept_ob + _take(oa, 3250, rng)
    ob_clean = kept_ob + _take([r for r in oa if not generic_name(r)], 3250, rng)  # registered set minus fallback names
    arms = {"h2h_base": base, "h2h_t1t4": kept + t1t4, "h2h_cp": kept + cp, "h2h_ob": ob, "h2h_ob_clean": ob_clean}
    counts = {}
    for name, rows in arms.items():
        _write(os.path.join(out, name + ".jsonl"), rows, rng)
        counts[name] = {"rows": len(rows), "aux": sum(r.get("kind") == "aux" for r in rows)}
    counts["pack_n"] = n
    counts["base_train"] = base_train
    json.dump(counts, open(os.path.join(out, "counts.json"), "w"), indent=1)
    print(json.dumps(counts, indent=1))
    return counts


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], *(int(a) for a in sys.argv[3:4]))
