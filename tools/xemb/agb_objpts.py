"""AgiBot object points WITHOUT a TCP offset (controller decision 2026-09-28 b, revised): LABEL frame = Pick start + BOUND
(object visible, before the approach); the grasp frame (Pick end) only identifies WHICH instance was grasped (SAM mask
nearest the flange projection), then the label-frame mask nearest that instance is labelled. Cap AGB_TASK_CAP rows per
task (default 200). Original note: on the grasp frame (Pick end_frame)
SAM 3.1 masks of the object named in the action text; the FLANGE projection of the closing arm only selects which
candidate mask (the nearest one); label = the top-surface centre of that mask (centroid of the upper 30 % of its rows,
snapped onto the mask). Mask quality gate: largest connected component >= 90 % of the mask, area 0.05 %..15 % of the
image, name passes pointlab.clean_name. Semantic intents from action_config (boundary frames excluded) as agb_points.
usage (pod, python 3.12 + sam3 / e3st sites, 1 GPU): python -m xemb.agb_objpts KEEP META OUT EPS_SPEC
  EPS_SPEC: comma list of task ids, or a json {episode: task}"""
from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np

from . import gsplit as GS
from . import pointlab as PL
from .agb_points import BOUND, LIC, SRC, closing_arm, intent_of, pick_name

AREA = (0.0005, 0.15)


def top_centre(m):
    ys, xs = np.nonzero(m)
    y0, y1 = ys.min(), ys.max()
    sel = ys <= y0 + 0.3 * (y1 - y0 + 1)
    c = np.array([xs[sel].mean(), ys[sel].mean()])
    i = int(np.argmin((xs - c[0]) ** 2 + (ys - c[1]) ** 2))
    return np.array([xs[i], ys[i]], float)


def quality(m, W, H):
    import cv2
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
    if n < 2:
        return False, "empty"
    big = stats[1:, cv2.CC_STAT_AREA].max()
    area = m.sum() / float(W * H)
    if big < 0.9 * m.sum():
        return False, "fragmented"
    if not (AREA[0] <= area <= AREA[1]):
        return False, "size"
    return True, "ok"


def episodes(keep, spec):
    if spec.endswith(".json"):
        return [(int(e), t) for e, t in json.load(open(spec)).items()]
    out = []
    for t in spec.split(","):
        out += [(int(os.path.basename(p)[:-4]), t) for p in sorted(glob.glob(os.path.join(keep, "npz", t, "*.npz")))]
    return out


def main(keep, meta, out, spec):
    import cv2
    from harvest.perception.seg import Sam31Image
    from .agb_projtest import frames, load_cam, proj
    seg = Sam31Image(thr=0.3)
    os.makedirs(os.path.join(out, "frames"), exist_ok=True)
    rows, st = [], {"episodes": 0, "cand": 0, "no_name": 0, "no_mask": 0, "fragmented": 0, "size": 0, "kept": 0}
    cap = int(os.environ.get("AGB_TASK_CAP", "200"))  # rows per task (balance: task 327 would dominate)
    per_task = {}
    infos = {}
    for ep, task in episodes(keep, spec):
        if task not in infos:
            infos[task] = {e["episode_id"]: e for e in
                           json.load(open(os.path.join(meta, "task_info", f"task_{task}.json")))}
        info = infos[task]
        npz = os.path.join(keep, "npz", task, f"{ep}.npz")
        pdir = os.path.join(keep, "params", task, str(ep), "parameters", "camera")
        vid = os.path.join(keep, "obs", task, str(ep), "videos", "head_color.mp4")
        if ep not in info or not all(os.path.exists(p) for p in (npz, pdir, vid)):
            continue
        st["episodes"] += 1
        z = np.load(npz)
        K, dist, Ts = load_cam(pdir)
        jobs = [(int(s["start_frame"]), int(s["end_frame"]), pick_name(s["action_text"]))
                for s in info[ep]["label_info"]["action_config"]
                if str(s.get("skill", "")).lower() in ("pick", "grasp", "retrieve", "grab")]
        fr = frames(vid, sorted({b for _, b, _ in jobs} | {a + BOUND for a, _, _ in jobs})) if jobs else {}

        def sam_masks(img, name):
            # SAM recall drops on specific names ('shiitake mushroom'): fall back to the head noun ('mushroom');
            # the label keeps the full name (a subtype of what SAM found)
            for qn in [name] + ([name.split()[-1]] if len(name.split()) > 1 else []):
                res, _ = seg.segment(img[:, :, ::-1], [qn])
                ms = [mk.astype(bool) for sc, mk in res[qn] if sc >= 0.3]
                if ms:
                    return ms
            return []

        def nearest(masks, p):
            best, bd = None, 1e9
            for m in masks:
                ys, xs = np.nonzero(m)
                d = float(np.min(np.hypot(xs - p[0], ys - p[1])))
                if d < bd:
                    best, bd = m, d
            return best, bd

        for a, b, name in jobs:
            if per_task.get(task, 0) >= cap:
                st["capped"] = st.get("capped", 0) + 1
                continue
            st["cand"] += 1
            if not name:
                st["no_name"] += 1
                continue
            L = a + BOUND  # label frame: Pick start, before the approach (object visible, 'where to go')
            if b not in fr or L not in fr or b >= len(Ts) or b >= len(z["end_pos"]):
                continue
            H, W = fr[b].shape[:2]
            arm = closing_arm(z, a, b)
            f = proj(K, dist, np.linalg.inv(Ts[b]), z["end_pos"][b][arm][None])
            mb = sam_masks(fr[b], name)  # grasp frame: only to know WHICH instance was grasped
            if f is None or not mb:
                st["no_mask"] += 1
                continue
            held, bd = nearest(mb, f[0])
            c_held = np.array(np.nonzero(held)[::-1], float).mean(1)
            ml = sam_masks(fr[L], name)  # label frame masks; the head is fixed, so the instance is at the same place
            if not ml:
                st["no_mask_label"] = st.get("no_mask_label", 0) + 1
                continue
            best, ld = nearest(ml, c_held)
            ok, why = quality(best, W, H)
            if not ok:
                st[why] = st.get(why, 0) + 1
                continue
            pt = top_centre(best)
            img_p = os.path.join(out, "frames", f"agb_{task}_{ep}_{L}.jpg")
            cv2.imwrite(img_p, fr[L])
            chk = os.path.join(out, "frames", f"agb_{task}_{ep}_{b}_grasp.jpg")  # check-only frame
            cv2.imwrite(chk, fr[b])
            r = PL.row(SRC, LIC, "head", img_p, W, H, pt, name, "obj_point", f"agb_t{task}_{ep}_{L}_obj",
                       extra={"task": task, "grasp_frame": b, "grasp_image": chk,
                              "flange_to_held_mask_px": round(bd, 1), "held_to_label_mask_px": round(ld, 1)})
            if r:
                rows.append(r)
                per_task[task] = per_task.get(task, 0) + 1
                st["kept"] += 1
    tr, g = GS.split(rows)
    for fn, rr in (("records.jsonl", tr), ("records_G.jsonl", g)):
        with open(os.path.join(out, fn), "a") as fh:
            fh.writelines(json.dumps(r) + "\n" for r in rr)
    st.update(rows_train=len(tr), rows_G=len(g))
    json.dump(st, open(os.path.join(out, "report.json"), "w"), indent=1)
    print(json.dumps(st))


if __name__ == "__main__":
    main(*sys.argv[1:5])
