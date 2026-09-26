"""E-SR1d strata and kinematic references from the S-E2E raw episodes (docs/stage3/prereg_sr1d.md §0.2; CPU only,
no model output). Needs pyarrow (the venv_e3st site-packages on the pod).

For every converted row (<rows>/<kind>.stageb.jsonl, se2e_c1) of both datasets:
  authority proxy of the row's active arm (harvest.train.sr1d_kin.episode_strata on the 10 fps measured gripper /
  end effector of its raw episode) + the same under the sensitivity settings (threshold 0.4 / 0.6, contact window
  2 / 4 frames) for G-a; the kinematic context of branch generation: end effector at k, event points (previous / next),
  episode floor, grasp height when closed, the other arm's end effector over k..k+H-1.
Dataset references from the TRAIN split episodes only: per-joint per-tick |delta target| p99.9 (both arms), per-tick
end-effector target speed p99.9, 0.4 s chunk displacement p99 (cap) and quantiles, workspace box per arm
(measured end effector p0.5 / p99.5).
  python tools/sr1d/strata.py --rows /data/harvest/data/se2e_c1/conv --raw /data/harvest/data/se2e/raw --out DIR
Outputs <out>/meta.jsonl (one line per row) and <out>/stats.json.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

import numpy as np  # noqa: E402

DATASETS = {"RB1": "Task_0001_CoffeeClassification_lerobot", "RB2": "Task_0002_OrderPicking_lerobot"}
URDF = "/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf"
ALT = {"thr0.4": {"thr": 0.4}, "thr0.6": {"thr": 0.6}, "win2": {"win": 2}, "win4": {"win": 4}}
H = 5


def r5(v):
    return None if v is None else round(float(v), 5)


def read_episode(root, info, ep):
    import pyarrow.parquet as pq
    c = ep // info["chunks_size"]
    t = pq.read_table(os.path.join(root, info["data_path"].format(episode_chunk=c, episode_index=ep)),
                      columns=["observation.state", "action"]).to_pydict()
    return np.asarray(t["observation.state"], float), np.asarray(t["action"], float)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", default="/data/harvest/data/se2e_c1/conv")
    ap.add_argument("--raw", default="/data/harvest/data/se2e/raw")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    from harvest.train import sr1d_kin as K
    from harvest.train.se2e_data import ARM_NAMES, fk_ee, load_arm_chain
    os.makedirs(a.out, exist_ok=True)
    chain = {arm: load_arm_chain(URDF, arm) for arm in ("left", "right")}
    t0 = time.time()
    stats = {"utc": None, "datasets": {}}
    w = open(os.path.join(a.out, "meta.jsonl.part"), "w", encoding="utf-8")
    for kind, name in DATASETS.items():
        root = os.path.join(a.raw, name)
        info = json.load(open(os.path.join(root, "meta/info.json")))
        names = info["features"]["observation.state"]["names"]
        rows = {}
        for x in open(os.path.join(a.rows, f"{kind}.stageb.jsonl"), encoding="utf-8"):
            r = json.loads(x)
            rows.setdefault(r["seed"], []).append({k: r[k] for k in ("seed", "k", "split", "arm", "bimanual",
                                                                        "committed", "images")})
        dq_all, spd_all, chunk_all, env = [], [], [], {"left": [], "right": []}
        cnt = {}
        ev_n = {"arm_eps": 0, "with_events": 0, "close": 0, "open": 0}
        for ep in sorted(rows):
            st, act = read_episode(root, info, ep)
            ix = {arm: [names.index(n) for n in ARM_NAMES[arm]] for arm in ("left", "right")}
            ee = {arm: fk_ee(chain[arm], st[:, ix[arm][:7]]) for arm in ("left", "right")}
            eea = {arm: fk_ee(chain[arm], act[:, ix[arm][:7]]) for arm in ("left", "right")}
            g = {arm: st[:, ix[arm][7]] for arm in ("left", "right")}
            floor = float(min(ee["left"][:, 2].min(), ee["right"][:, 2].min()))
            strata = {arm: K.episode_strata(g[arm], ee[arm]) for arm in ("left", "right")}
            alt = {arm: {n: K.episode_strata(g[arm], ee[arm], thr=o.get("thr", K.GRIP_CLOSED),
                                             win=o.get("win", K.CONTACT_WIN)) for n, o in ALT.items()}
                   for arm in ("left", "right")}
            events = {arm: K.gripper_events(g[arm]) for arm in ("left", "right")}
            train = rows[ep][0]["split"] == "train"
            if train:
                for arm in ("left", "right"):
                    dq_all.append(np.abs(np.diff(act[:, ix[arm][:7]], axis=0)))
                    spd_all.append(np.linalg.norm(np.diff(eea[arm], axis=0), axis=1))
                    if len(eea[arm]) > H - 1:
                        chunk_all.append(np.linalg.norm(eea[arm][H - 1:] - eea[arm][:-(H - 1)], axis=1))
                    env[arm].append(ee[arm])
                    ev_n["arm_eps"] += 1
                    ev_n["with_events"] += bool(events[arm])
                    ev_n["close"] += sum(e == "close" for _, e in events[arm])
                    ev_n["open"] += sum(e == "open" for _, e in events[arm])
            for r in rows[ep]:
                k, arm = r["k"], r["arm"]
                other = "left" if arm == "right" else "right"
                d, contact, av, sr = strata[arm][k]
                pts = K.event_points(events[arm], k)
                kk = [min(k + j, len(st) - 1) for j in range(H)]
                rec = {"key": f"{kind}_ep{ep}_k{k}", "kind": kind, "seed": ep, "k": k, "split": r["split"], "arm": arm,
                       "bimanual": r["bimanual"], "d": r5(d), "contact": contact, "a": av, "stratum": sr,
                       "alt": {n: alt[arm][n][k][3] for n in ALT},
                       "holding": bool(g[arm][k] > K.GRIP_CLOSED),
                       "ee": [r5(v) for v in ee[arm][k]], "floor_z": r5(floor),
                       "hold_z": r5(K.grasp_height(g[arm], ee[arm], k)),
                       "ev_pts": [[r5(v) for v in ee[arm][i]] for i in pts],
                       "other_ee": [[r5(v) for v in ee[other][i]] for i in kk],
                       "label_xy": (r.get("committed") or {}).get("dir_xy"),
                       "has_cams": sorted((r.get("images") or {}).keys())}
                w.write(json.dumps(rec) + "\n")
                key = f"{r['split']}/{sr}"
                cnt[key] = cnt.get(key, 0) + 1
        dq = np.concatenate(dq_all)
        spd = np.concatenate(spd_all)
        ch = np.concatenate(chunk_all)
        stats["datasets"][kind] = {
            "dq_p999": [float(np.percentile(dq[:, j], K.SPEED_Q)) for j in range(7)],
            "ee_tick_speed_p999": float(np.percentile(spd, K.SPEED_Q)),
            "chunk_cap_m": float(np.percentile(ch, K.CAP_Q)),
            "chunk_q": {str(p): float(np.percentile(ch, p)) for p in (50, 75, 90, 95, 99, 99.5)},
            "tick_speed_q": {str(p): float(np.percentile(spd, p)) for p in (50, 95, 99, 99.9)},
            "envelope": {arm: {"lo": np.percentile(np.concatenate(env[arm]), K.ENVELOPE_Q[0], axis=0).tolist(),
                               "hi": np.percentile(np.concatenate(env[arm]), K.ENVELOPE_Q[1], axis=0).tolist()}
                         for arm in ("left", "right")},
            "counts": cnt, "events_train": ev_n}
    w.close()
    os.replace(os.path.join(a.out, "meta.jsonl.part"), os.path.join(a.out, "meta.jsonl"))
    stats["utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    stats["wall_s"] = round(time.time() - t0, 1)
    json.dump(stats, open(os.path.join(a.out, "stats.json"), "w"), indent=1)
    print(json.dumps({k: v["counts"] for k, v in stats["datasets"].items()}), flush=True)


if __name__ == "__main__":
    main()
