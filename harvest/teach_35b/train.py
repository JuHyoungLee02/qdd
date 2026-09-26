"""E-TEACH-35B LoRA SFT of Qwen3.5-35B-A3B (venv_train: torch 2.13, transformers 5.17, peft 0.21).

Single GPU:  python -m harvest.teach_35b.train --data train.jsonl --out <run dir> [--epochs 2 ...]
N GPUs DDP:  torchrun --standalone --nproc-per-node N -m harvest.teach_35b.train ...  (tools/teach_35b/train.sh)

Same recipe as harvest.teach_l8.train (loss only on the answer; length-grouped micro-batches; AdamW, cosine with
warmup, gradient checkpointing, bf16). Rows: harvest.teach_35b.data — teach_l8.dataset rows (astra-solo@v2) as they
are, and coupled astra-couple@v2 rows (segment plan now/do/next + assessment/verification + command, production
'cam_x:' image labels) in the same file; every control label is checked with the runtime parser of its format
before the model loads (--label-check strict aborts on any invalid label). What differs for the 35B-A3B MoE:
- model class Qwen3_5MoeForConditionalGeneration (AutoModelForImageTextToText), routed experts run with the
  grouped_mm implementation (--experts-impl), vision tower frozen.
- LoRA targets (LORA_TARGET): every token-mixer projection — full attention q/k/v/o (10 layers) and Gated DeltaNet
  in_proj_qkv / in_proj_z / out_proj (30 layers) — plus the always-on shared expert gate/up/down (40 layers).
  NOT the 256 routed experts (3D fused parameters; each token uses 8, so a per-expert adapter sees 1/32 of the
  data, PEFT's parameter-LoRA re-materialises the full delta every forward, and the merge would touch 60 GB),
  not the router / shared_expert_gate (keep routing = keep the pretrained expert use), not in_proj_a/b (32-wide).
- chat template with enable_thinking=False: the answer follows '<think>\\n\\n</think>\\n\\n' (the same prefix vLLM
  renders for a non-thinking request), so the served model must run with thinking off (tools/teach_35b/vllm.sh).
- DDP: every GPU holds a full bf16 copy (about 67 GB) and a disjoint, equal share of the micro-batches of each
  epoch (shard); gradients of the LoRA parameters are all-reduced on the optimizer step only (no_sync otherwise).
  The optimizer step count per epoch is divided by the world size; --accum stays per GPU, so the global batch is
  micro x accum x world.
Logs <out>/log.jsonl every --log-every optimizer steps (global tokens/s incl. image tokens, answer tokens/s,
samples/s, peak GPU memory of rank 0); adapter per epoch in <out>/epoch<k>/; summary <out>/train.json."""
from __future__ import annotations

import argparse
import json
import math
import os
import time

from ..teach_l8.train import mask_labels, micro_batches
from .data import check_rows, messages, request_text

LORA_TARGET = (r".*language_model\.layers\.\d+\.(self_attn\.(q|k|v|o)_proj|linear_attn\.(in_proj_qkv|in_proj_z|out_proj)"
               r"|mlp\.shared_expert\.(gate|up|down)_proj)")
DEFAULT_MODEL = "/data/harvest/models/Qwen3.5-35B-A3B"
TEMPLATE_KW = {"enable_thinking": False}


def shard(mbs: list, rank: int, world: int) -> list:
    """Rank's share of the micro-batches: round robin, the same count on every rank (the remainder is dropped)."""
    n = len(mbs) // world
    return mbs[rank::world][:n]


def check_prefix(full: str, pre: str, rid: str):
    if not full.startswith(pre):
        raise ValueError(f"chat template: the prompt is not a prefix of the full text ({rid})")


class Encoder:
    def __init__(self, proc):
        self.p = proc

    def __call__(self, row: dict) -> dict:
        from PIL import Image
        ims = [Image.open(p).convert("RGB") for p in row["images"]]
        full = self.p.apply_chat_template(messages(row, True), tokenize=False, **TEMPLATE_KW)
        pre = self.p.apply_chat_template(messages(row, False), tokenize=False, add_generation_prompt=True,
                                         **TEMPLATE_KW)
        check_prefix(full, pre, row["id"])
        enc = self.p(text=[full], images=ims, return_tensors="pt")
        n_pre = self.p(text=[pre], images=ims, return_tensors="pt")["input_ids"].shape[1]
        ids = enc["input_ids"][0].tolist()
        x = {"input_ids": ids, "labels": mask_labels(ids, n_pre), "pixel_values": enc["pixel_values"],
             "image_grid_thw": enc["image_grid_thw"], "n_answer": len(ids) - n_pre}
        if "mm_token_type_ids" in enc:
            x["mm_token_type_ids"] = enc["mm_token_type_ids"][0].tolist()
        return x


