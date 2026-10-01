"""E-CL15 time / cost table across arms (prereg_cl15.md change 3): per episode wall clock, sim time, calls, per-call
latency (median / mean / max, from result.json calls[].latency_s), tokens in / out, cost. Arms: ep1.5 (out/cl15),
base35 (out/cl15b), astra (out/cl15c). Same 5 episodes. -> /data/harvest/out/cl15c/timing.{json,md}"""
from __future__ import annotations

import json
import os
import statistics

ARMS = [("ep1.5", "/data/harvest/out/cl15", "ep1.5"), ("base35", "/data/harvest/out/cl15b", "base35"),
        ("astra", "/data/harvest/out/cl15c", "astra")]
KINDS = ("bottle_bin", "ov_basket", "ov_behind", "ov_front", "ov_left")
OUT = "/data/harvest/out/cl15c"


def main():
    t1 = json.load(open("/data/harvest/out/cl15/t1.json"))["kinds"]
    rows = []
    for arm, root, ck in ARMS:
        for k in KINDS:
            v = t1[k]
            p = os.path.join(root, "res", ck, "none", "t1", f"{v['task']}_s{v['seed']}", "result.json")
            r = {"arm": arm, "kind": k}
            if os.path.exists(p):
                d = json.load(open(p))
                lat = [c["latency_s"] for c in d.get("calls") or [] if c.get("latency_s") is not None]
                r.update(success=d.get("success"), fail=f"{d.get('fail_stage')}/{d.get('end_reason')}",
                         n_calls=d.get("n_calls"), n_requests=len(lat), wall_s=d.get("wall_s"), sim_t=d.get("sim_t"),
                         lat_med=round(statistics.median(lat), 2) if lat else None,
                         lat_mean=round(sum(lat) / len(lat), 2) if lat else None, lat_max=max(lat) if lat else None,
                         lat_sum=round(sum(lat), 1), tok_in=d.get("tokens_in"), tok_out=d.get("tokens_out"),
                         cost_krw=d.get("cost_krw"))
            rows.append(r)
    os.makedirs(OUT, exist_ok=True)
    json.dump(rows, open(os.path.join(OUT, "timing.json"), "w"), indent=1)
    md = ["| task | arm | success | fail | calls | requests | wall s | sim s | latency med / mean / max s | "
          "sum latency s | tokens in / out | KRW |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k in KINDS:
        for r in rows:
            if r["kind"] == k:
                md.append(f"| {k} | {r['arm']} | {r.get('success')} | {r.get('fail')} | {r.get('n_calls')} | "
                          f"{r.get('n_requests')} | {r.get('wall_s')} | {r.get('sim_t')} | {r.get('lat_med')} / "
                          f"{r.get('lat_mean')} / {r.get('lat_max')} | {r.get('lat_sum')} | {r.get('tok_in')} / "
                          f"{r.get('tok_out')} | {r.get('cost_krw')} |")
    open(os.path.join(OUT, "timing.md"), "w").write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
