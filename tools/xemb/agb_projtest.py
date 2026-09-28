"""AgiBot projection test (user-log 163 step 1): head camera = head_color (intrinsics head_intrinsic_params.json,
per-frame extrinsics head_extrinsic_params_aligned.json). Tries both extrinsic readings (camera->base and base->camera)
on the end-effector positions (state/end/position, both arms) and keeps the one that puts the projected points inside
the image on the grasp frames; writes a contact sheet (projected EE on the frame of each Pick segment end) and
alignment facts (frame counts of video / extrinsics / proprio).
usage (pod, python 3.12 + venv_e3st site): python -m xemb.agb_projtest KEEP_DIR META_DIR TASK OUT_DIR"""
from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np


def load_cam(pdir):
    i = json.load(open(os.path.join(pdir, "head_intrinsic_params.json")))["intrinsic"]
    K = np.array([[i["fx"], 0, i["ppx"]], [0, i["fy"], i["ppy"]], [0, 0, 1.0]])
    dist = np.array([i.get("k1", 0), i.get("k2", 0), i.get("p1", 0), i.get("p2", 0), i.get("k3", 0)])
    ex = json.load(open(os.path.join(pdir, "head_extrinsic_params_aligned.json")))
    Ts = []
    for e in ex:
        T = np.eye(4)
        T[:3, :3] = np.array(e["extrinsic"]["rotation_matrix"])
        T[:3, 3] = np.array(e["extrinsic"]["translation_vector"])
        Ts.append(T)
    return K, dist, np.array(Ts)


def proj(K, dist, E, X):
    import cv2
    pc = (E[:3, :3] @ X.T).T + E[:3, 3]
    if (pc[:, 2] <= 0.05).any():
        return None
    uv, _ = cv2.projectPoints(pc, np.zeros(3), np.zeros(3), K, dist)
    return uv.reshape(-1, 2)


def frames(video, idx):
    import av
    out, want = {}, set(idx)
    with av.open(video) as c:
        for i, fr in enumerate(c.decode(video=0)):
            if i in want:
                out[i] = fr.to_ndarray(format="bgr24")
            if i >= max(want):
                break
    return out


def main(keep, meta, task, outd):
    import cv2
    os.makedirs(outd, exist_ok=True)
    info = {e["episode_id"]: e for e in json.load(open(os.path.join(meta, "task_info", f"task_{task}.json")))}
    rep, tiles = {"episodes": []}, []
    for npz in sorted(glob.glob(os.path.join(keep, "npz", task, "*.npz"))):
        ep = int(os.path.basename(npz)[:-4])
        z = np.load(npz)
        pdir = os.path.join(keep, "params", task, str(ep), "parameters", "camera")
        vid = os.path.join(keep, "obs", task, str(ep), "videos", "head_color.mp4")
        if not (os.path.exists(pdir) and os.path.exists(vid) and ep in info):
            continue
        K, dist, Ts = load_cam(pdir)
        segs = info[ep]["label_info"]["action_config"]
        picks = [s["end_frame"] for s in segs if "pick" in str(s.get("skill", "")).lower()][:2]
        fr = frames(vid, picks + [0])
        H, W = fr[0].shape[:2]
        r = {"ep": ep, "video_frames_seen": max(fr) + 1, "W": W, "H": H, "extrinsics": len(Ts),
             "proprio": len(z["end_pos"]), "head_joint_range": np.ptp(z["head"], 0).round(4).tolist(),
             "extr_translation_range_m": np.ptp(Ts[:, :3, 3], 0).round(4).tolist()}
        for k in picks:
            if k not in fr or k >= len(Ts) or k >= len(z["end_pos"]):
                continue
            X = z["end_pos"][k]  # (2, 3) both arms
            best = None
            for name, E in (("cam2base_inv", np.linalg.inv(Ts[k])), ("base2cam", Ts[k])):
                uv = proj(K, dist, E, X)
                if uv is None:
                    continue
                inside = int(((uv[:, 0] >= 0) & (uv[:, 0] < W) & (uv[:, 1] >= 0) & (uv[:, 1] < H)).sum())
                r.setdefault("conv", {})[name] = r.get("conv", {}).get(name, 0) + inside
                if best is None or inside > best[1]:
                    best = (name, inside, uv)
            img = fr[k].copy()
            if best:
                for u, v in best[2]:
                    cv2.circle(img, (int(u), int(v)), 8, (0, 0, 255), 2)
                cv2.putText(img, f"{ep} f{k} {best[0]}", (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            tiles.append(cv2.resize(img, (480, int(480 * H / W))))
        rep["episodes"].append(r)
    if tiles:
        h = min(t.shape[0] for t in tiles)
        tiles = [t[:h] for t in tiles[:8]]
        while len(tiles) % 2:
            tiles.append(np.zeros_like(tiles[0]))
        cv2.imwrite(os.path.join(outd, "sheet.jpg"), np.vstack([np.hstack(tiles[j:j + 2]) for j in range(0, len(tiles), 2)]))
    json.dump(rep, open(os.path.join(outd, "projtest.json"), "w"), indent=1)
    print(json.dumps(rep["episodes"][:4], indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:5])
