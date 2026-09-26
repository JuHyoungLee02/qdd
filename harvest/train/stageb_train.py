"""Stage-B training of the fused model (canon §51-§52, §58; docs/stage3/results/r4_stageB.md).

  smoke  --backbone tiny|qwen --device cpu|cuda --steps 50 --out DIR     synthetic data, loss / KI / save-load /
                                                                          latency checks (NOT a result)
  train  --data r2|pool --pool DIR[,DIR] --run NAME ...                  our 30 Hz data (R2 / pool stage-B rows)
  train  --data se2e [--se2e-root DIR --se2e-kinds RB1,RB2] --run NAME   S-E2E public data, 10 Hz, H 5 (§62, §63)
         [--reload-check]                                                 save -> reload -> identical chunk / eval
         [--val-per-kind N --val-seed S]                                  stratified val subset per source (§69 N2)
         [--save-every N] [--resume CKPT] [--stop-at N]                   checkpoints + exact resume (§69 N3)
  evalck --ckpt DIR [same data / val / --seed] --against LOG --step N    reloaded checkpoint eval == logged eval
  train  ... [--init-weights CKPT] [--train-subset N --train-subset-seed S] [--lr-schedule constant --warmup-steps W]
         [--eval-train-subset]                                            diagnostics (prereg_se2e_diag D1 / D2)
  predict --ckpt DIR [same data / val / --seed] --out JSONL               per-item decision predictions (D3)
  train|evalck|predict --data se2e [--camera-layout D27v2-video2] [--motion-line se2e-motion@v1 --motion-bins F]
         [--se2e-t-root DIR] [--motion-dropout 0.3]                       OPT-IN temporal context (prereg_se2e_temporal)
  train|evalck|predict ... [--aux-extra a3d@v1 --a3d-root DIR]            OPT-IN training-only aux trajectory target
         predict [--aux-view base] [--extra-out JSON]                     (prereg_ma1b; decision / chunk path unchanged)

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
    from ..serialize import format_record
    from .stagea_train import PROMPT_FILES, file_sha
    cams = sorted({D.camera_config(s["context"]["images"]) for s in samples if s.get("context")})
    cfg = {"camera": cams, "state": state, "layout": D.CAMERA_LAYOUT,
           "system_sha": hashlib.sha256(SYSTEM.encode()).hexdigest()[:12],
           **format_record(),  # ser-A-min-3 (canon §77 supplement (4), controller ruling PH-A 2)
           "files_sha": file_sha(PROMPT_FILES + PROMPT_FILES_B)}
    cfg["sha"] = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    return cfg


# prereg_se2e_temporal: OPT-IN temporal options (defaults = the S-E2E behaviour and prompt_config above, unchanged)
TEMPORAL_FILES = ("harvest/train/se2e_temporal.py", "harvest/train/se2e_temporal_model.py",
                  "harvest/train/se2e_data.py")


def temporal_on(a) -> bool:
    return getattr(a, "camera_layout", "D27v1") != "D27v1" or getattr(a, "motion_line", "none") != "none"


def prompt_config_t(samples, state, layout, bins=None, aux=None):
    """prompt_config of a temporal-option run: new layout id (D27v2-video2) / motion line version + bins, and the
    option files in files_sha, so its checkpoints never pass as a default-layout checkpoint. aux (prereg_ma1b) = the
    training-only auxiliary trajectory target version: recorded with its files (absent key when None = unchanged)."""
    import hashlib

    from ..clients.jevl import SYSTEM
    from ..serialize import format_record
    from .stagea_train import PROMPT_FILES, file_sha
    cams = sorted({layout + ":" + "|".join(im[0] for im in s["context"]["images"]) for s in samples
                   if s.get("context")})
    cfg = {"camera": cams, "state": state, "layout": layout, "motion": bins,
           "system_sha": hashlib.sha256(SYSTEM.encode()).hexdigest()[:12], **format_record(),
           "files_sha": file_sha(PROMPT_FILES + PROMPT_FILES_B + TEMPORAL_FILES + (AUX_FILES if aux else ()))}
    if aux:
        cfg["aux"] = aux
    cfg["sha"] = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    return cfg


# prereg_ma1b: OPT-IN training-only auxiliary trajectory target (the decision / chunk path is the default one)
AUX_CHOICES = ("none", "a3d@v1")
AUX_FILES = ("harvest/train/se2e_a3d.py", "harvest/train/se2e_trace.py", "harvest/train/se2e_trace_model.py")


def attach_aux_targets(a, samples) -> None:
    """In place: the --aux-extra targets of every sample (a3d@v1: <a3d-root>/<kind>.a3d.jsonl; KeyError if missing)."""
    if getattr(a, "aux_extra", "none") == "none":
        return
    from .se2e_a3d import attach
    for kind in sorted({s["key"].split("_")[0] for s in samples}):
        attach(samples, a.a3d_root, kind)


def aux_model(a, model, new: bool):
    """--aux-extra: a new model gets the extra aux outputs (with_trace_head); a loaded one is switched to the trained
    view (as_trace), or with --aux-view base to the plain StageB view (runtime path check)."""
    ver = getattr(a, "aux_extra", "none")
    if ver == "none":
        return model
    from . import se2e_trace_model as TM
    if new:
        return TM.with_trace_head(model, ver)
    if getattr(a, "aux_view", "trained") == "base":
        return TM.base_view(model, ver)
    return TM.as_trace(model, ver)


def motion_bins_of(a):
    if getattr(a, "motion_line", "none") == "none":
        return None
    if not a.motion_bins:
        raise SystemExit("--motion-line: --motion-bins FILE (train-split bins, fixed before training) needed")
    b = json.load(open(a.motion_bins))
    if b.get("version") != a.motion_line:
        raise SystemExit(f"--motion-bins version {b.get('version')!r} != --motion-line {a.motion_line!r}")
    return b


def temporal_model(a, model, proc):
    """(model, encoder) for the run's options: the default HFEncoder / StageB, or the video2 pair encoder."""
    if getattr(a, "camera_layout", "D27v1") == "D27v1":
        return model, HFEncoder(proc)
    from .se2e_temporal_model import VideoEncoder, as_temporal
    return as_temporal(model), VideoEncoder(proc)


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
def _param_groups(model):
    bb = [p for p in model.backbone.parameters() if p.requires_grad]
    heads = list(model.expert.parameters()) + (list(model.aux.parameters()) if model.aux is not None else [])
    heads += list(model.verify.parameters()) if getattr(model, "verify", None) is not None else []
    return heads, bb


