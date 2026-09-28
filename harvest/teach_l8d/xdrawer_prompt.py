"""L8-X drawer request "nd-xyz@v1+x2" (prereg_l8x_tasks 2.4, changes 10-12; pure).

The drawer commands add two fields to the v2 / nd-xyz vocabulary: eef "orient" ("down" = the usual top-down gripper,
"front" = pointing forward, fingers closing vertically) and gripper-open "width_m" (open only to that pad gap). They
get their own prompt version (+x2); the existing PROMPT_IDs are unchanged. The request is written in the already
stripped form (no table height, ring-only head image, names and roles only, no recipes: E-STRIP8 s-min), because a
drawer scene has no table: the same text is saved as prompt_v2.txt and prompt_nd-xyz@v1.txt, so every build format
of the dataset reads it unchanged (build b3d with format nd-xyz). The robot-frame line is the v2 line byte for byte
(dataset.with_lift inserts the lift line after it)."""
from __future__ import annotations

import hashlib
import json

import numpy as np

from ..astra_motion.executor import SAFE_X, SAFE_Y
from ..astra_solo import nd_prompts as NP
from ..astra_solo import prompts as V2

VERSION = "nd-xyz@v1+x2"
Z_BELOW, Z_ABOVE = 0.125, 0.25  # TCP z box around the handle (the executor's table_z = handle z - 0.15)

STATIC = """You control the right arm of a humanoid robot (ROBOTIS AI Worker FFW-SG2) in front of a piece of furniture, in simulation. You see its cameras and give one end-effector command at a time. The robot waits for your answer: each command is executed completely (the arm moves, then the gripper acts), and then you are called again with new images and the measured result. There is no time pressure between calls, so take the care you need; but the number of calls and the robot's motion time are limited (see NOW).

FRAME AND UNITS
- Robot frame: origin at the robot base, x forward (away from the robot), y to the robot's left, z up; positions in metres.
- The code keeps the TCP inside x {x0:.2f}..{x1:.2f}, y {y0:.2f}..{y1:.2f} m and within about {zb:.0f} cm below to {za:.0f} cm above the handle height (targets beyond are clipped, and you are told).

GRIPPER
- Two orientations (orient): "down" = it points straight down and its two fingers close along the robot x axis; "front" = it points forward (+x, away from the robot) and its fingers close vertically (along z). The gripper turns to the commanded orientation during a move. TCP = the point midway between the finger pads. The pads are 4.5 cm long; the gripper body starts 2.5 cm behind the TCP. Fully open pad gap 10.7 cm; a close with nothing between the pads ends near 0 cm.

COMMANDS (fixed code executes them; you never command joints)
- eef: move the TCP in a straight line (smooth start and stop, about 8 cm/s on average) to the absolute position_m [x, y, z] with orient "down" or "front" (omitted: keep the current orientation); then apply gripper: close (0.6 s), open (0.5 s) or keep. Any distance.
- edit: move by delta_m [dx, dy, dz] from the current target (at most 0.10 m; a longer delta is shortened); then apply gripper. Use it for small corrections seen in the wrist view.
- gripper: open or close in place. An open may give width_m (0.02 to 0.107): the pads open only to that gap, so the fingers fit next to a handle.
- stop: the task is complete (or cannot be completed); the episode ends.
Moves are straight lines.

CAMERAS (directions are unit vectors in the robot frame)
- Image 1: head camera, fixed on the robot head, {head}
- Image 2: RIGHT wrist camera, moves with the right hand and looks along the fingers; its pose now is under NOW.

""" + NP._OVL_ND + """DEFINITIONS (for your assessment)
- grasped = both finger pads are CLOSED on the handle bar (little or no gap between each pad and the bar) so that the drawer moves with the gripper; open fingers around the bar, or fingers closed in front of it, are NOT grasped. After a close, a pad gap above about 0.5 cm means the pads stopped on something.
- released = the pads are open and no longer touch the handle.
- open = the drawer is pulled out towards the robot; its opening is how far its front has moved.
- The head view alone can make the fingers look as if they hold the handle when they do not: verify contact, grasp and release in the right wrist view (and the pad gap).

TASK: {instruction}
Success = the {drawer} is pulled open by at least {open_cm:.0f} cm and the handle is released, the {piece} itself not moved. Then answer stop.
""" + "OBJECTS (other objects on the table are obstacles, do not touch them)" + """
- {piece_name} (furniture, stays in place)
- {handle_name} (the handle to pull)
"""

