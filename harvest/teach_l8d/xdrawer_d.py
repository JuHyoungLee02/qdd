"""L8-X drawer in the D format (point + intent + depth, d-min; user-log 159): "d-min@v1+x2" (prereg_l8x_tasks
change 13; pure).

The model points in image 1 (head, ring only) at the handle and names an intent; code turns it into the TCP target
from the head depth and the camera calibration. The drawer adds the +x2 fields of nd-xyz@v1+x2 (orient, width_m)
and four drawer intents (the pull direction = towards the robot, -x in the robot frame):
  front = the TCP 10.7 cm in front of the pointed spot on the handle (towards the robot), gripper pointing forward;
  grasp = the TCP 0.7 cm in front of that spot (the pads around the bar), gripper pointing forward;
  pull  = 1 cm towards the robot from where the TCP is now (point_2d not needed);
  back  = 3.5 cm towards the robot from where the TCP is now (point_2d not needed).
The request is made from the saved nd-xyz@v1+x2 request by swapping the eef bullet for the point bullet + the POINT
block and the answer form (the history keeps the executed eef wording, as min_format.d_text does for d-min).
Labels (the truth plan's step -> the D command) are made after collection from each call's saved head depth,
cams.json and the ground truth (handle bar centre, TCP): a point label is kept only when the resolver turns the
pixel back into the truth target within TOL_M (else label_missing, dropped from training)."""
from __future__ import annotations

import hashlib
import json

import numpy as np

from ..astra_motion import geometry as G
from ..astra_solo import resolve as RS
from . import xdrawer as XD
from . import xdrawer_prompt as XP

VERSION = "d-min@v1+x2"
INTENTS = ("front", "grasp", "pull", "back")
U = np.array([-1.0, 0.0, 0.0])  # opening direction (towards the robot)
FACE_M = 0.005  # bar front face = bar centre + 5 mm towards the robot (bars ~1 cm)
TOL_M = 0.010
WIN = 2  # the resolver takes the nearest-to-the-robot depth point in a (2 WIN + 1)^2 window around the pixel

_EEF = XP.STATIC[XP.STATIC.index("- eef: move the TCP"):].split("\n", 1)[0]
POINT_BULLET = ("- point: move the TCP in a straight line (smooth start and stop, about 8 cm/s on average) to the "
                "target made from point_2d and intent (and turn the gripper to orient); then apply gripper: close "
                "(0.6 s), open (0.5 s) or keep.")
POINT_BLOCK = """POINT, THEN ACT (you never compute target coordinates)
- You POINT in image 1 (the head camera) at the spot the gripper should go to, and choose an intent. Code measures the rest from the head camera's depth and its calibration.
- point_2d = [x, y] in image 1 on a 0-1000 scale: x from 0 (left edge) to 1000 (right edge), y from 0 (top edge) to 1000 (bottom edge). Point at the handle bar itself (the middle of its visible length).
- intent (the drawer opens towards the robot):
  front = the TCP about 10 cm in front of the pointed spot (towards the robot), at its height;
  grasp = the TCP just in front of the pointed spot, the pads around the bar;
  pull  = 1 cm towards the robot from where the TCP is now (point_2d not needed);
  back  = 3.5 cm towards the robot from where the TCP is now (point_2d not needed).

"""
ANSWER = XP.ANSWER.replace(
    '"mode": "eef"|"edit"|"gripper"|"stop", "position_m": [x, y, z] (eef only), "orient": "down"|"front" (eef only; '
    'omit to keep), ',
    '"mode": "point"|"edit"|"gripper"|"stop", "point_2d": [x, y] (point only; 0-1000 in image 1), "intent": '
    '"front"|"grasp"|"pull"|"back" (point only), "orient": "down"|"front" (point only; omit to keep), ').replace(
    "(eef / edit: after the move;", "(point / edit: after the move;")
assert ANSWER != XP.ANSWER and '"intent"' in ANSWER and "(point / edit" in ANSWER
TEMPLATES = {"bullet": POINT_BULLET, "block": POINT_BLOCK, "answer": ANSWER, "base": XP.PROMPT_ID, "version": VERSION}
PROMPT_ID = hashlib.sha256("\n".join(TEMPLATES[k] for k in sorted(TEMPLATES)).encode()).hexdigest()[:12]


def d_text(x2: str) -> str:
    """nd-xyz@v1+x2 request -> d-min@v1+x2 request of the same state."""
    if x2.count(_EEF) != 1 or x2.count(XP.ANSWER) != 1 or x2.count("FRAME AND UNITS") != 1:
        raise ValueError("not an nd-xyz@v1+x2 request")
    t = x2.replace(_EEF, POINT_BULLET).replace("FRAME AND UNITS", POINT_BLOCK + "FRAME AND UNITS", 1)
    return t.replace(XP.ANSWER, ANSWER)


