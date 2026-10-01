"""E-CL15 summary (docs/stage3/prereg_cl15.md): success rate with a Wilson 95 % interval, failure types
(fail_stage/end_reason), the same episode's E-M35CL results in the training environment (reference column), and the
video index. -> <root>/summary.json, summary.md, /data/harvest/videos/cl15/T1/index.md"""
from __future__ import annotations

import collections
import glob
import json
import math
import os

ROOT = "/data/harvest/out/cl15"
VID = "/data/harvest/videos/cl15/T1"
M35 = "/data/harvest/out/main35_closed/res"


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return None, None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(c - h, 3), round(c + h, 3)


def main():
    t1 = json.load(open(os.path.join(ROOT, "t1.json")))["kinds"]
    rows = []
    for k, v in sorted(t1.items()):
        name = f"{v['task']}_s{v['seed']}"
        od = os.path.join(ROOT, "res", "ep1.5", "none", "t1", name)
        r = {"kind": k, "task": v["task"], "seed": v["seed"]}
        if os.path.exists(os.path.join(od, "cl.json")):
            c = json.load(open(os.path.join(od, "cl.json")))
            r.update({x: c.get(x) for x in ("success", "fail_stage", "end_reason", "n_calls", "sim_t", "wall_s", "mp4")})
        elif os.path.exists(os.path.join(od, "error.json")) or os.path.exists(os.path.join(od, "skip.json")):
            r["success"] = None
            r["end_reason"] = "error" if os.path.exists(os.path.join(od, "error.json")) else "skip"
        else:
            r["success"] = None
            r["end_reason"] = "not_run"
        ref = {}
        for ck in ("f35d", "0.5", "1", "1.5"):
            p = os.path.join(M35, ck, "none", "l8s_val", name, "cl.json")
            if os.path.exists(p):
                ref[ck] = bool(json.load(open(p))["success"])
        r["train_env_ref"] = ref
        rows.append(r)
    done = [r for r in rows if r["success"] is not None]
    k = sum(bool(r["success"]) for r in done)
    fails = collections.Counter(f"{r.get('fail_stage')}/{r.get('end_reason')}" for r in done if not r["success"])
    lo, hi = wilson(k, len(done))
    out = {"n": len(done), "success": k, "sr": round(k / len(done), 3) if done else None, "wilson95": [lo, hi],
           "fail_types": dict(fails.most_common()), "not_finished": len(rows) - len(done), "rows": rows}
    json.dump(out, open(os.path.join(ROOT, "summary.json"), "w"), indent=1)
    md = [f"# E-CL15 T1 (ep1.5, held-out environment, loop break on)", "",
          f"- success {k}/{len(done)} = {out['sr']} (Wilson 95 % {lo}-{hi}); not finished {out['not_finished']}",
          f"- failure types: {', '.join(f'{w} {n}' for w, n in fails.most_common()) or '-'}", "",
          "| kind | task | seed | success | fail | calls | train-env ref (E-M35CL) | mp4 |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['kind']} | {r['task'][:48]} | {r['seed']} | {r['success']} | {r.get('fail_stage')}/"
                  f"{r.get('end_reason')} | {r.get('n_calls')} | {r['train_env_ref']} | {r.get('mp4')} |")
    open(os.path.join(ROOT, "summary.md"), "w").write("\n".join(md) + "\n")
    os.makedirs(VID, exist_ok=True)
    open(os.path.join(VID, "index.md"), "w").write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
