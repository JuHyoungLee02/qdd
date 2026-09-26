"""E-TEACH-L8 offline evaluation (prereg §4): send every DEV sample (control: the saved runtime request; aux: the
perception question) to a vLLM server with the runtime client (astra_motion.models.LocalVLM: greedy, same content
layout), save the replies, score them (metrics.py) and write a summary.

python -m harvest.teach_l8.evaluate --data dev.jsonl --url http://127.0.0.1:8392 --name l8_zs --out <dir>
[--workers 8] [--kinds control,aux]
Replies are cached in <out>/replies.jsonl (resume); summary in <out>/summary.json: all control samples, the
first-call subset (the untouched start state: the key perception moment), per step, per prev_kind group, aux per kind.
"""
from __future__ import annotations

import argparse
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from . import metrics as M


def _images(row):
    from .dataset import IMAGE_LABELS
    return [(IMAGE_LABELS[i], open(p, "rb").read()) for i, p in enumerate(row["images"])]


def _text(row):
    return row["prompt"] if row["kind"] == "aux" else open(row["prompt_path"], encoding="utf-8").read()


def summarize(rows: list, replies: dict) -> dict:
    ctrl = [r for r in rows if r["kind"] == "control" and r["id"] in replies]
    sc = []
    for r in ctrl:
        s = M.score(r, replies[r["id"]]["text"])
        s.update(episode=r["episode"], step=r["step"], prev_kind=r["prev_kind"], call=r["call"])
        sc.append(s)
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
        ak.setdefault(r["aux_kind"], []).append(M.aux_score(r, replies[r["id"]]["text"]))
    out["aux"] = {k: {"n": len(v), "valid_rate": round(sum(x is not None for x in v) / len(v), 4),
                      "xy_median_mm": round(float(np.median([x for x in v if x is not None])), 1)
                      if any(x is not None for x in v) else None,
                      "xy_p90_mm": round(float(np.percentile([x for x in v if x is not None], 90)), 1)
                      if any(x is not None for x in v) else None} for k, v in sorted(ak.items())}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--kinds", default="control,aux")
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
        rep = vlm.ask(_text(r), _images(r), {})
        d = {"id": r["id"], "text": rep.text, "error": rep.error, "latency_s": round(rep.latency_s, 3),
             "usage": rep.usage}
        with lock:
            f.write(json.dumps(d) + "\n")
            f.flush()
            replies[r["id"]] = d

    with ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(one, todo))
    f.close()
    s = summarize(rows, replies)
    s.update(name=a.name, data=a.data, n_rows=len(rows))
    json.dump(s, open(os.path.join(a.out, "summary.json"), "w"), indent=1)
    print("EVAL_DONE " + json.dumps({"control_all": s["control_all"], "control_first_call": s["control_first_call"],
                                     "aux": s["aux"]}), flush=True)


if __name__ == "__main__":
    main()
