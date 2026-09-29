"""prereg_se2e_temporal §5: decide latency of the four input formats (batch 1, head + active wrist, same GPU).

One decide = StageB.forward_shared([sample]) = the R3 shared-prefix pass of the context + the 3 decision questions
(what the fused decide call runs): FULL = image read + preprocessing (+ pair packing) + tokenization + GPU forward;
GPU = the packed forward only (groups encoded beforehand). Formats are interleaved round-robin (warm-up first) so
drift and CPU contention hit all four alike. Weights: one checkpoint for all formats (compute does not depend on the
weights). Pod: /data/harvest/venv_train, CUDA_VISIBLE_DEVICES = one training GPU.
  python tools/se2e/temporal_latency.py --ckpt DIR --bins F --out JSON [--n 50 --reps 4 --warm 30]
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
from harvest.train import se2e_temporal as T  # noqa: E402
from harvest.train import se2e_temporal_model as TM  # noqa: E402
from harvest.train import stageb_train as TR  # noqa: E402
from harvest.train.stageb_model import HFEncoder, StageB, load_heads  # noqa: E402

FORMATS = (("single", "none"), ("video2", "none"), ("single", "motion"), ("video2", "motion"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--bins", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=50, help="val samples (head + one wrist, stratified)")
    ap.add_argument("--reps", type=int, default=4, help="passes over the n samples per format (timed)")
    ap.add_argument("--warm", type=int, default=30)
    a = ap.parse_args()
    dev = torch.device("cuda")
    bins = json.load(open(a.bins))
    data = {}
    for v, m in FORMATS:
        ss, _ = T.load_for_training_t(layout=T.LAYOUT_VIDEO2 if v == "video2" else T.LAYOUT_SINGLE,
                                      bins=bins if m == "motion" else None)
        va = [s for s in ss if s["split"] == "val" and len(s["context"]["images"]) == 2]
        data[(v, m)] = TR.stratified_val(va, a.n // 2, 0)
    keys = [s["key"] for s in data[FORMATS[0]]]
    assert all([s["key"] for s in d] == keys for d in data.values())
    bb, proc, _ = TR.load_backbone("qwen", TR.MODEL_DIR, dev, adapter=os.path.join(a.ckpt, "adapter"))
    model = load_heads(a.ckpt, bb, dev).eval()
    enc_b, enc_v = HFEncoder(proc), TM.VideoEncoder(proc)

    def setup(v):
        model.__class__ = TM.StageBT if v == "video2" else StageB
        return enc_v if v == "video2" else enc_b

    def sync():
        torch.cuda.synchronize(dev)

    def full(fmt, s):
        enc = setup(fmt[0])
        sync()
        t0 = time.perf_counter()
        with torch.no_grad():
            model.forward_shared([s], enc, dev, grad=False)
        sync()
        return time.perf_counter() - t0

    pre = {}

    def gpu(fmt, s):
        enc = setup(fmt[0])
        key = (fmt, s["key"])
        if key not in pre:
            its = [{**it, "images": s["context"]["images"]} for it in s["items"]]
            gr, book = (TM.group_rows_v if fmt[0] == "video2" else P.group_rows)(enc, its, [s["context"]["text"]])
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
        for fmt in FORMATS:
            full(fmt, data[fmt][i % len(keys)])
            gpu(fmt, data[fmt][i % len(keys)])
    res = {fmt: {"full": [], "gpu": []} for fmt in FORMATS}
    load0 = os.getloadavg()
    for r in range(a.reps):
        for i in range(len(keys)):
            for fmt in FORMATS:
                res[fmt]["full"].append(full(fmt, data[fmt][i]))
                res[fmt]["gpu"].append(gpu(fmt, data[fmt][i]))
    load1 = os.getloadavg()
    q = lambda x, p: float(np.quantile(np.asarray(x), p))  # noqa: E731
    out = {"device": torch.cuda.get_device_name(dev), "ckpt": a.ckpt, "n_samples": len(keys), "reps": a.reps,
           "warm": a.warm, "loadavg_start": load0, "loadavg_end": load1, "formats": {}}
    for fmt in FORMATS:
        tok = pre[(fmt, keys[0])][2]
        out["formats"]["+".join(fmt)] = {
            **{f"{k}_{s}": q(res[fmt][k], p) for k in ("full", "gpu") for s, p in (("p50", 0.5), ("p95", 0.95))},
            "n": len(res[fmt]["full"]), "prompt_tokens_first_sample": tok,
            "image_tokens_first_sample": pre[(fmt, keys[0])][0]["rows"][0].count(P._image_id(enc_b))}
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
