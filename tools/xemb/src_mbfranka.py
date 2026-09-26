"""MolmoBot-data Franka pick-and-place (FrankaPickAndPlaceOmniCamConfig, ODC-BY) -> P + C' records (the C' main source).

Measured on 50 train packages (2026-09-27; howto 4.1, 9.1):
  a package holds several h5 batches 'trajectories_batch_<b>_of_20.h5' (each traj_0..4 + valid_traj_mask); the videos
    carry the same batch tag; cameras are randomised per batch: 3-4 exocentric ('droid_shoulder_light_randomization',
    'randomized_gopro_analogue_1', 'randomized_zed2_analogue_{1,2}') + 'wrist_camera_zed_mini' (+ its depth), 624 x 352.
  intrinsic_cv is stored for a 480 x 480 render -> rescale_K_vertical_fov(K, W, H) as for RBY1 (checked with G6).
  actions/ee_pose (JSON) keys 'arm' / 'gripper' (identical), ROBOT BASE frame, [x, y, z, qw, qx, qy, qz]; the base is
    fixed (obs/extra/robot_base_pose, world, wxyz).
  obs/agent/qpos 'gripper' = 2 equal joints, ~0.003 open ... ~0.8 closed empty (stops lower on an object);
    actions/joint_pos 'gripper' = command 0 (open) / 255 (close).
  obs/extra/object_image_points is ONE JSON per step {part: {camera: [[x, y] x10, normalised]}} with parts pickup_obj /
    place_receptacle only (no gripper points -> the EE-on-gripper gate is by eye).
  policy phases: unknown 0, gripper-open 1, pregrasp 2, grasp 3, gripper-close 4, lift 5, preplace 6, place 7,
    retreat 8, go_home 9.
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
from .src_molmobot import dec, read_frames

LAG = 1
HELD_Q = 0.74  # closed interval whose max finger qpos stays below this = the fingers stopped on an object
PHASE_OK = {"above_target": (0, 1, 2), "descend_close": (2, 3, 4), "carry_up": (4, 5), "carry_over": (5, 6),
            "lower_open": (6, 7), "retreat": (7, 8, 9), "done": (8, 9, 0), "reopen": (1, 2, 3, 4, 5)}
TOPDOWN_DEG = 30.0
MIN_EE_Z = 0.6  # EE point QA only when the TCP is >= 0.6 m from the camera (eye check: close views put the TCP
# ring one finger length past the tips, 4/15 tiles; the TCP definition is to be checked in the MJCF)


class Episode:
    def __init__(self, pkg, h, hp, k):
        g = h[f"traj_{k}"]
        self.g, self.k, self.pkg = g, k, pkg
        self.batch = os.path.basename(hp)[len("trajectories_"):-3]
        self.name = f"{os.path.basename(pkg).replace('FrankaPickAndPlaceOmniCamConfig_', 'fr_')}_" \
                    f"{self.batch.replace('batch_', 'b').replace('_of_', 'o')}_t{k}"
        n = g["obs/extra/robot_base_pose"].shape[0]
        self.n = n
        ee, last = [], None
        for i in range(n):
            last = dec(g["actions/ee_pose"][i]).get("gripper", last)
            ee.append(last)
        first = next(r for r in ee if r is not None)
        self.ee_base = np.array([r if r is not None else first for r in ee], float)
        self.q = np.array([dec(g["obs/agent/qpos"][i])["gripper"][0] for i in range(n)], float)
        cmd, lastc = [], 0.0
        for i in range(n):
            c = dec(g["actions/joint_pos"][i]).get("gripper")
            lastc = c[0] if c else lastc
            cmd.append(lastc)
        self.cmd = np.array(cmd, float)
        self.base = g["obs/extra/robot_base_pose"][:].astype(float)
        self.tcp = g["obs/extra/tcp_pose"][:].astype(float)  # MEASURED TCP (the only move group), base frame, wxyz
        self.scene = json.loads(g["obs_scene"][()])
        self.obj_start = g["obs/extra/obj_start"][0].astype(float)
        self.success = bool(g["success"][-1])
        self.phase = g["obs/extra/policy_phase"][:]
        self.retries = int(np.max(g["obs/extra/policy_num_retries"][:]))
        self.cams = [c for c in g["obs/sensor_param"].keys() if os.path.exists(self.video(c))]
        self.exo = sorted(c for c in self.cams if not c.startswith("wrist"))
        self.wrist = next((c for c in self.cams if c.startswith("wrist") and not c.endswith("depth")), None)
        self._wh = {}

    def video(self, cam):
        return os.path.join(self.pkg, f"episode_{self.k:08d}_{cam}_{self.batch}.mp4")

    def wh(self, cam):
        if cam not in self._wh:
            import cv2
            cap = cv2.VideoCapture(self.video(cam))
            self._wh[cam] = (int(cap.get(3)), int(cap.get(4)))
        return self._wh[cam]

    def T_world_base(self, i):
        return G.pose_to_T(self.base[i, :3], G.quat_wxyz_to_mat(self.base[i, 3:]))

    def T_base_ee(self, i):
        return G.pose_to_T(self.ee_base[i, :3], G.quat_wxyz_to_mat(self.ee_base[i, 3:]))

    def E(self, cam, i):
        return G.as_4x4(self.g[f"obs/sensor_param/{cam}/extrinsic_cv"][i])

    def K(self, cam, i):
        W, H = self.wh(cam)
        return G.rescale_K_vertical_fov(self.g[f"obs/sensor_param/{cam}/intrinsic_cv"][i], W, H)

    def pts(self, part, cam, i):
        W, H = self.wh(cam)
        o = self.g["obs/extra/object_image_points"]
        if not hasattr(o, "shape"):  # group layout (as RBY1): <part>/<cam>/points
            key = f"{part}/{cam}/points"
            if key not in o:
                return np.array([[np.nan, np.nan]])
            return o[key][i].astype(float) * [W, H]
        d = dec(o[i]).get(part, {}).get(cam)  # JSON-per-step layout
        return np.array(d if d else [[np.nan, np.nan]], float).reshape(-1, 2) * [W, H]

    def closed(self):
        return self.cmd > 127.5

    def held(self):
        c = self.closed()
        out = np.zeros_like(c)
        i = 0
        while i < len(c):
            if c[i]:
                j = i
                while j < len(c) and c[j]:
                    j += 1
                settle = self.q[min(i + 5, j - 1):j]  # after the fingers had time to close
                out[i:j] = len(settle) > 0 and settle.max() < HELD_Q
                i = j
            else:
                i += 1
        return out

    def names(self):
        r = self.scene.get("referral_expressions") or {}
        a = (r.get("pickup_name") or [["object"]])[0][0]
        b = (r.get("place_name") or [["target"]])[0][0]
        return a, b


def episodes(root):
    for pkg in sorted(glob.glob(os.path.join(root, "FrankaPickAndPlaceOmniCamConfig_*"))):
        if not os.path.isdir(pkg):
            continue
        for hp in sorted(glob.glob(os.path.join(pkg, "trajectories_*.h5"))):
            import h5py
            h = h5py.File(hp, "r")
            mask = h["valid_traj_mask"][:] if "valid_traj_mask" in h else None
            for key in sorted(x for x in h.keys() if x.startswith("traj_")):
                k = int(key.split("_")[1])
                if mask is not None and k < len(mask) and not mask[k]:
                    continue
                yield Episode(pkg, h, hp, k)


def convert(root, out, every=10, max_eps=400, max_frames_eps=60):
    import cv2
    os.makedirs(os.path.join(out, "frames"), exist_ok=True)
    eps = [e for _, e in zip(range(max_eps), episodes(root))]
    # approach axis from the final approach direction (as RBY1)
    Rs, vs, segs_of = [], [], {}
    for e in eps:
        segs = S.segment(e.ee_base[:, :3], e.closed(), e.held())
        segs_of[e.name] = segs
        for s in segs:
            if s["step"] == "descend_close":
                v = e.ee_base[s["t1"], :3] - e.ee_base[s["t0"], :3]
                if np.linalg.norm(v) >= 0.03:
                    Rs.append(e.T_base_ee(s["t1"])[:3, :3])
                    vs.append(v)
    ax, sg, score = G.approach_axis(Rs, vs)
    allee = np.concatenate([e.ee_base[:, :3] for e in eps])
    lo, hi = np.percentile(allee, 1, 0), np.percentile(allee, 99, 0)
    robot = {"name": "franka", "source": "molmobot/franka", "arm": "only",
             "desc": "Franka Emika Panda 7-DoF arm on a fixed base (MolmoBot simulation)",
             "gripper": {"open_gap_m": 0.085}, "workspace": {"x": [lo[0], hi[0]], "y": [lo[1], hi[1]], "z": [lo[2], hi[2]]},
             "cameras": []}
    recP, recC, items, per_ep = [], [], [], []
    g6, ph, tilts, qmax_closed, g10 = [], [], [], [], []
    n_c_all = 0
    near_cam = {True: 0, False: 0}
    for ei, e in enumerate(eps):
        if not e.exo or not e.wrist:
            continue
        segs = segs_of[e.name]
        closed, held = e.closed(), e.held()
        i0 = 0
        while i0 < e.n:  # closed-interval max qpos distribution (for HELD_Q)
            if closed[i0]:
                j = i0
                while j < e.n and closed[j]:
                    j += 1
                qmax_closed.append(float(e.q[min(i0 + 5, j - 1):j].max()))
                i0 = j
            else:
                i0 += 1
        for s in segs:
            ok = PHASE_OK.get(s["step"])
            if ok:
                ph += [int(e.phase[t]) in ok for t in range(s["t0"], s["t1"])]
        dc = [s for s in segs if s["step"] == "descend_close"]
        tilt = G.tilt_deg(sg * (e.T_world_base(dc[0]["t1"]) @ e.T_base_ee(dc[0]["t1"]))[:3, ax]) if dc else None
        if tilt is not None:
            tilts.append(tilt)
        keep_c = tilt is not None and tilt <= TOPDOWN_DEG
        ups = np.nonzero(closed[1:] & ~closed[:-1])[0]
        grasp_t = int(ups[0]) + 1 if len(ups) else e.n
        pick, place = e.names()
        cam = e.exo[ei % len(e.exo)]  # rotate the exocentric camera across episodes (camera diversity)
        do_p = ei < max_frames_eps
        idx_p = list(range(LAG, e.n, every)) if do_p else []
        idx_c = sorted({k for s in segs for k in S.sample_frames(s, 2)}) if keep_c else []
        n_c_all += sum(len(S.sample_frames(s, 2)) for s in segs)
        frames = read_frames(e.video(cam), sorted(set(idx_p + idx_c)))
        wfr = read_frames(e.video(e.wrist), idx_c)
        W, H = e.wh(cam)
        for i in idx_p:
            if i not in frames:
                continue
            img = os.path.join(out, "frames", f"{e.name}_{cam}_{i:04d}.jpg")
            cv2.imwrite(img, frames[i])
            K, Ewc = e.K(cam, i), e.E(cam, i)
            Tbc = G.inv_T(e.T_world_base(i)) @ G.inv_T(Ewc)
            robot["cameras"] = [{"name": cam.replace("_", " ") + " camera", "W": W, "H": H, "K": K.tolist(),
                                 "T_base_cam": Tbc.tolist()}]
            Twe = e.T_world_base(i) @ G.pose_to_T(e.tcp[i, :3], G.quat_wxyz_to_mat(e.tcp[i, 3:]))
            uv, z = G.project(K, Ewc, Twe[:3, 3])
            item = {"img": img, "label": f"{e.name[-16:]} f{i}", "crop": 200}
            if z > 0 and 0 <= uv[0] < W and 0 <= uv[1] < H:
                near_cam[z >= MIN_EE_Z] += 1
            if z >= MIN_EE_Z and 0 <= uv[0] < W and 0 <= uv[1] < H:  # close views: TCP offset beyond the tips shows
                recP.append(F.qa_point(robot, "ee_point", uv, 0, img, f"mf_{e.name}_{i}_ee"))
                recP.append(F.qa_xyz(robot, "ee_approach_cam", Ewc[:3, :3] @ (sg * Twe[:3, ax]), 0, img,
                                     f"mf_{e.name}_{i}_eeax"))
                tip, _ = G.project(K, Ewc, Twe[:3, 3] + 0.08 * sg * Twe[:3, ax])
                item.update(ee=uv, ax=tip)
            op = e.pts("pickup_obj", cam, i)
            if np.isfinite(op).all(1).any():
                c2 = np.nanmean(op, 0)
                recP.append(F.qa_point(robot, "obj_point", c2, 0, img, f"mf_{e.name}_{i}_obj", name=pick))
                item["obj"] = c2
                if i < grasp_t:
                    uvo, zo = G.project(K, Ewc, e.obj_start[:3])
                    if zo > 0:
                        g6.append(float(np.linalg.norm(uvo - c2)))
                        item["obj_proj"] = uvo
                    recP.append(F.qa_xyz(robot, "obj_center_cam", G.apply_T(Ewc, e.obj_start[:3]), 0, img,
                                         f"mf_{e.name}_{i}_objc", name=pick))
            pp = e.pts("place_receptacle", cam, i)
            if np.isfinite(pp).all(1).any():
                c3 = np.nanmean(pp, 0)
                recP.append(F.qa_point(robot, "place_point", c3, 0, img, f"mf_{e.name}_{i}_place", name=place))
                item["place"] = c3
            if ei < 12:
                items.append(item)
        hist, nC = [], 0
        for si, s in enumerate(segs):
            for k in (S.sample_frames(s, 2) if keep_c else []):
                if k not in frames or k not in wfr:
                    continue
                hi_ = os.path.join(out, "frames", f"{e.name}_{cam}_{k:04d}.jpg")
                wi = os.path.join(out, "frames", f"{e.name}_wrist_{k:04d}.jpg")
                cv2.imwrite(hi_, frames[k])
                cv2.imwrite(wi, wfr[k])
                K, Ewc = e.K(cam, k), e.E(cam, k)
                Tbc = G.inv_T(e.T_world_base(k)) @ G.inv_T(Ewc)
                ww, wh = e.wh(e.wrist)
                robot["cameras"] = [{"name": cam.replace("_", " ") + " camera", "W": W, "H": H, "K": K.tolist(),
                                     "T_base_cam": Tbc.tolist()},
                                    {"name": "wrist camera", "W": ww, "H": wh, "K": e.K(e.wrist, k).tolist(),
                                     "T_base_cam": None}]
                opening = float(np.clip(1 - e.q[k] / 0.8, 0, 1)) * robot["gripper"]["open_gap_m"]
                r = F.control_record(robot, s, k, e.tcp[k, :3], opening,
                                     e.scene.get("task_description", ""), pick, place, hist,
                                     first=(si == 0 and k == s["t0"]), images=[hi_, wi],
                                     rid=f"mf_{e.name}_{k}_{s['step']}")
                recC.append(r)
                g10.append(not F.leak_flags(r["answer"], {"x": [-9, 9], "y": [-9, 9], "z": [-9, 9]}))
                nC += 1
                if s["target"] is not None and ei < 12:
                    tuv, tz = G.project(K, Ewc, G.apply_T(e.T_world_base(k), s["target"]))
                    items.append({"img": hi_, "tgt": tuv if tz > 0 else None, "crop": 200,
                                  "label": f"{e.name[-16:]} f{k} {s['step']}"})
            if s["target"] is not None:
                t = s["target"]
                hist.append(f"{len(hist) + 1}: eef to ({t[0]:.3f}, {t[1]:.3f}, {t[2]:.3f}), gripper {s['gripper']} -> "
                            f"done; TCP now ({t[0]:.3f}, {t[1]:.3f}, {t[2]:.3f})")
            elif s["gripper"]:
                hist.append(f"{len(hist) + 1}: gripper {s['gripper']} -> done")
        per_ep.append({"ep": e.name, "success": e.success, "retries": e.retries, "n": e.n, "cam": cam,
                       "steps": [s["step"] for s in segs], "grasp_tilt_deg": tilt, "c_kept": keep_c, "n_C": nC})
    for name, rr in (("records_P.jsonl", recP), ("records_C.jsonl", recC)):
        with open(os.path.join(out, name), "w") as f:
            for r in rr:
                f.write(json.dumps(r) + "\n")
    T = np.array(tilts)
    full = [p for p in per_ep if p["steps"][-1:] == ["done"] and "lower_open" in p["steps"]]
    rep = {"episodes": len(per_ep), "packages": len({p["ep"].split("_b")[0] for p in per_ep}),
           "approach_axis": {"axis": int(ax), "sign": int(sg), "mean_cos": round(score, 3), "n": len(Rs)},
           "obj_start_proj_px_G6": Q.err_stats(g6), "step_vs_planner_phase_G7": Q.rate(ph),
           "full_cycle_episodes": len(full), "success": sum(p["success"] for p in per_ep),
           "grasp_tilt": {"n": int(len(T)), "le20": round(float((T <= 20).mean()), 3) if len(T) else None,
                          "le30": round(float((T <= 30).mean()), 3) if len(T) else None,
                          "median": round(float(np.median(T)), 1) if len(T) else None},
           "closed_interval_qmax_hist": np.histogram(qmax_closed, bins=[0, .3, .5, .6, .7, .74, .78, .8, 1])[0].tolist(),
           "n_P": len(recP), "n_C": len(recC), "n_C_without_topdown_filter": n_c_all,
           "G10_answers_clean": Q.rate(g10), "ee_visible_far_vs_near": {"far": near_cam[True], "near": near_cam[False]},
           "P_by_kind": {k: sum(r["qa_kind"] == k for r in recP) for k in sorted({r["qa_kind"] for r in recP})},
           "C_by_step": {k: sum(r["step"] == k for r in recC) for k in sorted({r["step"] for r in recC})},
           "robot": {k: v for k, v in robot.items() if k != "cameras"}, "per_episode": per_ep}
    return rep, items
