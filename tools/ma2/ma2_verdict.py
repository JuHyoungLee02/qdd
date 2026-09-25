"""E-MA2 verdict (docs/stage3/prereg_ma2.md §6, fixed before training; not edited after results).

  python tools/ma2/ma2_verdict.py --eval-set JSON --c0 JSONL --c1 JSONL --c2 JSONL --latency JSON --out JSON

Compliance of a model = over (snapshot, rotation in {e90, e180}) pairs whose true command has |xy| >= 1 cm and whose
rotated command's dir_xy bin (labels_v2 rule) is not none_xy: predicted dir_xy == that bin AND cos(xy of the chunk's
FK fingertip displacement, command xy) > 0.5. c0 (no command input) is scored on its 'none' record (reference).
No-command accuracy = all decision items of the 'none' records vs labels_v2 targets.
Rule (CMP_EPS 1e-12):
  NONE if compliance(c1) < 0.6 and compliance(c2) < 0.6            (VLA does not see commands; §11 code offset only)
  C2   elif comp(c2) - comp(c1) >= +0.10 and acc(c2) - acc(c0) >= -0.01 and FULL p95(c2) / FULL p95(c1) - 1 <= 0.10
  C1   elif comp(c1) >= 0.6 and acc(c1) - acc(c0) >= -0.01 and FULL p95(c1) / FULL p95(c0) - 1 <= 0.10
  NONE otherwise
Bootstrap (outside the rule): snapshots resampled 10,000 times (seed 0), 95 % percentile intervals.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

import numpy as np  # noqa: E402

EPS = 1e-12
ROTS = ("e90", "e180")
MIN_XY_M = 0.01


def dir_xy_bin(c) -> str:
    from harvest.labels_v2 import dir_xy_label
    return dir_xy_label(c)


def cos_xy(a, b) -> float:
    na, nb = math.hypot(a[0], a[1]), math.hypot(b[0], b[1])
    if na < 1e-9 or nb < 1e-9:
        return -2.0
    return (a[0] * b[0] + a[1] * b[1]) / (na * nb)


def load(path: str, ids: list, cond: str) -> dict:
    """{(id, cond): record}; checks: every eval id x expected condition exactly once, nothing else."""
    want = ["none"] + (["e0", "e90", "e180"] if cond in ("c1", "c2") else [])
    recs, summ = {}, None
    for x in open(path, encoding="utf-8"):
        r = json.loads(x)
        if r.get("event") == "summary":
            summ = r
            continue
        key = (r["id"], r["cond"])
        if key in recs:
            raise SystemExit(f"{path}: duplicate {key}")
        recs[key] = r
    exp = {(i, c) for i in ids for c in want}
    if set(recs) != exp or summ is None or summ.get("ma2") != cond:
        raise SystemExit(f"{path}: records {len(recs)} != expected {len(exp)} or summary missing / wrong cond")
    return recs


def per_snapshot(recs: dict, ids: list, cond: str):
    """Arrays over ids: items correct / items (none), and per rotation (eligible, complied)."""
    from harvest.train.r2_ma2 import eval_cmd
    corr, n_it = np.zeros(len(ids)), np.zeros(len(ids))
    el = {r: np.zeros(len(ids), bool) for r in ROTS + ("e0",)}
    ok = {r: np.zeros(len(ids), bool) for r in ROTS + ("e0",)}
    rot = {"e0": 0, "e90": 90, "e180": 180}
    for j, i in enumerate(ids):
        base = recs[(i, "none")]
        for q, tg in base["targets"].items():
            n_it[j] += 1
            corr[j] += base["preds"].get(q) in tg
        tc = np.asarray(base["true_cmd"], float)
        for r in el:
            c = eval_cmd(tc, rot[r])
            b = dir_xy_bin(c)
            if math.hypot(tc[0], tc[1]) < MIN_XY_M or b == "none_xy":
                continue
            el[r][j] = True
            rec = base if cond == "c0" else recs[(i, r)]
            if cond != "c0" and np.max(np.abs(np.asarray(rec["cmd"]) - c)) > 1e-5:
                raise SystemExit(f"{i} {r}: recorded command {rec['cmd']} != {c.tolist()}")
            ok[r][j] = rec["preds"].get("dir_xy") == b and cos_xy(rec["disp"], c) > 0.5
    return corr, n_it, el, ok


def compliance(el, ok, idx=None, rots=ROTS) -> float:
    idx = np.arange(len(el[rots[0]])) if idx is None else idx
    e = sum(el[r][idx].sum() for r in rots)
    return float(sum(ok[r][idx].sum() for r in rots) / e) if e else float("nan")


def decide(comp: dict, acc: dict, lat: dict) -> dict:
    """comp / acc / lat: {c0|c1|c2: value}; lat = FULL p95 seconds."""
    d21, a20, a10 = comp["c2"] - comp["c1"], acc["c2"] - acc["c0"], acc["c1"] - acc["c0"]
    l21, l10 = lat["c2"] / lat["c1"] - 1, lat["c1"] / lat["c0"] - 1
    low = comp["c1"] < 0.6 - EPS and comp["c2"] < 0.6 - EPS
    c2 = {"comp_diff": d21 >= 0.10 - EPS, "acc_c2_c0": a20 >= -0.01 - EPS, "lat_c2_c1": l21 <= 0.10 + EPS}
    c1 = {"comp_c1": comp["c1"] >= 0.6 - EPS, "acc_c1_c0": a10 >= -0.01 - EPS, "lat_c1_c0": l10 <= 0.10 + EPS}
    if low:
        v = "NONE"
    elif all(c2.values()):
        v = "C2"
    elif all(c1.values()):
        v = "C1"
    else:
        v = "NONE"
    return {"verdict": v, "both_below_0.6": low, "c2_conditions": c2, "c1_conditions": c1,
            "comp_c2_minus_c1": d21, "acc_c2_minus_c0": a20, "acc_c1_minus_c0": a10,
            "full_p95_c2_over_c1_minus_1": l21, "full_p95_c1_over_c0_minus_1": l10}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-set", required=True)
    for c in ("c0", "c1", "c2"):
        ap.add_argument(f"--{c}", required=True)
    ap.add_argument("--latency", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--boot", type=int, default=10000)
    a = ap.parse_args(argv)
    es = json.load(open(a.eval_set))
    ids = es["ids"]
    if len(set(ids)) != len(ids):
        raise SystemExit("eval set has duplicates")
    ps = {c: per_snapshot(load(getattr(a, c), ids, c), ids, c) for c in ("c0", "c1", "c2")}
    acc = {c: float(p[0].sum() / p[1].sum()) for c, p in ps.items()}
    comp = {c: compliance(p[2], p[3]) for c, p in ps.items()}
    lj = json.load(open(a.latency))
    lat = {c: lj["formats"][c]["full_p95"] for c in ("c0", "c1", "c2")}
    out = {"n_snapshots": len(ids), "eval_set_sha": es.get("sha"), "acc_none": acc, "compliance": comp,
           "full_p95_s": lat, **decide(comp, acc, lat)}
    out["eligible_pairs"] = {r: int(ps["c1"][2][r].sum()) for r in ROTS + ("e0",)}
    out["compliance_by_rot"] = {c: {r: compliance(p[2], p[3], rots=(r,)) for r in ROTS + ("e0",)}
                                for c, p in ps.items()}
    rng = np.random.default_rng(0)
    bd, ba2, ba1 = [], [], []
    for _ in range(a.boot):
        idx = rng.integers(0, len(ids), len(ids))
        bd.append(compliance(ps["c2"][2], ps["c2"][3], idx) - compliance(ps["c1"][2], ps["c1"][3], idx))
        acc_b = {c: p[0][idx].sum() / p[1][idx].sum() for c, p in ps.items()}
        ba2.append(acc_b["c2"] - acc_b["c0"])
        ba1.append(acc_b["c1"] - acc_b["c0"])
    ci = lambda x: [float(np.nanquantile(x, 0.025)), float(np.nanquantile(x, 0.975))]  # noqa: E731
    out["ci95"] = {"comp_c2_minus_c1": ci(bd), "acc_c2_minus_c0": ci(ba2), "acc_c1_minus_c0": ci(ba1)}
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
