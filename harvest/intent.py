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
  serialize.SEGMENTS / SEGMENT_ACTIONS).
  R2 / pool lines: from the planner phase (segment_from_phase): now = PHASE_SEGMENT[phase] (1:1 rename), do = the
    gripper action inside that segment (grasp -> close, release -> open, else none), next = the planned successor
    phase (sim.snapshot.PHASE_ORDER; done -> done). An unknown phase -> the unknown line.
  S-E2E episodes: from the per-row gripper labels above in frame order (segments_from_events): a closing row =
    grasp / close / carry; an opening row = release / open / (approach if a later close exists, else retreat); a keep
    row takes the next event ahead: close ahead -> approach / none / grasp, open ahead -> carry / none / release; no
    event ahead: after a release -> retreat / none / unknown, after a grasp -> carry / none / unknown, no event at all
    -> the unknown line; a row whose gripper label is not derivable (None) -> the unknown line. S-E2E cannot separate approach from descend or lift / carry / place (no phases): approach =
    open before a grasp, carry = closed before a release.
The runtime segment line comes from Astra's agreed segment plan (coupling, a later task); until set it is unknown.
"""
from __future__ import annotations

from .serialize import SEGMENT_UNKNOWN, segment_line

KEYS = ("close", "open", "keep")
RATE_THR = 0.176  # openness / s (canon §83 se2e-motion@v1 gripper bin)
PHASE_SEGMENT = {"approach": "approach", "descend": "descend", "close": "grasp", "lift": "lift", "carry": "carry",
                 "place_descend": "place", "open": "release", "retreat": "retreat", "done": "done"}
SEGMENT_DO = {"grasp": "close", "release": "open"}


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
    from .sim.snapshot import PHASE_ORDER
    now = PHASE_SEGMENT.get(phase)
    if now is None:
        return SEGMENT_UNKNOWN
    i = PHASE_ORDER.index(phase)
    nxt = PHASE_SEGMENT[PHASE_ORDER[i + 1]] if i + 1 < len(PHASE_ORDER) else "done"
    return segment_line(now, SEGMENT_DO.get(now, "none"), nxt)


def segments_from_events(labels) -> list:
    """Segment-intent lines of one S-E2E episode from its per-row gripper labels (close / open / keep, frame order;
    None = not derivable for that row -> the unknown line, and it is no event for the other rows)."""
    labels = list(labels)
    out = []
    for i, g in enumerate(labels):
        later = labels[i + 1:]
        if g is None:
            out.append(SEGMENT_UNKNOWN)
        elif g == "close":
            out.append(segment_line("grasp", "close", "carry"))
        elif g == "open":
            out.append(segment_line("release", "open", "approach" if "close" in later else "retreat"))
        else:
            ahead = next((x for x in later if x in ("close", "open")), None)
            before = next((x for x in reversed(labels[:i]) if x in ("close", "open")), None)
            if ahead == "close":
                out.append(segment_line("approach", "none", "grasp"))
            elif ahead == "open":
                out.append(segment_line("carry", "none", "release"))
            elif before == "open":
                out.append(segment_line("retreat", "none", "unknown"))
            elif before == "close":
                out.append(segment_line("carry", "none", "unknown"))
            else:
                out.append(SEGMENT_UNKNOWN)
    return out
