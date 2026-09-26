"""E-ACC prompt arms (docs/stage3/prereg_eacc.md): the production astra-couple@v1 (harvest/couple/prompt.py, used
unchanged through its own build_input) and the candidate astra-couple@v2 text built here. Pure text + parsing, no
model calls. harvest/couple/* belongs to the coupling controller and is not edited: v2 lives here until the
controller folds the recommended spec in.

v2 = v1 wording kept where the content does not change, plus (prompt health check F1-F11, canon §90/§91/§94):
  FRAME       verbal robot-frame axes (F4)
  DEFS        operational definitions of the judged concepts (F1; tools/prompt_health/variants.COUPLE_DEFS)
  legend      only the overlay elements actually drawn, the committed arrow = executed chunk motion (F2, F3)
  events      one legend line per event present in the request (F8)
  SEGMENTS    the segment plan output (canon §90; vocabulary = harvest.serialize.SEGMENTS / SEGMENT_ACTIONS)
  context     since_last_request: previous command + segment and the tip motion the VLA executed since (canon §91)
  valid_until next_answer | segment_end on an edit (canon §94 lever)
  limit       prompt 0.04 m, parser tolerance 0.05 m (F7 / P62)
  campose     optional: per-camera pose lines + tip height above the table (F5; the E-ACC lever A2)
  cameras     the camera sentence names only the cameras sent (2-camera arm)
"""
from __future__ import annotations

import base64
import hashlib
import json

from harvest.couple import prompt as CP
from harvest.couple import schema as CS
from harvest.serialize import SEGMENT_ACTIONS, SEGMENTS

SCHEMA_V2 = "astra-couple@v2-eacc"
VALID_UNTIL = ("next_answer", "segment_end")
EDIT_PROMPT_M = 0.04  # stated limit; the parser keeps CS.EDIT_MAX_M = 0.05 as the tolerance (margin, P62)

FRAME = ("Robot frame: origin at the robot base, x forward (away from the robot), y to the robot's left, z up; "
         "positions and deltas in metres, rotations as rotation vectors in radians.\n")
DEFS = ("Definitions for claims and progress: grasped = both finger pads are CLOSED on the object (little or no gap "
        "between each pad and the object) so that it moves with the gripper; open fingers with the object between "
        "them, fingers closed next to or in front of it, or an object that merely overlaps the fingers in a view are "
        "NOT grasped. released = the pads are open and the object no longer moves with the gripper. placed = the "
        "object rests upright on its target and is released. contact = a finger or pad touches the object. "
        "grasp_ready = the open pads surround the object at grasp height.\n")
CAM_ROLE = {"cam_head": "cam_head = overview for layout, path and target choice; it is NOT enough on its own for "
                        "contact, grasp or release (perspective makes fingers and objects overlap)",
            "cam_wrist_left": "cam_wrist_left = close-up of the left gripper",
            "cam_wrist_right": "cam_wrist_right = close-up of the right gripper"}
LEGEND = {
    "ring": "white ring = gripper tip now",
    "trace": "thin pale-green outlined line, fading = the tip over the last {trace_s:g} s",
    "next": ("THICK SOLID pale-green arrow with a FILLED head = the tip motion of the policy's current action chunk "
             "over the next 0.5 s (executed motion, drawn to scale)"),
    "offset": ("thin DASHED pale-green arrow with an OPEN head = your previous correction still being applied (go by "
               "line style and head shape, not colour)"),
    "axes": "short red / green / blue lines at the tip, no arrowhead = robot frame +x / +y / +z (3 cm long)",
}
WRIST_BOX = ("On wrist images the overlay is only a small box in the top-right corner: red / green / blue lines = "
             "robot +x / +y / +z as seen from that camera{wrist_arrows}.")
WRIST_ARROW = {"next": "; cyan solid arrow with a filled head = direction of the policy's next 0.5 s motion",
               "offset": "; magenta dashed arrow with an open head = direction of your correction"}
