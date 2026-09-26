"""Prompts of the probe (identical for Astra low / high and the local VLM): S = observe and steer with GPT-as-Policy-style
commands. Layout, static first so repeated calls share a cacheable prefix: [STATIC: robot, frames, command contract,
fixed head / left-wrist camera poses, evidence rules, task, objects] + [interface block: rules + JSON format] + [NOW:
right wrist camera pose, TCP pose, pad gap] + [per-call information]. Images (coupling spec §12, all three cameras):
1 = head, 2 = LEFT wrist, 3 = RIGHT wrist, each with the cyan TCP marker (when in view) and pixel rulers.

The assessment questions, task_progress from visual evidence only and the continue / edit / stop commands with the
5 cm / 0.35 rad limits adapt GPT-as-Policy (J. Su, Y. Zheng, M. Yan, L. Yi, Z. Zhang, H. Wang, "GPT 6 Astra as an
Embodied Policy", technical report + code, 2026: hybrid_rollout gate prompt, validation.py, action_edit_kinematics.py).
There the gate corrects a student VLA and Astra runs at xhigh; here there is no student policy yet (in the real design
the VLA is the fast corrector between Astra commands), so edit is how the arm moves and continue repeats the last
committed motion.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np

OBJ_NAME = {"o3": "red mug", "o5": "blue tray", "o8": "green bottle", "o9": "yellow box", "o11": "magenta marker"}
OBJ_DESC = {"o3": "cylinder, diameter 6.4 cm, height 9.5 cm (solid, flat top)",
            "o5": "flat box 18 cm (x) x 14 cm (y), 1.5 cm high",
            "o8": "cylinder, diameter 5.0 cm, height 10.0 cm (solid, flat top)",
            "o9": "box 5 x 5 cm, 7 cm high",
            "o11": "flat disc on the table, diameter 10 cm, 2 mm high (a painted target spot; no collision)"}
# L8-X objects (harvest/sim/scene.py X_OBJ_GEOM; only in L8-X scenes)
OBJ_NAME.update({"o12": "white stand", "o13": "blue mug", "o14": "small red cup", "o15": "grey bin",
                 "o17": "spot left of the green bottle", "o18": "spot right of the green bottle"})
OBJ_DESC.update({"o12": "box 12 x 12 cm, 8 cm high (a raised stand)",
                 "o13": "cylinder, diameter 6.4 cm, height 9.5 cm (solid, flat top)",
                 "o14": "cylinder, diameter 5.0 cm, height 7.5 cm (solid, flat top)",
                 "o15": "open box 16 x 16 cm with 5 cm high walls (put things inside, on its floor)",
                 "o17": "an empty place on the table about 10 cm to the robot's left (+y) of the green bottle's centre "
                        "(nothing is drawn there)",
                 "o18": "an empty place on the table about 10 cm to the robot's right (-y) of the green bottle's "
                        "centre (nothing is drawn there)"})

STATIC = """You control the right arm of a humanoid robot (ROBOTIS AI Worker FFW-SG2) at a table, in simulation, by looking at its cameras and giving short end-effector commands.

FRAMES AND UNITS
- Robot base frame for every 3D number: origin at the robot base, x forward (away from the robot), y to the robot's left, z up.
- Table top surface: z = {table_z:.3f} m. The code keeps the TCP inside x 0.25..0.65 m, y -0.50..0.10 m, z {zmin:.3f}..{zmax:.3f} m (commands beyond are clipped).

GRIPPER
- The gripper starts pointing straight down with its two fingers closing along the base x axis.
- TCP = the point midway between the two finger pads. The pads are 4.5 cm long (from 2.25 cm above to 2.25 cm below the TCP); the gripper body starts 2.5 cm above the TCP. Fully open pad gap 10.7 cm. An object is held only if it is between the pads when they close.

