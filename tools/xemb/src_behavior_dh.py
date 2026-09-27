"""BEHAVIOR-1K 2025 demos -> D / H depth rows (xemb.dh) + the quantisation budget of the converter (user-log 156).
Depth is stored log-quantised (src_behavior.dequantize) in 10-bit video: a step of 64 q units, i.e.
  step(d) = (d + 3.5) * ln(13.5 / 3.5) / 16383 * 64  (2.37 cm at 1 m).
Per movable task object in view (mask sane, GT centre on its own mask): point = mask centroid; converter = depth at the
point -> base frame; error vs the GT object centre. Reported: converter error, the quantisation step at that depth
(analytic) and the measured gap between neighbouring depth levels on the object (empirical step), and the share of the
converter error the quantisation can explain (step / 2 along the ray vs total).
usage (pod): python -m xemb.src_behavior_dh RAW_ROOT OUT_DIR [EVERY]"""
from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np

from . import dh as DH
from . import gates as Q
from . import geom as G
from .src_behavior import (HEAD_CAM, K_HEAD, SURFACE_PREFIX, _load, decode, task_layout)

LN = np.log(13.5 / 3.5)


def qstep(d):
    return (np.asarray(d, float) + 3.5) * LN / 16383.0 * 64


def _episode(args):
    import cv2
    import pyarrow.parquet as pq
    root, out, dp, every = args
    ep = os.path.basename(dp)[len("episode_"):-4]
    task = os.path.basename(os.path.dirname(os.path.dirname(dp)))
    res = {"conv": [], "qstep": [], "gap": [], "D": [], "H": [], "skip_range": 0}
    robot = {"name": "r1pro", "source": "behavior1k/r1pro"}
    try:
        meta = json.load(open(os.path.join(root, "meta", "episodes", task, f"episode_{ep}.json")))
        t = pq.read_table(os.path.join(root, "data", task, f"episode_{ep}.parquet"))
    except Exception as ex:
        res["error"] = repr(ex)
        return res
    st = np.array(t.column("observation.state").to_pylist(), float)
    cr = np.array(t.column("observation.cam_rel_poses").to_pylist(), float)[:, 14:21]
    ti = np.array(t.column("observation.task_info").to_pylist(), float)
    cfg = _load(meta["config"])
    inst = cfg["scene"]["scene_file"]["metadata"]["task"]["inst_to_name"]
    lay = task_layout(_load(meta["task_obs_keys"]))
    mapping = {int(k): v for k, v in _load(meta["ins_id_mapping"]).items()}
    ids = _load(meta[f"{HEAD_CAM}::unique_ins_ids"])
    idx = list(range(0, len(st), every))
    vid = os.path.join(root, "videos", task, "observation.images.{}.head", f"episode_{ep}.mp4")
    rgb, dep = decode(vid.format("rgb"), idx, "rgb"), decode(dp, idx, "depth")
    seg = decode(vid.format("seg_instance_id"), idx, "seg", ids)
    name_of = {i: (mapping.get(i, "").split("/") + [""] * 4)[3] for i in ids}
    for i in idx:
        if i not in rgb or i not in dep or i not in seg:
            continue
        Tbc = G.pose_to_T(cr[i, :3], G.quat_xyzw_to_mat(cr[i, 3:])) @ G.FLIP_GL_CV
        Ecb = G.inv_T(Tbc)
        Twb = G.pose_to_T(st[i, 140:143], G.yaw_mat(st[i, 149]))
        for syn, nm in inst.items():
            if syn.startswith(("agent", "floor")) or syn.startswith(SURFACE_PREFIX) or syn not in lay:
                continue
            if "pos" not in lay[syn] or "in_gripper_right" not in lay[syn]:
                continue
            m = np.isin(seg[i], [k for k, v in name_of.items() if v == nm])
            if m.sum() < 80:
                continue
            gt_b = G.apply_T(G.inv_T(Twb), ti[i, lay[syn]["pos"]])
            uvg, zg = G.project(K_HEAD, Ecb, gt_b)
            if zg <= 0 or not Q.on_mask(uvg, m, r_px=3):
                continue
            c2 = np.array(np.nonzero(m)[::-1]).mean(1)
            if not m[int(c2[1]), int(c2[0])]:
                continue
            xb = DH.converter(K_HEAD, Tbc, dep[i], c2)
            if xb is None:
                continue
            e = float(np.linalg.norm(xb - gt_b))
            d_at = float(dep[i][int(c2[1]), int(c2[0])])
            res["conv"].append(e)
            res["qstep"].append(float(qstep(d_at)))
            lv = np.unique(np.round(dep[i][m], 5))
            lv = lv[(lv > d_at - 0.3) & (lv < d_at + 0.3)]
            if len(lv) > 3:
                res["gap"].append(float(np.median(np.diff(lv))))
            if not (DH.D_LO <= d_at <= DH.D_HI):
                res["skip_range"] += 1
                continue
            if e > DH.CONV_TOL_M:
                continue
            rid = f"b1kdh_{ep}_{i}_{nm}"
            pi, pd = (os.path.join(out, "frames", f"{rid}_{k}") for k in ("rgb.jpg", "depth.png"))
            cv2.imwrite(pi, rgb[i])
            cv2.imwrite(pd, DH.encode_depth(dep[i]))
            nice = nm.rsplit("_", 1)[0].replace("_", " ")
            d, h = DH.rows(robot, 720, 720, K_HEAD, Tbc, c2, gt_b, nice, [pi, pd], rid)
            d["conv_err_m"] = h["conv_err_m"] = round(e, 4)
            res["D"].append(d)
            res["H"].append(h)
    return res


def convert(root, out, every=60, workers=24):
    from multiprocessing import Pool
    os.makedirs(os.path.join(out, "frames"), exist_ok=True)
    dps = sorted(glob.glob(os.path.join(root, "videos", "task-*", "observation.images.depth.head", "*.mp4")))
    with Pool(workers) as p:
        rs = p.map(_episode, [(root, out, dp, every) for dp in dps])
    agg = {k: sum((r.get(k, []) for r in rs), []) for k in ("conv", "qstep", "gap", "D", "H")}
    for k, name in (("D", "records_D.jsonl"), ("H", "records_H.jsonl")):
        with open(os.path.join(out, name), "w") as f:
            for r in agg[k]:
                f.write(json.dumps(r) + "\n")
    c, qs, gp = np.array(agg["conv"]), np.array(agg["qstep"]), np.array(agg["gap"])
    pct = lambda a: {"median": round(float(np.median(a)) * 100, 2), "p90": round(float(np.percentile(a, 90)) * 100, 2)} \
        if len(a) else None
    rep = {"episodes": len(dps), "errors": [r["error"] for r in rs if "error" in r][:5], "objects": int(len(c)),
           "converter_err_cm": pct(c), "converter_le5cm": round(float((c <= DH.CONV_TOL_M).mean()), 3) if len(c) else None,
           "quant_step_cm_at_point": pct(qs), "quant_half_step_over_conv_err_median": round(float(np.median(qs / 2 / np.maximum(c, 1e-6))), 3) if len(c) else None,
           "measured_level_gap_cm": pct(gp), "skip_depth_out_of_0.25-1.60": sum(r.get("skip_range", 0) for r in rs),
           "rows_D": len(agg["D"]), "rows_H": len(agg["H"])}
    json.dump(rep, open(os.path.join(out, "report.json"), "w"), indent=1)
    return rep


if __name__ == "__main__":
    print(json.dumps(convert(sys.argv[1], sys.argv[2], *(int(a) for a in sys.argv[3:4])), indent=1))
