"""Aggregate E-Astra-motion results (pure): per model x mode table, serial-stream metrics, the pre-registered F1
rule, paired bootstrap (Astra low vs the local VLM), grasp-probe rates, smooth vs immediate replay.

  python -m harvest.astra_motion.agg --out /data/harvest/out/astra_motion [--json summary.json]
Layout: <out>/<model>/<mode>/s<seed>_<task>/result.json (+ replay.json for stream episodes);
<out>/grasp_answers.jsonl.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os

import numpy as np

from .cost import KRW_PER_USD
from .harness import same_command

N_BOOT = 10000
F1_FLIP_RATIO = 0.5


def load(out: str) -> dict:
    rows = {}
    for p in glob.glob(os.path.join(out, "*", "*", "s*_*", "result.json")):
        model, mode, ep = p.replace("\\", "/").split("/")[-4:-1]
        r = json.load(open(p))
        rp = os.path.join(os.path.dirname(p), "replay.json")
        if os.path.exists(rp):
            r["replay"] = json.load(open(rp))
        rows.setdefault((model, mode), {})[ep] = r
    return rows


def _pct(v, q):
    return round(float(np.percentile(v, q)), 2) if len(v) else None


def grasp_err(r) -> float:
    c = r.get("first_close")
    return float(c["err_mm"]) if c else math.inf


STALE_S = 6.0  # provisional stale-answer threshold (spec §15-§16): reported, not applied


def stream_metrics(r: dict) -> dict:
    """Serial stream: latency and answer age (image time -> arrival, sim s), share of answers older than STALE_S,
    gaps between arrivals, timed-out calls, consecutive-answer agreement / flips, unjustified flips, per-call tokens and
    cost, cost per robot minute. flip = two consecutive valid answers (arrival order) whose effective commands disagree
    (harness.same_command: kind, gripper action, direction within 35 deg); unjustified = a flip with no gripper action
    completed and no holding change between the two answers' send times."""
    sg = r["stream"]
    arrived = [a for a in sg["answers"] if a.get("arr_t") is not None]
    A = [a for a in arrived if a["valid"]]
    arr = sorted(a["arr_t"] for a in arrived)
    gaps = np.diff(arr) if len(arr) >= 2 else np.array([])
    ev = sorted(sg.get("gripper_events", []) + r.get("hold_changes", []))
    flips = unjust = 0
    for a, b in zip(A[:-1], A[1:]):
        if same_command(a.get("effective"), b.get("effective")):
            continue
        flips += 1
        lo, hi = sorted((a["send_t"], b["send_t"]))
        if not any(lo < t <= hi for t in ev):
            unjust += 1
    n_pairs = max(len(A) - 1, 0)
    st = [a.get("status") for a in sg["answers"]]
    lat = [a["latency_s"] for a in arrived]
    age = [a["age_s"] for a in arrived if a.get("age_s") is not None]
    tin = [a["tokens_in"] for a in arrived if a.get("tokens_in")]
    tout = [a["tokens_out"] for a in arrived if a.get("tokens_out")]
    cost = [a["cost_usd"] for a in arrived if a.get("cost_usd") is not None]
    return {"answers": len(sg["answers"]), "valid": len(A), "timed_out": st.count("timed_out"),
            "latency_p50_s": _pct(lat, 50), "latency_p95_s": _pct(lat, 95), "age_p50_s": _pct(age, 50),
            "age_p95_s": _pct(age, 95), "stale_share": round(sum(x > STALE_S for x in age) / len(age), 3) if age
            else None, "gap_p50_s": _pct(gaps, 50), "gap_p95_s": _pct(gaps, 95),
            "flip_rate": round(flips / n_pairs, 3) if n_pairs else None,
            "unjustified_flip_rate": round(unjust / n_pairs, 3) if n_pairs else None,
            "revisions": sum(a.get("decision") == "revise" for a in A),
            "revisions_confirmed": st.count("confirmed"), "revisions_unconfirmed": st.count("unconfirmed"),
            "uncertain": sum(bool(a.get("uncertain")) for a in A),
            "tokens_in_per_call": round(float(np.mean(tin))) if tin else None,
            "tokens_out_per_call": round(float(np.mean(tout))) if tout else None,
            "cost_krw_per_call": round(float(np.mean(cost)) * KRW_PER_USD, 1) if cost else None,
            "exec_sim_s": sg["exec_sim_s"], "rtf": sg["rtf"],
            "cost_krw_per_robot_min": round(r["cost_usd"] * KRW_PER_USD / max(sg["exec_sim_s"] / 60, 1e-6), 1)}


