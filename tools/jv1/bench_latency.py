"""E-JV1 latency bench (docs/stage3/prereg_jv1.md §4-2): one model server, N held-out d1 decisions sent one at a time
(as the executor does) -> server compute latency_s and round trip p50 / p95, and the condition-R constants of that arm:
  lat_s = p50 latency rounded UP to the 20 Hz tick (0.05 s); period_dec = ceil(p95 / 0.2 s) decisions.
  python tools/jv1/bench_latency.py --url http://127.0.0.1:8171 --data /data/harvest/out/jcr/d1 --select ... --n 100
    --out /data/harvest/out/jv1/lat_B.json"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from harvest.jcr.serve import Client  # noqa: E402

import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("jcr_train", os.path.join(ROOT, "tools", "jcr", "train.py"))
J = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(J)

KEYS = ("k", "t", "tcp", "p_cmd", "v", "goal_cmd", "r_goal", "allow", "kappa", "height", "cmd_age", "q", "grip_w",
        "effort")


def main(argv=None):
    from PIL import Image
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--select", default="")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    _, va = J.load_data([a.data], "B", a.select)
    va = va[::max(1, len(va) // a.n)][:a.n]
    c = Client(a.url)
    lat, rtt, err = [], [], 0
    for i, s in enumerate(va):
        smp = {k: s[k] for k in KEYS if k in s}
        head = np.asarray(Image.open(s["_imgs"][0][1]).convert("RGB"))
        wrist = np.asarray(Image.open(s["_imgs"][1][1]).convert("RGB"))
        o = c.act(smp, head, wrist, seed=i)
        if o.get("error"):
            err += 1
        if o.get("latency_s") is not None:
            lat.append(float(o["latency_s"]))
            rtt.append(float(o["rtt_s"]))
    smi = subprocess.run(["nvidia-smi", "--query-gpu=index,utilization.gpu,memory.used", "--format=csv,noheader"],
                         capture_output=True, text=True).stdout.strip()
    p50, p95 = float(np.median(lat)), float(np.percentile(lat, 95))
    res = {"url": a.url, "n": len(lat), "errors": err, "lat_p50_s": p50, "lat_p95_s": p95,
           "rtt_p50_s": float(np.median(rtt)), "rtt_p95_s": float(np.percentile(rtt, 95)),
           "lat_s": math.ceil(p50 / 0.05 - 1e-9) * 0.05, "period_dec": max(1, math.ceil(p95 / 0.2 - 1e-9)),
           "nvidia_smi": smi}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(res, open(a.out, "w"), indent=1)
    print("BENCH " + json.dumps(res), flush=True)


if __name__ == "__main__":
    main()
