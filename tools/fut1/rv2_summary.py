"""E-FUT1 change 6 verdict: F2 vs F0 with two seeds pooled (prereg_fut1.md change 6).
seed 0 = the result-1 models on the whole held-out pool (arms F0rv / F2rv, rows data_rv); seed 1 = F0s1 / F2s1
(8,000 d1 rows, rows data_s1). Pooling: every (site, delta) pair of both seeds, bootstrap 10,000 by SITE (a site keeps
the pairs of both seeds), so the two seeds are not counted as independent sites.
  P1 pooled delta {0.5, 1, 2} action_acc gain F2 - F0 >= +3 pp and 95 % low > 0
  P2 Delta*(F2) >= 1.0 s: per delta, F2's drop vs its own delta 0 (pooled pairs) SAFE = drop high <= 2 pp and xy
     increase high <= 2 mm; Delta* = the largest SAFE delta (E-DEP1 rule)
  P3 pooled xy median increase (F2 - F0) 95 % high <= 2 mm
  P4a pooled delta-0 difference F2 - F0 >= -1 pp (point, as registered; CI reported)
  P4b-d mean over the two seeds of the static differences (L8S val acc >= -1 pp, > 20 mm <= +1 pp, G val hit >= -1 pp)
  P4e the main35 judge rule F2 vs F0 NONINFERIOR in both seeds
  python tools/fut1/rv2_summary.py --root /data/harvest/out/fut1"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fut_summary as S  # noqa: E402

NB = 10000
DELTAS = (0.0, 0.5, 1.0, 2.0, 3.0)


def rows_of(path):
    return {r["id"]: r for r in map(json.loads, open(path))}


def site_pairs(seeds, fn):
    """seeds: list of (rows, scores_a, scores_b) -> {site: [fn(row, a, b), ...]} over all seeds."""
    by = defaultdict(list)
    for rows, sa, sb in seeds:
        for i, a in sa.items():
            b = sb.get(i)
            if b is None or i not in rows:
                continue
            r = rows[i]
            v = fn(r, a, b)
            if v is not None:
                by[(r["episode"], r["call"])].append(v)
    return by


def boot_mean(by, rng):
    keys = list(by)
    vals = [np.asarray(by[k], float) for k in keys]
    allv = np.concatenate(vals)
    n = len(keys)
    bs = [np.concatenate([vals[i] for i in rng.integers(0, n, n)]).mean() for _ in range(NB)]
    return float(allv.mean()), [float(x) for x in np.percentile(bs, [2.5, 97.5])], int(len(allv)), n


def boot_median_inc(by, rng):
    """by[site] = [(x_new, x_ref), ...] -> median(x_new) - median(x_ref), CI by site."""
    keys = list(by)
    n = len(keys)
    if not n:
        return None
    est = np.median([p[0] for k in keys for p in by[k]]) - np.median([p[1] for k in keys for p in by[k]])
    bs = []
    for _ in range(NB):
        pr = [p for i in rng.integers(0, n, n) for p in by[keys[i]]]
        bs.append(np.median([p[0] for p in pr]) - np.median([p[1] for p in pr]))
    return float(est), [float(x) for x in np.percentile(bs, [2.5, 97.5])]


def judge_pair(root, x, y, out):
    """main35 judge rule x vs y (fut_summary.judge compares against 'F0'; here the reference is y)."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "final35"))
    import c35_judge as CJ  # noqa: PLC0415
    jr = os.path.join(out, f"judge_root_{x}")
    os.makedirs(jr, exist_ok=True)
    c35 = "/data/harvest/out/c35"
    for name, tgt in ((x, os.path.join(root, "arms", x, "eval")), (y, os.path.join(root, "arms", y, "eval")),
                      ("best_b_s0", os.path.join(c35, "eval", "best_b_s0")),
                      ("best_b_s1", os.path.join(c35, "eval", "best_b_s1"))):
        p = os.path.join(jr, name)
        if os.path.islink(p):
            os.remove(p)
        os.symlink(tgt, p)
    grows = CJ.PC.jl("/data/harvest/out/opratio/g_eval.jsonl")
    sub = {r["id"]: CJ.PC.GSUB[r["gset"]] for r in grows}
    nf = [g for g in grows if sub[g["id"]] != "molmobot_franka"]
    r = CJ.compare(jr, [x], [y], nf, sub, CJ.gmargins(jr, nf, sub), os.path.join(c35, "verdict", "aa_x_b.json"),
                   os.path.join(out, f"judge_{x}_vs_{y}.json"))
    return {"verdict": r["verdict"], "worse": r["worse"]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/data/harvest/out/fut1")
    a = ap.parse_args(argv)
    R = a.root
    rng = np.random.default_rng(0)
    seeds = []
    for tag, rdir, f0, f2 in (("s0", "data_rv", "F0rv", "F2rv"), ("s1", "data_s1", "F0s1", "F2s1")):
        rows = {**rows_of(os.path.join(R, rdir, "eval_cur.jsonl")), **rows_of(os.path.join(R, rdir, "eval_roll.jsonl"))}
        s0 = S.load(R, f0, "mm_cur")
        s2 = {i[: -len("roll")] + "cur": s for i, s in S.load(R, f2, "mm_roll").items()}
        seeds.append((tag, rows, s0, s2))
    out = {"per_seed": {}, "pooled": {}}

    def gain_fn(ds):
        def fn(r, x, y):
            return (float(x["action_ok"]) - float(y["action_ok"])) * 100 if float(r["delta"]) in ds else None
        return fn

    for name, ds in (("pool_0.5_1_2", (0.5, 1.0, 2.0)), ("d0", (0.0,)), ("d0.5", (0.5,)), ("d1", (1.0,)),
                     ("d2", (2.0,)), ("d3", (3.0,))):
        fn = gain_fn(ds)
        for tag, rows, s0, s2 in seeds:
            m, ci, nr, _ = boot_mean(site_pairs([(rows, s2, s0)], fn), rng)
            out["per_seed"].setdefault(tag, {})[name] = {"gain_pp": round(m, 2), "ci": [round(c, 2) for c in ci], "n": nr}
        m, ci, nr, ns = boot_mean(site_pairs([(rows, s2, s0) for _, rows, s0, s2 in seeds], fn), rng)
        out["pooled"][name] = {"gain_pp": round(m, 2), "ci": [round(c, 2) for c in ci], "n_rows": nr, "n_sites": ns}

    def fxy(r, x, y):
        if float(r["delta"]) in (0.5, 1.0, 2.0) and S.xy(x) is not None and S.xy(y) is not None:
            return (S.xy(x), S.xy(y))
        return None

    xyi = boot_median_inc(site_pairs([(rows, s2, s0) for _, rows, s0, s2 in seeds], fxy), rng)
    out["pooled"]["xy_inc"] = {"mm": round(xyi[0], 2), "ci": [round(c, 2) for c in xyi[1]]}
    curve = {}
    for d in DELTAS[1:]:
        acc, xyp = defaultdict(list), defaultdict(list)
        for _, rows, _, s2 in seeds:
            site = defaultdict(dict)
            for i, s in s2.items():
                if i in rows:
                    site[(rows[i]["episode"], rows[i]["call"])][float(rows[i]["delta"])] = s
            for k, v in site.items():
                if 0.0 in v and d in v:
                    acc[k].append((float(v[0.0]["action_ok"]) - float(v[d]["action_ok"])) * 100)
                    if S.xy(v[0.0]) is not None and S.xy(v[d]) is not None:
                        xyp[k].append((S.xy(v[d]), S.xy(v[0.0])))
        m, ci, nr, _ = boot_mean(acc, rng)
        xi = boot_median_inc(xyp, rng)
        safe = ci[1] <= 2 and (xi is None or xi[1][1] <= 2)
        need = ci[0] > 5 or (xi is not None and xi[1][0] > 5)
        curve[str(d)] = {"drop_pp": round(m, 2), "drop_ci": [round(c, 2) for c in ci], "n": nr,
                         "xy_inc_ci": [round(c, 2) for c in xi[1]] if xi else None,
                         "verdict": "SAFE" if safe else ("NEEDS_ROWS" if need else "GRAY")}
    safe = [float(d) for d, v in curve.items() if v["verdict"] == "SAFE"]
    out["F2_curve_pooled"] = curve
    out["delta_star"] = max(safe) if safe else 0.0
    st = {k: S.static(R, k) for k in ("F0", "F2", "F0s1", "F2s1")}

    def dif(key, x, y):
        return (st[x][key] - st[y][key]) * 100

    sm = {key: round((dif(key, "F2", "F0") + dif(key, "F2s1", "F0s1")) / 2, 2)
          for key in ("val_action_acc", "val_fail20", "val_open_hit")}
    r1 = json.load(open(os.path.join(R, "summary", "summary_fut1.json")))
    j1 = r1["judge"].get("F2", {}).get("verdict")
    od = os.path.join(R, "summary", "rv2")
    os.makedirs(od, exist_ok=True)
    try:
        js1 = judge_pair(R, "F2s1", "F0s1", od)
    except Exception as ex:  # noqa: BLE001
        js1 = {"verdict": "ERROR", "error": repr(ex)[:200]}
    out["static"] = {"per_arm": st, "mean_diff_pp": sm, "judge_s0": j1, "judge_s1": js1}
    p = out["pooled"]
    chk = {"P1_future_gain": p["pool_0.5_1_2"]["gain_pp"] >= 3 and p["pool_0.5_1_2"]["ci"][0] > 0,
           "P2_delta_star_ge_1s": out["delta_star"] >= 1.0,
           "P3_xy_not_worse": p["xy_inc"]["ci"][1] <= 2,
           "P4a_d1_static": p["d0"]["gain_pp"] >= -1.0,
           "P4b_l8s_val_acc": sm["val_action_acc"] >= -1, "P4c_l8s_val_fail20": sm["val_fail20"] <= 1,
           "P4d_g_val_hit": sm["val_open_hit"] >= -1,
           "P4e_judge": j1 == "NONINFERIOR" and js1.get("verdict") == "NONINFERIOR"}
    out["verdict_F2"] = {"status": "PASS" if all(chk.values()) else "FAIL", **chk}
    out["adopted"] = "F2" if all(chk.values()) else None
    json.dump(out, open(os.path.join(R, "summary", "summary_fut1_rv2.json"), "w"), indent=1)
    print(json.dumps({"adopted": out["adopted"], "verdict_F2": out["verdict_F2"], "P4a_d0_pooled": p["d0"],
                      "per_seed_d0": {t: v["d0"] for t, v in out["per_seed"].items()},
                      "d1": p["d1"], "d0.5": p["d0.5"], "delta_star": out["delta_star"],
                      "curve_1s": curve["1.0"], "static_mean_diff": sm}))


if __name__ == "__main__":
    main()