def _pixel_point(cam, depth, point_2d):
    """The base-frame depth point at the pixel: of the valid points in the window, the one nearest to the robot
    (smallest x: the bar in front of the drawer face behind it); None when the window has no depth."""
    iu, iv = RS.to_pixel(point_2d, cam.W, cam.H)
    P = RS.depth_points(cam, depth)[max(iv - WIN, 0):iv + WIN + 1, max(iu - WIN, 0):iu + WIN + 1].reshape(-1, 3)
    P = P[np.isfinite(P).all(1)]
    return None if len(P) == 0 else P[int(np.argmin(P[:, 0]))]


def resolve(cam, depth, cmd: dict, tcp):
    """D command -> TCP target (np.ndarray) or None (no depth at the pointed pixel)."""
    it = cmd["intent"]
    tcp = np.asarray(tcp, float)
    if it == "pull":
        return tcp + U * XD.FRONT_PULL
    if it == "back":
        return tcp + U * XD.FRONT_RETREAT
    P = _pixel_point(cam, depth, cmd["point_2d"])
    if P is None:
        return None
    g = P + U * (XD.FRONT_GRASP - FACE_M)
    return g + U * XD.FRONT_BACK if it == "front" else g


def label(step: str, xyz_cmd: dict, gt: dict, cam, depth):
    """(D command | None, meta). None = no verified pixel for a point step (label_missing)."""
    tcp = np.asarray(gt["tcp"], float)
    if step in ("pull", "retreat"):
        c = {"mode": "point", "point_2d": None, "intent": "pull" if step == "pull" else "back", "orient": "front",
             "gripper": "keep"}
        return c, {"err_mm": round(float(np.linalg.norm(resolve(cam, depth, c, tcp) - xyz_cmd["position_m"])) * 1e3, 1)}
    if step not in ("front_of_handle", "insert"):
        return dict(xyz_cmd), {}  # gripper (preshape / close / reopen / release) and stop: unchanged
    face = np.asarray(gt["handle"], float) + U * FACE_M
    want = np.asarray(xyz_cmd["position_m"], float)
    u, v, z = G.project(cam, face)
    if z <= 0 or not (0 <= u < cam.W and 0 <= v < cam.H):
        return None, {"reason": "outside"}
    intent = "front" if step == "front_of_handle" else "grasp"
    best = None
    for dv in (0.0, -1.0, 1.0, -2.0, 2.0):
        c = {"mode": "point", "point_2d": RS.to_scaled(u, v + dv, cam.W, cam.H), "intent": intent, "orient": "front",
             "gripper": "keep"}
        tg = resolve(cam, depth, c, tcp)
        if tg is None:
            continue
        e = float(np.linalg.norm(tg - want))
        if best is None or e < best[1]:
            best = (c, e)
        if e <= TOL_M:
            return c, {"err_mm": round(e * 1e3, 1), "dv": dv}
    return None, {"reason": "no pixel within tolerance", "best_err_mm": None if best is None else round(best[1] * 1e3, 1)}


def d_answer(xyz_answer: str, d_cmd: dict) -> str:
    a = json.loads(xyz_answer)
    return json.dumps(dict(a, command=d_cmd))


def build(root: str, out_dir: str, split: str) -> dict:
    """b3d rows in the D format (min_format.row d-min layout: ring head + wrist, the call's clean head depth), from
    collected dr__ episodes; train rows need a verified label and get the L8 repeats (perturbed prev kind); no aux."""
    import os
    from collections import Counter

    from ..teach_l8.dataset import IMAGE_FILES, episode_dirs, repeat_of
    from .dataset import load_rows
    train = split == "train"
    rows, stat = [], Counter()
    for d in episode_dirs(root):
        for r in load_rows(d, split):
            cam = G.Cam.from_json(json.load(open(r["cams_path"]))["head"])
            depth = np.load(r["depth_path"])["depth"]
            xyz = json.loads(r["answer"])["command"]
            c, meta = label(r["step"], xyz, r["gt"], cam, depth)
            miss = c is None
            stat["missing" if miss else "ok"] += 1
            if miss and train:
                continue
            x2 = open(os.path.join(r["call_dir"], "prompt_v2.txt"), encoding="utf-8").read()
            p = os.path.join(out_dir, "prompts_d_x2", r["id"] + ".txt")
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write(d_text(x2))
            x = dict(r, kind="control", arm="d-min", prompt_path=p, prompt_id=PROMPT_ID, prompt_version=VERSION,
                     images=[os.path.join(r["call_dir"], "img1_head_ring.png"),
                             os.path.join(r["call_dir"], IMAGE_FILES[1])],
                     answer=r["answer"] if miss else d_answer(r["answer"], c), xyz_answer=r["answer"],
                     label_missing=miss, pt_meta=meta, d_mode="clean")
            rows += [x] * (repeat_of(x) if train else 1)
    name = f"{split}_d-min_x2"
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, name + ".jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for x in rows:
            f.write(json.dumps(x) + "\n")
    counts = {"rows": len(rows), "labels": dict(stat), "by_step": dict(Counter(x["step"] for x in rows)),
              "prompt_id": PROMPT_ID}
    with open(os.path.join(out_dir, name + ".counts.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(counts, f, indent=1)
    return counts
