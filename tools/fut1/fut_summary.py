"""E-FUT1 summary and verdict (prereg_fut1.md §5). Reads /data/harvest/out/fut1/arms/<arm>/eval/<set>/scores.jsonl.
  python tools/fut1/fut_summary.py --root /data/harvest/out/fut1 --best-eval /data/harvest/out/main35/eval/ep<best>
1. Delta curves (the E-DEP1 stage-1 rule, per model and evaluation set): action_acc / approach-or-carry xy median per
   delta, paired with delta 0 on the same call site (bootstrap 10,000 by site): SAFE / GRAY / NEEDS_ROWS, Delta*.
2. Arm X (on its runtime variant) vs F0 (on 'cur' = what the overlap runtime sends now), the same rows paired by
   (site, delta): A_X = action_acc difference pooled over delta 0.5 / 1 / 2 (%p, 95 % CI by site); xy median
   increase pooled (mm, 95 % CI); delta 0 difference.
3. Static non-inferiority vs F0: L8S validation action_acc and > 20 mm failure rate, G open validation hit (points),
   and the main35 judge (tools/final35/c35_judge.compare, E-C35 A/A margins, G without MolmoBot Franka).
4. Verdict: pass = P1 A_X >= +3 %p and CI low > 0; P2 Delta*(X) >= 1.0 s; P3 xy increase CI high <= 2 mm;
   P4 d1 delta-0 drop <= 1 %p, L8S val action_acc drop <= 1 %p, > 20 mm increase <= 1 %p, G val hit drop <= 1 %p,
   judge NONINFERIOR. Adopted = the passing arm with the largest A_X; within 1 %p the one with fewer changes
   (F1 < F2 < F4 < F3)."""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

DELTAS = (0.0, 0.5, 1.0, 2.0, 3.0)
POOL = (0.5, 1.0, 2.0)
ARMS = ("F0", "F1", "F2", "F3", "F4")
VAR = {"F0": "cur", "F1": "cur", "F2": "roll", "F3": "rt", "F4": "roll"}
SIMPLICITY = ("F1", "F2", "F4", "F3")
NB = 10000


def xy(s):
    v = s.get("approach_xy_mm")
    return v if v is not None else s.get("carry_xy_mm")


def load(root, arm, st):
    p = os.path.join(root, "arms", arm, "eval", st, "scores.jsonl")
    return {s["id"]: s for s in map(json.loads, open(p))} if os.path.exists(p) else None


def key_of(rid, rows):
    r = rows[rid]
    return (r["episode"], r["call"]), float(r["delta"])


def curve(sc, rows, rng):
    site = defaultdict(dict)
    for i, s in sc.items():
        if i in rows:
            k, d = key_of(i, rows)
            site[k][d] = s
    out = {"n_sites": len(site)}
    for d in DELTAS:
        pairs = [(v[0.0], v[d]) for v in site.values() if 0.0 in v and d in v]
        if not pairs:
            continue
        a0 = np.array([float(p[0]["action_ok"]) for p in pairs])
        ad = np.array([float(p[1]["action_ok"]) for p in pairs])
        xs = [(xy(p[0]), xy(p[1])) for p in pairs if xy(p[0]) is not None and xy(p[1]) is not None]
        x0, xd = np.array([u for u, _ in xs]), np.array([v for _, v in xs])
        n = len(pairs)
        dr = [(a0[k].mean() - ad[k].mean()) * 100 for k in (rng.integers(0, n, n) for _ in range(NB))]
        inc = [np.median(xd[k]) - np.median(x0[k]) for k in (rng.integers(0, len(xs), len(xs)) for _ in range(NB))] \
            if len(xs) else [np.nan]
        dl, dh = np.percentile(dr, [2.5, 97.5])
        il, ih = np.percentile(inc, [2.5, 97.5])
        v = "SAFE" if (dh <= 2 and ih <= 2) else ("NEEDS_ROWS" if (dl > 5 or il > 5) else "GRAY")
        out[str(d)] = {"n": n, "action_acc": round(float(ad.mean()), 4), "action_acc_d0": round(float(a0.mean()), 4),
                       "drop_pp": round(float(np.mean(dr)), 2), "drop_ci": [round(float(dl), 2), round(float(dh), 2)],
                       "xy_med_mm": round(float(np.median(xd)), 1) if len(xd) else None,
                       "xy_inc_ci": [round(float(il), 2), round(float(ih), 2)], "verdict": v}
    safe = [d for d in DELTAS if out.get(str(d), {}).get("verdict") == "SAFE"]
    out["delta_star"] = max(safe) if safe else None
    return out


