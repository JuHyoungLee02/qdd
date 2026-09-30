"""E-VB1 re-collected episodes -> LeRobot v3 (docs/stage3/prereg_vb1.md change 1; GARO lerobot venv, CPU).
  convert.py shard <k> <K> [--limit N]  -> <root>/lerobot/vb1_s<k>: every K-th training episode starting at k
  convert.py merge <K>                  -> <root>/lerobot/vb1_l8s_train (lerobot aggregate_datasets of the shards)
  convert.py smoke                      -> <root>/lerobot/vb1_smoke from the smoke group g0000 (pipeline check only)
  convert.py stats [dataset id]         -> exact float64 stats of vb1_l8s_train (state + delta action, chunk 50,
                                           arm joints relative, gripper absolute); lerobot's own stats kept in
                                           meta/stats_lerobot_backup.json
Training episodes: rec.json success, not in the selection split (sel), vla/vla.npz present. 10 fps.
Features: observation.images.top (head, half resolution) and observation.images.wrist_right (right wrist) = the
pi05_base camera keys (no rename map; the left wrist is absent and filled / masked by the policy),
observation.state (11) and action (8) with the names of tools/vb1/rec.py; task = scene.json instruction."""
from __future__ import annotations

import glob
import json
import os
import sys
import time

import numpy as np

ROOT = os.environ.get("VB1_ROOT", "/data/harvest/out/vb1")
LR = os.path.join(ROOT, "lerobot")
MERGED = "vb1_l8s_train"
FPS = 10
CHUNK = 50
EXCLUDE = ["gripper", "lift", "head"]  # kept absolute (= lerobot relative_exclude_joints of the training run)


def train_episodes(smoke: bool = False) -> list:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from tools.vb1 import eps as E
    out = []
    for g in E._groups():
        if smoke and g["id"] != "g0000":
            continue
        for e in E._eps(g["id"]):
            o = E.ep_out(e)
            rp = os.path.join(o, "rec.json")
            if (e["sel"] and not smoke) or not os.path.exists(rp) or not os.path.exists(os.path.join(o, "vla", "vla.npz")):
                continue
            if json.load(open(rp)).get("success"):
                out.append(o)
    return sorted(out)


def features(names_s, names_a, hw_top, hw_wr):
    return {
        "observation.state": {"dtype": "float32", "shape": (len(names_s),), "names": list(names_s)},
        "action": {"dtype": "float32", "shape": (len(names_a),), "names": list(names_a)},
        "observation.images.top": {"dtype": "video", "shape": (*hw_top, 3), "names": ["height", "width", "channels"]},
        "observation.images.wrist_right": {"dtype": "video", "shape": (*hw_wr, 3),
                                           "names": ["height", "width", "channels"]},
    }


def shard(k: int, K: int, limit: int = 0, smoke: bool = False):
    from PIL import Image
    from lerobot.datasets.lerobot_dataset import LeRobotDataset
    eps = train_episodes(smoke)[k::K]
    if limit:
        eps = eps[:limit]
    rid = "vb1_smoke" if smoke else f"vb1_s{k}"
    root = os.path.join(LR, rid)
    done = set()
    logp = os.path.join(LR, f"{rid}.done.txt")
    if os.path.exists(root):
        if not os.path.exists(logp):
            raise SystemExit(f"{root} exists without its log; remove it")
        done = set(open(logp).read().split())
        ds = LeRobotDataset(rid, root=root)
    else:
        z = np.load(os.path.join(eps[0], "vla", "vla.npz"))
        h0 = Image.open(os.path.join(eps[0], "vla", "head", "0000.jpg"))
        w0 = Image.open(os.path.join(eps[0], "vla", "wrist", "0000.jpg"))
        ds = LeRobotDataset.create(rid, fps=FPS, root=root, use_videos=True,
                                   features=features(z["state_names"], z["action_names"], (h0.height, h0.width),
                                                     (w0.height, w0.width)))
    t0, n = time.time(), 0
    with open(logp, "a") as log:
        for o in eps:
            if o in done:
                continue
            z = np.load(os.path.join(o, "vla", "vla.npz"))
            task = json.load(open(os.path.join(o, "scene.json")))["instruction"]
            S, A = z["state"], z["action"]
            for i in range(len(S)):
                ds.add_frame({"observation.state": S[i].astype(np.float32), "action": A[i].astype(np.float32),
                              "task": task,
                              "observation.images.top": np.asarray(Image.open(
                                  os.path.join(o, "vla", "head", f"{i:04d}.jpg")).convert("RGB")),
                              "observation.images.wrist_right": np.asarray(Image.open(
                                  os.path.join(o, "vla", "wrist", f"{i:04d}.jpg")).convert("RGB"))})
            ds.save_episode()
            log.write(o + "\n")
            log.flush()
            n += 1
            if n % 50 == 0:
                print(f"shard {k}: {n}/{len(eps)} episodes, {time.time() - t0:.0f} s", flush=True)
    ds.finalize()
    print(f"SHARD_DONE {k} {n} new episodes, {time.time() - t0:.0f} s", flush=True)


