"""T1+T4 samples for another ROBOTIS AI Worker rig (RB3 pickup_obj; FFW-BG2 rev4, real) with the T4 silhouette-aligned
head camera (one camera per dataset, arm_base_link frame; proto/t4_rig.py -> t4r2/<rig>_box60g_r.npz, held-out
boundary chamfer as the gate value). Same records as src_rb2 (T4 branch):
  P  ee_point (FK end effector of the task's arm projected with the T4 camera, inside the image, in front)
  C' control records with the camera info (T4 camera) and camera unknown, targets = FK key poses in arm_base_link
Names come from the task sentence "Pick up the X with the {left|right} gripper and place it into the Y ..."; the arm is
the one the sentence names. Gripper joint 0 open .. ~1.1 closed, > 0.5 closed (as RB2).
usage (pod): python -m xemb.src_rig_t4 RAW_ROOT CAM_NPZ HELDOUT_PX OUT_DIR [N_EPISODES]
"""
from __future__ import annotations

import json
import os
import re
import sys

import numpy as np

from . import fmt as F
from . import geom as G
from . import steps as S

W, H = 672, 376
GRIP_CLOSED = 0.5
GATE_PX = 5.0
URDF = "/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf"
GJ = {"left": "gripper_l_joint1", "right": "gripper_r_joint1"}
_TASK = re.compile(r"pick up (?:the |a )?(?P<obj>.+?) with the (?P<arm>left|right) gripper and (?:place|put) it "
                   r"(?:into|in|onto|on) (?:the |a )?(?P<rec>.+?)(?: below| above)?\.?$", re.I)


def parse_task(task: str):
    m = _TASK.match((task or "").strip())
    return (m.group("obj"), m.group("rec"), m.group("arm").lower()) if m else None


def convert(raw, cam_npz, heldout_px, out, n_eps=10 ** 9, every=5, tag="rb3", source="robotis/ffw_bg2_rb3"):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    import av
    import pyarrow.parquet as pq
    from harvest.train import se2e_data as SD
    os.makedirs(os.path.join(out, "frames"), exist_ok=True)
    z = np.load(cam_npz)
    E, K = z["E_head"], z["K"]
    gate = float(heldout_px) <= GATE_PX
    info = json.load(open(os.path.join(raw, "meta", "info.json")))
    names = info["features"]["observation.state"]["names"]
    eps = [json.loads(x) for x in open(os.path.join(raw, "meta", "episodes.jsonl"))]
    chain = {a: SD.load_arm_chain(URDF, a) for a in ("left", "right")}
    rng = np.random.default_rng(0)
    pick = sorted(rng.permutation(len(eps))[:n_eps].tolist())
    base = {"name": "ffw_bg2", "source": source, "gripper": {"open_gap_m": 0.10}, "workspace": None,
            "desc": "ROBOTIS AI Worker FFW-BG2 (real robot; positions from its URDF and joint encoders)"}
    cam_c = [{"name": "head camera", "W": W, "H": H, "K": K.tolist(), "T_base_cam": G.inv_T(E).tolist()}]
    cam_u = [{"name": "head camera", "W": W, "H": H, "K": None, "T_base_cam": None}]
    fP, fC = open(os.path.join(out, "records_P.jsonl"), "w"), open(os.path.join(out, "records_C.jsonl"), "w")
    cnt = {"episodes": 0, "parsed": 0, "ee_point": 0, "control_with_camera": 0, "control_camera_unknown": 0,
           "gate_pass": gate, "heldout_px": float(heldout_px)}
    allee = []
    plan = []
    for i in pick:
        e = eps[i]
        ep, task = int(e["episode_index"]), (e.get("tasks") or [""])[0]
        cnt["episodes"] += 1
        pt = parse_task(task)
        if pt is None:
            continue
        cnt["parsed"] += 1
        c = ep // info["chunks_size"]
        t = pq.read_table(os.path.join(raw, info["data_path"].format(episode_chunk=c, episode_index=ep)))
        st = np.asarray(t.column("observation.state").to_pylist(), float)
        a = pt[2]
        X = SD.fk_ee(chain[a], st[:, SD.arm_index(names, a)[:7]])
        g = st[:, list(names).index(GJ[a])]
        allee.append(X)
        plan.append((ep, c, task, pt, X, g))
    lo, hi = np.percentile(np.concatenate(allee), 1, 0), np.percentile(np.concatenate(allee), 99, 0)
    base["workspace"] = {"x": [lo[0], hi[0]], "y": [lo[1], hi[1]], "z": [lo[2], hi[2]]}
    for ep, c, task, (obj, rec, a), X, g in plan:
        closed = g > GRIP_CLOSED
        segs = S.segment(X, closed, None) if closed.any() else []
        kc = sorted({k for s in segs for k in S.sample_frames(s, 1)})
        kp = list(range(0, len(X), every))
        want = set(kp + kc)
        vid = os.path.join(raw, info["video_path"].format(episode_chunk=c, video_key="observation.images.cam_head",
                                                          episode_index=ep))
        if not os.path.exists(vid):
            continue
        imgs = {}
        with av.open(vid) as cont:
            for i, fr in enumerate(cont.decode(video=0)):
                if i in want:
                    p = os.path.join(out, "frames", f"{tag}_ep{ep:06d}_f{i:04d}.jpg")
                    fr.to_image().save(p, quality=90)
                    imgs[i] = p
                if i >= max(want):
                    break
        rob_c, rob_u = dict(base, arm=a, cameras=cam_c), dict(base, arm=a, cameras=cam_u)
        Xc = X @ E[:3, :3].T + E[:3, 3]
        for k in kp:
            if k not in imgs or not gate or Xc[k, 2] <= 0.05:
                continue
            u = K[0, 0] * Xc[k, 0] / Xc[k, 2] + K[0, 2]
            v = K[1, 1] * Xc[k, 1] / Xc[k, 2] + K[1, 2]
            if 12 <= u <= W - 12 and 12 <= v <= H - 12:
                fP.write(json.dumps(F.qa_point(rob_c, "ee_point", [u, v], 0, imgs[k], f"{tag}_{ep}_{k}_{a}_t4")) + "\n")
                cnt["ee_point"] += 1
        hist = []
        for si, s in enumerate(segs):
            for k in S.sample_frames(s, 1):
                if k not in imgs:
                    continue
                for robot, key in ((rob_u, "control_camera_unknown"), (rob_c, "control_with_camera")):
                    if key == "control_with_camera" and not gate:
                        continue
                    r = F.control_record(robot, s, k, X[k], 0.10 * max(0.0, 1 - g[k] / 1.1), task, obj, rec, hist,
                                         first=(si == 0), images=[imgs[k]],
                                         rid=f"{tag}_{ep}_{a}_{k}_{s['step']}_{key[8:11]}")
                    fC.write(json.dumps(r) + "\n")
                    cnt[key] += 1
            if s["target"] is not None:
                tt = s["target"]
                hist.append(f"{len(hist) + 1}: eef to ({tt[0]:.3f}, {tt[1]:.3f}, {tt[2]:.3f}), gripper {s['gripper']}")
    fP.close()
    fC.close()
    json.dump(cnt, open(os.path.join(out, "report.json"), "w"), indent=1)
    return cnt


if __name__ == "__main__":
    print(json.dumps(convert(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4],
                             *(int(x) for x in sys.argv[5:6])), indent=1))
