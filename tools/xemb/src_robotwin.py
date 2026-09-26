"""RoboTwin 2.0 (TianxingChen/RoboTwin2.0, MIT) -> perception QA (P) + frame-explicit control (C').

Measured (lift_pot clean_50 episode 0; 8 pick-and-place tasks randomized_500 episodes 0-2, howto 4.3 / 9.3):
  observation/<cam>/extrinsic_cv = world -> camera (OpenCV) = inv(cam2world_gl @ diag(1, -1, -1, 1)); intrinsic_cv is
    for the stored JPEG size (head 320 x 240); rgb = JPEG bytes.
  endpose/{left,right}_endpose = [x, y, z, qw, qx, qy, qz] of the arm's end link in the WORLD frame; local +x is the
    approach axis; the finger-tip centre (TCP) = pos + 0.12 * R[:, 0] (RoboTwin gripper_bias 0.12, all embodiments).
  endpose/{left,right}_gripper: 1 open ... 0 closed (0.5 = the planner's half-open pre-grasp).
  No depth / point cloud / object pose stored; scene_info.json gives the object ids ({A}, {B}) per episode.
Robot base frame (C'): embodiments/<e>/config.yml robot_pose [x, y, z, qw, qx, qy, qz] = base in the world;
  aloha-agilex [0, -0.65, 0, 0.707, 0, 0, 0.707]: base x = world +y (forward), base y = world -x (left).
  p_base = R_base^T (p_world - t_base). The dual-arm robot is ONE base (like our FFW), so no per-arm mount offset is
  applied: targets of both arms are in the same body base frame, as in our own runtime.
"""
from __future__ import annotations

import glob
import json
import os
import re

import numpy as np

from . import fmt as F
from . import geom as G
from . import steps as S

ROBOT_POSE = {"aloha-agilex": [0.0, -0.65, 0.0, 0.707, 0.0, 0.0, 0.707]}  # embodiments/aloha-agilex.yml robot_pose
TIP_M = 0.12
AXIS = 0  # local +x
TOPDOWN_DEG = 30.0


def T_world_base(emb: str) -> np.ndarray:
    p = ROBOT_POSE[emb]
    return G.pose_to_T(p[:3], G.quat_wxyz_to_mat(p[3:]))


def world_to_base(p, emb: str) -> np.ndarray:
    return G.apply_T(G.inv_T(T_world_base(emb)), p)


def _obj_name(s: str) -> str:
    """'060_kitchenpot/base0' -> 'kitchenpot'"""
    s = s.split("/")[0]
    return re.sub(r"^\d+_", "", s).replace("_", " ")


