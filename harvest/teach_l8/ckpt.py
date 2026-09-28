"""Full-state training checkpoints for the LoRA trainers (harvest.teach_l8.train, harvest.teach_35b.train).

A checkpoint is taken on an optimizer-step boundary (no gradient is accumulated at that point) and holds everything the
training loop needs to continue as if it had never stopped:
- the trainable (LoRA) parameters, exactly (torch.save of the tensors, not a re-cast);
- the optimizer state (AdamW moments and step counts);
- the loop position: optimizer step, epoch, and the index of the next micro-batch in this rank's share of the epoch
  (the micro-batch order is a pure function of --seed and the epoch, so the position alone restores the sampler);
  the LR schedule is a pure function of the step;
- the RNG states of every rank (python, numpy, torch CPU, CUDA), so dropout continues the same stream;
- the layout it was taken with (world size, micro, accum, seed, epochs, max steps): a resume with another layout would
  change the batches, so it is refused.
Layout: <out>/state/{meta.json, trainable.pt, optim.pt, rng_rank<r>.pt}; written to <out>/state.tmp and renamed, so a
crash mid-write leaves the previous checkpoint intact."""
from __future__ import annotations

import json
import os
import random
import shutil

import numpy as np

LAYOUT_KEYS = ("world", "micro", "accum", "seed", "epochs", "max_steps", "rows")


def _trainable(model) -> dict:
    return {n: p.detach().clone() for n, p in model.named_parameters() if p.requires_grad}


def rng_state() -> dict:
    import torch
    s = {"python": random.getstate(), "numpy": np.random.get_state(), "torch": torch.get_rng_state()}
    if torch.cuda.is_available():
        s["cuda"] = torch.cuda.get_rng_state_all()
    return s


def set_rng_state(s: dict) -> None:
    import torch
    random.setstate(s["python"])
    np.random.set_state(s["numpy"])
    torch.set_rng_state(s["torch"])
    if "cuda" in s and torch.cuda.is_available():
        torch.cuda.set_rng_state_all(s["cuda"])


def save(out: str, model, opt, pos: dict, layout: dict, rank: int = 0, barrier=None) -> str:
    """pos = {step, epoch, next_k}. Every rank calls it (each writes its RNG); rank 0 writes the rest and renames."""
    import torch
    tmp, fin = os.path.join(out, "state.tmp"), os.path.join(out, "state")
    if rank == 0:
        shutil.rmtree(tmp, ignore_errors=True)
        os.makedirs(tmp)
    if barrier:
        barrier()
    torch.save(rng_state(), os.path.join(tmp, f"rng_rank{rank}.pt"))
    if rank == 0:
        torch.save(_trainable(model), os.path.join(tmp, "trainable.pt"))
        torch.save(opt.state_dict(), os.path.join(tmp, "optim.pt"))
        json.dump({"pos": pos, "layout": layout}, open(os.path.join(tmp, "meta.json"), "w"), indent=1)
    if barrier:
        barrier()
    if rank == 0:
        shutil.rmtree(fin, ignore_errors=True)
        os.replace(tmp, fin)
    if barrier:
        barrier()
    return fin


def load(out: str, model, opt, layout: dict, rank: int = 0) -> dict:
    """Restore a checkpoint into the model / optimizer / RNG; returns pos. Raises if the layout differs."""
    import torch
    d = os.path.join(out, "state")
    meta = json.load(open(os.path.join(d, "meta.json")))
    diff = {k: (meta["layout"].get(k), layout.get(k)) for k in LAYOUT_KEYS if meta["layout"].get(k) != layout.get(k)}
    if diff:
        raise ValueError(f"resume refused: the checkpoint was taken with another layout {diff}")
    saved = torch.load(os.path.join(d, "trainable.pt"), map_location="cpu")
    params = dict(model.named_parameters())
    missing = [n for n in saved if n not in params]
    if missing:
        raise ValueError(f"resume refused: {len(missing)} saved parameters are not in the model, e.g. {missing[:2]}")
    with torch.no_grad():
        for n, t in saved.items():
            params[n].copy_(t.to(params[n].device, params[n].dtype))
    opt.load_state_dict(torch.load(os.path.join(d, "optim.pt"), map_location="cpu"))
    set_rng_state(torch.load(os.path.join(d, f"rng_rank{rank}.pt"), map_location="cpu", weights_only=False))
    return meta["pos"]


def exists(out: str) -> bool:
    return os.path.exists(os.path.join(out, "state", "meta.json"))
