"""Prompt variants for the prompt health check (user-log 96). Pure text functions, no model calls.

Every variant is built FROM the production text by checked string edits (a missing anchor raises), so a drift of the
production prompt breaks the tests instead of silently testing an old copy. The 'base' variants are byte-identical to
production (tests/prompt_health/test_variants.py):
  grasp   harvest/astra_motion/prompts.py GRASP_Q (probe G1 v2 grasp question)
  couple  harvest/couple/prompt.py astra-couple@v1 (F0), built with the production build_input
  frame   a short direction question in the couple prompt's own wording ('robot frame', |delta_position_m| <= 0.05),
          with / without an explicit axis definition (the couple prompt names the robot frame but never says which
          way x / y / z point; only the overlay axes show it)
Variant kinds: paraphrase (same content, other wording), option order reversed, camera order reversed, definition
ablation (grasp: the 'held' definition removed; couple: definitions / frame added = the proposed fix)."""
from __future__ import annotations

import hashlib

from harvest.astra_motion import prompts as PR
from harvest.couple import prompt as CP


def sha12(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:12]


def _sub(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"anchor not found exactly once: {old[:60]!r}")
    return text.replace(old, new)


# ----------------------------------------------------------------------------------------------- grasp question
GRASP_DEF_LINE = ("DEFINITION: 'held' means the two finger pads are CLOSED on the object (little or no gap between each "
                  "pad and the object) so that it would move with the gripper. Open fingers with the object between "
                  "them, fingers closed next to or in front of the object, or an object merely overlapping the fingers "
                  "in a view are NOT held. Judge the finger opening from the right wrist view.\n")
GRASP_JSON = ('Return JSON only: {{"grasp_state": "grasped"|"not_grasped"|"uncertain", "evidence_view": "head"|'
              '"right_wrist"|"left_wrist"|"multiple", "evidence": "<= 30 words", "confidence": "low"|"medium"|"high"}}')
GRASP_JSON_REV = ('Return JSON only: {{"grasp_state": "uncertain"|"not_grasped"|"grasped", "evidence_view": "multiple"|'
                  '"left_wrist"|"right_wrist"|"head", "evidence": "<= 30 words", "confidence": "high"|"medium"|"low"}}')

GRASP_PARA1 = """Below are camera images from a humanoid robot working at a table in simulation. Its right gripper faces downward and its two fingers close along the robot's forward axis. {views}
HOW TO USE THE VIEWS: use the head view only for the overall layout -- from that angle the fingers can appear to hold an object even when they do not. Touching or grasping can only be confirmed in a wrist view (the right wrist camera looks between the right fingers). If the views disagree, go with the wrist view.
WHAT 'HELD' MEANS: the object counts as held only if both finger pads are CLOSED on it (no or almost no gap between each pad and the object), so that it would move together with the gripper. Not held: fingers open with the object between them; fingers closed beside or in front of the object; the object only overlapping the fingers in an image. Decide how open the fingers are from the right wrist view.
QUESTION: right now, is the {tgt_name} grasped (held) by the RIGHT gripper?
""" + GRASP_JSON

GRASP_PARA2 = """Simulation, humanoid robot at a table, right arm. Right gripper points down; fingers close along the robot's forward direction. {views}
Views: head = layout only (perspective may fake a grasp); grasp/contact must be judged from a wrist view (right wrist camera = between the right fingers); wrist beats head on conflict.
Held = both pads CLOSED on the object, (almost) no pad-object gap, object would move with the gripper. NOT held = open fingers around the object, closed fingers beside / in front of it, or mere overlap in the image. Judge finger opening in the right wrist view.
Is the {tgt_name} held (grasped) by the RIGHT gripper now?
""" + GRASP_JSON

GRASP_PARA3 = """QUESTION: is the {tgt_name} held (grasped) by the RIGHT gripper right now? Read the rules below before answering.
SETTING: cameras of a humanoid robot's right arm at a table (simulation). The right gripper points down; its two fingers close along the robot's forward axis. {views}
EVIDENCE: the head view gives the layout, but its perspective can make fingers look as if they hold an object when they do not. Contact and grasp can be verified only from a wrist view (the right wrist camera sees between the right fingers). If they conflict, the wrist view wins.
DEFINITION OF HELD: the two finger pads are CLOSED on the object (little or no gap between each pad and the object) so that it would move with the gripper. Open fingers with the object between them, fingers closed next to or in front of the object, or an object merely overlapping the fingers in a view are NOT held. Judge the finger opening from the right wrist view.
""" + GRASP_JSON