def collate(items: list, pad_id: int):
    import torch
    L = max(len(x["input_ids"]) for x in items)
    ids = torch.full((len(items), L), pad_id, dtype=torch.long)
    lab = torch.full((len(items), L), -100, dtype=torch.long)
    att = torch.zeros((len(items), L), dtype=torch.long)
    mm = torch.zeros((len(items), L), dtype=torch.long) if "mm_token_type_ids" in items[0] else None
    for i, x in enumerate(items):
        n = len(x["input_ids"])
        ids[i, :n] = torch.tensor(x["input_ids"])
        lab[i, :n] = torch.tensor(x["labels"])
        att[i, :n] = 1
        if mm is not None:
            mm[i, :n] = torch.tensor(x["mm_token_type_ids"])
    out = {"input_ids": ids, "labels": lab, "attention_mask": att,
           "pixel_values": torch.cat([x["pixel_values"] for x in items]),
           "image_grid_thw": torch.cat([x["image_grid_thw"] for x in items])}
    if mm is not None:
        out["mm_token_type_ids"] = mm
    return out


class MBData:
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
    ap.add_argument("--model", default=DEFAULT_MODEL)
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
    ap.add_argument("--experts-impl", default="grouped_mm", help="transformers experts implementation")
    ap.add_argument("--max-steps", type=int, default=0, help="stop after this many optimizer steps (smoke)")
    ap.add_argument("--limit", type=int, default=0, help="use only the first N rows (smoke)")
    ap.add_argument("--save-every-epoch", type=int, default=1)
    ap.add_argument("--label-check", choices=("strict", "warn"), default="strict")
    ap.add_argument("--mem-frac", type=float, default=0.0, help="cap this process's GPU memory share (0 = no cap)")
    a = ap.parse_args(argv)

    import torch
    import torch.distributed as dist
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForImageTextToText, AutoProcessor

    world = int(os.environ.get("WORLD_SIZE", "1"))
    rank = int(os.environ.get("RANK", "0"))
    local = int(os.environ.get("LOCAL_RANK", "0"))
    if world > 1:
        dist.init_process_group("nccl")
    torch.cuda.set_device(local)
    dev = torch.device("cuda", local)
    if a.mem_frac:  # sharing a GPU with another job (e.g. an Isaac lane): cap our allocator, never theirs
        torch.cuda.set_per_process_memory_fraction(a.mem_frac, dev)
    main_rank = rank == 0

    torch.manual_seed(a.seed)
    os.makedirs(a.out, exist_ok=True)
    rows = [json.loads(x) for x in open(a.data)]
    if a.limit:
        rows = rows[:a.limit]
    chk = check_rows(rows)
    if main_rank:
        print("LABELS " + json.dumps(chk), flush=True)
    if chk["invalid"] and a.label_check == "strict":
        raise SystemExit(f"{chk['invalid']} control labels fail the runtime parser (--label-check warn to go on)")
    proc = AutoProcessor.from_pretrained(a.model)
    enc = Encoder(proc)
    t0 = time.time()
    lengths = [len(proc.tokenizer(request_text(r))["input_ids"]) + 300 * len(r["images"]) for r in rows]
    model = AutoModelForImageTextToText.from_pretrained(a.model, dtype=torch.bfloat16, attn_implementation="sdpa",
                                                        device_map={"": dev},
                                                        experts_implementation=a.experts_impl)
    model.config.use_cache = False
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.enable_input_require_grads()
    model = get_peft_model(model, LoraConfig(r=a.r, lora_alpha=a.alpha, lora_dropout=0.05, target_modules=LORA_TARGET,
                                             bias="none"))
    n_train = sum(p.numel() for p in model.parameters() if p.requires_grad)
    n_mod = sum(1 for n, _ in model.named_modules() if n.endswith(".lora_A"))
    params = [p for p in model.parameters() if p.requires_grad]
    core = model
    if world > 1:
        model = torch.nn.parallel.DistributedDataParallel(model, device_ids=[local], find_unused_parameters=False)
    opt = torch.optim.AdamW(params, lr=a.lr, weight_decay=0.0)
    n_ep = math.ceil(a.epochs)
    per_epoch = math.ceil(len(shard(micro_batches(lengths, a.micro, a.window, 0), 0, world)) / a.accum)
    total = a.max_steps or int(per_epoch * a.epochs)
    if main_rank:
        print("SETUP " + json.dumps({"rows": len(rows), "world": world, "trainable": n_train, "lora_modules": n_mod,
                                     "steps_per_epoch": per_epoch, "total_steps": total,
                                     "load_s": round(time.time() - t0, 1)}), flush=True)

    def lr_at(s):
        if s < a.warmup:
            return a.lr * (s + 1) / a.warmup
        return a.lr * 0.5 * (1 + math.cos(math.pi * min(1.0, (s - a.warmup) / max(1, total - a.warmup))))

    pad = proc.tokenizer.pad_token_id if proc.tokenizer.pad_token_id is not None else 0
    log = open(os.path.join(a.out, "log.jsonl"), "a") if main_rank else None
    step = 0
    cnt = torch.zeros(5, dtype=torch.float64, device=dev)  # tokens, answer tokens, samples, loss sum, loss count
    t_win = t_train0 = time.time()
    epoch_times = []
    model.train()
    done = False
    for ep in range(n_ep):
        te = time.time()
        mbs = micro_batches(lengths, a.micro, a.window, a.seed + ep)
        if a.epochs - ep < 1:
            mbs = mbs[:int(len(mbs) * (a.epochs - ep))]
        mine = shard(mbs, rank, world)
        loader = torch.utils.data.DataLoader(MBData(rows, mine, enc, pad), batch_size=None, shuffle=False,
                                             num_workers=a.workers, prefetch_factor=4 if a.workers else None)
        for k, (bc, n_ans, n_items) in enumerate(loader):
            b = {kk: v.to(dev, non_blocking=True) for kk, v in bc.items()}
            boundary = (k + 1) % a.accum == 0 or k + 1 == len(mine)
            if world > 1 and not boundary:
                with model.no_sync():
                    out = model(**b)
                    (out.loss / a.accum).backward()
            else:
                out = model(**b)
                (out.loss / a.accum).backward()
            cnt += torch.tensor([float(b["attention_mask"].sum()), float(n_ans), float(n_items),
                                 float(out.loss.detach()), 1.0], dtype=torch.float64, device=dev)
            if boundary:
                for g in opt.param_groups:
                    g["lr"] = lr_at(step)
                torch.nn.utils.clip_grad_norm_(params, 1.0)
                opt.step()
                opt.zero_grad(set_to_none=True)
                step += 1
                if step % a.log_every == 0:
                    tot = cnt.clone()
                    if world > 1:
                        dist.all_reduce(tot)
                    dt = time.time() - t_win
                    rec = {"step": step, "epoch": ep, "loss": round(float(tot[3] / tot[4]), 5), "lr": lr_at(step),
                           "tok_s": round(float(tot[0]) / dt, 1), "answer_tok_s": round(float(tot[1]) / dt, 1),
                           "samples_s": round(float(tot[2]) / dt, 3),
                           "gpu_gb": round(torch.cuda.max_memory_allocated(dev) / 2**30, 1),
                           "t": round(time.time() - t_train0, 1)}
                    if main_rank:
                        log.write(json.dumps(rec) + "\n")
                        log.flush()
                        print("LOG " + json.dumps(rec), flush=True)
                    cnt.zero_()
                    t_win = time.time()
                if a.max_steps and step >= a.max_steps:
                    done = True
                    break
        epoch_times.append(round(time.time() - te, 1))
        if main_rank and (a.save_every_epoch or done or ep == n_ep - 1):
            core.save_pretrained(os.path.join(a.out, f"epoch{ep + 1}"))
        if main_rank:
            print(f"EPOCH {ep + 1} {epoch_times[-1]} s", flush=True)
        if done:
            break
    if main_rank:
        summ = {"rows": len(rows), "world": world, "trainable_params": n_train, "lora_modules": n_mod, "steps": step,
                "epoch_s": epoch_times, "train_s": round(time.time() - t_train0, 1), "setup_s": round(t_train0 - t0, 1),
                "peak_gb_rank0": round(torch.cuda.max_memory_allocated(dev) / 2**30, 1), "args": vars(a)}
        json.dump(summ, open(os.path.join(a.out, "train.json"), "w"), indent=1)
        print("TRAIN_DONE " + json.dumps(summ), flush=True)
    if world > 1:
        dist.barrier()
        dist.destroy_process_group()


if __name__ == "__main__":
    main()
