"""E-TEACH-L8 LoRA SFT of Qwen3-VL-8B-Instruct (prereg §3.5; venv_train: torch 2.13, transformers 5.17, peft 0.21).

python -m harvest.teach_l8.train --data train.jsonl --out <run dir> [--epochs 2 --lr 1e-4 --r 16 --micro 4 --accum 4]
- samples: dataset.py rows (control = runtime request -> label JSON; aux = perception QA), messages built with
  dataset.user_content (the LocalVLM layout) and the model's own chat template; loss only on the assistant answer
  (+ <|im_end|>), prompt tokens masked (-100).
- LoRA on the language model's q/k/v/o and gate/up/down (= harvest/train/stagea_train.LORA_TARGET); vision frozen.
- micro-batches of similar length (sorted inside shuffled windows), right padding; AdamW, cosine with warmup,
  gradient checkpointing, bf16.
- logs <out>/log.jsonl every --log-every optimizer steps: loss, tokens/s (all input tokens incl. image tokens),
  answer tokens/s, samples/s, GPU memory; adapter saved per epoch in <out>/epoch<k>/, summary in <out>/train.json.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import time

LORA_TARGET = r".*language_model\.layers\.\d+\.(self_attn\.(q|k|v|o)_proj|mlp\.(gate|up|down)_proj)"


def messages(row: dict, with_answer: bool) -> list:
    from .dataset import user_content
    text = row["prompt"] if row["kind"] == "aux" else open(row["prompt_path"], encoding="utf-8").read()
    m = [{"role": "user", "content": user_content(text, len(row["images"]))}]
    if with_answer:
        m.append({"role": "assistant", "content": [{"type": "text", "text": row["answer"]}]})
    return m


def mask_labels(input_ids: list, n_prompt: int) -> list:
    return [-100] * n_prompt + list(input_ids[n_prompt:])


def micro_batches(lengths: list, micro: int, window: int, seed: int) -> list:
    """Indices grouped into micro-batches of similar length: shuffle, sort inside windows, cut, shuffle batches."""
    rng = random.Random(seed)
    idx = list(range(len(lengths)))
    rng.shuffle(idx)
    out = []
    for w in range(0, len(idx), window):
        chunk = sorted(idx[w:w + window], key=lambda i: lengths[i])
        out += [chunk[k:k + micro] for k in range(0, len(chunk), micro)]
    rng.shuffle(out)
    return out


class Encoder:
    def __init__(self, proc):
        self.p = proc

    def __call__(self, row: dict) -> dict:
        from PIL import Image
        ims = [Image.open(p).convert("RGB") for p in row["images"]]
        full = self.p.apply_chat_template(messages(row, True), tokenize=False)
        pre = self.p.apply_chat_template(messages(row, False), tokenize=False, add_generation_prompt=True)
        if not full.startswith(pre):
            raise ValueError(f"chat template: the prompt is not a prefix of the full text ({row['id']})")
        enc = self.p(text=[full], images=ims, return_tensors="pt")
        n_pre = self.p(text=[pre], images=ims, return_tensors="pt")["input_ids"].shape[1]
        ids = enc["input_ids"][0].tolist()
        return {"input_ids": ids, "labels": mask_labels(ids, n_pre), "pixel_values": enc["pixel_values"],
                "image_grid_thw": enc["image_grid_thw"], "mm_token_type_ids": enc["mm_token_type_ids"][0].tolist(),
                "n_answer": len(ids) - n_pre}


def collate(items: list, pad_id: int):
    import torch
    L = max(len(x["input_ids"]) for x in items)
    ids = torch.full((len(items), L), pad_id, dtype=torch.long)
    lab = torch.full((len(items), L), -100, dtype=torch.long)
    att = torch.zeros((len(items), L), dtype=torch.long)
    mm = torch.zeros((len(items), L), dtype=torch.long)
    for i, x in enumerate(items):
        n = len(x["input_ids"])
        ids[i, :n] = torch.tensor(x["input_ids"])
        lab[i, :n] = torch.tensor(x["labels"])
        mm[i, :n] = torch.tensor(x["mm_token_type_ids"])
        att[i, :n] = 1
    return {"input_ids": ids, "labels": lab, "attention_mask": att, "mm_token_type_ids": mm,
            "pixel_values": torch.cat([x["pixel_values"] for x in items]),
            "image_grid_thw": torch.cat([x["image_grid_thw"] for x in items])}


class MBData:
    """Map-style dataset of pre-cut micro-batches: encoding + collation run in DataLoader workers."""

    def __init__(self, rows, mbs, enc, pad):
        self.rows, self.mbs, self.enc, self.pad = rows, mbs, enc, pad

    def __len__(self):
        return len(self.mbs)

    def __getitem__(self, k):
        items = [self.enc(self.rows[i]) for i in self.mbs[k]]
        return collate(items, self.pad), sum(x["n_answer"] for x in items), len(items)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="/data/harvest/models/Qwen3-VL-8B-Instruct")
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--r", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--micro", type=int, default=4)
    ap.add_argument("--accum", type=int, default=4)
    ap.add_argument("--window", type=int, default=64)
    ap.add_argument("--warmup", type=int, default=20)
    ap.add_argument("--log-every", type=int, default=5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--max-steps", type=int, default=0, help="stop after this many optimizer steps (smoke)")
    ap.add_argument("--limit", type=int, default=0, help="use only the first N rows (smoke)")
    a = ap.parse_args(argv)

    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForImageTextToText, AutoProcessor

    torch.manual_seed(a.seed)
    os.makedirs(a.out, exist_ok=True)
    rows = [json.loads(x) for x in open(a.data)]
    if a.limit:
        rows = rows[:a.limit]
    proc = AutoProcessor.from_pretrained(a.model)
    enc = Encoder(proc)
    t0 = time.time()
    lengths = [len(proc.tokenizer(open(r["prompt_path"], encoding="utf-8").read() if r["kind"] == "control"
                                  else r["prompt"])["input_ids"]) + 300 * len(r["images"]) for r in rows]
    model = AutoModelForImageTextToText.from_pretrained(a.model, dtype=torch.bfloat16, attn_implementation="sdpa")
    model.to("cuda")
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.enable_input_require_grads()
    model = get_peft_model(model, LoraConfig(r=a.r, lora_alpha=a.alpha, lora_dropout=0.05, target_modules=LORA_TARGET,
                                             bias="none"))
    n_train = sum(p.numel() for p in model.parameters() if p.requires_grad)
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=a.lr, weight_decay=0.0)
    n_ep = math.ceil(a.epochs)
    per_epoch = math.ceil(len(micro_batches(lengths, a.micro, a.window, 0)) / a.accum)
    total = a.max_steps or int(per_epoch * a.epochs)

    def lr_at(s):
        if s < a.warmup:
            return a.lr * (s + 1) / a.warmup
        return a.lr * 0.5 * (1 + math.cos(math.pi * min(1.0, (s - a.warmup) / max(1, total - a.warmup))))

    pad = proc.tokenizer.pad_token_id if proc.tokenizer.pad_token_id is not None else 0
    log = open(os.path.join(a.out, "log.jsonl"), "a")
    step, tok, ans_tok, n_s, lsum, lcnt = 0, 0, 0, 0, 0.0, 0
    t_win = time.time()
    t_train0 = time.time()
    epoch_times = []
    model.train()
    done = False
    for ep in range(n_ep):
        te = time.time()
        mbs = micro_batches(lengths, a.micro, a.window, a.seed + ep)
        if a.epochs - ep < 1:
            mbs = mbs[:int(len(mbs) * (a.epochs - ep))]
        loader = torch.utils.data.DataLoader(MBData(rows, mbs, enc, pad), batch_size=None, shuffle=False,
                                             num_workers=a.workers, prefetch_factor=4 if a.workers else None)
        for k, (bc, n_ans, n_items) in enumerate(loader):
            b = {kk: v.to("cuda", non_blocking=True) for kk, v in bc.items()}
            out = model(**b)
            (out.loss / a.accum).backward()
            lsum, lcnt = lsum + float(out.loss.detach()), lcnt + 1
            tok += int(b["attention_mask"].sum())
            ans_tok += int(n_ans)
            n_s += int(n_items)
            if (k + 1) % a.accum == 0 or k + 1 == len(mbs):
                for g in opt.param_groups:
                    g["lr"] = lr_at(step)
                torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.0)
                opt.step()
                opt.zero_grad(set_to_none=True)
                step += 1
                if step % a.log_every == 0:
                    dt = time.time() - t_win
                    rec = {"step": step, "epoch": ep, "loss": round(lsum / lcnt, 5), "lr": lr_at(step),
                           "tok_s": round(tok / dt, 1), "answer_tok_s": round(ans_tok / dt, 1),
                           "samples_s": round(n_s / dt, 3), "gpu_gb": round(torch.cuda.max_memory_allocated() / 2**30, 1),
                           "t": round(time.time() - t_train0, 1)}
                    log.write(json.dumps(rec) + "\n")
                    log.flush()
                    print("LOG " + json.dumps(rec), flush=True)
                    tok, ans_tok, n_s, lsum, lcnt, t_win = 0, 0, 0, 0.0, 0, time.time()
                if a.max_steps and step >= a.max_steps:
                    done = True
                    break
        epoch_times.append(round(time.time() - te, 1))
        model.save_pretrained(os.path.join(a.out, f"epoch{ep + 1}"))
        print(f"EPOCH {ep + 1} {epoch_times[-1]} s", flush=True)
        if done:
            break
    summ = {"rows": len(rows), "trainable_params": n_train, "steps": step, "epoch_s": epoch_times,
            "train_s": round(time.time() - t_train0, 1), "setup_s": round(t_train0 - t0, 1), "args": vars(a)}
    json.dump(summ, open(os.path.join(a.out, "train.json"), "w"), indent=1)
    print("TRAIN_DONE " + json.dumps(summ), flush=True)


if __name__ == "__main__":
    main()