GRASP_VIEWS_REV = ("Image 1: RIGHT wrist camera. Image 2: head camera. Image 3: LEFT wrist camera (idle left arm).")
GRASP_ORDER = {"base": ("head", "wrist_left", "wrist"), "camrev": ("wrist", "head", "wrist_left")}
GRASP_VARIANTS = ("base", "para1", "para2", "para3", "optrev", "camrev", "nodef")
GRASP_PARAPHRASES = ("para1", "para2", "para3")


def grasp_prompt(variant: str, tgt_name: str) -> tuple[str, tuple]:
    """(text, camera order) for the all-three-cameras condition of the probe's G1 v2."""
    views = PR.GRASP_VIEWS["all3"]
    order = GRASP_ORDER["base"]
    if variant == "base":
        tpl = PR.GRASP_Q
    elif variant in GRASP_PARAPHRASES:
        tpl = {"para1": GRASP_PARA1, "para2": GRASP_PARA2, "para3": GRASP_PARA3}[variant]
    elif variant == "optrev":
        tpl = _sub(PR.GRASP_Q, GRASP_JSON, GRASP_JSON_REV)
    elif variant == "camrev":
        tpl, views, order = PR.GRASP_Q, GRASP_VIEWS_REV, GRASP_ORDER["camrev"]
    elif variant == "nodef":
        tpl = _sub(PR.GRASP_Q, GRASP_DEF_LINE, "")
    else:
        raise ValueError(variant)
    return tpl.format(views=views, tgt_name=tgt_name), order


# ----------------------------------------------------------------------------------------------- couple prompt
COUPLE_DEFS = ("Definitions for claims and progress: grasped = both finger pads are CLOSED on the object (little or no "
               "gap between each pad and the object) so that it moves with the gripper; open fingers with the object "
               "between them, fingers closed next to or in front of it, or an object that merely overlaps the fingers "
               "in a view are NOT grasped. released = the pads are open and the object no longer moves with the "
               "gripper. placed = the object rests upright on its target and is released. contact = a finger or pad "
               "touches the object. grasp_ready = the open pads surround the object at grasp height.\n")
COUPLE_FRAME = ("Robot frame: origin at the robot base, x forward (away from the robot), y to the robot's left, z up; "
                "positions and deltas in metres, rotations as rotation vectors in radians.\n")
_ANCHOR_OVERLAY = "Overlay (drawn by code"
_ANCHOR_ASSESS = ("Assess two things: (1) execution of the last seconds: not_started | progressing | failed | uncertain | "
                  "recovered; (2) intent: does the policy's current motion pursue the right subgoal? aligned | misaligned | "
                  "uncertain.\n")
_ANCHOR_CMDS = ("Commands: continue = let the policy go on. edit = one short correction of the gripper tip in the robot frame: "
                "|delta_position_m| <= 0.05, |delta_rotation_rad| <= 0.35, gripper keep | open | close. An edit requires "
                "execution=failed or intent=misaligned; uncertainty alone or an imperfect pose is not a reason to take over. "
                "stop = the whole task is complete (needs a wrist claim placed or released). info_request slow_down asks the "
                "robot to move slower for 2 s when you need a clearer view; otherwise none.\n")
_ANCHOR_CAMS_START = "Cameras (each image is preceded by its name): "
_ANCHOR_CAMS_END = "if head and wrist disagree, trust the wrist.\n"

COUPLE_PARA1_ASSESS_CMDS = (
    "Judge two separate things. (1) How did the last few seconds of execution go? Pick one of not_started | "
    "progressing | failed | uncertain | recovered. (2) Is the policy's current motion heading for the correct subgoal? "
    "Pick aligned | misaligned | uncertain.\n"
    "Then pick a command. continue: the policy keeps going on its own. edit: a single small correction of the gripper "
    "tip, expressed in the robot frame, with |delta_position_m| <= 0.05 and |delta_rotation_rad| <= 0.35 and gripper "
    "keep | open | close. Only edit when execution=failed or intent=misaligned; being unsure, or a pose that is merely "
    "not perfect, does not justify taking over. stop: the entire task is finished (this needs a placed or released "
    "claim seen in the wrist camera). info_request: slow_down makes the robot move slower for 2 s if you need a clearer "
    "view; otherwise none.\n")
COUPLE_PARA2_CAMS = (
    "Camera guide (the name of each camera is written just before its image): cam_head gives the overview -- use it "
    "for layout, the path and which target to choose; on its own it cannot settle contact, grasp or release, because "
    "in perspective fingers and objects can appear to overlap. cam_wrist_left and cam_wrist_right are close-ups of the "
    "left and right gripper, for contact, grasp, release and alignment. Any claim that something is grasped, released, "
    "placed or touching counts only if the active wrist camera ({wrist}) shows it; when the head and the wrist "
    "disagree, believe the wrist.\n")


