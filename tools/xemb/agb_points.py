"""AgiBot World Beta -> point labels (user-log 164/165/167; CC BY-NC-SA 4.0: nc rows, never sent to Astra).
Per episode (head_color 640x480, head fixed within an episode; per-frame camera->base extrinsics, inverted to project):
  * segments from label_info.action_config; semantic intents (embodiment-free, user-log 167) per segment:
      Pick / Grasp / Retrieve -> approach (first half), grasp (second half); Place / Put -> move (first half),
      place (second half); Lift -> lift; others -> none. Boundary frames (BOUND of each segment edge) excluded.
  * object point (obj_point): name = the object phrase of a Pick-like action text; contact = TCP at the Pick end frame
    (arm = the one whose gripper closes most in the segment; TCP = flange end/position + TCP_D along the end z axis,
    quaternion xyzw); label frame = Pick start + BOUND (object not yet in the hand); SAM 3.1 with the name on that
    frame -> the mask under / nearest the projected contact point; point = mask pixel nearest the mask centroid.
  * place point (place_point): same with the receptacle phrase of a Place-like text, contact = TCP at the Place end.
  * G-proj (<= 5 px): distance from the projected contact point to the chosen mask <= GATE_PX, else the row is dropped.
usage (pod, python 3.12 + venv_sam3 + venv_e3st sites, 1 GPU):
  python -m xemb.agb_points KEEP META OUT TASK [TASK ...] [--fit]    (--fit: TCP_D scan, report only)"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

import numpy as np

from . import gsplit as GS
from . import pointlab as PL

TCP_D = float(os.environ.get("AGB_TCP_D", "0.12"))
BOUND = 5
GATE_PX = 5.0
LIC = "CC BY-NC-SA 4.0"
SRC = "agibot/g1"
_PICK = re.compile(r"^(?:pick up|pick|grasp|grab|retrieve|take|lift|hold)\s+(?:up\s+)?(?:the |a |an )?(.+?)"
                   r"(?:\s+(?:from|off|out of|outside|on|in|inside|at|with|using|and|near|to)\b.*)?\.?$", re.I)
_PLACE = re.compile(r"^(?:place|put|drop|insert|hang|set)\s+(?:the |a |an )?(?:held\s+)?(.+?)\s+"
                    r"(?:into|in|onto|on|inside|to|at)\s+(?:the |a |an )?(.+?)"
                    r"(?:\s+(?:with|using|in the|on the|of the)\b.*)?\.?$", re.I)


def pick_name(text):
    m = _PICK.match(text.strip())
    return PL.clean_name(m.group(1)) if m else None


def place_name(text):
    m = _PLACE.match(text.strip())
    return PL.clean_name(m.group(2)) if m else None


def intent_of(skill, frac):
    s = skill.lower()
    if s in ("pick", "grasp", "retrieve", "grab"):
        return "approach" if frac < 0.5 else "grasp"
    if s in ("place", "put", "drop"):
        return "move" if frac < 0.5 else "place"
    if s in ("lift", "raise"):
        return "lift"
    return None


def load_cam(pdir):
    from .agb_projtest import load_cam as lc
    return lc(pdir)


def tcp(z, k, arm):
    from scipy.spatial.transform import Rotation as Rot
    p, q = z["end_pos"][k][arm], z["end_quat"][k][arm]
    return p + TCP_D * Rot.from_quat(q).as_matrix()[:, 2]


def project(K, dist, Tcb, X):
    from .agb_projtest import proj
    uv = proj(K, dist, np.linalg.inv(Tcb), np.asarray(X)[None])
    return None if uv is None else uv[0]


def closing_arm(z, a, b):
    g = z["grip"][a:b + 1]
    return int(np.argmax(g.max(0) - g.min(0))) if len(g) else 1


def mask_pick(masks, uv):
    """(mask, distance px) of the mask under / nearest the point."""
    import cv2
    best = (None, 1e9)
    for m in masks:
        u, v = int(round(uv[0])), int(round(uv[1]))
        if 0 <= v < m.shape[0] and 0 <= u < m.shape[1] and m[v, u]:
            return m, 0.0
        dt = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 3)
        if 0 <= v < m.shape[0] and 0 <= u < m.shape[1]:
            d = float(dt[v, u])
            if d < best[1]:
                best = (m, d)
    return best


def centroid_on(m):
    ys, xs = np.nonzero(m)
    c = np.array([xs.mean(), ys.mean()])
    i = int(np.argmin((xs - c[0]) ** 2 + (ys - c[1]) ** 2))
    return np.array([xs[i], ys[i]], float)


def main(keep, meta, out, tasks, fit=False):
    import cv2
    from .agb_projtest import frames
    from harvest.perception.seg import Sam31Image
    seg = Sam31Image(thr=0.3)
    os.makedirs(os.path.join(out, "frames"), exist_ok=True)
    rows, intents, st = [], [], {"episodes": 0, "cand": 0, "kept": 0, "gate_px": [], "no_name": 0, "no_mask": 0}
    scan = {round(d, 2): [] for d in np.arange(0.0, 0.26, 0.02)} if fit else None
    for task in tasks:
        info = {e["episode_id"]: e for e in json.load(open(os.path.join(meta, "task_info", f"task_{task}.json")))}
        for npz in sorted(glob.glob(os.path.join(keep, "npz", task, "*.npz"))):
            ep = int(os.path.basename(npz)[:-4])
            pdir = os.path.join(keep, "params", task, str(ep), "parameters", "camera")
            vid = os.path.join(keep, "obs", task, str(ep), "videos", "head_color.mp4")
            if ep not in info or not (os.path.exists(pdir) and os.path.exists(vid)):
                continue
            st["episodes"] += 1
            z = np.load(npz)
            K, dist, Ts = load_cam(pdir)
            segs = info[ep]["label_info"]["action_config"]
            for s in segs:  # intents (embodiment-free), boundary frames excluded
                a, b = int(s["start_frame"]), int(s["end_frame"])
                for f in range(a + BOUND, b - BOUND):
                    it = intent_of(str(s.get("skill", "")), (f - a) / max(1, b - a))
                    if it:
                        intents.append((ep, f, it))
            jobs = []
            for s in segs:
                sk = str(s.get("skill", "")).lower()
                a, b = int(s["start_frame"]), int(s["end_frame"])
                if sk in ("pick", "grasp", "retrieve", "grab"):
                    jobs.append(("obj_point", pick_name(s["action_text"]), a + BOUND, b, a, b))
                elif sk in ("place", "put", "drop"):
                    jobs.append(("place_point", place_name(s["action_text"]), a + BOUND, b, a, b))
            want = sorted({j[2] for j in jobs if j[1]} | {j[3] for j in jobs if j[1]})
            if not want:
                st["no_name"] += len(jobs)
                continue
            fr = frames(vid, want)
            for kind, name, lf, cf, a, b in jobs:
                if not name or lf not in fr or cf >= len(z["end_pos"]) or lf >= len(Ts):
                    st["no_name"] += 1
                    continue
                st["cand"] += 1
                arm = closing_arm(z, a, b)
                img = fr[lf]
                H, W = img.shape[:2]
                out_s, _ = seg.segment(img[:, :, ::-1], [name])
                masks = [mk.astype(bool) for sc, mk in out_s[name] if sc >= 0.3]
                if fit and kind == "obj_point" and masks:
                    from scipy.spatial.transform import Rotation as Rot
                    p, q = z["end_pos"][cf][arm], z["end_quat"][cf][arm]
                    ax = Rot.from_quat(q).as_matrix()[:, 2]
                    for d in scan:
                        uv = project(K, dist, Ts[lf], p + d * ax)
                        if uv is not None:
                            scan[d].append(mask_pick(masks, uv)[1])
                uv = project(K, dist, Ts[lf], tcp(z, cf, arm))
                if uv is None or not masks:
                    st["no_mask"] += 1
                    continue
                m, dpx = mask_pick(masks, uv)
                st["gate_px"].append(dpx)
                if m is None or dpx > GATE_PX:
                    continue
                pt = centroid_on(m)
                img_p = os.path.join(out, "frames", f"agb_{task}_{ep}_{lf}.jpg")
                if not os.path.exists(img_p):
                    cv2.imwrite(img_p, img)
                r = PL.row(SRC, LIC, "head", img_p, W, H, pt, name, kind, f"agb_t{task}_{ep}_{lf}_{kind[:3]}",
                           extra={"contact_px": round(dpx, 2), "task": task})
                if r:
                    rows.append(r)
                    st["kept"] += 1
    tr, g = GS.split(rows)
    for name_, rr in (("records.jsonl", tr), ("records_G.jsonl", g)):
        with open(os.path.join(out, name_), "a") as f:
            f.writelines(json.dumps(r) + "\n" for r in rr)
    with open(os.path.join(out, "intents.jsonl"), "a") as f:
        f.writelines(json.dumps({"ep": e, "frame": fr_, "intent": it}) + "\n" for e, fr_, it in intents)
    gp = np.array(st.pop("gate_px"))
    st["contact_to_mask_px"] = {"median": round(float(np.median(gp)), 2), "p90": round(float(np.percentile(gp, 90)), 2),
                                "le5": round(float((gp <= GATE_PX).mean()), 3)} if len(gp) else None
    st.update(rows_train=len(tr), rows_G=len(g), intents=len(intents), tcp_d=TCP_D)
    if fit:
        st["tcp_scan"] = {str(d): {"n": len(v), "median_px": round(float(np.median(v)), 2) if v else None,
                                   "le5": round(float((np.array(v) <= 5).mean()), 3) if v else None}
                          for d, v in scan.items()}
    json.dump(st, open(os.path.join(out, f"report_{'_'.join(tasks)[:40]}.json"), "w"), indent=1)
    print(json.dumps(st, indent=1))


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if x != "--fit"]
    main(a[0], a[1], a[2], a[3:], fit="--fit" in sys.argv)