def convert(root: str, out: str, every: int = 6) -> dict:
    import cv2
    import h5py
    os.makedirs(os.path.join(out, "frames"), exist_ok=True)
    recP, recC, items, per_ep, tilts, base_check = [], [], [], [], [], []
    files = sorted(glob.glob(os.path.join(root, "**", "data", "episode*.hdf5"), recursive=True))
    for fpath in files:
        d = os.path.dirname(os.path.dirname(fpath))
        split_dir = os.path.basename(d)
        emb = split_dir.split("_clean")[0].split("_randomized")[0]
        task = os.path.basename(os.path.dirname(d))
        epn = os.path.basename(fpath)[:-5]
        instr = json.load(open(os.path.join(d, "instructions", f"{epn}.json")))["seen"][0]
        info = {}
        si_path = os.path.join(d, "scene_info.json")
        if os.path.exists(si_path):
            info = json.load(open(si_path)).get(epn.replace("episode", "episode_"), {}).get("info", {})
        tgt = _obj_name(info.get("{A}", "object"))
        place = _obj_name(info["{B}"]) if "{B}" in info else "target"
        Twb = T_world_base(emb)
        Tbw = G.inv_T(Twb)
        h = h5py.File(fpath, "r")
        n = h["endpose/right_endpose"].shape[0]
        for arm in ("left", "right"):
            ep = h[f"endpose/{arm}_endpose"][:].astype(float)
            grip = h[f"endpose/{arm}_gripper"][:].astype(float)
            Rw = [G.quat_wxyz_to_mat(ep[i, 3:]) for i in range(n)]
            tip_w = np.array([ep[i, :3] + TIP_M * Rw[i][:, AXIS] for i in range(n)])
            tip_b = G.apply_T(Tbw, tip_w)
            closed = S.closed_from_opening(grip, close_below=0.3, open_above=0.45)
            segs = S.segment(tip_b, closed, None)
            dc = [s for s in segs if s["step"] == "descend_close"]
            tilt = G.tilt_deg(Rw[dc[0]["t1"]][:, AXIS]) if dc else None
            if tilt is not None:
                tilts.append(tilt)
            keep_c = tilt is not None and tilt <= TOPDOWN_DEG
            robot = {"name": emb.replace("-", "_"), "source": f"robotwin2/{emb}", "arm": arm,
                     "desc": "AgileX dual-arm (ALOHA-style) table robot, two 6-DoF arms (RoboTwin 2.0 SAPIEN simulation)",
                     "gripper": {"open_gap_m": 0.08},
                     "workspace": {k: [float(tip_b[:, j].min()), float(tip_b[:, j].max())] for j, k in enumerate("xyz")},
                     "cameras": []}
            base_check.append(float(tip_b[0, 0]))  # start pose should be in front of the base (x > 0)
            hist = []
            for i in range(0, n, every):
                K = h["observation/head_camera/intrinsic_cv"][i]
                E = G.as_4x4(h["observation/head_camera/extrinsic_cv"][i])
                img = os.path.join(out, "frames", f"rt_{task}_{split_dir}_{epn}_head_{i:04d}.jpg")
                if not os.path.exists(img):
                    cv2.imwrite(img, cv2.imdecode(np.frombuffer(h["observation/head_camera/rgb"][i], np.uint8),
                                                  cv2.IMREAD_COLOR))
                Tbc = Tbw @ G.inv_T(E)
                robot["cameras"] = [{"name": "head camera", "W": 320, "H": 240, "K": np.asarray(K).tolist(),
                                     "T_base_cam": Tbc.tolist()}]
                uv, z = G.project(K, E, tip_w[i])
                if z > 0 and 0 <= uv[0] < 320 and 0 <= uv[1] < 240:
                    recP.append(F.qa_point(robot, "ee_point", uv, 0, img, f"rt_{task}_{epn}_{arm}_{i}_ee"))
                    recP.append(F.qa_xyz(robot, "ee_approach_cam", E[:3, :3] @ Rw[i][:, AXIS], 0, img,
                                         f"rt_{task}_{epn}_{arm}_{i}_ax"))
                    ax2, _ = G.project(K, E, tip_w[i] + 0.06 * Rw[i][:, AXIS])
                    if len(items) < 60 and i % (every * 4) == 0:
                        items.append({"img": img, "ee": uv, "ax": ax2, "label": f"{task[:14]} {arm[0]} f{i}"})
            nC = 0
            for si, s in enumerate(segs):
                for k in (S.sample_frames(s, 2) if keep_c else []):
                    hi = os.path.join(out, "frames", f"rt_{task}_{split_dir}_{epn}_head_{k:04d}.jpg")
                    if not os.path.exists(hi):
                        cv2.imwrite(hi, cv2.imdecode(np.frombuffer(h["observation/head_camera/rgb"][k], np.uint8),
                                                     cv2.IMREAD_COLOR))
                    wi = os.path.join(out, "frames", f"rt_{task}_{split_dir}_{epn}_{arm}wrist_{k:04d}.jpg")
                    if not os.path.exists(wi):
                        cv2.imwrite(wi, cv2.imdecode(np.frombuffer(h[f"observation/{arm}_camera/rgb"][k], np.uint8),
                                                     cv2.IMREAD_COLOR))
                    E = G.as_4x4(h["observation/head_camera/extrinsic_cv"][k])
                    K = h["observation/head_camera/intrinsic_cv"][k]
                    robot["cameras"] = [{"name": "head camera", "W": 320, "H": 240, "K": np.asarray(K).tolist(),
                                         "T_base_cam": (Tbw @ G.inv_T(E)).tolist()},
                                        {"name": f"{arm} wrist camera", "W": 320, "H": 240,
                                         "K": np.asarray(h[f"observation/{arm}_camera/intrinsic_cv"][k]).tolist(),
                                         "T_base_cam": None}]
                    recC.append(F.control_record(robot, s, k, tip_b[k], 0.08 * grip[k], instr, tgt, place, hist,
                                                 first=(si == 0 and k == s["t0"]), images=[hi, wi],
                                                 rid=f"rt_{task}_{split_dir}_{epn}_{arm}_{k}_{s['step']}"))
                    nC += 1
                    if s["target"] is not None and len(items) < 90:
                        tuv, tz = G.project(K, E, tip_w[s["target_t"]])
                        items.append({"img": hi, "tgt": tuv if tz > 0 else None,
                                      "label": f"{task[:14]} {arm[0]} f{k} {s['step']}"})
                if s["target"] is not None:
                    t = s["target"]
                    hist.append(f"{len(hist) + 1}: eef to ({t[0]:.3f}, {t[1]:.3f}, {t[2]:.3f}), gripper "
                                f"{s['gripper']} -> done")
            per_ep.append({"ep": f"{task}/{split_dir}/{epn}/{arm}", "n": n, "steps": [s["step"] for s in segs],
                           "grasp_tilt_deg": None if tilt is None else round(tilt, 1), "c_kept": keep_c, "n_C": nC})
    for name, rr in (("records_P.jsonl", recP), ("records_C.jsonl", recC)):
        with open(os.path.join(out, name), "w") as f:
            for r in rr:
                f.write(json.dumps(r) + "\n")
    T = np.array(tilts)
    rep = {"episodes": len(files), "arms_with_grasp": int(len(T)), "n_P": len(recP), "n_C": len(recC),
           "grasp_tilt": {"le30": round(float((T <= 30).mean()), 3) if len(T) else None,
                          "median": round(float(np.median(T)), 1) if len(T) else None},
           "start_tip_base_x_min": round(min(base_check), 3) if base_check else None,
           "note": "EE-on-gripper gate is by eye on the sheets (no gripper points / segmentation stored)",
           "C_by_step": {k: sum(r["step"] == k for r in recC) for k in sorted({r["step"] for r in recC})},
           "per_episode": per_ep}
    return rep, items
