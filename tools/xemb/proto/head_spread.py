"""Head / lift joint spread over a LeRobot dataset's state (does the head move?). usage: head_spread.py RAW_ROOT [N_EPS]"""
import json, os, sys
import numpy as np
import pyarrow.parquet as pq

raw = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 200
info = json.load(open(os.path.join(raw, "meta", "info.json")))
names = info["features"]["observation.state"]["names"]
cols = [i for i, x in enumerate(names) if x.startswith(("head", "lift"))]
eps = [json.loads(x) for x in open(os.path.join(raw, "meta", "episodes.jsonl"))][:n]
within, means = [], []
for e in eps:
    ep = int(e["episode_index"])
    st = np.asarray(pq.read_table(os.path.join(raw, info["data_path"].format(
        episode_chunk=ep // info["chunks_size"], episode_index=ep))).column("observation.state").to_pylist(), float)
    h = st[:, cols]
    within.append(h.max(0) - h.min(0))
    means.append(h.mean(0))
within, means = np.array(within), np.array(means)
for j, c in enumerate(cols):
    print(names[c], "within-episode range deg p50/p90/max", np.degrees(np.percentile(within[:, j], [50, 90, 100])).round(2),
          "episode means deg p5/p50/p95", np.degrees(np.percentile(means[:, j], [5, 50, 95])).round(2))
