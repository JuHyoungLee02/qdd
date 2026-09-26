"""Stage-A SFT of the Jev-L typed selector (canon §51-§52, D26 §1.4, docs/stage3/results/stageA_pipeline.md).

  train   --pool DIR --run NAME [--cameras HW] [--state S1] ... LoRA SFT on labels_v2 targets (default; --rule R only
                                                               with --target-source outcome), early stopping on val
                                                               (POOL `eval`) NLL
  parity  --dev DIR --acc JSONL [--adapter DIR] --n N          HF option probs vs the recorded vLLM Jev-L probs
  load    --adapter DIR [--pool DIR] [--n N] [--seed S]        reload a saved adapter and score a few val items
                                                               (same target options as train: labels_v2 default;
                                                               --rule R only with --target-source outcome)

Prompt = the Jev-L request exactly: --cameras HW (default, canon §59) = jevl.JevLClient._body_mm layout HW (system
jevl.SYSTEM, user ["head camera:", head 672x376, "right wrist camera (active arm):", wrist 424x240,
jevl.question_text(...)]); --cameras H = jevl._body (head image only, the §55 smoke prompt); + generation prompt.
The camera configuration goes into config.json prompt_config (question_id hash input, §59). R3 throughput: the
questions of a snapshot share one forward (prefix_share, --micro snapshots per forward; --no-share = old path); state text = E3-lite S1 on a 1 mm grid by default (canon §53-§54); the option probabilities are jevl's trie
decomposition (stagea_loss). Targets (--target-source): labels_v2 (default, canon §54: observation-defined answers,
file <folder>.labels_v2.jsonl), outcome (labeler best set under --rule, auxiliary), or py:<module>:<factory> with
factory(pool_dir, seed) -> stagea_data source. Never the pool oracle.
--pool takes one or more episode folders (comma separated); DEV folders need --dev-val-seeds (smoke only). Model Qwen3-VL-4B-Instruct BF16,
LoRA r32 a64 dropout 0.05 on every LLM linear layer (q,k,v,o,gate,up,down of model.language_model), vision tower,
merger and lm_head frozen. AdamW lr 1e-4, cosine, 3 % warmup, 1-2 epochs.
Pod: run with CUDA_VISIBLE_DEVICES=2 (training compute, no rendering: user-log 62, 64; GPU 1 = Isaac render, GPU 3 =
vLLM; check the GPU is free with nvidia-smi first) from /data/harvest/venv_train; every output under /data/harvest.
TORCH_DISABLE_NATIVE_JIT=1 is set below when absent (the pod has no C compiler for Triton's launcher, R7 cycle-1 N1).
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

os.environ.setdefault("TORCH_DISABLE_NATIVE_JIT", "1")  # before any torch import (functions import torch lazily)

MODEL_DIR = "/data/harvest/models/Qwen3-VL-4B-Instruct"
MODEL_REV = "ebb281ec70b05090aa6165b016eac8ec08e71b17"
LORA_TARGET = r".*language_model\.layers\.\d+\.(self_attn\.(q|k|v|o)_proj|mlp\.(gate|up|down)_proj)"
END_TOKEN = "<|im_end|>"


def _utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def file_sha(paths):
    """{path: sha256[:12]} of repo files; an entry "path.py:NAME" hashes the repr of that module constant instead
    (a prompt-shaping constant of a large module, so an unrelated edit of the module does not change the hash)."""
    import importlib
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    out = {}
    for p in paths:
        if ":" in p:
            path, name = p.split(":")
            val = getattr(importlib.import_module(path[:-len(".py")].replace("/", ".")), name)
            out[p] = hashlib.sha256(repr(val).encode()).hexdigest()[:12]
        else:
            out[p] = hashlib.sha256(open(os.path.join(root, p), "rb").read()).hexdigest()[:12]
    return out


PROMPT_FILES = ("harvest/clients/jevl.py", "harvest/deccall_snap.py", "harvest/jevcall.py", "harvest/options.py",
                "harvest/e3lite.py",
                "harvest/serialize.py", "harvest/train/stagea_data.py", "harvest/train/stagea_loss.py",
                "harvest/train/prefix_share.py",
                "harvest/intent.py",  # ser-A-min-3: the §90 segment line of training prompts comes from its rule
                # ser-A-min-3 fix round 1: the fused dir_xy / mag_coarse wording (labels_v2 constants, the MAG bins),
                # the segment rule's phase order, the stage (S1 / S2) and object names in the question text
                "harvest/labels_v2.py", "harvest/sim/planner.py:MAG_BINS", "harvest/sim/snapshot.py:PHASE_ORDER",
                "harvest/sim/snapshot.py:_S1", "harvest/sim/snapshot.py:SPEC_NAMES")


def Scorer(processor, image_root):
    """Processor + tokenized option tries (stageb_model.HFEncoder): item -> {name: log p~} (old per-item path via
    .logprobs; the R3 shared path is prefix_share.items_logprobs). Items carry `images` ([[label, path]], §59
    layout) or `image` (legacy head-only prompt = jevl._body)."""
    from .stageb_model import HFEncoder
    return HFEncoder(processor, image_root)


def item_batches(items, micro):
    """Consecutive runs of at most `micro` snapshots (groups of items with one shared prefix)."""
    out, cur, keys = [], [], set()
    for it in items:
        if it["key"] not in keys and len(keys) == micro:
            out.append(cur)
            cur, keys = [], set()
        cur.append(it)
        keys.add(it["key"])
    if cur:
        out.append(cur)
    return out


def batch_logprobs(model, scorer, items, device, share=True, micro=8, canonical=False):
    """[{name: log p~}] for items (same order): shared-prefix batches of `micro` snapshots, or one forward per
    item (share=False, the old path). canonical: batch in (snapshot, question) order whatever the input order,
    so an evaluation of the same item set packs the same batches (bit-identical across train / load)."""
    if not share:
        return [scorer.logprobs(model, it, device) for it in items]
    from .prefix_share import items_logprobs
    idx = sorted(range(len(items)), key=lambda i: (items[i]["key"], items[i].get("qid", ""))) if canonical \
        else list(range(len(items)))
    got = []
    for b in item_batches([items[i] for i in idx], micro):
        got += items_logprobs(model, scorer, b, device)
    out = [None] * len(items)
    for i, lp in zip(idx, got):
        out[i] = lp
    return out


def serializer_of(pc: dict) -> str:
    """State serializer version a checkpoint was trained with (canon §77): prompt_config["serializer"]; a config
    without it (stage-B stageb_train.prompt_config, pre-§77 runs) is current only if its prompt-building files are
    byte-identical to this code's (the version constant lives in one of them), else it predates the current one."""
    from ..serialize import SERIALIZER_VERSION
    if pc.get("serializer"):
        return pc["serializer"]
    fs = pc.get("files_sha") or {}
    try:
        same = bool(fs) and isinstance(fs, dict) and file_sha(tuple(fs)) == fs
    except (OSError, AttributeError, ImportError):  # a recorded file / constant this code no longer has
        same = False
    return SERIALIZER_VERSION if same else f"older than {SERIALIZER_VERSION} (prompt-building files changed)"


