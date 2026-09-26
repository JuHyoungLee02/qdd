"""Astra coupling prompt astra-couple@v1: general control only (continue / edit / stop + assessment, GPT-as-Policy
gate wording), three labelled cameras with the wrist-evidence rule (spec §12), the code-drawn overlay legend
(spec §13, plan ruling 4: robot-frame axes at the tip). The static text comes first (prompt-cache friendly), the
request JSON (sorted keys) between REQ_OPEN / REQ_CLOSE, then the labelled images."""
from __future__ import annotations

import base64
import hashlib
import json

REQ_OPEN, REQ_CLOSE = "<request>", "</request>"
WRIST_OF = {"right": "cam_wrist_right", "left": "cam_wrist_left"}
TEMPLATE = (
    "You supervise a robot doing this task: {task}\n"
    "A fast policy (VLA) moves the {arm} gripper every 0.33 s and never waits for you. Your answer arrives seconds "
    "after these images were taken: judge the situation at predicted_ee_at_arrival.\n"
    "Cameras (each image is preceded by its name): cam_head = overview for layout, path and target choice; it is NOT "
    "enough on its own for contact, grasp or release (perspective makes fingers and objects overlap). cam_wrist_left "
    "/ cam_wrist_right = close-up of each gripper for contact, grasp, release and alignment. A claim that something "
    "is grasped, released, placed or touching is valid only with the active wrist camera ({wrist}) as evidence; if "
    "head and wrist disagree, trust the wrist.\n"
    "Overlay (drawn by code from the robot's own kinematics, never from object ground truth): white ring = gripper "
    "tip now; fading yellow line = the tip over the last {trace_s:g} s; cyan arrow = the motion the policy has "
    "committed for the next 0.5 s; magenta arrow = your previous correction still being applied; short red / green "
    "/ blue lines at the tip = robot frame x / y / z. On wrist images the overlay is only a small box in the "
    "top-right corner.\n"
    "Assess two things: (1) execution of the last seconds: not_started | progressing | failed | uncertain | "
    "recovered; (2) intent: does the policy's current motion pursue the right subgoal? aligned | misaligned | "
    "uncertain.\n"
    "Commands: continue = let the policy go on. edit = one short correction of the gripper tip in the robot frame: "
    "|delta_position_m| <= 0.05, |delta_rotation_rad| <= 0.35, gripper keep | open | close. An edit requires "
    "execution=failed or intent=misaligned; uncertainty alone or an imperfect pose is not a reason to take over. "
    "stop = the whole task is complete (needs a wrist claim placed or released). info_request slow_down asks the "
    "robot to move slower for 2 s when you need a clearer view; otherwise none.\n"
    "{mode_rules}\n"
    "{req_open}\n{request_json}\n{req_close}\n"
    "Answer with one JSON object only, in this form:\n{answer_form}")
MODE_RULES = {
    "F0": "Give the full command every time. A new edit is applied at half strength until your next answer repeats "
          "it.",
    "F1": "flow_state.last_command is the command being applied now. Answer diff=keep to confirm it, or "
          "diff=revise with a new command. A revised edit is applied at half strength until your next answer "
          "confirms it with keep."}
_ASSESS = ('"assessment": {"task_progress": {"verified_completed": ["..."], "currently_attempting": "...", '
           '"remaining": ["..."]}, "execution": "...", "intent": "...", "confidence": "low|medium|high", '
           '"evidence": "...", "evidence_views": ["cam_..."], "claims": [{"kind": '
           '"grasp_ready|grasped|not_grasped|released|placed|contact", "view": "cam_..."}]}')
_CMD = ('"command": "continue|edit|stop", "edit": {"delta_position_m": [dx, dy, dz], "delta_rotation_rad": '
        '[rx, ry, rz], "gripper": "keep|open|close"} (only with command edit, else null), '
        '"info_request": "none|slow_down"')
ANSWER_FORM = {"F0": "{" + _ASSESS + ", " + _CMD + "}",
               "F1": "{" + _ASSESS + ', "diff": "keep|revise", ' + _CMD + " (command only with diff revise)}"}
PROMPT_ID = {m: hashlib.sha256((TEMPLATE + MODE_RULES[m] + ANSWER_FORM[m]).encode()).hexdigest()[:12]
             for m in ("F0", "F1")}


def build_input(req: dict, images: dict, p, task: str) -> list:
    text = TEMPLATE.format(task=task, arm=p.active_arm, wrist=WRIST_OF[p.active_arm], trace_s=p.trace_s,
                           mode_rules=MODE_RULES[p.request_mode], req_open=REQ_OPEN,
                           request_json=json.dumps(req, sort_keys=True, ensure_ascii=False), req_close=REQ_CLOSE,
                           answer_form=ANSWER_FORM[p.request_mode])
    content = [{"type": "input_text", "text": text}]
    for cam in p.cameras:
        b = images.get(cam)
        if b is None:
            continue
        content.append({"type": "input_text", "text": f"{cam}:"})
        content.append({"type": "input_image", "image_url": "data:image/jpeg;base64," + base64.b64encode(b).decode()})
    return [{"role": "user", "content": content}]


def request_from_input(inp: list) -> dict:
    text = inp[-1]["content"][0]["text"]
    i = text.index(REQ_OPEN) + len(REQ_OPEN)
    return json.loads(text[i:text.index(REQ_CLOSE)])
