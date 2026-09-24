"""Stage-A SFT of the Jev-L typed selector (canon §51-§52, D26 §1.4, docs/stage3/results/stageA_pipeline.md).

  train   --pool DIR --rule R --run NAME [--state S1] ...      LoRA SFT, early stopping on val (POOL `eval`) NLL
  parity  --dev DIR --acc JSONL [--adapter DIR] --n N          HF option probs vs the recorded vLLM Jev-L probs
  load    --adapter DIR --pool DIR --rule R                    reload a saved adapter and score a few val items

Prompt = jevl.JevLClient._body exactly: system jevl.SYSTEM, user [head image, jevl.question_text(...)], generation
prompt; state text = E3-lite S1 on a 1 mm grid by default (canon §53-§54); the option probabilities are jevl's trie
decomposition (stagea_loss). Targets (--target-source): labels_v2 (default, canon §54: observation-defined answers,
file <folder>.labels_v2.jsonl), outcome (labeler best set under --rule, auxiliary), or py:<module>:<factory> with
factory(pool_dir, seed) -> stagea_data source. Never the pool oracle.
--pool takes one or more episode folders (comma separated); DEV folders need --dev-val-seeds (smoke only). Model Qwen3-VL-4B-Instruct BF16,
LoRA r32 a64 dropout 0.05 on every LLM linear layer (q,k,v,o,gate,up,down of model.language_model), vision tower,
merger and lm_head frozen. AdamW lr 1e-4, cosine, 3 % warmup, 1-2 epochs.
Pod: run with CUDA_VISIBLE_DEVICES=1 (smoke) from /data/harvest/venv_train; every output under /data/harvest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import sys
import time

MODEL_DIR = "/data/harvest/models/Qwen3-VL-4B-Instruct"
MODEL_REV = "ebb281ec70b05090aa6165b016eac8ec08e71b17"
LORA_TARGET = r".*language_model\.layers\.\d+\.(self_attn\.(q|k|v|o)_proj|mlp\.(gate|up|down)_proj)"
END_TOKEN = "<|im_end|>"


def _utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def file_sha(paths):
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    return {p: hashlib.sha256(open(os.path.join(root, p), "rb").read()).hexdigest()[:12] for p in paths}


PROMPT_FILES = ("harvest/clients/jevl.py", "harvest/deccall_snap.py", "harvest/jevcall.py", "harvest/options.py",
                "harvest/e3lite.py",
                "harvest/serialize.py", "harvest/train/stagea_data.py", "harvest/train/stagea_loss.py")


class Scorer:
    """Processor + tokenized option tries; item -> {name: log p~} with a given model."""

    def __init__(self, processor, image_root):
        from ..clients.jevl import SYSTEM
        self.p, self.root, self.system = processor, image_root, SYSTEM
        tk = processor.tokenizer
        e = tk.encode(END_TOKEN, add_special_tokens=False)
        if len(e) != 1:
            raise ValueError(f"end token {END_TOKEN!r} is not one token: {e}")
        self.end, self.pad = e[0], tk.pad_token_id if tk.pad_token_id is not None else e[0]
        self._tries = {}

    def trie(self, names):
        from ..clients.jevl import option_trie
        key = tuple(names)
        if key not in self._tries:
            tok = {n: self.p.tokenizer.encode(n, add_special_tokens=False) for n in names}
            self._tries[key] = (tok, option_trie(tok, self.end))
        return self._tries[key]

    def inputs(self, text, image_path, device):
        from PIL import Image
        msgs = [{"role": "system", "content": self.system}, {"role": "user", "content": []}]
        imgs = None
        if image_path is not None:
            msgs[1]["content"].append({"type": "image"})
            imgs = [Image.open(os.path.join(self.root, image_path)).convert("RGB")]
        msgs[1]["content"].append({"type": "text", "text": text})
        prompt = self.p.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        x = self.p(text=[prompt], images=imgs, return_tensors="pt")
        return {k: v.to(device) for k, v in x.items()}

    def logprobs(self, model, item, device):
        from .stagea_loss import item_logprobs
        tok, trie = self.trie(item["names"])
        return item_logprobs(model, self.inputs(item["text"], item.get("image"), device), tok, trie, self.end,
                             self.pad)


def load_model(model_dir, device, adapter=None, lora=None):
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor
    proc = AutoProcessor.from_pretrained(model_dir)
    model = AutoModelForImageTextToText.from_pretrained(model_dir, dtype=torch.bfloat16, attn_implementation="sdpa")
    model.to(device)
    if adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter, is_trainable=False)
    elif lora:
        from peft import LoraConfig, get_peft_model
        model = get_peft_model(model, LoraConfig(r=lora["r"], lora_alpha=lora["alpha"], lora_dropout=lora["dropout"],
                                                 target_modules=LORA_TARGET, bias="none"))
    return model, proc


def select_val(va, n, seed):
    """Deterministic validation subset (the same in train and load)."""
    if not n:
        return va
    va = sorted(va, key=lambda x: (x["key"], x["question"]))
    random.Random(seed + 1).shuffle(va)
    return va[:n]


def evaluate(model, scorer, items, device):
    import torch
    from .stagea_loss import set_nll
    was = model.training
    model.eval()
    nll, acc, pset, per_q = [], [], [], {}
    with torch.no_grad():
        for it in items:
            lp = scorer.logprobs(model, it, device)
            v = float(set_nll(lp, it["target"]))
            nll.append(v)
            top = max(lp, key=lambda n: float(lp[n]))
            acc.append(top in it["target"])
            pset.append(math.exp(-v))
            per_q.setdefault(it["question"], []).append(v)
    model.train(was)
    return {"nll": sum(nll) / len(nll), "acc": sum(acc) / len(acc), "p_target": sum(pset) / len(pset),
            "n": len(nll), "nll_q": {q: round(sum(v) / len(v), 4) for q, v in per_q.items()}}


def source_factory(spec, rule, partial, labels_v2=None):
    """'labels_v2' | 'outcome' (labeler best sets under `rule`) | 'py:pkg.mod:fn' (a stagea_data source factory)."""
    from .stagea_data import labels_v2_factory, outcome_factory
    if spec == "labels_v2":
        return labels_v2_factory(labels_v2)
    if spec == "outcome":
        if not rule:
            raise SystemExit("--rule is required with --target-source outcome")
        return outcome_factory(rule, partial)
    if spec.startswith("py:"):
        import importlib
        mod, fn = spec[3:].rsplit(":", 1)
        return getattr(importlib.import_module(mod), fn)
    raise SystemExit(f"--target-source {spec!r}: labels_v2 | outcome | py:<module>:<factory>")


def _seedset(spec):
    out = set()
    for part in filter(None, spec.split(",")):
        a, _, b = part.partition("-")
        out |= set(range(int(a), int(b or a) + 1))
    return out


def _items(a):
    from .stagea_data import load_pool
    dev = _seedset(a.dev_val_seeds) if a.dev_val_seeds else None
    items = []
    for folder in filter(None, a.pool.split(",")):
        items += load_pool(folder, state=a.state, partial=a.partial, step_cm=a.step_cm, dev_val_seeds=dev,
                           source_factory=source_factory(a.target_source, a.rule, a.partial, a.labels_v2 or None))
    return items


def cmd_train(a):
    import torch
    from transformers import get_cosine_schedule_with_warmup

    from .stagea_loss import set_nll
    out = os.path.join(a.out_root, a.run)
    if os.path.exists(os.path.join(out, "config.json")) and not a.overwrite:
        raise SystemExit(f"{out} exists (use --overwrite)")
    os.makedirs(out, exist_ok=True)
    rng = random.Random(a.seed)
    torch.manual_seed(a.seed)
    items = _items(a)
    tr = [x for x in items if x["split"] == "train"]
    va = [x for x in items if x["split"] == "val"]
    if a.max_train:
        rng.shuffle(tr)
        tr = tr[:a.max_train]
    va = select_val(va, a.max_val, a.seed)
    if not tr or not va:
        raise SystemExit(f"no items: train {len(tr)} val {len(va)}")
    steps_per_epoch = math.ceil(len(tr) / a.accum)
    total = min(a.max_steps or 10 ** 9, steps_per_epoch * a.epochs)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, proc = load_model(a.model, device, lora={"r": a.lora_r, "alpha": a.lora_alpha, "dropout": a.lora_dropout})
    trainable = [p for p in model.parameters() if p.requires_grad]
    n_tr = sum(p.numel() for p in trainable)
    bad = [n for n, p in model.named_parameters() if p.requires_grad and ("visual" in n or "lora" not in n)]
    if bad:
        raise RuntimeError(f"non-LoRA or vision params trainable: {bad[:5]}")
    if a.grad_ckpt:
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        model.enable_input_require_grads()
    opt = torch.optim.AdamW(trainable, lr=a.lr, weight_decay=0.0)
    sched = get_cosine_schedule_with_warmup(opt, math.ceil(a.warmup * total), total)
    scorer = Scorer(proc, "")
    import peft
    import transformers
    cfg = {"utc": _utc(), "args": vars(a), "model_rev": MODEL_REV, "lora_target": LORA_TARGET,
           "n_train": len(tr), "n_val": len(va), "n_trainable": n_tr, "total_steps": total,
           "steps_per_epoch": steps_per_epoch, "ne_train": sum(x["ne"] for x in tr),
           "multi_target_train": sum(len(x["target"]) > 1 for x in tr),
           "questions": sorted({x["question"] for x in tr}),
           "target_sources": sorted({x["source"] for x in tr}), "prompt_files_sha": file_sha(PROMPT_FILES),
           "versions": {"torch": torch.__version__, "transformers": transformers.__version__,
                        "peft": peft.__version__, "python": sys.version.split()[0]},
           "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"}
    json.dump(cfg, open(os.path.join(out, "config.json"), "w"), indent=1)
    log = open(os.path.join(out, "log.jsonl"), "a")

    def write(rec):
        rec["utc"] = _utc()
        log.write(json.dumps(rec) + "\n")
        log.flush()
        print(json.dumps(rec), flush=True)

    ev = evaluate(model, scorer, va, device)
    write({"event": "eval", "step": 0, **ev})
    best, bad_evals, step, t0, tok_seen = ev["nll"], 0, 0, time.time(), 0
    model.save_pretrained(os.path.join(out, "best"))  # step 0 = zero-shot adapter (LoRA B = 0)
    run_loss, run_n = 0.0, 0
    model.train()
    done = False
    for epoch in range(a.epochs):
        order = list(range(len(tr)))
        rng.shuffle(order)
        for j in range(0, len(order), a.accum):
            chunk = [tr[i] for i in order[j:j + a.accum]]
            for it in chunk:
                lp = scorer.logprobs(model, it, device)
                loss = set_nll(lp, it["target"])
                (loss / len(chunk)).backward()
                run_loss, run_n = run_loss + float(loss), run_n + 1
            gn = float(torch.nn.utils.clip_grad_norm_(trainable, 1.0))
            opt.step()
            sched.step()
            opt.zero_grad(set_to_none=True)
            step += 1
            if step % a.log_every == 0:
                el = time.time() - t0
                write({"event": "train", "step": step, "epoch": epoch, "loss": round(run_loss / run_n, 5),
                       "grad_norm": round(gn, 4), "lr": sched.get_last_lr()[0], "items_per_s":
                       round(step * a.accum / el, 3), "elapsed_s": round(el, 1),
                       "max_mem_gb": round(torch.cuda.max_memory_allocated() / 2 ** 30, 2)
                       if torch.cuda.is_available() else None})
                run_loss, run_n = 0.0, 0
            if step % a.eval_every == 0 or step == total:
                ev = evaluate(model, scorer, va, device)
                improved = ev["nll"] < best - 1e-6
                write({"event": "eval", "step": step, "epoch": epoch, "improved": improved, **ev})
                if improved:
                    best, bad_evals = ev["nll"], 0
                    model.save_pretrained(os.path.join(out, "best"))
                else:
                    bad_evals += 1
                if bad_evals >= a.patience:
                    write({"event": "early_stop", "step": step, "best_nll": best})
                    done = True
            if step >= total or done:
                done = True
                break
        if done:
            break
    model.save_pretrained(os.path.join(out, "last"))
    write({"event": "done", "step": step, "best_nll": best, "wall_s": round(time.time() - t0, 1)})


def cmd_parity(a):
    """Base (or adapter) HF probabilities vs the recorded vLLM probabilities (tools/jevl_e3lite.py acc rows)."""
    import torch

    from ..deccall_snap import build_snapshot_request
    from ..e3lite import state_text
    from ..clients.jevl import question_text
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                    "tools"))
    from jevl_acc import snapshots
    acc = {}
    meta = None
    for x in open(a.acc, encoding="utf-8"):
        r = json.loads(x)
        if r.get("probs"):
            acc[(r["snap"], r["qid"])] = r["probs"]
            meta = meta or (r.get("S", "S0"), r.get("inp", "img"), r.get("order", "fixed"))
    S, inp, order = meta
    snaps = snapshots(a.dev)
    idx = {f"{s['kind']}_s{s['seed']}_k{s['k']}": i for i, s in enumerate(snaps)}
    keys = sorted({k for k, _ in acc})
    random.Random(0).shuffle(keys)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, proc = load_model(a.model, device, adapter=a.adapter)
    model.eval()
    sc = Scorer(proc, a.dev)
    diffs, agree, n, by_q = [], 0, 0, {}
    with torch.no_grad():
        for key in keys[:a.n]:
            s = snaps[idx[key]]
            req, _, shown = build_snapshot_request(s, text_state=state_text(s, S, step_cm=a.step_cm),
                                                   shift=idx[key] if order == "rot" else 0)
            for qid in req["questions"]:
                if (key, qid) not in acc:
                    continue
                q = req["questions"][qid]
                it = {"text": question_text(req["state"], qid, q), "names": list(q["criteria"]),
                      "image": f"{s['kind']}/{s['images']['cam_head']}" if inp == "img" else None}
                lp = sc.logprobs(model, it, device)
                hf = {k: math.exp(float(v)) for k, v in lp.items()}
                vl = acc[(key, qid)]
                diffs.append(max(abs(hf[k] - vl[k]) for k in hf))
                by_q.setdefault(qid.split(".", 1)[1], []).append(diffs[-1])
                agree += max(hf, key=hf.get) == max(vl, key=vl.get)
                n += 1
    diffs.sort()
    res = {"n_items": n, "cond": [S, inp, order], "argmax_agree": agree / n, "maxabs_p_median": diffs[n // 2],
           "maxabs_p_p95": diffs[int(0.95 * (n - 1))], "maxabs_p_max": diffs[-1], "adapter": a.adapter,
           "by_question_median_max": {q: [sorted(v)[len(v) // 2], max(v)] for q, v in by_q.items()},
           "utc": _utc()}
    print("PARITY " + json.dumps(res), flush=True)
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)


def cmd_load(a):
    import torch

    items = select_val([x for x in _items(a) if x["split"] == "val"], a.n, a.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, proc = load_model(a.model, device, adapter=a.adapter)
    ev = evaluate(model, Scorer(proc, ""), items, device)
    print("LOAD " + json.dumps({"adapter": a.adapter, **ev}), flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("train")
    t.add_argument("--pool", default="/data/harvest/data/pool", help="episode folder(s), comma separated")
    t.add_argument("--run", required=True)
    t.add_argument("--out-root", default="/data/harvest/ckpt/stageA")
    t.add_argument("--model", default=MODEL_DIR)
    t.add_argument("--epochs", type=int, default=2)
    t.add_argument("--lr", type=float, default=1e-4)
    t.add_argument("--warmup", type=float, default=0.03)
    t.add_argument("--accum", type=int, default=64, help="items per optimizer step (effective batch)")
    t.add_argument("--lora-r", type=int, default=32)
    t.add_argument("--lora-alpha", type=int, default=64)
    t.add_argument("--lora-dropout", type=float, default=0.05)
    t.add_argument("--eval-every", type=int, default=100)
    t.add_argument("--patience", type=int, default=3)
    t.add_argument("--log-every", type=int, default=1)
    t.add_argument("--max-steps", type=int, default=0)
    t.add_argument("--max-train", type=int, default=0)
    t.add_argument("--max-val", type=int, default=0)
    t.add_argument("--seed", type=int, default=0)
    t.add_argument("--grad-ckpt", action="store_true")
    t.add_argument("--overwrite", action="store_true")
    p = sub.add_parser("parity")
    p.add_argument("--dev", default="/data/harvest/data/jsel_dev")
    p.add_argument("--acc", required=True)
    p.add_argument("--model", default=MODEL_DIR)
    p.add_argument("--adapter", default=None)
    p.add_argument("--n", type=int, default=20, help="snapshots")
    p.add_argument("--out", default="")
    p.add_argument("--step-cm", type=float, default=1.0, help="S1 grid of the recorded run (E3-lite runs: 1)")
    lo = sub.add_parser("load")
    lo.add_argument("--adapter", required=True)
    lo.add_argument("--pool", default="/data/harvest/data/pool")
    lo.add_argument("--model", default=MODEL_DIR)
    lo.add_argument("--n", type=int, default=20)
    lo.add_argument("--seed", type=int, default=0)

    for x in (t, lo):
        x.add_argument("--target-source", default="labels_v2", help="labels_v2 | outcome | py:<module>:<factory>")
        x.add_argument("--labels-v2", default="", help="labels_v2 file (default: <folder>.labels_v2.jsonl)")
        x.add_argument("--rule", default="", help="prereg_labeler.md rule (outcome source)")
        x.add_argument("--state", default="S1", help="prompt state (E3-lite S0/S1/S2; canon §53 = S1)")
        x.add_argument("--step-cm", type=float, default=0.1, help="S1 print grid (canon §54 = 0.1 cm)")
        x.add_argument("--dev-val-seeds", default="", help="smoke on DEV folders: val seeds, e.g. 24-29")
        x.add_argument("--partial", action="store_true", help="smoke: also read label files without .done")
    a = ap.parse_args(argv)
    {"train": cmd_train, "parity": cmd_parity, "load": cmd_load}[a.cmd](a)


if __name__ == "__main__":
    main()
