"""Serving readiness probe (E-TEACH-35B, free): send saved astra-solo@v2 runtime requests (L8 DEV control rows) to a
vLLM server ONE AT A TIME and record latency, output tokens and the runtime score (valid JSON, action, approach xy).

python -m harvest.teach_35b.probe --data dev.jsonl --url http://127.0.0.1:8395 --name q35_fp8 --out <dir>
       [--thinking off|on] [--n 40] [--max-tokens 2000] [--warmup 2]

Body = astra_motion.models.LocalVLM (same content layout, temperature 0, seed 0) + chat_template_kwargs
{"enable_thinking": ...}; the server runs --reasoning-parser qwen3, so message.content is the answer only and the
thinking text (if any) comes back in reasoning_content (its tokens count in completion_tokens).
Rows: the first --n control rows in the order first calls (call 0) of every DEV episode, then the rest by id — so a
small n is dominated by the hardest (perception) state. Warm-up requests (the first rows again) are not timed."""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

from ..teach_l8 import metrics as M
from ..teach_l8.evaluate import _images, _text


def pick(rows: list, n: int) -> list:
    ctrl = [r for r in rows if r["kind"] == "control"]
    seen, uniq = set(), []
    for r in ctrl:
        if r["id"] not in seen:
            seen.add(r["id"])
            uniq.append(r)
    first = sorted([r for r in uniq if r["call"] == 0], key=lambda r: r["id"])
    rest = sorted([r for r in uniq if r["call"] != 0], key=lambda r: r["id"])
    return (first + rest)[:n]


def body_of(served: str, text: str, images: list, thinking: bool, max_tokens: int) -> dict:
    from ..astra_motion.models import _data_url
    content = [{"type": "text", "text": text}]
    for i, (label, png) in enumerate(images):
        content.append({"type": "text", "text": f"Image {i + 1}: {label}"})
        content.append({"type": "image_url", "image_url": {"url": _data_url(png)}})
    return {"model": served, "messages": [{"role": "user", "content": content}], "temperature": 0.0,
            "max_tokens": max_tokens, "seed": 0, "chat_template_kwargs": {"enable_thinking": thinking}}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--thinking", choices=("off", "on"), default="off")
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--max-tokens", type=int, default=2000)
    ap.add_argument("--warmup", type=int, default=2)
    a = ap.parse_args(argv)
    import httpx
    rows = pick([json.loads(x) for x in open(a.data)], a.n)
    os.makedirs(a.out, exist_ok=True)
    cli = httpx.Client(timeout=600.0)
    th = a.thinking == "on"

    def ask(r):
        t0 = time.monotonic()
        resp = cli.post(f"{a.url.rstrip('/')}/v1/chat/completions",
                        json=body_of(a.name, _text(r), _images(r), th, a.max_tokens))
        dt = time.monotonic() - t0
        if resp.status_code != 200:
            return {"id": r["id"], "error": f"http_{resp.status_code}:{resp.text[:200]}", "latency_s": dt}
        d = resp.json()
        ch = d["choices"][0]
        u = d.get("usage") or {}
        return {"id": r["id"], "latency_s": round(dt, 3), "text": ch["message"].get("content") or "",
                "reasoning_chars": len(ch["message"].get("reasoning_content") or ch["message"].get("reasoning") or ""),
                "finish": ch.get("finish_reason"), "in_tok": u.get("prompt_tokens"), "out_tok": u.get("completion_tokens")}

    for r in rows[:a.warmup]:
        ask(r)
    rec = []
    with open(os.path.join(a.out, f"replies_{a.thinking}.jsonl"), "w") as f:
        for r in rows:
            d = ask(r)
            if "error" not in d:
                s = M.score(r, d["text"])
                d.update(valid=s.get("valid"), action_ok=s.get("action_ok"), xy_mm=s.get("approach_xy_mm"), step=r["step"],
                         call=r["call"])
            f.write(json.dumps(d) + "\n")
            f.flush()
            rec.append(d)
    ok = [d for d in rec if "error" not in d]
    lat = [d["latency_s"] for d in ok]
    xy = [d["xy_mm"] for d in ok if d.get("xy_mm") is not None and d["step"] in ("above_target", "descend_close")]
    summ = {"name": a.name, "thinking": a.thinking, "n": len(rec), "errors": len(rec) - len(ok),
            "latency_p50": round(float(np.median(lat)), 3) if lat else None,
            "latency_p95": round(float(np.percentile(lat, 95)), 3) if lat else None,
            "latency_max": round(float(max(lat)), 3) if lat else None,
            "out_tok_p50": float(np.median([d["out_tok"] for d in ok])) if ok else None,
            "out_tok_max": max(d["out_tok"] for d in ok) if ok else None,
            "in_tok_p50": float(np.median([d["in_tok"] for d in ok])) if ok else None,
            "valid_json_rate": round(sum(bool(d.get("valid")) for d in ok) / len(ok), 4) if ok else None,
            "truncated": sum(d.get("finish") == "length" for d in ok),
            "action_acc": round(sum(bool(d.get("action_ok")) for d in ok) / len(ok), 4) if ok else None,
            "approach_xy_median_mm": round(float(np.median(xy)), 1) if xy else None, "approach_n": len(xy),
            "max_tokens": a.max_tokens}
    json.dump(summ, open(os.path.join(a.out, f"summary_{a.thinking}.json"), "w"), indent=1)
    print("PROBE_DONE " + json.dumps(summ), flush=True)


if __name__ == "__main__":
    main()
