"""Format v3 request / answer text for articulated episodes (pure; the d-min structure of L9 v2 + ART_BLOCK).
The request is stored per call as prompt_v3.txt; build_art turns it into training rows."""
from __future__ import annotations

import json

import numpy as np

VERSION = "d-min-v3@art2"  # art2: joint axis fields (axis, pivot_2d, turn, amount) in the answer
ROBOT_WORDS = {"ffw_sg2": "a humanoid robot (ROBOTIS AI Worker FFW-SG2)", "franka_mast": "a robot arm (Franka Emika Panda) on a stand",
               "r1pro": "a humanoid robot (Galaxea R1 Pro)"}

ART_BLOCK = """SKILLS (format v3: "skill" in every point command; v2 commands without it are pick / place)
- skill: pick | place | pull_axis | push_axis | rotate | press | push_slide.
- pull_axis = hold a handle and move it along its joint (open / close a drawer, swing a door, slide a door); push_axis = push a part along its joint without grasping (shut a drawer or a door); rotate = hold a knob or dial and turn it; press = push a button or switch in and let it spring back; push_slide = push an object along the table without lifting it.
- point2 = [x, y] in image 1 (0-1000): where the pointed contact (handle, pushed spot, the knob's white mark, the pushed object's centre) should END. Give it only with the move along the joint / the push / the turn.
- With every move along a joint also give the joint: "axis": "linear" (drawer, sliding door: the part slides along point -> point2; "amount_cm" = how far) or "rotary" (hinged door, knob, dial) with "pivot_2d" = [x, y] the rotation axis in image 1 (a door's hinge line at the handle's height, a knob's centre), "turn": "cw" | "ccw" as seen in image 1 and "amount_deg" = how far.
- press: point at the button with height grasp (the code presses it in and backs off); no point2.
- Grasping a handle or knob: point at it with height above (pre-pose in front of it, approach and rot as for grasps), then height grasp with gripper close. Pushes and presses use closed fingers: close the gripper first.

"""

STATIC = """You control the {arm} arm of {robot} in simulation. You see its cameras and give one command at a time; each command is executed completely, then you are called again with new images and the measured result.

ROBOT
- {robot_line}

POINT, THEN ACT (you never compute target coordinates)
- point_2d = [x, y] in image 1 (the head camera) on a 0-1000 scale (x from the left edge, y from the top edge), on the part you mean.
- height: above = the pre-pose about 10 cm in front of / above the pointed part; grasp = at the part (fingers around it, or touching it for pushes and presses); lift = straight up where the TCP is now.
- approach: top | oblique | front | side (robot base frame); rot: 0-11 = the line between the finger pads as seen in image 1, 15-degree steps.

{art_block}COMMANDS
- point: move to the target made from point_2d (+ point2) and height; then apply gripper: close, open or keep.
- edit: move by delta_m [dx, dy, dz] (robot frame, metres, at most 0.10 m); gripper mode: open or close in place; stop: the task is complete (or cannot be completed).

TASK: {instruction}
Success = {success}. Then answer stop.
"""

NOW = """
NOW
- TCP at ({tcp[0]:.3f}, {tcp[1]:.3f}, {tcp[2]:.3f}) m; pad gap {gap:.1f} cm.
- Call {i} of at most {n}.
YOUR COMMANDS SO FAR (oldest first; results measured by the robot):
{history}
"""

ANSWER = """
First assess what your last command did (images + measured TCP / pad gap), then give exactly one command.
Return JSON only: {"assessment": {"task_progress": {"verified_completed": [string], "currently_attempting": string, "remaining": [string]}, "execution_status": "not_started"|"progressing"|"failed"|"uncertain"|"recovered", "evidence": "<= 40 words", "evidence_view": "head"|"wrist"|"both", "confidence": "low"|"medium"|"high"}, "command": {"mode": "point"|"edit"|"gripper"|"stop", "skill": string (point only), "point_2d": [x, y] (point only), "point2": [x, y] (moves along a joint / pushes / turns only), "axis": "linear"|"rotary", "pivot_2d": [x, y] (rotary), "turn": "cw"|"ccw" (rotary), "amount_cm": number (linear), "amount_deg": int (rotary) (moves along a joint only), "height": "above"|"grasp"|"lift" (point only), "approach": string, "rot": int, "delta_m": [dx, dy, dz] (edit only), "gripper": "keep"|"open"|"close", "hand": "left"|"right"}, "reason": "<= 30 words"}"""