COMMANDS (executed by fixed code; you never command joints)
- edit: move the TCP target by delta_position_cm (base frame, norm <= 5 cm; relative to the current target -- the measured TCP can lag it by up to about 1 cm when carrying a load) in a straight line at 8 cm/s, turn the gripper by delta_rotation_rad (rotation vector in the base frame, norm <= 0.35 rad; optional, default none), then apply gripper: close (squeeze, 0.6 s), open (0.5 s) or keep.
- continue: repeat your last committed motion once (the same delta_position_cm and delta_rotation_rad, gripper keep); with no earlier motion the robot holds still.
- stop: end the episode (task done, or it cannot be done).

CAMERAS (pixel rulers on the top and left borders, labels every 100 px; a cyan ring with a cross marks the current TCP of the right gripper when it is in view; directions are unit vectors in the base frame)
- Image 1: head camera (fixed on the robot head), {head}
- Image 2: LEFT wrist camera (on the idle left arm), {left}
- Image 3: RIGHT wrist camera (moves with the right hand, sees between the fingers); its pose now is under NOW.

EVIDENCE RULES
- The head view is for layout, paths and targets. Its perspective can make the fingers look as if they touch or hold an object when they do not.
- Contact, grasp, lift, place and release can be verified only from a wrist view (the right wrist camera for the right gripper); name the view in execution_evidence. On a conflict the wrist view wins; cross-check with the pad gap.
- 'Held' means the two finger pads are CLOSED on the object (little or no gap between each pad and the object) so that it moves with the gripper. Open fingers with the object between them, fingers closed next to or in front of the object, or an object merely overlapping the fingers in a view are NOT held.
- If you are not sure, say so (execution_status or intent_status "uncertain", or confidence "low"): the robot then continues its current motion instead of changing course.

