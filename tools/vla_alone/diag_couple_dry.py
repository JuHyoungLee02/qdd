"""Stagewise diagnosis of the E-Couple dry run VLA-alone / coupled failures (docs/stage3/results/vla_alone_diag.md; CPU
only, reads the existing closed-loop logs, no simulator, no model).

For every episode log (<root>/<variant>/<arm>/ours/<run>/<scene>-e0.jsonl, runtime/core.py records) it decomposes the
failure per decision step (0.33 s):
  - hold chain: steps with M4 'hold' (a T1 CONTRADICT of the previous step empties the executed decisions and the
    chunk is not played -> last action held), which T1 predicate was false, gripper width w vs the open threshold
    (runtime/measure.ProprioRules.th_w = 80.5 mm), first hold time, longest hold run, share of the episode held;
  - approach geometry: gripper (g_tbl) vs mug (o3_tbl) xy distance (min, when), height above the mug, overshoot along the
    initial approach axis (projection of g - mug on unit(mug - g0), > 0 = past the mug), command vs measured TCP gap;
  - decisions: executed dir_xy vs the oracle direction to the mug (8 sectors, cos > 0.5 as the E-SR0 metric), the
    model's per-call answer (every call, committed or not) vs the same oracle, and the executed displacement over a
    played step vs the executed dir_xy;
  - phases: time per phase, final phase; summary chunk stats (played / held / stale_dec).
  python tools/vla_alone/diag_couple_dry.py --root /data/harvest/out/couple_dry/main --out diag.json
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
from collections import Counter, defaultdict

import numpy as np

TH_W = 0.08050180748425541
DT = 0.33
UNIT = {"plus_x": (1, 0), "plus_x_plus_y": (1, 1), "plus_y": (0, 1), "minus_x_plus_y": (-1, 1), "minus_x": (-1, 0),
        "minus_x_minus_y": (-1, -1), "minus_y": (0, -1), "plus_x_minus_y": (1, -1)}


def cos(a, b):
    na, nb = math.hypot(*a), math.hypot(*b)
    return 0.0 if na < 1e-9 or nb < 1e-9 else (a[0] * b[0] + a[1] * b[1]) / (na * nb)


def match(vec, name, min_m=1e-4):
    """E-SR0 match_xy shape: |vec| >= 0.1 mm and cos(vec, unit(name)) > 0.5; none_xy <-> |vec| small."""
    if name == "none_xy":
        return math.hypot(*vec) < 0.005
    return math.hypot(*vec) >= min_m and cos(vec, UNIT[name]) > 0.5


def runs(flags):
    best = cur = 0
    for f in flags:
        cur = cur + 1 if f else 0
        best = max(best, cur)
    return best


def episode(path):
    recs = [json.loads(x) for x in open(path, encoding="utf-8")]
    steps = [r for r in recs if r.get("type") == "step" and "g_tbl" in r and "o3_tbl" in r]
    calls = [r for r in recs if r.get("type") == "call"]
    summ_p = path[:-len(".jsonl")] + "_summary.json"
    summ = json.load(open(summ_p)) if os.path.exists(summ_p) else {}
    if not steps:
        return None
    g = np.array([s["g_tbl"] for s in steps])
    o = np.array([s["o3_tbl"] for s in steps])
    tcp, cmd = np.array([s["tcp"] for s in steps]), np.array([s["cmd"] for s in steps])
    t = np.array([s["t"] for s in steps])
    w = np.array([s["w"] for s in steps])
    ph = [s.get("phase") for s in steps]
    hold = np.array([bool(s.get("hold")) for s in steps])
    d_xy = np.linalg.norm(g[:, :2] - o[:, :2], axis=1)
    u = o[0, :2] - g[0, :2]
    u = u / max(np.linalg.norm(u), 1e-9)
    over = (g[:, :2] - o[:, :2]) @ u
    appr = np.array([p == "approach" for p in ph])
    i_min = int(np.argmin(d_xy))
    t1 = Counter(x for s in steps for x in (s.get("t1_check") or []))
    outc = Counter(s.get("prev_outcome") for s in steps if s.get("prev_outcome"))
    first_hold = float(t[hold][0]) if hold.any() else None
    # decisions
    ex_match, ex_n, ans_match, ans_n, mv_match, mv_n = 0, 0, 0, 0, 0, 0
    ex_by = Counter()
    for k, s in enumerate(steps):
        dxy = (s.get("decisions") or {}).get("dir_xy") or [None, None]
        v = o[k, :2] - g[k, :2]
        if dxy[0] is not None and ph[k] == "approach" and np.linalg.norm(v) > 0.02:
            ex_n += 1
            ex_match += int(dxy[0] != "none_xy" and match(v, dxy[0]))
            ex_by[dxy[0]] += 1
        if dxy[0] not in (None, "none_xy") and not s.get("hold") and k + 1 < len(steps):
            mv = g[k + 1, :2] - g[k, :2]
            if np.linalg.norm(mv) >= 0.002:
                mv_n += 1
                mv_match += int(match(mv, dxy[0]))
    by_t = {round(s["t"], 2): k for k, s in enumerate(steps)}
    ans_by = Counter()
    near_calls = []
    for c in calls:
        k = by_t.get(round(c.get("t_state", -1), 2))
        a = (c.get("answers") or {}).get("dir_xy")
        if k is None or a is None or ph[k] != "approach":
            continue
        v = o[k, :2] - g[k, :2]
        if np.linalg.norm(v) <= 0.03:  # over the mug (pregrasp xy reached): what does the model want next?
            ans = c.get("answers") or {}
            near_calls.append({"z_mm": 1e3 * float(g[k, 2] - o[k, 2]), "dir_z": (ans.get("dir_z") or [None])[0],
                               "phase": (ans.get("phase") or [None])[0], "dir_xy": a[0]})
        if np.linalg.norm(v) <= 0.02:
            continue
        ans_n += 1
        ans_match += int(a[0] != "none_xy" and match(v, a[0]))
        ans_by[a[0]] += 1
    phase_t = Counter()
    for p in ph:
        phase_t[p] += DT
    ch = summ.get("chunk") or {}
    below = (w < TH_W) & appr
    return {
        "n_steps": len(steps), "t_end": float(t[-1]), "final_phase": ph[-1], "success": summ.get("env_success"),
        "phase_s": {k: round(v, 2) for k, v in phase_t.items()},
        "hold_share": round(float(hold.mean()), 3), "first_hold_t": first_hold,
        "longest_hold_s": round(runs(hold) * DT, 2), "t1_false": dict(t1), "outcomes": dict(outc),
        "w_start_mm": round(1e3 * w[0], 1), "w_min_approach_mm": round(1e3 * float(w[appr].min()), 1) if appr.any() else None,
        "w_first_hold_mm": round(1e3 * float(w[hold][0]), 1) if hold.any() else None,
        "approach_share_w_below_open": round(float(below.sum() / max(appr.sum(), 1)), 3),
        "first_w_below_open_t": float(t[below][0]) if below.any() else None,
        "d_xy_start_mm": round(1e3 * d_xy[0], 1), "d_xy_min_mm": round(1e3 * float(d_xy[i_min]), 1),
        "t_d_xy_min": float(t[i_min]), "z_above_mug_at_min_mm": round(1e3 * float(g[i_min, 2] - o[i_min, 2]), 1),
        "d_xy_first_hold_mm": round(1e3 * float(d_xy[hold][0]), 1) if hold.any() else None,
        "d_xy_end_mm": round(1e3 * float(d_xy[-1]), 1), "z_above_mug_end_mm": round(1e3 * float(g[-1, 2] - o[-1, 2]), 1),
        "overshoot_max_mm": round(1e3 * float(over.max()), 1),
        "overshoot_at_first_hold_mm": round(1e3 * float(over[hold][0]), 1) if hold.any() else None,
        "cmd_gap_mm_median": round(1e3 * float(np.median(np.linalg.norm(cmd - tcp, axis=1))), 1),
        "cmd_gap_mm_median_hold": round(1e3 * float(np.median(np.linalg.norm((cmd - tcp)[hold], axis=1))), 1)
        if hold.any() else None,
        "exec_dir_vs_oracle": [ex_match, ex_n], "exec_dir_hist": dict(ex_by),
        "answer_dir_vs_oracle": [int(ans_match), ans_n], "answer_dir_hist": dict(ans_by),
        "moved_vs_exec_dir": [mv_match, mv_n],
        "chunk": {k: ch.get(k) for k in ("played", "held", "stale_dec", "requested", "delivered")},
        "mug_moved_mm": round(1e3 * float(np.linalg.norm(o[-1] - o[0])), 1),
        "over_mug_calls": len(near_calls),
        "over_mug_z_mm_median": round(float(np.median([x["z_mm"] for x in near_calls])), 1) if near_calls else None,
        "over_mug_dir_z": dict(Counter(x["dir_z"] for x in near_calls)),
        "over_mug_phase": dict(Counter(x["phase"] for x in near_calls)),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/data/harvest/out/couple_dry/main")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out, agg = {}, defaultdict(list)
    for p in sorted(glob.glob(os.path.join(a.root, "*", "*", "ours", "*", "*-e0.jsonl"))):
        parts = p.split(os.sep)
        var, arm, scene = parts[-5], parts[-4], os.path.basename(p)[:-len("-e0.jsonl")]
        e = episode(p)
        if e is None:
            continue
        out[f"{var}/{arm}/{scene}"] = e
        agg[arm].append(e)
    tot = {}
    for arm, es in agg.items():
        def s(key, i):
            return int(sum(e[key][i] for e in es))
        tot[arm] = {
            "n": len(es), "success": sum(bool(e["success"]) for e in es),
            "final_phase": dict(Counter(e["final_phase"] for e in es)),
            "hold_share_median": float(np.median([e["hold_share"] for e in es])),
            "longest_hold_s_median": float(np.median([e["longest_hold_s"] for e in es])),
            "eps_with_hold": sum(e["first_hold_t"] is not None for e in es),
            "t1_false": dict(sum((Counter(e["t1_false"]) for e in es), Counter())),
            "w_first_hold_mm_median": float(np.median([e["w_first_hold_mm"] for e in es if e["w_first_hold_mm"]]
                                                      or [float("nan")])),
            "approach_share_w_below_open_median": float(np.median([e["approach_share_w_below_open"] for e in es])),
            "d_xy_min_mm_median": float(np.median([e["d_xy_min_mm"] for e in es])),
            "z_above_mug_at_min_mm_median": float(np.median([e["z_above_mug_at_min_mm"] for e in es])),
            "overshoot_max_mm_median": float(np.median([e["overshoot_max_mm"] for e in es])),
            "d_xy_end_mm_median": float(np.median([e["d_xy_end_mm"] for e in es])),
            "exec_dir_vs_oracle": [s("exec_dir_vs_oracle", 0), s("exec_dir_vs_oracle", 1)],
            "answer_dir_vs_oracle": [s("answer_dir_vs_oracle", 0), s("answer_dir_vs_oracle", 1)],
            "moved_vs_exec_dir": [s("moved_vs_exec_dir", 0), s("moved_vs_exec_dir", 1)],
            "over_mug_calls": sum(e["over_mug_calls"] for e in es),
            "over_mug_dir_z": dict(sum((Counter(e["over_mug_dir_z"]) for e in es), Counter())),
            "over_mug_phase": dict(sum((Counter(e["over_mug_phase"]) for e in es), Counter())),
            "over_mug_z_mm_median": float(np.median([e["over_mug_z_mm_median"] for e in es
                                                     if e["over_mug_z_mm_median"] is not None] or [float("nan")])),
            "chunk_played_share": round(sum(e["chunk"]["played"] or 0 for e in es)
                                        / max(1, sum((e["chunk"]["played"] or 0) + (e["chunk"]["held"] or 0) for e in es)), 3),
            "stale_dec_share_of_held": round(sum(e["chunk"]["stale_dec"] or 0 for e in es)
                                             / max(1, sum(e["chunk"]["held"] or 0 for e in es)), 3),
        }
    json.dump({"episodes": out, "arms": tot}, open(a.out, "w"), indent=1, default=int)
    print(json.dumps(tot, indent=1, default=int))


if __name__ == "__main__":
    main()