EVENT_LEGEND = {
    "m7_critic_alarm": "the visual critic judged the last step as failing",
    "m7_hard_t1": "proprioception (pad gap / force) shows a hard failure, e.g. the object slipped out",
    "b_contradict": "the check after the last step contradicts what the policy expected",
    "j5_escalate": "the policy was unsure about the same decision several times in a row",
    "no_progress": "the tip did not move along your active correction for 2 s",
    "offset_contradicted": "the policy's executed motion opposed your active correction for 1 s (it was scaled down)",
    "offset_vs_b": "a step check failed while your correction was active",
    "layer_mismatch": "the policy wanted an irreversible gripper action but your assessment did not allow it for 1 s",
    "astra_stop_confirmed": "your stop was confirmed by two answers",
}
SEGMENT_TEXT = (
    "Task segments (the policy is told the segment you name and decides by itself when to act inside it): approach = "
    "move the open gripper above the target object; descend = lower it around the object to grasp height; grasp = "
    "close the gripper on the object; lift = raise the held object; carry = move it above the place; place = lower it "
    "onto the place; release = open the gripper; retreat = move the empty gripper up and away; done = the task is "
    "complete. In your segment plan: now = the segment the policy should be in when your answer arrives; do = the "
    "gripper action of that segment (close for grasp, open for release, none otherwise); next = the segment after "
    "now. Use only these segment names; the policy's own phase names in the request map to them (close = grasp, "
    "place_descend = place, open = release, the rest are the same).\n")
CONTEXT_RULE = (
    "since_last_request (in the request) = what happened since your previous request: your previous command and "
    "segment plan, the tip displacement the policy actually executed since then (robot frame, m) and the policy's "
    "phases in that time. Check whether your previous judgement still holds; do not repeat a correction the policy "
    "has already carried out.\n")
ASSESS = ("Assess two things: (1) execution of the last seconds: not_started | progressing | failed | uncertain | "
          "recovered; (2) intent: does the policy's current motion pursue the right subgoal? aligned | misaligned | "
          "uncertain.\n")
COMMANDS = ("Commands: continue = let the policy go on. edit = one short correction of the gripper tip in the robot "
            "frame: |delta_position_m| <= 0.04, |delta_rotation_rad| <= 0.35, gripper keep | open | close, "
            "valid_until next_answer (apply it until your next answer) | segment_end (drop it as soon as the "
            "policy's segment changes). An edit requires execution=failed or intent=misaligned; uncertainty alone or "
            "an imperfect pose is not a reason to take over. stop = the whole task is complete (needs a wrist claim "
            "placed or released). info_request slow_down asks the robot to move slower for 2 s when you need a "
            "clearer view; otherwise none.\n")
_SEG = ('"segment": {"now": "' + "|".join(SEGMENTS) + '", "do": "' + "|".join(SEGMENT_ACTIONS) + '", "next": "'
        + "|".join(SEGMENTS) + '"}')
_CMD = ('"command": "continue|edit|stop", "edit": {"delta_position_m": [dx, dy, dz], "delta_rotation_rad": '
        '[rx, ry, rz], "gripper": "keep|open|close", "valid_until": "next_answer|segment_end"} (only with command '
        'edit, else null), "info_request": "none|slow_down"')
ANSWER_FORM = "{" + CP._ASSESS + ", " + _SEG + ", " + _CMD + "}"
MODE_RULE = CP.MODE_RULES["F0"]
TEMPLATE = (
    "You supervise a robot doing this task: {task}\n"
    "A fast policy (VLA) moves the {arm} gripper every 0.33 s and never waits for you. Your answer arrives about "
    "{horizon:g} s after these images were taken: judge the situation at predicted_ee_at_arrival.\n"
    + FRAME + "{campose}{cameras}" + DEFS + "{legend}{events}" + SEGMENT_TEXT + "{context}" + ASSESS + COMMANDS
    + "{mode_rules}\n{req_open}\n{request_json}\n{req_close}\n"
    "Answer with one JSON object only, in this form (assessment, segment, command, edit and info_request are five "
    "top-level keys; nothing is nested inside assessment except its own fields):\n{answer_form}")
PROMPT_ID = hashlib.sha256((TEMPLATE + ANSWER_FORM + json.dumps(LEGEND, sort_keys=True) + WRIST_BOX
                            + json.dumps(WRIST_ARROW, sort_keys=True) + json.dumps(EVENT_LEGEND, sort_keys=True)
                            + json.dumps(CAM_ROLE, sort_keys=True)).encode()).hexdigest()[:12]


def camera_text(cams: list, arm: str = "right") -> str:
    wrist = CP.WRIST_OF[arm]
    roles = "; ".join(CAM_ROLE[c] for c in cams)
    tail = (f" A claim that something is grasped, released, placed or touching is valid only with the active wrist "
            f"camera ({wrist}) as evidence; if head and wrist disagree, trust the wrist.") if wrist in cams else ""
    return f"Cameras (each image is preceded by its name): {roles}.{tail}\n"


