"""Merge a stage-A LoRA adapter into the base Qwen3-VL-4B weights -> a plain model directory vLLM can serve.

usage (pod, venv_train):
  python tools/stagea_merge.py --adapter /data/harvest/ckpt/stageA/<run>/best --out /data/harvest/ckpt/stageA/<run>/merged
Writes safetensors in --dtype (default bfloat16) plus the base's processor / tokenizer / chat-template files
unchanged (the prompt must render exactly as for the base), and merge_info.json (adapter sha, base, versions).
The merge is done in float32 (W + BA rounded once to --dtype). --check: reload the merged model and compare its
logits with the float32 base+adapter on one random token sequence; the same comparison for the base alone
(--dtype base vs float32 base) is reported as the rounding noise floor.
Serve: vllm serve <out> --served-model-name <name> (same flags as the base, then redo the latency / determinism
re-check of canon §50 / D26 §1.4 on the merged model).
"""
import argparse
import hashlib
import json
import os
import shutil
import time

BASE = "/data/harvest/models/Qwen3-VL-4B-Instruct"
COPY = ("chat_template.json", "chat_template.jinja", "preprocessor_config.json", "video_preprocessor_config.json",
        "tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt", "special_tokens_map.json",
        "added_tokens.json", "generation_config.json", "processor_config.json")


def sha_dir(d):
    h = hashlib.sha256()
    for f in sorted(os.listdir(d)):
        p = os.path.join(d, f)
        if os.path.isfile(p):
            h.update(f.encode())
            h.update(open(p, "rb").read())
    return h.hexdigest()[:16]


def merge(adapter, out, base=BASE, dtype="bfloat16", check=False):
    import peft
    import torch
    import transformers
    from peft import PeftModel
    from transformers import AutoModelForImageTextToText
    dt = getattr(torch, dtype)
    model = AutoModelForImageTextToText.from_pretrained(base, dtype=torch.float32)
    model = PeftModel.from_pretrained(model, adapter)
    ref = None
    if check:
        torch.manual_seed(0)
        ids = torch.randint(0, min(1000, model.config.text_config.vocab_size), (1, 16))
        with torch.no_grad():
            ref = model(input_ids=ids).logits.float()
    merged = model.merge_and_unload().to(dt)
    os.makedirs(out, exist_ok=True)
    merged.save_pretrained(out, safe_serialization=True)
    for f in COPY:
        if os.path.exists(os.path.join(base, f)):
            shutil.copy2(os.path.join(base, f), os.path.join(out, f))
    info = {"base": base, "adapter": os.path.abspath(adapter), "adapter_sha": sha_dir(adapter), "dtype": dtype,
            "versions": {"torch": torch.__version__, "transformers": transformers.__version__,
                         "peft": peft.__version__}, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if check:
        m2 = AutoModelForImageTextToText.from_pretrained(out, dtype=dt)
        with torch.no_grad():
            got = m2(input_ids=ids).logits.float()
        info["check_max_abs_logit_diff"] = float((got - ref).abs().max())
        info["check_argmax_equal"] = bool((got.argmax(-1) == ref.argmax(-1)).all())
        if dt != torch.float32:
            del m2
            b32 = AutoModelForImageTextToText.from_pretrained(base, dtype=torch.float32)
            bdt = AutoModelForImageTextToText.from_pretrained(base, dtype=dt)
            with torch.no_grad():
                info["noise_floor_max_abs_logit_diff"] = float(
                    (bdt(input_ids=ids).logits.float() - b32(input_ids=ids).logits.float()).abs().max())
    json.dump(info, open(os.path.join(out, "merge_info.json"), "w"), indent=1)
    print("MERGED " + json.dumps(info), flush=True)
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--dtype", default="bfloat16")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    merge(a.adapter, a.out, a.base, a.dtype, a.check)


if __name__ == "__main__":
    main()