def summarize(rows: dict, eps: list | None = None) -> dict:
    R = [rows[e] for e in (eps or sorted(rows)) if e in rows]
    n = len(R)
    if not n:
        return {"n": 0}
    calls = [c for r in R for c in r["calls"]]
    lat = [c["latency_s"] for c in calls if not c["api_error"]]
    ft = [c["first_token_s"] for c in calls if not c["api_error"]]
    ge = [grasp_err(r) for r in R]
    stages = {}
    for r in R:
        if not r["success"]:
            stages[r["fail_stage"]] = stages.get(r["fail_stage"], 0) + 1
    conf = {k: sum(r.get("confidence", {}).get(k, 0) for r in R) for k in ("low", "medium", "high")}
    tin = sum(r["tokens_in"] for r in R)
    out = {
        "n": n, "success": sum(r["success"] for r in R), "success_rate": round(sum(r["success"] for r in R) / n, 3),
        "grasp_lift": sum(r["grasp_lift"] for r in R), "grasp_err_median_mm": float(np.median(ge)),
        "fail_stages": stages, "collision_eps": sum(r["collision"] for r in R),
        "clipped": sum(r["n_clipped"] for r in R), "timeouts": sum(r["n_timeout"] for r in R),
        "calls": len(calls), "calls_per_ep": round(len(calls) / n, 2),
        "invalid_calls": sum(not c["valid"] for c in calls if c["kind"] != "st_after_end"),
        "schema_violation_rate": round(sum(not c["valid"] for c in calls if c["kind"] != "st_after_end")
                                       / max(len(calls), 1), 3),
        "schema_fail_eps": sum(r["schema_fail_end"] for r in R),
        "latency_p50_s": _pct(lat, 50), "latency_p95_s": _pct(lat, 95), "first_token_p50_s": _pct(ft, 50),
        "tokens_in_per_ep": round(tin / n), "cached_share": round(sum(r.get("tokens_cached", 0) for r in R)
                                                                 / max(tin, 1), 3),
        "tokens_out_per_ep": round(sum(r["tokens_out"] for r in R) / n),
        "tokens_reasoning_per_ep": round(sum(r["tokens_reasoning"] for r in R) / n),
        "cost_krw_per_ep": round(sum(r["cost_usd"] for r in R) / n * KRW_PER_USD, 1),
        "cost_krw_total": round(sum(r["cost_usd"] for r in R) * KRW_PER_USD, 1),
        "decisions": {k: sum(r.get("decisions", {}).get(k, 0) for r in R) for k in ("continue", "edit", "stop", "keep",
                                                                                  "revise")},
        "confidence": conf, "uncertain_to_continue": sum(r.get("n_uncertain_continue", 0) for r in R),
        "proprio_conflicts": sum(len(r.get("proprio_conflicts", [])) for r in R),
        "max_speed_median": _pct([r["max_speed"] for r in R if r.get("max_speed") is not None], 50),
        "jerk_rms_median": _pct([r["jerk_rms"] for r in R if r.get("jerk_rms") is not None], 50),
        "sim_t_median": _pct([r["sim_t"] for r in R], 50)}
    if any("stream" in r for r in R):
        sm = [stream_metrics(r) for r in R]
        for k in ("latency_p50_s", "latency_p95_s", "age_p50_s", "age_p95_s", "stale_share", "gap_p50_s",
                  "gap_p95_s", "flip_rate", "unjustified_flip_rate", "tokens_in_per_call", "tokens_out_per_call",
                  "cost_krw_per_call", "cost_krw_per_robot_min", "rtf"):
            v = [m[k] for m in sm if m[k] is not None]
            out[f"stream_{k}"] = round(float(np.mean(v)), 3) if v else None
        pairs = sum(max(m["valid"] - 1, 0) for m in sm)
        out["stream_flips_pooled"] = (round(sum((m["flip_rate"] or 0) * max(m["valid"] - 1, 0) for m in sm)
                                            / pairs, 3) if pairs else None)
        for k in ("timed_out", "revisions", "revisions_confirmed", "revisions_unconfirmed", "uncertain"):
            out[f"stream_{k}"] = sum(m[k] for m in sm)
        rp = [r["replay"] for r in R if r.get("replay")]
        if rp:
            for ex in ("smooth", "immediate"):
                for k in ("max_speed", "jerk_rms", "jerk_max"):
                    v = [x[ex][k] for x in rp if x[ex].get(k) is not None]
                    out[f"replay_{ex}_{k}_median"] = _pct(v, 50)
    return out


