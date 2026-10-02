"""Canonical camera-slot input schema for L9 rows (user 10-02, pi0.5-style fixed slots + masks): every row lists the four
view slots in a fixed order -- head, wrist_left, wrist_right, third_person -- each either with its image ("- view:
<slot> -- Image k: ...") or "- view: <slot> (none)". Head is always present; per row each wrist is kept with
probability wrist_keep (slot dropout); the third-person slot is filled only by the third-person switch. point_2d always
refers to Image 1 (view: head). The command carries "arm": left|right. `image_views` lists the slot of every image in
order (a trainer puts "view: <slot>" right before each image). Build-time only: nothing is re-rendered. Pure."""
from __future__ import annotations

import hashlib
import json
import math
import re

import numpy as np

SLOTS = ("head", "wrist_left", "wrist_right", "third_person")
POINT_NOTE = "- point_2d always refers to Image 1 (view: head)."
ARM_NOTE = ('- every command names its arm ("arm": "left"|"right"); a call may give one command, or two as '
            '"commands": [one per arm].')
_HEAD = re.compile(r"^- Image 1: (head camera[^\n]*)$", re.M)
_WRIST = re.compile(r"^- Image 2: ([^\n]*wrist camera[^\n]*)$", re.M | re.I)
_WRIST_POSE = re.compile(r"^- ((?:Right|Left|RIGHT|LEFT) wrist camera) \(image 2\): ([^\n]*)$", re.M)
_WRIST_NOTE = re.compile(r"^- The wrist image has no drawing\.\n", re.M)
_WRIST_VERIFY = re.compile(r"in the (?:right |left |RIGHT |LEFT )?wrist view( \(and the pad gap\))?")
_ROW = re.compile(r"^- view: (head|wrist_left|wrist_right|third_person)(?: \(none\)| -- Image (\d+): [^\n]*)$", re.M)


def row_rng(row_id: str, seed: int = 0) -> np.random.Generator:
    """Per-row generator (the off and on builds draw the same slots for the same row)."""
    h = int(hashlib.sha256(f"{seed}:{row_id}".encode()).hexdigest()[:12], 16)
    return np.random.default_rng(h)


def hfov_deg(cam: dict) -> float:
    return math.degrees(2 * math.atan(float(cam["W"]) / 2 / float(cam["fx"])))


def slot_line(slot: str, cam: dict, source: str) -> str:
    """`camera: <slot>, ...` in the same units for every slot (px, intrinsics, height above the floor m, pitch / pan
    deg, hfov deg)."""
    from . import hcam9 as HC
    s = HC.line(cam, source).replace("camera: head,", f"camera: {slot},", 1)
    return s.replace("; source:", f", hfov {hfov_deg(cam):.0f} deg; source:", 1)


def cam_text(cam: dict) -> str:
    from ..astra_motion.prompts import CAM
    return CAM.format(W=cam["W"], H=cam["H"], t=list(cam["t"]), R=np.asarray(cam["R"], float).tolist())


def canonical(text: str, answer: str, arm: str, head_img: str, used_wrist: tuple | None, other_wrist: tuple | None,
              third: tuple | None, rng, wrist_keep: float = 0.7, source: str = "l9", anchor: str | None = None) -> dict:
    """One row in the 4-slot schema. used_wrist / other_wrist / third = (image path, cams.json record) or None.
    -> {"text", "answer", "images", "image_views", "slots": {slot: bool}}."""
    if len(_HEAD.findall(text)) != 1:
        raise ValueError("no single head 'Image 1' line")
    other = "wrist_left" if arm == "right" else "wrist_right"
    used = "wrist_right" if arm == "right" else "wrist_left"
    have = {"head": (head_img, None)}
    if used_wrist is not None and rng.random() < wrist_keep:
        have[used] = used_wrist
    if other_wrist is not None and rng.random() < wrist_keep:
        have[other] = other_wrist
    if third is not None:
        have["third_person"] = third
    idx, images, views = {}, [], []
    for s in SLOTS:
        if s in have:
            images.append(have[s][0])
            views.append(s)
            idx[s] = len(images)
    wl = _WRIST.findall(text)
    out = _HEAD.sub(lambda m: "- view: head -- Image 1: " + m.group(1), text)
    lines = {}
    for s in SLOTS[1:]:
        if s not in idx:
            lines[s] = f"- view: {s} (none)"
        elif s == used and wl:
            lines[s] = f"- view: {s} -- Image {idx[s]}: {wl[0]}"
        elif s in (used, other):
            side = s.split("_")[1].upper()
            lines[s] = (f"- view: {s} -- Image {idx[s]}: {side} wrist camera, moves with the {side.lower()} hand and "
                        f"looks down between the fingers, {cam_text(have[s][1])}")
        else:
            lines[s] = (f"- view: {s} -- Image {idx[s]}: third-person camera, fixed in the room (not on the robot), "
                        f"{cam_text(have[s][1])}")
    block = "\n".join(lines[s] for s in SLOTS[1:]) + "\n" + POINT_NOTE + "\n" + ARM_NOTE
    out = _WRIST.sub("", out) if wl else out
    out = re.sub(r"^(- view: head -- Image 1: [^\n]*)$", lambda m: m.group(1) + "\n" + block, out, count=1, flags=re.M)
    out = re.sub(r"\n\n+(?=- view: wrist_left)", "\n", out)
    out = out.replace("\n\n- view:", "\n- view:")
    if used in idx:  # the used wrist's pose line under NOW: its new image number
        out = _WRIST_POSE.sub(lambda m: f"- {m.group(1)} (image {idx[used]}): {m.group(2)}", out)
    else:
        out = _WRIST_POSE.sub("", out)
        out = _WRIST_NOTE.sub("", out)
        out = _WRIST_VERIFY.sub("with the pad gap (no wrist image this time)", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    if anchor and anchor in out:
        cam_lines = [slot_line(s, have[s][1], source) for s in SLOTS[1:] if s in have and have[s][1] is not None]
        if cam_lines:
            out = out.replace(anchor, anchor + "".join("- " + c + "\n" for c in cam_lines), 1)
    a = json.loads(answer)
    c = a.get("command")
    if isinstance(c, dict):
        c["arm"] = arm
    s = a.get("assessment") or {}
    if used not in idx and s.get("evidence_view") not in (None, "head"):
        s["evidence_view"] = "head"
    return {"text": out, "answer": json.dumps(a), "images": images, "image_views": views,
            "slots": {s: s in idx for s in SLOTS}}


def parse_slots(text: str) -> dict:
    """The 4-slot block of a row text -> {slot: image index | None}; raises if a slot is missing or out of order."""
    got = [(m.group(1), int(m.group(2)) if m.group(2) else None) for m in _ROW.finditer(text)]
    if [g[0] for g in got] != list(SLOTS):
        raise ValueError(f"slots {[g[0] for g in got]}")
    return dict(got)