SUCCESS = {
    "drawer_open": "the {H} is open at least 80 % of its travel", "drawer_open_half": "the {H} is open between 35 and 65 % of its travel",
    "drawer_close": "the {H} is closed (within 10 % of its travel)", "door_open": "the {H} is open at least 62 % of its swing",
    "door_close": "the {H} is closed (within 8 % of its swing)", "slide_open": "the {H} is open at least 75 % of its travel",
    "slide_close": "the {H} is closed (within 10 % of its travel)",
    "knob_turn": "the {H} is turned {DEG} degrees {DIR} from where it started (within 15 degrees)",
    "dial_turn_top": "the {H} is turned {DEG} degrees {DIR} from where it started (within 15 degrees)",
    "knob_off": "the {H} mark is back at its start position (within 12 degrees)",
    "button_press": "the {H} was pressed in", "switch_press": "the {H} was pressed in",
    "push_object": "the {O} ends about {DIST} cm to the {DIR} of where it started (within 3 cm), still upright",
    "push_object_far": "the {O} ends about {DIST} cm further away than where it started (within 3 cm), still upright",
    "drawer_put_close": "the {O} lies in the {H} and the drawer is closed", "drawer_take_close": "the {O} stands on the table and the {H} is closed",
    "knob_then_button": "the {K} is turned {DEG} degrees {DIR} and then the {B} was pressed",
}

STAGE_TEXT = {"pull": "move the {X} along its joint", "push": "push the {X} along its joint", "rotate": "turn the {X}",
              "press": "press the {X}", "slide": "push the {X}", "pick": "pick up the {X}", "place": "put the {X} down"}


def robot_line(ep) -> str:
    g = ep.ex.gr
    return f"robot: {ep.ex.profile}, arm {ep.ex.arm} 7-DoF, parallel gripper max {float(g['max_open']) * 100:.1f} cm"


def static(ep) -> str:
    words = {k: v for k, v in ep.prog["words"].items()}
    succ = SUCCESS.get(ep.prog["def"], "the task is done").format(**{k: words.get(k, "") for k in
                                                                     ("H", "O", "K", "B", "DEG", "DIR", "DIST")})
    return STATIC.format(arm=ep.ex.arm, robot=ROBOT_WORDS.get(ep.ex.profile, ep.ex.profile), robot_line=robot_line(ep),
                         art_block=ART_BLOCK, instruction=ep.prog["instruction"], success=succ)


def now(ep, obs, i: int, n: int) -> str:
    return NOW.format(tcp=np.asarray(obs.tcp, float).tolist(), gap=float(obs.grip_w) * 100, i=i, n=n,
                      history="\n".join(ep.history[-10:]) if ep.history else "(none yet)") + ANSWER


def describe(cmd: dict) -> str:
    m = cmd.get("mode")
    if m == "point":
        s = f"{cmd.get('skill', 'pick')} point {cmd.get('point_2d')} height {cmd.get('height')}"
        if cmd.get("point2") is not None:
            s += f" to {cmd['point2']}"
        return s + f", gripper {cmd.get('gripper')}"
    if m == "edit":
        d = cmd["delta_m"]
        return f"edit by ({d[0]:+.3f}, {d[1]:+.3f}, {d[2]:+.3f}), gripper {cmd.get('gripper')}"
    if m == "gripper":
        return f"gripper {cmd['gripper']}"
    return "stop"


def _stage_words(ep, st) -> str:
    w = ep.prog["words"]
    x = w.get(st["ref"], st["ref"]) if st.get("ref") else "part"
    if st["kind"] == "place":
        return f"put the {w.get('O', 'object')} {x}"
    return STAGE_TEXT[st["kind"]].format(X=x)


def answer(ep, lab: dict, last_note) -> str:
    stages = ep.prog["stages"]
    done = [_stage_words(ep, stages[k]) for k in ep.done_stages]
    cur = _stage_words(ep, stages[ep.stage_i]) if ep.stage_i < len(stages) else "finished"
    rem = [_stage_words(ep, s) for s in stages[ep.stage_i + 1:]]
    failed = last_note is not None and any(k in last_note for k in ("failed", "lost", "nothing", "stopped at", "only",
                                                                       "no collision-free", "could not"))
    status = "not_started" if last_note is None else ("failed" if failed else "progressing")
    ev = (last_note or "nothing done yet")[:200]
    a = {"assessment": {"task_progress": {"verified_completed": done, "currently_attempting": cur, "remaining": rem},
                        "execution_status": status, "evidence": ev, "evidence_view": "both", "confidence": "high"},
         "command": lab["cmd"], "reason": f"Next: {lab['sub']} ({lab.get('skill') or 'stop'})."}
    return json.dumps(a)
