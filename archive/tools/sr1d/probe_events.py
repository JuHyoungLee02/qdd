"""E-SR1d design probe (before registration; data only, no model outputs): gripper signal, lift, end-effector
height, recorded chunk speed of the S-E2E raw episodes (LeRobot parquet, 10 fps). Prints one JSON summary.
  python tools/sr1d/probe_events.py --raw /data/harvest/data/se2e/raw --out probe.json [--max-eps N]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

import numpy as np  # noqa: E402

DATASETS = {"RB1": "Task_0001_CoffeeClassification_lerobot", "RB2": "Task_0002_OrderPicking_lerobot"}
URDF = "/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf"


def q(x, ps=(0, 0.5, 1, 5, 25, 50, 75, 95, 99, 99.5, 100)):
    x = np.asarray(x, float)
    return {str(p): round(float(np.percentile(x, p)), 5) for p in ps} if len(x) else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="/data/harvest/data/se2e/raw")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-eps", type=int, default=0)
    a = ap.parse_args()
    import pyarrow.parquet as pq

    from harvest.train.se2e_data import ARM_NAMES, fk_ee, load_arm_chain
    chain = {arm: load_arm_chain(URDF, arm) for arm in ("left", "right")}
    out = {}
    for kind, name in DATASETS.items():
        root = os.path.join(a.raw, name)
        info = json.load(open(os.path.join(root, "meta/info.json")))
        names = info["features"]["observation.state"]["names"]
        eps = [json.loads(x)["episode_index"] for x in open(os.path.join(root, "meta/episodes.jsonl"))]
        if a.max_eps:
            eps = eps[:a.max_eps]
        g_st, g_act, lift_rng, zs, chunk, dq, ncross = [], [], [], [], [], [], {}
        for ep in eps:
            c = ep // info["chunks_size"]
            p = os.path.join(root, info["data_path"].format(episode_chunk=c, episode_index=ep))
            t = pq.read_table(p, columns=["observation.state", "action"]).to_pydict()
            st = np.asarray(t["observation.state"], float)
            act = np.asarray(t["action"], float)
            lift = st[:, names.index("lift_joint")] if "lift_joint" in names else np.zeros(len(st))
            lift_rng.append(float(lift.max() - lift.min()))
            for arm in ("left", "right"):
                ix = [names.index(n) for n in ARM_NAMES[arm]]
                g = st[:, ix[7]]
                g_st.append(g[::5])
                g_act.append(act[::5, ix[7]])
                for th in (0.2, 0.3, 0.4, 0.5):
                    b = (g > th).astype(int)
                    ncross.setdefault(str(th), []).append(int(np.abs(np.diff(b)).sum()))
                ee = fk_ee(chain[arm], st[:, ix[:7]])
                zs.append(ee[::5, 2] + lift[::5])
                ea = fk_ee(chain[arm], act[:, ix[:7]])
                if len(ea) > 5:
                    chunk.append(np.linalg.norm(ea[4:] - ea[:-4], axis=1)[::5])
                dq.append(np.abs(np.diff(act[:, ix[:7]], axis=0))[::5])
        dq = np.concatenate(dq)
        out[kind] = {"episodes": len(eps), "names": names,
                     "grip_state": q(np.concatenate(g_st)), "grip_action": q(np.concatenate(g_act)),
                     "grip_state_hist": np.histogram(np.concatenate(g_st), bins=12, range=(-0.1, 1.3))[0].tolist(),
                     "crossings_per_arm_ep": {th: q(v, (0, 25, 50, 75, 95, 100)) for th, v in ncross.items()},
                     "lift_range_in_ep": q(lift_rng, (0, 50, 95, 100)),
                     "ee_z_base": q(np.concatenate(zs)),
                     "chunk_disp_m_0p4s": q(np.concatenate(chunk)),
                     "dq_tick_rad": {f"j{j + 1}": q(dq[:, j], (50, 99, 99.9, 100)) for j in range(7)}}
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
