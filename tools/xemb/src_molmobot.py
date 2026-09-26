"""MolmoBot-data (allenai/molmobot-data, ODC-BY) -> perception QA (P) + frame-explicit control (C') records.

Measured conventions (val shard of RBY1PickAndPlaceDataGenConfig, 2026-09-26; howto doc 4.1):
  traj_k/actions/ee_pose (JSON per step) = per-part poses in the ROBOT BASE frame, [x, y, z, qw, qx, qy, qz]
    ('base' is the identity [0,0,0,1,0,0,0]); the acting gripper is 'right_gripper' or 'left_gripper'.
  obs/extra/tcp_pose is the LEFT gripper here (constant while the right arm works) -- do not use it as 'the TCP'.
  obs/extra/robot_base_pose = world pose of the base, [x, y, z, qw, qx, qy, qz].
  obs/sensor_param/<cam>/extrinsic_cv = world -> camera (OpenCV); cam2world_gl = its plain inverse (no axis flip).
  obs/sensor_param/<cam>/intrinsic_cv is for a 480 x 480 render (cx = cy = 240) but the videos are 1024 x 576 with the
    same VERTICAL fov (frozen_config: head fov 138.5 deg = GoPro): K_video = rescale_K_vertical_fov(K, 1024, 576).
  object_image_points/<part>/<cam>/points = 10 geometry points per part in NORMALISED image coords (x W, y H), NaN when
    not visible.
  obs/extra/obj_start = world pose of the pick object at episode start [x, y, z, qw, qx, qy, qz].
  qpos gripper: -0.05 open ... 0 closed (per finger); grasp_state_* 'held' is never true in this shard (unused).
"""
from __future__ import annotations

import glob
import json
import os

import cv2
import h5py
import numpy as np

from . import fmt as F
from . import gates as Q
from . import geom as G
from . import steps as S

W, H = 1024, 576
OPEN_Q = 0.05
EMPTY_OPEN = 0.03  # 12 % marked thin objects (3 of 15 successful episodes) as empty closes; the empty retry ends at 0.01
LAG = 1  # frames between the commanded ee_pose and the pose seen in the image (gate sweep in gates.json)
LAGS = (0, 1, 2, 3)
PHASE_OK = {"above_target": (0,), "descend_close": (0, 1), "carry_up": (1, 2), "carry_over": (2, 3), "lower_open": (3,),
            "retreat": (3, 4), "done": (4, 5), "reopen": (0, 1, 2, 3)}


def dec(a):
    return json.loads(bytes(np.asarray(a)).decode("utf-8").rstrip("\x00"))


def read_frames(path, idx):
    cap = cv2.VideoCapture(path)
    out, i, want = {}, 0, set(idx)
    while want:
        ok, fr = cap.read()
        if not ok:
            break
        if i in want:
            out[i] = fr
            want.discard(i)
        i += 1
    return out


