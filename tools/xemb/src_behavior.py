"""BEHAVIOR-1K 2025 challenge demos (behavior-1k/2025-challenge-demos, MIT) -> perception QA (P).

Conventions (BEHAVIOR-1K v3.7.2 OmniGibson/omnigibson/learning/utils/{obs_utils,eval_utils}.py + measured, howto 4.2):
  observation.state (256) R1Pro: eef_right_pos 225:228 / eef_right_quat 228:232 (x, y, z, w) in the ROBOT BASE frame;
    gripper_right_qpos 232:234 (0.05 + 0.05 open); robot_pos 140:143 (world), robot_2d_ori 149 (yaw, world).
  observation.cam_rel_poses (21) = 3 cameras x [pos, quat xyzw], camera -> base, OpenGL camera axes; order
    left wrist, right wrist, head (head z = 1.39 m). depth_to_pcd rotates 180 deg about x to get CV axes.
  head intrinsics are a code constant: fx = fy = 306, cx = cy = 360 (720 x 720).
  depth video: HEVC yuv420p10le (info.json says yuv420p16le); gray16le decode ~ 14-bit log-quantised value q:
    d = exp(q / 16383 * (ln(13.5) - ln(3.5)) + ln(3.5)) - 3.5  (MIN 0, MAX 10 m, SHIFT 3.5); 10-bit storage means a
    step of 64 q units (~2.4 cm at 1 m).
  seg_instance_id video: RGB = generate_yuv_palette(len(ids))[index of the id in meta '<cam>::unique_ins_ids'];
    nearest palette colour -> id -> meta ins_id_mapping path '/World/scene_0/<object name>/...'.
  observation.task_info: per task object (meta task_obs_keys) real 1, pos 3 (world), ori_cos 3, ori_sin 3, then
    in_gripper_left / right 1 each for movable objects (always -1 in these episodes: unusable as a 'held' flag).
  action (23): index 22 = right gripper command (+1 open, -1 close).
"""
from __future__ import annotations

import glob
import json
import os

import numpy as np

from . import fmt as F
from . import gates as Q
from . import geom as G
from . import steps as S

K_HEAD = np.array([[306.0, 0, 360.0], [0, 306.0, 360.0], [0, 0, 1]])
HEAD_CAM = "robot_r1::robot_r1:zed_link:Camera:0"
SIZES = {"real": 1, "pos": 3, "ori_cos": 3, "ori_sin": 3, "in_gripper_left": 1, "in_gripper_right": 1}


def dequantize(q):
    lo, hi = np.log(3.5), np.log(13.5)
    return np.clip(np.exp(q.astype(float) / 16383.0 * (hi - lo) + lo) - 3.5, 0.0, 10.0)


def yuv_palette(n: int) -> np.ndarray:  # = BEHAVIOR generate_yuv_palette (v3.7.2)
    m = int(np.ceil(n ** (1 / 3)))
    Y, U, V = np.linspace(16, 235, m), np.linspace(16, 240, m), np.linspace(16, 240, m)
    pal = [[y, u, v] for y in Y for u in U for v in V][:n]
    return np.array(pal, dtype=np.uint8)


def task_layout(keys: list) -> dict:
    """task_obs_keys -> {object: {field: slice}}"""
    out, off = {}, 0
    for k in keys:
        for f, n in SIZES.items():
            if k.endswith("_" + f):
                obj = k[: -len(f) - 1]
                out.setdefault(obj, {})[f] = slice(off, off + n)
                off += n
                break
        else:
            raise ValueError(f"unknown task_obs key {k}")
    return out


def decode(path, idx, kind, ids=None):
    import av
    want, out = set(idx), {}
    c = av.open(path)
    pal = yuv_palette(len(ids)).astype(np.int32) if kind == "seg" else None
    for i, fr in enumerate(c.decode(video=0)):
        if i in want:
            if kind == "depth":
                out[i] = dequantize(fr.reformat(format="gray16le").to_ndarray())
            elif kind == "seg":
                rgb = fr.to_ndarray(format="rgb24").reshape(-1, 3).astype(np.int32)
                best = np.zeros(len(rgb), np.int64)
                bd = np.full(len(rgb), 1 << 30, np.int64)
                for j, p in enumerate(pal):
                    d = ((rgb - p) ** 2).sum(1)
                    m = d < bd
                    bd[m], best[m] = d[m], j
                out[i] = np.asarray(ids)[best].reshape(fr.height, fr.width)
            else:
                out[i] = fr.to_ndarray(format="bgr24")
            want.discard(i)
        if not want:
            break
    c.close()
    return out


