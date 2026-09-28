"""E-OPRATIO8 builds (prereg_opratio.md): the guarded open-point pool, the four training files (additive open share),
and the G evaluation rows. usage:
  python opratio_build.py pool   <out dir>
  python opratio_build.py train  <out dir> <base d-min jsonl>      -> train_p{0,25,50,75}.jsonl (+ counts)
  python opratio_build.py geval  <out dir> <gbench dir>            -> g_eval.jsonl (+ counts)"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from xemb import gsplit as GS  # noqa: E402

X = "/data/harvest/out/xemb_proto/points"
SOURCES = ("behavior", "molmobot_franka", "molmobot_rby1", "rb2", "rb3", "maniskill")
PACKS = ("/data/harvest/out/xemb/dh_pack/dh_D.jsonl", "/data/harvest/out/xemb/dist8_packs/obj_pixel.jsonl",
         "/data/harvest/out/xemb/dist8_packs/t1t4_pixel.jsonl")
G_SOURCES = ("behavior", "molmobot_franka", "molmobot_rby1", "rb2")
RATIOS = (0, 25, 50, 75)
ANS = '\nAnswer JSON only: {"point": [x, y]} with x, y on a 0-1000 scale of image 1 (x from the left edge, y from the top edge).'


def _rows(p):
    return [json.loads(x) for x in open(p, encoding="utf-8")] if os.path.exists(p) else []


def pool(out):
    rows, seen, counts = [], set(), {}
    for s in SOURCES:
        rs = _rows(os.path.join(X, s, "records_verified.jsonl"))
        counts[s] = len(rs)
        rows += rs
    for p in PACKS:
        rs = _rows(p)
        counts[os.path.basename(p)] = len(rs)
        rows += rs
    uniq = []
    for r in rows:
        if r["id"] not in seen:
            seen.add(r["id"])
            uniq.append(dict(r, kind="aux", aux_kind="open_" + r.get("qa_kind", "qa")))
    GS.guard(uniq, "opratio pool")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "pool.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for r in uniq:
            f.write(json.dumps(r) + "\n")
    counts.update(pool_unique=len(uniq), g_rows=0)
    json.dump(counts, open(os.path.join(out, "pool.counts.json"), "w"), indent=1)
    print(json.dumps(counts))


def train(out, base_p):
    base = open(base_p, encoding="utf-8").read().splitlines()
    pool_rows = open(os.path.join(out, "pool.jsonl"), encoding="utf-8").read().splitlines()
    counts = {}
    for p in RATIOS:
        rng = np.random.default_rng(8)
        need = int(round(len(base) * p / 100))
        idx = np.concatenate([rng.permutation(len(pool_rows)) for _ in range(need // len(pool_rows) + 1)])[:need]
        rows = base + [pool_rows[int(i)] for i in idx]
        order = np.random.default_rng([8, p]).permutation(len(rows))
        with open(os.path.join(out, f"train_p{p}.jsonl"), "w", encoding="utf-8", newline="\n") as f:
            for i in order:
                f.write(rows[int(i)] + "\n")
        counts[f"p{p}"] = {"base": len(base), "open": need, "total": len(rows), "steps": int(round(1632 * (1 + p / 100))),
                           "pool_repeat": round(need / max(len(pool_rows), 1), 3)}
    json.dump(counts, open(os.path.join(out, "train.counts.json"), "w"), indent=1)
    print(json.dumps(counts))


def geval(out, gb):
    rows, counts = [], {}
    for s in G_SOURCES:
        rs = [r for r in _rows(os.path.join(X, s, "records_G.jsonl")) if r.get("answer") and r.get("images")]
        rng = np.random.default_rng(0)
        take = [rs[int(i)] for i in rng.permutation(len(rs))[:300]]
        for r in take:
            q = r["prompt"].split("\nAnswer in 0-1000")[0].split("\nReturn JSON only.")[0]
            rows.append({"id": "g_" + r["id"], "kind": "gpoint", "gset": s, "prompt": q + ANS, "images": r["images"][:1],
                         "answer": r["answer"], "score": "label"})
        counts[s] = len(take)
    w = os.path.join(gb, "where2place")
    n = 0
    for x in _rows(os.path.join(w, "point_questions.jsonl")):
        q = x["text"].split(" Your answer should")[0]
        rows.append({"id": f"g_w2p_{x['question_id']}", "kind": "gpoint", "gset": "where2place",
                     "prompt": "Image 1 is a camera image.\n" + q + ANS, "images": [os.path.join(w, "images", x["image"])],
                     "mask": os.path.join(w, "masks", x["image"].rsplit(".", 1)[0] + ".png"), "score": "mask"})
        n += 1
    counts["where2place"] = n
    for sub in ("Location", "Placement", "Unseen"):
        d = os.path.join(gb, "refspatial_bench", sub)
        qs = json.load(open(os.path.join(d, "question.json"))) if os.path.exists(os.path.join(d, "question.json")) else []
        for x in qs:
            rows.append({"id": f"g_rsb_{sub}_{x['id']}", "kind": "gpoint", "gset": "refspatial_" + sub.lower(),
                         "prompt": "Image 1 is a camera image.\n" + x["prompt"] + ANS,
                         "images": [os.path.join(d, x["rgb_path"])], "mask": os.path.join(d, x["mask_path"]),
                         "score": "mask"})
        counts["refspatial_" + sub.lower()] = len(qs)
    with open(os.path.join(out, "g_eval.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    counts["total"] = len(rows)
    json.dump(counts, open(os.path.join(out, "g_eval.counts.json"), "w"), indent=1)
    print(json.dumps(counts))


if __name__ == "__main__":
    {"pool": lambda: pool(sys.argv[2]), "train": lambda: train(sys.argv[2], sys.argv[3]),
     "geval": lambda: geval(sys.argv[2], sys.argv[3])}[sys.argv[1]]()
