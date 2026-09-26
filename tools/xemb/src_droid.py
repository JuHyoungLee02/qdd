"""DROID 1.0.1 (lerobot/droid_1.0.1, LeRobot v3.0; CC BY 4.0) -> C' (frame-explicit control, `frame: base_franka_droid`).

Real Franka Panda + Robotiq 2F-85, 15 Hz. Per episode: `observation.state.cartesian_position` (EE xyz + euler xyz in
the robot base frame), `action.gripper_position` (command, 0 open .. 1 closed), `observation.state.gripper_position`
(measured), `language_instruction`. Only pick-and-place instructions whose object and receptacle names parse
(names_of) are used, so the answers never carry fallback names ('the object').
Cameras: the lerobot port's `date` field repeats the collector id, so episodes cannot be joined to the 2025 improved
calibration (KarlP/droid, keyed by '<lab>+<collector>+<date>'); the shipped per-episode extrinsics are the original
noisy ones -> images are given as `camera: unknown (no calibration)` (route 4). Exterior camera 1 + wrist camera.
Steps: xemb.steps.segment on the EE path; closed = commanded close (> 0.5); held = measured opening stopped short of
fully closed (< HELD_GP) while closed. Top-down filter: approach tilt at the grasp (gripper z vs -z) <= TOPDOWN_DEG.
usage (pod): python -m xemb.src_droid DROID_ROOT DATA_FILE OUT_DIR   (uses whichever video files are on disk)
"""
from __future__ import annotations

import json
import os
import re
import sys

import numpy as np

from . import fmt as F
from . import steps as S

HELD_GP = 0.95
TOPDOWN_DEG = 30.0
FPS = 15
_OBJ = r"(?:the |a |an )?(?P<obj>[a-z0-9 \-']+?)"
_REC = r"(?:the |a |an )?(?P<rec>[a-z0-9 \-']+?)"
_PREP = r"(?:in|into|on|onto|inside|on top of)"
_PATS = [re.compile(rf"^(?:put|place|drop) {_OBJ}(?: from [a-z0-9 \-']+?)? {_PREP} {_REC}$"),
         re.compile(rf"^(?:pick up|pick|grab|take) {_OBJ}(?: from [a-z0-9 \-']+?)? and (?:put|place|drop) "
                    rf"(?:it|them) {_PREP} {_REC}$"),
         re.compile(rf"^move {_OBJ} (?:in|into|onto|inside) {_REC}$")]
_BAD = {"left", "right", "table", "side", "front", "back", "middle", "center", "other side", "top"}


def names_of(instr: str):
    s = (instr or "").strip().lower().rstrip(".").strip()
    for p in _PATS:
        m = p.match(s)
        if m:
            obj, rec = m.group("obj").strip(), m.group("rec").strip()
            if obj and rec and rec not in _BAD and obj not in ("it", "them") and len(obj.split()) <= 6:
                return obj, rec
    return None


def _R_xyz(e):
    cx, cy, cz = np.cos(e)
    sx, sy, sz = np.sin(e)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx  # scipy R.from_euler("xyz") (extrinsic x, then y, then z)


def tilt_deg_euler(e) -> float:
    z = _R_xyz(np.asarray(e, float))[:, 2]
    return float(np.degrees(np.arccos(np.clip(-z[2], -1, 1))))


def _frames(video, want):
    """{global frame index: BGR} for the wanted indices (sequential decode; 15 fps; index = round(t * FPS))."""
    import av
    out, want = {}, set(want)
    if not want:
        return out
    last = max(want)
    with av.open(video) as c:
        for fr in c.decode(video=0):
            i = int(round(float(fr.pts * fr.time_base) * FPS))
            if i in want:
                out[i] = fr.to_ndarray(format="bgr24")
            if i >= last:
                break
    return out


