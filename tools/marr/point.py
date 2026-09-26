"""MolmoAct real-data readiness, step 2 (GPU 0 of the main pod): Molmo2-ER gripper pointing on every head frame, both
arms, the E-MA1 G0 prompt "point to the {left|right} robot gripper" (MolmoAct's bimanual form), greedy, max 64 new
tokens, bf16. Answer parsed with se2e_trace.parse_point (model-card parser, coords / 1000); no point = None.
Batched generation (--batch, left padding); resumable (keys already in --out are skipped).

  CUDA_VISIBLE_DEVICES=0 PYTHONPATH=/data/harvest/pylib_molmo2:<code> venv_train/bin/python tools/marr/point.py \
      --jobs point_jobs.jsonl --out points.jsonl [--batch 16] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

PROMPT = "point to the {arm} robot gripper"
MAX_NEW = 64


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="/data/harvest/models/Molmo2-ER")
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    import torch
    import transformers
    from PIL import Image
    from transformers import AutoModelForImageTextToText, AutoProcessor

    from harvest.train.se2e_trace import parse_point
    rev = json.load(open(os.path.join(a.model, "REVISION.json")))
    proc = AutoProcessor.from_pretrained(a.model, trust_remote_code=True, padding_side="left")
    model = AutoModelForImageTextToText.from_pretrained(a.model, trust_remote_code=True, dtype=torch.bfloat16)
    model.to("cuda").eval()
    jobs = [json.loads(x) for x in open(a.jobs, encoding="utf-8")]
    done = set()
    if os.path.exists(a.out):
        done = {json.loads(x)["key"] for x in open(a.out, encoding="utf-8")}
    todo = [j for j in jobs if j["key"] not in done][:a.limit]
    t_all = time.time()
    with open(a.out, "a", encoding="utf-8") as f:
        for i in range(0, len(todo), a.batch):
            chunk = todo[i:i + a.batch]
            imgs = [Image.open(j["image"]).convert("RGB") for j in chunk]
            msgs = [[{"role": "user", "content": [{"type": "text", "text": PROMPT.format(arm=j["arm"])},
                                                  {"type": "image", "image": im}]}] for j, im in zip(chunk, imgs)]
            x = proc.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, return_tensors="pt",
                                         return_dict=True, padding=True)
            x = {k: v.to("cuda") if hasattr(v, "to") else v for k, v in x.items()}
            t0 = time.time()
            with torch.inference_mode():
                y = model.generate(**x, max_new_tokens=MAX_NEW, do_sample=False)
            dt = (time.time() - t0) / len(chunk)
            L = x["input_ids"].size(1)
            for j, im, row in zip(chunk, imgs, y):
                text = proc.tokenizer.decode(row[L:], skip_special_tokens=True)
                pt = parse_point(text, im.width, im.height)
                f.write(json.dumps({"key": j["key"], "src": j["src"], "ep": j["ep"], "k": j["k"], "arm": j["arm"],
                                    "text": text, "point": None if pt is None else [round(v, 2) for v in pt],
                                    "sec_per_call": round(dt, 4), "batch": len(chunk), "model_sha": rev["sha"],
                                    "transformers": transformers.__version__}) + "\n")
            f.flush()
            if (i // a.batch) % 20 == 0:
                print(json.dumps({"done": i + len(chunk), "todo": len(todo), "sec_per_call": round(dt, 4),
                                  "elapsed_s": round(time.time() - t_all, 1)}), flush=True)
    print(json.dumps({"finished": len(todo), "elapsed_s": round(time.time() - t_all, 1)}), flush=True)


if __name__ == "__main__":
    main()
