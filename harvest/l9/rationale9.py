"""L9 v2 "why" rationale (spec owner 10-02 22:40: "VLM이 생각을 하면서 조작"; L9_PRINCIPLES.md §2). Build-time only, from
sim ground truth (never invented): one top-level answer key "rationale", one fixed template family, clauses joined by
"; ", only for clauses whose cause is derivable this row. 8B check arm: --rationale on|off from tools/l9/build_v2.py.

Clauses (owner's order): arm -> approach+part (grasp calls only) -> rot (same pick) -> place -> handover -> articulated.
  arm:      "<left|right> arm: <cause>" -- two-armed robots only (alloc9.ROBOT_ARMS); single-command rows: the frozen
            single-arm rule (arm = object side) restated; multi-command (bimanual) rows: each command's own role.
  approach: "<approach> grasp on the <part>: <cause>" -- only on the (one) command that carries approach/rot, matched
            back to its grasp_v2 pick (meta) by (obj, family, rot_bin_img); omitted when no unique pick matches.
  rot:      "rot <bin>: pads across its <w> cm width" -- same matched pick's width_m.
  place:    "place: <x> cm off-centre, <y> cm above the spot, tol <t> cm (in|out) -> <verdict>" -- carry-phase rows
            only (step in carry_up/carry_over/lower_open; place_oscillation fix (b), place_readiness_clause).
  handover: "handover: <cause>" -- a command naming handover_point / handover_height (owner r3, not yet produced).
  axis:     "axis <linear|rotary>[ <cw|ccw>]: <cause>" -- a command naming axis (harvest/l9art articulated rows).
check_rows()-style consistency: parse_rationale() must read back arm / approach / rot / handover / axis words that
agree with the commands that produced them (specgate9.rationale_mismatches)."""
from __future__ import annotations

import json
import math
import re

TWO_ARMED_DEFAULT = ("right", "left")
CARRY_STEPS = ("carry_up", "carry_over", "lower_open")  # = teach_l8.labels.CARRY_STEPS
PLACE_VERDICT = {"lower_open": "place and open", "carry_over": "align above the spot", "carry_up": "lift"}
PART_WORDS = {"handle": "handle", "rim": "rim", "edge": "edge", "body": "body"}
PART_CAUSE = {"handle": "it has a handle", "rim": "it's hollow, grasped by the rim",
              "edge": "it's flat, grasped by the edge"}
WIDTH_CAUSE = {"narrow": "it's narrow", "wide": "it's wide"}
ROLE_CAUSE = {"lead": "it does the lead action", "support": "the other hand is busy"}
MAX_WORDS = 42  # spec: <= ~40 words


def two_armed(robot: str) -> bool:
    from .alloc9 import ROBOT_ARMS
    return len(ROBOT_ARMS.get(robot, TWO_ARMED_DEFAULT)) > 1


def commands_of(answer: dict) -> list:
    if answer.get("commands") is not None:
        return [c for c in answer["commands"] if isinstance(c, dict)]
    c = answer.get("command")
    return [c] if isinstance(c, dict) else []


def pick_for(meta: dict, obj_key, approach, rot) -> dict | None:
    """The grasp_v2 pick of this object at this (approach, rot) -- unique match only (never guess)."""
    if obj_key is None or approach is None or rot is None:
        return None
    picks = ((meta.get("grasp_v2") or {}).get("picks")) or []
    hits = [p for p in picks if p.get("obj") == obj_key and p.get("family") == approach
            and p.get("rot_bin_img") == rot and p.get("width_m") is not None]
    return hits[0] if len(hits) == 1 else None


def obj_name(meta: dict, obj_key) -> str | None:
    o = (meta.get("objects") or {}).get(obj_key)
    return o.get("name") if isinstance(o, dict) else None


def arm_clause(meta: dict, r: dict, cmd: dict) -> str | None:
    arm = cmd.get("arm") or cmd.get("hand")
    if arm not in ("left", "right"):
        return None
    role = cmd.get("role")
    if role in ROLE_CAUSE:
        cause = ROLE_CAUSE[role]
    else:
        name = obj_name(meta, r.get("tgt"))
        if not name:
            return None
        cause = f"the {name} is on the robot's {arm}"
    return f"{arm} arm: {cause}"


def approach_part_cause(pick: dict) -> str | None:
    part = pick.get("part")
    structural = PART_CAUSE.get(part)
    width = WIDTH_CAUSE.get(pick.get("open_bin3"))
    pieces = [p for p in (structural, width if part == "body" else None) if p]
    if not pieces and width:
        pieces = [width]
    if not pieces and pick.get("approach_reason") == "natural":
        pieces = ["a natural grasp for this object"]
    return " and ".join(pieces) if pieces else None


def grasp_clauses(meta: dict, r: dict, cmd: dict) -> tuple:
    """-> (approach_part_clause, rot_clause), either may be None (cause not derivable)."""
    approach, rot = cmd.get("approach"), cmd.get("rot")
    if approach is None or rot is None:
        return None, None
    pick = pick_for(meta, r.get("tgt"), approach, rot)
    if pick is None:
        return None, None
    part = PART_WORDS.get(pick.get("part"), pick.get("part"))
    cause = approach_part_cause(pick)
    ap = f"{approach} grasp on the {part}: {cause}" if cause and part else None
    w = pick.get("width_m")
    rc = f"rot {rot}: pads across its {w * 100:.1f} cm width" if w else None
    return ap, rc


