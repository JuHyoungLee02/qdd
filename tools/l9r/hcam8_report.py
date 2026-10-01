"""E-HCAM8 per-arm report (pure; pod venv python): per seed and pooled, for every evaluated set: approach 3D error
median and > 20 mm failure rate (approach rows; an invalid answer counts as a failure), G hit rates per subset; and
the A/A widths of the H0 seed pairs (0 vs 1, 2 vs 3: half width of the 95 % paired-bootstrap interval of the
median difference and of the failure-rate difference, prereg §5).
usage: python tools/l9r/hcam8_report.py <eval root> <arm> [--out file.json]"""
import glob
import json
import os
import sys

import numpy as np

FAIL_MM = 20.0


def scores(path):
    out = {}
    for x in open(path):
        r = json.loads(x)
        if not r.get("approach_row"):
            continue
        v = r.get("approach_3d_mm")
        out[r["id"]] = float("inf") if (v is None or not r.get("valid")) else float(v)
    return out


def stats(v):
    a = np.asarray(list(v), float)
    fin = a[np.isfinite(a)]
    return {"n": int(len(a)), "median_mm": round(float(np.median(np.where(np.isfinite(a), a, 1e9))), 2) if len(a) else None,
            "fail20": round(float(np.mean(a > FAIL_MM)), 4) if len(a) else None,
            "invalid": int(len(a) - len(fin))}


def aa(x, y, reps=2000, seed=0):
    ids = sorted(set(x) & set(y))
    if len(ids) < 20:
        return None
    a = np.array([x[i] for i in ids]); b = np.array([y[i] for i in ids])
    a = np.where(np.isfinite(a), a, 1e4); b = np.where(np.isfinite(b), b, 1e4)
    rng = np.random.default_rng(seed)
    dm, df = [], []
    for _ in range(reps):
        k = rng.integers(0, len(ids), len(ids))
        dm.append(np.median(a[k]) - np.median(b[k]))
        df.append(np.mean(a[k] > FAIL_MM) - np.mean(b[k] > FAIL_MM))
    return {"n": len(ids), "aa_med_mm": round(float(np.diff(np.percentile(dm, [2.5, 97.5]))[0] / 2), 2),
            "aa_fail_pp": round(100 * float(np.diff(np.percentile(df, [2.5, 97.5]))[0] / 2), 2)}


def main():
    root, arm = sys.argv[1], sys.argv[2]
    runs = sorted(d for d in glob.glob(os.path.join(root, f"{arm}_s*")) if os.path.exists(os.path.join(d, "EVAL_DONE")))
    sets = sorted({os.path.basename(os.path.dirname(p)) for d in runs for p in glob.glob(os.path.join(d, "*", "scores.jsonl"))})
    rep = {"arm": arm, "seeds": [os.path.basename(d) for d in runs], "sets": {}, "g": {}, "aa": {}}
    per = {}
    for s in sets:
        rep["sets"][s] = {}
        pooled = []
        for d in runs:
            p = os.path.join(d, s, "scores.jsonl")
            if not os.path.exists(p):
                continue
            sc = scores(p)
            per[(os.path.basename(d), s)] = sc
            rep["sets"][s][os.path.basename(d)] = stats(sc.values())
            pooled += list(sc.values())
        rep["sets"][s]["pooled"] = stats(pooled)
    for d in runs:
        g = os.path.join(d, "g", "summary.json")
        if os.path.exists(g):
            rep["g"][os.path.basename(d)] = json.load(open(g))
    if arm == "H0":
        for s in sets:
            rep["aa"][s] = {f"{a}-{b}": aa(per.get((f"H0_s{a}", s), {}), per.get((f"H0_s{b}", s), {}))
                            for a, b in ((0, 1), (2, 3))}
    txt = json.dumps(rep, indent=1)
    if "--out" in sys.argv:
        open(sys.argv[sys.argv.index("--out") + 1], "w").write(txt)
    print(txt)


if __name__ == "__main__":
    main()