def legend_text(drawn: dict | None, trace_s: float) -> str:
    """drawn: {"head": set of LEGEND keys drawn on the head image, "wrist": set of WRIST_ARROW keys drawn in the
    wrist boxes (axes always) or None when no wrist image carries an overlay}; None = no overlay at all."""
    if not drawn:
        return "No overlay is drawn on the images.\n"
    parts = [LEGEND[k].format(trace_s=trace_s) for k in ("ring", "trace", "next", "offset", "axes")
             if k in drawn.get("head", set())]
    out = ("Overlay on cam_head (drawn by code from the robot's own kinematics, never from object ground truth): "
           + "; ".join(parts) + ".\n") if parts else ""
    if drawn.get("wrist") is not None:
        out += WRIST_BOX.format(wrist_arrows="".join(WRIST_ARROW[k] for k in ("next", "offset")
                                                     if k in drawn["wrist"])) + "\n"
    return out


def events_text(events: list) -> str:
    names = sorted({e if isinstance(e, str) else e.get("event") for e in events} & set(EVENT_LEGEND))
    if not names:
        return ""
    return "Events in the request: " + "; ".join(f"{n} = {EVENT_LEGEND[n]}" for n in names) + ".\n"


def _v3(v) -> str:
    return "(" + ", ".join(f"{float(x):+.2f}" for x in v) + ")"


def campose_text(cams: dict, order: list, tip_above_table_m: float) -> str:
    """cams: name -> {"R": 3x3 base-from-optical (columns = image right, image down, looking along), "t": position}."""
    lines = []
    for c in order:
        if c not in cams:
            continue
        R, t = cams[c]["R"], cams[c]["t"]
        col = lambda j: [R[i][j] for i in range(3)]  # noqa: E731
        lines.append(f"{c} at {_v3(t)} m looking along {_v3(col(2))}, image right = {_v3(col(0))}, image down = "
                     f"{_v3(col(1))}")
    return ("Camera poses now (unit vectors in the robot frame): " + "; ".join(lines)
            + f". The tip is {tip_above_table_m:.2f} m above the table top.\n")


def build_v2(req: dict, images: dict, cams_order: list, task: str, *, arm: str = "right", trace_s: float = 2.5,
             horizon_s: float = 9.3, drawn: dict | None = None, campose: str = "", detail: str | None = None) -> list:
    """Same message layout as the production build_input: text first, then 'cam:' label + JPEG per camera sent."""
    sent = [c for c in cams_order if images.get(c) is not None]
    text = TEMPLATE.format(task=task, arm=arm, horizon=round(horizon_s, 1), campose=campose,
                           cameras=camera_text(sent, arm), legend=legend_text(drawn, trace_s),
                           events=events_text(req.get("events", [])),
                           context=CONTEXT_RULE if "since_last_request" in req else "", mode_rules=MODE_RULE,
                           req_open=CP.REQ_OPEN, request_json=json.dumps(req, sort_keys=True, ensure_ascii=False),
                           req_close=CP.REQ_CLOSE, answer_form=ANSWER_FORM)
    content = [{"type": "input_text", "text": text}]
    for cam in sent:
        content.append({"type": "input_text", "text": f"{cam}:"})
        part = {"type": "input_image", "image_url": "data:image/jpeg;base64," + base64.b64encode(images[cam]).decode()}
        if detail:
            part["detail"] = detail
        content.append(part)
    return [{"role": "user", "content": content}]


class V2Error(ValueError):
    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("; ".join(self.problems))


def parse_v2(text: str, sent_cameras) -> tuple:
    """(production AstraAnswer of the common part, segment dict, valid_until or None). The common part goes through
    the production parser (it ignores the extra keys); the v2 fields are checked here. Raises V2Error with every
    problem found (the production SchemaError problems included)."""
    probs = []
    a = None
    try:
        a = CS.parse_answer(text, "F0", sent_cameras, 1, 0.0, 1.0)
    except CS.SchemaError as e:
        probs += e.problems
    try:
        d = CS.extract_json(text)
    except CS.SchemaError as e:
        raise V2Error(probs or e.problems) from None
    seg = d.get("segment")
    if not (isinstance(seg, dict) and seg.get("now") in SEGMENTS and seg.get("do") in SEGMENT_ACTIONS
            and seg.get("next") in SEGMENTS):
        probs.append(f"segment: {{now, next in {SEGMENTS}, do in {SEGMENT_ACTIONS}}}")
        seg = None
    vu = None
    if a is not None and a.command == "edit":
        vu = (d.get("edit") or {}).get("valid_until")
        if vu not in VALID_UNTIL:
            probs.append(f"edit.valid_until: one of {VALID_UNTIL}")
    if probs:
        raise V2Error(probs)
    return a, {k: seg[k] for k in ("now", "do", "next")}, vu
