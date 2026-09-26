"""Minimal serialization (candidate-A shape, E §1.4 measurement format) + J2 canonicalization (canon §28)."""
import re
import unicodedata

SERIALIZER_VERSION = "ser-A-min-3"
# -2 (canon §77, R7 cycle 12 D3): every DecCall state ends with the M4 (b) category line of the last finished
# decision step, `last_step: <category>` (M4 §4.2 `next_jev_input.add_line(f"last_step: {s.outcome}")`); "none" =
# no step checked yet / no check in the data / the category withheld (C5', conditions without (b)).
# -3 (canon §83, §90, plan 2026-09-26 Task 12): the segment-intent line `segment: now=<..> do=<..> next=<..>` (§90:
# current segment, the gripper action in it, next segment; names only) and the motion line `motion: arm=<..>
# gripper=<..>` (se2e-motion@v1 bins, causal backward differences) sit before the last_step line, in this order:
# state -> segment -> motion -> last_step. "unknown" where no plan / no history is recorded.
LAST_STEP_VALUES = ("none", "OK", "LAG", "DEVIATE", "CONTRADICT")
MOTION_UNKNOWN = "motion: arm=unknown gripper=unknown"
_MOTION_RE = re.compile(r"^motion: arm=(still|slow|fast|unknown) gripper=(closing|still|opening|unknown)$")
# §90 vocabulary. LINE_SEGMENTS = the VLA's segment-intent line (fix round 1, controller ruling F12): a segment
# CONTAINS its gripper event, so its name does not change at the grasp / release (Astra names the segment and its
# action, the VLA decides when): approach = open gripper going to the object and grasping it (do=close), carry =
# holding it until it is released (do=open), retreat, done (harvest.intent.PHASE_SEGMENT). SEGMENTS = Astra's
# segment-PLAN answer vocabulary (the R2 planner phases renamed 1:1; the pre-registered E-ACC v2 prompt reads it,
# tools/eacc/prompt_v2.py) -- the coupling maps a plan name to its line segment with harvest.intent.PLAN_TO_LINE.
# actions = the §87 gripper options (close / open) + none
SEGMENTS = ("approach", "descend", "grasp", "lift", "carry", "place", "release", "retreat", "done")
LINE_SEGMENTS = ("approach", "carry", "retreat", "done")
SEGMENT_ACTIONS = ("close", "open", "none")
SEGMENT_UNKNOWN = "segment: now=unknown do=unknown next=unknown"


def format_record() -> dict:
    """What every checkpoint prompt_config records about the DecCall state format (controller ruling PH-A 2,
    ser-A-min-3): the serializer version and the (b) `last_step` categories; checked by
    train.stagea_train.format_checks (fused_model.check_prompt)."""
    return {"serializer": SERIALIZER_VERSION, "last_step_values": list(LAST_STEP_VALUES)}


def with_last_step(state: str, last_step: str) -> str:
    if last_step not in LAST_STEP_VALUES:
        raise ValueError(f"last_step {last_step!r}: one of {LAST_STEP_VALUES}")
    return f"{state}\nlast_step: {last_step}"


def with_motion_last_step(state: str, motion: str, last_step: str) -> str:
    if not _MOTION_RE.match(motion):
        raise ValueError(f"motion line {motion!r}: 'motion: arm=<still|slow|fast|unknown> "
                         f"gripper=<closing|still|opening|unknown>'")
    return with_last_step(f"{state}\n{motion}", last_step)


def segment_line(now: str, do: str, nxt: str) -> str:
    """The §90 segment-intent line; ValueError on a name outside the line vocabulary (+ "unknown")."""
    for v, allowed in ((now, LINE_SEGMENTS), (do, SEGMENT_ACTIONS), (nxt, LINE_SEGMENTS)):
        if v not in allowed + ("unknown",):
            raise ValueError(f"segment value {v!r}: one of {allowed + ('unknown',)}")
    return f"segment: now={now} do={do} next={nxt}"


def check_segment(line: str) -> str:
    m = re.match(r"^segment: now=(\S+) do=(\S+) next=(\S+)$", line)
    if not m:
        raise ValueError(f"segment line {line!r}: 'segment: now=<segment> do=<action> next=<segment>'")
    return segment_line(*m.groups())


def with_intent_last_step(state: str, segment: str, motion: str, last_step: str) -> str:
    """ser-A-min-3 DecCall state tail: state -> segment line -> motion line -> last_step line."""
    return with_motion_last_step(f"{state}\n{check_segment(segment)}", motion, last_step)


def _v(x):
    return "unknown" if x is None else ("yes" if x else "no")


def canonicalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\t", " "))
    out = []
    for line in text.split("\n"):
        lead = len(line) - len(line.lstrip(" "))
        out.append(" " * lead + re.sub(r" {2,}", " ", line.strip()))
    return "\n".join(out).strip("\n")


def serialize_state(t_state, contract, stage, robot_line, objects, facts, named, changes):
    lines = [f"t_state: {t_state}  contract: {contract}  stage: {stage['id']} \"{stage['text']}\"",
             f"robot: {robot_line}", "objects:"]
    for oid, desc, support, pose in objects:
        lines.append(f"  {oid} {desc} | {support} | {pose}")
    shown = sorted(k for k, v in facts.items() if v is True or k in named)
    lines.append("facts: " + " ".join(f"{k}={_v(facts[k])}" for k in shown))
    lines.append(f"stage {stage['id']}: exit={stage['exit']} invariants={' '.join(stage['invariants'])} "
                 f"elapsed={stage['elapsed']}")
    recent = sorted([c for c in changes if c[0] >= -3.0], key=lambda c: c[0])[-8:]
    lines.append("changes (last 3s): " + "; ".join(f"{t:+.1f}s {p}: {a}->{b}" for t, p, a, b in recent))
    return "\n".join(lines)
