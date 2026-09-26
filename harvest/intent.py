"""Decision-intent label rules of serializer ser-A-min-3 (plan 2026-09-26 Task 12) -- the ONE place for them.

Gripper decision question (canon §87, user-log 93-94): options close / open / keep (+ NONE_ESCALATE, canon §27 R1).
  R2 / pool (sim) lines: from the recorded planner phase at the snapshot (the "oracle phase"): the `close` phase ->
    close, the `open` phase -> open, anything else -> keep (from_phase).
  S-E2E (real teleop): from the recorded gripper JOINT COMMAND over the decision-label horizon (se2e_data.HORIZON_S
    = 1/3 s -> label_steps, the same window as the direction labels): openness rate r = (open(cmd[k + n]) -
    open(cmd[k])) / (n / fps), openness per stageb_data.GRIP_CAL; r > RATE_THR -> open, r < -RATE_THR -> close,
    else keep (from_openness). RATE_THR = the se2e-motion@v1 gripper bin 0.176 /s (canon §83), strict comparison
    like the motion line (a rate exactly at the threshold is keep).
Segment-intent line (canon §90, user-log 100): `segment: now=<segment> do=<action> next=<segment>` (vocabulary in
  serialize.SEGMENTS / SEGMENT_ACTIONS). Fix round 1 (controller ruling F12): a segment CONTAINS its gripper event --
  §90: Astra names the segment and the action to do in it, the VLA decides WHEN within the segment -- so the segment
  line is the same before and during the event, both keep and the event label occur inside one segment, and the
  line never tells the gripper answer (tests/test_intent.py).
  R2 / pool lines: from the planner phase (segment_from_phase): approach / descend / close -> approach (do=close,
    next=carry); lift / carry / place_descend / open -> carry (do=open, next=retreat); retreat -> retreat (do=none,
    next=done); done -> done (none, done). An unknown phase -> the unknown line.
  S-E2E episodes: from the per-row gripper labels above in frame order (segments_from_events): a row takes the first
    event at or after it (its own label included): close -> approach / close / carry; open -> carry / open /
    (approach if a close follows that release, else retreat); no event at or after it: after a release -> retreat /
    none / done, after a grasp -> carry / none / unknown (holding at the end, no release recorded), no event at all
    -> the unknown line; a row whose gripper label is not derivable (None) -> the unknown line and no event.
The runtime segment line comes from Astra's agreed segment plan (coupling, a later task); until set it is unknown --
training shows unknown too with p SEGMENT_DROPOUT (segment_dropout, training only, like the motion line's §83 p 0.3).
"""
from __future__ import annotations

import hashlib
import re

from .serialize import SEGMENT_UNKNOWN, segment_line

KEYS = ("close", "open", "keep")
RATE_THR = 0.176  # openness / s (canon §83 se2e-motion@v1 gripper bin)
PHASE_SEGMENT = {"approach": "approach", "descend": "approach", "close": "approach", "lift": "carry", "carry": "carry",
                 "place_descend": "carry", "open": "carry", "retreat": "retreat", "done": "done"}
SEGMENT_PLAN = {"approach": ("close", "carry"), "carry": ("open", "retreat"), "retreat": ("none", "done"),
                "done": ("none", "done")}  # segment -> (do, next) of the planned R2 order
# Astra's segment-plan names (serialize.SEGMENTS, the E-ACC v2 answer) -> the line segment that contains them
PLAN_TO_LINE = {"approach": "approach", "descend": "approach", "grasp": "approach", "lift": "carry", "carry": "carry",
                "place": "carry", "release": "carry", "retreat": "retreat", "done": "done"}
SEGMENT_DROPOUT = 0.3  # = se2e_temporal.MOTION_DROPOUT (canon §83 line dropout, training only)


def from_phase(phase) -> str:
    """Gripper decision label of a sim snapshot from its recorded planner phase."""
    return "close" if phase == "close" else "open" if phase == "open" else "keep"