def _load(v):
    return json.loads(v) if isinstance(v, str) else v



SURFACE_PREFIX = ("table", "countertop", "desk", "shelf", "counter", "coffee_table", "bench", "stool", "sink",
                  "cabinet", "dishwasher", "stove", "oven", "bed", "sofa", "chair")
TOPDOWN_DEG = 30.0


def _episode(args):
    """One episode -> P records, sheet items and gate lists (run in a worker process)."""
    import cv2
    import pyarrow.parquet as pq
    root, out, dp, every, keep_masks = args
    ep = os.path.basename(dp)[len("episode_"):-4]
    task = os.path.basename(os.path.dirname(os.path.dirname(dp)))
    res = {k: [] for k in ("recP", "items", "g_ee", "e_c", "e_med", "e_lat", "e_ray", "g_obj2d", "planes", "tilts",
                           "base_still")}
    res["seg_rej"] = {}
    robot = {"name": "r1pro", "source": "behavior1k/r1pro", "arm": "right",
             "desc": "Galaxea R1 Pro wheeled humanoid with two arms (BEHAVIOR-1K OmniGibson simulation)",
             "gripper": {"open_gap_m": 0.10}, "workspace": {"x": [0, 0], "y": [0, 0], "z": [0, 0]},
             "cameras": [{"name": "head camera", "W": 720, "H": 720, "K": K_HEAD.tolist(), "T_base_cam": None}]}
    try:
        meta = json.load(open(os.path.join(root, "meta", "episodes", task, f"episode_{ep}.json")))
        t = pq.read_table(os.path.join(root, "data", task, f"episode_{ep}.parquet"))
    except Exception as ex:
        res["error"] = f"{task}/{ep}: {ex!r}"
        return res
    st = np.array(t.column("observation.state").to_pylist(), float)
    cr = np.array(t.column("observation.cam_rel_poses").to_pylist(), float)[:, 14:21]
    ti = np.array(t.column("observation.task_info").to_pylist(), float)
    act = np.array(t.column("action").to_pylist(), float)
    cfg = _load(meta["config"])
    inst = cfg["scene"]["scene_file"]["metadata"]["task"]["inst_to_name"]
    lay = task_layout(_load(meta["task_obs_keys"]))
    mapping = {int(k): v for k, v in _load(meta["ins_id_mapping"]).items()}
    ids = _load(meta[f"{HEAD_CAM}::unique_ins_ids"])
    n = len(st)
    # grasp events of both arms (tilt of the eef local +z from straight down, base-still check)
    for a_idx, pos, quat, grip in ((14, slice(186, 189), slice(189, 193), slice(193, 195)),
                                   (22, slice(225, 228), slice(228, 232), slice(232, 234))):
        ee = st[:, pos]
        closed = S.closed_from_opening((act[:, a_idx] + 1) / 2, close_below=0.5, open_above=0.8)
        held = closed & (st[:, grip].sum(1) > 0.004)
        segs = S.segment(ee, closed, held)
        for s in segs:
            if s["step"] == "descend_close":
                R = G.quat_xyzw_to_mat(st[s["t1"], quat])
                res["tilts"].append(G.tilt_deg(R[:, 2]))
            if s["target"] is not None:
                a, b = s["t0"], s["target_t"]
                res["base_still"].append(bool(np.linalg.norm(st[b, 140:142] - st[a, 140:142]) < 0.02
                                              and abs(np.angle(np.exp(1j * (st[b, 149] - st[a, 149])))) < np.radians(2)))
    idx = list(range(0, n, every))
    rgb = decode(os.path.join(root, "videos", task, "observation.images.rgb.head", f"episode_{ep}.mp4"), idx, "rgb")
    dep = decode(dp, idx, "depth")
    seg = decode(os.path.join(root, "videos", task, "observation.images.seg_instance_id.head", f"episode_{ep}.mp4"),
                 idx, "seg", ids)
    name_of = {i: (mapping.get(i, "").split("/") + [""] * 4)[3] for i in ids}
    grip_ids = [i for i in ids if "right_gripper" in mapping.get(i, "")]
    objs = {syn: nm for syn, nm in inst.items() if not syn.startswith(("agent", "floor"))}
    ee = st[:, 225:228]
    for i in idx:
        if i not in rgb or i not in dep or i not in seg:
            continue
        img = os.path.join(out, "frames", f"b1k_{ep}_head_{i:05d}.jpg")
        cv2.imwrite(img, rgb[i])
        Tbc = G.pose_to_T(cr[i, :3], G.quat_xyzw_to_mat(cr[i, 3:])) @ G.FLIP_GL_CV  # cam(CV) -> base
        Ecb = G.inv_T(Tbc)
        robot["cameras"][0]["T_base_cam"] = Tbc.tolist()
        Twb = G.pose_to_T(st[i, 140:143], G.yaw_mat(st[i, 149]))
        item = {"img": img, "label": f"b1k {task[-4:]}/{ep[-4:]} f{i}"}
        uv, z = G.project(K_HEAD, Ecb, ee[i])
        gm = np.isin(seg[i], grip_ids)
        if gm.sum() > 30 and z > 0 and 0 <= uv[0] < 720 and 0 <= uv[1] < 720:
            ok = Q.on_mask(uv, gm, r_px=4)
            res["g_ee"].append(ok)
            item.update(ee=uv, mask=gm if keep_masks else None)
            if not ok:
                item["fail"] = True
                item["label"] += " FAIL"
            else:
                res["recP"].append(F.qa_point(robot, "ee_point", uv, 0, img, f"b1k_{ep}_{i}_ee"))
        for syn, nm in objs.items():
            if syn not in lay or "pos" not in lay[syn]:
                continue
            surface = syn.startswith(SURFACE_PREFIX)  # tables also carry in_gripper fields in task_info
            movable = "in_gripper_right" in lay[syn] and not surface

            if not movable and not surface:
                continue
            m = np.isin(seg[i], [k_ for k_, v_ in name_of.items() if v_ == nm])
            npx = int(m.sum())
            if npx == 0:
                continue
            pts = G.backproject(K_HEAD, dep[i], m, dmin=0.05, dmax=9.9)
            valid = len(pts) / npx
            spread = float(np.linalg.norm(np.percentile(pts, 95, 0) - np.percentile(pts, 5, 0))) if len(pts) else 9
            rej = Q.seg_sane(npx, valid, spread, max_spread_m=2.5 if surface else 0.5)
            for r in rej:
                res["seg_rej"][r] = res["seg_rej"].get(r, 0) + 1
            if rej:
                continue
            if surface:
                nrm, d, inl = G.fit_plane(pts[:: max(1, len(pts) // 4000)], tol=0.01)
                n_base = Tbc[:3, :3] @ nrm
                tilt_up = float(np.degrees(np.arccos(abs(n_base[2]))))
                res["planes"].append({"ep": ep, "f": i, "obj": nm, "tilt_from_up_deg": round(tilt_up, 2),
                                      "inliers": round(inl, 3)})
                if inl > 0.5 and tilt_up <= 3.0:
                    sgn = 1.0 if nrm @ (Ecb[:3, :3] @ [0, 0, 1.0]) > 0 else -1.0
                    res["recP"].append(F.qa_plane(robot, sgn * nrm, sgn * d, 0, img, f"b1k_{ep}_{i}_{nm}_plane"))
                continue
            gt_w = ti[i, lay[syn]["pos"]]
            gt_c = G.apply_T(Ecb, G.apply_T(G.inv_T(Twb), gt_w))
            res["e_c"].append(float(np.linalg.norm(pts.mean(0) - gt_c)))
            me = cv2.erode(m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
            pe = G.backproject(K_HEAD, dep[i], me, dmin=0.05, dmax=9.9)
            if len(pe) >= 50:
                dv = np.median(pe, 0) - gt_c
                ray = gt_c / np.linalg.norm(gt_c)
                res["e_med"].append(float(np.linalg.norm(dv)))
                res["e_lat"].append(float(np.linalg.norm(dv - (dv @ ray) * ray)))
                res["e_ray"].append(float(dv @ ray))
            uvg, zg = G.project(K_HEAD, Ecb, G.apply_T(G.inv_T(Twb), gt_w))
            inm = zg > 0 and Q.on_mask(uvg, m, r_px=3)
            if zg > 0:
                res["g_obj2d"].append(inm)
            c2 = np.array(np.nonzero(m)[::-1]).mean(1)
            nice = nm.rsplit("_", 1)[0].split("_")[0]
            res["recP"].append(F.qa_point(robot, "obj_point", c2, 0, img, f"b1k_{ep}_{i}_{nm}_pt", name=nice))
            if inm:  # GT centre only when it lands on its own mask (G3 as a filter)
                res["recP"].append(F.qa_xyz(robot, "obj_center_cam", gt_c, 0, img, f"b1k_{ep}_{i}_{nm}_c", name=nice))
            item.update(obj=c2, obj_proj=uvg)
        res["items"].append(item)
    res["per_ep"] = {"ep": ep, "task": task, "frames": n, "sampled": len(idx)}
    return res


def convert(root: str, out: str, every: int = 90, workers: int = 40) -> dict:
    from multiprocessing import Pool
    os.makedirs(os.path.join(out, "frames"), exist_ok=True)
    dps = sorted(glob.glob(os.path.join(root, "videos", "task-*", "observation.images.depth.head", "*.mp4")))
    args = [(root, out, dp, every, i < 12) for i, dp in enumerate(dps)]
    with Pool(workers) as pool:
        outs = pool.map(_episode, args)
    agg = {k: [] for k in ("recP", "items", "g_ee", "e_c", "e_med", "e_lat", "e_ray", "g_obj2d", "planes", "tilts",
                           "base_still")}
    seg_rej, per_ep, errors = {}, [], []
    for r in outs:
        if "error" in r:
            errors.append(r["error"])
            continue
        for k in agg:
            agg[k] += r[k]
        for k, v in r["seg_rej"].items():
            seg_rej[k] = seg_rej.get(k, 0) + v
        per_ep.append(r["per_ep"])
    T = np.array(agg["tilts"])
    pl = agg["planes"]
    rep = {"episodes": len(per_ep), "tasks": len({p["task"] for p in per_ep}), "errors": errors,
           "gate_ee_on_gripper_mask_r4": Q.rate(agg["g_ee"]),
           "obj_center_err_mean_of_visible_m": Q.err_stats(agg["e_c"]),
           "obj_err_eroded_median_m": Q.err_stats(agg["e_med"]), "obj_err_lateral_to_ray_m": Q.err_stats(agg["e_lat"]),
           "obj_err_along_ray_m_signed": {"median": float(np.median(agg["e_ray"])) if agg["e_ray"] else None,
                                          "n": len(agg["e_ray"])},
           "gt_center_projects_into_mask": Q.rate(agg["g_obj2d"]), "seg_rejections": seg_rej,
           "planes": {"n": len(pl), "pass": sum(p["inliers"] > 0.5 and p["tilt_from_up_deg"] <= 3 for p in pl),
                      "tilt_median": float(np.median([p["tilt_from_up_deg"] for p in pl])) if pl else None},
           "grasp_tilt": {"n": int(len(T)), "le20": round(float((T <= 20).mean()), 3) if len(T) else None,
                          "le30": round(float((T <= 30).mean()), 3) if len(T) else None,
                          "median": round(float(np.median(T)), 1) if len(T) else None},
           "cprime_base_still_rate": Q.rate(agg["base_still"]), "n_P": len(agg["recP"]),
           "P_by_kind": {k: sum(r["qa_kind"] == k for r in agg["recP"]) for k in sorted({r["qa_kind"] for r in agg["recP"]})},
           "per_episode": per_ep}
    with open(os.path.join(out, "records_P.jsonl"), "w") as f:
        for r in agg["recP"]:
            f.write(json.dumps(r) + "\n")
    with open(os.path.join(out, "gates.json"), "w") as f:
        json.dump(rep, f, indent=1, default=float)
    return rep, agg["items"]
