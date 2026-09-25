"""Stage-B training of the fused model (canon §51-§52, §58; docs/stage3/results/r4_stageB.md).

  smoke  --backbone tiny|qwen --device cpu|cuda --steps 50 --out DIR     synthetic data, loss / KI / save-load /
                                                                          latency checks (NOT a result)
  train  --data r2|pool --pool DIR[,DIR] --run NAME ...                  our 30 Hz data (R2 / pool stage-B rows)
  train  --data se2e [--se2e-root DIR --se2e-kinds RB1,RB2] --run NAME   S-E2E public data, 10 Hz, H 5 (§62, §63)
         [--reload-check]                                                 save -> reload -> identical chunk / eval

Model: Qwen3-VL-4B-Instruct (stage A's revision) + LoRA r32 on every LLM linear layer (stage A's target, vision
tower frozen) + ActionExpert (flow matching, KI stop-gradient) + AuxGeomHead (privileged geometry, gradient to
the backbone). Loss = lam_dec * decision NLL + lam_act * flow matching + lam_aux * aux (+ lam_vqa * VQA, off).
Prompt state default IMG (task sentence + contract summary + gripper, head + active wrist images; §58); S0/S1
text states are ablations (--state). Action target default absolute (teacher S); --mode residual = ablation.
Data (canon §63): per-arm normalization statistics, gripper as [0, 1] openness per dataset, masked proprio (S-E2E tau)
out of the statistics and the expert input; the dataset's hz goes to the rows check and into stageb.json ("hz").
Pod: /data/harvest/venv_train, every output under /data/harvest, GPU 2 = training / inference compute (user-log 62,
64: no rendering on GPU 2; check it is free with nvidia-smi first). TORCH_DISABLE_NATIVE_JIT=1 (set below if absent).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time

# the pod has no C compiler: torch 2.13 would send some eager ops (Qwen3-VL mrope bmm) to Triton, whose launcher
# build fails ("Failed to find C compiler"); must be set before torch is imported (R7 cycle-1 N1)
os.environ.setdefault("TORCH_DISABLE_NATIVE_JIT", "1")

import numpy as np  # noqa: E402
import torch  # noqa: E402

from . import stageb_data as D
from .stageb_expert import fm_loss, n_params, sample_actions, sample_time
from .stageb_model import HFEncoder, load_heads, new_model

MODEL_DIR = "/data/harvest/models/Qwen3-VL-4B-Instruct"
MODEL_REV = "ebb281ec70b05090aa6165b016eac8ec08e71b17"


def _utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


PROMPT_FILES_B = ("harvest/train/stageb_data.py", "harvest/train/stageb_model.py")


def prompt_config(samples, state):
    """What must match between training and inference (question_id@vN hash input, §59): camera layout, prompt
    state mode, system prompt and the prompt-building source files. 'sha' = hash of all of it."""
    import hashlib

    from ..clients.jevl import SYSTEM
    from .stagea_train import PROMPT_FILES, file_sha
    cams = sorted({D.camera_config(s["context"]["images"]) for s in samples if s.get("context")})
    cfg = {"camera": cams, "state": state, "layout": D.CAMERA_LAYOUT,
           "system_sha": hashlib.sha256(SYSTEM.encode()).hexdigest()[:12],
           "files_sha": file_sha(PROMPT_FILES + PROMPT_FILES_B)}
    cfg["sha"] = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    return cfg


# ------------------------------------------------------------------------------------------ backbone
def tiny_qwen(model_dir=MODEL_DIR, seed=0):
    """Random-init Qwen3-VL with the real architecture, shrunk (2 LLM layers, hidden 64): CPU smoke / tests."""
    from transformers import AutoConfig, AutoModelForImageTextToText
    cfg = AutoConfig.from_pretrained(model_dir)
    t, v = cfg.text_config, cfg.vision_config
    t.hidden_size, t.num_hidden_layers, t.num_attention_heads, t.num_key_value_heads = 64, 2, 4, 2
    t.head_dim, t.intermediate_size = 16, 128
    rs = getattr(t, "rope_scaling", None) or getattr(t, "rope_parameters", None)
    if rs is not None:
        rs["mrope_section"] = [4, 2, 2]
    v.depth, v.hidden_size, v.num_heads, v.intermediate_size, v.out_hidden_size = 2, 32, 2, 64, 64
    v.deepstack_visual_indexes = [0]
    torch.manual_seed(seed)
    return AutoModelForImageTextToText.from_config(cfg, dtype=torch.float32)


def load_backbone(kind, model_dir, device, adapter=None, lora=None, dtype=torch.bfloat16):
    """(peft backbone, processor, hidden size). kind: qwen (real weights) | tiny (random init, fp32)."""
    from peft import LoraConfig, PeftModel, get_peft_model
    from transformers import AutoModelForImageTextToText, AutoProcessor

    from .stagea_train import LORA_TARGET
    proc = AutoProcessor.from_pretrained(model_dir)
    if kind == "tiny":
        base = tiny_qwen(model_dir)
    else:
        base = AutoModelForImageTextToText.from_pretrained(model_dir, dtype=dtype, attn_implementation="sdpa")
    base.to(device)
    if adapter:
        bb = PeftModel.from_pretrained(base, adapter, is_trainable=True)
    else:
        lora = lora or {"r": 32, "alpha": 64, "dropout": 0.05}
        bb = get_peft_model(base, LoraConfig(r=lora["r"], lora_alpha=lora["alpha"], lora_dropout=lora["dropout"],
                                             target_modules=LORA_TARGET, bias="none"))
    return bb, proc, base.config.text_config.hidden_size


def backbone_trainable(bb):
    ps = [(n, p) for n, p in bb.named_parameters() if p.requires_grad]
    bad = [n for n, _ in ps if "visual" in n or "lora" not in n]
    if bad:
        raise RuntimeError(f"non-LoRA or vision params trainable: {bad[:5]}")
    return [p for _, p in ps]


# ------------------------------------------------------------------------------------------ loop
def make_optimizer(model, lr, lr_heads, total, warmup=0.03):
    bb = [p for p in model.backbone.parameters() if p.requires_grad]
    heads = list(model.expert.parameters()) + (list(model.aux.parameters()) if model.aux is not None else [])
    heads += list(model.verify.parameters()) if getattr(model, "verify", None) is not None else []
    groups = [{"params": heads, "lr": lr_heads}]
    if bb:
        groups.append({"params": bb, "lr": lr})
    opt = torch.optim.AdamW(groups, weight_decay=0.0)
    w = max(1, math.ceil(warmup * total))
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: (s + 1) / w if s < w else 0.5 * (1 + math.cos(math.pi * min(1.0, (s - w) / max(1, total - w)))))
    return opt, sched


@torch.no_grad()
def evaluate(model, enc, val, device, seed=0, steps=10):
    """Fixed-noise validation: flow-matching loss (fixed t, noise), aux loss, decision NLL / accuracy, and the
    sampled chunk error (10 Euler steps) in normalized units and in physical units (rad / m)."""
    was = model.training
    model.eval()
    g = torch.Generator().manual_seed(seed)
    fm, aux, dec, acc, mse_n, mae_q = [], [], [], [], [], []
    for s in val:
        a, valid, _ = model.targets([s], device)
        t = sample_time(1, device, g)
        noise = torch.randn(a.shape, generator=g).to(device)
        _, logs = model.losses([s], enc, device, fm_t=t, fm_noise=noise)
        fm.append(logs["fm"])
        if "aux" in logs:
            aux.append(logs["aux"])
        fw = model.last_fw if model.shared and hasattr(enc, "p") else None  # R3: reuse the shared pass of losses()
        if "dec" in logs:
            dec.append(logs["dec"])
            if fw:
                lps = fw[2][0]
            else:
                from .stageb_model import item_images
                from .stagea_loss import item_logprobs
                lps = [item_logprobs(model.backbone, enc.inputs(it["text"], item_images(it), device),
                                     *enc.trie(it["names"]), enc.end, enc.pad) for it in s["items"]]
            for it, lp in zip(s["items"], lps):
                acc.append(max(lp, key=lambda n: float(lp[n])) in it["target"])
        n0 = torch.randn(a.shape, generator=g).to(device)
        ctx, mask = (fw[0], fw[1]) if fw else model.contexts([s], enc, device, grad=False)
        z = sample_actions(model.expert, model.cond([s], ctx, mask, device), steps, n0)
        m = valid[..., None]
        mse_n.append(float((((z - a) ** 2) * m).sum() / (m.sum() * a.shape[-1])))
        act = model.norm.action(z[0].cpu().numpy(), s["action_script"], s.get("arm", "right"))
        ex = np.asarray(s["action_exec"], np.float32)
        vv = np.asarray(s["valid"]) > 0
        mae_q.append(float(np.abs(act[vv, :7] - ex[vv, :7]).mean()))
    model.train(was)
    mean = lambda x: float(np.mean(x)) if x else None  # noqa: E731
    return {"fm": mean(fm), "aux": mean(aux), "dec": mean(dec), "dec_acc": mean(acc), "sample_mse_norm": mean(mse_n),
            "sample_mae_arm_rad": mean(mae_q), "n": len(val)}


def train_loop(model, enc, train, val, device, steps, batch=4, lr=1e-4, lr_heads=1e-4, eval_every=10,
               seed=0, log=print, clip=1.0):
    rng = random.Random(seed)
    torch.manual_seed(seed)
    opt, sched = make_optimizer(model, lr, lr_heads, steps)
    params = [p for g in opt.param_groups for p in g["params"]]
    hist = [{"event": "eval", "step": 0, **evaluate(model, enc, val, device, seed)}]
    log(hist[-1])
    model.train()
    order, t0 = [], time.time()
    for step in range(1, steps + 1):
        if len(order) < batch:
            order += rng.sample(range(len(train)), len(train))
        idx, order = order[:batch], order[batch:]
        loss, logs = model.losses([train[i] for i in idx], enc, device)
        loss.backward()
        gn = float(torch.nn.utils.clip_grad_norm_(params, clip))
        opt.step()
        sched.step()
        opt.zero_grad(set_to_none=True)
        rec = {"event": "train", "step": step, **{k: round(v, 5) for k, v in logs.items()}, "grad_norm": round(gn, 4),
               "lr_heads": opt.param_groups[0]["lr"], "elapsed_s": round(time.time() - t0, 1)}
        hist.append(rec)
        log(rec)
        if step % eval_every == 0 or step == steps:
            hist.append({"event": "eval", "step": step, **evaluate(model, enc, val, device, seed)})
            log(hist[-1])
    return hist


# ------------------------------------------------------------------------------------------ checks
def ki_check(model, enc, samples, device):
    """Gradient of each loss w.r.t. the trainable backbone parameters (LoRA): the flow-matching loss must give
    exactly zero under KI 'stop'; the aux and decision losses must reach the backbone."""
    from .stageb_expert import aux_loss
    bb = [p for p in model.backbone.parameters() if p.requires_grad]
    model.zero_grad(set_to_none=True)
    ctx, mask = model.contexts(samples, enc, device, grad=True)
    a, valid, _ = model.targets(samples, device)
    l_fm = fm_loss(model.expert, model.cond(samples, ctx, mask, device), a, valid)
    g_fm = torch.autograd.grad(l_fm, bb, allow_unused=True, retain_graph=True)
    r, rm, c, cm = (torch.tensor(np.stack(x), device=device) for x in zip(*[D.aux_vecs(s["aux"]) for s in samples]))
    l_aux, _ = aux_loss(model.aux, ctx, mask, r, rm, c, cm)
    g_aux = torch.autograd.grad(l_aux, bb, allow_unused=True)
    l_dec = model.decision_loss(samples, enc, device)
    g_dec = torch.autograd.grad(l_dec, bb, allow_unused=True)
    norm = lambda gs: float(sum((g.float() ** 2).sum() for g in gs if g is not None)) ** 0.5  # noqa: E731
    g_exp = torch.autograd.grad(l_fm, list(model.expert.parameters()), allow_unused=True)
    return {"ki": model.ki, "backbone_grad_norm_from_fm": norm(g_fm), "backbone_grad_norm_from_aux": norm(g_aux),
            "backbone_grad_norm_from_dec": norm(g_dec), "expert_grad_norm_from_fm": norm(g_exp)}


def latency(model, enc, sample, device, steps=10, reps=30, warm=5):
    """Expert-only sampling (context precomputed) and full predict (context forward + sampling), seconds."""
    def sync():
        if device.type == "cuda":
            torch.cuda.synchronize()
    with torch.no_grad():
        ctx, mask = model.contexts([sample], enc, device, grad=False)
        cond = model.cond([sample], ctx, mask, device)
        out = {}
        for name, fn in (("expert_sample_s", lambda: sample_actions(model.expert, cond, steps)),
                         ("full_predict_s", lambda: model.predict(sample, enc, device, steps))):
            ts = []
            for i in range(warm + reps):
                sync()
                t0 = time.perf_counter()
                fn()
                sync()
                if i >= warm:
                    ts.append(time.perf_counter() - t0)
            ts.sort()
            out[name] = {"p50": ts[len(ts) // 2], "p95": ts[int(0.95 * (len(ts) - 1))], "n": len(ts)}
    out["ctx_tokens"] = int(mask.sum())
    return out


def reload_check(model, enc, va, device, ck, backbone_kind, model_dir, seed=0, dtype=torch.bfloat16) -> dict:
    """Reload a saved checkpoint (adapter + heads) into a fresh backbone: the sampled chunk of va[0] (fixed noise)
    and the fixed-noise validation metrics must be identical (R7 cycle-1 N10)."""
    g = torch.Generator().manual_seed(123)
    noise = torch.randn(1, model.expert.cfg.horizon, model.expert.cfg.act_dim, generator=g).to(device)
    was = model.training
    model.eval()
    before = model.predict(va[0], enc, device, noise=noise)
    ev_before = evaluate(model, enc, va, device, seed)
    bb2, _, _ = load_backbone(backbone_kind, model_dir, device, adapter=os.path.join(ck, "adapter"), dtype=dtype)
    m2 = load_heads(ck, bb2, device).eval()
    m2.shared = model.shared
    after = m2.predict(va[0], enc, device, noise=noise)
    ev_after = evaluate(m2, enc, va, device, seed)
    model.train(was)
    del m2, bb2
    if device.type == "cuda":
        torch.cuda.empty_cache()
    return {"max_abs_action_diff": float(np.abs(before - after).max()), "eval_before": ev_before,
            "eval_after": ev_after, "eval_equal": ev_before == ev_after,
            "norm_equal": json.load(open(os.path.join(ck, "stageb.json")))["norm"] == model.norm.to_json()}


# ------------------------------------------------------------------------------------------ commands
def cmd_smoke(a):
    out = a.out
    os.makedirs(out, exist_ok=True)
    device = torch.device(a.device)
    samples = D.synthetic_rows(a.n, seed=a.seed, img_dir=os.path.join(out, "img"))
    tr, va = D.split_samples(samples)
    bb, proc, hd = load_backbone(a.backbone, a.model, device)
    backbone_trainable(bb)
    ek = {"width": a.width, "depth": a.depth, "heads": a.heads}
    model = new_model(bb, tr, hd, mode=a.mode, ki=a.ki, expert_kw=ek,
                      aux_kw={"width": min(512, a.width), "heads": 4 if a.width < 256 else 8},
                      lam={"dec": a.lam_dec, "act": a.lam_act, "aux": a.lam_aux, "ver": a.lam_ver}).to(device)
    model.shared = not a.no_share
    enc = HFEncoder(proc)
    log = open(os.path.join(out, "log.jsonl"), "w")

    def write(rec):
        rec["utc"] = _utc()
        log.write(json.dumps(rec) + "\n")
        log.flush()
        print(json.dumps(rec), flush=True)
    pcfg = prompt_config(samples, "IMG")
    write({"event": "config", "args": vars(a), "n_train": len(tr), "n_val": len(va), "prompt_config": pcfg,
           "expert_params": n_params(model.expert), "aux_params": n_params(model.aux),
           "lora_params": sum(p.numel() for p in bb.parameters() if p.requires_grad),
           "device": torch.cuda.get_device_name(device) if device.type == "cuda" else "cpu"})
    write({"event": "ki_check_step0", **ki_check(model, enc, tr[:2], device)})
    hist = train_loop(model, enc, tr, va, device, a.steps, a.batch, a.lr, a.lr_heads, a.eval_every, a.seed, write)
    write({"event": "ki_check_end", **ki_check(model, enc, tr[:2], device)})
    # save -> reload into a fresh backbone -> identical outputs
    ck = os.path.join(out, "ckpt")
    bb.save_pretrained(os.path.join(ck, "adapter"))
    model.save_heads(ck, {"base_model": a.model, "base_rev": MODEL_REV if a.backbone == "qwen" else "tiny-random",
                          "prompt_config": pcfg, "hz": D.HZ})
    write({"event": "save_load", **reload_check(model, enc, va, device, ck, a.backbone, a.model, a.seed)})
    write({"event": "latency", "steps": 10, **latency(model, enc, va[0], device)})
    first = [h for h in hist if h["event"] == "train"][:5]
    last = [h for h in hist if h["event"] == "train"][-5:]
    write({"event": "summary", "train_total_first5": float(np.mean([h["total"] for h in first])),
           "train_total_last5": float(np.mean([h["total"] for h in last])),
           "eval_first": hist[0], "eval_last": [h for h in hist if h["event"] == "eval"][-1]})


def cmd_train(a):
    """Stage-B training: --data r2|pool (our 30 Hz rows) or se2e (S-E2E public data, 10 Hz, H 5; §62-§63)."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dev = None
    if a.dev_val_seeds:
        from .stagea_train import _seedset
        dev = _seedset(a.dev_val_seeds)
    if a.data != "se2e" and not a.pool:
        raise SystemExit(f"--data {a.data}: --pool DIR[,DIR] needed")
    if a.data == "se2e" and a.state != "IMG":
        raise SystemExit("--data se2e: the rows carry an IMG-style context only (task + gripper), --state IMG")
    try:
        samples, hz = D.load_for_training(a.data, pool=a.pool, rows=a.rows, se2e_root=a.se2e_root,
                                          se2e_kinds=a.se2e_kinds, state=a.state, wrist=not a.no_wrist,
                                          dev_val_seeds=dev, labels=not a.no_labels)
    except ValueError as e:
        raise SystemExit(str(e))
    tr, va = D.split_samples(samples)
    if a.max_train:
        tr = random.Random(a.seed).sample(tr, min(a.max_train, len(tr)))
    if not tr or not va:
        raise SystemExit(f"no samples: train {len(tr)} val {len(va)}")
    out = os.path.join(a.out_root, a.run)
    if os.path.exists(os.path.join(out, "log.jsonl")) and not a.overwrite:
        raise SystemExit(f"{out} exists (use --overwrite)")
    os.makedirs(out, exist_ok=True)
    bb, proc, hd = load_backbone("qwen", a.model, device, adapter=a.init_adapter or None)
    backbone_trainable(bb)
    if a.grad_ckpt:
        bb.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        bb.enable_input_require_grads()
    model = new_model(bb, tr, hd, mode=a.mode, ki=a.ki, lam={"dec": a.lam_dec, "act": a.lam_act, "aux": a.lam_aux,
                                                             "vqa": 0.0, "ver": a.lam_ver}).to(device)
    model.shared = not a.no_share
    enc = HFEncoder(proc)
    log = open(os.path.join(out, "log.jsonl"), "a")

    def write(rec):
        rec["utc"] = _utc()
        log.write(json.dumps(rec) + "\n")
        log.flush()
        print(json.dumps(rec), flush=True)
    pcfg = prompt_config(samples, a.state)
    arms = {arm: sum(s.get("arm", "right") == arm for s in tr) for arm in ("left", "right")}
    write({"event": "config", "args": vars(a), "n_train": len(tr), "n_val": len(va), "model_rev": MODEL_REV,
           "prompt_config": pcfg, "data": a.data, "hz": hz, "H": tr[0]["H"], "train_arms": arms,
           "grip_space": model.norm.grip_space, "grip_src": sorted({s["grip_src"] for s in tr}),
           "proprio_masked": sum(1 for s in tr if s.get("proprio_mask") and 0 in s["proprio_mask"].values()),
           "expert_params": n_params(model.expert), "python": sys.version.split()[0]})
    total = a.max_steps or math.ceil(len(tr) / a.batch) * a.epochs
    val = va[:a.max_val] if a.max_val else va
    train_loop(model, enc, tr, val, device, total, a.batch, a.lr, a.lr_heads, a.eval_every, a.seed, write)
    last = os.path.join(out, "last")
    bb.save_pretrained(os.path.join(last, "adapter"))
    model.save_heads(last, {"base_model": a.model, "base_rev": MODEL_REV, "prompt_config": pcfg, "hz": hz,
                            "data": a.data})
    if a.reload_check:
        write({"event": "save_load", **reload_check(model, enc, val, device, last, "qwen", a.model, a.seed)})


