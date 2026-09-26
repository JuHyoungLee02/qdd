"""Astra coupling prompt astra-couple@v2 (plan 2026-09-26 Task 18, controller rulings T18 / T18b): the E-ACC v2 prompt
ADOPTED by E-ACC R1 (docs/stage3/results/eacc.md §5, commit 2a7b9ae; registered text tools/eacc/prompt_v2.py,
PROMPT_ID 83fa03a5de19) folded into the coupling. Every text part below is copied byte for byte from the registered
E-ACC file (tests/couple/test_prompt_v2.py checks the built prompt bytes and the id against it); the E-ACC file itself
stays untouched while its pre-registered stage 2 runs.

v2 = the v1 wording kept where the content does not change, plus (prompt health check F1-F11, canon §90/§91/§94):
  FRAME       verbal robot-frame axes (F4)
  DEFS        operational definitions of grasped / released / placed / contact / grasp_ready (F1; couple_dry B8: the
              grasped over-claims -- a grasped claim needs CLOSED pads and the active wrist view, gate unchanged)
  legend      only the overlay elements actually drawn; the committed arrow = the executed chunk motion (F2, F3)
  events      one legend line per event present in the request (F8)
  SEGMENTS    the segment plan output (canon §90; vocabulary = harvest.serialize.SEGMENTS / SEGMENT_ACTIONS)
  context     since_last_request: previous command + segment and the tip motion since (canon §91)
  valid_until next_answer | segment_end on an edit (canon §94 lever)
  limit       prompt 0.04 m, parser tolerance 0.05 m (F7 / P62)
  answer form 'five top-level keys' sentence (E-ACC change 2: invalid 0/90 in P1; couple_dry B8 command-value errors)
Options (all off by default = the adopted arm's bytes): AxisGuide legend line (E-ACC R2' undecided -> off; id suffix
+ax<sha6>), camera pose lines (E-ACC R2 not run -> off; id suffix +cp), extra_instruction (one extra sentence right
before the mode rule line, e.g. the E-ACC stage-2 target-check sentence; id suffix +x<sha6>), image detail (None = no
field, as adopted; id suffix +d<detail>). F1 (flow mode, not registered by E-ACC): the same parts with the F1 mode rule and a diff key; an F1
'keep' answer's accompanying edit is ignored, not a schema error (F9, schema.parse_answer version v2).

PROMPT_ID covers every template part: the E-ACC formula (core parts) is kept so the adopted F0 bytes keep their
registered id; the parts the E-ACC formula did not hash (mode rule, context rule, camera / overlay / event heads,
camera tail, request markers, campose texts) are hashed separately and, when they differ from the registered bytes
(or for F1), appended as +p<sha6>."""
from __future__ import annotations

import base64
import hashlib
import json

from ..serialize import SEGMENT_ACTIONS, SEGMENTS
from . import prompt as CP

SCHEMA_ID = "astra-couple@v2"
VALID_UNTIL = ("next_answer", "segment_end")
EDIT_PROMPT_M = 0.04  # stated limit; the parser keeps schema.EDIT_MAX_M = 0.05 as the tolerance (margin, P62)

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
ANSWER_FORM = {"F0": "{" + CP._ASSESS + ", " + _SEG + ", " + _CMD + "}",
               "F1": "{" + CP._ASSESS + ", " + _SEG + ', "diff": "keep|revise", ' + _CMD
                     + " (command only with diff revise)}"}
MODE_RULES = dict(CP.MODE_RULES)  # F0 = the registered E-ACC MODE_RULE
_BODY = (
    "You supervise a robot doing this task: {task}\n"
    "A fast policy (VLA) moves the {arm} gripper every 0.33 s and never waits for you. Your answer arrives about "
    "{horizon:g} s after these images were taken: judge the situation at predicted_ee_at_arrival.\n"
    + FRAME + "{campose}{cameras}" + DEFS + "{legend}{events}" + SEGMENT_TEXT + "{context}" + ASSESS + COMMANDS
    + "{mode_rules}\n{req_open}\n{request_json}\n{req_close}\n")
TEMPLATE = {
    "F0": _BODY + ("Answer with one JSON object only, in this form (assessment, segment, command, edit and "
                   "info_request are five top-level keys; nothing is nested inside assessment except its own "
                   "fields):\n{answer_form}"),
    "F1": _BODY + ("Answer with one JSON object only, in this form (assessment, segment, diff, command, edit and "
                   "info_request are six top-level keys; nothing is nested inside assessment except its own "
                   "fields):\n{answer_form}")}
