"""Prompt of the Astra-solo arm ("astra-solo@v2"): synchronous direct control (GPT-as-Policy direct / eef style), with
the v2 content that the E-Astra-motion probe and the prompt health check found missing or useful (docs/stage3/results/
prompt_health.md F1-F7, pitfall P88): operational definitions of the judged concepts (the COUPLE_DEFS wording of
tools/prompt_health/variants.py), the robot-frame axis line, camera poses (looking along / image right / image down in
the robot frame, as in the probe), a legend that describes exactly the drawn elements (grid, TCP ring, drop line; no
arrows are drawn), and the measured history of the commands. Layout: static part first (cacheable prefix), then NOW
and the history, then the answer form. Images: 1 = head (overlay), 2 = right wrist (no drawing); the idle left wrist
is not sent (probe G1: head + right wrist 26/40 vs all three 27/40).
"""
from __future__ import annotations

import hashlib

import numpy as np

from ..astra_motion.executor import SAFE_DZ, SAFE_X, SAFE_Y
from ..astra_motion.prompts import CAM, OBJ_DESC, OBJ_NAME, place_rule

VERSION = "astra-solo@v2"

STATIC = """You control the right arm of a humanoid robot (ROBOTIS AI Worker FFW-SG2) at a table, in simulation. You see its cameras and give one end-effector command at a time. The robot waits for your answer: each command is executed completely (the arm moves, then the gripper acts), and then you are called again with new images and the measured result. There is no time pressure between calls, so take the care you need; but the number of calls and the robot's motion time are limited (see NOW).

FRAME AND UNITS
- Robot frame: origin at the robot base, x forward (away from the robot), y to the robot's left, z up; positions in metres.
- Table top surface: z = {tz:.3f} m. The code keeps the TCP inside x {x0:.2f}..{x1:.2f}, y {y0:.2f}..{y1:.2f}, z {z0:.3f}..{z1:.3f} m (targets beyond are clipped, and you are told).

GRIPPER
- It points straight down; its two fingers close along the robot x axis. TCP = the point midway between the finger pads. The pads are 4.5 cm long (from 2.25 cm above to 2.25 cm below the TCP); the gripper body starts 2.5 cm above the TCP. Fully open pad gap 10.7 cm; a close with nothing between the pads ends near {wc:.1f} cm.
- Grasping an upright object of height h that stands on the table: move the TCP about 10 cm above its top, centred over it; then straight down to z = table + h - 0.02 (the pads around its upper part); then close.
- Putting a held object down: carry it high enough to clear everything, move above the target, lower until the object's bottom is about 1 cm above the target surface (TCP z = surface + h - 0.02 + 0.01), open, then move up about 10 cm, then answer stop.

COMMANDS (fixed code executes them; you never command joints)
- eef: move the TCP in a straight line (smooth start and stop, about 8 cm/s on average) to the absolute position_m [x, y, z]; then apply gripper: close (0.6 s), open (0.5 s) or keep. Any distance.
- edit: move by delta_m [dx, dy, dz] from the current target (at most 0.10 m; a longer delta is shortened); then apply gripper. Use it for small corrections seen in the wrist view.
- gripper: open or close in place.
- stop: the task is complete (or cannot be completed); the episode ends.
Moves are straight lines: lift before moving sideways over objects.

CAMERAS (directions are unit vectors in the robot frame)
- Image 1: head camera, fixed on the robot head, {head}
- Image 2: RIGHT wrist camera, moves with the right hand and looks down between the fingers; its pose now is under NOW.

HEAD IMAGE OVERLAY (drawn by code from the camera calibration and the robot's own joint angles, never from object positions)
- WHITE GRID: lines lying ON THE TABLE SURFACE (z = table top) every 5 cm, brighter every 10 cm, labelled with robot-frame metres (x=0.40, y=-0.20). An object standing on the table meets the grid at its base: read its (x, y) at the centre of its base footprint, not at its top (the top looks shifted because it is higher).
- White ring with a black outline: the TCP now.
- DROP LINE: a white dotted line from the TCP straight down to the table, ending in a white dot = the table point directly below the TCP. When that dot is at the centre of an object's base, the gripper is directly above the object.
- The wrist image has no drawing.

DEFINITIONS (for your assessment)
- grasped = both finger pads are CLOSED on the object (little or no gap between each pad and the object) so that it moves with the gripper; open fingers with the object between them, fingers closed next to or in front of it, or an object that merely overlaps the fingers in a view are NOT grasped. After a close, a pad gap well above {wc:.1f} cm means the pads stopped on something.
- released = the pads are open and the object no longer moves with the gripper.
- placed = the object rests upright on its target and is released.
- contact = a finger or pad touches the object.
- The head view alone can make the fingers look as if they hold an object when they do not: verify contact, grasp and release in the right wrist view (and the pad gap).

TASK: {instruction}
Success = the {tgt_name} stands upright {place_rule}, released by the gripper, for 1 s. Then answer stop.
OBJECTS (name: shape; other objects on the table are obstacles, do not touch them)
{objects}
"""

