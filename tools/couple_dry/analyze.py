"""E-Couple dry run analysis (docs/stage3/prereg_couple_dry.md §4): plumbing counts and descriptive behaviour, no
verdict. Reads <out>/closed.json, the per-trial sidecars + summaries, dry_calls_*.jsonl, dry_trace_*.jsonl, the
ledger and worker logs; writes <out>/dry_analysis.json and prints a markdown summary.

  python tools/couple_dry/analyze.py --out /data/harvest/out/couple_dry/main [--v-max 0.08 --a-max 0.32]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import Counter, defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

DT = 0.01  # control tick (RuntimeConfig.control_hz 100)


def arm_of(condition: str) -> str:
    return condition.rsplit("|cp-", 1)[1] if "|cp-" in condition else "off"


def read_jsonl(p):
    if not os.path.exists(p):
        return []
    return [json.loads(x) for x in open(p, encoding="utf-8") if x.strip()]


def pct(xs, q):
    xs = [x for x in xs if x is not None]
    return round(float(np.percentile(xs, q)), 3) if xs else None


def inflight_violations(rows: list) -> dict:
    """The serial invariant from the sidecar alone: send k+1 only after request k was answered (any answer row, also
    an error / schema error) or timed out. Returns {sends, violations, after_timeout}."""
    ev = []
    for r in rows:
        k = r.get("couple_kind")
        if k == "send":
            ev.append((r["t"], 1, "send", r["no"]))
        elif k == "answer":
            ev.append((r["t_deliver"], 0, "late" if r.get("late") else "answer", r["no"]))
        elif k == "timeout":
            ev.append((r["t"], 0, "timeout", r["no"]))
    ev.sort()
    open_no, closed, viol, after_to, sends = None, set(), 0, 0, 0
    for t, _, kind, no in ev:
        if kind == "send":
            sends += 1
            if open_no is not None and open_no not in closed:
                viol += 1
            open_no = no
        elif kind in ("answer", "timeout"):
            closed.add(no)
            if kind == "timeout":
                after_to += 1
    return {"sends": sends, "violations": viol, "timeouts_seen": after_to}


def trace_stats(rows: list, v_max: float, a_max: float) -> dict:
    from harvest.astra_motion.harness import motion_stats
    path = [[r[0], *r[1]] for r in rows]
    ms = motion_stats(path) if len(path) >= 5 else {"max_speed": None, "jerk_rms": None, "jerk_max": None}
    out = {**ms, "ticks": len(rows)}
    ap = [r[4] for r in rows]
    out["a_priv_share"] = {"none": sum(1 for a in ap if a is None) / max(len(ap), 1),
                           "a0": sum(1 for a in ap if a == 0.0) / max(len(ap), 1),
                           "a_mid": sum(1 for a in ap if a is not None and 0 < a < 1) / max(len(ap), 1),
                           "a1": sum(1 for a in ap if a == 1.0) / max(len(ap), 1)}
    cp = [r for r in rows if len(r) > 6]
    if cp:
        st = np.array([r[6][:3] for r in cp], float)
        sp = np.linalg.norm(st, axis=1) / DT
        acc = np.abs(np.diff(sp)) / DT if len(sp) > 1 else np.zeros(1)
        stepn = np.linalg.norm(st, axis=1)
        a_arr = np.array([np.nan if r[4] is None else r[4] for r in cp], float)
        out.update({
            "offset_ticks_moving": int((stepn > 1e-9).sum()),
            "offset_path_m": round(float(stepn.sum()), 5),
            "offset_net_m": [round(float(x), 5) for x in st.sum(axis=0)],
            "offset_speed_max": round(float(sp.max()), 5), "offset_speed_cap": v_max,
            "offset_speed_cap_held": bool(sp.max() <= v_max + 1e-6),
            "offset_accel_max_scalar": round(float(acc.max()), 4), "offset_accel_cap": a_max,
            "offset_rem_max_m": round(float(max(r[8] for r in cp)), 5),
            "offset_path_at_a0_m": round(float(stepn[a_arr == 0.0].sum()), 5),
            "offset_path_at_a_lt1_m": round(float(stepn[~(a_arr == 1.0)].sum()), 5),
            "slowed_ticks": int(sum(1 for r in cp if r[9] != 1.0))})
    return out


def episode_key(variant, scene):
    return f"{variant}/{scene}"


def analyze(out: str, v_max: float, a_max: float) -> dict:
    cj = json.load(open(os.path.join(out, "closed.json"), encoding="utf-8"))
    res, meta = cj["result"], cj["meta"]
    trials = res["trials"]
    variants = sorted({t["variant"] for t in trials})
    calls = {v: read_jsonl(os.path.join(out, f"dry_calls_{v}.jsonl")) for v in variants}
    traces = {}
    for v in variants:
        for r in read_jsonl(os.path.join(out, f"dry_trace_{v}.jsonl")):
            arm = "serial" if "cp-serial" in r["policy"] else "off"
            traces[(v, arm, r["scene"])] = r["rows"]
    eps, crash = [], {}
    for v in variants:
        log = os.path.join(out, f"worker_{v}.log")
        txt = open(log, encoding="utf-8", errors="replace").read() if os.path.exists(log) else ""
        crash[v] = {"tracebacks": txt.count("Traceback"), "worker_done": "R6_WORKER_DONE" in txt}
    for t in trials:
        arm = arm_of(t["condition"])
        side = t.get("sidecar")
        rows = read_jsonl(side) if side else []
        cr = [r for r in rows if r.get("type") == "couple"]
        sm_p = side[:-len(".jsonl")] + "_summary.json" if side else None
        sm = json.load(open(sm_p, encoding="utf-8")) if sm_p and os.path.exists(sm_p) else {}
        scene = os.path.basename(side)[:-len(".jsonl")].rsplit("-e", 1)[0] if side else None
        e = {"variant": t["variant"], "arm": arm, "seed": t["seed"], "success": bool(t["success"]),
             "sim_time": t["sim_time"], "termination": t["termination"], "scene": scene,
             "rtf": sm.get("rtf_env"), "final_phase": sm.get("final_phase"), "dec_calls": sm.get("calls_delivered"),
             "dec_errors": sm.get("call_errors"), "dec_lat_p95": (sm.get("latency_s") or {}).get("p95"),
             "chunk": sm.get("chunk")}
        tr = traces.get((t["variant"], arm, scene))
        e["trace"] = trace_stats(tr, v_max, a_max) if tr else None
        c = sm.get("couple")
        if c:
            ans = [r for r in cr if r.get("couple_kind") == "answer"]
            good = [r for r in ans if "gate" in r]
            e["couple"] = {k: c.get(k) for k in ("calls_sent", "answers", "schema_errors", "api_errors", "timeouts",
                                                  "late", "max_inflight", "max_outstanding", "latency_s",
                                                  "answer_age_s", "cost_krw", "gates", "layer", "offset", "irrev",
                                                  "events", "budget_excluded", "adherence", "prompt_id")}
            e["couple"]["inflight_check"] = inflight_violations(cr)
            e["couple"]["ages"] = [r.get("age_s") for r in good]
            e["couple"]["commands"] = dict(Counter(r.get("command") for r in good))
            e["couple"]["notes"] = dict(Counter(n for r in good for n in (r.get("notes") or [])))
            e["couple"]["schema_problems"] = dict(Counter(p for r in ans for p in (r.get("schema_error") or [])))
            e["couple"]["hold_send"] = dict(Counter(r.get("why") for r in cr if r.get("couple_kind") == "hold_send"))
        eps.append(e)
    ledger = read_jsonl(os.path.join(out, "ledger.jsonl"))
    allc = [r for v in variants for r in calls[v]]
    serial = [e for e in eps if e["arm"] == "serial"]

    def tot(key):
        cc = Counter()
        for e in serial:
            cc.update((e["couple"] or {}).get(key) or {})
        return dict(cc)
    ages = [a for e in serial for a in (e["couple"] or {}).get("ages", []) if a is not None]
    plumbing = {
        "episodes": {"expected": None, "got": len(eps), "by_arm": dict(Counter(e["arm"] for e in eps))},
        "crashes": crash, "eval_runs": [{k: r.get(k) for k in ("_cond_done", "status", "error", "wall_s")}
                                        for r in res.get("eval_runs", [])],
        "calls_sent": sum(e["couple"]["calls_sent"] for e in serial if e.get("couple")),
        "answers_valid": sum(e["couple"]["answers"] for e in serial if e.get("couple")),
        "schema_errors": sum(e["couple"]["schema_errors"] for e in serial if e.get("couple")),
        "api_errors": sum(e["couple"]["api_errors"] for e in serial if e.get("couple")),
        "timeouts": sum(e["couple"]["timeouts"] for e in serial if e.get("couple")),
        "late": sum(e["couple"]["late"] for e in serial if e.get("couple")),
        "max_outstanding": max([e["couple"]["max_outstanding"] for e in serial if e.get("couple")] or [None]),
        "inflight_violations": sum(e["couple"]["inflight_check"]["violations"] for e in serial if e.get("couple")),
        "client_conc_max": max([r["conc_at_start"] for r in allc] or [None]),
        "client_conc_gt1": sum(1 for r in allc if r["conc_at_start"] > 1),
        "faults_injected": sum(1 for r in allc if r["fault"]),
        "stale_gate": tot("gates").get("stale", 0), "gates": tot("gates"), "layer": tot("layer"),
        "irrev": tot("irrev"), "events": tot("events"), "notes": tot("notes"), "commands": tot("commands"),
        "schema_problems": tot("schema_problems"), "hold_send": tot("hold_send"),
        "answer_age_s": {"p50": pct(ages, 50), "p95": pct(ages, 95), "max": max(ages) if ages else None,
                         "n_gt_15": sum(1 for a in ages if a > 15.0)},
        "qwen_actual_s": {"p50": pct([r["actual_s"] for r in allc], 50), "p95": pct([r["actual_s"] for r in allc], 95),
                          "max": max([r["actual_s"] for r in allc] or [None])},
        "padded_s": {"p50": pct([r["padded_s"] for r in allc], 50), "p95": pct([r["padded_s"] for r in allc], 95)},
        "ledger": {"rows": len(ledger), "krw": round(sum(float(r["cost_krw"]) for r in ledger), 6),
                   "kinds": dict(Counter(r.get("kind") for r in ledger)),
                   "price_models": sorted({r.get("model") for r in ledger})},
        "offset_speed_cap_held": all((e["trace"] or {}).get("offset_speed_cap_held", True) for e in serial),
        "offset_speed_max": max([(e["trace"] or {}).get("offset_speed_max") or 0 for e in serial] or [0]),
        "offset_accel_max_scalar": max([(e["trace"] or {}).get("offset_accel_max_scalar") or 0 for e in serial] or [0]),
        "offset_v_max_seen": max([((e["couple"] or {}).get("offset") or {}).get("v_max_seen", 0) for e in serial] or [0]),
        "offset_a_max_seen": max([((e["couple"] or {}).get("offset") or {}).get("a_max_seen", 0) for e in serial] or [0]),
        "offset_path_m_total": round(sum((e["trace"] or {}).get("offset_path_m", 0) for e in serial), 5),
        "offset_path_at_a0_m_total": round(sum((e["trace"] or {}).get("offset_path_at_a0_m", 0) for e in serial), 5),
        "offset_path_at_a_lt1_m_total": round(sum((e["trace"] or {}).get("offset_path_at_a_lt1_m", 0) for e in serial),
                                              5),
        "adherence": [((e["couple"] or {}).get("adherence")) for e in serial],
    }
    beh = defaultdict(dict)
    for v in variants:
        for arm in ("off", "serial"):
            E = [e for e in eps if e["variant"] == v and e["arm"] == arm]
            beh[v][arm] = {"n": len(E), "success": sum(e["success"] for e in E),
                           "t_success_med": pct([e["sim_time"] for e in E if e["success"]], 50),
                           "jerk_rms_med": pct([(e["trace"] or {}).get("jerk_rms") for e in E], 50),
                           "max_speed_med": pct([(e["trace"] or {}).get("max_speed") for e in E], 50),
                           "rtf_med": pct([e["rtf"] for e in E], 50),
                           "final_phase": dict(Counter(e["final_phase"] for e in E))}
    return {"out": out, "git": meta.get("git"), "code_sha": meta.get("code_sha"), "plumbing": plumbing,
            "behaviour": beh, "episodes": eps, "cells": {k: {"n": c["n"], "success": c["success"], "couple": c["couple"]}
                                                         for k, c in res["cells"].items()},
            "couple_diff": res.get("couple_diff"), "runtime_s": meta.get("runtime_s")}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--v-max", type=float, default=0.08)
    ap.add_argument("--a-max", type=float, default=0.32)
    a = ap.parse_args(argv)
    r = analyze(a.out, a.v_max, a.a_max)
    json.dump(r, open(os.path.join(a.out, "dry_analysis.json"), "w", encoding="utf-8"), indent=1, default=str)
    print(json.dumps({"plumbing": r["plumbing"], "behaviour": r["behaviour"]}, indent=1, default=str))


if __name__ == "__main__":
    main()