def place_readiness_clause(r: dict) -> str | None:
    """place_oscillation fix (b) (docs/research/place_oscillation_2026-10-03.md §4): on a carry-phase row
    (r["step"] in CARRY_STEPS) with its own ground truth (gt.tgt = the held object's centre, gt.place, gt.tcp),
    one fixed "readiness" clause with the row's own numbers (never invented): the held object's xy offset from the
    place, the TCP's height above the place, the tolerance used (v2plan.place_tol) and whether it is inside it,
    and the step's verdict. None when the row has no carry step or no gt (non-L9 / incomplete rows)."""
    step = r.get("step")
    if step not in CARRY_STEPS:
        return None
    gt = r.get("gt") or {}
    tgt, place, tcp = gt.get("tgt"), gt.get("place"), gt.get("tcp")
    if not (tgt and place and tcp):
        return None
    from .v2plan import place_tol
    dxy = math.hypot(float(tgt[0]) - float(place[0]), float(tgt[1]) - float(place[1]))
    dz = float(tcp[2]) - float(place[2])
    try:
        tol = place_tol(r.get("place") or "")
    except (KeyError, TypeError):
        return None
    inside = dxy < tol
    return (f"place: {dxy * 100:.1f} cm off-centre, {dz * 100:.1f} cm above the spot, tol {tol * 100:.1f} cm "
            f"({'in' if inside else 'out'}) -> {PLACE_VERDICT[step]}")


def handover_clause(cmd: dict) -> str | None:
    hp, hh = cmd.get("handover_point"), cmd.get("handover_height")
    if hp is None and hh is None:
        return None
    bits = ["reachable by both arms, between them"]
    if hh is not None:
        bits.append(f"{hh} height")
    return "handover: " + ", ".join(bits)


def axis_clause(cmd: dict) -> str | None:
    axis = cmd.get("axis")
    if axis not in ("linear", "rotary"):
        return None
    if axis == "linear":
        return "axis linear: it slides along a straight track"
    turn = cmd.get("turn")
    tag = f"axis rotary {turn}" if turn in ("cw", "ccw") else "axis rotary"
    return f"{tag}: it turns about a hinge"


def build(meta: dict, r: dict, answer: dict) -> str | None:
    """-> the rationale string for one row's parsed answer dict, or None (nothing derivable). Pure."""
    cmds = commands_of(answer)
    if not cmds:
        return None
    robot = meta.get("robot") or "ffw_sg2"
    clauses = []
    if two_armed(robot):
        for cmd in cmds:
            c = arm_clause(meta, r, cmd)
            if c:
                clauses.append(c)
    grasp_cmds = [c for c in cmds if c.get("approach") is not None and c.get("rot") is not None]
    if grasp_cmds:
        ap, rc = grasp_clauses(meta, r, grasp_cmds[0])
        if ap:
            clauses.append(ap)
        if rc:
            clauses.append(rc)
    pc = place_readiness_clause(r)
    if pc:
        clauses.append(pc)
    for cmd in cmds:
        h = handover_clause(cmd)
        if h:
            clauses.append(h)
            break
    for cmd in cmds:
        a = axis_clause(cmd)
        if a:
            clauses.append(a)
            break
    if not clauses:
        return None
    text = "; ".join(clauses)
    if len(text.split()) > MAX_WORDS:  # defensive trim (template stays fixed; this should not trigger in practice)
        text = "; ".join(text.split("; ")[:2])
    return text


def for_answer(meta: dict, r: dict, answer_json: str) -> str | None:
    try:
        d = json.loads(answer_json)
    except (TypeError, ValueError):
        return None
    if not isinstance(d, dict):
        return None
    return build(meta, r, d)


def inject(answer_json: str, text: str) -> str:
    """answer_json with "rationale": text inserted right before "reason" (after command/commands); unchanged if
    there is no "reason" key (appended) or the row already carries one (idempotent)."""
    d = json.loads(answer_json)
    if "rationale" in d or "reason" not in d:
        d.setdefault("rationale", text)
        return json.dumps(d)
    out = {}
    for k, v in d.items():
        if k == "reason":
            out["rationale"] = text
        out[k] = v
    return json.dumps(out)


def strip(answer_json: str) -> str:
    """The inverse of inject(): answer_json with any "rationale" key removed (the off variant of a --rationale both
    build, from the same on-disk rows)."""
    d = json.loads(answer_json)
    if "rationale" not in d:
        return answer_json
    d.pop("rationale")
    return json.dumps(d)


_ARM = re.compile(r"(left|right) arm: ")
_APPROACH = re.compile(r"(top|oblique|front|side) grasp on the \w+: ")
_ROT = re.compile(r"rot (\d+): ")
_PLACE = re.compile(r"place: [\d.]+ cm off-centre, [\d.]+ cm above the spot, tol [\d.]+ cm \((in|out)\) -> "
                    r"(place and open|align above the spot|lift)")
_HANDOVER = re.compile(r"handover: ")
_AXIS = re.compile(r"axis (linear|rotary)(?: (cw|ccw))?: ")


def parse(text: str) -> dict:
    """The rationale string -> {"arms": [...], "approach": str|None, "rot": int|None, "place": verdict str|None,
    "handover": bool, "axis": (kind, turn|None)|None}, in textual order (parse-back for the consistency gate)."""
    arms = _ARM.findall(text)
    am = _APPROACH.search(text)
    rm = _ROT.search(text)
    pm = _PLACE.search(text)
    axm = _AXIS.search(text)
    return {"arms": list(arms), "approach": am.group(1) if am else None, "rot": int(rm.group(1)) if rm else None,
            "place": pm.group(2) if pm else None,
            "handover": bool(_HANDOVER.search(text)), "axis": (axm.group(1), axm.group(2)) if axm else None}
