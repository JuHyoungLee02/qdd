"""P0-9 upper-error distribution for JCR (docs/stage3/jcr_design.md §0-2): pool the per-call scores of the main 35B
offline evaluation (every x_* control set of one checkpoint's eval folder) into empirical samples.
  python tools/jcr/upper_err_dist.py --eval /data/harvest/out/main35/eval/ep1 --out /data/harvest/out/jcr/upper_err_dist.json
Default --eval = the latest folder with EVAL_COMPLETE. Writes approach_xy_mm, carry_xy_mm, grasp_z_mm (signed), the
wrong-action rate by label action (action_err), latency_s (replies.jsonl), per-set counts, source, sha256."""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os


def latest_complete(root: str) -> str:
    c = [d for d in glob.glob(os.path.join(root, "ep*")) if os.path.exists(os.path.join(d, "EVAL_COMPLETE"))]
    if not c:
        raise SystemExit(f"no complete eval under {root}")
    return max(c, key=lambda d: float(os.path.basename(d)[2:]))


def build(ev: str) -> dict:
    out = {"approach_xy_mm": [], "carry_xy_mm": [], "grasp_z_mm": [], "latency_s": []}
    act = {}
    sets = {}
    for sd in sorted(glob.glob(os.path.join(ev, "x_*"))):
        n = 0
        for line in open(os.path.join(sd, "scores.jsonl")):
            r = json.loads(line)
            n += 1
            for k in ("approach_xy_mm", "carry_xy_mm", "grasp_z_mm"):
                if r.get(k) is not None:
                    out[k].append(float(r[k]))
            la = r.get("label_action")
            if la is not None and r.get("action_ok") is not None:
                a = act.setdefault(la, [0, 0])
                a[0] += int(not r["action_ok"])
                a[1] += 1
        rp = os.path.join(sd, "replies.jsonl")
        if os.path.exists(rp):
            for line in open(rp):
                r = json.loads(line)
                if r.get("latency_s") is not None and not r.get("error"):
                    out["latency_s"].append(float(r["latency_s"]))
        sets[os.path.basename(sd)] = n
    out["action_err"] = {k: round(v[0] / v[1], 4) for k, v in act.items() if v[1]}
    out["action_n"] = {k: v[1] for k, v in act.items()}
    out["sets"] = sets
    out["source"] = ev
    body = json.dumps(out, sort_keys=True).encode()
    out["sha256"] = hashlib.sha256(body).hexdigest()[:16]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", default=None)
    ap.add_argument("--root", default="/data/harvest/out/main35/eval")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    ev = a.eval or latest_complete(a.root)
    d = build(ev)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(d, f)
    q = lambda xs, p: sorted(xs)[int(p * (len(xs) - 1))] if xs else None  # noqa: E731
    print(json.dumps({"source": ev, "sha256": d["sha256"], "sets": d["sets"], "action_err": d["action_err"],
                      **{k: {"n": len(d[k]), "p50": q(d[k], 0.5), "p90": q(d[k], 0.9)}
                         for k in ("approach_xy_mm", "carry_xy_mm", "grasp_z_mm", "latency_s")}}))


if __name__ == "__main__":
    main()