def opt_param_names(model):
    """Parameter names in optimizer order (a resumed optimizer state must meet the same parameters)."""
    names = {id(p): n for n, p in model.named_parameters()}
    return [[names[id(p)] for p in g] for g in _param_groups(model) if g]


def make_optimizer(model, lr, lr_heads, total, warmup=0.03, schedule="cosine", warmup_steps=0):
    """AdamW; linear warmup (warmup_steps, 0 = warmup * total) then cosine to 0 (default) or constant
    (prereg_se2e_diag D1 / D2)."""
    heads, bb = _param_groups(model)
    groups = [{"params": heads, "lr": lr_heads}]
    if bb:
        groups.append({"params": bb, "lr": lr})
    opt = torch.optim.AdamW(groups, weight_decay=0.0)
    w = warmup_steps or max(1, math.ceil(warmup * total))
    if schedule == "constant":
        f = lambda s: (s + 1) / w if s < w else 1.0  # noqa: E731
    elif schedule == "cosine":
        f = lambda s: (s + 1) / w if s < w else 0.5 * (1 + math.cos(math.pi * min(1.0, (s - w) / max(1, total - w))))  # noqa: E731
    else:
        raise ValueError(f"schedule {schedule!r}")
    return opt, torch.optim.lr_scheduler.LambdaLR(opt, f)


@torch.no_grad()
def evaluate(model, enc, val, device, seed=0, steps=10, records=None):
    """Fixed-noise validation: flow-matching loss (fixed t, noise), aux loss, decision NLL / accuracy, and the
    sampled chunk error (10 Euler steps) in normalized units and in physical units (rad / m). records = a list:
    one dict per decision item appended (key, question, target, option log-probs, argmax, correct; D3 dumps)."""
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
                if records is not None:
                    lpf = {n: float(v) for n, v in lp.items()}
                    pred = max(lp, key=lambda n: float(lp[n]))
                    records.append({"key": s["key"], "question": it["question"], "target": list(it["target"]),
                                    "pred": pred, "correct": acc[-1], "lp": lpf})
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


def source_of(s) -> str:
    """Source dataset of a sample = its key prefix (S-E2E: RB1 / RB2; our rows: the perturbation kind)."""
    return s["key"].split("_")[0]