def convert(root, file_index, out, max_eps=10 ** 9):
    import cv2
    import pyarrow.parquet as pq
    os.makedirs(os.path.join(out, "frames"), exist_ok=True)
    cols = ["episode_index", "frame_index", "language_instruction", "observation.state.cartesian_position",
            "observation.state.gripper_position", "action.gripper_position", "is_episode_successful"]
    d = pq.read_table(os.path.join(root, f"data/chunk-000/file-{file_index:03d}.parquet"), columns=cols)
    ep_meta = pq.read_table(os.path.join(root, "meta/episodes/chunk-000/file-000.parquet")).to_pylist()
    meta = {m["episode_index"]: m for m in ep_meta}
    ei = np.asarray(d.column("episode_index").to_pylist())
    cart = np.asarray(d.column("observation.state.cartesian_position").to_pylist(), float)
    gp = np.asarray(d.column("observation.state.gripper_position").to_pylist(), float).reshape(-1)
    ga = np.asarray(d.column("action.gripper_position").to_pylist(), float).reshape(-1)
    instr = d.column("language_instruction").to_pylist()
    succ = d.column("is_episode_successful").to_pylist()
    lo, hi = np.percentile(cart[:, :3], 1, 0), np.percentile(cart[:, :3], 99, 0)
    robot = {"name": "franka_droid", "source": "droid/franka", "arm": "only",
             "desc": "Franka Emika Panda 7-DoF arm with a Robotiq 2F-85 gripper on a fixed base (DROID, real)",
             "gripper": {"open_gap_m": 0.085}, "workspace": {"x": [lo[0], hi[0]], "y": [lo[1], hi[1]],
                                                             "z": [lo[2], hi[2]]},
             "cameras": [{"name": "external camera", "W": 320, "H": 180, "K": None},
                         {"name": "wrist camera", "W": 320, "H": 180, "K": None}]}
    plan, stats = [], {"episodes": 0, "success": 0, "pickplace_names": 0, "has_grasp": 0, "topdown": 0, "tilts": []}
    for e in sorted(set(ei.tolist()))[:max_eps]:
        idx = np.nonzero(ei == e)[0]
        stats["episodes"] += 1
        if not succ[idx[0]]:
            continue
        stats["success"] += 1
        nm = names_of(instr[idx[0]])
        if nm is None:
            continue
        stats["pickplace_names"] += 1
        ee, closed = cart[idx, :3], ga[idx] > 0.5
        held = closed & (gp[idx] < HELD_GP) & (gp[idx] > 0.05)
        segs = S.segment(ee, closed, held)
        dc = [s for s in segs if s["step"] == "descend_close"]
        if not dc or "lower_open" not in [s["step"] for s in segs]:
            continue
        stats["has_grasp"] += 1
        tilt = tilt_deg_euler(cart[idx[dc[0]["t1"]], 3:])
        stats["tilts"].append(tilt)
        if tilt > TOPDOWN_DEG:
            continue
        stats["topdown"] += 1
        plan.append((e, idx, nm, segs, instr[idx[0]]))
    recs = []
    cams = ("exterior_1_left", "wrist_left")

    def vpath(c, fi):
        return os.path.join(root, f"videos/observation.images.{c}/chunk-000/file-{fi:03d}.mp4")
    # each camera's episodes live in their own video files (indices differ per camera): keep episodes whose files
    # for both cameras are on disk, then decode only the wanted frames of each file
    plan = [p for p in plan if all(meta[p[0]][f"videos/observation.images.{c}/chunk_index"] == 0 and os.path.exists(
        vpath(c, meta[p[0]][f"videos/observation.images.{c}/file_index"])) for c in cams)]
    stats["in_video_files"] = len(plan)
    want = {c: {} for c in cams}  # (episode, k) -> (video file, frame index in that file)
    for e, idx, nm, segs, _ in plan:
        for c in cams:
            fi = meta[e][f"videos/observation.images.{c}/file_index"]
            f0 = meta[e][f"videos/observation.images.{c}/from_timestamp"]
            for s in segs:
                for k in S.sample_frames(s, 2):
                    want[c][(e, k)] = (fi, int(round(f0 * FPS)) + k)
    fr = {c: {} for c in cams}
    for c in cams:
        for fi in sorted({v[0] for v in want[c].values()}):
            got = _frames(vpath(c, fi), {v[1] for v in want[c].values() if v[0] == fi})
            fr[c].update({(fi, i): im for i, im in got.items()})
    for e, idx, nm, segs, task in plan:
        hist = []
        for si, s in enumerate(segs):
            for k in S.sample_frames(s, 2):
                if any(want[c][(e, k)] not in fr[c] for c in cams):
                    continue
                ims = []
                for c in cams:
                    p = os.path.join(out, "frames", f"droid_{e:06d}_{c}_{k:04d}.jpg")
                    cv2.imwrite(p, fr[c][want[c][(e, k)]])
                    ims.append(p)
                opening = float(np.clip(1 - gp[idx[k]], 0, 1)) * robot["gripper"]["open_gap_m"]
                r = F.control_record(robot, s, k, cart[idx[k], :3], opening, task, nm[0], nm[1], hist,
                                     first=(si == 0 and k == s["t0"]), images=ims,
                                     rid=f"droid_{e}_{k}_{s['step']}")
                recs.append(r)
            if s["target"] is not None:
                t = s["target"]
                hist.append(f"{len(hist) + 1}: eef to ({t[0]:.3f}, {t[1]:.3f}, {t[2]:.3f}), gripper {s['gripper']} -> "
                            f"done; TCP now ({t[0]:.3f}, {t[1]:.3f}, {t[2]:.3f})")
            elif s["gripper"]:
                hist.append(f"{len(hist) + 1}: gripper {s['gripper']} -> done")
    with open(os.path.join(out, "records_C.jsonl"), "w") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")
    T = np.array(stats.pop("tilts"))
    stats.update(n_C=len(recs), clean=sum(not F.leak_flags(r["answer"], {"x": [-9, 9], "y": [-9, 9], "z": [-9, 9]})
                                          for r in recs),
                 grasp_tilt={"n": int(len(T)), "le30": round(float((T <= 30).mean()), 3) if len(T) else None,
                             "le45": round(float((T <= 45).mean()), 3) if len(T) else None,
                             "median": round(float(np.median(T)), 1) if len(T) else None},
                 C_by_step={k: sum(r["step"] == k for r in recs) for k in sorted({r["step"] for r in recs})})
    json.dump(stats, open(os.path.join(out, "report.json"), "w"), indent=1)
    return stats


if __name__ == "__main__":
    print(json.dumps(convert(sys.argv[1], int(sys.argv[2]), sys.argv[3]), indent=1))
