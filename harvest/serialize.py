"""Minimal serialization (candidate-A shape, E §1.4 measurement format) + J2 canonicalization (canon §28)."""
import re
import unicodedata

SERIALIZER_VERSION = "ser-A-min-2"
# -2 (canon §77, R7 cycle 12 D3): every DecCall state ends with the M4 (b) category line of the last finished
# decision step, `last_step: <category>` (M4 §4.2 `next_jev_input.add_line(f"last_step: {s.outcome}")`); "none" =
# no step checked yet / no check in the data / the category withheld (C5', conditions without (b)).
LAST_STEP_VALUES = ("none", "OK", "LAG", "DEVIATE", "CONTRADICT")


def with_last_step(state: str, last_step: str) -> str:
    if last_step not in LAST_STEP_VALUES:
        raise ValueError(f"last_step {last_step!r}: one of {LAST_STEP_VALUES}")
    return f"{state}\nlast_step: {last_step}"


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
