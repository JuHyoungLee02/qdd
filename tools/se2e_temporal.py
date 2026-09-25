"""prereg_se2e_temporal data (pod, CPU, venv with pyarrow + av + PIL = /data/harvest/venv_e3st).

  augment     rows of /data/harvest/data/se2e/conv (read only) + se2e_temporal.hist_fields -> <out>/<kind>.stageb.jsonl
              (same order, original fields byte-equal after json round trip, checked), past frames k_prev =
              max(0, k - 3) (0.3 s at 10 Hz) of the row's cameras -> <out>/img_prev/<kind>/ep<N>/k<K>_<cam>.jpg
              (same decode / RB1 wrist rotation / JPEG q90 as tools/se2e_convert.py)
  bins        motion-line bins from the TRAIN split rows the loader keeps (head + active wrist present) -> json
  transition  frame-level labels (se2e_data.episode_rows stride 1, the label rule) -> transition flags of every
              val row (se2e_temporal.transition_flags) -> json
Never writes under /data/harvest/data/se2e.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import se2e_convert as C  # noqa: E402

from harvest.train import se2e_data as S  # noqa: E402
from harvest.train import se2e_temporal as T  # noqa: E402

SRC = "/data/harvest/data/se2e/conv"
OUT = "/data/harvest/data/se2e_t/conv"
NEW_KEYS = ("k_prev", "dt_prev_s", "images_prev", "motion_src")


def _episodes(conv, kind):
    by = {}
    for x in open(S.rows_path(conv, kind), encoding="utf-8"):
        r = json.loads(x)
        by.setdefault(r["seed"], []).append(r)
    return by


def _augment_ep(args):
    from PIL import Image
    root, info, kind, ep, rows, out = args
    pq_path, vids = C._paths(root, info, ep)
    _, st, _ = C._read_pq(pq_path)
    names = info["features"]["observation.state"]["names"]
    rel = os.path.join("img_prev", kind, f"ep{ep:06d}")
    ref = lambda kp: {c: os.path.join(rel, f"k{kp:04d}_{c}.jpg") for c in C.CAMS}  # noqa: E731
    aug, need = [], {}
    for r in rows:
        h = T.hist_fields(r, st, info["fps"], names, ref)
        aug.append({**r, **h})
        for c in h["images_prev"]:
            need.setdefault(c, set()).add(h["k_prev"])
    os.makedirs(os.path.join(out, rel), exist_ok=True)
    for cam, ks in need.items():
        ims = C._decode(vids[cam], ks)
        if set(ims) != ks:
            raise RuntimeError(f"{kind} ep{ep} {cam}: frames {sorted(ks - set(ims))} not decoded")
        for k, im in ims.items():
            if cam in C.ROTATE_CW.get(kind, ()):
                im = im.transpose(Image.Transpose.ROTATE_270)
            im.save(os.path.join(out, rel, f"k{k:04d}_{cam}.jpg"), quality=C.JPEG_Q)
    return aug


def augment(a):
    os.makedirs(a.out, exist_ok=True)
    rep = {}
    for kind, name in C.DATASETS.items():
        if a.kinds and kind not in a.kinds.split(","):
            continue
        t0 = time.time()
        root = os.path.join(a.raw, name)
        info, _, _ = C._meta(root)
        by = _episodes(a.src, kind)
        order = [json.loads(x) for x in open(S.rows_path(a.src, kind), encoding="utf-8")]
        jobs = [(root, info, kind, ep, rows, a.out) for ep, rows in by.items()]
        got = {}
        with Pool(a.workers) as p:
            for rows in p.imap_unordered(_augment_ep, jobs, chunksize=2):
                for r in rows:
                    got[(r["seed"], r["k"])] = r
        n, same = 0, 0
        with open(S.rows_path(a.out, kind), "w", encoding="utf-8") as f:
            for r in order:
                x = got[(r["seed"], r["k"])]
                same += {k: v for k, v in x.items() if k not in NEW_KEYS} == r
                f.write(json.dumps(x, separators=(",", ":")) + "\n")
                n += 1
        if same != n:
            raise SystemExit(f"{kind}: {n - same} rows changed their original fields")
        rep[kind] = {"rows": n, "original_fields_equal": same, "episodes": len(by),
                     "seconds": round(time.time() - t0, 1)}
        print(kind, rep[kind], flush=True)
    json.dump(rep, open(os.path.join(a.out, "augment.json"), "w"), indent=1)


def bins(a):
    rows = []
    for kind in a.kinds.split(","):
        for x in open(S.rows_path(a.out, kind), encoding="utf-8"):
            r = json.loads(x)
            if set(S.needed_cams(r)) <= set(r.get("images") or {}):  # the rows load_se2e keeps
                rows.append(r)
    b = T.fit_motion_bins(rows)
    counts = {}
    for r in rows:
        if r["split"] == "train":
            ln = T.motion_line(r, b)
            counts[ln] = counts.get(ln, 0) + 1
    b["train_line_counts"] = dict(sorted(counts.items()))
    json.dump(b, open(a.bins_out, "w"), indent=1)
    print(json.dumps(b, indent=1))


def _labels_ep(args):
    root, info, tasks, kind, ep, urdf, keys = args
    chain = {arm: S.load_arm_chain(urdf, arm) for arm in ("left", "right")}
    pq_path, _ = C._paths(root, info, ep)
    t, st, act = C._read_pq(pq_path)
    rows = S.episode_rows(st, act, info["fps"], chain, ep, kind, "x", stride=1, labels=True,
                          names=info["features"]["observation.state"]["names"])
    lab = [r["committed"] for r in rows]
    out = {}
    for k, committed in keys:
        if lab[k] != committed:
            raise RuntimeError(f"{kind} ep{ep} k{k}: relabel {lab[k]} != row {committed}")
        anyf, per = T.transition_flags(lab, k)
        out[f"{kind}_ep{ep}_k{k}"] = {"transition": anyf, "per_q": per}
    return out


def transition(a):
    res = {}
    for kind, name in C.DATASETS.items():
        if kind not in a.kinds.split(","):
            continue
        root = os.path.join(a.raw, name)
        info, _, tasks = C._meta(root)
        by = {}
        for x in open(S.rows_path(a.out, kind), encoding="utf-8"):
            r = json.loads(x)
            if r["split"] == a.split:
                by.setdefault(r["seed"], []).append((r["k"], r["committed"]))
        jobs = [(root, info, tasks, kind, ep, a.urdf, ks) for ep, ks in by.items()]
        with Pool(a.workers) as p:
            for o in p.imap_unordered(_labels_ep, jobs, chunksize=2):
                res.update(o)
    rate = sum(v["transition"] for v in res.values()) / max(1, len(res))
    meta = {"split": a.split, "n": len(res), "transition_rate": rate, "steps": 3,
            "rule": "any question's frame-level label (se2e_heur_ee033@v1) differs between k and k+j, j in 1..3"}
    json.dump({"meta": meta, "flags": res}, open(a.trans_out, "w"))
    print(json.dumps(meta))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("augment", "bins", "transition"))
    ap.add_argument("--raw", default="/data/harvest/data/se2e/raw")
    ap.add_argument("--src", default=SRC)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--urdf", default="/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf")
    ap.add_argument("--kinds", default="RB1,RB2")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--bins-out", default="/data/harvest/data/se2e_t/motion_bins.json")
    ap.add_argument("--split", default="val")
    ap.add_argument("--trans-out", default="/data/harvest/data/se2e_t/transition_val.json")
    a = ap.parse_args()
    if os.path.abspath(a.out).startswith(os.path.abspath(SRC)):
        raise SystemExit("--out must not be under the S-E2E conversion")
    {"augment": augment, "bins": bins, "transition": transition}[a.cmd](a)


if __name__ == "__main__":
    main()