class Episode:
    def __init__(self, pkg: str, h5, k: int):
        g = h5[f"traj_{k}"]
        self.pkg, self.k, self.g = pkg, k, g
        self.name = f"{os.path.basename(pkg)}_t{k}"
        n = g["obs/extra/robot_base_pose"].shape[0]
        self.n = n
        ee = [dec(g["actions/ee_pose"][i]) for i in range(n)]
        qp = [dec(g["obs/agent/qpos"][i]) for i in range(n)]
        cmd = [dec(g["actions/joint_pos"][i]) for i in range(n)]
        path = {}
        for arm in ("right", "left"):  # the acting arm = the one whose commanded EE travels most (the idle arm may
            ps = [e[f"{arm}_gripper"][:3] for e in ee if f"{arm}_gripper" in e]  # hold its gripper closed all along)
            path[arm] = float(np.sum(np.linalg.norm(np.diff(np.array(ps), axis=0), axis=1))) if len(ps) > 1 else 0.0
        self.arm = max(path, key=path.get)
        a = self.arm
        rows, last = [], None
        for e in ee:  # some steps (e.g. the last) carry an empty action JSON: hold the previous pose
            last = e.get(f"{a}_gripper", last)
            rows.append(last)
        first = next(r for r in rows if r is not None)
        self.ee_base = np.array([r if r is not None else first for r in rows], float)  # x y z qw qx qy qz
        self.n_missing_ee = sum(f"{a}_gripper" not in e for e in ee)
        self.open_meas = np.array([abs(q[f"{a}_gripper"][0]) / OPEN_Q for q in qp])
        oc = np.array([abs(c[f"{a}_gripper"][0]) / OPEN_Q if f"{a}_gripper" in c else np.nan for c in cmd])
        for i in range(1, len(oc)):  # forward-fill empty action steps
            if not np.isfinite(oc[i]):
                oc[i] = oc[i - 1]
        self.open_cmd = oc
        self.base = g["obs/extra/robot_base_pose"][:].astype(float)
        self.scene = json.loads(g["obs_scene"][()])
        self.obj_start = g["obs/extra/obj_start"][0].astype(float)
        self.success = bool(g["success"][-1])
        self.phase = g["obs/extra/policy_phase"][:]
        self.retries = int(np.max(g["obs/extra/policy_num_retries"][:]))

    def T_world_base(self, i):
        return G.pose_to_T(self.base[i, :3], G.quat_wxyz_to_mat(self.base[i, 3:]))

    def T_base_ee(self, i):
        return G.pose_to_T(self.ee_base[i, :3], G.quat_wxyz_to_mat(self.ee_base[i, 3:]))

    def E(self, cam, i):  # world -> cam (CV)
        return G.as_4x4(self.g[f"obs/sensor_param/{cam}/extrinsic_cv"][i])

    def K(self, cam, i):
        return G.rescale_K_vertical_fov(self.g[f"obs/sensor_param/{cam}/intrinsic_cv"][i], W, H)

    def pts(self, part, cam, i):
        p = self.g[f"obs/extra/object_image_points/{part}/{cam}/points"][i].astype(float)
        return p * [W, H]

    def closed(self):
        """From the MEASURED opening: actions/joint_pos '<arm>_gripper' is not a joint position (values 0 / 0.05 /
        100 seen), so the command is not used."""
        return S.closed_from_opening(self.open_meas, close_below=0.8, open_above=0.95)

    def held(self):
        """Closed on something: over each closed interval the fingers stop before fully closing (min opening > EMPTY_OPEN);
        an interval that ends near 0 is an empty close (the retry case)."""
        c = self.closed()
        out = np.zeros_like(c)
        i = 0
        while i < len(c):
            if c[i]:
                j = i
                while j < len(c) and c[j]:
                    j += 1
                out[i:j] = self.open_meas[i:j].min() > EMPTY_OPEN
                i = j
            else:
                i += 1
        return out

    def video(self, cam):
        return glob.glob(os.path.join(self.pkg, f"episode_{self.k:08d}_{cam}_batch_*.mp4"))[0]

    def names(self):
        r = self.scene.get("referral_expressions", {})
        pick = r.get("pickup_name", [["object"]])[0][0]
        place = r.get("place_name", [["target"]])[0][0]
        return pick, place


def episodes(root: str):
    for pkg in sorted(glob.glob(os.path.join(root, "*"))):
        h5s = glob.glob(os.path.join(pkg, "*.h5"))
        if not h5s:
            continue
        h = h5py.File(h5s[0], "r")
        for key in sorted(h.keys()):
            yield Episode(pkg, h, int(key.split("_")[1]))


def approach_axis(eps):
    """Local EE axis along which the gripper moves in the final approach (descend_close segment: EE(c) - EE(p),
    world frame, successful grasps with >= 3 cm of approach). The object-minus-EE vector at the close was tried first
    and is too short to be informative (mean cosine 0.44, 2026-09-26 run)."""
    Rs, vs = [], []
    for e in eps:
        c = S.segment(e.ee_base[:, :3], e.closed(), e.held())
        dc = [s for s in c if s["step"] == "descend_close"]
        if not dc:
            continue
        p, t = dc[0]["t0"], dc[0]["t1"]
        Tw = e.T_world_base(t) @ e.T_base_ee(t)
        v = Tw[:3, 3] - (e.T_world_base(p) @ e.T_base_ee(p))[:3, 3]
        if np.linalg.norm(v) < 0.03:
            continue
        Rs.append(Tw[:3, :3])
        vs.append(v)
    return G.approach_axis(Rs, vs), len(Rs)


def robot_desc(eps, arm="right"):
    allee = np.concatenate([e.ee_base[:, :3] for e in eps])
    lo, hi = np.percentile(allee, 1, 0), np.percentile(allee, 99, 0)
    return {"name": "rby1", "source": "molmobot/rby1", "arm": arm,
            "desc": "Rainbow Robotics RB-Y1 wheeled humanoid with two 7-DoF arms (MolmoBot simulation)",
            "gripper": {"open_gap_m": 2 * OPEN_Q},
            "workspace": {"x": [lo[0], hi[0]], "y": [lo[1], hi[1]], "z": [lo[2], hi[2]]},
            "cameras": []}