def stratified_val(va, n_per_source: int, seed: int = 0):
    """§69 N2: a seeded random validation subset with n samples of every source dataset (all of a source with fewer),
    independent of the input order (sorted by key first). n 0 = the whole split. `--max-val` (first N) would see RB1
    only, because the rows are loaded RB1 first."""
    if not n_per_source:
        return va
    by = {}
    for s in sorted(va, key=lambda s: s["key"]):
        by.setdefault(source_of(s), []).append(s)
    rng = random.Random(seed)
    return [s for src in sorted(by) for s in (by[src] if len(by[src]) <= n_per_source
                                              else rng.sample(by[src], n_per_source))]


# settings that change the training trajectory (or the logged evaluation sets): a resumed run must use the
# checkpoint's values. R7 cycle 15 N2: + the prereg_se2e_diag options (schedule, warmup, train subset / fraction,
# train-set evaluation) and the prereg_se2e_temporal options (camera layout, motion line / bins / dropout, rows root).
RESUME_KEYS = ("data", "pool", "rows", "se2e_root", "se2e_kinds", "no_labels", "state", "no_wrist", "dev_val_seeds",
               "model", "mode", "ki", "lam_dec", "lam_act", "lam_aux", "lam_ver", "lr", "lr_heads", "batch", "seed",
               "epochs", "max_steps", "max_train", "max_val", "val_per_kind", "val_seed", "no_share", "init_adapter",
               "lr_schedule", "warmup_steps", "train_subset", "train_subset_seed", "train_fraction",
               "eval_train_subset", "eval_train_per_kind",
               "camera_layout", "motion_line", "motion_bins", "motion_dropout", "se2e_t_root", "aux_extra", "a3d_root")
# every other option of `train` (bookkeeping: names, output, cadence, memory). eval_every: evaluate() uses its own
# generator, so the trajectory does not depend on it; init_weights: refused together with --resume (the weights come
# from the checkpoint); grad_ckpt: recomputation only. A new option must be added to one of the two (test).
RESUME_FREE = ("cmd", "run", "out_root", "resume", "stop_at", "overwrite", "reload_check", "save_every", "eval_every",
               "grad_ckpt", "init_weights")


def val_subset(va, max_val: int, val_per_kind: int, val_seed: int):
    """Evaluation set: --max-val N (first N, earlier smokes) or --val-per-kind N (stratified, seeded; §69 N2)."""
    if max_val and val_per_kind:
        raise SystemExit("--max-val and --val-per-kind: use one")
    return va[:max_val] if max_val else stratified_val(va, val_per_kind, val_seed)


def check_resume_args(saved: dict, now: dict):
    """Refuse a resume whose RESUME_KEYS differ from the checkpoint's. A key missing from the saved args (a checkpoint
    written before the option existed) counts as the option's default: every option was added with a default that
    keeps the earlier behaviour (prereg_se2e_diag section 1, prereg_se2e_temporal)."""
    d = vars(build_parser().parse_args(["train", "--run", "_"]))
    bad = {k: (saved.get(k, d[k]), now.get(k, d[k])) for k in RESUME_KEYS if saved.get(k, d[k]) != now.get(k, d[k])}
    if bad:
        raise SystemExit(f"--resume: settings differ from the checkpoint's run (saved, now): {bad}")


def train_subset(tr, n_per_source: int, seed: int = 0):
    """prereg_se2e_diag D2: a seeded stratified subset of the train split, n samples of every source (0 = all)."""
    return stratified_val(tr, n_per_source, seed)


def train_fraction(tr, frac: float, seed: int = 0):
    """prereg_se2e_diag section 7: round(frac * n) samples of every source (the source mix of the whole split), the
    head of a seeded shuffle of the key-sorted samples, so smaller fractions are inside larger ones (0 = all)."""
    if not frac:
        return tr
    by = {}
    for s in sorted(tr, key=lambda s: s["key"]):
        by.setdefault(source_of(s), []).append(s)
    out = []
    for src in sorted(by):
        xs = list(by[src])
        random.Random(seed).shuffle(xs)
        out += xs[:round(frac * len(xs))]
    return out


