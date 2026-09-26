"""Record builders: public robot data -> our training records (JSONL rows like harvest/teach_l8/dataset.py).

Rules (docs/research/cross_embodiment_data_use_2026-09-26.md 2): public samples never answer in OUR robot frame;
every request starts with 'source: <dataset>/<robot>' and 'frame: pixel | cam_<name> | base_<robot>'; the camera
intrinsics are written as text; frame-explicit control (C') uses our runtime answer schema unchanged, with the target in
THAT robot's base frame, and the frame tag only in the request (so a tag or pixel key in an answer is a leak).
The self-info block is generated from the robot description dict (dataset calibration + robot model), never by hand.
"""
from __future__ import annotations

import json

import numpy as np

# = harvest/astra_solo/prompts.ANSWER (test_our_answer_spec_is_the_runtime_one keeps them equal)
ANSWER = """
First assess: (1) what did your LAST command do? Compare the images with the measured TCP and pad gap; tell an observed failure from an uncertain result. (2) task_progress from visual evidence only (undo a step the images show was lost). Then give exactly one command.
Return JSON only: {"assessment": {"task_progress": {"verified_completed": [string], "currently_attempting": string, "remaining": [string]}, "execution_status": "not_started"|"progressing"|"failed"|"uncertain"|"recovered", "evidence": "<= 40 words", "evidence_view": "head"|"right_wrist"|"both", "confidence": "low"|"medium"|"high"}, "command": {"mode": "eef"|"edit"|"gripper"|"stop", "position_m": [x, y, z] (eef only), "delta_m": [dx, dy, dz] (edit only), "gripper": "keep"|"open"|"close" (eef / edit: after the move; gripper mode: open or close)}, "reason": "<= 30 words"}"""

FOREIGN_KEYS = ("frame", "point", "points", "xyz_cam", "uv", "pixel", "source")


def _cam_line(i: int, c: dict) -> str:
    if c.get("K") is None:  # route 4: no calibration shipped (and none made): say so, never invent numbers
        return f"- Image {i + 1}: {c['name']}, {c['W']}x{c['H']} px; camera: unknown (no calibration)."
    K = np.asarray(c["K"], float)
    s = (f"- Image {i + 1}: {c['name']}, {c['W']}x{c['H']} px, fx {K[0, 0]:.1f} fy {K[1, 1]:.1f} cx {K[0, 2]:.1f} "
         f"cy {K[1, 2]:.1f}")
    if c.get("T_base_cam") is None:
        return s + "; it moves with the hand (pose not given)."
    T = np.asarray(c["T_base_cam"], float)
    t, R = T[:3, 3], T[:3, :3]
    return s + (f"; at ({t[0]:.2f}, {t[1]:.2f}, {t[2]:.2f}) m, looking along ({R[0, 2]:+.2f}, {R[1, 2]:+.2f}, "
                f"{R[2, 2]:+.2f}); image right = ({R[0, 0]:+.2f}, {R[1, 0]:+.2f}, {R[2, 0]:+.2f}), image down = "
                f"({R[0, 1]:+.2f}, {R[1, 1]:+.2f}, {R[2, 1]:+.2f}).")


def header(robot: dict, frame: str) -> str:
    return f"source: {robot['source']}\nframe: {frame}\n"


def self_info(robot: dict) -> str:
    g, w = robot["gripper"], robot["workspace"]
    lines = [header(robot, f"base_{robot['name']}").rstrip("\n"),
             "ROBOT (generated from this robot's model and calibration)",
             f"- {robot['desc']}; you command its {robot['arm']} arm.",
             "- Robot frame: origin at the robot base, x forward, y to the robot's left, z up; positions in metres.",
             f"- Gripper: parallel two-finger; fully open gap {g['open_gap_m'] * 100:.1f} cm; TCP = midway between the "
             f"finger tips.",
             f"- TCP positions seen in this robot's data: x {w['x'][0]:.2f}..{w['x'][1]:.2f}, "
             f"y {w['y'][0]:.2f}..{w['y'][1]:.2f}, z {w['z'][0]:.2f}..{w['z'][1]:.2f} m.",
             "CAMERAS (from calibration; directions are unit vectors in the robot frame)"]
    lines += [_cam_line(i, c) for i, c in enumerate(robot["cameras"])]
    return "\n".join(lines) + "\n"


