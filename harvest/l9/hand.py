"""L9 `hand` field (spec §4): the top-level output D gets one field `hand: left|right`; rows / answers without it are
right-arm rows (L8S). Left-arm requests say LEFT where the right-arm request says RIGHT (the wrist image is the used
arm's wrist). Pure."""
from __future__ import annotations

import json

HANDS = ("right", "left")
# (right-arm wording, left-arm wording): every place the L8S request names the right arm / its wrist camera
_SWAPS = (("RIGHT wrist camera", "LEFT wrist camera"), ("Right wrist camera", "Left wrist camera"),
          ("right wrist camera", "left wrist camera"), ("the right hand", "the left hand"),
          ("the right gripper", "the left gripper"), ("right_wrist", "left_wrist"), ("right gripper", "left gripper"),
          ("right hand", "left hand"), ("right arm", "left arm"), ("RIGHT arm", "LEFT arm"))
HAND_FIELD = ', "hand": "left"|"right" (point only; the arm that moves, default right)'


def left_text(text: str) -> str:
    """The right-arm request text -> the left-arm one (arm / wrist wording only)."""
    out = text
    for a, b in _SWAPS:
        out = out.replace(a, "\0" + b.replace(" ", "\1"))
    return out.replace("\0", "").replace("\1", " ")


def add_hand_format(text: str) -> str:
    """Add the hand field to the command JSON format line (after "point_2d": ... ) once."""
    key = '"height": "above"|"grasp"|"place"|"lift" (point only)'
    if HAND_FIELD in text or key not in text:
        return text
    return text.replace(key, key + HAND_FIELD, 1)


def with_hand(answer: str | None, hand: str) -> str | None:
    """A JSON answer string with command.hand set (point commands only; other modes unchanged)."""
    if answer is None:
        return None
    if hand not in HANDS:
        raise ValueError(f"hand {hand!r}")
    d = json.loads(answer)
    c = d.get("command")
    if isinstance(c, dict) and c.get("mode") == "point":
        c["hand"] = hand
    return json.dumps(d)


def hand_of(cmd: dict) -> str:
    return (cmd or {}).get("hand") or "right"
