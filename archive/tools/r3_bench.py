"""R3 training-throughput bench (docs/stage3/results/r3_throughput.md): old per-question path vs shared-prefix
batched path, stage A and stage B, real Qwen3-VL-4B BF16 + LoRA r32 on one GPU. Timing only (weights move with a
tiny lr; nothing is saved). NOT a result about model quality.

  stagea  --pool DIR --n-snap N   POOL fit snapshots (labels_v2), 5 questions each; configs old-H, old-HW,
                                  shared-HW micro in --micros, shared-H; items/s of forward+backward+AdamW step
                                  per --accum items, eval items/s (no grad), peak memory
  stageb  --n N [--pool DIR]      synthetic stage-B samples (R4 smoke data: 3 questions, IMG-like context) and,
                                  with --pool, POOL snapshots (IMG state, head + right wrist, 5 labels_v2
                                  questions) grafted onto synthetic action fields; s/step at --batches
Pod: CUDA_VISIBLE_DEVICES=2 (user-log 64: training compute only, no rendering), venv_train, TORCH_DISABLE_NATIVE_JIT=1.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time

import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harvest.train import stagea_train as A  # noqa: E402
from harvest.train.stagea_loss import set_nll  # noqa: E402

MODEL = A.MODEL_DIR


def _sync():
    torch.cuda.synchronize()


def _peak_reset():
    _sync()
    torch.cuda.reset_peak_memory_stats()


def _peak():
    return round(torch.cuda.max_memory_allocated() / 2 ** 30, 2)


def pool_items(pool, n_snap, cameras, state="S1", seed=0):
    from harvest.train.stagea_data import labels_v2_factory, load_pool
    its = [x for x in load_pool(pool, state=state, source_factory=labels_v2_factory(), cameras=cameras)
           if x["split"] == "train"]
    keys = sorted({x["key"] for x in its})
    random.Random(seed).shuffle(keys)
    keep = set(keys[:n_snap])
    return [x for x in its if x["key"] in keep]


def time_train_a(model, sc, items, share, micro, accum, reps=1):
    """forward + backward over `items` in the training loop's order/grouping, AdamW step per accum items."""
    ps = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(ps, lr=1e-7)
    model.train()
    warm = items[:min(len(items), 2 * 5)]
    for mb in (A.item_batches(warm, micro) if share else [[x] for x in warm]):  # warm-up (allocator, kernels)
        lps = A.batch_logprobs(model, sc, mb, "cuda", share, micro)
        torch.stack([set_nll(lp, it["target"]) for lp, it in zip(lps, mb)]).sum().backward()
    opt.zero_grad(set_to_none=True)
    _peak_reset()
    t0 = time.perf_counter()
    n = 0
    for _ in range(reps):
        for j in range(0, len(items), accum):
            chunk = items[j:j + accum]
            for mb in (A.item_batches(chunk, micro) if share else [[x] for x in chunk]):
                lps = A.batch_logprobs(model, sc, mb, "cuda", share, micro)
                loss = torch.stack([set_nll(lp, it["target"]) for lp, it in zip(lps, mb)]).sum() / len(chunk)
                loss.backward()
                n += len(mb)
            torch.nn.utils.clip_grad_norm_(ps, 1.0)
            opt.step()
            opt.zero_grad(set_to_none=True)
    _sync()
    dt = time.perf_counter() - t0
    return {"items": n, "s": round(dt, 2), "items_per_s": round(n / dt, 3), "peak_gb": _peak()}


def time_eval_a(model, sc, items, share, micro):
    model.eval()
    with torch.no_grad():
        A.batch_logprobs(model, sc, items[:10], "cuda", share, micro)
        _peak_reset()
        t0 = time.perf_counter()
        A.batch_logprobs(model, sc, items, "cuda", share, micro)
        _sync()
    dt = time.perf_counter() - t0
    return {"items": len(items), "s": round(dt, 2), "items_per_s": round(len(items) / dt, 3), "peak_gb": _peak()}


def token_stats(sc, items):
    """Prompt tokens per item and the shared-prefix length per snapshot (what the shared path saves)."""
    from harvest.train.prefix_share import group_items, group_rows, shared_len, _image_id
    P, L, R = [], [], []
    for grp in group_items(items)[:20]:
        gr, book = group_rows(sc, grp)
        L.append(shared_len(gr["rows"], {_image_id(sc)}, gr["cap"]))
        P += [b[4] for b in book]
        R.append(len(gr["rows"]))
    med = lambda v: sorted(v)[len(v) // 2]  # noqa: E731
    return {"prompt_tokens_median": med(P), "shared_prefix_median": med(L), "rows_per_snapshot_median": med(R),
            "questions_per_snapshot": round(len(P) / max(1, len(L)), 2)}


def cmd_stagea(a):
    out = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "gpu": torch.cuda.get_device_name(0),
           "args": vars(a), "runs": []}
    model, proc = A.load_model(a.model, torch.device("cuda"), lora={"r": 32, "alpha": 64, "dropout": 0.05})
    sc = A.Scorer(proc, "")
    for cam in ("H", "HW"):
        items = pool_items(a.pool, a.n_snap, cam)
        out[f"tokens_{cam}"] = token_stats(sc, items)
        print(json.dumps({"cam": cam, "n_items": len(items), **out[f"tokens_{cam}"]}), flush=True)
        confs = [("old", 1)] + [("shared", m) for m in (a.micros if cam == "HW" else [8])]
        for mode, micro in confs:
            share = mode == "shared"
            its = items if share else items[:a.old_items]
            try:
                r = {"cam": cam, "mode": mode, "micro": micro,
                     "train": time_train_a(model, sc, its, share, micro, a.accum),
                     "eval": time_eval_a(model, sc, its, share, micro)}
            except torch.OutOfMemoryError as e:
                r = {"cam": cam, "mode": mode, "micro": micro, "oom": str(e)[:200]}
                torch.cuda.empty_cache()
            out["runs"].append(r)
            print(json.dumps(r), flush=True)
            json.dump(out, open(a.out, "w"), indent=1)