def paired_bootstrap(a: dict, b: dict, key="success", n_boot=N_BOOT, seed=0) -> dict | None:
    """Mean difference a - b over the episodes both have (episode = cluster), 95 % percentile CI."""
    eps = sorted(set(a) & set(b))
    if not eps:
        return None
    x = np.array([float(a[e][key]) - float(b[e][key]) for e in eps])
    rng = np.random.default_rng(seed)
    bs = x[rng.integers(0, len(x), size=(n_boot, len(x)))].mean(1)
    return {"n": len(eps), "diff": round(float(x.mean()), 3), "ci95": [round(float(np.percentile(bs, 2.5)), 3),
                                                                        round(float(np.percentile(bs, 97.5)), 3)]}


def f1_rule(tab: dict, model="astra-low") -> dict:
    """Pre-registered: F1 is adopted as the request style if its pooled flip rate <= 0.5 x F0's and its full-task
    successes >= F0's on the same episodes; otherwise F0 (fresh) stays."""
    f0, f1 = tab.get((model, "S-stream-F0")), tab.get((model, "S-stream-F1"))
    if not f0 or not f1 or not f0.get("n") or not f1.get("n"):
        return {"verdict": "incomplete"}
    a, b = f0.get("stream_flips_pooled"), f1.get("stream_flips_pooled")
    if a is None or b is None:
        return {"verdict": "incomplete"}
    ok = b <= F1_FLIP_RATIO * a + 1e-12 and f1["success"] >= f0["success"]
    return {"verdict": "F1" if ok else "F0", "flip_F0": a, "flip_F1": b, "success_F0": f0["success"],
            "success_F1": f1["success"], "n_F0": f0["n"], "n_F1": f1["n"]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/data/harvest/out/astra_motion")
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)
    rows = load(a.out)
    tab = {k: summarize(v) for k, v in sorted(rows.items())}
    boots = {}
    for mode in ("S", "S-stream-F0", "S-stream-F1"):
        for other in ("qwen8b", "astra-high"):
            x, y = rows.get(("astra-low", mode)), rows.get((other, mode))
            if x and y:
                boots[f"astra-low-{other}:{mode}"] = {k: paired_bootstrap(x, y, k) for k in ("success", "grasp_lift")}
    g = os.path.join(a.out, "grasp_answers.jsonl")
    grasp = None
    if os.path.exists(g):
        from .grasp_probe import score
        grasp = score([json.loads(x) for x in open(g)])
    out = {"table": {f"{k[0]}|{k[1]}": v for k, v in tab.items()}, "f1_rule": f1_rule(tab), "bootstrap": boots,
           "grasp_probe": grasp}
    print(json.dumps(out, indent=1, default=str))
    if a.json:
        with open(a.json, "w") as f:
            json.dump(out, f, indent=1, default=str)


if __name__ == "__main__":
    main()