def paired(sx, s0, rows, deltas, rng):
    """X vs F0 on the same (site, delta) rows: action_acc gain (%p) and xy median increase (mm), CIs by site."""
    by = defaultdict(list)
    for i, s in sx.items():
        j = i if i in s0 else None
        if j is None:
            continue
        k, d = key_of(i, rows)
        if d in deltas:
            by[k].append((s, s0[j]))
    keys = list(by)
    if not keys:
        return None
    gx = [np.array([float(a["action_ok"]) - float(b["action_ok"]) for a, b in by[k]]) for k in keys]
    xx = [[(xy(a), xy(b)) for a, b in by[k] if xy(a) is not None and xy(b) is not None] for k in keys]
    n = len(keys)
    g_all = np.concatenate(gx)
    gains, incs = [], []
    for _ in range(NB):
        k = rng.integers(0, n, n)
        gains.append(np.concatenate([gx[i] for i in k]).mean() * 100)
        pr = [p for i in k for p in xx[i]]
        if pr:
            incs.append(np.median([p[0] for p in pr]) - np.median([p[1] for p in pr]))
    return {"n_rows": int(len(g_all)), "n_sites": n, "gain_pp": round(float(g_all.mean() * 100), 2),
            "gain_ci": [round(float(x), 2) for x in np.percentile(gains, [2.5, 97.5])],
            "xy_inc_ci": [round(float(x), 2) for x in np.percentile(incs, [2.5, 97.5])] if incs else None}


def static(root, arm):
    d = os.path.join(root, "arms", arm, "eval")
    try:
        v = [json.loads(x) for x in open(os.path.join(d, "x_val_l8s_d-min_clean", "scores.jsonl"))]
        g = [json.loads(x) for x in open(os.path.join(d, "g_val_open", "scores.jsonl"))]
    except FileNotFoundError:
        return None
    e = [1e6 if r.get("approach_3d_mm") is None else float(r["approach_3d_mm"]) for r in v if r.get("approach_row")]
    return {"val_action_acc": round(float(np.mean([bool(r["action_ok"]) for r in v])), 4),
            "val_fail20": round(sum(x > 20.0 for x in e) / max(1, len(e)), 4),
            "val_open_hit": round(sum(bool(r.get("hit")) for r in g) / max(1, len(g)), 4)}