def require_serializer(pc: dict | None, what: str) -> None:
    """Refuse a checkpoint trained on another DecCall state format (canon §77: ser-A-min-2 adds the M4 (b)
    `last_step:` line; every earlier checkpoint is invalid -- retrain)."""
    from ..serialize import SERIALIZER_VERSION
    if pc is None:
        return
    got = serializer_of(pc)
    if got != SERIALIZER_VERSION:
        raise ValueError(f"{what}: trained with state serializer {got!r}, this code feeds {SERIALIZER_VERSION!r} "
                         f"(canon §77 / §83 / §90: the DecCall state ends with the segment, motion and M4 (b) "
                         f"'last_step:' lines) -- retrain on the new format")


def format_checks(pc: dict) -> dict:
    """The DecCall format a checkpoint recorded (serialize.format_record, controller ruling PH-A 2) against this code:
    {"serializer_ok", "last_step_ok"} -- the state serializer version (serializer_of) and the exact (b) `last_step`
    category list (a config without it predates ser-A-min-3's record and fails)."""
    from ..serialize import LAST_STEP_VALUES, SERIALIZER_VERSION
    return {"serializer_ok": serializer_of(pc) == SERIALIZER_VERSION,
            "last_step_ok": pc.get("last_step_values") == list(LAST_STEP_VALUES)}


def prompt_config(items, a):
    """Training-side record of what inference must match (question_id@vN hash input, canon §59): camera
    configuration(s), state mode and grid, system prompt, DecCall format (serialize.format_record: serializer version
    + the (b) `last_step` categories), prompt-building files; sha = hash of all of it."""
    from ..clients.jevl import SYSTEM
    from ..serialize import format_record
    from .stagea_data import camera_of
    cfg = {"camera": sorted({camera_of(x) for x in items}), "state": a.state, "step_cm": a.step_cm,
           "system_sha": hashlib.sha256(SYSTEM.encode()).hexdigest()[:12], **format_record(),
           "files_sha": file_sha(PROMPT_FILES)}
    cfg["sha"] = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    return cfg


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


def evaluate(model, scorer, items, device, share=True, micro=8):
    import torch
    from .stagea_loss import set_nll
    was = model.training
    model.eval()
    nll, acc, pset, per_q = [], [], [], {}
    with torch.no_grad():
        lps = batch_logprobs(model, scorer, items, device, share, micro, canonical=True)
        for it, lp in zip(items, lps):
            v = float(set_nll(lp, it["target"]))
            nll.append(v)
            top = max(lp, key=lambda n: float(lp[n]))
            acc.append(top in it["target"])
            pset.append(math.exp(-v))
            per_q.setdefault(it["question"], []).append(v)
    model.train(was)
    return {"nll": sum(nll) / len(nll), "acc": sum(acc) / len(acc), "p_target": sum(pset) / len(pset),
            "n": len(nll), "nll_q": {q: round(sum(v) / len(v), 4) for q, v in per_q.items()}}