_TEXTS = {
    "above_target": lambda t, p: (f"move the TCP above the {t}", [f"lower to the {t} and close on it",
                                                                    f"carry it above the {p}",
                                                                    "put it down and release it"], []),
    "descend_close": lambda t, p: (f"lower to the {t} and close on it", [f"carry it above the {p}",
                                                                           "put it down and release it"], []),
    "reopen": lambda t, p: ("reopen the gripper: the close caught nothing", [f"move above the {t}",
                                                                              f"lower to the {t} and close on it",
                                                                              f"carry it above the {p}",
                                                                              "put it down and release it"], []),
    "carry_up": lambda t, p: (f"lift the {t} to carrying height", [f"carry it above the {p}",
                                                                   "put it down and release it"], [f"grasp the {t}"]),
    "carry_over": lambda t, p: (f"carry the {t} above the {p}", ["put it down and release it"], [f"grasp the {t}"]),
    "lower_open": lambda t, p: (f"lower the {t} onto the {p} and release it", [], [f"grasp the {t}"]),
    "retreat": lambda t, p: ("move the gripper up away from the released object", [],
                             [f"grasp the {t}", f"place the {t} on the {p}"]),
    "done": lambda t, p: ("task complete", [], [f"grasp the {t}", f"place the {t} on the {p}"]),
}


def _r3(p) -> list:
    return [round(float(v), 3) for v in p]


def command_of(seg: dict) -> dict:
    if seg["step"] == "done":
        return {"mode": "stop"}
    if seg["target"] is None:
        return {"mode": "gripper", "gripper": seg["gripper"]}
    return {"mode": "eef", "position_m": _r3(seg["target"]), "gripper": seg["gripper"]}


def control_record(robot: dict, seg: dict, k: int, tcp, opening_m: float, task: str, tgt: str, place: str,
                   history: list, first: bool, images: list, rid: str, extra: dict | None = None) -> dict:
    """One C' sample: request = self-info + task + NOW + history + our answer spec; answer = our schema."""
    doing, remaining, done = _TEXTS[seg["step"]](tgt, place)
    status = "not_started" if first else ("failed" if seg["step"] == "reopen" else "progressing")
    t = np.asarray(tcp, float)
    now = (f"\nTASK: {task}\nNOW\n- TCP at ({t[0]:.3f}, {t[1]:.3f}, {t[2]:.3f}) m; gripper opening "
           f"{opening_m * 100:.1f} cm.\nYOUR COMMANDS SO FAR (oldest first; results measured by the robot):\n"
           + ("\n".join(history[-10:]) if history else "(none yet)") + "\n")
    ev = f"TCP at ({t[0]:.3f}, {t[1]:.3f}, {t[2]:.3f}) m, gripper opening {opening_m * 100:.1f} cm"
    if seg["step"] == "reopen":
        ev += "; the gripper closed with nothing between the fingers"
    ans = {"assessment": {"task_progress": {"verified_completed": done, "currently_attempting": doing,
                                            "remaining": remaining},
                          "execution_status": status, "evidence": ev, "evidence_view": "both", "confidence": "high"},
           "command": command_of(seg), "reason": f"Next: {doing}."}
    rec = {"id": rid, "kind": "control_xemb", "source": robot["source"], "frame": f"base_{robot['name']}",
           "step": seg["step"], "t": int(k), "prompt": self_info(robot) + now + ANSWER, "images": list(images),
           "answer": json.dumps(ans)}
    if extra:
        rec.update(extra)
    return rec