def from_openness(open_now: float, open_then: float, window_s: float, thr: float = RATE_THR) -> str:
    """Gripper decision label from the commanded openness now and one label window later."""
    if not window_s > 0:
        raise ValueError(f"label window {window_s!r} s: must be > 0")
    r = (float(open_then) - float(open_now)) / float(window_s)
    return "open" if r > thr else "close" if r < -thr else "keep"


def segment_from_phase(phase) -> str:
    """Segment-intent line of a sim snapshot from its recorded planner phase."""
    now = PHASE_SEGMENT.get(phase)
    if now is None:
        return SEGMENT_UNKNOWN
    return segment_line(now, *SEGMENT_PLAN[now])


def segments_from_events(labels) -> list:
    """Segment-intent lines of one S-E2E episode from its per-row gripper labels (close / open / keep, frame order;
    None = not derivable for that row -> the unknown line, and it is no event for the other rows)."""
    labels = list(labels)
    ev = [(j, g) for j, g in enumerate(labels) if g in ("close", "open")]
    out = []
    for i, g in enumerate(labels):
        if g is None:
            out.append(SEGMENT_UNKNOWN)
            continue
        ahead = next(((j, x) for j, x in ev if j >= i), None)
        if ahead is not None and ahead[1] == "close":
            out.append(segment_line("approach", "close", "carry"))
        elif ahead is not None:  # a release at or after this row
            later_close = any(x == "close" for j, x in ev if j > ahead[0])
            out.append(segment_line("carry", "open", "approach" if later_close else "retreat"))
        else:
            before = next((x for j, x in reversed(ev) if j < i), None)
            out.append(segment_line("retreat", "none", "done") if before == "open" else
                       segment_line("carry", "none", "unknown") if before == "close" else SEGMENT_UNKNOWN)
    return out


# ------------------------------------------------------------------------------------------ unknown-segment share
_SEG_LINE = re.compile(r"(?m)^segment: now=\S+ do=\S+ next=\S+$")


def drop_segment(text: str) -> str:
    """The text with its segment-intent line replaced by the unknown line (the runtime's value until Astra's plan)."""
    return _SEG_LINE.sub(SEGMENT_UNKNOWN, text)


def segment_dropped(key: str, step: int, seed: int, p: float = SEGMENT_DROPOUT) -> bool:
    """Whether a training sample shows the unknown segment line at this optimizer step: a hash of (seed, step, key),
    so every item of one snapshot drops together (prefix sharing) and no training RNG is touched."""
    if p <= 0:
        return False
    h = hashlib.sha256(f"segdrop|{int(seed)}|{int(step)}|{key}".encode()).digest()
    return int.from_bytes(h[:8], "big") / 2 ** 64 < p


def segment_dropout(batch, step: int, seed: int, p: float = SEGMENT_DROPOUT) -> list:
    """Stage-B training batch (samples with context.text + items[].text) with each sample's segment line replaced by
    the unknown line with probability p (segment_dropped on the sample key). Shallow copies; evaluation never drops."""
    out = []
    for s in batch:
        if segment_dropped(s["key"], step, seed, p):
            s = {**s, "context": {**s["context"], "text": drop_segment(s["context"]["text"])},
                 "items": [{**it, "text": drop_segment(it["text"])} for it in s["items"]]}
        out.append(s)
    return out


def with_segment_dropout(batch_fn, p: float, seed: int):
    """A stage-B training batch transform (stageb_train.train_loop batch_fn): the given one (e.g. the motion-line
    dropout, or None) followed by segment_dropout; p <= 0 -> batch_fn unchanged."""
    if p <= 0:
        return batch_fn

    def f(batch, step):
        return segment_dropout(batch_fn(batch, step) if batch_fn is not None else batch, step, seed, p)
    return f


def segment_dropout_items(items, step: int, seed: int, p: float = SEGMENT_DROPOUT) -> list:
    """Stage-A training items (one per question, text) -- the same rule on the item's snapshot key."""
    return [{**it, "text": drop_segment(it["text"])} if segment_dropped(it["key"], step, seed, p) else it
            for it in items]