TASK: {instruction}
Success = the {tgt_name} stands upright {place_rule}, released by the gripper, for 1 s.
OBJECTS ON THE TABLE (name: shape)
{objects}
"""

CAM = ("{W}x{H} px at ({t[0]:.2f}, {t[1]:.2f}, {t[2]:.2f}) m, looking along ({R[0][2]:+.2f}, {R[1][2]:+.2f}, "
       "{R[2][2]:+.2f}); image right = ({R[0][0]:+.2f}, {R[1][0]:+.2f}, {R[2][0]:+.2f}), image down = ({R[0][1]:+.2f}, "
       "{R[1][1]:+.2f}, {R[2][1]:+.2f}).")

DYNAMIC = """
NOW
- Right wrist camera (image 3): {wrist}
- TCP at ({tcp[0]:.3f}, {tcp[1]:.3f}, {tcp[2]:.3f}) m; gripper turned {yaw:+.0f} deg about z from its start; pad gap {grip_cm:.1f} cm (closing on nothing ends near {w_close_cm:.1f} cm).
"""

TP_JSON = ('"task_progress": {"verified_completed": [string], "currently_attempting": string, '
           '"remaining": [string]}')
ASSESS_JSON = ('"assessment": {' + TP_JSON + ', "current_subgoal": string, "execution_status": '
               '"not_started"|"progressing"|"failed"|"uncertain"|"recovered", "execution_evidence": string, '
               '"intent_status": "aligned"|"misaligned"|"uncertain", "intent_evidence": string, '
               '"confidence": "low"|"medium"|"high"}')
EDIT_JSON = ('{"delta_position_cm": [number, number, number], "delta_rotation_rad": [number, number, number], '
             '"gripper": "keep"|"open"|"close"}')

ASSESS = """Assess two separate questions:
1. What happened during the LAST executed motion? Compare the images with the measured TCP and pad gap. A close command alone proves neither grasp success nor failure. Look for object motion during lifting, slipping, missed placement or lack of progress. Distinguish pending / uncertain results from an observed failure.
2. Does the robot's CURRENT motion (the last committed command, which continue repeats) pursue the right subgoal: right object, right place, right order, right grasp / release phase? Advancing to a dependent subgoal after its prerequisite failed is wrong.
Update task_progress only from visual evidence; undo a completed subgoal if the images show it was lost."""

S_SYNC = """INTERFACE: observe and steer, synchronous. The robot waits for your answer, executes it, and then you are called again with new images.
""" + ASSESS + """
Then give exactly one command (continue / edit / stop).
Return JSON only: {""" + ASSESS_JSON + """, "decision": "continue"|"edit"|"stop", "edit": """ + EDIT_JSON + """ (edit only), "reason": "<= 30 words"}"""
S_SYNC_DYN = """- Call {i} of at most {n}.
- YOUR LAST COMMANDS AND RESULTS (oldest first): {history}"""

ST_COMMON = ("INTERFACE: observe and steer, streaming. The robot does NOT wait for you: calls are made one at a time, "
             "and as soon as your answer arrives the next call is sent with the newest images; meanwhile the robot "
             "keeps executing the earlier command (see the motion overlay). An edit is applied smoothly: its "
             "delta_position_cm is spread over the time until your next answer is expected (about as long as this "
             "call takes) at half strength, or full strength when it agrees with your previous answer, and fades out "
             "if no new answer refreshes it. With a gripper action the move is done quickly and the gripper acts right "
             "after it.")

ST_F0 = ST_COMMON + "\n" + ASSESS + """
Then give exactly one command (continue / edit / stop) for the moment your answer arrives.
Return JSON only: {""" + ASSESS_JSON + """, "decision": "continue"|"edit"|"stop", "edit": """ + EDIT_JSON + """ (edit only), "reason": "<= 30 words"}"""

ST_F1 = ST_COMMON + """ A COMMITTED FLOW (the command being executed, the committed task_progress, the robot's recent motion and its predicted state when your answer arrives) is given under NOW. Answer as a DIFF against it:
- "keep": the committed command still fits -- it is repeated once when your answer arrives (like continue);
- "revise": replace it by your command (edit or stop).
Evidence is required: what in the images shows the committed command fits, or why it no longer fits. A revision is executed only if the next overlapping answer confirms it (also revise, same gripper action, movement direction within about 35 degrees) -- do not revise for small imperfections.
""" + ASSESS + """
Return JSON only: {""" + ASSESS_JSON + """, "decision": "keep"|"revise", "command": {"decision": "edit"|"stop", "edit": """ + EDIT_JSON + """ (edit only)} (revise only), "evidence": string}"""
ST_F1_DYN = """- COMMITTED COMMAND: {committed}
- COMMITTED task_progress: {tp_now}
- RECENT MOTION (last 3 s): {recent}
- PREDICTED WHEN YOUR ANSWER ARRIVES (+{horizon:.0f} s, if nothing changes): {predicted}"""

REPAIR = "\n\nYOUR PREVIOUS ANSWER WAS INVALID: {errors}\nAnswer again with JSON only, in the required format."

GRASP_Q = """You look at the cameras of a humanoid robot's right arm at a table (simulation). The right gripper points down; its two fingers close along the robot's forward axis. {views}
EVIDENCE RULES: the head view shows the layout, but its perspective can make fingers look as if they hold an object when they do not; contact and grasp can be verified only from a wrist view (the right wrist camera sees between the right fingers). On a conflict the wrist view wins.
DEFINITION: 'held' means the two finger pads are CLOSED on the object (little or no gap between each pad and the object) so that it would move with the gripper. Open fingers with the object between them, fingers closed next to or in front of the object, or an object merely overlapping the fingers in a view are NOT held. Judge the finger opening from the right wrist view.
QUESTION: is the {tgt_name} held (grasped) by the RIGHT gripper right now?
Return JSON only: {{"grasp_state": "grasped"|"not_grasped"|"uncertain", "evidence_view": "head"|"right_wrist"|"left_wrist"|"multiple", "evidence": "<= 30 words", "confidence": "low"|"medium"|"high"}}"""
GRASP_VIEWS = {"head": "Image 1: head camera.", "head+right": "Image 1: head camera. Image 2: RIGHT wrist camera.",
               "all3": "Image 1: head camera. Image 2: LEFT wrist camera (idle left arm). Image 3: RIGHT wrist camera."}

TEMPLATES = {"grasp": GRASP_Q, "static": STATIC, "cam": CAM, "dynamic": DYNAMIC, "assess": ASSESS, "S": S_SYNC, "S-dyn": S_SYNC_DYN,
             "F0": ST_F0, "F1": ST_F1, "F1-dyn": ST_F1_DYN, "repair": REPAIR}
PROMPT_ID = hashlib.sha256("\n".join(TEMPLATES[k] for k in sorted(TEMPLATES)).encode()).hexdigest()[:12]


def place_rule(place: str, place_name: str) -> str:
    if place == "o11":
        return (f"on the {place_name} (its centre within 4 cm of the marker centre, standing on the table inside the "
                f"marker)")
    if place == "o15":  # L8-X
        return f"inside the {place_name} (standing on its floor, supported by it)"
    if place in ("o17", "o18"):  # L8-X relational spot
        side = "left (+y)" if place == "o17" else "right (-y)"
        return (f"on the table about 10 cm to the robot's {side} of the green bottle (its centre within 4 cm of "
                f"that point, standing on the table)")
    return f"on the {place_name} (resting on it, supported by it)"


def _cam(c) -> str:
    return CAM.format(W=c.W, H=c.H, fx=c.fx, fy=c.fy, cx=c.cx, cy=c.cy, t=np.asarray(c.t, float).tolist(),
                      R=np.asarray(c.R, float).tolist())


def static(task_info: dict, head, left, table_z: float) -> str:
    from .executor import SAFE_DZ
    objs = "\n".join(f"- {OBJ_NAME[k]}: {OBJ_DESC[k]}" + (" (the object to move)" if k == task_info["tgt"] else "")
                     + (" (where to put it)" if k == task_info["place"] else "") for k in task_info["present"])
    return STATIC.format(table_z=table_z, zmin=table_z + SAFE_DZ[0], zmax=table_z + SAFE_DZ[1], head=_cam(head), left=_cam(left),
                         instruction=task_info["instruction"], tgt_name=OBJ_NAME[task_info["tgt"]],
                         place_rule=place_rule(task_info["place"], OBJ_NAME[task_info["place"]]), objects=objs)


def dynamic(wrist, tcp, yaw_deg: float, grip_w: float, w_close: float) -> str:
    return DYNAMIC.format(wrist=_cam(wrist), tcp=np.asarray(tcp, float).tolist(), yaw=yaw_deg, grip_cm=grip_w * 100,
                          w_close_cm=w_close * 100)


def s_sync_dyn(i: int, n: int, history: list) -> str:
    return S_SYNC_DYN.format(i=i, n=n, history=" | ".join(history[-6:]) if history else "(none yet)")


def st_f1_dyn(committed: str, tp_now, recent: str, predicted: str, horizon: float) -> str:
    return ST_F1_DYN.format(committed=committed, tp_now=json.dumps(tp_now), recent=recent, predicted=predicted,
                            horizon=horizon)


def describe_cmd(c: dict | None) -> str:
    """One line for a committed command (history, F1 flow)."""
    if not c:
        return "none (holding still)"
    if c["decision"] == "stop":
        return "stop"
    e = c["edit"]
    dp, dr = e["delta_position_cm"], e["delta_rotation_rad"]
    rot = f", rotate ({dr[0]:+.2f}, {dr[1]:+.2f}, {dr[2]:+.2f}) rad" if any(abs(x) > 1e-9 for x in dr) else ""
    return f"move ({dp[0]:+.1f}, {dp[1]:+.1f}, {dp[2]:+.1f}) cm{rot}, gripper {e['gripper']}"
