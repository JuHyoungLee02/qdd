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


def convert(root: str, out: str, every: int = 60) -> dict:
    import cv2
    import pyarrow.parquet as pq
    os.makedirs(os.path.join(out, "frames"), exist_ok=True)
    robot = {"name": "r1pro", "source": "behavior1k/r1pro", "arm": "right",
             "desc": "Galaxea R1 Pro wheeled humanoid with two arms (BEHAVIOR-1K OmniGibson simulation)",
             "gripper": {"open_gap_m": 0.10}, "workspace": {"x": [0, 0], "y": [0, 0], "z": [0, 0]},
             "cameras": [{"name": "head camera", "W": 720, "H": 720, "K": K_HEAD.tolist(), "T_base_cam": None}]}
    recP, items, per_ep = [], [], []
    g_ee, e_c, e_b, g_obj2d, planes, tilts, base_still = [], [], [], [], [], [], []
    seg_rej = {}
    e_med, e_lat, e_ray = [], [], []
    for dp in sorted(glob.glob(os.path.join(root, "videos", "task-*", "observation.images.depth.head", "*.mp4"))):
        ep = os.path.basename(dp)[len("episode_"):-4]
        task = os.path.basename(os.path.dirname(os.path.dirname(dp)))
        meta = json.load(open(os.path.join(root, "meta", "episodes", task, f"episode_{ep}.json")))
        t = pq.read_table(os.path.join(root, "data", task, f"episode_{ep}.parquet"))
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
        idx = list(range(0, n, every))
        rgb = decode(os.path.join(root, "videos", task, "observation.images.rgb.head", f"episode_{ep}.mp4"), idx, "rgb")
        dep = decode(dp, idx, "depth")
        seg = decode(os.path.join(root, "videos", task, "observation.images.seg_instance_id.head", f"episode_{ep}.mp4"),
                     idx, "seg", ids)
        name_of = {i: (mapping.get(i, "").split("/") + [""] * 4)[3] for i in ids}
        grip_ids = [i for i in ids if "right_gripper" in mapping.get(i, "")]
        objs = {syn: nm for syn, nm in inst.items() if not syn.startswith(("agent", "floor"))}
        # grasp approach tilt (R1Pro approach axis measured below from the descent direction)
        ee = st[:, 225:228]
        closed = S.closed_from_opening((act[:, 22] + 1) / 2, close_below=0.5, open_above=0.8)
        held = closed & (st[:, 232:234].sum(1) / 0.10 > 0.1)
        segs = S.segment(ee, closed, held)
        for s in segs:
            if s["target"] is not None:
                a, b = s["t0"], s["target_t"]
                base_still.append(float(np.linalg.norm(st[b, 140:142] - st[a, 140:142])) < 0.02
                                  and abs(np.angle(np.exp(1j * (st[b, 149] - st[a, 149])))) < np.radians(2))
        for s in segs:
            if s["step"] == "descend_close":
                p, c = s["t0"], s["t1"]
                v = ee[c] - ee[p]
                R = G.quat_xyzw_to_mat(st[c, 228:232])
                tilts.append({"ep": ep, "axes_tilt_deg": [round(G.tilt_deg(sg * R[:, ax]), 1) for ax in range(3)
                                                          for sg in (1, -1)],
                              "descent_dir_tilt_deg": round(G.tilt_deg(v), 1) if np.linalg.norm(v) > 0.02 else None,
                              "descent_len_m": round(float(np.linalg.norm(v)), 3)})
        allee = ee
        for i in idx:
            if i not in rgb or i not in dep or i not in seg:
                continue
            img = os.path.join(out, "frames", f"b1k_{ep}_head_{i:05d}.jpg")
            cv2.imwrite(img, rgb[i])
            Tbc = G.pose_to_T(cr[i, :3], G.quat_xyzw_to_mat(cr[i, 3:])) @ G.FLIP_GL_CV  # cam(CV) -> base
            Ecb = G.inv_T(Tbc)  # base -> cam
            robot["cameras"][0]["T_base_cam"] = Tbc.tolist()
            Twb = G.pose_to_T(st[i, 140:143], G.yaw_mat(st[i, 149]))
            item = {"img": img, "label": f"b1k {ep} f{i}"}
            # EE point
            uv, z = G.project(K_HEAD, Ecb, ee[i])
            gm = np.isin(seg[i], grip_ids)
            if gm.sum() > 30 and z > 0 and 0 <= uv[0] < 720 and 0 <= uv[1] < 720:
                ok = Q.on_mask(uv, gm, r_px=4)
                g_ee.append(ok)
                item.update(ee=uv, mask=gm)
                if not ok:
                    item["fail"] = True
                    item["label"] += " FAIL"
                recP.append(F.qa_point(robot, "ee_point", uv, 0, img, f"b1k_{ep}_{i}_ee"))
            # objects: mask ∩ depth -> 3D centre vs GT
            for syn, nm in objs.items():
                if syn not in lay or "pos" not in lay[syn]:
                    continue
                gt_w = ti[i, lay[syn]["pos"]]
                gt_c = G.apply_T(Ecb, G.apply_T(G.inv_T(Twb), gt_w))
                m = seg[i] == -12345
                for k_, v_ in name_of.items():
                    if v_ == nm:
                        m |= seg[i] == k_
                npx = int(m.sum())
                if npx == 0:
                    continue
                pts = G.backproject(K_HEAD, dep[i], m, dmin=0.05, dmax=9.9)
                valid = len(pts) / npx
                spread = float(np.linalg.norm(np.percentile(pts, 95, 0) - np.percentile(pts, 5, 0))) if len(pts) else 9
                rej = Q.seg_sane(npx, valid, spread, max_spread_m=1.5 if "table" in syn else 0.5)
                for r in rej:
                    seg_rej[r] = seg_rej.get(r, 0) + 1
                if rej:
                    continue
                cen = pts.mean(0)
                me = cv2.erode(m.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)  # drop codec edge bleed
                pe = G.backproject(K_HEAD, dep[i], me, dmin=0.05, dmax=9.9)
                if len(pe) >= 50 and "table" not in syn:
                    med = np.median(pe, 0)
                    ray = gt_c / np.linalg.norm(gt_c)
                    dv = med - gt_c
                    e_med.append(float(np.linalg.norm(dv)))
                    e_lat.append(float(np.linalg.norm(dv - (dv @ ray) * ray)))
                    e_ray.append(float(dv @ ray))
                box = (np.percentile(pts, 2, 0) + np.percentile(pts, 98, 0)) / 2
                uvg, zg = G.project(K_HEAD, Ecb, G.apply_T(G.inv_T(Twb), gt_w))
                if "table" in syn:
                    nrm, d, inl = G.fit_plane(pts[:: max(1, len(pts) // 4000)], tol=0.01)
                    n_base = Tbc[:3, :3] @ nrm
                    planes.append({"ep": ep, "f": i, "tilt_from_up_deg": round(float(np.degrees(np.arccos(
                        abs(n_base[2])))), 2), "inliers": round(inl, 3),
                        "top_z_base_m": round(float(G.apply_T(Tbc, nrm * d)[2]), 3)})
                    if inl > 0.5:
                        sgn = 1.0 if nrm @ (Ecb[:3, :3] @ [0, 0, 1.0]) > 0 else -1.0  # normal points up (base z)
                        recP.append(F.qa_plane(robot, sgn * nrm, sgn * d, 0, img, f"b1k_{ep}_{i}_plane"))
                    continue
                e_c.append(float(np.linalg.norm(cen - gt_c)))
                e_b.append(float(np.linalg.norm(box - gt_c)))
                if zg > 0:
                    g_obj2d.append(Q.on_mask(uvg, m, r_px=3))
                c2 = np.array(np.nonzero(m)[::-1]).mean(1)
                recP.append(F.qa_point(robot, "obj_point", c2, 0, img, f"b1k_{ep}_{i}_{nm}_pt", name=nm.split("_")[0]))
                recP.append(F.qa_xyz(robot, "obj_center_cam", gt_c, 0, img, f"b1k_{ep}_{i}_{nm}_c",
                                     name=nm.split("_")[0]))
                item.update(obj=c2, obj_proj=uvg)
            items.append(item)
        per_ep.append({"ep": ep, "task": task, "frames": n, "sampled": len(idx), "steps": [s["step"] for s in segs]})
    rep = {"episodes": len(per_ep), "gate_ee_on_gripper_mask_r4": Q.rate(g_ee),
           "obj_center_err_mean_of_visible_m": Q.err_stats(e_c), "obj_center_err_bbox_of_visible_m": Q.err_stats(e_b),
           "obj_err_eroded_median_m": Q.err_stats(e_med), "obj_err_lateral_to_ray_m": Q.err_stats(e_lat),
           "obj_err_along_ray_m_signed": {"median": float(np.median(e_ray)) if e_ray else None, "n": len(e_ray)},
           "gt_center_projects_into_mask": Q.rate(g_obj2d), "seg_rejections": seg_rej, "table_planes": planes,
           "grasp_axes": tilts, "cprime_base_still_rate": Q.rate(base_still), "n_P": len(recP),
           "P_by_kind": {k: sum(r["qa_kind"] == k for r in recP) for k in sorted({r["qa_kind"] for r in recP})},
           "per_episode": per_ep}
    with open(os.path.join(out, "records_P.jsonl"), "w") as f:
        for r in recP:
            f.write(json.dumps(r) + "\n")
    with open(os.path.join(out, "gates.json"), "w") as f:
        json.dump(rep, f, indent=1, default=float)
    return rep, items