def stageb_samples(a):
    from harvest.train import stageb_data as D
    syn = D.synthetic_rows(max(a.n, 8), seed=0, img_dir=os.path.join(os.path.dirname(a.out), "r3_syn_img"))
    sets = {"synthetic": syn[:a.n]}
    if a.pool:
        from harvest.jevcall import canonicalize
        from harvest.train.stagea_data import build_items, labels_v2_factory, split_of
        import glob
        src_make = labels_v2_factory()
        pool = []
        for p in sorted(glob.glob(f"{a.pool}/ep*.jsonl"))[:40]:
            seed = int(os.path.basename(p)[2:-6])
            src = src_make(a.pool, seed)
            for ln in (json.loads(x) for x in open(p, encoding="utf-8")):
                if not ln.get("decision") or split_of(ln) != "train":
                    continue
                items = build_items([ln], src, lambda x: D.prompt_state(x, "IMG"), 0)
                ims = D.images_of(ln, "right", True, a.pool)
                for it in items:
                    it["images"] = ims
                s = dict(syn[len(pool) % len(syn)])
                s.update(items=items, key=items[0]["key"], split="train",
                         context={"text": canonicalize(D.prompt_state(ln, "IMG")), "images": ims})
                pool.append(s)
                if len(pool) >= a.n:
                    break
            if len(pool) >= a.n:
                break
        sets["pool_img"] = pool
    return syn, sets


def cmd_stageb(a):
    from harvest.train import stageb_train as T
    from harvest.train.stageb_model import HFEncoder, new_model
    out = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "gpu": torch.cuda.get_device_name(0),
           "args": vars(a), "runs": []}
    dev = torch.device("cuda")
    syn, sets = stageb_samples(a)
    bb, proc, hd = T.load_backbone("qwen", a.model, dev)
    model = new_model(bb, syn, hd, expert_kw={"width": 768, "depth": 8, "heads": 12},
                      aux_kw={"width": 512, "heads": 8}, lam={"dec": 1.0, "act": 1.0, "aux": 0.1}).to(dev)
    enc = HFEncoder(proc)
    opt, _ = T.make_optimizer(model, 1e-7, 1e-7, 100)
    params = [p for g in opt.param_groups for p in g["params"]]
    model.train()
    for name, ss in sets.items():
        if a.sets and name not in a.sets.split(","):
            continue
        for mode, B in [("old", b) for b in a.old_batches] + [("shared", b) for b in a.batches]:
            model.shared = mode == "shared"
            steps = max(2, min(a.steps, len(ss) // B))
            try:
                for i in range(2):  # warm-up
                    loss, _ = model.losses(ss[i * B % len(ss):][:B] or ss[:B], enc, dev)
                    loss.backward()
                opt.zero_grad(set_to_none=True)
                _peak_reset()
                t0 = time.perf_counter()
                for i in range(steps):
                    batch = [ss[(i * B + j) % len(ss)] for j in range(B)]
                    loss, logs = model.losses(batch, enc, dev)
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(params, 1.0)
                    opt.step()
                    opt.zero_grad(set_to_none=True)
                _sync()
                dt = time.perf_counter() - t0
                r = {"data": name, "mode": mode, "batch": B, "steps": steps, "s_per_step": round(dt / steps, 3),
                     "steps_per_s": round(steps / dt, 4), "samples_per_s": round(steps * B / dt, 3),
                     "questions_per_sample": round(sum(len(s["items"]) for s in ss) / len(ss), 2),
                     "peak_gb": _peak()}
            except torch.OutOfMemoryError as e:
                r = {"data": name, "mode": mode, "batch": B, "oom": str(e)[:200]}
                opt.zero_grad(set_to_none=True)
                torch.cuda.empty_cache()
            out["runs"].append(r)
            print(json.dumps(r), flush=True)
            json.dump(out, open(a.out, "w"), indent=1)


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("stagea")
    s.add_argument("--pool", default="/data/harvest/data/pool")
    s.add_argument("--n-snap", type=int, default=64)
    s.add_argument("--old-items", type=int, default=96, help="items timed on the (slow) old path")
    s.add_argument("--accum", type=int, default=64)
    s.add_argument("--micros", type=lambda x: [int(v) for v in x.split(",")], default=[1, 4, 8, 16])
    b = sub.add_parser("stageb")
    b.add_argument("--pool", default="")
    b.add_argument("--n", type=int, default=64)
    b.add_argument("--steps", type=int, default=8)
    b.add_argument("--batches", type=lambda x: [int(v) for v in x.split(",")], default=[4, 8, 16])
    b.add_argument("--old-batches", type=lambda x: [int(v) for v in x.split(",") if v], default=[4])
    b.add_argument("--sets", default="", help="synthetic,pool_img (default: all)")
    for x in (s, b):
        x.add_argument("--model", default=MODEL)
        x.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    {"stagea": cmd_stagea, "stageb": cmd_stageb}[a.cmd](a)


if __name__ == "__main__":
    main()
