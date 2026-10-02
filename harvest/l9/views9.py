"""Canonical camera-slot input schema for L9 rows (user 10-02, pi0.5-style fixed slots + masks): every row lists the four
view slots in a fixed order -- head, wrist_left, wrist_right, third_person -- each either with its image ("- view:
<slot> -- Image k: ...") or "- view: <slot> (none)". Head is always present; per row each wrist is kept with
probability wrist_keep (slot dropout); the third-person slot is filled only by the third-person switch. point_2d always
refers to Image 1 (view: head). The command carries "arm": left|right. `image_views` lists the slot of every image in
order (a trainer puts "view: <slot>" right before each image). Build-time only: nothing is re-rendered. Pure.

Spec r2-cams (user 10-03 02h "each robot uses its own cameras as they are; the number of cameras must not matter"):
the four standard slots stay first, in this order, with "(none)" markers; a robot's further NATIVE cameras follow as
extra tagged views ("- view: head_right -- Image k: ...", names from EXTRA_VIEWS), so robots with 1, 2, 5+ cameras
share one format. A slot the robot does not have natively is never filled (NATIVE_SLOTS: G1 = head only, its palm
cameras were ours, not Unitree's). view_label / view_line are the ONE tag function of builder, trainer and runtime;
specgate9.view_schema_errors is the gate."""
from __future__ import annotations

import hashlib
import json
import math
import re

import numpy as np

SLOTS = ("head", "wrist_left", "wrist_right", "third_person")
POINT_NOTE = "- point_2d always refers to Image 1 (view: head)."
# main 10-02 decision: one fixed sentence on every row (ego and third-person), build time only
FRAME_NOTE = "Directions in the task (left, right, front, behind) are in the robot's frame, not the camera image."
ARM_NOTE = ('- every command names its arm ("arm": "left"|"right"); a call may give one command, or two as '
            '"commands": [one per arm].')
_HEAD = re.compile(r"^- Image 1: (head camera[^\n]*)$", re.M)
_WRIST = re.compile(r"^- Image 2: ([^\n]*wrist camera[^\n]*)$", re.M | re.I)
_WRIST_POSE = re.compile(r"^- ((?:Right|Left|RIGHT|LEFT) wrist camera) \(image 2\): ([^\n]*)$", re.M)
_WRIST_NOTE = re.compile(r"^- The wrist image has no drawing\.\n", re.M)
_WRIST_VERIFY = re.compile(r"in the (?:right |left |RIGHT |LEFT )?wrist view( \(and the pad gap\))?")
_ROW = re.compile(r"^- view: ([a-z][a-z0-9_]*)(?: \(none\)| -- Image (\d+): [^\n]*)$", re.M)

# r2-cams: image labels of every view (standard slots + extra native views). Extra views: name -> (label, the request
# line's description before the camera pose text). Only these names pass the schema gate; a new robot's extra camera
# adds its name here (one place).
VIEW_LABELS = {"head": "head camera", "wrist_left": "left wrist camera", "wrist_right": "right wrist camera",
               "third_person": "third-person camera"}
EXTRA_VIEWS = {
    "head_right": ("right head camera", "right eye of the head stereo camera, fixed on the robot head"),
    "chest": ("chest camera", "chest camera, fixed on the robot body"),
    "torso": ("torso camera", "torso camera, fixed on the robot body"),
    "base_front": ("base front camera", "base camera looking forward, fixed on the mobile base"),
    "base_rear": ("base rear camera", "base camera looking backward, fixed on the mobile base"),
    "base_left": ("base left camera", "base camera looking left, fixed on the mobile base"),
    "base_right": ("base right camera", "base camera looking right, fixed on the mobile base"),
}
VIEW_LABELS.update({k: v[0] for k, v in EXTRA_VIEWS.items()})
# the standard robot-camera slots each robot has natively (docs/stage3/results/l9v2_gates.md "native cameras");
# third_person is a room camera, allowed for every robot. Unknown robots: head + both wrists (the pre-r2 default).
NATIVE_SLOTS = {"ffw_sg2": ("head", "wrist_left", "wrist_right"), "franka_mast": ("head", "wrist_right"),
                "r1pro": ("head", "wrist_left", "wrist_right"), "g1": ("head",)}


