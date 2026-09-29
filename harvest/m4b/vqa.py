"""V1z / V1q: world-side predicates asked as typed yes/no questions to Qwen3-VL-4B (pod, venv_train).

  python -m harvest.m4b.vqa score --out FILE [--adapter DIR] --splits fi_eval,fi_cal:10-14,pool_eval
  python -m harvest.m4b.vqa train --out RUNDIR            (V1q: LoRA SFT, stage-A recipe, 1 epoch)

Prompt = D27 layout (system -> head -> right wrist) + IMG state + "Question: ...", options yes / no; the answer
probability is the option-set renormalized trie probability (stage A's scorer, shared-prefix path).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import time

import numpy as np

from . import spec as FS

BASE = "/data/harvest/models/Qwen3-VL-4B-Instruct"
QUESTIONS = {
    "on_tp": "Is the red mug resting on the blue tray?",
    "contact_tp": "Is the red mug touching the blue tray?",
    "lifted_t": "Is the red mug lifted off the table (its bottom at least 3 cm above the table)?",
    "near_tp": "Is the center of the red mug within 5 cm of the center of the blue tray?",
    "above_tp": "Is the red mug above the blue tray without touching it?",
}
NAMES = ["yes", "no"]


def item_text(ctx: str, q: str) -> str:
    return f"{ctx}\n\nQuestion: {q}\nAnswer with one option.\nOptions:\n- yes\n- no"


def items_of(s: dict) -> list:
    out = []
    for p, q in QUESTIONS.items():
        v = s["truth"].get(p)
        out.append({"key": s["key"], "question": p, "qid": p, "text": item_text(s["ctx"], q), "images": s["images"],
                    "names": list(NAMES), "target": None if v is None else (["yes"] if v else ["no"])})
    return out


def select(snaps, spec: str):
    keep = []
    for part in spec.split(","):
        name, _, rng = part.partition(":")
        lo, hi = (int(x) for x in rng.split("-")) if rng else (-1, 10 ** 9)
        keep += [s for s in snaps if s["split"] == name and lo <= s["seed"] <= hi]
    return keep


def _load(a):
    from .vhead import load_all
    _, snaps = load_all(a.fi, a.pool)
    return snaps


def cmd_score(a):
    import torch

    from ..train.stagea_train import Scorer, batch_logprobs, load_model
    snaps = select(_load(a), a.splits)
    dev = torch.device("cuda")
    model, proc = load_model(a.model, dev, adapter=a.adapter or None)
    model.eval()
    sc = Scorer(proc, "")
    done = set()
    if os.path.exists(a.out):
        done = {json.loads(x)["key"] for x in open(a.out)}
    fo = open(a.out, "a")
    t0 = time.time()
    todo = [s for s in snaps if s["key"] not in done]
    for b in range(0, len(todo), a.micro):
        ss = todo[b:b + a.micro]
        its = [it for s in ss for it in items_of(s)]
        with torch.no_grad():
            lps = batch_logprobs(model, sc, its, dev, share=True, micro=a.micro)
        for j, s in enumerate(ss):
            p = {}
            for it, lp in zip(its[5 * j:5 * j + 5], lps[5 * j:5 * j + 5]):
                p[it["question"]] = float(math.exp(float(lp["yes"])))
            fo.write(json.dumps({"key": s["key"], "p_yes": p}) + "\n")
        fo.flush()
        if (b // a.micro) % 20 == 0:
            print(json.dumps({"done": b + len(ss), "of": len(todo), "s": round(time.time() - t0, 1)}), flush=True)
    print(json.dumps({"finished": len(todo), "s": round(time.time() - t0, 1)}), flush=True)


def cmd_train(a):
    import torch

    from ..train.stagea_loss import set_nll
    from ..train.stagea_train import Scorer, batch_logprobs, load_model
    snaps = select(_load(a), a.splits)
    items_by = [[it for it in items_of(s) if it["target"] is not None] for s in snaps]
    rng = random.Random(0)
    rng.shuffle(items_by)
    n_items = sum(len(x) for x in items_by)
    dev = torch.device("cuda")
    torch.manual_seed(0)
    model, proc = load_model(a.model, dev, lora={"r": 32, "alpha": 64, "dropout": 0.05})
    sc = Scorer(proc, "")
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=a.lr, weight_decay=0.0)
    steps = math.ceil(n_items / a.accum)
    w = max(1, math.ceil(0.03 * steps))
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: (s + 1) / w if s < w else 0.5 * (1 + math.cos(math.pi * min(1.0, (s - w) / max(1, steps - w)))))
    os.makedirs(a.out, exist_ok=True)
    log = open(os.path.join(a.out, "log.jsonl"), "w")
    model.train()
    t0, step, seen, acc_n, acc_loss = time.time(), 0, 0, 0, 0.0
    for b in range(0, len(items_by), a.micro):
        its = [it for x in items_by[b:b + a.micro] for it in x]
        if not its:
            continue
        lps = batch_logprobs(model, sc, its, dev, share=True, micro=a.micro)
        loss = torch.stack([set_nll(lp, it["target"]) for it, lp in zip(its, lps)])
        (loss.sum() / a.accum).backward()
        acc_n += len(its)
        acc_loss += float(loss.sum())
        seen += len(its)
        if acc_n >= a.accum or b + a.micro >= len(items_by):
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
            sched.step()
            opt.zero_grad(set_to_none=True)
            step += 1
            r = {"step": step, "of": steps, "loss": round(acc_loss / acc_n, 5), "items": seen,
                 "s": round(time.time() - t0, 1)}
            log.write(json.dumps(r) + "\n")
            log.flush()
            print(json.dumps(r), flush=True)
            acc_n, acc_loss = 0, 0.0
    model.save_pretrained(os.path.join(a.out, "adapter"))
    json.dump({"n_snapshots": len(items_by), "n_items": n_items, "steps": step, "splits": a.splits, "lr": a.lr,
               "accum": a.accum}, open(os.path.join(a.out, "config.json"), "w"), indent=1)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["score", "train"])
    ap.add_argument("--fi", default="/data/harvest/m4b/fidev")
    ap.add_argument("--pool", default="/data/harvest/data/pool")
    ap.add_argument("--model", default=BASE)
    ap.add_argument("--adapter", default="")
    ap.add_argument("--splits", default="fi_eval,fi_cal:10-14,pool_eval")
    ap.add_argument("--out", required=True)
    ap.add_argument("--micro", type=int, default=8)
    ap.add_argument("--accum", type=int, default=64)
    ap.add_argument("--lr", type=float, default=1e-4)
    a = ap.parse_args(argv)
    {"score": cmd_score, "train": cmd_train}[a.cmd](a)


if __name__ == "__main__":
    main()
