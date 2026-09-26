"""E-VLA-solo analysis + verdict (docs/stage3/prereg_vla_solo.md §4; rules fixed at registration, not edited after
results). CPU only.

  python tools/vla_alone/analyze_vla.py --arm A=/data/harvest/out/vla_solo/A ... --out verdict.json

Per episode (trace of tools/vla_alone/vla_closed.py + the runtime summary):
  success       env_success of the runtime summary
  min_d3_mm     min over the episode of |finger midpoint g - mug o3| (sim, privileged, analysis only)
  min_xy_mm     the same in xy
  phase_rank    highest phase reached (approach 0 < descend 1 < close 2 < lift 3 < carry 4 < place_descend 5 < open 6
                < retreat 7 < done 8)
  stuck_s       time with TCP speed < 5 mm/s (0.5 s window) while not in close / open / done and not succeeded
  hold_s        time with the M4 hold flag; perm_hold = the hold lasts from its first tick to the episode end
  overshoot_mm  before the first 'close': max of (g - o3)_xy . u0, u0 = unit(o3_xy - g_xy at t 0) (> 0 = past the mug)
  t_end_s       episode end (success ends it)
  jump_ticks    ticks with max |delta action joint| > 0.04 rad (safety rule, memory 'no jumps')
  v_appr_mm_s   median TCP speed in 'approach' over moving ticks (> 5 mm/s) (speed sanity, G-speed)
Rules (EPS 1e-9), arm names fixed by the registration: A = VLA C5 1.0x, B = VLA C3 1.0x, C = VLA C3 0.75x,
D = VLA C3 0.5x, E = VLA C5 0.5x, F = scripted (modular code rule + skill, privileged) C5 1.0x, G = no-op (fused mock:
hold chunk) C5.
  G-bench       F success >= 10/12, else the bench is suspect (no verdict; redesign)
  Q1 meaning    TASK_MEANINGFUL if some VLA arm (A-E) has success >= 4/12; else PROGRESS_ONLY if some VLA arm beats
                G on progress: >= 10 of 12 paired episodes with min_d3 lower than G's by >= 20 mm and median
                min_d3 <= 40 mm; else NOT_MEANINGFUL
  Q2 speed      for S in (C 0.75, D 0.5): ADOPT_S if success(S) - success(B) >= 2 episodes and median overshoot(S) <
                median overshoot(B); else NOT_ADOPTED (1.0x kept). E vs A reported (not a rule)
  Q3 deadlock   CONFIRMED if >= 6 of 12 A episodes end in a permanent hold and B's median phase_rank > A's or
                success(B) > success(A); else NOT_CONFIRMED
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from collections import defaultdict

import numpy as np

PH = ("approach", "descend", "close", "lift", "carry", "place_descend", "open", "retreat", "done")
RANK = {p: i for i, p in enumerate(PH)}
VLA = ("A", "B", "C", "D", "E")


def summaries(root):
    out = {}
    for p in glob.glob(os.path.join(root, "*", "*", "*", "*", "*_summary.json")):
        parts = p.split(os.sep)
        var = parts[-5]
        scene = os.path.basename(p)[:-len("-e0_summary.json")]
        out[(var, scene)] = json.load(open(p))
    return out


def episode(tr, summ):
    rows = tr["rows"]
    t = np.array([r[0] for r in rows])
    tcp = np.array([r[1] for r in rows], float)
    ok = [r[2] is not None and r[3] is not None for r in rows]
    g = np.array([r[2] if o else [np.nan] * 3 for r, o in zip(rows, ok)], float)
    o3 = np.array([r[3] if o else [np.nan] * 3 for r, o in zip(rows, ok)], float)
    ph = [r[5] for r in rows]
    hold = np.array([bool(r[7]) for r in rows])
    a = np.array([r[8] for r in rows], float)
    succ = bool(summ.get("env_success")) if summ else False
    d3 = np.linalg.norm(g - o3, axis=1)
    dxy = np.linalg.norm(g[:, :2] - o3[:, :2], axis=1)
    i0 = int(np.argmax(np.isfinite(dxy)))
    u0 = o3[i0, :2] - g[i0, :2]
    u0 = u0 / max(np.linalg.norm(u0), 1e-9)
    first_close = next((i for i, p in enumerate(ph) if RANK.get(p, 0) >= RANK["close"]), len(ph))
    ov = ((g[:first_close, :2] - o3[:first_close, :2]) @ u0) if first_close > 0 else np.array([np.nan])
    dt = np.median(np.diff(t)) if len(t) > 1 else 0.01
    w = max(1, int(round(0.5 / dt)))
    sp = np.full(len(t), np.nan)
    if len(t) > w:
        sp[w:] = np.linalg.norm(tcp[w:] - tcp[:-w], axis=1) / (t[w:] - t[:-w])
    active = np.array([p not in ("close", "open", "done") for p in ph])
    stuck = (sp < 0.005) & active
    appr = np.array([p == "approach" for p in ph]) & (sp > 0.005)
    jumps = int((np.abs(np.diff(a, axis=0)).max(1) > 0.04).sum()) if len(a) > 1 else 0
    first_hold = int(np.argmax(hold)) if hold.any() else None
    perm = first_hold is not None and bool(hold[first_hold:].all())
    return {"success": succ, "min_d3_mm": round(1e3 * float(np.nanmin(d3)), 1),
            "min_xy_mm": round(1e3 * float(np.nanmin(dxy)), 1),
            "phase_rank": max(RANK.get(p, 0) for p in ph), "phase_max": PH[max(RANK.get(p, 0) for p in ph)],
            "stuck_s": round(float(stuck.sum() * dt), 2), "hold_s": round(float(hold.sum() * dt), 2),
            "perm_hold": perm, "overshoot_mm": round(1e3 * float(np.nanmax(ov)), 1),
            "t_end_s": round(float(t[-1]), 2), "jump_ticks": jumps,
            "v_appr_mm_s": round(1e3 * float(np.nanmedian(sp[appr])), 1) if appr.any() else None}


def load_arm(root):
    summ = summaries(root)
    eps = {}
    for p in sorted(glob.glob(os.path.join(root, "vla_trace_*.jsonl"))):
        var = os.path.basename(p)[len("vla_trace_"):-len(".jsonl")]
        for x in open(p, encoding="utf-8"):
            tr = json.loads(x)
            scene = tr["scene"]
            eps[f"{var}/{scene}"] = episode(tr, summ.get((var, scene)))
    return eps


def med(xs):
    xs = [x for x in xs if x is not None]
    return float(np.median(xs)) if xs else None


def agg(eps):
    v = list(eps.values())
    return {"n": len(v), "success": sum(e["success"] for e in v),
            "min_d3_mm_median": med([e["min_d3_mm"] for e in v]), "min_xy_mm_median": med([e["min_xy_mm"] for e in v]),
            "phase_rank_median": med([e["phase_rank"] for e in v]),
            "phase_max": {p: sum(e["phase_max"] == p for e in v) for p in PH if any(e["phase_max"] == p for e in v)},
            "stuck_s_median": med([e["stuck_s"] for e in v]), "hold_s_median": med([e["hold_s"] for e in v]),
            "perm_hold": sum(e["perm_hold"] for e in v), "overshoot_mm_median": med([e["overshoot_mm"] for e in v]),
            "t_end_s_median": med([e["t_end_s"] for e in v]), "jump_ticks_median": med([e["jump_ticks"] for e in v]),
            "v_appr_mm_s_median": med([e["v_appr_mm_s"] for e in v])}


def verdict(arms: dict, n_expect: int = 12) -> dict:
    A = {k: agg(v) for k, v in arms.items()}
    out = {"agg": A}
    bench_ok = "F" in A and A["F"]["success"] >= 10
    out["G_bench"] = bench_ok
    if not bench_ok:
        out["Q1"] = out["Q2"] = out["Q3"] = "NO_VERDICT_BENCH"
        return out
    task = [k for k in VLA if k in A and A[k]["success"] >= 4]
    prog = {}
    for k in VLA:
        if k not in arms or "G" not in arms:
            continue
        pairs = [(arms[k][e]["min_d3_mm"], arms["G"][e]["min_d3_mm"]) for e in arms[k] if e in arms["G"]]
        better = sum(1 for a, g in pairs if a <= g - 20 + 1e-9)
        prog[k] = {"better_pairs": better, "n_pairs": len(pairs),
                   "ok": better >= 10 and (A[k]["min_d3_mm_median"] or 1e9) <= 40 + 1e-9}
    out["Q1_progress"] = prog
    out["Q1"] = "TASK_MEANINGFUL" if task else ("PROGRESS_ONLY" if any(p["ok"] for p in prog.values())
                                                else "NOT_MEANINGFUL")
    out["Q1_task_arms"] = task
    q2 = {}
    for k in ("C", "D"):
        if k in A and "B" in A:
            ds = A[k]["success"] - A["B"]["success"]
            ov = (A[k]["overshoot_mm_median"] is not None and A["B"]["overshoot_mm_median"] is not None
                  and A[k]["overshoot_mm_median"] < A["B"]["overshoot_mm_median"])
            q2[k] = {"d_success": ds, "overshoot_lower": bool(ov), "adopt": ds >= 2 and bool(ov)}
    out["Q2_detail"] = q2
    ad = [k for k in ("C", "D") if q2.get(k, {}).get("adopt")]
    out["Q2"] = ("ADOPT_" + ",".join(ad)) if ad else "NOT_ADOPTED"
    if "A" in A and "B" in A:
        conf = A["A"]["perm_hold"] >= 6 and ((A["B"]["phase_rank_median"] or 0) > (A["A"]["phase_rank_median"] or 0)
                                            or A["B"]["success"] > A["A"]["success"])
        out["Q3"] = "CONFIRMED" if conf else "NOT_CONFIRMED"
    out["n_ok"] = {k: v["n"] == n_expect for k, v in A.items()}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", action="append", required=True, help="NAME=OUT_DIR")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    arms = {}
    for x in a.arm:
        k, root = x.split("=", 1)
        arms[k] = load_arm(root)
    res = verdict(arms, a.n)
    res["episodes"] = arms
    json.dump(res, open(a.out, "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "episodes"}, indent=1))


if __name__ == "__main__":
    main()