_CMD_V2 = '"mode": "eef"|"edit"|"gripper"|"stop", "position_m": [x, y, z] (eef only), '
_GRIP_V2 = '"gripper": "keep"|"open"|"close" (eef / edit: after the move; gripper mode: open or close)}'
assert _CMD_V2 in V2.ANSWER and _GRIP_V2 in V2.ANSWER
ANSWER = V2.ANSWER.replace(_CMD_V2, _CMD_V2 + '"orient": "down"|"front" (eef only; omit to keep), ').replace(
    _GRIP_V2, _GRIP_V2[:-1] + ', "width_m": number (optional, gripper open only)}')
TEMPLATES = {"static": STATIC, "now": V2.NOW, "answer": ANSWER, "labels": "|".join(V2.IMAGE_LABELS),
             "version": VERSION}
PROMPT_ID = hashlib.sha256("\n".join(TEMPLATES[k] for k in sorted(TEMPLATES)).encode()).hexdigest()[:12]
NOTE_TCP = "\nNOTE: the TCP is outside the head image this time: no ring is drawn."

KIND = {"Dresser": "dresser", "Desk": "desk", "Side": "side table"}
ORDINAL = ("first", "second", "third", "fourth", "fifth", "sixth")
PHRASES = ("Open the {drawer} of the {piece}.", "Pull the {drawer} of the {piece} open.",
           "Open the {piece}'s {drawer} by pulling its handle.")


def piece_kind(piece: str) -> str:
    return KIND.get(piece.split("_")[0], "furniture")


def drawer_words(rank: int, n: int) -> str:
    """The drawer among the n graspable top drawers of a piece, rank 0 = the robot's leftmost (largest y)."""
    if n == 1:
        return "top drawer"
    if n == 2:
        return "top left drawer" if rank == 0 else "top right drawer"
    return f"{ORDINAL[rank]} top drawer from the left"


def instruction(piece: str, rank: int, n: int, seed: int) -> dict:
    d, p = drawer_words(rank, n), piece_kind(piece)
    return {"instruction": PHRASES[int(seed) % len(PHRASES)].format(drawer=d, piece=p), "drawer": d, "piece": p,
            "piece_name": f"the {p}", "handle_name": f"the handle of its {d}"}


def static(words: dict, head, open_target: float) -> str:
    return STATIC.format(x0=SAFE_X[0], x1=SAFE_X[1], y0=SAFE_Y[0], y1=SAFE_Y[1], zb=Z_BELOW * 100, za=Z_ABOVE * 100,
                         head=V2._cam(head), open_cm=0.8 * open_target * 100, **words)


def now(wrist, tcp, gap_m: float, orient: str, i: int, n: int, t_used: float, t_max: float, history: list) -> str:
    t = V2.now(wrist, tcp, gap_m, i, n, t_used, t_max, history)
    a = "; pad gap"
    assert a in t
    return t.replace(a, f"; gripper {orient}{a}", 1)


def describe(cmd: dict) -> str:
    s = V2.describe(cmd)
    if cmd["mode"] == "eef" and cmd.get("orient"):
        s = s.replace(", gripper", f" orient {cmd['orient']}, gripper", 1)
    if cmd.get("width_m") is not None:
        s += f" to {cmd['width_m'] * 100:.1f} cm"
    return s


def answer(step: str, cmd: dict, st: dict, words: dict, first: bool, last_line: str, prev_failed: bool,
           open_q: float) -> str:
    """The label answer (v2 answer form + the +x2 command fields)."""
    from ..teach_l8 import labels as L
    from .xdrawer import texts_front as texts
    doing, remaining, done = texts(step, words["drawer"])
    t = np.asarray(st["tcp"], float)
    ev = (f"TCP at ({t[0]:.3f}, {t[1]:.3f}, {t[2]:.3f}) m, pad gap {float(st['grip_w']) * 100:.1f} cm; "
          f"drawer open {max(open_q, 0.0) * 100:.0f} cm")
    if "BLOCKED" in (last_line or ""):
        ev += "; the last move was blocked"
    elif "clipped" in (last_line or ""):
        ev += "; the last target was clipped"
    a = {"assessment": {"task_progress": {"verified_completed": done, "currently_attempting": doing,
                                          "remaining": remaining},
                        "execution_status": L.status_of(step, first, last_line, prev_failed), "evidence": ev,
                        "evidence_view": "both", "confidence": "high"},
         "command": cmd, "reason": f"Next: {doing}."}
    return json.dumps(a)
