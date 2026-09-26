"""RoboTwin 2.0 (TianxingChen/RoboTwin2.0, MIT) -> perception QA (P) + frame-explicit control (C').

Measured on lift_pot/aloha-agilex_clean_50 episode 0 (howto 4.3):
  observation/<cam>/extrinsic_cv = world -> camera (OpenCV) = inv(cam2world_gl @ diag(1, -1, -1, 1)); intrinsic_cv is
    for the stored JPEG size (head 320 x 240); rgb = JPEG bytes.
  endpose/{left,right}_endpose = [x, y, z, qw, qx, qy, qz] of the arm's end link in the WORLD frame (x right, y away
    from the robot, z up; origin at the table centre); it sits at the wrist, not between the finger tips.
  endpose/{left,right}_gripper: 1 open ... 0 closed (0.5 = the pre-grasp half-open used by the planner).
  No depth or point cloud is stored (pointcloud empty), no object pose in the h5 (scene_info.json has the object id).
Our control frame for this robot: 'base_aloha_agilex' = the RoboTwin world rotated to x forward (= world +y), y left
(= world -x), z up, origin kept at the world origin (the robot base pose is not stored).
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

R_OURS_WORLD = np.array([[0.0, 1, 0], [-1, 0, 0], [0, 0, 1]])  # ours = R @ world
TIP_M = 0.12  # end link -> finger-tip centre along the approach axis (eye-checked on the overlay, howto 4.3)


def to_ours(p):
    return R_OURS_WORLD @ np.asarray(p, float)


def convert(root: str, out: str, every: int = 6) -> dict:
    import cv2
    import h5py
    os.makedirs(os.path.join(out, "frames"), exist_ok=True)
    robot = {"name": "aloha_agilex", "source": "robotwin2/aloha_agilex", "arm": "right",
             "desc": "AgileX dual-arm (ALOHA-style) table robot, two 6-DoF arms (RoboTwin 2.0 SAPIEN simulation)",
             "gripper": {"open_gap_m": 0.08}, "workspace": {"x": [0, 0], "y": [0, 0], "z": [0, 0]}, "cameras": []}
    recP, recC, items, g_eye, per_ep, tilts = [], [], [], [], [], []
    files = sorted(glob.glob(os.path.join(root, "*", "data", "episode*.hdf5")))
    for fpath in files:
        task = os.path.basename(os.path.dirname(os.path.dirname(fpath)))
        epn = os.path.basename(fpath)[:-5]
        instr = json.load(open(os.path.join(os.path.dirname(os.path.dirname(fpath)), "instructions",
                                            f"{epn}.json")))["seen"][0]
        h = h5py.File(fpath, "r")
        n = h["endpose/right_endpose"].shape[0]
        for arm in ("left", "right"):
            ep = h[f"endpose/{arm}_endpose"][:].astype(float)
            grip = h[f"endpose/{arm}_gripper"][:].astype(float)
            closed = S.closed_from_opening(grip, close_below=0.3, open_above=0.45)
            segs = S.segment(ep[:, :3], closed, None)
            # approach axis of the end link from the final approach direction
            dc = [s for s in segs if s["step"] == "descend_close"]
            Rs, vs = [], []
            for s in dc:
                v = ep[s["t1"], :3] - ep[s["t0"], :3]
                if np.linalg.norm(v) > 0.02:
                    Rs.append(G.quat_wxyz_to_mat(ep[s["t1"], 3:]))
                    vs.append(v)
            ax, sg, score = G.approach_axis(Rs, vs) if Rs else (0, 1, float("nan"))
            for s in dc:
                R = G.quat_wxyz_to_mat(ep[s["t1"], 3:])
                tilts.append({"ep": f"{task}/{epn}/{arm}", "axis": [ax, sg], "cos": round(score, 3),
                              "tilt_deg": round(G.tilt_deg(sg * R[:, ax]), 1)})
            tip = np.array([ep[i, :3] + TIP_M * sg * G.quat_wxyz_to_mat(ep[i, 3:])[:, ax] for i in range(n)])
            robot["arm"] = arm
            wall = np.array([to_ours(p) for p in tip])
            robot["workspace"] = {k: [float(wall[:, j].min()), float(wall[:, j].max())] for j, k in enumerate("xyz")}
            hist = []
            for i in range(0, n, every):
                K = h["observation/head_camera/intrinsic_cv"][i]
                E = h["observation/head_camera/extrinsic_cv"][i]
                img = os.path.join(out, "frames", f"rt_{task}_{epn}_head_{i:04d}.jpg")
                if not os.path.exists(img):
                    im = cv2.imdecode(np.frombuffer(h["observation/head_camera/rgb"][i], np.uint8), cv2.IMREAD_COLOR)
                    cv2.imwrite(img, im)
                Tbc = np.eye(4)
                Tcw = G.inv_T(G.as_4x4(E))
                Tbc[:3, :3] = R_OURS_WORLD @ Tcw[:3, :3]
                Tbc[:3, 3] = R_OURS_WORLD @ Tcw[:3, 3]
                robot["cameras"] = [{"name": "head camera", "W": 320, "H": 240, "K": np.asarray(K).tolist(),
                                     "T_base_cam": Tbc.tolist()}]
                uv, z = G.project(K, E, tip[i])
                uvw, _ = G.project(K, E, ep[i, :3])
                if z > 0 and 0 <= uv[0] < 320 and 0 <= uv[1] < 240:
                    recP.append(F.qa_point(robot, "ee_point", uv, 0, img, f"rt_{task}_{epn}_{arm}_{i}_ee"))
                    a_cam = G.as_4x4(E)[:3, :3] @ (sg * G.quat_wxyz_to_mat(ep[i, 3:])[:, ax])
                    recP.append(F.qa_xyz(robot, "ee_approach_cam", a_cam, 0, img, f"rt_{task}_{epn}_{arm}_{i}_ax"))
                    ax2, _ = G.project(K, E, tip[i] + 0.06 * sg * G.quat_wxyz_to_mat(ep[i, 3:])[:, ax])
                    items.append({"img": img, "ee": uv, "ax": ax2, "obj": uvw, "label": f"rt {arm} f{i}"})
            for si, s in enumerate(segs):
                s2 = dict(s, target=None if s["target"] is None else to_ours(tip[s["target_t"]]).tolist())
                for k in S.sample_frames(s, 2):
                    hi = os.path.join(out, "frames", f"rt_{task}_{epn}_head_{k:04d}.jpg")
                    if not os.path.exists(hi):
                        im = cv2.imdecode(np.frombuffer(h["observation/head_camera/rgb"][k], np.uint8),
                                          cv2.IMREAD_COLOR)
                        cv2.imwrite(hi, im)
                    wi = os.path.join(out, "frames", f"rt_{task}_{epn}_{arm}wrist_{k:04d}.jpg")
                    if not os.path.exists(wi):
                        im = cv2.imdecode(np.frombuffer(h[f"observation/{arm}_camera/rgb"][k], np.uint8),
                                          cv2.IMREAD_COLOR)
                        cv2.imwrite(wi, im)
                    robot["cameras"].append({"name": f"{arm} wrist camera", "W": 320, "H": 240,
                                             "K": np.asarray(h[f"observation/{arm}_camera/intrinsic_cv"][k]).tolist(),
                                             "T_base_cam": None})
                    recC.append(F.control_record(robot, s2, k, to_ours(tip[k]), 0.08 * grip[k], instr,
                                                 "kitchenpot", "table", hist, first=(si == 0 and k == s["t0"]),
                                                 images=[hi, wi], rid=f"rt_{task}_{epn}_{arm}_{k}_{s['step']}"))
                    robot["cameras"] = robot["cameras"][:1]
                    if s["target"] is not None:
                        E = h["observation/head_camera/extrinsic_cv"][k]
                        K = h["observation/head_camera/intrinsic_cv"][k]
                        tuv, tz = G.project(K, E, tip[s["target_t"]])
                        items.append({"img": hi, "tgt": tuv if tz > 0 else None, "label": f"rt {arm} f{k} {s['step']}"})
                if s2["target"] is not None:
                    t = s2["target"]
                    hist.append(f"{len(hist) + 1}: eef to ({t[0]:.3f}, {t[1]:.3f}, {t[2]:.3f}), gripper "
                                f"{s['gripper']} -> done")
            per_ep.append({"ep": f"{task}/{epn}/{arm}", "n": n, "steps": [s["step"] for s in segs],
                           "approach_axis": [int(ax), int(sg), round(score, 3)]})
    for name, rr in (("records_P.jsonl", recP), ("records_C.jsonl", recC)):
        with open(os.path.join(out, name), "w") as f:
            for r in rr:
                f.write(json.dumps(r) + "\n")
    rep = {"episodes": len(files), "n_P": len(recP), "n_C": len(recC), "grasp_tilts": tilts,
           "note": "EE-on-gripper gate is by eye on the sheets (no gripper points / segmentation stored)",
           "C_by_step": {k: sum(r["step"] == k for r in recC) for k in sorted({r["step"] for r in recC})},
           "per_episode": per_ep}
    return rep, items