CAM_HEAD = "Cameras (each image is preceded by its name): "
CAM_TAIL = (" A claim that something is grasped, released, placed or touching is valid only with the active wrist "
            "camera ({wrist}) as evidence; if head and wrist disagree, trust the wrist.")
NO_OVERLAY = "No overlay is drawn on the images.\n"
OVERLAY_HEAD = ("Overlay on cam_head (drawn by code from the robot's own kinematics, never from object ground truth): ")
EVENTS_HEAD = "Events in the request: "
AXISGUIDE_LINE = ("Axis guide on {cams}: long red / green / blue arrows from the gripper tip, labelled +x / +y / +z, "
                  "are the robot frame axes (10 cm long) as seen in that image -- read from them which image direction "
                  "is +x (forward), +y (left) and +z (up) before you choose delta_position_m.")
CAMPOSE_HEAD = "Camera poses now (unit vectors in the robot frame): "
CAMPOSE_LINE = "{c} at {t} m looking along {z}, image right = {x}, image down = {y}"
CAMPOSE_TAIL = ". The tip is {h:.2f} m above the table top.\n"


def _sha(s: str, n: int) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:n]


def parts(mode: str = "F0") -> dict:
    """Every template part of one mode, by name (what PROMPT_ID covers)."""
    return {"TEMPLATE": TEMPLATE[mode], "ANSWER_FORM": ANSWER_FORM[mode], "LEGEND": LEGEND, "WRIST_BOX": WRIST_BOX,
            "WRIST_ARROW": WRIST_ARROW, "EVENT_LEGEND": EVENT_LEGEND, "CAM_ROLE": CAM_ROLE,
            "MODE_RULE": MODE_RULES[mode], "CONTEXT_RULE": CONTEXT_RULE, "CAM_HEAD": CAM_HEAD, "CAM_TAIL": CAM_TAIL,
            "NO_OVERLAY": NO_OVERLAY, "OVERLAY_HEAD": OVERLAY_HEAD, "EVENTS_HEAD": EVENTS_HEAD,
            "CAMPOSE_HEAD": CAMPOSE_HEAD, "CAMPOSE_LINE": CAMPOSE_LINE, "CAMPOSE_TAIL": CAMPOSE_TAIL,
            "REQ_OPEN": CP.REQ_OPEN, "REQ_CLOSE": CP.REQ_CLOSE}


CORE = ("TEMPLATE", "ANSWER_FORM", "LEGEND", "WRIST_BOX", "WRIST_ARROW", "EVENT_LEGEND", "CAM_ROLE")
REGISTERED_REST = {"F0": "6005f3"}  # sha6 of the non-core parts as registered in the E-ACC F0 text (the byte test
# against tools/eacc/prompt_v2.py covers every one of them)


def rest_sha(pt: dict) -> str:
    return _sha(json.dumps({k: v for k, v in pt.items() if k not in CORE}, sort_keys=True), 6)


def prompt_id_of(pt: dict, mode: str = "F0") -> str:
    """Core = the registered E-ACC formula (TEMPLATE + ANSWER_FORM + LEGEND + WRIST_BOX + WRIST_ARROW + EVENT_LEGEND +
    CAM_ROLE); the other parts add +p<sha6> unless they are the registered bytes."""
    core = _sha(pt["TEMPLATE"] + pt["ANSWER_FORM"] + json.dumps(pt["LEGEND"], sort_keys=True) + pt["WRIST_BOX"]
                + json.dumps(pt["WRIST_ARROW"], sort_keys=True) + json.dumps(pt["EVENT_LEGEND"], sort_keys=True)
                + json.dumps(pt["CAM_ROLE"], sort_keys=True), 12)
    rest = rest_sha(pt)
    return core if REGISTERED_REST.get(mode) == rest else f"{core}+p{rest}"


PROMPT_ID = {m: prompt_id_of(parts(m), m) for m in ("F0", "F1")}
AXISGUIDE_ID = _sha(AXISGUIDE_LINE, 6)


def variant_id(mode: str = "F0", *, axisguide: bool = False, extra: str = "", campose: bool = False,
               detail: str | None = None) -> str:
    """The id of one built prompt: PROMPT_ID[mode] + '+ax<sha6>' when the axis guide line is in the text (as E-ACC)
    + '+x<sha6 of the extra sentence>' when extra_instruction is set + '+cp' when camera pose lines are in the text
    (their wording is in PROMPT_ID's parts; the numbers are request data) + '+d<detail>' when the image parts carry a
    detail field (Task 18 fix M3; E-ACC logged neither)."""
    return (PROMPT_ID[mode] + (f"+ax{AXISGUIDE_ID}" if axisguide else "")
            + (f"+x{_sha(extra_line(extra), 6)}" if extra_line(extra) else "")
            + ("+cp" if campose else "") + (f"+d{detail}" if detail else ""))


