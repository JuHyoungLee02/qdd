"""E-NOV0 scoring latency (docs/stage3/prereg_nov0.md §5): the extra cost per snapshot of the novelty score on top of
the decide pass (the features are by-products of that pass). Primary variant dec/cl2n, k = 10, reference = the memory
set. One query at a time (runtime shape): centre + unit norm, similarities to the reference, top-k, mean.
  GPU: torch float32 on the current device, synchronized per query; CPU: numpy float32.
  python tools/nov0/nov0_latency.py --dir D --out JSON [--n 1000 --warm 50]
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np


def _stats(ms):
    ms = np.asarray(ms)
    return {"p50_ms": float(np.percentile(ms, 50)), "p95_ms": float(np.percentile(ms, 95)),
            "max_ms": float(ms.max()), "n": int(len(ms))}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--warm", type=int, default=50)
    ap.add_argument("--k", type=int, default=10)
    a = ap.parse_args(argv)
    M = np.load(os.path.join(a.dir, "mem.npz"))["dec"].astype(np.float32)
    Q = np.load(os.path.join(a.dir, "eval.npz"))["dec"].astype(np.float32)[:a.n + a.warm]
    mu = M.mean(0)
    Mn = (M - mu) / np.linalg.norm(M - mu, axis=1, keepdims=True)
    out = {"n_ref": int(len(M)), "dim": int(M.shape[1]), "k": a.k}
    cpu = []
    for i, q in enumerate(Q):
        t = time.perf_counter()
        z = q - mu
        z /= np.linalg.norm(z)
        d = 1.0 - Mn @ z
        float(np.partition(d, a.k - 1)[:a.k].mean())
        if i >= a.warm:
            cpu.append(1000 * (time.perf_counter() - t))
    out["cpu"] = _stats(cpu)
    import torch
    if torch.cuda.is_available():
        dev = torch.device("cuda")
        Mg, mug = torch.tensor(Mn, device=dev), torch.tensor(mu, device=dev)
        Qg = torch.tensor(Q, device=dev)
        gpu = []
        for i in range(len(Qg)):
            torch.cuda.synchronize()
            t = time.perf_counter()
            z = Qg[i] - mug
            z = z / z.norm()
            d = 1.0 - Mg @ z
            float(torch.topk(d, a.k, largest=False).values.mean())
            torch.cuda.synchronize()
            if i >= a.warm:
                gpu.append(1000 * (time.perf_counter() - t))
        out["gpu"] = _stats(gpu)
        out["device"] = torch.cuda.get_device_name(0)
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
