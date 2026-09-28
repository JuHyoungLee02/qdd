"""E-OPRATIO8 G evaluation: send G rows to a vLLM server (runtime LocalVLM client, greedy), parse the point (keys
"point" / "point_2d", 0-1000), score: label rows -> pixel error in image px and hit = error <= 3 % of the image
diagonal; mask rows -> hit = mask pixel at the point is non-zero. Replies cached (resume); summary per G set.
usage: python geval.py --data g_eval.jsonl --url http://127.0.0.1:PORT --name NAME --out DIR [--workers 8]
       python geval.py --score-only --data ... --out DIR"""
import argparse
import json
import math
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor

import numpy as np


def parse_point(text):
    if not text:
        return None
    m = re.search(r'"?(?:point|point_2d)"?\s*:\s*\[\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)', text)
    if not m:
        m = re.search(r"\[\s*\(?\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)", text)
    if not m:
        return None
    x, y = float(m.group(1)), float(m.group(2))
    if max(x, y) <= 1.0:  # a 0-1 answer despite the instruction
        x, y = x * 1000, y * 1000
    return [x, y]


def score_row(r, text):
    from PIL import Image
    p = parse_point(text)
    out = {"id": r["id"], "gset": r["gset"], "valid": p is not None, "hit": False, "px_err": None}
    if p is None:
        return out
    im = Image.open(r["images"][0])
    W, H = im.size
    u, v = p[0] / 1000 * W, p[1] / 1000 * H
    if r["score"] == "mask":
        m = np.asarray(Image.open(r["mask"]).convert("L"))
        iu, iv = int(min(max(u, 0), m.shape[1] - 1)), int(min(max(v, 0), m.shape[0] - 1))
        out["hit"] = bool(m[iv, iu] > 0)
    else:
        a = json.loads(r["answer"])
        t = a.get("point") or a.get("point_2d")
        if t is None:
            out["valid"] = False
            return out
        e = math.hypot(u - t[0] / 1000 * W, v - t[1] / 1000 * H)
        out["px_err"] = round(e, 1)
        out["hit"] = e <= 0.03 * math.hypot(W, H)
    return out


def summarize(sc):
    by = {}
    for s in sc:
        by.setdefault(s["gset"], []).append(s)
    res = {}
    for k, v in sorted(by.items()) + [("ALL", sc)]:
        pe = [s["px_err"] for s in v if s["px_err"] is not None]
        res[k] = {"n": len(v), "valid": round(sum(s["valid"] for s in v) / len(v), 4),
                  "hit": round(sum(s["hit"] for s in v) / len(v), 4),
                  "px_err_median": round(float(np.median(pe)), 1) if pe else None}
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--url")
    ap.add_argument("--name")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--score-only", action="store_true")
    a = ap.parse_args(argv)
    rows = [json.loads(x) for x in open(a.data, encoding="utf-8")]
    os.makedirs(a.out, exist_ok=True)
    rp = os.path.join(a.out, "replies.jsonl")
    replies = {}
    if os.path.exists(rp):
        for x in open(rp):
            d = json.loads(x)
            if not d.get("error"):
                replies[d["id"]] = d
    if not a.score_only:
        from harvest.astra_motion.models import LocalVLM
        vlm = LocalVLM(a.url, a.name, a.name, max_tokens=200)
        lock = threading.Lock()
        f = open(rp, "a")

        def one(r):
            rep = vlm.ask(r["prompt"], [("image", open(r["images"][0], "rb").read())], {})
            d = {"id": r["id"], "text": rep.text, "error": rep.error, "latency_s": round(rep.latency_s, 3)}
            with lock:
                f.write(json.dumps(d) + "\n")
                f.flush()
                if not rep.error:
                    replies[r["id"]] = d
        with ThreadPoolExecutor(a.workers) as ex:
            list(ex.map(one, [r for r in rows if r["id"] not in replies]))
        f.close()
    sc = [score_row(r, replies[r["id"]]["text"]) for r in rows if r["id"] in replies]
    with open(os.path.join(a.out, "scores.jsonl"), "w") as f:
        for s in sc:
            f.write(json.dumps(s) + "\n")
    s = summarize(sc)
    json.dump(s, open(os.path.join(a.out, "summary.json"), "w"), indent=1)
    print("GEVAL_DONE " + json.dumps(s["ALL"]))


if __name__ == "__main__":
    main()
