"""Merge an E-TEACH-L8 LoRA adapter into Qwen3-VL-8B-Instruct for vLLM serving (venv_train).
python -m harvest.teach_l8.merge --adapter <run>/epoch2 --out <dir> [--model /data/harvest/models/Qwen3-VL-8B-Instruct]"""
from __future__ import annotations

import argparse
import json
import os
import shutil


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="/data/harvest/models/Qwen3-VL-8B-Instruct")
    a = ap.parse_args(argv)
    import torch
    from peft import PeftModel
    from transformers import AutoModelForImageTextToText, AutoProcessor
    base = AutoModelForImageTextToText.from_pretrained(a.model, dtype=torch.bfloat16)
    m = PeftModel.from_pretrained(base, a.adapter).merge_and_unload()
    m.save_pretrained(a.out, safe_serialization=True)
    AutoProcessor.from_pretrained(a.model).save_pretrained(a.out)
    for fn in os.listdir(a.model):  # tokenizer / template / generation files the processor may not write
        if fn.endswith((".json", ".jinja", ".txt")) and "safetensors" not in fn \
                and not os.path.exists(os.path.join(a.out, fn)):  # never the base's shard index (stale shards)
            shutil.copy(os.path.join(a.model, fn), a.out)
    print("MERGED " + json.dumps({"adapter": a.adapter, "out": a.out}), flush=True)


if __name__ == "__main__":
    main()