def train_loop(model, enc, train, val, device, steps, batch=4, lr=1e-4, lr_heads=1e-4, eval_every=10,
               seed=0, log=print, clip=1.0, save_every=0, save=None, resume=None, stop_at=0, schedule="cosine",
               warmup_steps=0, extra_evals=None, batch_fn=None):
    """steps = the schedule length. save(step, train_state) every save_every steps and at the last step (the caller
    writes the weights). resume = a saved train_state: optimizer, scheduler, RNG states and the data order continue
    exactly (the caller has loaded the checkpoint's weights). stop_at = stop after that step (resume check).
    extra_evals = {name: samples}: also evaluated at every eval step, logged as event 'eval_<name>'.
    batch_fn(batch, step) -> batch: training-batch transform (prereg_se2e_temporal motion-line dropout; None = off)."""
    rng = random.Random(seed)
    torch.manual_seed(seed)
    opt, sched = make_optimizer(model, lr, lr_heads, steps, schedule=schedule, warmup_steps=warmup_steps)
    params = [p for g in opt.param_groups for p in g["params"]]
    order, start = [], 0

    def extra(step):
        for name, ss in (extra_evals or {}).items():
            hist.append({"event": f"eval_{name}", "step": step, **evaluate(model, enc, ss, device, seed)})
            log(hist[-1])
    if resume is None:
        hist = [{"event": "eval", "step": 0, **evaluate(model, enc, val, device, seed)}]
        log(hist[-1])
        extra(0)
    else:
        start, order = resume["step"], list(resume["order"])
        rng.setstate(resume["py_rng"])
        opt.load_state_dict(resume["opt"])
        sched.load_state_dict(resume["sched"])
        torch.set_rng_state(resume["torch_rng"])
        if device.type == "cuda" and resume.get("cuda_rng") is not None:
            torch.cuda.set_rng_state(resume["cuda_rng"], device)
        hist = [{"event": "resume", "step": start}]
        log(hist[-1])
    model.train()
    t0 = time.time()
    for step in range(start + 1, steps + 1):
        if len(order) < batch:
            order += rng.sample(range(len(train)), len(train))
        idx, order = order[:batch], order[batch:]
        batch_s = [train[i] for i in idx]
        if batch_fn is not None:
            batch_s = batch_fn(batch_s, step)
        loss, logs = model.losses(batch_s, enc, device)
        loss.backward()
        gn = float(torch.nn.utils.clip_grad_norm_(params, clip))
        opt.step()
        sched.step()
        opt.zero_grad(set_to_none=True)
        rec = {"event": "train", "step": step, **{k: round(v, 5) for k, v in logs.items()}, "grad_norm": round(gn, 4),
               "lr_heads": opt.param_groups[0]["lr"], "idx": idx, "elapsed_s": round(time.time() - t0, 1)}
        hist.append(rec)
        log(rec)
        if step % eval_every == 0 or step == steps:
            hist.append({"event": "eval", "step": step, **evaluate(model, enc, val, device, seed)})
            log(hist[-1])
            extra(step)
        if save is not None and save_every and (step % save_every == 0 or step == steps):
            save(step, {"step": step, "order": list(order), "py_rng": rng.getstate(), "opt": opt.state_dict(),
                        "sched": sched.state_dict(), "torch_rng": torch.get_rng_state(),
                        "cuda_rng": torch.cuda.get_rng_state(device) if device.type == "cuda" else None})
        if stop_at and step >= stop_at:
            break
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


def _load_data(a):
    """(samples, hz, train, val split) of --data (train subset by --max-train)."""
    dev = None
    if a.dev_val_seeds:
        from .stagea_train import _seedset
        dev = _seedset(a.dev_val_seeds)
    if a.data != "se2e" and not a.pool:
        raise SystemExit(f"--data {a.data}: --pool DIR[,DIR] needed")
    if a.data == "se2e" and a.state != "IMG":
        raise SystemExit("--data se2e: the rows carry an IMG-style context only (task + gripper), --state IMG")
    try:
        if temporal_on(a):  # prereg_se2e_temporal: augmented rows (se2e_t), current frames from --se2e-root
            if a.data != "se2e":
                raise SystemExit("--camera-layout / --motion-line: --data se2e only")
            from .se2e_temporal import load_for_training_t
            samples, hz = load_for_training_t(a.se2e_t_root, image_root=a.se2e_root, kinds=a.se2e_kinds,
                                              layout=a.camera_layout, bins=motion_bins_of(a),
                                              labels=not a.no_labels, wrist=not a.no_wrist)
        else:
            samples, hz = D.load_for_training(a.data, pool=a.pool, rows=a.rows, se2e_root=a.se2e_root,
                                              se2e_kinds=a.se2e_kinds, state=a.state, wrist=not a.no_wrist,
                                              dev_val_seeds=dev, labels=not a.no_labels)
    except ValueError as e:
        raise SystemExit(str(e))
    if getattr(a, "aux_extra", "none") != "none":
        if a.data != "se2e":
            raise SystemExit("--aux-extra: --data se2e only")
        attach_aux_targets(a, samples)
    tr, va = D.split_samples(samples)
    if getattr(a, "max_train", 0):
        tr = random.Random(a.seed).sample(tr, min(a.max_train, len(tr)))
    if not tr or not va:
        raise SystemExit(f"no samples: train {len(tr)} val {len(va)}")
    return samples, hz, tr, va