def extra_line(extra: str) -> str:
    """One extra instruction sentence as a prompt line ('' = none)."""
    return extra.rstrip("\n") + "\n" if extra and extra.strip() else ""


def camera_text(cams: list, arm: str = "right") -> str:
    wrist = CP.WRIST_OF[arm]
    roles = "; ".join(CAM_ROLE[c] for c in cams)
    tail = CAM_TAIL.format(wrist=wrist) if wrist in cams else ""
    return f"{CAM_HEAD}{roles}.{tail}\n"


def legend_text(drawn: dict | None, trace_s: float) -> str:
    """drawn: {"head": set of LEGEND keys drawn on the head image, "wrist": set of WRIST_ARROW keys drawn in the
    wrist boxes (axes always) or None when no wrist image carries an overlay, "axisguide": cameras with the axis
    guide}; None / empty = no overlay at all."""
    if not drawn:
        return NO_OVERLAY
    pts = [LEGEND[k].format(trace_s=trace_s) for k in ("ring", "trace", "next", "offset", "axes")
           if k in drawn.get("head", set())]
    out = (OVERLAY_HEAD + "; ".join(pts) + ".\n") if pts else ""
    if drawn.get("wrist") is not None:
        out += WRIST_BOX.format(wrist_arrows="".join(WRIST_ARROW[k] for k in ("next", "offset")
                                                     if k in drawn["wrist"])) + "\n"
    if drawn.get("axisguide"):
        out += AXISGUIDE_LINE.format(cams=" and ".join(drawn["axisguide"])) + "\n"
    return out


def events_text(events: list) -> str:
    names = sorted({e if isinstance(e, str) else e.get("event") for e in events} & set(EVENT_LEGEND))
    if not names:
        return ""
    return EVENTS_HEAD + "; ".join(f"{n} = {EVENT_LEGEND[n]}" for n in names) + ".\n"


def _v3(v) -> str:
    return "(" + ", ".join(f"{float(x):+.2f}" for x in v) + ")"


def campose_text(cams: dict, order: list, tip_above_table_m: float) -> str:
    """Optional (off by default): cams: name -> {"R": 3x3 base-from-optical (columns = image right, image down,
    looking along), "t": position}."""
    lines = []
    for c in order:
        if c not in cams:
            continue
        R, t = cams[c]["R"], cams[c]["t"]
        col = lambda j: [R[i][j] for i in range(3)]  # noqa: E731
        lines.append(CAMPOSE_LINE.format(c=c, t=_v3(t), z=_v3(col(2)), x=_v3(col(0)), y=_v3(col(1))))
    return CAMPOSE_HEAD + "; ".join(lines) + CAMPOSE_TAIL.format(h=tip_above_table_m)


def build(req: dict, images: dict, cams_order: list, task: str, *, mode: str = "F0", arm: str = "right",
          trace_s: float = 2.5, horizon_s: float = 9.3, drawn: dict | None = None, campose: str = "",
          detail: str | None = None, extra: str = "") -> list:
    """Same message layout as prompt.build_input: text first, then 'cam:' label + JPEG per camera sent (in
    cams_order). extra: one extra instruction line right before the mode rule line ('' = the adopted bytes)."""
    sent = [c for c in cams_order if images.get(c) is not None]
    text = TEMPLATE[mode].format(task=task, arm=arm, horizon=round(horizon_s, 1), campose=campose,
                                 cameras=camera_text(sent, arm), legend=legend_text(drawn, trace_s),
                                 events=events_text(req.get("events", [])),
                                 context=CONTEXT_RULE if "since_last_request" in req else "",
                                 mode_rules=extra_line(extra) + MODE_RULES[mode], req_open=CP.REQ_OPEN,
                                 request_json=json.dumps(req, sort_keys=True, ensure_ascii=False),
                                 req_close=CP.REQ_CLOSE, answer_form=ANSWER_FORM[mode])
    content = [{"type": "input_text", "text": text}]
    for cam in sent:
        content.append({"type": "input_text", "text": f"{cam}:"})
        part = {"type": "input_image", "image_url": "data:image/jpeg;base64," + base64.b64encode(images[cam]).decode()}
        if detail:
            part["detail"] = detail
        content.append(part)
    return [{"role": "user", "content": content}]