def _rev_enums(s: str) -> str:
    for a, b in (("not_started | progressing | failed | uncertain | recovered",
                  "recovered | uncertain | failed | progressing | not_started"),
                 ("aligned | misaligned | uncertain", "uncertain | misaligned | aligned"),
                 ("gripper keep | open | close", "gripper close | open | keep")):
        s = _sub(s, a, b)
    return s


def _rev_answer_form(s: str) -> str:
    for a, b in (('"low|medium|high"', '"high|medium|low"'),
                 ('"grasp_ready|grasped|not_grasped|released|placed|contact"',
                  '"contact|placed|released|not_grasped|grasped|grasp_ready"'),
                 ('"continue|edit|stop"', '"stop|edit|continue"'), ('"keep|open|close"', '"close|open|keep"'),
                 ('"none|slow_down"', '"slow_down|none"')):
        s = _sub(s, a, b)
    return s


COUPLE_VARIANTS = ("base", "def", "v2", "para1", "para2", "optrev", "camrev")
COUPLE_PARAPHRASES = ("para1", "para2")


def couple_template(variant: str, mode: str = "F0") -> tuple[str, str, str]:
    """(TEMPLATE, MODE_RULES[mode], ANSWER_FORM[mode]) of a variant; base = production."""
    t, mr, af = CP.TEMPLATE, CP.MODE_RULES[mode], CP.ANSWER_FORM[mode]
    if variant in ("base", "camrev"):
        return t, mr, af
    if variant == "def":
        return _sub(t, _ANCHOR_OVERLAY, COUPLE_DEFS + _ANCHOR_OVERLAY), mr, af
    if variant == "v2":
        t = _sub(t, _ANCHOR_OVERLAY, COUPLE_DEFS + COUPLE_FRAME + _ANCHOR_OVERLAY)
        return t, mr, af
    if variant == "para1":
        return _sub(t, _ANCHOR_ASSESS + _ANCHOR_CMDS, COUPLE_PARA1_ASSESS_CMDS), mr, af
    if variant == "para2":
        i, j = t.index(_ANCHOR_CAMS_START), t.index(_ANCHOR_CAMS_END) + len(_ANCHOR_CAMS_END)
        return t[:i] + COUPLE_PARA2_CAMS + t[j:], mr, af
    if variant == "optrev":
        return _rev_enums(t), mr, _rev_answer_form(af)
    raise ValueError(variant)


def couple_input(variant: str, req: dict, images: dict, p, task: str) -> list:
    """Same structure as harvest.couple.prompt.build_input (text first, then 'cam:' label + image per camera)."""
    import base64
    import json
    t, mr, af = couple_template(variant, p.request_mode)
    text = t.format(task=task, arm=p.active_arm, wrist=CP.WRIST_OF[p.active_arm], trace_s=p.trace_s, mode_rules=mr,
                    req_open=CP.REQ_OPEN, request_json=json.dumps(req, sort_keys=True, ensure_ascii=False),
                    req_close=CP.REQ_CLOSE, answer_form=af)
    cams = list(p.cameras)
    if variant == "camrev":
        cams = cams[::-1]
    content = [{"type": "input_text", "text": text}]
    for cam in cams:
        b = images.get(cam)
        if b is None:
            continue
        content.append({"type": "input_text", "text": f"{cam}:"})
        content.append({"type": "input_image", "image_url": "data:image/jpeg;base64," + base64.b64encode(b).decode()})
    return [{"role": "user", "content": content}]


# ----------------------------------------------------------------------------------------------- frame question
FRAME_BASE = ("You supervise a robot doing this task: {task}\n"
              "Cameras (each image is preceded by its name): cam_head = overview for layout, path and target choice. "
              "cam_wrist_right = close-up of the right gripper.\n"
              "{frame}"
              "Give one short correction of the right gripper tip in the robot frame that moves it toward the {target}: "
              "|delta_position_m| <= 0.05.\n"
              "Answer with one JSON object only, in this form:\n"
              '{{"delta_position_m": [dx, dy, dz]}}')
FRAME_DEFS = {"prod": "",
              "frame": COUPLE_FRAME,
              "frame_para": ("Axes of the robot frame: +x points away from the robot (forward), +y points to the robot's "
                             "left-hand side, +z points up; metres.\n")}
FRAME_OVERLAY_VARIANTS = ("prod_ov", "frame_ov")  # same text; the head image carries the production coupling overlay
FRAME_VARIANTS = tuple(FRAME_DEFS) + FRAME_OVERLAY_VARIANTS


def frame_prompt(variant: str, task: str, target: str) -> str:
    return FRAME_BASE.format(task=task, target=target, frame=FRAME_DEFS[variant.removesuffix("_ov")])