def _writer(path):
    log = open(path, "a")

    def write(rec):
        rec["utc"] = _utc()
        log.write(json.dumps(rec) + "\n")
        log.flush()
        print(json.dumps(rec), flush=True)
    return write


def save_ckpt(path, bb, model, extra, state=None):
    """adapter/ + heads.pt + stageb.json (the runtime / reload format) [+ train_state.pt for --resume]."""
    bb.save_pretrained(os.path.join(path, "adapter"))
    model.save_heads(path, extra)
    if state is not None:
        torch.save(state, os.path.join(path, "train_state.pt"))


def cmd_train(a):
    """Stage-B training: --data r2|pool (our 30 Hz rows) or se2e (S-E2E public data, 10 Hz, H 5; §62-§63).
    --save-every N: checkpoints <run>/ckpt/step_NNNNNN (+ train_state.pt); --resume DIR continues one exactly
    (same settings, checked); --stop-at N stops after step N (resume check); --val-per-kind N: stratified val (§69)."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    samples, hz, tr, va = _load_data(a)
    out = os.path.join(a.out_root, a.run)
    if os.path.exists(os.path.join(out, "log.jsonl")) and not a.overwrite:
        raise SystemExit(f"{out} exists (use --overwrite)")
    resume = None
    if a.resume:
        resume = torch.load(os.path.join(a.resume, "train_state.pt"), map_location="cpu", weights_only=False)
        check_resume_args(resume["args"], vars(a))
        if a.init_adapter or a.init_weights:
            raise SystemExit("--resume and --init-adapter / --init-weights: use one")
    if a.init_weights and a.init_adapter:
        raise SystemExit("--init-weights and --init-adapter: use one")
    os.makedirs(out, exist_ok=True)
    wdir = a.resume or a.init_weights  # --init-weights: adapter + heads only, fresh optimizer / schedule / data order
    if wdir:
        bb, proc, hd = load_backbone("qwen", a.model, device, adapter=os.path.join(wdir, "adapter"))
        model = load_heads(wdir, bb, device)
    else:
        bb, proc, hd = load_backbone("qwen", a.model, device, adapter=a.init_adapter or None)
    backbone_trainable(bb)
    if a.grad_ckpt:
        bb.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        bb.enable_input_require_grads()
    if not wdir:
        model = new_model(bb, tr, hd, mode=a.mode, ki=a.ki,
                          lam={"dec": a.lam_dec, "act": a.lam_act, "aux": a.lam_aux, "vqa": 0.0, "ver": a.lam_ver})
    model = aux_model(a, model, new=not wdir)  # prereg_ma1b --aux-extra (none: unchanged)
    # --train-subset: after new_model, so normalization statistics / vocabularies still come from the whole split
    if a.train_subset and a.train_fraction:
        raise SystemExit("--train-subset and --train-fraction: use one")
    full_n, tr = len(tr), train_subset(tr, a.train_subset, a.train_subset_seed)
    tr = train_fraction(tr, a.train_fraction, a.train_subset_seed)
    tr_eval = stratified_val(tr, a.eval_train_per_kind, a.train_subset_seed)  # --eval-train-subset set (0 = all)
    model = model.to(device)
    model.shared = not a.no_share
    pnames = opt_param_names(model)
    if resume is not None and resume["param_names"] != pnames:
        raise SystemExit("--resume: the optimizer state belongs to other parameters")
    model, enc = temporal_model(a, model, proc)
    write = _writer(os.path.join(out, "log.jsonl"))
    bins = motion_bins_of(a)
    aux_ver = None if a.aux_extra == "none" else a.aux_extra
    if aux_ver and not temporal_on(a):
        raise SystemExit("--aux-extra: with the motion line (prereg_ma1b cells)")
    pcfg = prompt_config_t(samples, a.state, a.camera_layout, bins, aux=aux_ver) if temporal_on(a) else \
        prompt_config(samples, a.state)
    batch_fn = None
    if bins is not None and a.motion_dropout > 0:
        from .se2e_temporal import motion_dropout
        batch_fn = lambda b, step: motion_dropout(b, step, a.seed, a.motion_dropout)  # noqa: E731
    arms = {arm: sum(s.get("arm", "right") == arm for s in tr) for arm in ("left", "right")}
    total = a.max_steps or math.ceil(len(tr) / a.batch) * a.epochs
    val = val_subset(va, a.max_val, a.val_per_kind, a.val_seed)
    write({"event": "config", "args": vars(a), "n_train": len(tr), "n_val": len(va), "model_rev": MODEL_REV,
           "prompt_config": pcfg, "data": a.data, "hz": hz, "H": tr[0]["H"], "train_arms": arms,
           "grip_space": model.norm.grip_space, "grip_src": sorted({s["grip_src"] for s in tr}),
           "proprio_masked": sum(1 for s in tr if s.get("proprio_mask") and 0 in s["proprio_mask"].values()),
           "expert_params": n_params(model.expert), "python": sys.version.split()[0], "total_steps": total,
           "val_used": len(val), "val_sources": {k: sum(source_of(s) == k for s in val)
                                                 for k in sorted({source_of(s) for s in val})},
           "val_keys_sha": _sha([s["key"] for s in val])})
    if a.train_subset or a.train_fraction or a.init_weights or a.lr_schedule != "cosine" or a.warmup_steps \
            or a.eval_train_subset:
        write({"event": "diag_config", "n_train_full": full_n, "n_train_used": len(tr),
               "train_keys_sha": _sha(sorted(s["key"] for s in tr)), "train_fraction": a.train_fraction,
               "n_eval_train": len(tr_eval) if a.eval_train_subset else 0,
               "train_sources": {k: sum(source_of(s) == k for s in tr) for k in sorted({source_of(s) for s in tr})},
               "init_weights": a.init_weights, "lr_schedule": a.lr_schedule, "warmup_steps": a.warmup_steps})
    if temporal_on(a):
        write({"event": "temporal_config", "camera_layout": a.camera_layout, "motion_line": a.motion_line,
               "motion_bins": bins, "motion_dropout": a.motion_dropout if bins is not None else 0.0,
               "se2e_t_root": a.se2e_t_root, "image_root": a.se2e_root})
    if resume is not None and resume["total"] != total:
        raise SystemExit(f"--resume: schedule length {total} != checkpoint's {resume['total']}")
    extra = {"base_model": a.model, "base_rev": MODEL_REV, "prompt_config": pcfg, "hz": hz, "data": a.data}
    if aux_ver:
        extra["aux_extra"] = aux_ver

    def save(step, st):
        path = os.path.join(out, "ckpt", f"step_{step:06d}")
        save_ckpt(path, bb, model, extra, {**st, "args": (resume or {}).get("args", vars(a)), "total": total,
                                           "param_names": pnames})
        write({"event": "ckpt", "step": step, "dir": path})
    train_loop(model, enc, tr, val, device, total, a.batch, a.lr, a.lr_heads, a.eval_every, a.seed, write,
               save_every=a.save_every, save=save, resume=resume, stop_at=a.stop_at, schedule=a.lr_schedule,
               warmup_steps=a.warmup_steps, extra_evals={"train_subset": tr_eval} if a.eval_train_subset else None,
               batch_fn=batch_fn)
    if a.stop_at:
        return
    last = os.path.join(out, "last")
    save_ckpt(last, bb, model, extra)
    if a.reload_check:
        write({"event": "save_load", **reload_check(model, enc, val, device, last, "qwen", a.model, a.seed)})


def _sha(obj) -> str:
    import hashlib
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:12]


def cmd_evalck(a):
    """Reload a saved checkpoint into a fresh backbone and run the fixed-noise validation (same --seed, same val
    subset as the run); --against LOG --step N: must equal the run's logged eval at step N exactly (§69 / S-E2E)."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _, _, _, va = _load_data(a)
    val = val_subset(va, a.max_val, a.val_per_kind, a.val_seed)
    bb, proc, _ = load_backbone("qwen", a.model, device, adapter=os.path.join(a.ckpt, "adapter"))
    m = aux_model(a, load_heads(a.ckpt, bb, device).eval(), new=False)
    m.shared = not a.no_share
    m, enc = temporal_model(a, m, proc)
    ev = evaluate(m, enc, val, device, a.seed)
    rec = {"event": "evalck", "ckpt": a.ckpt, "val_keys_sha": _sha([s["key"] for s in val]), **ev}
    if a.against:
        logged = [json.loads(x) for x in open(a.against)]
        ref = [r for r in logged if r.get("event") == "eval" and r["step"] == a.step]
        if not ref:
            raise SystemExit(f"no eval at step {a.step} in {a.against}")
        ref = {k: v for k, v in ref[-1].items() if k in ev}
        rec.update(step=a.step, logged=ref, equal=ref == ev,
                   max_abs_diff=max(abs((ev[k] or 0) - (ref[k] or 0)) for k in ev))
    write = _writer(a.out) if a.out else (lambda r: print(json.dumps(r), flush=True))
    write(rec)


