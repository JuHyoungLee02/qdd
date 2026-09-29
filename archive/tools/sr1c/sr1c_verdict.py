"""E-SR1c verdict (docs/stage3/prereg_sr1c.md §4, fixed before the main runs; not edited after results).

  python tools/sr1c/sr1c_verdict.py --c0 C0.jsonl --c1 C1.jsonl --c2 C2.jsonl [--c1-s1 F --c2-s1 F] [--s S.jsonl] \
      --n 1200 --out verdict.json [--boot 10000]

Per snapshot = tools/sr0/sr0_verdict.snap_stats (A_xy pairs, chance, A_z, rho, true baseline, gripper, MSE; imported,
not modified) + stratum (privileged authority: far a = 1, band 0 < a < 1, near a = 0), plausible-edit hits (edit:theta,
chunk xy >= 0.1 mm and cos(chunk xy, edit vector) > 0.5; plausible = +-30 / +-45 deg, stress = +-90 / 180 deg),
true-chunk end-point FK error, decision accuracy (prediction = label, 5 questions), counterfactual penetration proxy
(xy:<d> chunks, d != label: tcp_z + dzmin - PAD_BELOW_M < 2 mm).
Rule (CMP_EPS 1e-12; C0 = the E-MA2 C0 checkpoint evaluated by sr1c_eval):
  far       A_xy_far >= 0.80
  N1        near mean normalized MSE of the true-decision chunk <= C0 x 1.05
  N2        near median true-chunk end-point FK error <= C0 x 1.10
  N3        near phase_id close/open gripper hit >= C0 - 0.02 (gripper-hit proxy: the vocabulary has no §87 option)
  N4        near decision accuracy on target + phase items >= C0 - 0.01
  N5        near true-decision direction hit (label != none) >= C0 - 0.02
  i         whole-range true-decision direction hit >= 0.90
  ii        whole-range counterfactual penetration-proxy rate <= C0 + 0.02
  iii       whole-range decision accuracy (5 questions, no command) >= C0 - 0.01
  iv        chunk-path p95 latency <= C0 + 10 ms
  ADOPT(arm) = all of them; grade FULL if A_z_far >= 0.80 and rho_far >= 0.5, else XY; far passes but an N fails ->
  near_bleed (not adopted). Boundary: A_xy_far in [0.77, 0.83] -> NEED_SEED1 (seed 1 of that arm, the two seeds'
  metrics averaged, the rule applied again). Both adopted -> C2 if A_xy_far(C2) - A_xy_far(C1) >= +0.03 and its paired
  bootstrap 95 % lower bound > 0, else C1; one -> that arm; none -> RUN_S.
  S: A_xy_far >= 0.99 (construction check, else S_BUG); STRUCT if N1-N5, ii, iv and the far median true-chunk end-point
  error <= C0 x 1.15, else NONE.
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
_spec = importlib.util.spec_from_file_location("sr0_verdict", os.path.join(_HERE, "..", "sr0", "sr0_verdict.py"))
V0 = importlib.util.module_from_spec(_spec)
sys.path.insert(0, os.path.join(_HERE, "..", "sr0"))
_spec.loader.exec_module(V0)

EPS = 1e-12
FAR_MIN = 0.80
BOUNDARY = (0.77, 0.83)
PAD_BELOW_M = 0.027  # = harvest.train.sr1c_branch.PAD_BELOW_M
PEN_M = 0.002
PLAUSIBLE, STRESS = (30, -30, 45, -45), (90, -90, 180)
QS = ("dir_xy", "dir_z", "mag_coarse", "target", "phase")
STRATA = ("far", "band", "near")


def cos2(d, e) -> float:
    n, m = math.hypot(d[0], d[1]), math.hypot(e[0], e[1])
    return 0.0 if n < V0.MIN_DISP_M or m == 0 else (d[0] * e[0] + d[1] * e[1]) / (n * m)


def snap_stats(s: dict) -> dict:
    st = V0.snap_stats(s, grip=True)
    c, lab = s["c"], s["labels"]
    st.update(stratum=s["stratum"], a_priv=s["a_priv"], a_hat=s["a_hat"], task=s["id"].split("/")[1],
              end_err=float(s["true_end_err"]), id=s["id"])
    st["edit"] = {}
    for name, info in (s.get("edits") or {}).items():
        d = c[name][:3]
        st["edit"][name.split(":")[1]] = bool(math.hypot(d[0], d[1]) >= V0.MIN_DISP_M and cos2(d, info[:2]) > 0.5)
    st["acc"] = {q: s["preds"].get(q) == lab.get(q) for q in QS if lab.get(q) is not None}
    pen = [s["tcp_z"] + c[f"xy:{d}"][6] - PAD_BELOW_M < PEN_M for d in V0.DIR_XY8 if d != lab["dir_xy"]]
    st["pen_pairs"], st["pen_hits"] = len(pen), int(sum(pen))
    return st


def _mean(x):
    return float(np.mean(x)) if len(x) else float("nan")


def pool(sel: list) -> dict:
    if not sel:
        return {"n_snap": 0}
    out = V0.pool([sel], range(len(sel)))
    ed = {}
    for th in PLAUSIBLE + STRESS:
        h = [x["edit"][str(th)] for x in sel if str(th) in x["edit"]]
        ed[str(th)] = _mean(h)
    out["edit"] = ed
    out["edit_n"] = sum(1 for x in sel if x["edit"])
    out["edit_plausible"] = _mean([x["edit"][str(t)] for x in sel for t in PLAUSIBLE if str(t) in x["edit"]])
    out["edit_stress"] = _mean([x["edit"][str(t)] for x in sel for t in STRESS if str(t) in x["edit"]])
    out["end_err_median"] = float(np.median([x["end_err"] for x in sel]))
    out["acc_target_phase"] = _mean([x["acc"][q] for x in sel for q in ("target", "phase") if q in x["acc"]])
    out["dec_acc"] = _mean([v for x in sel for v in x["acc"].values()])
    pp = sum(x["pen_pairs"] for x in sel)
    out["pen_rate"] = sum(x["pen_hits"] for x in sel) / pp if pp else float("nan")
    out["a_hat_mean"] = _mean([x["a_hat"] for x in sel if x["a_hat"] is not None])
    return out


def summarize(stats: list) -> dict:
    out = {k: pool([x for x in stats if x["stratum"] == k]) for k in STRATA}
    out["all"] = pool(stats)
    tasks = sorted({x["task"] for x in stats})
    out["far_by_task"] = {t: pool([x for x in stats if x["stratum"] == "far" and x["task"] == t]) for t in tasks}
    far = [x for x in stats if x["stratum"] == "far"]
    out["far_by_a_hat"] = {"a_hat=1": pool([x for x in far if x["a_hat"] == 1.0]),
                           "a_hat<1": pool([x for x in far if x["a_hat"] is not None and x["a_hat"] < 1.0])}
    out["far_breakdown"] = V0.breakdown([far]) if far else {}
    return out


def metrics(summary: dict, latency_p95_ms) -> dict:
    return {"far": summary["far"], "near": summary["near"], "all": summary["all"], "latency_p95_ms": latency_p95_ms}


def arm_check(m: dict, c0: dict) -> dict:
    f, n, a = m["far"], m["near"], m["all"]
    f0, n0, a0 = c0["far"], c0["near"], c0["all"]
    checks = [
        ("far", f["a_xy"] >= FAR_MIN - EPS),
        ("N1", n["mse_true"] <= n0["mse_true"] * 1.05 + EPS),
        ("N2", n["end_err_median"] <= n0["end_err_median"] * 1.10 + EPS),
        ("N3", n["grip_hit"] >= n0["grip_hit"] - 0.02 - EPS),
        ("N4", n["acc_target_phase"] >= n0["acc_target_phase"] - 0.01 - EPS),
        ("N5", n["true_rate"] >= n0["true_rate"] - 0.02 - EPS),
        ("i", a["true_rate"] >= 0.90 - EPS),
        ("ii", a["pen_rate"] <= a0["pen_rate"] + 0.02 + EPS),
        ("iii", a["dec_acc"] >= a0["dec_acc"] - 0.01 - EPS),
        ("iv", m["latency_p95_ms"] <= c0["latency_p95_ms"] + 10.0 + EPS),
    ]
    fails = [k for k, ok in checks if not ok]
    adopt = not fails
    grade = ("FULL" if f["a_z"] >= FAR_MIN - EPS and f["rho_mean"] >= 0.5 - EPS else "XY") if adopt else None
    near = [k for k in fails if k.startswith("N")]
    return {"adopt": adopt, "grade": grade, "fails": fails, "a_xy_far": f["a_xy"],
            "near_bleed": "far" not in fails and bool(near),
            "boundary": BOUNDARY[0] - EPS <= f["a_xy"] <= BOUNDARY[1] + EPS}


def choose(r1: dict, r2: dict, diff: float, diff_lo: float) -> dict:
    need = [k for k, r in (("C1", r1), ("C2", r2)) if r is not None and r["boundary"]]
    if need:
        return {"verdict": "NEED_SEED1", "arms": need}
    ok1, ok2 = r1["adopt"], r2 is not None and r2["adopt"]
    if ok1 and ok2:
        c2 = diff >= 0.03 - EPS and diff_lo > 0
        return {"verdict": "ADOPT_C2" if c2 else "ADOPT_C1", "grade": (r2 if c2 else r1)["grade"]}
    if ok1:
        return {"verdict": "ADOPT_C1", "grade": r1["grade"]}
    if ok2:
        return {"verdict": "ADOPT_C2", "grade": r2["grade"]}
    return {"verdict": "RUN_S"}


def struct_check(m: dict, c0: dict) -> dict:
    if m["far"]["a_xy"] < 0.99 - EPS:
        return {"verdict": "S_BUG", "a_xy_far": m["far"]["a_xy"]}
    r = arm_check(m, c0)
    fails = [k for k in r["fails"] if k in ("N1", "N2", "N3", "N4", "N5", "ii", "iv")]
    if m["far"]["end_err_median"] > c0["far"]["end_err_median"] * 1.15 + EPS:
        fails.append("far_end")
    return {"verdict": "STRUCT" if not fails else "NONE", "fails": fails}


def average(ms: list) -> dict:
    """Seed average of metric dicts (numbers averaged, the rest from the first)."""
    def av(xs):
        if isinstance(xs[0], dict):
            return {k: av([x[k] for x in xs]) for k in xs[0] if all(k in x for x in xs)}
        if isinstance(xs[0], (int, float)) and not isinstance(xs[0], bool):
            return float(np.mean(xs))
        return xs[0]
    return av(ms)


def paired_diff(s1: list, s2: list, n_boot: int = 10000, seed: int = 0):
    """(A_xy_far(C2) - A_xy_far(C1), bootstrap 2.5 % quantile) over far snapshots, the same resampled ids."""
    f1 = {x["id"]: x for x in s1 if x["stratum"] == "far"}
    f2 = {x["id"]: x for x in s2 if x["stratum"] == "far"}
    ids = sorted(set(f1) & set(f2))
    h1 = np.array([f1[i]["xy_hits"] for i in ids], float)
    h2 = np.array([f2[i]["xy_hits"] for i in ids], float)
    p = np.array([f1[i]["xy_pairs"] for i in ids], float)
    d = h2.sum() / p.sum() - h1.sum() / p.sum()
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(n_boot):
        j = rng.integers(0, len(ids), len(ids))
        bs.append(h2[j].sum() / p[j].sum() - h1[j].sum() / p[j].sum())
    return float(d), float(np.quantile(bs, 0.025))


def boot_far(stats: list, n_boot: int = 10000, seed: int = 0):
    far = [x for x in stats if x["stratum"] == "far"]
    return V0.boot_ci([far], n_boot, seed) if far else {}


def load(path: str, n_expect: int) -> tuple:
    """(snap records, summary); checks: n = n_expect records, no skip, unique ids, every sr0 condition present, finite."""
    want = set(V0.cond_names(True))
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


def evaluate_file(path: str, n: int, n_boot: int):
    snaps, summ = load(path, n)
    st = [snap_stats(s) for s in snaps]
    sm = summarize(st)
    lat = (summ.get("latency_ms") or {}).get("p95")
    return st, sm, metrics(sm, lat), boot_far(st, n_boot), summ


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--c0", required=True)
    ap.add_argument("--c1", required=True)
    ap.add_argument("--c2", default="")
    ap.add_argument("--c1-s1", default="")
    ap.add_argument("--c2-s1", default="")
    ap.add_argument("--s", default="")
    ap.add_argument("--n", type=int, default=1200)
    ap.add_argument("--boot", type=int, default=10000)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    res = {"files": {}, "arms": {}}
    st, sm, mt, ci = {}, {}, {}, {}
    for name, path in (("c0", a.c0), ("c1", a.c1), ("c2", a.c2), ("c1_s1", a.c1_s1), ("c2_s1", a.c2_s1),
                       ("s", a.s)):
        if path:
            st[name], sm[name], mt[name], ci[name], summ = evaluate_file(path, a.n, a.boot)
            res["files"][name] = {"path": path, "keys_sha": summ.get("keys_sha"), "latency_ms": summ.get("latency_ms")}
    for name in mt:
        if mt[name]["latency_p95_ms"] is None:
            raise SystemExit(f"{name}: no latency in the summary (--latency)")
    c0 = mt["c0"]
    for arm in ("c1", "c2"):
        if arm in mt and f"{arm}_s1" in mt:
            mt[arm + "_avg"] = average([mt[arm], mt[arm + "_s1"]])
    r1 = arm_check(mt.get("c1_avg", mt["c1"]), c0)
    r2 = arm_check(mt.get("c2_avg", mt["c2"]), c0) if "c2" in mt else None
    if "c1_s1" in mt:
        r1["boundary"] = False  # seed 1 already averaged in: the rule is applied once more, no further seed
    if r2 is not None and "c2_s1" in mt:
        r2["boundary"] = False
    diff = diff_lo = None
    if "c2" in st:
        diff, diff_lo = paired_diff(st["c1"], st["c2"], a.boot)
    res["arms"] = {"c1": r1, "c2": r2}
    res["choice"] = choose(r1, r2, diff if diff is not None else 0.0, diff_lo if diff_lo is not None else 0.0)
    res["c2_minus_c1_far"] = {"diff": diff, "boot_lo": diff_lo}
    if "s" in mt:
        res["struct"] = struct_check(mt["s"], c0)
    res["summary"] = sm
    res["boot_far"] = ci
    json.dump(res, open(a.out, "w"), indent=1, default=float)
    print(json.dumps({"choice": res["choice"], "arms": res["arms"], "c2_minus_c1_far": res["c2_minus_c1_far"],
                      **({"struct": res["struct"]} if "struct" in res else {})}, default=float), flush=True)


if __name__ == "__main__":
    main()