_ASK = {
    "ee_point": "Point to the {arm} gripper's TCP (midway between the finger tips) in image {i}.",
    "ee_point_detected": "Point to the {arm} robot gripper in image {i}.",
    "ee_trace": ("Where will the {arm} gripper go? Give its path in image {i} as up to 5 points, from where it is now to "
                 "where it releases the object."),
    "obj_point": "Point to the {name} in image {i}.",
    "place_point": "Point to the {name} (where the object will be put) in image {i}.",
    "obj_center_cam": "What is the 3D centre of the {name} in the {cam} frame (x right, y down, z forward, metres)?",
    "ee_approach_cam": ("Which way does the {arm} gripper point (from the wrist toward the finger tips), as a unit "
                        "vector in the {cam} frame (x right, y down, z forward)?"),
    "table_plane_cam": ("Give the table-top plane in the {cam} frame (x right, y down, z forward) as a unit normal "
                        "n (pointing up, away from the table) and offset d in metres with n . p = d."),
}


def _qa(robot, kind, frame, cam, image, rid, ans, name=""):
    c = robot["cameras"][cam]
    q = (header(robot, frame) + "CAMERAS\n" + _cam_line(0, c) + "\n"
         + _ASK[kind].format(arm=robot["arm"], name=name, i=1, cam=frame) + "\nReturn JSON only.")
    return {"id": rid, "kind": "qa_xemb", "qa_kind": kind, "source": robot["source"], "frame": frame, "prompt": q,
            "images": [image], "answer": json.dumps(ans)}


def cam_frame(robot: dict, cam: int) -> str:
    return "cam_" + robot["cameras"][cam]["name"].replace(" camera", "").replace(" ", "_")


def qa_point(robot, kind, uv, cam, image, rid, name=""):
    return _qa(robot, kind, "pixel", cam, image, rid, {"point": [int(round(uv[0])), int(round(uv[1]))]}, name)


def qa_trace(robot, uvs, cam, image, rid, arm="right"):
    """Route 1/2 (pixel only): the gripper path as up to 5 pixel points (MolmoAct trace, in pixels of this image)."""
    r = dict(robot, arm=robot.get("arm", arm) if "arm" in robot else arm)
    r["arm"] = arm
    ans = {"trace": [[int(round(u)), int(round(v))] for u, v in uvs]}
    return _qa(r, "ee_trace", "pixel", cam, image, rid, ans)


def qa_xyz(robot, kind, xyz, cam, image, rid, name=""):
    key = "xyz_cam" if kind == "obj_center_cam" else "dir_cam"
    return _qa(robot, kind, cam_frame(robot, cam), cam, image, rid, {key: _r3(xyz)}, name)


def qa_plane(robot, n, d, cam, image, rid):
    return _qa(robot, "table_plane_cam", cam_frame(robot, cam), cam, image, rid,
               {"normal_cam": _r3(n), "d_m": round(float(d), 3)})


def leak_flags(answer_text: str, our_box: dict) -> list:
    """Frame-leak check of an answer to one of OUR runtime requests (no source/frame line): foreign keys from the
    public formats, or an eef target outside our workspace box (another robot's frame)."""
    out = []
    try:
        d = json.loads(answer_text[answer_text.find("{"): answer_text.rfind("}") + 1])
    except Exception:
        return ["not_json"]
    for k in FOREIGN_KEYS:
        if k in d or k in (d.get("command") or {}):
            out.append(f"foreign_key:{k}")
    c = d.get("command") or {}
    p = c.get("position_m")
    if c.get("mode") == "eef" and isinstance(p, list) and len(p) == 3:
        margin = 0.05
        if not all(our_box[a][0] - margin <= float(v) <= our_box[a][1] + margin for a, v in zip("xyz", p)):
            out.append("outside_box")
    return out
