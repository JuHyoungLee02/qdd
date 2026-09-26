"""Call-level and perception numbers for docs/stage3/results/open_vlm_solo.md (no model calls).
Per model: latency p50/p95, input / output / reasoning tokens, KRW per call, invalid share; per episode: approach
commanded-target signed error (dx, dy mm = command - mug centre, median over approach calls), closes, lowest commanded z.
usage: python stats.py <ledger.jsonl> <label>=<api model>=<out root>/proxy-low [...]"""
import glob
import json
import os
import statistics
import sys


def pct(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, int(round(q * (len(v) - 1))))] if v else None


rows = [json.loads(x) for x in open(sys.argv[1]) if x.strip()]
for spec in sys.argv[2:]:
    label, model, root = spec.split("=")
    rs = [r for r in rows if r["model"] == model]
    lat = [r["latency_s"] for r in rs if r.get("latency_s") is not None]
    u = [r.get("usage") or {} for r in rs]
    ins = [x.get("input_tokens", 0) for x in u]
    outs = [x.get("output_tokens", 0) for x in u]
    rea = [(x.get("output_tokens_details") or {}).get("reasoning_tokens", 0) for x in u]
    print(f"## {label} calls={len(rs)} krw={sum(r['cost_krw'] for r in rs):.1f} "
          f"krw/call={sum(r['cost_krw'] for r in rs) / max(len(rs), 1):.2f} lat_p50={pct(lat, .5)} "
          f"lat_p95={pct(lat, .95)} in_med={statistics.median(ins) if ins else None} "
          f"out_med={statistics.median(outs) if outs else None} reason_med={statistics.median(rea) if rea else None} "
          f"errors={sum(1 for r in rs if r.get('error'))}")
    for p in sorted(glob.glob(os.path.join(root, "*", "s*", "result.json"))):
        r = json.load(open(p))
        dx, dy, zs, closes = [], [], [], 0
        for c in r["calls"]:
            cmd = (c.get("parsed") or {}).get("command") or {}
            if cmd.get("gripper") == "close" or cmd.get("mode") == "gripper" and cmd.get("gripper") == "close":
                closes += 1
            sc = c.get("score")
            if c["phase_truth"] == "approach" and sc:
                g, t = sc["goal"], c["truth"]["tgt_xyz"]
                dx.append((g[0] - t[0]) * 1e3)
                dy.append((g[1] - t[1]) * 1e3)
                zs.append(g[2])
        first = (r["calls"][0].get("score") or {}) if r["calls"] else {}
        print(f"{r['variant']} s{r['seed']}: success={r['success']} grasp_lift={r['grasp_lift']} "
              f"stage={r['fail_stage']} end={r['end_reason']} calls={r['n_calls']} invalid={r['n_invalid']} "
              f"krw={r['cost_krw']:.1f} motion_s={r['sim_t']} wall_s={r['wall_s']} t_success={r['t_success']} "
              f"blocked={r['n_blocked']} clipped={r['n_clipped']} closes={closes} "
              f"first_xy_mm={first.get('xy_err_mm')} "
              f"appr_dx_med={statistics.median(dx) if dx else None} appr_dy_med={statistics.median(dy) if dy else None} "
              f"appr_xy_med={statistics.median([c['score']['xy_err_mm'] for c in r['calls'] if c.get('score') and c['phase_truth'] == 'approach']) if dx else None} "
              f"min_cmd_z={min(zs) if zs else None} mug={r['calls'][0]['truth']['tgt_xyz'] if r['calls'] else None} "
              f"first_close={r.get('first_close')}")
