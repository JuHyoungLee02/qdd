"""E-STRIP8 request stripping (prereg_strip8.md §1): remove hand-given scene / recipe information from an
astra-solo@v2 request (or from an E-PT nd-xyz@v1 request of the same state), field by field. Fields (canon §97
inventory numbers in brackets):
  table    the table-top height line and the numeric workspace z range derived from it [2, 3] -> the nd-xyz line
           ("not given: judge it from the images", x / y box kept, z in words)
  overlay  the grid + drop-line legend [20, 22] (both drawn at the known table height) -> the ring-only legend of
           nd-xyz; the image must then be the ring-only head image (the caller switches it); the v2 "outside the
           image" note becomes the nd note
  sizes    object shapes and sizes [17] -> names and roles only ("- red mug (the object to move)")
  recipes  the grasp and put-down recipes and the "lift before moving sideways" advice [10, 11, 12]
Kept in every request: robot frame, the robot's gripper geometry, commands, camera poses, definitions, the TCP ring,
NOW (TCP, pad gap, wrist camera pose) and the measured history (robot self-information, canon §97 category R), the
task sentence, object names / roles and the success rule. S-min = all four fields removed."""
from __future__ import annotations

import hashlib
import re

from ..astra_motion.prompts import OBJ_DESC
from ..astra_solo import nd_prompts as NP

VERSION = "strip8-min@v1"
FIELDS = ("table", "overlay", "sizes", "recipes")
P_ALL = 0.3
P_EACH = 0.5

_TABLE_RE = re.compile(r"- Table top surface: z = -?[\d.]+ m\. The code keeps the TCP inside x (-?[\d.]+)\.\.(-?[\d.]+), "
                       r"y (-?[\d.]+)\.\.(-?[\d.]+), z -?[\d.]+\.\.-?[\d.]+ m \(targets beyond are clipped, and you "
                       r"are told\)\.")
_TABLE_ND_HEAD = "- The table height is not given: judge it from the images."
_NOTE_TCP_V2 = "\nNOTE: the TCP is outside the head image this time: no ring and no drop line are drawn."
_NOTE_DROP_V2 = ("\nNOTE: the table point below the TCP is outside the head image this time: the drop line leaves "
                 "the image and its dot is not visible.")
_NOTE_TCP_ND = "\nNOTE: the TCP is outside the head image this time: no ring is drawn."
_OBJ_HEAD_V2 = "OBJECTS (name: shape; other objects on the table are obstacles, do not touch them)"
_OBJ_HEAD_MIN = "OBJECTS (other objects on the table are obstacles, do not touch them)"
_RECIPE_STARTS = ("- Grasping an upright object of height h", "- Putting a held object down:")
_LIFT_V2 = "Moves are straight lines: lift before moving sideways over objects."
_LIFT_MIN = "Moves are straight lines."


def _table(t: str) -> str:
    m = _TABLE_RE.search(t)
    if m is None:
        if _TABLE_ND_HEAD in t:
            return t
        raise ValueError("strip: no table line found")
    x0, x1, y0, y1 = (float(v) for v in m.groups())
    nd = NP._TABLE_ND.format(x0=x0, x1=x1, y0=y0, y1=y1)
    return t[:m.start()] + nd + t[m.end():]


def _overlay(t: str) -> str:
    if NP._OVL_V2 in t:
        t = t.replace(NP._OVL_V2, NP._OVL_ND)
        if t.endswith(_NOTE_TCP_V2):
            t = t[:-len(_NOTE_TCP_V2)] + _NOTE_TCP_ND
        elif t.endswith(_NOTE_DROP_V2):
            t = t[:-len(_NOTE_DROP_V2)]
        return t
    if NP._OVL_ND in t:
        return t
    raise ValueError("strip: no overlay legend found")


def _sizes(t: str) -> str:
    if _OBJ_HEAD_V2 not in t:
        if _OBJ_HEAD_MIN in t:
            return t
        raise ValueError("strip: no OBJECTS block found")
    head, rest = t.split(_OBJ_HEAD_V2, 1)
    block, sep, tail = rest.partition("\n\n")
    lines = []
    for ln in block.split("\n"):
        if ln.startswith("- "):
            for desc in sorted(OBJ_DESC.values(), key=len, reverse=True) + ["object"]:
                k = ln.find(": " + desc)
                if k > 0:
                    ln = ln[:k] + ln[k + 2 + len(desc):]
                    break
            else:
                raise ValueError(f"strip: unknown object line {ln!r}")
        lines.append(ln)
    return head + _OBJ_HEAD_MIN + "\n".join(lines) + sep + tail


def _recipes(t: str) -> str:
    out, found = [], False
    for ln in t.split("\n"):
        if ln.startswith(_RECIPE_STARTS):
            found = True
            continue
        out.append(ln)
    t2 = "\n".join(out)
    if _LIFT_V2 in t2:
        t2, found = t2.replace(_LIFT_V2, _LIFT_MIN), True
    if not found and _LIFT_MIN not in t2:
        raise ValueError("strip: no recipe lines found")
    return t2


_OPS = {"table": _table, "overlay": _overlay, "sizes": _sizes, "recipes": _recipes}


def strip(text: str, drop) -> str:
    """Remove the fields in `drop` (subset of FIELDS) from a v2 / nd-xyz request; the other parts stay byte-identical."""
    drop = set(drop)
    bad = drop - set(FIELDS)
    if bad:
        raise ValueError(f"unknown fields {sorted(bad)}")
    for f in FIELDS:
        if f in drop:
            text = _OPS[f](text)
    return text


def minimal(text: str) -> str:
    return strip(text, FIELDS)


def sample_drops(rng, p_all: float = P_ALL, p_each: float = P_EACH) -> frozenset:
    """Privileged-information dropout draw: all fields with p_all, else each field independently with p_each."""
    if rng.random() < p_all:
        return frozenset(FIELDS)
    return frozenset(f for f in FIELDS if rng.random() < p_each)


PROMPT_ID = hashlib.sha256((VERSION + "|" + NP.PROMPT_IDS["nd-xyz@v1"] + "|" + _OBJ_HEAD_MIN + "|" + _LIFT_MIN + "|"
                            + "|".join(_RECIPE_STARTS)).encode()).hexdigest()[:12]
