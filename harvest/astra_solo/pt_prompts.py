"""Prompt of the point-then-act interface ("astra-solo-pt@v1", canon §97 보충 2): astra-solo@v2 (prompts.py) with the
metric-coordinate burden removed from the answer. The model POINTS at the thing the gripper should go to in image 1
and names a height intent; code turns that into the TCP target from the head depth and the camera calibration
(resolve.py). Kept from v2 (canon §97: robot self-information stays): the frame, table height and workspace box, the
gripper geometry, the camera poses, the overlay legend (the images are the same as v2's), the definitions, the task,
the object list with sizes, NOW (wrist pose, measured TCP and pad gap, limits) and the measured history. The grasp /
place recipes are restated as intents. Coordinates: 0-1000 scale (x right, y down) -- the grounding convention of
Qwen3-VL; `px_variant()` rewrites a prompt to integer pixel coordinates (a wording check, prereg §4)."""
from __future__ import annotations

import hashlib

from ..astra_motion.executor import SAFE_DZ, SAFE_X, SAFE_Y
from ..astra_motion.prompts import CAM, OBJ_DESC, OBJ_NAME, place_rule
from . import prompts as V2

VERSION = "astra-solo-pt@v1"

STATIC = """You control the right arm of a humanoid robot (ROBOTIS AI Worker FFW-SG2) at a table, in simulation. You see its cameras and give one command at a time. The robot waits for your answer: each command is executed completely (the arm moves, then the gripper acts), and then you are called again with new images and the measured result. There is no time pressure between calls, so take the care you need; but the number of calls and the robot's motion time are limited (see NOW).

POINT, THEN ACT (you never compute target coordinates)
- You POINT in image 1 (the head camera) at the thing the gripper should go to, and choose a height. Code measures the rest from the head camera's depth and its calibration: the table plane, the pointed object's footprint centre and top height, and how high the held object hangs below the TCP.
- point_2d = [x, y] in image 1 on a 0-1000 scale: x from 0 (left edge) to 1000 (right edge), y from 0 (top edge) to 1000 (bottom edge). Point at a spot ON the object you mean (its top or the middle of its visible body); the code finds the whole object around that spot. A point on bare table means that table spot.
- height:
  above = the TCP about 8 cm above the pointed object's top, centred over it (while holding an object: the held object's bottom 8 cm above it);
  grasp = the TCP 2 cm below the pointed object's top, centred on it (the pads around its upper part);
  place = while holding an object: its bottom about 1 cm above the pointed object's top surface;
  lift  = straight up to the carrying height (22 cm above the table) where the TCP is now (point_2d not needed).

FRAME AND UNITS (for the measured numbers you are given)
- Robot frame: origin at the robot base, x forward (away from the robot), y to the robot's left, z up; positions in metres.
- Table top surface: z = {tz:.3f} m. The code keeps the TCP inside x {x0:.2f}..{x1:.2f}, y {y0:.2f}..{y1:.2f}, z {z0:.3f}..{z1:.3f} m (targets beyond are clipped, and you are told).

GRIPPER
- It points straight down; its two fingers close along the robot x axis. TCP = the point midway between the finger pads. The pads are 4.5 cm long (from 2.25 cm above to 2.25 cm below the TCP); the gripper body starts 2.5 cm above the TCP. Fully open pad gap 10.7 cm; a close with nothing between the pads ends near {wc:.1f} cm.
- Grasping an upright object that stands on the table: point at it with height above; then point at it with height grasp and gripper close.
- Putting a held object down: lift if it is low; point at the target with height above; then point at the target with height place and gripper open; then move up about 10 cm (edit), then answer stop.

COMMANDS (fixed code executes them; you never command joints)
- point: move the TCP in a straight line (smooth start and stop, about 8 cm/s on average) to the target made from point_2d and height; then apply gripper: close (0.6 s), open (0.5 s) or keep.
- edit: move by delta_m [dx, dy, dz] (robot frame, metres) from the current target (at most 0.10 m; a longer delta is shortened); then apply gripper. Use it for small corrections seen in the wrist view.
- gripper: open or close in place.
- stop: the task is complete (or cannot be completed); the episode ends.
Moves are straight lines: lift before moving sideways over objects.

CAMERAS (directions are unit vectors in the robot frame)
- Image 1: head camera, fixed on the robot head, {head}
- Image 2: RIGHT wrist camera, moves with the right hand and looks down between the fingers; its pose now is under NOW.

HEAD IMAGE OVERLAY (drawn by code from the camera calibration and the robot's own joint angles, never from object positions)
- WHITE GRID: lines lying ON THE TABLE SURFACE (z = table top) every 5 cm, brighter every 10 cm, labelled with robot-frame metres (x=0.40, y=-0.20). You do not need to read coordinates from it; point at the objects themselves.
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

ANSWER = """
First assess: (1) what did your LAST command do? Compare the images with the measured TCP and pad gap; tell an observed failure from an uncertain result. (2) task_progress from visual evidence only (undo a step the images show was lost). Then give exactly one command.
Return JSON only: {"assessment": {"task_progress": {"verified_completed": [string], "currently_attempting": string, "remaining": [string]}, "execution_status": "not_started"|"progressing"|"failed"|"uncertain"|"recovered", "evidence": "<= 40 words", "evidence_view": "head"|"right_wrist"|"both", "confidence": "low"|"medium"|"high"}, "command": {"mode": "point"|"edit"|"gripper"|"stop", "point_2d": [x, y] (point only; 0-1000 in image 1), "height": "above"|"grasp"|"place"|"lift" (point only), "delta_m": [dx, dy, dz] (edit only), "gripper": "keep"|"open"|"close" (point / edit: after the move; gripper mode: open or close)}, "reason": "<= 30 words"}"""

NOW = V2.NOW
REPAIR = V2.REPAIR
IMAGE_LABELS = V2.IMAGE_LABELS
TEMPLATES = {"static": STATIC, "now": NOW, "answer": ANSWER, "repair": REPAIR, "cam": CAM,
             "labels": "|".join(IMAGE_LABELS), "version": VERSION}
PROMPT_ID = hashlib.sha256("\n".join(TEMPLATES[k] for k in sorted(TEMPLATES)).encode()).hexdigest()[:12]

# wording check (prereg §4): integer pixel coordinates instead of the 0-1000 scale
_PX_FROM = ("- point_2d = [x, y] in image 1 on a 0-1000 scale: x from 0 (left edge) to 1000 (right edge), y from 0 "
            "(top edge) to 1000 (bottom edge).")
_PX_TO = ("- point_2d = [x, y] in image 1 in integer pixel coordinates: x from 0 (left edge) to {Wm} (right edge), y "
          "from 0 (top edge) to {Hm} (bottom edge); the image is {W}x{H} px.")
_PX_ANS_FROM = '"point_2d": [x, y] (point only; 0-1000 in image 1)'
_PX_ANS_TO = '"point_2d": [x, y] (point only; pixels of image 1)'


def static(info: dict, head, table_z: float, w_close: float) -> str:
    objs = [info["tgt"], info["place"]] + [k for k in info["present"] if k not in (info["tgt"], info["place"])]
    lines = "\n".join(f"- {OBJ_NAME.get(k, k)}: {OBJ_DESC.get(k, 'object')}"
                      + (" (the object to move)" if k == info["tgt"] else "")
                      + (" (where to put it)" if k == info["place"] else " (obstacle)" if k != info["tgt"] else "")
                      for k in objs)
    return STATIC.format(tz=table_z, x0=SAFE_X[0], x1=SAFE_X[1], y0=SAFE_Y[0], y1=SAFE_Y[1],
                         z0=table_z + SAFE_DZ[0], z1=table_z + SAFE_DZ[1], wc=w_close * 100, head=V2._cam(head),
                         instruction=info["instruction"], tgt_name=OBJ_NAME[info["tgt"]],
                         place_rule=place_rule(info["place"], OBJ_NAME[info["place"]]), objects=lines)


def now(wrist, tcp, gap_m, i, n, t_used, t_max, history) -> str:
    return V2.now(wrist, tcp, gap_m, i, n, t_used, t_max, history)


def px_variant(text: str, W: int, H: int) -> str:
    """The same request with integer pixel coordinates (answers are scaled back by the scorer)."""
    if _PX_FROM not in text or _PX_ANS_FROM not in text:
        raise ValueError("not an astra-solo-pt@v1 request")
    return text.replace(_PX_FROM, _PX_TO.format(W=W, H=H, Wm=W - 1, Hm=H - 1)).replace(_PX_ANS_FROM, _PX_ANS_TO)


def describe(cmd: dict, res: dict | None = None) -> str:
    if cmd["mode"] == "point":
        where = "" if cmd.get("point_2d") is None else \
            f" at ({cmd['point_2d'][0]:.0f}, {cmd['point_2d'][1]:.0f}) in image 1"
        s = f"point{where}, height {cmd['height']}, gripper {cmd['gripper']}"
        if res and res.get("goal") is not None:
            g = res["goal"]
            kind = {"object": "an object", "table": "the table"}.get(res.get("kind"))
            at = "" if kind is None else f"pointed at {kind}" + (
                f" with top z {res['top']:.3f}" if res.get("kind") == "object" else "") + "; "
            s += f" [measured: {at}target ({g[0]:.3f}, {g[1]:.3f}, {g[2]:.3f})]"
        return s
    return V2.describe(cmd)
