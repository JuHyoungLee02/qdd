"""AgiBot TCP offset check (user request 2026-09-28): on the Pick end frame of each check episode, overlay the flange
point, candidates end + d * z for d in 0, 4, 8, 10, 12, 14, 16 cm, and end + 12 cm along x and y; find the fingertip
centre from SAM 3.1 gripper masks (the component nearest the flange projection; the fingertip centre = centroid of
its pixels in the farthest 15 % along the projected z direction) and report each candidate's pixel distance to it.
usage (pod, python 3.12 + venv_sam3 + venv_e3st sites, 1 GPU): python -m xemb.agb_tcpcheck KEEP META EPS_JSON OUT_DIR"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

D_CM = (0, 4, 8, 10, 12, 14, 16)
PHRASES = ("robot gripper", "gripper fingers", "robot hand")


def main(keep, meta, eps_json, outd):
    import cv2
    from scipy.spatial.transform import Rotation as Rot
    from harvest.perception.seg import Sam31Image
    from .agb_points import closing_arm
    from .agb_projtest import frames, load_cam, proj
    os.makedirs(outd, exist_ok=True)
    seg = Sam31Image(thr=0.2)
    eps = json.load(open(eps_json))
    rep = {}
    for ep_s, task in eps.items():
        ep = int(ep_s)
        info = {e["episode_id"]: e for e in json.load(open(os.path.join(meta, "task_info", f"task_{task}.json")))}
        npz = os.path.join(keep, "npz", task, f"{ep}.npz")
        pdir = os.path.join(keep, "params", task, str(ep), "parameters", "camera")
        vid = os.path.join(keep, "obs", task, str(ep), "videos", "head_color.mp4")
        if not all(os.path.exists(p) for p in (npz, pdir, vid)) or ep not in info:
            rep[ep_s] = "missing inputs"
            continue
        z = np.load(npz)
        K, dist, Ts = load_cam(pdir)
        segs = [s for s in info[ep]["label_info"]["action_config"]
                if str(s.get("skill", "")).lower() in ("pick", "grasp", "retrieve", "grab")]
        if not segs:
            rep[ep_s] = "no pick segment"
            continue
        a, k = int(segs[0]["start_frame"]), int(segs[0]["end_frame"])
        arm = closing_arm(z, a, k)
        img = frames(vid, [k])[k]
        H, W = img.shape[:2]
        E = np.linalg.inv(Ts[k])
        p, R = z["end_pos"][k][arm], Rot.from_quat(z["end_quat"][k][arm]).as_matrix()
        cands = {f"z{d}": p + d / 100 * R[:, 2] for d in D_CM}
        cands.update({"x12": p + 0.12 * R[:, 0], "y12": p + 0.12 * R[:, 1]})
        uv = {n: proj(K, dist, E, x[None]) for n, x in cands.items()}
        uv = {n: u[0] for n, u in uv.items() if u is not None}
        # fingertip centre from SAM
        out, _ = seg.segment(img[:, :, ::-1], list(PHRASES))
        f0 = uv.get("z0")
        tip, used = None, None
        for ph in PHRASES:
            for sc, mk in out[ph]:
                m = mk.astype(bool)
                if not m.any() or f0 is None:
                    continue
                ys, xs = np.nonzero(m)
                dmin = np.min(np.hypot(xs - f0[0], ys - f0[1]))
                if dmin > 40:
                    continue
                dirv = uv["z16"] - f0 if "z16" in uv else np.array([0, 1.0])
                dirv = dirv / (np.linalg.norm(dirv) + 1e-9)
                s = (xs - f0[0]) * dirv[0] + (ys - f0[1]) * dirv[1]
                sel = s >= np.percentile(s, 85)
                tip, used = np.array([xs[sel].mean(), ys[sel].mean()]), f"{ph} {sc:.2f}"
                break
            if tip is not None:
                break
        vis = img.copy()
        for n, u in uv.items():
            col = (0, 0, 255) if n.startswith("z") else ((0, 255, 0) if n == "x12" else (255, 0, 0))
            cv2.circle(vis, (int(u[0]), int(u[1])), 4 if n != "z0" else 7, col, 2)
            cv2.putText(vis, n, (int(u[0]) + 5, int(u[1]) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.35, col, 1)
        dists = {}
        if tip is not None:
            cv2.drawMarker(vis, (int(tip[0]), int(tip[1])), (0, 255, 255), cv2.MARKER_CROSS, 14, 2)
            dists = {n: round(float(np.linalg.norm(u - tip)), 1) for n, u in uv.items()}
        cv2.putText(vis, f"task {task} ep {ep} f{k} arm {arm} tip={used}", (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 255, 255), 1)
        cv2.imwrite(os.path.join(outd, f"tcp_{task}_{ep}.png"), vis)
        best = min((d for d in dists if d.startswith("z")), key=lambda d: dists[d]) if dists else None
        rep[ep_s] = {"task": task, "frame": k, "arm": arm, "tip_source": used, "dist_px": dists, "best": best}
    json.dump(rep, open(os.path.join(outd, "tcp_check.json"), "w"), indent=1)
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:5])
