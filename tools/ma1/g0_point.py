"""E-MA1 G0 reference points (prereg_ma1 §2): Molmo2-ER (allenai/Molmo2-ER, Apache-2.0, local copy with REVISION.json)
points to the active gripper in each selected head frame. Prompt = the MolmoAct form "point to the <left|right> robot
gripper" (the arm of the frame's row; robot left/right). Greedy decoding, max_new_tokens 64, bf16, one frame per
call. The answer is parsed with the model card's parser (se2e_trace.parse_point; coords scaled by 1000); no parseable
point = reference failure (recorded; no human fallback in this run).

Pod: PYTHONPATH=/data/harvest/pylib_molmo2 (transformers 4.57.1, the model card's pin) + venv_train torch,
CUDA_VISIBLE_DEVICES = a training GPU (never 0 / 1).
  python tools/ma1/g0_point.py --frames frames.jsonl --model /data/harvest/models/Molmo2-ER --out points.jsonl
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
    ap.add_argument("--frames", required=True)
    ap.add_argument("--model", default="/data/harvest/models/Molmo2-ER")
    ap.add_argument("--out", required=True)
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
    frames = [json.loads(x) for x in open(a.frames, encoding="utf-8")]
    with open(a.out, "w", encoding="utf-8") as f:
        for fr in frames:
            img = Image.open(fr["image"]).convert("RGB")
            prompt = PROMPT.format(arm=fr["arm"])
            msgs = [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image", "image": img}]}]
            x = proc.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, return_tensors="pt",
                                         return_dict=True)
            x = {k: v.to("cuda") for k, v in x.items()}
            t0 = time.time()
            with torch.inference_mode():
                y = model.generate(**x, max_new_tokens=MAX_NEW, do_sample=False)
            text = proc.tokenizer.decode(y[0, x["input_ids"].size(1):], skip_special_tokens=True)
            pt = parse_point(text, img.width, img.height)
            f.write(json.dumps({"key": fr["key"], "prompt": prompt, "text": text,
                                "point": None if pt is None else list(pt), "seconds": round(time.time() - t0, 3),
                                "model": rev["repo"], "model_sha": rev["sha"],
                                "transformers": transformers.__version__}) + "\n")
            f.flush()
    print(a.out, len(frames))


if __name__ == "__main__":
    main()
