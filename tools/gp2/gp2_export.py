"""E-GP2 learning-curve checkpoints (prereg_gp2 §5 metric 4): a training state snapshot (<snap>/trainable.pt, written by
harvest.teach_l8.ckpt.save) -> a merged Qwen3-VL-8B model for vLLM, on CPU (the training card is never used).
The LoRA layout is the trainer's own (harvest.teach_l8.train LORA_TARGET, r 16, alpha 32).
usage: gp2_export.py <snap dir> <out dir> [--model /data/harvest/models/Qwen3-VL-8B-Instruct]"""
import json
import os
import shutil
import sys


def main():
    a = sys.argv[1:]
    snap, out = a[0], a[1]
    model = a[a.index("--model") + 1] if "--model" in a else "/data/harvest/models/Qwen3-VL-8B-Instruct"
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForImageTextToText, AutoProcessor
    from harvest.teach_l8.train import LORA_TARGET
    base = AutoModelForImageTextToText.from_pretrained(model, dtype=torch.bfloat16)
    m = get_peft_model(base, LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, target_modules=LORA_TARGET, bias="none"))
    sd = torch.load(os.path.join(snap, "trainable.pt"), map_location="cpu")
    res = m.load_state_dict(sd, strict=False)
    if res.unexpected_keys:
        raise SystemExit(f"unexpected keys {res.unexpected_keys[:3]}")
    names = {n for n, p in m.named_parameters() if p.requires_grad}
    if names - set(sd):
        raise SystemExit(f"trainable parameters missing in the snapshot: {sorted(names - set(sd))[:3]}")
    m = m.merge_and_unload()
    tmp = out + ".tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    m.save_pretrained(tmp, safe_serialization=True)
    AutoProcessor.from_pretrained(model).save_pretrained(tmp)
    for fn in os.listdir(model):  # same extra files as harvest.teach_l8.merge
        if fn.endswith((".json", ".jinja", ".txt")) and "safetensors" not in fn and not os.path.exists(os.path.join(tmp, fn)):
            shutil.copy(os.path.join(model, fn), tmp)
    os.rename(tmp, out)
    print("EXPORTED " + json.dumps({"snap": snap, "out": out, "tensors": len(sd)}), flush=True)


if __name__ == "__main__":
    main()
