"""MolmoAct real-data readiness (plan docs/superpowers/plans/2026-09-26-molmoact-real-readiness.md), step 1 (CPU, pod
venv_e3st: pyarrow + PyAV): pick the episodes (RB1 24 + RB2 24, seed 0, RB2 ep 46 excluded), decode EVERY cam_head
frame (10 Hz, native 672x376, JPEG q90), compute both arms' FK end effector (URDF, arm_base_link) and gripper values.

  python tools/marr/select_decode.py --out /data/harvest/data/marr [--n 24] [--workers 12]
Writes <out>/frames/<src>/ep<NNNNNN>/f<KKKK>.jpg, <out>/eps/<src>_ep<NNNNNN>.npz (ee_l, ee_r, g_l, g_r, t),
<out>/episodes.json (selection + task text), <out>/point_jobs.jsonl (one line per frame x arm).
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from harvest.train import se2e_data as S  # noqa: E402

RAW = "/data/harvest/data/se2e/raw"
URDF = "/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf"
DATASETS = {"RB1": "Task_0001_CoffeeClassification_lerobot", "RB2": "Task_0002_OrderPicking_lerobot"}
EXCLUDE = {"RB2": {46}}  # video 50 frames vs 300 rows (se2e_data.md)
GRIP = {"left": "gripper_l_joint1", "right": "gripper_r_joint1"}


def meta(root):
    info = json.load(open(os.path.join(root, "meta/info.json")))
    eps = [json.loads(x) for x in open(os.path.join(root, "meta/episodes.jsonl"))]
    tasks = {json.loads(x)["task_index"]: json.loads(x)["task"] for x in open(os.path.join(root, "meta/tasks.jsonl"))}
    return info, eps, tasks


def select(n: int, seed: int = 0) -> list:
    out = []
    for src, name in DATASETS.items():
        info, eps, _ = meta(os.path.join(RAW, name))
        ids = sorted(e["episode_index"] for e in eps if e["episode_index"] not in EXCLUDE.get(src, ()))
        pick = sorted(random.Random(seed).sample(ids, n))
        out += [(src, ep) for ep in pick]
    return out


def do_ep(args):
    import av
    import pyarrow.parquet as pq
    src, ep, out = args
    root = os.path.join(RAW, DATASETS[src])
    info, _, tasks = meta(root)
    c = ep // info["chunks_size"]
    t = pq.read_table(os.path.join(root, info["data_path"].format(episode_chunk=c, episode_index=ep))).to_pydict()
    st = np.asarray(t["observation.state"], float)
    names = info["features"]["observation.state"]["names"]
    chain = {a: S.load_arm_chain(URDF, a) for a in ("left", "right")}
    ee = {a: S.fk_ee(chain[a], st[:, S.arm_index(names, a)[:7]]) for a in ("left", "right")}
    g = {a: st[:, list(names).index(GRIP[a])] for a in ("left", "right")}
    vid = os.path.join(root, info["video_path"].format(episode_chunk=c, episode_index=ep,
                                                       video_key="observation.images.cam_head"))
    d = os.path.join(out, "frames", src, f"ep{ep:06d}")
    os.makedirs(d, exist_ok=True)
    n = 0
    with av.open(vid) as cont:
        for i, f in enumerate(cont.decode(video=0)):
            f.to_image().save(os.path.join(d, f"f{i:04d}.jpg"), quality=90)
            n += 1
    np.savez_compressed(os.path.join(out, "eps", f"{src}_ep{ep:06d}.npz"), ee_l=ee["left"], ee_r=ee["right"],
                        g_l=g["left"], g_r=g["right"], t=np.asarray(t["timestamp"], float))
    return {"src": src, "ep": ep, "task": tasks[int(t["task_index"][0])], "rows": len(st), "frames": n,
            "split": S.split_of(src, ep)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    os.makedirs(os.path.join(a.out, "eps"), exist_ok=True)
    t0 = time.time()
    sel = select(a.n)
    with Pool(a.workers) as p:
        eps = p.map(do_ep, [(s, e, a.out) for s, e in sel])
    bad = [e for e in eps if e["frames"] != e["rows"]]
    json.dump({"selection_seed": 0, "n_per_source": a.n, "episodes": eps, "frame_row_mismatch": bad},
              open(os.path.join(a.out, "episodes.json"), "w"), indent=1)
    with open(os.path.join(a.out, "point_jobs.jsonl"), "w") as f:
        for e in eps:
            for k in range(min(e["frames"], e["rows"])):
                for arm in ("left", "right"):
                    f.write(json.dumps({"key": f"{e['src']}_ep{e['ep']:06d}_f{k:04d}_{arm}", "src": e["src"],
                                        "ep": e["ep"], "k": k, "arm": arm,
                                        "image": os.path.join(a.out, "frames", e["src"], f"ep{e['ep']:06d}",
                                                              f"f{k:04d}.jpg")}) + "\n")
    print(json.dumps({"episodes": len(eps), "frames": sum(e["frames"] for e in eps), "mismatch": len(bad),
                      "seconds": round(time.time() - t0, 1)}), flush=True)


if __name__ == "__main__":
    main()