def source_factory(spec, rule, partial, labels_v2=None, stats=None):
    """'labels_v2' | 'outcome' (labeler best sets under `rule`; rows whose replay was not bit-identical are dropped
    and counted in `stats`, canon §78 (1)) | 'py:pkg.mod:fn' (a stagea_data source factory)."""
    from .stagea_data import labels_v2_factory, outcome_factory
    if spec == "labels_v2":
        return labels_v2_factory(labels_v2)
    if spec == "outcome":
        if not rule:
            raise SystemExit("--rule is required with --target-source outcome")
        return outcome_factory(rule, partial, stats)
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


# stage-A OutcomeLabels counts every row of a snapshot's label file, fine_dir (near contact) included, unlike
# eval.common.load_truth (the five QUESTIONS only) -- on the pool 886 vs 805 untrusted rows (R7 cycle 15 N3)
STAGEA_TRUST_QUESTIONS = "all label rows (dir_xy, dir_z, mag_coarse, target, phase + fine_dir near contact)"


def _items(a, stats=None):
    """All items of --pool; stats (optional) collects the outcome-label trust counts (canon §78 (1))."""
    from .stagea_data import load_pool
    dev = _seedset(a.dev_val_seeds) if a.dev_val_seeds else None
    items = []
    for folder in filter(None, a.pool.split(",")):
        items += load_pool(folder, state=a.state, partial=a.partial, step_cm=a.step_cm, dev_val_seeds=dev,
                           source_factory=source_factory(a.target_source, a.rule, a.partial, a.labels_v2 or None,
                                                         stats),
                           cameras=a.cameras)
    if stats:  # outcome labels were read: say which rows the counts cover (R7 cycle 15 N3)
        stats["questions"] = STAGEA_TRUST_QUESTIONS
    return items


def cmd_train(a):
    import torch
    from transformers import get_cosine_schedule_with_warmup

    from ..intent import segment_dropout_items
    from .stagea_loss import set_nll
    if not 0.0 <= a.segment_dropout < 1.0:
        raise SystemExit("--segment-dropout: 0 <= p < 1")
    out = os.path.join(a.out_root, a.run)
    if os.path.exists(os.path.join(out, "config.json")) and not a.overwrite:
        raise SystemExit(f"{out} exists (use --overwrite)")
    os.makedirs(out, exist_ok=True)
    rng = random.Random(a.seed)
    torch.manual_seed(a.seed)
    trust = {}
    items = _items(a, trust)
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
    share = not a.no_share
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
           "target_sources": sorted({x["source"] for x in tr}), "label_trust": trust or None,
           "prompt_files_sha": file_sha(PROMPT_FILES),
           "prompt_config": prompt_config(tr + va, a),
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

    ev = evaluate(model, scorer, va, device, share, a.micro)
    write({"event": "eval", "step": 0, **ev})
    best, bad_evals, step, t0, tok_seen = ev["nll"], 0, 0, time.time(), 0
    model.save_pretrained(os.path.join(out, "best"))  # step 0 = zero-shot adapter (LoRA B = 0)
    run_loss, run_n = 0.0, 0
    model.train()
    done = False
    for epoch in range(a.epochs):
        if share:  # R3: snapshots shuffled, a snapshot's questions contiguous (they share one prefix pass)
            from .prefix_share import snapshot_order
            order = snapshot_order(tr, rng)
        else:
            order = list(range(len(tr)))
            rng.shuffle(order)
        for j in range(0, len(order), a.accum):
            # canon §90 unknown-segment share (the modular runtime shows unknown until Astra's plan); per snapshot
            chunk = segment_dropout_items([tr[i] for i in order[j:j + a.accum]], step, a.seed, a.segment_dropout)
            for mb in item_batches(chunk, a.micro) if share else [[it] for it in chunk]:
                lps = batch_logprobs(model, scorer, mb, device, share, a.micro)
                losses = [set_nll(lp, it["target"]) for lp, it in zip(lps, mb)]
                (torch.stack(losses).sum() / len(chunk)).backward()
                run_loss, run_n = run_loss + sum(float(x.detach()) for x in losses), run_n + len(losses)
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
                ev = evaluate(model, scorer, va, device, share, a.micro)
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
    ev = evaluate(model, Scorer(proc, ""), items, device, not a.no_share, a.micro)
    print("LOAD " + json.dumps({"adapter": a.adapter, **ev}), flush=True)


def main(argv=None):
    from ..intent import SEGMENT_DROPOUT
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
    t.add_argument("--segment-dropout", type=float, default=SEGMENT_DROPOUT,
                   help="training-only probability of the 'unknown' segment-intent line (canon §90)")
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
        x.add_argument("--cameras", default="HW", choices=("H", "HW"),
                       help="HW = canon §59 head + active wrist (default); H = head only (the §55 smoke prompt)")
        x.add_argument("--micro", type=int, default=4, help="snapshots per shared-prefix forward (R3; 4 = 63 GB on H200, HW)")
        x.add_argument("--no-share", action="store_true", help="old path: one forward per item")
    a = ap.parse_args(argv)
    {"train": cmd_train, "parity": cmd_parity, "load": cmd_load}[a.cmd](a)


if __name__ == "__main__":
    main()