def judge(root, arm, out):
    """main35 judge rule (c35_judge.compare, G without MolmoBot Franka) X vs F0."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "final35"))
    import c35_judge as CJ  # noqa: PLC0415
    jr = os.path.join(out, "judge_root")
    os.makedirs(jr, exist_ok=True)
    c35 = "/data/harvest/out/c35"
    for name, tgt in ((arm, os.path.join(root, "arms", arm, "eval")), ("F0", os.path.join(root, "arms", "F0", "eval")),
                      ("best_b_s0", os.path.join(c35, "eval", "best_b_s0")),
                      ("best_b_s1", os.path.join(c35, "eval", "best_b_s1"))):
        p = os.path.join(jr, name)
        if os.path.islink(p):
            os.remove(p)
        os.symlink(tgt, p)
    grows = CJ.PC.jl("/data/harvest/out/opratio/g_eval.jsonl")
    sub = {r["id"]: CJ.PC.GSUB[r["gset"]] for r in grows}
    nf = [x for x in grows if sub[x["id"]] != "molmobot_franka"]
    r = CJ.compare(jr, [arm], ["F0"], nf, sub, CJ.gmargins(jr, nf, sub),
                   os.path.join(c35, "verdict", "aa_x_b.json"), os.path.join(out, f"judge_{arm}_vs_F0.json"))
    return {"verdict": r["verdict"], "worse": r["worse"]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/data/harvest/out/fut1")
    ap.add_argument("--no-judge", action="store_true")
    a = ap.parse_args(argv)
    rng = np.random.default_rng(0)
    rows = {}
    for v in ("cur", "roll", "rt"):
        for x in open(os.path.join(a.root, "data", f"eval_{v}.jsonl")):
            r = json.loads(x)
            rows[r["id"]] = r
    mm1 = {}
    for x in open("/data/harvest/out/deploy/mm1/rows.jsonl"):
        r = json.loads(x)
        mm1[r["id"]] = r
    out = os.path.join(a.root, "summary")
    os.makedirs(out, exist_ok=True)
    res = {"curves": {}, "vs_F0": {}, "static": {}, "judge": {}, "verdict": {}}
    arms_dir = os.path.join(a.root, "arms")
    for arm in sorted(os.listdir(arms_dir)):
        for st in ("mm_cur", "mm_roll", "mm_rt", "mm1"):
            sc = load(a.root, arm, st)
            if sc:
                res["curves"][f"{arm}/{st}"] = curve(sc, mm1 if st == "mm1" else rows, rng)
    s0 = load(a.root, "F0", "mm_cur")
    for arm in ARMS[1:] + ("F0",):
        v = VAR[arm]
        sx = load(a.root, arm, f"mm_{v}")
        if not sx or not s0:
            continue
        sx = {i[: -len(v)] + "cur": s for i, s in sx.items()}  # ids end with _<variant>
        res["vs_F0"][arm] = {"pool_0.5_1_2": paired(sx, s0, rows, POOL, rng), "delta0": paired(sx, s0, rows, (0.0,), rng),
                             **{f"d{d}": paired(sx, s0, rows, (d,), rng) for d in (0.5, 1.0, 2.0, 3.0)}}
    for arm in ARMS:
        res["static"][arm] = static(a.root, arm)
        if not a.no_judge and arm != "F0" and res["static"][arm] and res["static"].get("F0"):
            try:
                res["judge"][arm] = judge(a.root, arm, out)
            except Exception as ex:  # noqa: BLE001
                res["judge"][arm] = {"verdict": "ERROR", "error": repr(ex)[:300]}
    st0 = res["static"].get("F0")
    passing = {}
    for arm in ARMS[1:]:
        c = res["vs_F0"].get(arm, {})
        pool, d0 = c.get("pool_0.5_1_2"), c.get("delta0")
        cv = res["curves"].get(f"{arm}/mm_{VAR[arm]}", {})
        st = res["static"].get(arm)
        if not (pool and d0 and st and st0):
            res["verdict"][arm] = {"status": "INCOMPLETE"}
            continue
        chk = {"P1_future_gain": pool["gain_pp"] >= 3.0 and pool["gain_ci"][0] > 0,
               "P2_delta_star_ge_1s": (cv.get("delta_star") or 0) >= 1.0,
               "P3_xy_not_worse": pool["xy_inc_ci"] is not None and pool["xy_inc_ci"][1] <= 2.0,
               "P4a_d1_static": d0["gain_pp"] >= -1.0,
               "P4b_l8s_val_acc": (st["val_action_acc"] - st0["val_action_acc"]) * 100 >= -1.0,
               "P4c_l8s_val_fail20": (st["val_fail20"] - st0["val_fail20"]) * 100 <= 1.0,
               "P4d_g_val_hit": (st["val_open_hit"] - st0["val_open_hit"]) * 100 >= -1.0,
               "P4e_judge": res["judge"].get(arm, {}).get("verdict") == "NONINFERIOR"}
        ok = all(chk.values())
        res["verdict"][arm] = {"status": "PASS" if ok else "FAIL", **chk, "gain_pp": pool["gain_pp"]}
        if ok:
            passing[arm] = pool["gain_pp"]
    if passing:
        top = max(passing.values())
        near = [x for x in SIMPLICITY if x in passing and passing[x] >= top - 1.0]
        res["adopted"] = near[0]
    else:
        res["adopted"] = None
    json.dump(res, open(os.path.join(out, "summary_fut1.json"), "w"), indent=1)
    print(json.dumps({"adopted": res["adopted"], "verdict": res["verdict"],
                      "delta_star": {k: v.get("delta_star") for k, v in res["curves"].items()}}))


if __name__ == "__main__":
    main()