def convert(root: str, out: str, every: int = 10, max_eps: int = 50) -> dict:
    os.makedirs(os.path.join(out, "frames"), exist_ok=True)
    eps = [e for _, e in zip(range(max_eps), episodes(root))]
    (ax, sg, score), n_ax = approach_axis(eps)
    robot = robot_desc(eps)
    recP, recC, g_ee, g_obj, tilts, sheet_items, per_ep = [], [], [], [], [], [], []
    lag_gate, g_near = {}, []
    n_c_all = [0]
    ph_agree = []
    for e in eps:
        robot["arm"] = e.arm
        cam_r = f"wrist_camera_{e.arm[0]}"
        closed, held = e.closed(), e.held()
        segs = S.segment(e.ee_base[:, :3], closed, held)
        for s in segs:  # agreement with the dataset planner phase (pregrasp 0, grasp 1, lift 2, place 3, post 4, done 5)
            ok_ph = PHASE_OK.get(s["step"])
            if ok_ph:
                ph_agree += [int(e.phase[t]) in ok_ph for t in range(s["t0"], s["t1"])]
        pick, place = e.names()
        idx_p = list(range(0, e.n, every))
        idx_c = sorted({k for s in segs for k in S.sample_frames(s, 2)})
        frames = read_frames(e.video("head_camera"), sorted(set(idx_p + idx_c)))
        wfr = read_frames(e.video(cam_r), idx_c)
        dc = [s for s in segs if s["step"] == "descend_close"]
        tilt = None
        if dc:
            t = dc[0]["t1"]
            Rw = (e.T_world_base(t) @ e.T_base_ee(t))[:3, :3]
            tilt = G.tilt_deg(sg * Rw[:, ax])
            tilts.append(tilt)
        ups = np.nonzero(closed[1:] & ~closed[:-1])[0]
        grasp_t = int(ups[0]) + 1 if len(ups) else e.n  # object at obj_start only before the first close
        n_ee = [0, 0]
        for i in idx_p:
            if i not in frames:
                continue
            img = os.path.join(out, "frames", f"{e.name}_head_{i:04d}.jpg")
            cv2.imwrite(img, frames[i])
            K, Ewc = e.K("head_camera", i), e.E("head_camera", i)
            Tbc = G.inv_T(e.T_world_base(i)) @ G.inv_T(Ewc)
            robot["cameras"] = [{"name": "head camera", "W": W, "H": H, "K": K.tolist(), "T_base_cam": Tbc.tolist()}]
            ref = e.pts(f"{e.arm}_gripper", "head_camera", i)
            for lag in LAGS:  # actions/ee_pose is the COMMAND; the measured pose lags it (eye check 2026-09-26)
                j = max(i - lag, 0)
                u2, z2 = G.project(K, Ewc, (e.T_world_base(i) @ e.T_base_ee(j))[:3, 3])
                if np.isfinite(ref).all(1).any() and z2 > 0 and i >= lag:
                    lag_gate.setdefault(lag, []).append(Q.on_points(u2, ref, margin_px=10))
                    if lag == LAG:
                        g_near.append(Q.near_points(u2, ref, k=0.5))
            if i < LAG:
                continue
            Twe = e.T_world_base(i) @ e.T_base_ee(i - LAG)
            uv, z = G.project(K, Ewc, Twe[:3, 3])
            vis = np.isfinite(ref).all(1).any() and z > 0 and 0 <= uv[0] < W and 0 <= uv[1] < H
            item = {"img": img, "ee": uv if vis else None, "ref": ref, "label": f"{e.name[-14:]} f{i}", "crop": 240}
            if vis:
                ok = Q.on_points(uv, ref, margin_px=10)
                if not ok:
                    item["fail"] = True
                    item["label"] += " FAIL"
                g_ee.append(ok)
                n_ee[0] += 1
                n_ee[1] += ok
            if vis and Q.near_points(uv, ref, k=0.5):  # quality filter: the command is off the rendered gripper
                recP.append(F.qa_point(robot, "ee_point", uv, 0, img, f"mb_{e.name}_{i}_ee"))
                a_cam = Ewc[:3, :3] @ (sg * Twe[:3, ax])
                recP.append(F.qa_xyz(robot, "ee_approach_cam", a_cam, 0, img, f"mb_{e.name}_{i}_eeax"))
                tip, _ = G.project(K, Ewc, Twe[:3, 3] + 0.08 * sg * Twe[:3, ax])
                item["ax"] = tip
            op = e.pts("pickup_obj", "head_camera", i)
            if np.isfinite(op).all(1).any():
                c2 = np.nanmean(op, 0)
                recP.append(F.qa_point(robot, "obj_point", c2, 0, img, f"mb_{e.name}_{i}_obj", name=pick))
                item["obj"] = c2
                if i < grasp_t:  # object still at its start pose
                    uvo, zo = G.project(K, Ewc, e.obj_start[:3])
                    g_obj.append(float(np.linalg.norm(uvo - c2)))
                    item["obj_proj"] = uvo
                    recP.append(F.qa_xyz(robot, "obj_center_cam", G.apply_T(Ewc, e.obj_start[:3]), 0, img,
                                         f"mb_{e.name}_{i}_objc", name=pick))
            pp = e.pts("place_receptacle", "head_camera", i)
            if np.isfinite(pp).all(1).any():
                c3 = np.nanmean(pp, 0)
                recP.append(F.qa_point(robot, "place_point", c3, 0, img, f"mb_{e.name}_{i}_place", name=place))
                item["place"] = c3
            sheet_items.append(item)
        # C': top-down filter on the grasp approach
        keep_c = tilt is not None and tilt <= 30.0
        hist = []
        nC = 0
        n_c_all[0] += sum(len(S.sample_frames(s, 2)) for s in segs)
        for si, s in enumerate(segs):
            if keep_c:
                for k in S.sample_frames(s, 2):
                    if k not in frames or k not in wfr:
                        continue
                    hi = os.path.join(out, "frames", f"{e.name}_head_{k:04d}.jpg")
                    wi = os.path.join(out, "frames", f"{e.name}_{cam_r}_{k:04d}.jpg")
                    cv2.imwrite(hi, frames[k])
                    cv2.imwrite(wi, wfr[k])
                    K, Ewc = e.K("head_camera", k), e.E("head_camera", k)
                    Tbc = G.inv_T(e.T_world_base(k)) @ G.inv_T(Ewc)
                    robot["cameras"] = [{"name": "head camera", "W": W, "H": H, "K": K.tolist(),
                                         "T_base_cam": Tbc.tolist()},
                                        {"name": f"{e.arm} wrist camera", "W": W, "H": H,
                                         "K": e.K(cam_r, k).tolist(), "T_base_cam": None}]
                    recC.append(F.control_record(robot, s, k, e.ee_base[max(k - LAG, 0), :3], e.open_meas[k] * 2 * OPEN_Q,
                                                 e.scene.get("task_description", ""), pick, place, hist,
                                                 first=(si == 0 and k == s["t0"]), images=[hi, wi],
                                                 rid=f"mb_{e.name}_{k}_{s['step']}"))
                    nC += 1
                    if s["target"] is not None:
                        tuv, tz = G.project(K, Ewc, G.apply_T(e.T_world_base(k), s["target"]))
                        sheet_items.append({"img": hi, "tgt": tuv if tz > 0 else None, "ee": None, "crop": 240,
                                            "label": f"{e.name[-14:]} f{k} {s['step']}"})
            if s["target"] is not None:
                t = s["target"]
                hist.append(f"{len(hist) + 1}: eef to ({t[0]:.3f}, {t[1]:.3f}, {t[2]:.3f}), gripper {s['gripper']} -> "
                            f"done; TCP now ({t[0]:.3f}, {t[1]:.3f}, {t[2]:.3f})")
            elif s["gripper"]:
                hist.append(f"{len(hist) + 1}: gripper {s['gripper']} -> done")
        per_ep.append({"ep": e.name, "arm": e.arm, "success": e.success, "retries": e.retries, "n": e.n,
                       "steps": [s["step"] for s in segs], "grasp_tilt_deg": tilt, "c_kept": keep_c, "n_C": nC,
                       "ee_on_gripper": n_ee})
    with open(os.path.join(out, "records_P.jsonl"), "w") as f:
        for r in recP:
            f.write(json.dumps(r) + "\n")
    with open(os.path.join(out, "records_C.jsonl"), "w") as f:
        for r in recC:
            f.write(json.dumps(r) + "\n")
    rep = {"episodes": len(eps), "approach_axis": {"axis": int(ax), "sign": int(sg), "mean_cos": round(score, 3),
                                                   "n_grasps": n_ax},
           "gate_ee_on_gripper": Q.rate(g_ee), "gate_lag_sweep": {k: Q.rate(v) for k, v in lag_gate.items()},
           "gate_ee_near_gripper_0.5diag": Q.rate(g_near),
           "obj_start_proj_px": Q.err_stats(g_obj),
           "grasp_tilt_deg": sorted(round(t, 1) for t in tilts),
           "topdown_keep_30": Q.rate([t <= 30 for t in tilts]), "topdown_keep_20": Q.rate([t <= 20 for t in tilts]),
           "n_P": len(recP), "n_C": len(recC), "n_C_without_topdown_filter": n_c_all[0], "step_vs_planner_phase_agree": Q.rate(ph_agree),
           "P_by_kind": {k: sum(r["qa_kind"] == k for r in recP) for k in sorted({r["qa_kind"] for r in recP})},
           "C_by_step": {k: sum(r["step"] == k for r in recC) for k in sorted({r["step"] for r in recC})},
           "robot": {k: v for k, v in robot.items() if k != "cameras"}, "per_episode": per_ep}
    with open(os.path.join(out, "gates.json"), "w") as f:
        json.dump(rep, f, indent=1, default=float)
    return rep, sheet_items
