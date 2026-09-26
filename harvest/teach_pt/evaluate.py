"""E-PT offline evaluation (prereg_pt.md §4): send an arm's DEV / OOD samples to a vLLM server with the runtime client
(astra_motion.models.LocalVLM: greedy, same content layout), save the replies, score them (metrics.py).
python -m harvest.teach_pt.evaluate --data dev_pt.jsonl --arm pt --url http://127.0.0.1:8394 --name pt_zs
--out <dir> [--workers 8] [--kinds control,aux] [--coords n1000|px]
--coords px (pt only): the request is rewritten to integer pixel coordinates (pt_prompts.px_variant) and the reply's
point is scaled back to 0-1000 before scoring (a wording check). Replies cached in <out>/replies.jsonl (resume);
<out>/summary.json: all, first call, on-path, recovery, by step, aux; <out>/scores.jsonl per sample."""
from __future__ import annotations

import argparse
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from . import metrics as M

W, H = 672, 376


def _images(row):
    from ..teach_l8.dataset import IMAGE_LABELS
    return [(IMAGE_LABELS[i], open(p, "rb").read()) for i, p in enumerate(row["images"])]


def _text(row, coords):
    if row["kind"] == "aux":
        t = row["prompt"]
        if coords == "px":
            t = t.replace("on a 0-1000 scale of image 1 (x from the left edge, y from the top edge)",
                          f"in integer pixel coordinates of image 1 ({W}x{H} px; x from the left edge, y from the top)")
        return t
    t = open(row["prompt_path"], encoding="utf-8").read()
    if coords == "px":
        from ..astra_solo.pt_prompts import px_variant
        t = px_variant(t, W, H)
    return t


def rescale(reply: str, coords: str) -> str:
    """px replies -> the 0-1000 scale (only the point_2d field is touched)."""
    if coords != "px" or not reply:
        return reply
    from ..astra_motion.schema import SchemaError, extract_json
    try:
        d = extract_json(reply)
    except SchemaError:
        return reply
    c = d.get("command") if isinstance(d.get("command"), dict) else d
    p = c.get("point_2d") if isinstance(c, dict) else None
    if isinstance(p, list) and len(p) == 2 and all(isinstance(v, (int, float)) for v in p):
        c["point_2d"] = [min(max(p[0] / W * 1000, 0), 1000), min(max(p[1] / H * 1000, 0), 1000)]
        return json.dumps(d)
    return reply


def summarize(rows: list, replies: dict, arm: str, coords: str, out_dir: str | None = None) -> dict:
    ctrl = [r for r in rows if r["kind"] == "control" and r["id"] in replies]
    sc = []
    for r in ctrl:
        s = M.score(r, rescale(replies[r["id"]]["text"], coords), arm)
        s.update(id=r["id"], episode=r["episode"], step=r["step"], prev_kind=r["prev_kind"], call=r["call"])
        sc.append(s)
    if out_dir:
        with open(os.path.join(out_dir, "scores.jsonl"), "w") as f:
            for s in sc:
                f.write(json.dumps(s) + "\n")
    out = {"control_all": M.summarize(sc),
           "control_first_call": M.summarize([s for s in sc if s["call"] == 0]),
           "control_on_path": M.summarize([s for s in sc if s["prev_kind"] in ("start", "clean")]),
           "control_recovery": M.summarize([s for s in sc if s["prev_kind"] not in ("start", "clean")]),
           "by_step": {k: M.summarize([s for s in sc if s["step"] == k]) for k in sorted({s["step"] for s in sc})}}
    lat = [replies[r["id"]]["latency_s"] for r in ctrl if replies[r["id"]].get("latency_s") is not None]
    out["latency_s_p50"] = round(float(np.median(lat)), 3) if lat else None
    aux = [r for r in rows if r["kind"] == "aux" and r["id"] in replies]
    ak = {}
    for r in aux:
        ak.setdefault(r["aux_kind"], []).append(M.aux_score(r, rescale(replies[r["id"]]["text"], coords)))
    out["aux"] = {k: {"n": len(v), "valid_rate": round(sum(x is not None for x in v) / len(v), 4),
                      "err_median": round(float(np.median([x for x in v if x is not None])), 1)
                      if any(x is not None for x in v) else None} for k, v in sorted(ak.items())}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--arm", required=True, choices=["xyz", "pt", "nd-xyz", "nd-est", "nd-pt"])
    ap.add_argument("--url", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--kinds", default="control,aux")
    ap.add_argument("--coords", default="n1000", choices=["n1000", "px"])
    ap.add_argument("--max-tokens", type=int, default=2000)
    a = ap.parse_args(argv)
    from ..astra_motion.models import LocalVLM
    kinds = set(a.kinds.split(","))
    rows, seen = [], set()
    for x in open(a.data):
        r = json.loads(x)
        if r["kind"] in kinds and r["id"] not in seen:
            seen.add(r["id"])
            rows.append(r)
    os.makedirs(a.out, exist_ok=True)
    rp = os.path.join(a.out, "replies.jsonl")
    replies = {}
    if os.path.exists(rp):
        for x in open(rp):
            d = json.loads(x)
            replies[d["id"]] = d
    todo = [r for r in rows if r["id"] not in replies]
    vlm = LocalVLM(a.url, a.name, a.name, max_tokens=a.max_tokens)
    lock = threading.Lock()
    f = open(rp, "a")

    def one(r):
        rep = vlm.ask(_text(r, a.coords), _images(r), {})
        d = {"id": r["id"], "text": rep.text, "error": rep.error, "latency_s": round(rep.latency_s, 3),
             "usage": rep.usage}
        with lock:
            f.write(json.dumps(d) + "\n")
            f.flush()
            replies[r["id"]] = d

    with ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(one, todo))
    f.close()
    s = summarize(rows, replies, a.arm, a.coords, a.out)
    s.update(name=a.name, data=a.data, arm=a.arm, coords=a.coords, n_rows=len(rows))
    json.dump(s, open(os.path.join(a.out, "summary.json"), "w"), indent=1)
    print("EVAL_DONE " + json.dumps({"control_all": s["control_all"], "aux": s["aux"]}), flush=True)


if __name__ == "__main__":
    main()
