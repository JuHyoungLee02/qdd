"""E-CAM3 (docs/stage3/prereg_cam3.md): decide latency, head + active wrist (cam2) vs head + both wrists (cam3).

Measured as tools/se2e/temporal_latency.py (prereg_se2e_temporal §5): one decide = StageB.forward_shared([sample])
(the R3 shared-prefix pass of the context + the 3 decision questions); FULL = image read + preprocessing +
tokenization + GPU forward (cuda synchronized), GPU = the packed forward only. Batch 1, the motion line on in both
formats, the SAME val snapshots (single-arm rows, stratified n/2 per source, seed 0), formats interleaved
round-robin after a warm-up, one checkpoint (compute does not depend on the weights). Rule input: FULL p95 ratio.
  python tools/cam3/cam3_latency.py --ckpt DIR --bins F --cam3-root DIR --out JSON [--n 50 --reps 4 --warm 30]
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

from harvest.train import prefix_share as P  # noqa: E402
from harvest.train import se2e_cam3 as C  # noqa: E402
from harvest.train import se2e_temporal as T  # noqa: E402
from harvest.train import stageb_train as TR  # noqa: E402
from harvest.train.stageb_model import HFEncoder, load_heads  # noqa: E402

FORMATS = ("cam2", "cam3")
C1 = "/data/harvest/data/se2e_c1/conv"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--bins", required=True)
    ap.add_argument("--cam3-root", default=C.CAM3_ROOT)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--reps", type=int, default=4)
    ap.add_argument("--warm", type=int, default=30)
    a = ap.parse_args()
    dev = torch.device("cuda")
    bins = json.load(open(a.bins))
    data = {}
    for f in FORMATS:
        ss, _ = T.load_for_training_t(C1, image_root=C1, bins=bins)
        va = [s for s in ss if s["split"] == "val" and len(s["context"]["images"]) == 2]
        va = TR.stratified_val(va, a.n // 2, 0)
        if f == "cam3":
            C.apply_cam3(va, a.cam3_root)
        data[f] = va
    keys = [s["key"] for s in data["cam2"]]
    assert [s["key"] for s in data["cam3"]] == keys
    assert all(len(s["context"]["images"]) == 3 for s in data["cam3"])
    bb, proc, _ = TR.load_backbone("qwen", TR.MODEL_DIR, dev, adapter=os.path.join(a.ckpt, "adapter"))
    model = load_heads(a.ckpt, bb, dev).eval()
    enc = HFEncoder(proc)

    def sync():
        torch.cuda.synchronize(dev)

    def full(s):
        sync()
        t0 = time.perf_counter()
        with torch.no_grad():
            model.forward_shared([s], enc, dev, grad=False)
        sync()
        return time.perf_counter() - t0

    pre = {}

    def gpu(f, s):
        key = (f, s["key"])
        if key not in pre:
            its = [{**it, "images": s["context"]["images"]} for it in s["items"]]
            gr, book = P.group_rows(enc, its, [s["context"]["text"]])
            req = {}
            P._logits_req(0, book, req)
            pre[key] = (gr, req, len(gr["rows"][0]))
        gr, req, _ = pre[key]
        sync()
        t0 = time.perf_counter()
        with torch.no_grad():
            P.shared_forward(model.backbone, [gr], dev, req, hidden_of=[(0, 0)], layer=model.layer, pad_id=enc.pad,
                             enc=enc)
        sync()
        return time.perf_counter() - t0

    for i in range(a.warm):
        for f in FORMATS:
            full(data[f][i % len(keys)])
            gpu(f, data[f][i % len(keys)])
    res = {f: {"full": [], "gpu": []} for f in FORMATS}
    load0 = os.getloadavg()
    for _ in range(a.reps):
        for i in range(len(keys)):
            for f in FORMATS:
                res[f]["full"].append(full(data[f][i]))
                res[f]["gpu"].append(gpu(f, data[f][i]))
    load1 = os.getloadavg()
    q = lambda x, p: float(np.quantile(np.asarray(x), p))  # noqa: E731
    img = P._image_id(enc)
    out = {"device": torch.cuda.get_device_name(dev), "ckpt": a.ckpt, "n_samples": len(keys), "reps": a.reps,
           "warm": a.warm, "loadavg_start": load0, "loadavg_end": load1, "formats": {}}
    for f in FORMATS:
        toks = [pre[(f, k)][0]["rows"][0].count(img) for k in keys]
        out["formats"][f] = {**{f"{k}_{s}": q(res[f][k], p) for k in ("full", "gpu")
                                for s, p in (("p50", 0.5), ("p95", 0.95))},
                             "n": len(res[f]["full"]), "image_tokens_mean": float(np.mean(toks)),
                             "image_tokens_min": int(min(toks)), "image_tokens_max": int(max(toks)),
                             "prompt_tokens_mean": float(np.mean([pre[(f, k)][2] for k in keys]))}
    out["full_p95_ratio"] = out["formats"]["cam3"]["full_p95"] / out["formats"]["cam2"]["full_p95"]
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
