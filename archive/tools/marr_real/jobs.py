"""E-MAR-real (docs/stage3/prereg_marr.md) step 1 (CPU, pod venv_e3st: pyarrow + PyAV): the RB2 frames the trace
labels of the se2e_c1 RB2 rows need.

A row (episode, frame k, active arm a) gets the MolmoAct trace over frames k..e, e = the arm's next release
(se2e_molmo.grip_segment_ends, require_grasp; rows after the last release get no label). So the frames to point are
the union over rows of [k, e]; both arms are pointed on every such frame (filter v2 was validated with both arms'
pointings of every frame -- its per-episode offset uses both). Per episode also: both arms' FK end effectors (URDF,
arm_base_link) and gripper values (for filter v2 and the segment ends), and the row check |FK(k + label_steps) - FK(k)
- ee_delta| (the rows and the parquet index the same frames; ee_delta is rounded to 1e-5 m).

  python tools/marr_real/jobs.py --out /data/harvest/data/marr_real [--count-only] [--workers 12]
Writes <out>/frames/RB2/ep<NNNNNN>/f<KKKK>.jpg (needed frames only, JPEG q90 as tools/marr/select_decode.py),
<out>/eps/RB2_ep<NNNNNN>.npz (ee_l, ee_r, g_l, g_r, t), <out>/episodes.json, <out>/point_jobs.jsonl, <out>/jobs_stats.json.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from harvest.train import se2e_data as S  # noqa: E402
from harvest.train import se2e_molmo as M  # noqa: E402

RAW = "/data/harvest/data/se2e/raw"
URDF = "/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf"
ROWS = "/data/harvest/data/se2e_c1/conv/RB2.stageb.jsonl"
DATASET = "Task_0002_OrderPicking_lerobot"
GRIP = {"left": "gripper_l_joint1", "right": "gripper_r_joint1"}
CHECK_M = 2e-5


def load_rows(path=ROWS) -> dict:
    by = {}
    for x in open(path, encoding="utf-8"):
        r = json.loads(x)
        by.setdefault(int(r["seed"]), []).append({"k": int(r["k"]), "arm": r["arm"], "split": r["split"],
                                                  "label_steps": int(r["label_steps"]),
                                                  "ee_delta": r["ee_delta"]})
    return by


def needed_frames(rows, ends) -> list:
    """Sorted union over rows of [k, e] (e = ends[row arm][k]); rows without a segment end add nothing."""
    need = set()
    for r in rows:
        e = ends[r["arm"]][r["k"]]
        if e is not None:
            need.update(range(r["k"], e + 1))
    return sorted(need)


def do_ep(args):
    import pyarrow.parquet as pq
    ep, rows, out, count_only = args
    root = os.path.join(RAW, DATASET)
    info = json.load(open(os.path.join(root, "meta/info.json")))
    c = ep // info["chunks_size"]
    t = pq.read_table(os.path.join(root, info["data_path"].format(episode_chunk=c, episode_index=ep))).to_pydict()
    st = np.asarray(t["observation.state"], float)
    names = info["features"]["observation.state"]["names"]
    chain = {a: S.load_arm_chain(URDF, a) for a in ("left", "right")}
    ee = {a: S.fk_ee(chain[a], st[:, S.arm_index(names, a)[:7]]) for a in ("left", "right")}
    g = {a: st[:, list(names).index(GRIP[a])] for a in ("left", "right")}
    ends = {a: M.grip_segment_ends(g[a]) for a in ("left", "right")}
    chk = max(float(np.abs(S.interp_at(ee[r["arm"]], r["k"] + r["label_steps"]) - ee[r["arm"]][r["k"]]
                           - np.asarray(r["ee_delta"])).max()) for r in rows)
    need = needed_frames(rows, ends)
    rec = {"src": "RB2", "ep": ep, "rows": len(rows), "n_state": len(st), "need": len(need),
           "rows_with_end": sum(ends[r["arm"]][r["k"]] is not None for r in rows),
           "rows_val": sum(r["split"] == "val" for r in rows), "row_check_m": chk,
           "releases": {a: len({x for x in ends[a] if x is not None}) for a in ("left", "right")},
           "split": S.split_of("RB2", ep), "frames_decoded": 0, "video_frames": None}
    if count_only or not need:
        return rec, need
    import av
    vid = os.path.join(root, info["video_path"].format(episode_chunk=c, episode_index=ep,
                                                       video_key="observation.images.cam_head"))
    d = os.path.join(out, "frames", "RB2", f"ep{ep:06d}")
    os.makedirs(d, exist_ok=True)
    want, n, last = set(need), 0, max(need)
    with av.open(vid) as cont:
        for i, f in enumerate(cont.decode(video=0)):
            if i in want:
                f.to_image().save(os.path.join(d, f"f{i:04d}.jpg"), quality=90)
                n += 1
            if i >= last:
                break
    rec["frames_decoded"] = n
    np.savez_compressed(os.path.join(out, "eps", f"RB2_ep{ep:06d}.npz"), ee_l=ee["left"], ee_r=ee["right"],
                        g_l=g["left"], g_r=g["right"], t=np.asarray(t["timestamp"], float))
    return rec, need


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--rows", default=ROWS)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--count-only", action="store_true")
    a = ap.parse_args()
    os.makedirs(os.path.join(a.out, "eps"), exist_ok=True)
    t0 = time.time()
    by = load_rows(a.rows)
    with Pool(a.workers) as p:
        res = p.map(do_ep, [(ep, by[ep], a.out, a.count_only) for ep in sorted(by)])
    recs = [r for r, _ in res]
    bad_check = [r for r in recs if r["row_check_m"] > CHECK_M]
    bad_decode = [r for r in recs if not a.count_only and r["frames_decoded"] != r["need"]]
    stats = {"episodes": len(recs), "rows": sum(r["rows"] for r in recs),
             "rows_with_end": sum(r["rows_with_end"] for r in recs), "rows_val": sum(r["rows_val"] for r in recs),
             "frames_needed": sum(r["need"] for r in recs), "calls": 2 * sum(r["need"] for r in recs),
             "frames_state": sum(r["n_state"] for r in recs), "row_check_max_m": max(r["row_check_m"] for r in recs),
             "row_check_fail": len(bad_check), "decode_mismatch": len(bad_decode), "count_only": a.count_only,
             "seconds": round(time.time() - t0, 1)}
    json.dump(stats, open(os.path.join(a.out, "jobs_stats.json"), "w"), indent=1)
    print(json.dumps(stats), flush=True)
    if bad_check:
        raise SystemExit(f"row check failed on {len(bad_check)} episodes (> {CHECK_M} m)")
    if a.count_only:
        return
    if bad_decode:
        raise SystemExit(f"decoded frame count != needed on {len(bad_decode)} episodes")
    json.dump({"source": "RB2", "rows": a.rows, "episodes": recs}, open(os.path.join(a.out, "episodes.json"), "w"),
              indent=1)
    with open(os.path.join(a.out, "point_jobs.jsonl"), "w") as f:
        for r, need in res:
            for k in need:
                for arm in ("left", "right"):
                    f.write(json.dumps({"key": f"RB2_ep{r['ep']:06d}_f{k:04d}_{arm}", "src": "RB2", "ep": r["ep"],
                                        "k": k, "arm": arm,
                                        "image": os.path.join(a.out, "frames", "RB2", f"ep{r['ep']:06d}",
                                                              f"f{k:04d}.jpg")}) + "\n")


if __name__ == "__main__":
    main()
