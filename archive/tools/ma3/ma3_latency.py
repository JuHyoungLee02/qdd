"""E-MA3 (docs/stage3/prereg_ma3.md): FULL decide + chunk latency, baseline expert vs kvcond@v1 expert.

As tools/se2e/temporal_latency.py, extended to the chunk because the change is in the expert: FULL = image read +
preprocessing + tokenization + the shared-prefix forward (context + 3 questions; with kvcond the K / V capture hooks)
+ cond + expert sampling (10 Euler steps), cuda synchronized; DECIDE = the forward_shared part alone. Batch 1, motion
line on, the same val snapshots (single-arm rows, stratified n/2 per source, seed 0), interleaved round-robin after
a warm-up. One backbone (the baseline checkpoint's adapter) shared by both head sets (compute does not depend on the
weights). Rule input: FULL p95 ratio kv / base.
  python tools/ma3/ma3_latency.py --base CKPT --kv CKPT --bins F --out JSON [--n 50 --reps 4 --warm 30]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

os.environ.setdefault("TORCH_DISABLE_NATIVE_JIT", "1")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

import numpy as np  # noqa: E402
import torch  # noqa: E402

from harvest.train import se2e_kvcond as K  # noqa: E402
from harvest.train import se2e_temporal as T  # noqa: E402
from harvest.train import stageb_train as TR  # noqa: E402
from harvest.train.stageb_expert import sample_actions  # noqa: E402
from harvest.train.stageb_model import HFEncoder, load_heads  # noqa: E402

C1 = "/data/harvest/data/se2e_c1/conv"
ARMS = ("base", "kv")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--kv", required=True)
    ap.add_argument("--bins", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--reps", type=int, default=4)
    ap.add_argument("--warm", type=int, default=30)
    a = ap.parse_args()
    dev = torch.device("cuda")
    ss, _ = T.load_for_training_t(C1, image_root=C1, bins=json.load(open(a.bins)))
    va = [s for s in ss if s["split"] == "val" and len(s["context"]["images"]) == 2]
    data = TR.stratified_val(va, a.n // 2, 0)
    bb, proc, _ = TR.load_backbone("qwen", TR.MODEL_DIR, dev, adapter=os.path.join(a.base, "adapter"))
    models = {"base": load_heads(a.base, bb, dev).eval(), "kv": K.load_heads_kv(a.kv, bb, dev).eval()}
    assert isinstance(models["kv"], K.StageBKV) and not isinstance(models["base"], K.StageBKV)
    enc = HFEncoder(proc)
    noise = torch.randn(1, models["base"].expert.cfg.horizon, models["base"].expert.cfg.act_dim,
                        generator=torch.Generator().manual_seed(0)).to(dev)

    def sync():
        torch.cuda.synchronize(dev)

    def run(arm, s):
        m = models[arm]
        sync()
        t0 = time.perf_counter()
        with torch.no_grad():
            ctx, mask, _ = m.forward_shared([s], enc, dev, grad=False)
            sync()
            t1 = time.perf_counter()
            sample_actions(m.expert, m.cond([s], ctx, mask, dev), 10, noise)
        sync()
        t2 = time.perf_counter()
        return t2 - t0, t1 - t0

    for i in range(a.warm):
        for arm in ARMS:
            run(arm, data[i % len(data)])
    res = {arm: {"full": [], "decide": []} for arm in ARMS}
    load0 = os.getloadavg()
    for _ in range(a.reps):
        for s in data:
            for arm in ARMS:
                f, d = run(arm, s)
                res[arm]["full"].append(f)
                res[arm]["decide"].append(d)
    load1 = os.getloadavg()
    q = lambda x, p: float(np.quantile(np.asarray(x), p))  # noqa: E731
    out = {"device": torch.cuda.get_device_name(dev), "base": a.base, "kv": a.kv, "n_samples": len(data),
           "reps": a.reps, "warm": a.warm, "loadavg_start": load0, "loadavg_end": load1, "arms": {}}
    for arm in ARMS:
        out["arms"][arm] = {f"{k}_{s}": q(res[arm][k], p) for k in ("full", "decide")
                            for s, p in (("p50", 0.5), ("p95", 0.95))}
        out["arms"][arm]["n"] = len(res[arm]["full"])
    out["full_p95_ratio"] = out["arms"]["kv"]["full_p95"] / out["arms"]["base"]["full_p95"]
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