def native_slots(robot: str | None) -> tuple:
    return NATIVE_SLOTS.get(robot or "ffw_sg2", ("head", "wrist_left", "wrist_right"))


def view_label(view: str) -> str:
    """Image label of one view (trainer / runtime 'Image k: <label>'); KeyError for an unknown view name."""
    return VIEW_LABELS[view]


def view_line(view: str, k: int | None, desc: str = "") -> str:
    """The request line of one view: '- view: <view> (none)' or '- view: <view> -- Image k: <desc>'."""
    if view not in VIEW_LABELS:
        raise ValueError(f"unknown view {view!r}")
    return f"- view: {view} (none)" if k is None else f"- view: {view} -- Image {k}: {desc}"


def extra_desc(view: str, cam: dict | None) -> str:
    d = EXTRA_VIEWS[view][1]
    return f"{d}, {cam_text(cam)}" if cam is not None else d


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
              third: tuple | None, rng, wrist_keep: float = 0.7, source: str = "l9", anchor: str | None = None,
              robot: str | None = None, extras=()) -> dict:
    """One row in the 4-slot schema. used_wrist / other_wrist / third = (image path, cams.json record) or None.
    robot (r2-cams): a wrist slot the robot does not have natively (native_slots) stays "(none)" even when an image
    exists (G1 palm cameras). extras (r2-cams): [(view name in EXTRA_VIEWS, image path, cams record | None)] of the
    robot's further native cameras, appended after the 4 slots (always kept, in the given order).
    -> {"text", "answer", "images", "image_views", "slots": {slot: bool}}."""
    if len(_HEAD.findall(text)) != 1:
        raise ValueError("no single head 'Image 1' line")
    other = "wrist_left" if arm == "right" else "wrist_right"
    used = "wrist_right" if arm == "right" else "wrist_left"
    if robot is not None:
        nat = native_slots(robot)
        used_wrist = used_wrist if used in nat else None
        other_wrist = other_wrist if other in nat else None
    for e in extras:
        if e[0] not in EXTRA_VIEWS:
            raise ValueError(f"unknown extra view {e[0]!r}")
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
    xlines = []
    for name, img, cam in extras:
        images.append(img)
        views.append(name)
        xlines.append(view_line(name, len(images), extra_desc(name, cam)))
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
    block = "\n".join([lines[s] for s in SLOTS[1:]] + xlines) + "\n" + POINT_NOTE + "\n" + ARM_NOTE + "\n- " + FRAME_NOTE
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
        cam_lines += [slot_line(n, c, source) for n, _, c in extras if c is not None]
        if cam_lines:  # after the head camera line when there is one (slot order)
            add = "".join("- " + c + "\n" for c in cam_lines)
            m = re.search(r"^- camera: head,[^\n]*\n", out[out.index(anchor):], re.M)
            at = out.index(anchor) + (m.end() if m else len(anchor))
            out = out[:at] + add + out[at:]
    a = json.loads(answer)
    c = a.get("command")
    if isinstance(c, dict):
        c["arm"] = arm
    s = a.get("assessment") or {}
    if used not in idx and s.get("evidence_view") not in (None, "head"):
        s["evidence_view"] = "head"
    return {"text": out, "answer": json.dumps(a), "images": images, "image_views": views,
            "slots": {s: s in idx for s in SLOTS}}


def parse_views(text: str) -> list:
    """Every '- view:' line of a row text in order -> [(view, image index | None)]."""
    return [(m.group(1), int(m.group(2)) if m.group(2) else None) for m in _ROW.finditer(text)]


def parse_slots(text: str) -> dict:
    """The view block of a row text -> {view: image index | None}: the 4 standard slots first, in order, then any
    extra native views (r2-cams, names in EXTRA_VIEWS, never "(none)"); raises otherwise."""
    got = parse_views(text)
    if [g[0] for g in got[:4]] != list(SLOTS):
        raise ValueError(f"slots {[g[0] for g in got]}")
    for v, k in got[4:]:
        if v not in EXTRA_VIEWS or k is None:
            raise ValueError(f"extra view {v!r} {k!r}")
    if len({g[0] for g in got}) != len(got):
        raise ValueError(f"duplicate views {[g[0] for g in got]}")
    return dict(got)
