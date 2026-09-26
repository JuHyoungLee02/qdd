"""Shard-level LoRA merge for Qwen3.5-35B-A3B (E-TEACH-35B; venv_train, CPU only, no model load).

python -m harvest.teach_35b.merge --adapter <run>/epoch2 --out <dir> [--model /data/harvest/models/Qwen3.5-35B-A3B]

Why not PeftModel.merge_and_unload + save_pretrained (the L8 path): the HF model does not load the checkpoint's
MTP head (mtp.*), so a re-save drops it, re-shards, and the base shard index must not be copied (P123). Here the
base shard layout is kept: every shard that holds a LoRA target is rewritten with W + (alpha / r) * B @ A (fp32 sum,
cast back to the stored dtype), every other shard and all small files (config, tokenizer, chat template, the index)
are hard-linked (copied if linking fails). The index stays valid because the shard names do not change; check_index
verifies it. MTP weights are the base ones (stale against the merged trunk: only speculative decoding acceptance
can drop)."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import time

PREFIX = "base_model.model."


def base_key(adapter_key: str):
    """PEFT adapter tensor name -> (base weight name, 'A' | 'B'); None for anything that is not a LoRA factor."""
    if not adapter_key.startswith(PREFIX):
        return None
    k = adapter_key[len(PREFIX):]
    for part in ("A", "B"):
        tail = f".lora_{part}.weight"
        if k.endswith(tail):
            return k[:-len(tail)] + ".weight", part
    return None


def _place(src: str, dst: str) -> str:
    try:
        os.link(src, dst)
        return "link"
    except OSError:
        shutil.copy2(src, dst)
        return "copy"


def check_index(out: str) -> None:
    idx = json.load(open(os.path.join(out, "model.safetensors.index.json")))
    missing = sorted({f for f in idx["weight_map"].values() if not os.path.exists(os.path.join(out, f))})
    if missing:
        raise RuntimeError(f"index names shards that do not exist: {missing[:5]}")


def merge(model: str, adapter: str, out: str) -> dict:
    import torch
    from safetensors import safe_open
    from safetensors.torch import load_file, save_file

    cfg = json.load(open(os.path.join(adapter, "adapter_config.json")))
    if cfg.get("use_dora") or cfg.get("use_rslora"):
        raise ValueError("only plain LoRA is supported (no DoRA / rsLoRA)")
    scale = cfg["lora_alpha"] / cfg["r"]
    fac = {}
    for k, v in load_file(os.path.join(adapter, "adapter_model.safetensors")).items():
        bk = base_key(k)
        if bk is None:
            raise ValueError(f"unexpected adapter tensor {k} (modules_to_save / bias are not supported)")
        fac.setdefault(bk[0], {})[bk[1]] = v
    bad = [k for k, d in fac.items() if set(d) != {"A", "B"}]
    if bad:
        raise ValueError(f"LoRA factors without a pair: {bad[:3]}")
    idx = json.load(open(os.path.join(model, "model.safetensors.index.json")))
    wm = idx["weight_map"]
    absent = [k for k in fac if k not in wm]
    if absent:
        raise ValueError(f"adapter targets not in the base checkpoint: {absent[:3]}")
    os.makedirs(out, exist_ok=True)
    by_shard = {}
    for k in fac:
        by_shard.setdefault(wm[k], []).append(k)
    rep = {"merged": 0, "shards_written": 0, "shards_linked": 0, "files_placed": 0, "scale": scale}
    for fn in sorted(os.listdir(model)):
        src, dst = os.path.join(model, fn), os.path.join(out, fn)
        if os.path.isdir(src) or os.path.exists(dst):
            continue
        if fn in by_shard:
            with safe_open(src, "pt") as f:
                meta = f.metadata()
                tens = {k: f.get_tensor(k) for k in f.keys()}
            for k in by_shard[fn]:
                w = tens[k]
                d = (fac[k]["B"].float() @ fac[k]["A"].float()) * scale
                if d.shape != w.shape:
                    raise ValueError(f"shape {tuple(d.shape)} != {tuple(w.shape)} for {k}")
                tens[k] = (w.float() + d).to(w.dtype).contiguous()
                rep["merged"] += 1
            save_file(tens, dst, metadata=meta)
            shutil.copymode(src, dst)  # save_file writes 0600; keep the base file's mode
            rep["shards_written"] += 1
        else:
            _place(src, dst)
            rep["shards_linked" if fn.endswith(".safetensors") else "files_placed"] += 1
    check_index(out)
    if rep["merged"] != len(fac):
        raise RuntimeError(f"merged {rep['merged']} of {len(fac)} targets")
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="/data/harvest/models/Qwen3.5-35B-A3B")
    a = ap.parse_args(argv)
    t0 = time.time()
    rep = merge(a.model, a.adapter, a.out)
    rep.update(adapter=a.adapter, out=a.out, s=round(time.time() - t0, 1))
    print("MERGED " + json.dumps(rep), flush=True)


if __name__ == "__main__":
    main()
