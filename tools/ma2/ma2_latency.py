"""E-MA2 (docs/stage3/prereg_ma2.md): decide latency of the three input forms, c0 (no command) / c1 (text line) /
c2 (arrow drawn on the head image IN MEMORY, as the runtime would: read JPEG -> project -> draw -> processor).

Same method as tools/cam3/cam3_latency.py: one decide = StageB.forward_shared([sample]) (shared-prefix pass of the
context + every decision question); FULL = image read (+ arrow drawing) + preprocessing + tokenization + GPU forward
(cuda synchronized), GPU = the packed forward only. Batch 1, the same eval snapshots (n, seeded sample of the fixed
eval set), each carrying its true command (e0), formats interleaved round-robin after a warm-up, one checkpoint
(compute does not depend on the weights). Rule input: FULL p95 per format.
  python tools/ma2/ma2_latency.py --ckpt DIR --pool <views> --rows <eval rows> --eval-set JSON --out JSON
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
from PIL import Image  # noqa: E402

from harvest.train import prefix_share as P  # noqa: E402
from harvest.train import r2_ma2 as M  # noqa: E402
from harvest.train import stageb_data as D  # noqa: E402
from harvest.train import stageb_train as TR  # noqa: E402
from harvest.train.stageb_model import HFEncoder, load_heads  # noqa: E402

FORMATS = ("c0", "c1", "c2")
DRAW = "MA2DRAW::"
_SPECS: dict = {}
_open0 = Image.open


def _open(fp, *x, **kw):
    """PIL open; a DRAW-marked path = the head JPEG with the command arrow drawn in memory."""
    if isinstance(fp, str) and fp.startswith(DRAW):
        path = fp[len(DRAW):].split("#", 1)[0]
        tcp, c = _SPECS[fp]
        return M.draw_arrow(_open0(path).convert("RGB"), tcp, c)
    return _open0(fp, *x, **kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--pool", required=True)
    ap.add_argument("--rows", required=True)
    ap.add_argument("--eval-set", required=True)
    ap.add_argument("--ma2-root", default=M.MA2_ROOT)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--reps", type=int, default=4)
    ap.add_argument("--warm", type=int, default=30)
    a = ap.parse_args()
    dev = torch.device("cuda")
    ids = json.load(open(a.eval_set))["ids"]
    pick = sorted(random.Random(0).sample(ids, a.n))
    samples, _ = D.load_for_training("r2", pool=a.pool, rows=a.rows)
    by = {M.sample_id(s["context"]["images"][0][1]): s for s in samples}
    table = M.read_table(a.ma2_root, a.pool)
    data = {f: [] for f in FORMATS}
    for i in pick:
        s, r = by[i], table[i]
        c = M.eval_cmd(r["cmd"], 0)
        data["c0"].append(s)
        data["c1"].append(M.with_command(s, "c1", c, relabel=False))
        mark = DRAW + s["context"]["images"][0][1] + "#" + i
        _SPECS[mark] = (np.asarray(r["tcp"], float), c)
        data["c2"].append(M.with_command(s, "c2", c, arrow_path=mark, relabel=False))
    Image.open = _open
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

    def gpu(f, j, s):
        key = (f, j)
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

    n = len(pick)
    for i in range(a.warm):
        for f in FORMATS:
            full(data[f][i % n])
            gpu(f, i % n, data[f][i % n])
    res = {f: {"full": [], "gpu": []} for f in FORMATS}
    load0 = os.getloadavg()
    for _ in range(a.reps):
        for j in range(n):
            for f in FORMATS:
                res[f]["full"].append(full(data[f][j]))
                res[f]["gpu"].append(gpu(f, j, data[f][j]))
    load1 = os.getloadavg()
    q = lambda x, p: float(np.quantile(np.asarray(x), p))  # noqa: E731
    img = P._image_id(enc)
    out = {"device": torch.cuda.get_device_name(dev), "ckpt": a.ckpt, "n_samples": n, "reps": a.reps,
           "warm": a.warm, "loadavg_start": load0, "loadavg_end": load1, "ids": pick, "formats": {}}
    for f in FORMATS:
        toks = [pre[(f, j)][0]["rows"][0].count(img) for j in range(n)]
        out["formats"][f] = {**{f"{k}_{s}": q(res[f][k], p) for k in ("full", "gpu")
                                for s, p in (("p50", 0.5), ("p95", 0.95))},
                             "n": len(res[f]["full"]), "image_tokens_mean": float(np.mean(toks)),
                             "prompt_tokens_mean": float(np.mean([pre[(f, j)][2] for j in range(n)]))}
    out["full_p95_ratio_c2_c1"] = out["formats"]["c2"]["full_p95"] / out["formats"]["c1"]["full_p95"]
    out["full_p95_ratio_c1_c0"] = out["formats"]["c1"]["full_p95"] / out["formats"]["c0"]["full_p95"]
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "ids"}, indent=1))


if __name__ == "__main__":
    main()
