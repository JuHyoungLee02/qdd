"""Envelope-rule sweep, stage 1 (offline, kinematic; prereg_jcr1.md change 3). No Isaac, no model: the TCP follows the
commanded rows exactly and JCR is replaced by its truth label 'P' (straight to the true point) -- the RULE's ceiling.
Segments = recorded point commands of JCR data (cmds.jsonl + the first sample of each command: commanded TCP, velocity,
true point, received destination, adapter kappa, height). Fast validation set: HARD 70 % (|true - destination| > 1 cm,
or a disturbed / failed episode) + EASY 30 %, fixed seed.
Configs: blend rho {2,3,5,7} cm x w_min {0,.1,.2,.3} x shape {gauss, p4} x A {5,10,15} cm x w_max {.5,.7,.9}
(w_max: see truth.PRIO note) + hard-clip baselines {1,2,3} cm.
Per segment and config:
  TA1 / TA2   end point within 1 / 2 cm of the upper's destination (authority)
  OK          end point at the true point (grasp / place heights 8 mm, else 15 mm) -- task success proxy
  ALIGNED     OK and TA2 (primary);  ALIGNED1 = OK and TA1
  SENS        destination moved 5 cm (horizontal, fixed random direction), true point fixed: |end' - end| / 5 cm
  CS          executed rows within speed V_BLEND and acceleration 1.05 A_MAX
  T_RET       JCR detours toward destination + 8 cm for 1 s, then back to the truth: s until within 1 cm of the
              undisturbed end point (capped at 6 s)
Adoption (prereg): a blend config is adoptable when ALIGNED > the best hard-clip baseline's ALIGNED and mean SENS >= 0.9.
  python tools/jcr/rule_sweep.py --data /data/harvest/out/jcr/d1 --out /data/harvest/out/jcr/sweep1 [--n 300 --procs 4]"""
from __future__ import annotations

import argparse
import glob
import itertools
import json
import os
import sys
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from harvest.jcr import truth as T  # noqa: E402

T_MAX = 6.0
SHIFT_M = 0.05
DETOUR_M, DETOUR_S = 0.08, 1.0


def configs():
    out = [{"kind": "clip", "r": r} for r in (0.01, 0.02, 0.03)]
    for rho, wm, shape, A, wx in itertools.product((0.02, 0.03, 0.05, 0.07), (0.0, 0.1, 0.2, 0.3), ("gauss", "p4"),
                                                   (0.05, 0.10, 0.15), (0.5, 0.7, 0.9)):
        out.append({"kind": "blend", "shape": shape, "rho": rho, "w_min": wm, "A": A, "w_max": wx,
                    "eps": T.PRIO["eps"], "t_ramp": T.PRIO["t_ramp"]})
    return out


def segments(root, n, seed=0):
    segs = []
    for ej in sorted(glob.glob(os.path.join(root, "*", "s*", "ep.json"))):
        d = os.path.dirname(ej)
        ep = json.load(open(ej))
        hard_ep = (not ep["plan"]["normal"]) or (not ep["success"])
        sp = os.path.join(d, "samples_r3.jsonl")
        ss = [json.loads(x) for x in open(sp if os.path.exists(sp) else os.path.join(d, "samples.jsonl"))]
        seen = set()
        for s in ss:
            key = tuple(np.round(s["goal_cmd"], 4))
            if key in seen or s.get("role") not in ("approach", "carry") or s.get("stop"):
                continue
            seen.add(key)
            err = float(np.linalg.norm(np.asarray(s["goal_true"]) - s["goal_cmd"]))
            segs.append({"p0": s["p_cmd"], "v0": s["v"], "pt": s["goal_true"], "g": s["goal_cmd"],
                         "kappa": float(s.get("kappa", 0.9)), "height": s.get("height", "above"),
                         "hard": bool(err > 0.01 or hard_ep), "err_mm": round(err * 1e3, 1),
                         "src": f"{os.path.basename(os.path.dirname(d))}/{os.path.basename(d)}"})
    rng = np.random.default_rng(seed)
    hard = [x for x in segs if x["hard"]]
    easy = [x for x in segs if not x["hard"]]
    nh = min(len(hard), int(round(0.7 * n)))
    ne = min(len(easy), n - nh)
    pick = [hard[i] for i in rng.choice(len(hard), nh, replace=False)] + \
        [easy[i] for i in rng.choice(len(easy), ne, replace=False)]
    for i, x in enumerate(pick):
        a = rng.uniform(0, 2 * np.pi)
        x["shift"] = [SHIFT_M * np.cos(a), SHIFT_M * np.sin(a), 0.0]
        b = rng.uniform(0, 2 * np.pi)
        x["detour"] = [DETOUR_M * np.cos(b), DETOUR_M * np.sin(b), 0.0]
    return pick, {"all": len(segs), "hard": len(hard), "easy": len(easy), "picked_hard": nh, "picked_easy": ne}


def rows_of(cfg, x, v, pt, g, kappa, age, jcr_target=None):
    if cfg["kind"] == "clip":
        return T.mode_chunk("A", x, v, pt, g, r=cfg["r"])
    P = T.smooth_chunk(x, v, pt if jcr_target is None else jcr_target)[0]
    return T.blend_rows(x, v, P, g, cfg, kappa, age)


