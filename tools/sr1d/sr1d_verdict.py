"""E-SR1d verdict (docs/stage3/prereg_sr1d.md §4, fixed before the main runs; not edited after results).

  python tools/sr1d/sr1d_verdict.py --c0 C0_S1.jsonl C0_S2.jsonl --c1 C1_S1.jsonl C1_S2.jsonl [--mode far|all] \
      --n 1799 --out verdict.json [--boot 10000]

Per snapshot = tools/sr0/sr0_verdict.snap_stats (grip=False; imported, not modified) + the authority-proxy stratum,
plausible-edit hits (edit:theta: chunk xy >= 0.1 mm and cos(chunk xy, edit vector) > 0.5; plausible = +-30 / +-45 deg,
stress = +-90 / 180 deg), true-chunk end-point FK error, decision accuracy (prediction = label, 3 questions),
gripper-event proxy (recorded chunk openness change |r| >= 0.1: hit = the true-decision chunk changes the same way by
>= 0.1), counterfactual floor proxy (xy:<d> chunks, d != label: ee_z + dzmin < floor_z - 2 mm).
Strata (mode far): far = proxy a 1, near = proxy a 0, band, unknown (no gripper event of that arm). Mode all (the
registered fallback): the primary set = every snapshot, near = the contact proxy (gripper moving or within 0.3 s of
an event).
Every metric of an arm = the mean of its two seeds' values (C0 = motion_s1 / motion_s2, C1 = seed 1 / 2).
Rule (CMP_EPS 1e-12):
  far       A_xy(primary set) >= 0.80, and each seed >= 0.75
  N1        near mean normalized MSE of the true-decision chunk <= C0 x 1.05
  N2        near median true-chunk end-point FK error <= C0 x 1.10
  N3        near gripper-event hit >= C0 - 0.02
  N4        near decision accuracy (3 questions) >= C0 - 0.01
  N5        near true-decision direction hit (label != none) >= C0 - 0.02
  i         whole-range true-decision direction hit >= C0 - 0.02
  ii        whole-range counterfactual floor-proxy rate <= C0 + 0.02
  iii       whole-range decision accuracy (3 questions, no command) >= C0 - 0.01
  iv        chunk-path p95 latency <= C0 + 10 ms
  ADOPT = all; grade FULL if A_z >= 0.80 and rho >= 0.5 on the primary set, else XY; far passes but an N fails ->
  NEAR_BLEED; far passes, N pass, i-iv fail -> NOT_ADOPTED; far fails -> NOT_REACHED.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "sr0"))
_spec = importlib.util.spec_from_file_location("sr0_verdict", os.path.join(_HERE, "..", "sr0", "sr0_verdict.py"))
V0 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V0)

EPS = 1e-12
FAR_MIN, SEED_MIN = 0.80, 0.75
PEN_M = 0.002
GRIP_MIN = 0.1
PLAUSIBLE, STRESS = (30, -30, 45, -45), (90, -90, 180)
QS = ("dir_xy", "dir_z", "mag_coarse")
STRATA = ("far", "band", "near", "unknown")
EDITS = (30, -30, 45, -45, 90, -90, 180)


def cos2(d, e) -> float:
    n, m = math.hypot(d[0], d[1]), math.hypot(e[0], e[1])
    return 0.0 if n < V0.MIN_DISP_M or m == 0 else (d[0] * e[0] + d[1] * e[1]) / (n * m)


def snap_stats(s: dict) -> dict:
    st = V0.snap_stats(s, grip=False)
    c, lab = s["c"], s["labels"]
    st.update(stratum=s["stratum"], contact=bool(s["contact"]), kind=s["key"].split("_")[0],
              end_err=float(s["true_end_err"]), id=s["id"])
    st["edit"] = {}
    for name, info in (s.get("edits") or {}).items():
        d = c[name][:3]
        st["edit"][name.split(":")[1]] = bool(math.hypot(d[0], d[1]) >= V0.MIN_DISP_M and cos2(d, info[:2]) > 0.5)
    st["acc"] = {q: s["preds"].get(q) == lab.get(q) for q in QS if lab.get(q) is not None}
    pen = [s["ee_z"] + c[f"xy:{d}"][6] < s["floor_z"] - PEN_M for d in V0.DIR_XY8 if d != lab["dir_xy"]]
    st["pen_pairs"], st["pen_hits"] = len(pen), int(sum(pen))
    r = s["grip_rec"][1] - s["grip_rec"][0]
    st["grip_event"] = abs(r) >= GRIP_MIN - EPS
    t = c["true"][4] - c["true"][3]
    st["grip_hit"] = bool(st["grip_event"] and t * math.copysign(1.0, r) >= GRIP_MIN - EPS)
    st["grip_end_err"] = abs(c["true"][4] - s["grip_rec"][1])
    return st


def _mean(x):
    return float(np.mean(x)) if len(x) else float("nan")


def pool(sel: list) -> dict:
    if not sel:
        return {"n_snap": 0}
    out = V0.pool([sel], range(len(sel)))
    out["edit"] = {str(th): _mean([x["edit"][str(th)] for x in sel if str(th) in x["edit"]]) for th in EDITS}
    out["edit_n"] = sum(1 for x in sel if x["edit"])
    out["edit_plausible"] = _mean([x["edit"][str(t)] for x in sel for t in PLAUSIBLE if str(t) in x["edit"]])
    out["edit_stress"] = _mean([x["edit"][str(t)] for x in sel for t in STRESS if str(t) in x["edit"]])
    out["end_err_median"] = float(np.median([x["end_err"] for x in sel]))
    out["dec_acc"] = _mean([v for x in sel for v in x["acc"].values()])
    pp = sum(x["pen_pairs"] for x in sel)
    out["pen_rate"] = sum(x["pen_hits"] for x in sel) / pp if pp else float("nan")
    ev = [x for x in sel if x["grip_event"]]
    out["grip_n"] = len(ev)
    out["grip_hit"] = _mean([x["grip_hit"] for x in ev])
    out["grip_end_err"] = _mean([x["grip_end_err"] for x in sel])
    return out


def groups(stats: list, mode: str) -> dict:
    if mode == "far":
        g = {k: [x for x in stats if x["stratum"] == k] for k in STRATA}
        g["primary"] = g["far"]
    else:
        g = {k: [x for x in stats if x["stratum"] == k] for k in STRATA}
        g["primary"] = list(stats)
        g["near"] = [x for x in stats if x["contact"]]
    g["all"] = list(stats)
    return g


def summarize(stats: list, mode: str) -> dict:
    g = groups(stats, mode)
    out = {k: pool(v) for k, v in g.items()}
    out["primary_by_kind"] = {k: pool([x for x in g["primary"] if x["kind"] == k]) for k in ("RB1", "RB2")}
    out["primary_breakdown"] = V0.breakdown([g["primary"]]) if g["primary"] else {}
    return out


def average(ms: list):
    def av(xs):
        if isinstance(xs[0], dict):
            return {k: av([x[k] for x in xs]) for k in xs[0] if all(k in x for x in xs)}
        if isinstance(xs[0], (int, float)) and not isinstance(xs[0], bool):
            return float(np.mean(xs))
        return xs[0]
    return av(ms)


def check(c1: dict, c0: dict, seeds_far: list) -> dict:
    f, n, a = c1["primary"], c1["near"], c1["all"]
    n0, a0 = c0["near"], c0["all"]
    checks = [
        ("far", f["a_xy"] >= FAR_MIN - EPS and all(v >= SEED_MIN - EPS for v in seeds_far)),
        ("N1", n["mse_true"] <= n0["mse_true"] * 1.05 + EPS),
        ("N2", n["end_err_median"] <= n0["end_err_median"] * 1.10 + EPS),
        ("N3", n["grip_hit"] >= n0["grip_hit"] - 0.02 - EPS),
        ("N4", n["dec_acc"] >= n0["dec_acc"] - 0.01 - EPS),
        ("N5", n["true_rate"] >= n0["true_rate"] - 0.02 - EPS),
        ("i", a["true_rate"] >= a0["true_rate"] - 0.02 - EPS),
        ("ii", a["pen_rate"] <= a0["pen_rate"] + 0.02 + EPS),
        ("iii", a["dec_acc"] >= a0["dec_acc"] - 0.01 - EPS),
        ("iv", c1["latency_p95_ms"] <= c0["latency_p95_ms"] + 10.0 + EPS),
    ]
    fails = [k for k, ok in checks if not ok]
    if not fails:
        v = "ADOPT"
    elif "far" in fails:
        v = "NOT_REACHED"
    elif any(k.startswith("N") for k in fails):
        v = "NEAR_BLEED"
    else:
        v = "NOT_ADOPTED"
    grade = ("FULL" if f["a_z"] >= FAR_MIN - EPS and f["rho_mean"] >= 0.5 - EPS else "XY") if v == "ADOPT" else None
    return {"verdict": v, "grade": grade, "fails": fails, "checks": dict(checks), "a_xy_primary": f["a_xy"],
            "a_xy_primary_seeds": seeds_far}


def load(path: str, n_expect: int) -> tuple:
    want = set(V0.cond_names(False))
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
    ids = [s["id"] for s in snaps]
    if summ is None or summ.get("n") != n_expect or len(snaps) != n_expect or skips:
        raise SystemExit(f"{path}: {len(snaps)} snaps, {skips} skips, summary n {summ and summ.get('n')} != {n_expect}")
    if len(set(ids)) != len(ids):
        raise SystemExit(f"{path}: duplicate snapshot ids")
    for s in snaps:
        miss = want - set(s["c"])
        if miss:
            raise SystemExit(f"{path} {s['id']}: missing conditions {sorted(miss)}")
        if not all(math.isfinite(v) for vals in s["c"].values() for v in vals):
            raise SystemExit(f"{path} {s['id']}: non-finite value")
        if s["stratum"] not in STRATA:
            raise SystemExit(f"{path} {s['id']}: stratum {s['stratum']}")
    return snaps, summ


def paired_diff(a: list, b: list, n_boot: int, seed: int = 0):
    """(A_xy(b) - A_xy(a), bootstrap 2.5 %, 97.5 %) over the primary snapshots of paired seed runs [[s1], [s2]]."""
    ha = np.array([[x["xy_hits"] for x in r] for r in a], float)
    hb = np.array([[x["xy_hits"] for x in r] for r in b], float)
    p = np.array([[x["xy_pairs"] for x in r] for r in a], float)
    d = hb.sum() / p.sum() - ha.sum() / p.sum()
    rng = np.random.default_rng(seed)
    n = p.shape[1]
    bs = []
    for _ in range(n_boot):
        j = rng.integers(0, n, n)
        bs.append(hb[:, j].sum() / p[:, j].sum() - ha[:, j].sum() / p[:, j].sum())
    return float(d), float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--c0", nargs=2, required=True)
    ap.add_argument("--c1", nargs=2, required=True)
    ap.add_argument("--mode", default="far", choices=("far", "all"))
    ap.add_argument("--n", type=int, default=1799)
    ap.add_argument("--boot", type=int, default=10000)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    runs, lat, files = {}, {}, {}
    for arm in ("c0", "c1"):
        for i, path in enumerate(getattr(a, arm)):
            snaps, summ = load(path, a.n)
            runs[f"{arm}_s{i + 1}"] = [snap_stats(s) for s in snaps]
            lat[f"{arm}_s{i + 1}"] = (summ.get("latency_ms") or {}).get("p95")
            files[f"{arm}_s{i + 1}"] = {"path": path, "keys_sha": summ.get("keys_sha"), "latency_ms": summ.get("latency_ms")}
    ids = [x["id"] for x in runs["c0_s1"]]
    if any([x["id"] for x in r] != ids for r in runs.values()):
        raise SystemExit("the four runs are not on the same snapshots in the same order")
    if any(v is None for v in lat.values()):
        raise SystemExit(f"no latency in {[k for k, v in lat.items() if v is None]} (--latency)")
    per = {k: summarize(v, a.mode) for k, v in runs.items()}
    for k in per:
        per[k]["latency_p95_ms"] = lat[k]
    avg = {arm: average([per[f"{arm}_s1"], per[f"{arm}_s2"]]) for arm in ("c0", "c1")}
    seeds_far = [per["c1_s1"]["primary"]["a_xy"], per["c1_s2"]["primary"]["a_xy"]]
    res = {"mode": a.mode, "files": files, "rule": check(avg["c1"], avg["c0"], seeds_far), "avg": avg, "per_seed": per}
    prim = {k: [x for x in groups(v, a.mode)["primary"]] for k, v in runs.items()}
    res["ci95_primary"] = {arm: V0.boot_ci([prim[f"{arm}_s1"], prim[f"{arm}_s2"]], a.boot, 0) for arm in ("c0", "c1")}
    d, lo, hi = paired_diff([prim["c0_s1"], prim["c0_s2"]], [prim["c1_s1"], prim["c1_s2"]], a.boot)
    res["c1_minus_c0_primary"] = {"diff": d, "ci95": [lo, hi]}
    json.dump(res, open(a.out, "w"), indent=1, default=float)
    print(json.dumps({"rule": res["rule"], "c1_minus_c0_primary": res["c1_minus_c0_primary"]}, default=float),
          flush=True)


if __name__ == "__main__":
    main()
