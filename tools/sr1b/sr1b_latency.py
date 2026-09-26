"""E-SR1b (docs/stage3/prereg_sr1b.md): decide -> chunk latency without and with decision CFG.

FULL = one runtime decide -> chunk step, batch 1: image read + preprocessing + tokenization + the shared-prefix
forward (StageB.forward_shared: context hidden states + every decision question), argmax decisions, StageB.cond, and
the expert's 10 Euler steps -- plain (sample_actions) or CFG (sample_actions_cfg, conditional + null rows in one
batched pass; the cost does not depend on w != 1) -- cuda synchronized. EXPERT = the Euler part only. The same eval
snapshots (n, seeded sample of the fixed eval set), the two modes interleaved after a warm-up, one checkpoint (compute
does not depend on the weights). Rule input: full_p95_ratio_cfg_plain.
  python tools/sr1b/sr1b_latency.py --ckpt DIR --pool <views> --rows <eval rows> --eval-set JSON --out JSON
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time

os.environ.setdefault("TORCH_DISABLE_NATIVE_JIT", "1")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

import numpy as np  # noqa: E402
import torch  # noqa: E402

from harvest.train import r2_ma2 as M  # noqa: E402
from harvest.train import sr1b as S  # noqa: E402
from harvest.train import stageb_data as D  # noqa: E402
from harvest.train import stageb_train as TR  # noqa: E402
from harvest.train.stageb_model import HFEncoder, load_heads  # noqa: E402

MODES = {"plain": 1.0, "cfg": 2.0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--pool", required=True)
    ap.add_argument("--rows", required=True)
    ap.add_argument("--eval-set", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--reps", type=int, default=4)
    ap.add_argument("--warm", type=int, default=30)
    ap.add_argument("--steps", type=int, default=10)
    a = ap.parse_args()
    dev = torch.device("cuda")
    ids = json.load(open(a.eval_set))["ids"]
    pick = sorted(random.Random(0).sample(ids, a.n))
    samples, _ = D.load_for_training("r2", pool=a.pool, rows=a.rows)
    by = {}
    for s in samples:
        by.setdefault(M.sample_id(s["context"]["images"][0][1]), s)
    data = [by[i] for i in pick]
    bb, proc, _ = TR.load_backbone("qwen", TR.MODEL_DIR, dev, adapter=os.path.join(a.ckpt, "adapter"))
    model = load_heads(a.ckpt, bb, dev).eval()
    enc = HFEncoder(proc)
    H, A = model.expert.cfg.horizon, model.expert.cfg.act_dim

    def sync():
        torch.cuda.synchronize(dev)

    def step(s, w):
        sync()
        t0 = time.perf_counter()
        with torch.no_grad():
            ctx, mask, lps = model.forward_shared([s], enc, dev, grad=False)
            preds = {it["question"]: max(lp, key=lambda n: float(lp[n])) for it, lp in zip(s["items"], lps[0])}
            cond = model.cond([{**s, "committed": {**s["committed"], **preds}}], ctx, mask, dev)
            noise = torch.randn(1, H, A, device=dev)
            sync()
            t1 = time.perf_counter()
            S.sample_actions_cfg(model.expert, cond, w, a.steps, noise)
        sync()
        t2 = time.perf_counter()
        return t2 - t0, t2 - t1

    n = len(data)
    for i in range(a.warm):
        for w in MODES.values():
            step(data[i % n], w)
    res = {m: {"full": [], "expert": []} for m in MODES}
    load0 = os.getloadavg()
    for _ in range(a.reps):
        for j in range(n):
            for m, w in MODES.items():
                f, e = step(data[j], w)
                res[m]["full"].append(f)
                res[m]["expert"].append(e)
    load1 = os.getloadavg()
    q = lambda x, p: float(np.quantile(np.asarray(x), p))  # noqa: E731
    out = {"device": torch.cuda.get_device_name(dev), "ckpt": a.ckpt, "n_samples": n, "reps": a.reps,
           "warm": a.warm, "steps": a.steps, "loadavg_start": load0, "loadavg_end": load1, "ids": pick, "modes": {}}
    for m in MODES:
        out["modes"][m] = {f"{k}_{s}": q(res[m][k], p) for k in ("full", "expert") for s, p in (("p50", 0.5),
                                                                                              ("p95", 0.95))}
        out["modes"][m]["n"] = len(res[m]["full"])
    out["full_p95_ratio_cfg_plain"] = out["modes"]["cfg"]["full_p95"] / out["modes"]["plain"]["full_p95"]
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "ids"}, indent=1))


if __name__ == "__main__":
    main()
