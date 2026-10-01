"""E-JV1 summary and verdict (docs/stage3/prereg_jv1.md §5, §6; fixed at registration).
  python tools/jv1/summary.py --eval /data/harvest/out/jv1/eval --out /data/harvest/out/jv1/eval/summary.json
Jobs = <arm>_<cond>_<set>/<variant>/s<seed>/ (arm A / B / C, condition Z / R, set clean / dist, DEV seeds 0-19 x
standard / dr = 40 episodes per arm x condition x set). Paired bootstrap 10,000 over (variant, seed)."""
from __future__ import annotations

import argparse
import glob
import json
import os

import numpy as np

JOINT_STEP_MAX = 0.04
MARGIN = 0.10


def load_job(d):
    out = {}
    for ej in glob.glob(os.path.join(d, "*", "s*", "ep.json")):
        ed = os.path.dirname(ej)
        ep = json.load(open(ej))
        key = (ep["variant"], int(ep["seed"]))
        r = {"success": bool(ep["success"]), "failure": ep.get("failure"),
             "grip_fallback": (ep.get("exec_stats") or {}).get("grip_fallback"),
             "errors": (ep.get("exec_stats") or {}).get("errors"), "lat_p50_s": ep.get("lat_p50_s")}
        q, cmd = [], []
        for line in open(os.path.join(ed, "ticks.jsonl")):
            x = json.loads(line)
            q.append(x["q"])
            cmd.append(x["cmd"])
        q, cmd = np.asarray(q, float), np.asarray(cmd, float)
        if len(q) > 1:
            st = np.abs(np.diff(q, axis=0)).max(1)
            r.update(jstep_max=float(st.max()), jstep_p99=float(np.percentile(st, 99)),
                     jstep_viol=int((st > JOINT_STEP_MAX + 1e-6).sum()))
        if len(cmd) > 3:
            jerk = np.linalg.norm(np.diff(cmd, 3, axis=0), axis=1) / 0.05 ** 3
            r["jerk_p95"] = float(np.percentile(jerk, 95))
        sig = []
        for line in open(os.path.join(ed, "samples.jsonl")):
            s = json.loads(line)
            j = s.get("jcr") or {}
            if j.get("anomaly_p"):
                sig.append((float(j["anomaly_p"][-1]), bool(s.get("anomaly")), float(j.get("contact_p") or 0.0),
                            bool(s.get("contact"))))
        r["sig"] = sig
        out[key] = r
    return out


def auroc(p, y):
    p, y = np.asarray(p), np.asarray(y, bool)
    if y.all() or not y.any():
        return None
    o = np.argsort(p)
    rk = np.empty(len(p))
    rk[o] = np.arange(1, len(p) + 1)
    n1 = y.sum()
    return float((rk[y].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(y) - n1)))


def f1(p, y, thr=0.5):
    p, y = np.asarray(p) >= thr, np.asarray(y, bool)
    tp = int((p & y).sum())
    pr, rc = tp / max(int(p.sum()), 1), tp / max(int(y.sum()), 1)
    return 2 * pr * rc / max(pr + rc, 1e-9)


def stats(job):
    if not job:
        return None
    v = list(job.values())
    sig = [x for r in v for x in r["sig"]]
    g = lambda k, f: float(f([r[k] for r in v if r.get(k) is not None])) if any(r.get(k) is not None for r in v) else None  # noqa: E731
    return {"n": len(v), "success": sum(r["success"] for r in v), "rate": float(np.mean([r["success"] for r in v])),
            "grip_fallback": sum(r["grip_fallback"] or 0 for r in v), "errors": sum(r["errors"] or 0 for r in v),
            "lat_p50_s": g("lat_p50_s", np.median), "jstep_max": g("jstep_max", np.max),
            "jstep_viol_eps": sum((r.get("jstep_viol") or 0) > 0 for r in v), "jerk_p95_med": g("jerk_p95", np.median),
            "anomaly_auroc": auroc([x[0] for x in sig], [x[1] for x in sig]) if sig else None,
            "anomaly_f1": f1([x[0] for x in sig], [x[1] for x in sig]) if sig else None,
            "contact_f1": f1([x[2] for x in sig], [x[3] for x in sig]) if sig else None,
            "failures": sorted({r["failure"] for r in v if r["failure"]})}


def paired(a, b, n_boot=10000, seed=0):
    keys = sorted(set(a) & set(b))
    if not keys:
        return None
    d = np.array([float(b[k]["success"]) - float(a[k]["success"]) for k in keys])
    rng = np.random.default_rng(seed)
    bs = rng.choice(d, size=(n_boot, len(d)), replace=True).mean(1)
    return {"n": len(d), "diff": float(d.mean()), "lo": float(np.percentile(bs, 2.5)), "hi": float(np.percentile(bs, 97.5))}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    jobs = {os.path.basename(d): load_job(d) for d in sorted(glob.glob(os.path.join(a.eval, "[ABC]_[ZR]_*")))}
    res = {"arms": {k: stats(v) for k, v in jobs.items()}}
    pool = lambda arm, c: {(st,) + k: r for st in ("clean", "dist") for k, r in jobs.get(f"{arm}_{c}_{st}", {}).items()}  # noqa: E731
    res["pairs"] = {f"B-A_{c}_{st}": paired(jobs.get(f"A_{c}_{st}", {}), jobs.get(f"B_{c}_{st}", {}))
                    for c in ("Z", "R") for st in ("clean", "dist")}
    res["pairs"]["B-A_R_pooled"] = dR = paired(pool("A", "R"), pool("B", "R"))
    res["pairs"]["B-A_Z_pooled"] = dZ = paired(pool("A", "Z"), pool("B", "Z"))
    res["pairs"]["C-B_Z_pooled"] = paired(pool("B", "Z"), pool("C", "Z"))
    for f in ("lat", "sens"):
        for arm in "ABC":
            p = os.path.join(a.eval, f"{f}_{arm}.json")
            if os.path.exists(p):
                res[f"{f}_{arm}"] = json.load(open(p))
    za, zb = (res["arms"].get(f"{x}_Z_clean") or {} for x in "AB")
    verdict = "INCOMPLETE"
    if dR and dZ and dR["n"] >= 80 and dZ["n"] >= 80:
        if za.get("success", 99) <= 4 and zb.get("success", 99) <= 4:
            verdict = "BOTH_FLOOR"
        elif dR["diff"] >= MARGIN and dR["lo"] > 0 and dZ["lo"] > -MARGIN:
            verdict = "B_BETTER"
        elif dR["diff"] <= -MARGIN and dR["hi"] < 0 and dZ["hi"] < MARGIN:
            verdict = "A_BETTER"
        elif (dR["lo"] > 0 and dZ["hi"] < 0) or (dR["hi"] < 0 and dZ["lo"] > 0):
            verdict = "MIXED"
        else:
            verdict = "NO_DIFF"
    cz = res["arms"].get("C_Z_clean") or {}
    res["controller_limit"] = bool(cz) and cz.get("success", 40) < 30
    res["verdict"] = verdict
    json.dump(res, open(a.out, "w"), indent=1, default=str)
    print(json.dumps({"verdict": verdict, "R": dR, "Z": dZ, "controller_limit": res["controller_limit"]}))


if __name__ == "__main__":
    main()