def merge(K: int):
    from pathlib import Path

    from lerobot.datasets.aggregate import aggregate_datasets
    ids = [f"vb1_s{k}" for k in range(K) if os.path.exists(os.path.join(LR, f"vb1_s{k}", "meta", "info.json"))]
    if len(ids) != K:
        raise SystemExit(f"only {len(ids)}/{K} shards")
    aggregate_datasets(ids, MERGED, roots=[Path(LR) / i for i in ids], aggr_root=Path(LR) / MERGED)
    info = json.load(open(os.path.join(LR, MERGED, "meta", "info.json")))
    print(f"MERGE_DONE {info['total_episodes']} episodes {info['total_frames']} frames", flush=True)


def stats(rid: str = MERGED):
    """= /data/juhyoung_pi05/exact_relative_stats_v6.py (Task C v6, float64) for action, plus exact state stats."""
    import pandas as pd
    root = os.path.join(LR, rid)
    info = json.load(open(os.path.join(root, "meta", "info.json")))
    names = info["features"]["action"]["names"]
    files = sorted(glob.glob(os.path.join(root, "data", "*", "*.parquet")))
    df = pd.concat([pd.read_parquet(f, columns=["index", "episode_index", "action", "observation.state"])
                    for f in files]).sort_values("index")
    assert len(df) == info["total_frames"]
    A = np.stack(df["action"].values).astype(np.float64)
    S = np.stack(df["observation.state"].values).astype(np.float64)
    ep = df["episode_index"].values
    tok = [t.lower() for t in EXCLUDE]
    mask = np.array([not any(t == n.lower() or t in n.lower() for t in tok) for n in names], np.float64)
    Sm = np.zeros_like(A)
    Sm[:, :len(mask)] = S[:, :A.shape[1]] * mask  # relative dims = the first action dims (state order = action order)
    N = len(A)
    starts = np.arange(N - CHUNK + 1)
    starts = starts[ep[starts] == ep[starts + CHUNK - 1]]
    s1 = np.zeros(A.shape[1]); s2 = np.zeros(A.shape[1]); mn = np.full(A.shape[1], np.inf); mx = -mn.copy(); cnt = 0
    for k in range(CHUNK):
        R = A[starts + k] - Sm[starts]
        s1 += R.sum(0); s2 += (R * R).sum(0); mn = np.minimum(mn, R.min(0)); mx = np.maximum(mx, R.max(0)); cnt += len(R)
    mean = s1 / cnt
    std = np.sqrt(np.maximum(0.0, s2 / cnt - mean ** 2))
    sub = starts[::10]
    Rs = np.concatenate([A[sub + k] - Sm[sub] for k in range(CHUNK)], 0)
    qa = {f"q{int(q * 100):02d}": np.quantile(Rs, q, axis=0) for q in (0.01, 0.10, 0.50, 0.90, 0.99)}
    qs = {f"q{int(q * 100):02d}": np.quantile(S, q, axis=0) for q in (0.01, 0.10, 0.50, 0.90, 0.99)}
    sp = os.path.join(root, "meta", "stats.json")
    st = json.load(open(sp))
    bk = os.path.join(root, "meta", "stats_lerobot_backup.json")
    if not os.path.exists(bk):
        json.dump(st, open(bk, "w"), indent=2)
    st["action"] = {"min": mn.tolist(), "max": mx.tolist(), "mean": mean.tolist(), "std": std.tolist(),
                    "count": [int(cnt)], **{k: v.tolist() for k, v in qa.items()}}
    st["observation.state"] = {"min": S.min(0).tolist(), "max": S.max(0).tolist(), "mean": S.mean(0).tolist(),
                               "std": S.std(0).tolist(), "count": [int(N)], **{k: v.tolist() for k, v in qs.items()}}
    json.dump(st, open(sp, "w"), indent=2)
    for i, n in enumerate(names):
        print(f"  action {n:14s} {'rel' if mask[i] else 'abs'} mean {mean[i]:+.5f} std {std[i]:.3e} "
              f"min {mn[i]:+.4f} max {mx[i]:+.4f}")
    print(f"EXACT_STATS_DONE frames {N} chunks {len(starts)}", flush=True)


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "shard":
        lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 0
        shard(int(sys.argv[2]), int(sys.argv[3]), lim)
    elif c == "merge":
        merge(int(sys.argv[2]))
    elif c == "smoke":
        shard(0, 1, 0, smoke=True)
    elif c == "stats":
        stats(sys.argv[2] if len(sys.argv) > 2 else MERGED)
    elif c == "count":
        print(len(train_episodes()))
    else:
        raise SystemExit(c)