NOW = """
NOW
- Right wrist camera (image 2): {wrist}
- TCP at ({tcp[0]:.3f}, {tcp[1]:.3f}, {tcp[2]:.3f}) m; pad gap {gap:.1f} cm.
- Call {i} of at most {n}; robot motion time used {t_used:.0f} s of {t_max:.0f} s.
YOUR COMMANDS SO FAR (oldest first; results measured by the robot):
{history}
"""

ANSWER = """
First assess: (1) what did your LAST command do? Compare the images with the measured TCP and pad gap; tell an observed failure from an uncertain result. (2) task_progress from visual evidence only (undo a step the images show was lost). Then give exactly one command.
Return JSON only: {"assessment": {"task_progress": {"verified_completed": [string], "currently_attempting": string, "remaining": [string]}, "execution_status": "not_started"|"progressing"|"failed"|"uncertain"|"recovered", "evidence": "<= 40 words", "evidence_view": "head"|"right_wrist"|"both", "confidence": "low"|"medium"|"high"}, "command": {"mode": "eef"|"edit"|"gripper"|"stop", "position_m": [x, y, z] (eef only), "delta_m": [dx, dy, dz] (edit only), "gripper": "keep"|"open"|"close" (eef / edit: after the move; gripper mode: open or close)}, "reason": "<= 30 words"}"""

REPAIR = "\n\nYOUR PREVIOUS ANSWER WAS INVALID: {errors}\nAnswer again with JSON only, in the required format."
IMAGE_LABELS = ("head camera", "right wrist camera")
TEMPLATES = {"static": STATIC, "now": NOW, "answer": ANSWER, "repair": REPAIR, "cam": CAM,
             "labels": "|".join(IMAGE_LABELS), "version": VERSION}
PROMPT_ID = hashlib.sha256("\n".join(TEMPLATES[k] for k in sorted(TEMPLATES)).encode()).hexdigest()[:12]


def _cam(c) -> str:
    return CAM.format(W=c.W, H=c.H, fx=c.fx, fy=c.fy, cx=c.cx, cy=c.cy, t=np.asarray(c.t, float).tolist(),
                      R=np.asarray(c.R, float).tolist())


def static(info: dict, head, table_z: float, w_close: float) -> str:
    objs = [info["tgt"], info["place"]] + [k for k in info["present"] if k not in (info["tgt"], info["place"])]
    lines = "\n".join(f"- {OBJ_NAME.get(k, k)}: {OBJ_DESC.get(k, 'object')}"
                      + (" (the object to move)" if k == info["tgt"] else "")
                      + (" (where to put it)" if k == info["place"] else " (obstacle)" if k != info["tgt"] else "")
                      for k in objs)
    return STATIC.format(tz=table_z, x0=SAFE_X[0], x1=SAFE_X[1], y0=SAFE_Y[0], y1=SAFE_Y[1],
                         z0=table_z + SAFE_DZ[0], z1=table_z + SAFE_DZ[1], wc=w_close * 100, head=_cam(head),
                         instruction=info["instruction"], tgt_name=OBJ_NAME[info["tgt"]],
                         place_rule=place_rule(info["place"], OBJ_NAME[info["place"]]), objects=lines)


def now(wrist, tcp, gap_m: float, i: int, n: int, t_used: float, t_max: float, history: list) -> str:
    return NOW.format(wrist=_cam(wrist), tcp=np.asarray(tcp, float).tolist(), gap=gap_m * 100, i=i, n=n,
                      t_used=t_used, t_max=t_max, history="\n".join(history[-10:]) if history else "(none yet)")


def describe(cmd: dict) -> str:
    m = cmd["mode"]
    if m == "eef":
        p = cmd["position_m"]
        return f"eef to ({p[0]:.3f}, {p[1]:.3f}, {p[2]:.3f}), gripper {cmd['gripper']}"
    if m == "edit":
        d = cmd["delta_m"]
        return f"edit by ({d[0]:+.3f}, {d[1]:+.3f}, {d[2]:+.3f}), gripper {cmd['gripper']}" + \
            (" [delta shortened to 0.10 m]" if cmd.get("scaled") else "")
    if m == "gripper":
        return f"gripper {cmd['gripper']}"
    return "stop"