def _common(p):
    p.add_argument("--model", default=MODEL_DIR)
    p.add_argument("--mode", default="absolute", choices=("absolute", "residual"))
    p.add_argument("--ki", default="stop", help="stop | none | scale:<g>")
    p.add_argument("--lam-dec", type=float, default=1.0)
    p.add_argument("--lam-act", type=float, default=1.0)
    p.add_argument("--lam-aux", type=float, default=0.1)
    p.add_argument("--lam-ver", type=float, default=0.1, help="verification head (§61/§64), 0 = off")
    p.add_argument("--lr", type=float, default=1e-4, help="LoRA")
    p.add_argument("--lr-heads", type=float, default=1e-4, help="expert + aux head")
    p.add_argument("--batch", type=int, default=4)
    p.add_argument("--eval-every", type=int, default=10)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--no-share", action="store_true", help="old path: separate forward per context / question")


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("smoke")
    _common(s)
    s.add_argument("--backbone", default="tiny", choices=("tiny", "qwen"))
    s.add_argument("--device", default="cpu")
    s.add_argument("--out", required=True)
    s.add_argument("--n", type=int, default=40)
    s.add_argument("--steps", type=int, default=50)
    s.add_argument("--width", type=int, default=128)
    s.add_argument("--depth", type=int, default=2)
    s.add_argument("--heads", type=int, default=4)
    t = sub.add_parser("train")
    _common(t)
    t.add_argument("--data", default="r2", choices=sorted(D.DATA_HZ), help="r2 | pool (30 Hz) | se2e (10 Hz, §62)")
    t.add_argument("--pool", default="", help="--data r2|pool: episode folder(s) with <folder>.stageb.jsonl")
    t.add_argument("--se2e-root", default=D.SE2E_ROOT, help="--data se2e: <root>/<kind>.stageb.jsonl + frames")
    t.add_argument("--se2e-kinds", default="RB1,RB2")
    t.add_argument("--no-labels", action="store_true", help="--data se2e: actions only (no heuristic decisions)")
    t.add_argument("--reload-check", action="store_true", help="after saving: reload -> identical chunk / eval")
    t.add_argument("--run", required=True)
    t.add_argument("--out-root", default="/data/harvest/ckpt/stageB")
    t.add_argument("--state", default="IMG", help="IMG (default, §58) | S0 | S1 (ablation)")
    t.add_argument("--no-wrist", action="store_true", help="head image only (ablation of §57)")
    t.add_argument("--init-adapter", default="", help="start from a stage-A LoRA adapter")
    t.add_argument("--epochs", type=int, default=2)
    t.add_argument("--max-steps", type=int, default=0)
    t.add_argument("--max-val", type=int, default=0)
    t.add_argument("--dev-val-seeds", default="")
    t.add_argument("--rows", default="", help="R2 rows file per --pool folder (default <folder>.stageb.jsonl)")
    t.add_argument("--max-train", type=int, default=0, help="random subset of the train samples (smoke)")
    t.add_argument("--grad-ckpt", action="store_true")
    t.add_argument("--overwrite", action="store_true")
    a = ap.parse_args(argv)
    {"smoke": cmd_smoke, "train": cmd_train}[a.cmd](a)


if __name__ == "__main__":
    main()
