"""E-JV1 arm B training / offline evaluation (docs/stage3/prereg_jv1.md §3). venv_train, one GPU.
Same data, selection, split, sampling weights, branches (K) and step count as JCR1-0 (tools/jcr/train.py, imported):
  train : python tools/jv1/train_b.py train --data /data/harvest/out/jcr/d1 --select /data/harvest/out/jcr/d1_select.json
          --out /data/harvest/ckpt/jv1/b_P [--label P|A --steps 4000 --batch 8 --K 2 --lr 2e-4 --mb 6 --save-every 500]
  eval  : python tools/jv1/train_b.py eval --ckpt DIR --data ... --select ... --out DIR/offline.json
Every step = `batch` real samples, each with K forced-command branches (features.branch, same rule as JCR), i.e. the
same 8 x (1 + K) supervised samples as JCR; the branches only change the command text (no shared backbone pass, the
extra cost is recorded as GPU seconds). Offline = JCR's offline_eval (rows from the rule controller, so the numbers are
on JCR's scale) + waypoint error (mm, through the text quantisation) + parse rate."""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from harvest.jcr import features as FT  # noqa: E402
from harvest.jv1 import text as X  # noqa: E402

_spec = importlib.util.spec_from_file_location("jcr_train", os.path.join(ROOT, "tools", "jcr", "train.py"))
J = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(J)
MODEL_DIR = J.MODEL_DIR
MODE_OF = {"P": "B", "A": "A"}  # JCR loader mode giving the matching chunk label (P <-> rules B / C, A <-> hard clip)


def paths(s):
    return [p for _, p in s["_imgs"]]


def make_model(a, device):
    import torch

    from harvest.jv1.model import JV1
    from harvest.train.stageb_train import load_backbone
    bb, proc, _ = load_backbone("qwen", MODEL_DIR, device, lora={"r": 32, "alpha": 64, "dropout": 0.05},
                                dtype=torch.bfloat16)
    bb.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    bb.enable_input_require_grads()
    return JV1(bb, proc, a.label)


def cmd_train(a):
    import torch
    torch.manual_seed(a.seed)
    rng = np.random.default_rng(a.seed)
    mode = MODE_OF[a.label]
    tr, va = J.load_data(a.data, mode, a.select)
    print(json.dumps({"train": len(tr), "val": len(va), "label": a.label, "mode": mode}), flush=True)
    device = "cuda"
    m = make_model(a, device)
    lora = [p for p in m.backbone.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(lora, lr=a.lr, weight_decay=0.0)
    wu = max(1, int(0.03 * a.steps))
    sch = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: (s + 1) / wu if s < wu else 0.5 * (1 + math.cos(math.pi * min(1.0, (s - wu) / max(1, a.steps - wu)))))
    w = J.weights(tr)
    os.makedirs(a.out, exist_ok=True)
    log = open(os.path.join(a.out, "train.jsonl"), "a")
    t0 = time.time()
    for step in range(a.steps):
        idx = rng.choice(len(tr), size=a.batch, p=w)
        items = []
        for i in idx:
            items += [(paths(tr[i]), tr[i])] + [(paths(tr[i]), FT.branch(tr[i], rng, mode=mode)) for _ in range(a.K)]
        m.backbone.train()
        opt.zero_grad(set_to_none=True)
        tot = 0.0
        for j in range(0, len(items), a.mb):
            mb = items[j:j + a.mb]
            with torch.autocast("cuda", dtype=torch.bfloat16):
                loss = m.losses(mb, device) * (len(mb) / len(items))
            loss.backward()
            tot += float(loss)
        gn = torch.nn.utils.clip_grad_norm_(lora, 1.0)
        opt.step()
        sch.step()
        if step % 20 == 0 or step == a.steps - 1:
            el = time.time() - t0
            rec = {"step": step, "loss": round(tot, 5), "gn": round(float(gn), 3),
                   "s_per_step": round(el / (step + 1), 3), "gpu_s": round(el, 1)}
            log.write(json.dumps(rec) + "\n")
            log.flush()
            print("STEP " + json.dumps(rec), flush=True)
        if a.save_every and (step + 1) % a.save_every == 0 and step + 1 < a.steps:
            m.save(os.path.join(a.out, f"step{step + 1}"), {"step": step + 1, "gpu_s": round(time.time() - t0, 1)})
    m.save(os.path.join(a.out, "last"), {"step": a.steps, "data": a.data, "n_train": len(tr), "args": vars(a),
                                         "gpu_s": round(time.time() - t0, 1)})
    if va:
        res = offline(m, va[:a.max_val] if a.max_val else va, device, mode, a.label)
        json.dump(res, open(os.path.join(a.out, "last", "offline.json"), "w"), indent=1)
        print("OFFLINE " + json.dumps(res), flush=True)
    print("TRAIN_DONE", flush=True)


def offline(m, va, device, mode, label):
    m.eval()
    res = J.offline_eval(m, None, va, device, seed=0, mode=mode)
    err, ok, lat = [], 0, []
    for s in va:
        t0 = time.perf_counter()
        o = m.predict(None, s["_imgs"], [s], device)[0]
        lat.append(time.perf_counter() - t0)
        if o["parse_ok"]:
            ok += 1
            err.append(float(np.linalg.norm(np.asarray(o["c_hat"]) - X.waypoint(s, label))) * 1e3)
    res.update(parse_rate=ok / max(len(va), 1), waypoint_err_mm_p50=float(np.median(err)) if err else None,
               waypoint_err_mm_p90=float(np.percentile(err, 90)) if err else None,
               predict_s_p50=float(np.median(lat)), predict_s_p95=float(np.percentile(lat, 95)))
    return res


def cmd_eval(a):
    from harvest.jv1.model import load
    mode = MODE_OF[a.label]
    _, va = J.load_data(a.data, mode, a.select)
    m, _ = load(a.ckpt, MODEL_DIR, "cuda")
    res = offline(m, va[:a.max_val] if a.max_val else va, "cuda", mode, m.label)
    json.dump(res, open(a.out, "w"), indent=1)
    print("OFFLINE " + json.dumps(res), flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["train", "eval"])
    ap.add_argument("--data", action="append", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ckpt", default=None)
    ap.add_argument("--select", default="")
    ap.add_argument("--label", default="P", choices=["P", "A"])
    ap.add_argument("--steps", type=int, default=4000)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--K", type=int, default=2)
    ap.add_argument("--mb", type=int, default=6, help="micro-batch (sequences) for gradient accumulation")
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--max-val", type=int, default=400)
    ap.add_argument("--save-every", type=int, default=500)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    (cmd_train if a.mode == "train" else cmd_eval)(a)


if __name__ == "__main__":
    main()