def cmd_predict(a):
    """prereg_se2e_diag D3: reload a checkpoint, run evaluate() on the val subset (same --seed / subset) and write
    one record per decision item (option log-probs, argmax, target) + a final 'summary' record (the eval metrics)."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _, _, _, va = _load_data(a)
    val = val_subset(va, a.max_val, a.val_per_kind, a.val_seed)
    bb, proc, _ = load_backbone("qwen", a.model, device, adapter=os.path.join(a.ckpt, "adapter"))
    m = aux_model(a, load_heads(a.ckpt, bb, device).eval(), new=False)
    m.shared = not a.no_share
    m, enc = temporal_model(a, m, proc)
    recs = []
    ev = evaluate(m, enc, val, device, a.seed, records=recs)
    write = _writer(a.out)
    for r in recs:
        write({"event": "item", **r})
    write({"event": "summary", "ckpt": a.ckpt, "val_keys_sha": _sha([s["key"] for s in val]), **ev})
    if a.extra_out:  # prereg_ma1b: aux trajectory error (cm) and predicted-decision chunk error, outside the rule
        from .se2e_trace_model import extra_metrics
        json.dump({"ckpt": a.ckpt, "val_keys_sha": _sha([s["key"] for s in val]),
                   **extra_metrics(m, enc, val, device, a.seed)}, open(a.extra_out, "w"), indent=1)


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
    a = build_parser().parse_args(argv)
    {"smoke": cmd_smoke, "train": cmd_train, "evalck": cmd_evalck, "predict": cmd_predict}[a.cmd](a)


def build_parser():
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
    _data(t)
    t.add_argument("--reload-check", action="store_true", help="after saving: reload -> identical chunk / eval")
    t.add_argument("--run", required=True)
    t.add_argument("--out-root", default="/data/harvest/ckpt/stageB")
    t.add_argument("--init-adapter", default="", help="start from a stage-A LoRA adapter")
    t.add_argument("--epochs", type=int, default=2)
    t.add_argument("--max-steps", type=int, default=0)
    t.add_argument("--max-train", type=int, default=0, help="random subset of the train samples (smoke)")
    t.add_argument("--save-every", type=int, default=0, help="checkpoint <run>/ckpt/step_NNNNNN every N steps")
    t.add_argument("--resume", default="", help="continue from a --save-every checkpoint dir (same settings)")
    t.add_argument("--stop-at", type=int, default=0, help="stop after this step (resume check); no last/ save")
    t.add_argument("--grad-ckpt", action="store_true")
    t.add_argument("--overwrite", action="store_true")
    # prereg_se2e_diag (D1 / D2); the defaults keep the S-E2E behaviour
    t.add_argument("--init-weights", default="", help="start from a checkpoint dir's adapter + heads (fresh optimizer)")
    t.add_argument("--train-subset", type=int, default=0, help="stratified train subset: N per source (0 = all)")
    t.add_argument("--train-subset-seed", type=int, default=0)
    t.add_argument("--lr-schedule", default="cosine", choices=("cosine", "constant"))
    t.add_argument("--warmup-steps", type=int, default=0, help="linear warmup steps (0 = 3 %% of the schedule)")
    t.add_argument("--eval-train-subset", action="store_true", help="also evaluate the train (sub)set at each eval")
    t.add_argument("--train-fraction", type=float, default=0.0,
                   help="same fraction of every source, nested across fractions (--train-subset-seed; 0 = all)")
    t.add_argument("--eval-train-per-kind", type=int, default=0,
                   help="--eval-train-subset: stratified N per source of the train (sub)set (0 = all of it)")
    t.add_argument("--motion-dropout", type=float, default=0.3,
                   help="--motion-line: training-only probability of the 'unknown' line (prereg_se2e_temporal)")
    e = sub.add_parser("evalck", help="reload a checkpoint, fixed-noise validation, compare with the run's log")
    _common(e)
    _data(e)
    e.add_argument("--ckpt", required=True)
    e.add_argument("--max-train", type=int, default=0)
    e.add_argument("--against", default="", help="the run's log.jsonl")
    e.add_argument("--step", type=int, default=0, help="the logged eval step the checkpoint belongs to")
    e.add_argument("--out", default="", help="append the result (jsonl)")
    e.add_argument("--aux-view", default="trained", choices=("trained", "base"))
    pr = sub.add_parser("predict", help="per-item decision predictions of a checkpoint on the val subset (D3)")
    _common(pr)
    _data(pr)
    pr.add_argument("--ckpt", required=True)
    pr.add_argument("--max-train", type=int, default=0)
    pr.add_argument("--out", required=True, help="jsonl: one 'item' record per decision item + 'summary'")
    pr.add_argument("--aux-view", default="trained", choices=("trained", "base"),
                    help="--aux-extra checkpoint: trained view, or base = plain StageB (runtime path, prereg_ma1b)")
    pr.add_argument("--extra-out", default="", help="json: aux trajectory error + predicted-decision chunk error")
    return ap


def _data(p):
    p.add_argument("--data", default="r2", choices=sorted(D.DATA_HZ), help="r2 | pool (30 Hz) | se2e (10 Hz, §62)")
    p.add_argument("--pool", default="", help="--data r2|pool: episode folder(s) with <folder>.stageb.jsonl")
    p.add_argument("--se2e-root", default=D.SE2E_ROOT, help="--data se2e: <root>/<kind>.stageb.jsonl + frames")
    p.add_argument("--se2e-kinds", default="RB1,RB2")
    p.add_argument("--no-labels", action="store_true", help="--data se2e: actions only (no heuristic decisions)")
    p.add_argument("--state", default="IMG", help="IMG (default, §58) | S0 | S1 (ablation)")
    p.add_argument("--no-wrist", action="store_true", help="head image only (ablation of §57)")
    p.add_argument("--dev-val-seeds", default="")
    p.add_argument("--rows", default="", help="R2 rows file per --pool folder (default <folder>.stageb.jsonl)")
    p.add_argument("--max-val", type=int, default=0, help="first N val samples (earlier smokes)")
    p.add_argument("--val-per-kind", type=int, default=0,
                   help="stratified val: N random samples of every source (RB1 / RB2), --val-seed (§69 N2)")
    p.add_argument("--val-seed", type=int, default=0)
    # prereg_se2e_temporal (OPT-IN; defaults = the S-E2E inputs)
    p.add_argument("--camera-layout", default="D27v1", choices=("D27v1", "D27v2-video2"),
                   help="D27v2-video2: every camera = 2-frame clip [t-0.3 s, t] in one temporal patch (--data se2e)")
    p.add_argument("--motion-line", default="none", choices=("none", "se2e-motion@v1"),
                   help="se2e-motion@v1: coarse arm-speed / gripper-rate line (needs --motion-bins)")
    p.add_argument("--motion-bins", default="", help="bins json (tools/se2e_temporal.py bins, train split)")
    p.add_argument("--se2e-t-root", default="/data/harvest/data/se2e_t/conv",
                   help="augmented S-E2E rows (past frames, causal motion); current frames stay under --se2e-root")
    # prereg_ma1b (OPT-IN, training-only aux target; default = no extra aux outputs)
    p.add_argument("--aux-extra", default="none", choices=AUX_CHOICES,
                   help="a3d@v1: future end-effector displacements (base frame) as an extra aux regression target")
    p.add_argument("--a3d-root", default="/data/harvest/data/ma1b/conv", help="<root>/<kind>.a3d.jsonl targets")


if __name__ == "__main__":
    main()
