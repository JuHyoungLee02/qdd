"""L9R pilot summary (pure): per robot / head-camera mode, per definition yield (success and max_dq_rad <= 0.04),
G1 (n >= 10 and yield >= 0.5), the AI Worker drawn-camera yield vs the production (standard camera, motion l9m-2)
yield of the same definitions and arms, joint-step tails, head camera geometry realized, end reasons.
usage: python tools/l9r/pilot_summary.py <run dir> <production collect root>  -> JSON on stdout"""
import glob
import json
import os
import sys
from collections import Counter, defaultdict

import numpy as np


def metas(root):
    for m in glob.glob(os.path.join(root, "**", "meta.json"), recursive=True):
        try:
            d = json.load(open(m))
        except (OSError, ValueError):
            continue
        if d.get("gen") == "l9":
            d["_dir"] = os.path.dirname(m)
            yield d


def ok(d):
    return bool(d.get("success")) and (d.get("max_dq_rad") or 0) <= 0.04


def wilson(k, n, z=1.96):
    if not n:
        return None
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(c - h, 3), round(c + h, 3)]


def q(a):
    a = [x for x in a if x is not None]
    return [round(float(v), 3) for v in np.percentile(a, [0, 5, 50, 95, 100])] if a else None


def main():
    run, prod = sys.argv[1], sys.argv[2]
    eps = list(metas(os.path.join(run, "collect")))
    groups = defaultdict(list)
    for d in eps:
        groups[(d.get("robot") or "ffw_sg2", ((d.get("head_cam") or {}).get("draw") or {}).get("mode", "std"))].append(d)
    out = {"n": len(eps), "skipped": len(glob.glob(os.path.join(run, "collect", "**", "skipped.json"), recursive=True))}
    for (robot, mode), ds in sorted(groups.items()):
        per = defaultdict(lambda: [0, 0])
        for d in ds:
            per[d["task_id"]][0] += 1
            per[d["task_id"]][1] += ok(d)
        g1 = sorted(k for k, (n, s) in per.items() if n >= 10 and s / n >= 0.5)
        hc = [d.get("head_cam") or {} for d in ds]
        k = sum(ok(d) for d in ds)
        out[f"{robot}/{mode}"] = {
            "n": len(ds), "ok": k, "yield": round(k / len(ds), 3), "wilson95": wilson(k, len(ds)),
            "arms": dict(Counter(d["arm"] for d in ds)),
            "jump_share": round(sum((d.get("max_dq_rad") or 0) > 0.04 for d in ds) / len(ds), 3),
            "max_dq_q": q([d.get("max_dq_rad") for d in ds]),
            "end_reason": dict(Counter(str(d.get("end_reason")) for d in ds).most_common(8)),
            "per_def": {k2: {"n": n, "ok": s, "yield": round(s / n, 3)} for k2, (n, s) in sorted(per.items())},
            "g1_pass": g1, "g1_n_pass": len(g1), "g1_n_defs": len(per),
            "head_cam": {"height_above_surface_m": q([h.get("height_above_surface_m") for h in hc]),
                         "pitch_deg": q([h.get("pitch_deg") for h in hc]), "pan_deg": q([h.get("pan_deg") for h in hc]),
                         "hfov_deg": q([h.get("hfov_deg") for h in hc]), "redraws": dict(Counter(h.get("redraws") for h in hc)),
                         "modes": dict(Counter((h.get("draw") or {}).get("mode") for h in hc))},
            "base_drop_m": q([(d.get("base") or {}).get("drop_m") for d in ds]),
        }
    # production baseline (standard camera, l9m-2) for the AI Worker drawn-camera definitions / arms
    rand = groups.get(("ffw_sg2", "rand"), [])
    if rand:
        want = {(d["task_id"], d["arm"]) for d in rand}
        base = [d for d in metas(prod) if (d["task_id"], d["arm"]) in want and d.get("motion_version") == "l9m-2"]
        # weight the baseline like the pilot: per (definition, arm) yield, averaged with the pilot's counts
        pc = Counter((d["task_id"], d["arm"]) for d in rand)
        by = defaultdict(lambda: [0, 0])
        for d in base:
            by[(d["task_id"], d["arm"])][0] += 1
            by[(d["task_id"], d["arm"])][1] += ok(d)
        w = [(pc[k], by[k][1] / by[k][0]) for k in pc if by[k][0] >= 5]
        if w:
            exp = sum(c * y for c, y in w) / sum(c for c, _ in w)
            got = [ok(d) for d in rand if by[(d["task_id"], d["arm"])][0] >= 5]
            out["ffw_rand_vs_prod_std"] = {"pilot_yield": round(float(np.mean(got)), 3), "prod_yield_weighted": round(exp, 3),
                                           "diff_pp": round(100 * (float(np.mean(got)) - exp), 1),
                                           "n_pilot": len(got), "n_prod": len(base),
                                           "gate_diff_ge_minus5pp": bool(100 * (float(np.mean(got)) - exp) >= -5.0)}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