def rollout(cfg, sg, g=None, detour=None):
    x, v = np.asarray(sg["p0"], float), np.asarray(sg["v0"], float)
    g = np.asarray(sg["g"] if g is None else g, float)
    pt = np.asarray(sg["pt"], float)
    path, t = [x], 0.0
    while t < T_MAX - 1e-9:
        jt = (g + np.asarray(detour, float)) if (detour is not None and t < DETOUR_S) else None
        R = rows_of(cfg, x, v, pt, g, sg["kappa"], t, jt)
        path += list(R[:4])
        v = (R[3] - R[2]) / T.DT
        x = R[3]
        t += 4 * T.DT
        if detour is None and np.linalg.norm(R[-1] - R[-2]) < 1e-5 and np.linalg.norm(x - R[-1]) < 1e-4:
            break
    return np.array(path)


def eval_cfg(args):
    cfg, segs = args
    rec = {k: [] for k in ("ta1", "ta2", "ok", "al", "al1", "sens", "cs", "tret", "end_g_mm", "end_t_mm")}
    for sg in segs:
        g, pt = np.asarray(sg["g"]), np.asarray(sg["pt"])
        P = rollout(cfg, sg)
        e = P[-1]
        vel = np.diff(P, axis=0) / T.DT
        acc = np.diff(vel, axis=0) / T.DT
        tol = 0.008 if sg["height"] in ("grasp", "place") else 0.015
        dg, dt_ = float(np.linalg.norm(e - g)), float(np.linalg.norm(e - pt))
        ok = dt_ <= tol
        rec["ta1"].append(dg <= 0.01)
        rec["ta2"].append(dg <= 0.02)
        rec["ok"].append(ok)
        rec["al"].append(ok and dg <= 0.02)
        rec["al1"].append(ok and dg <= 0.01)
        rec["end_g_mm"].append(dg * 1e3)
        rec["end_t_mm"].append(dt_ * 1e3)
        rec["cs"].append(bool(np.linalg.norm(vel, axis=1).max(initial=0) <= T.V_BLEND + 1e-6 and
                              np.linalg.norm(acc, axis=1).max(initial=0) <= 1.05 * T.A_MAX))
        e2 = rollout(cfg, sg, g=g + np.asarray(sg["shift"]))[-1]
        rec["sens"].append(float(np.linalg.norm(e2 - e)) / SHIFT_M)
        D = rollout(cfg, sg, detour=sg["detour"])
        k0 = int(round(DETOUR_S / T.DT))
        back = np.nonzero(np.linalg.norm(D[k0:] - e, axis=1) < 0.01)[0]
        rec["tret"].append(float(back[0] * T.DT) if len(back) else T_MAX)
    hard = np.array([s["hard"] for s in segs])
    out = {"cfg": cfg}
    for k, v in rec.items():
        v = np.asarray(v, float)
        out[k] = round(float(v.mean()), 4)
        if k in ("al", "ok", "ta2"):
            out[k + "_hard"] = round(float(v[hard].mean()), 4) if hard.any() else None
            out[k + "_easy"] = round(float(v[~hard].mean()), 4) if (~hard).any() else None
    out["sens_p10"] = round(float(np.percentile(rec["sens"], 10)), 3)
    out["tret_p50"] = round(float(np.median(rec["tret"])), 3)
    return out


def pareto(rows, a="ta2", b="ok"):
    keep = []
    for r in rows:
        if not any((o[a] >= r[a] and o[b] >= r[b]) and (o[a] > r[a] or o[b] > r[b]) for o in rows):
            keep.append(r)
    return keep


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", action="append", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--limit-cfg", type=int, default=0, help="smoke: first k blend configs only")
    a = ap.parse_args(argv)
    segs, info = [], {}
    for r in a.data:
        s, i = segments(r, a.n, a.seed)
        segs += s
        info[r] = i
    cfgs = configs()
    if a.limit_cfg:
        cfgs = cfgs[:3 + a.limit_cfg]
    with Pool(a.procs) as pool:
        res = pool.map(eval_cfg, [(c, segs) for c in cfgs])
    base = max((r for r in res if r["cfg"]["kind"] == "clip"), key=lambda r: r["al"])
    for r in res:
        r["adoptable"] = bool(r["cfg"]["kind"] == "blend" and r["al"] > base["al"] and r["sens"] >= 0.9)
    os.makedirs(a.out, exist_ok=True)
    summ = {"segments": info, "n_segments": len(segs), "n_cfgs": len(cfgs), "best_clip": base,
            "adoptable": sorted([r for r in res if r["adoptable"]], key=lambda r: -r["al"])[:10],
            "pareto_ta2_ok": sorted(pareto(res), key=lambda r: -r["ta2"]),
            "clip": [r for r in res if r["cfg"]["kind"] == "clip"]}
    json.dump(res, open(os.path.join(a.out, "all.json"), "w"))
    json.dump(summ, open(os.path.join(a.out, "summary.json"), "w"), indent=1)
    print(json.dumps({"n_segments": len(segs), "info": info, "best_clip": {k: base[k] for k in ("cfg", "al", "ta2", "ok", "sens")},
                      "n_adoptable": sum(r["adoptable"] for r in res),
                      "top": [{k: r[k] for k in ("cfg", "al", "ta2", "ok", "sens", "tret_p50", "cs")}
                              for r in summ["adoptable"][:3]]}))


if __name__ == "__main__":
    main()
