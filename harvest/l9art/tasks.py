"""Phase-1 articulated task definitions (pure). 17 definitions: 14 single-skill + 3 combos.

A definition names the fixture family, the stages (skill program) and the success rule; instantiate(def, spec, seed)
picks the handle / knob / button, the start and goal joint values and the instruction text. Success is always a
privileged-state check: joint value / displacement thresholds (+ held time), object displacement for pushes.
Format v3 skills: pick, place, pull_axis, push_axis, rotate, press, push_slide.
Benchmark task strings never appear verbatim (bench_clash; owner principle: no benchmark sniping)."""
from __future__ import annotations

import math

import numpy as np

SKILLS = ("pick", "place", "pull_axis", "push_axis", "rotate", "press", "push_slide")
ROBOTS = ("ffw_sg2", "franka_mast", "r1pro")  # phase 1: AI Worker + Franka first, R1 Pro next; G1 out of scope

# stage kinds -> skill tag of every call of that stage
STAGE_SKILL = {"pull": "pull_axis", "push": "push_axis", "rotate": "rotate", "press": "press", "slide": "push_slide",
               "pick": "pick", "place": "place"}

DEFS = {}


def add(did, family, stages, texts, start=None, judge=None, robots=ROBOTS, combo=False, need_obj=None):
    DEFS[did] = {"id": did, "family": family, "stages": stages, "texts": texts, "start": start or {},
                 "judge": judge or {}, "robots": robots, "combo": combo, "need_obj": need_obj}


# goal values are shares of the joint range (prismatic / door) or angles (knob, rad); judge thresholds per stage
add("drawer_open", "drawer", [("pull", "H", ("share", 0.85))],
    ("Open the {H}.", "Pull the {H} open.", "Slide the {H} out.", "Pull out the {H} of the {F}."),
    judge={"min_share": 0.80})
add("drawer_open_half", "drawer", [("pull", "H", ("share", 0.5))],
    ("Open the {H} about halfway.", "Pull the {H} out half way.", "Open the {H} partly, about half."),
    judge={"band": (0.35, 0.65)})
add("drawer_close", "drawer", [("push", "H", ("share", 0.0))],
    ("Close the {H}.", "Push the {H} shut.", "Push the open {H} closed."),
    start={"H": ("share", (0.55, 0.95))}, judge={"max_share": 0.10})
add("door_open", "door", [("pull", "H", ("share", 0.75))],
    ("Open the {H}.", "Swing the {H} open.", "Pull the {H} of the {F} open."),
    judge={"min_share": 0.62})
add("door_close", "door", [("pull", "H", ("share", 0.0))],  # grasp the handle and swing it shut (smoke: the push pre-pose was out of reach 8/8)
    ("Close the {H}.", "Swing the {H} shut.", "Swing the open {H} closed."),
    start={"H": ("share", (0.30, 0.55))}, judge={"max_share": 0.08})  # wider doors put the free edge at the robot (smoke)
add("slide_open", "slide", [("pull", "H", ("share", 0.85))],
    ("Slide the {H} open.", "Open the {H} by sliding it {D}.", "Push the {H} aside to open it."),
    judge={"min_share": 0.75})
add("slide_close", "slide", [("pull", "H", ("share", 0.0))],  # grasp the handle and slide it back (smoke: no room beside the bar for a push)
    ("Slide the {H} closed.", "Close the {H}.", "Slide the {H} back to close it."),
    start={"H": ("share", (0.55, 0.95))}, judge={"max_share": 0.10})
add("knob_turn", "knob", [("rotate", "H", ("turn", None))],
    ("Turn the {H} {DIR} by about {DEG} degrees.", "Rotate the {H} {DEG} degrees {DIR}.",
     "Twist the {H} {DIR}, roughly {DEG} degrees."),
    start={"H": ("angle", (0.0, 0.6))}, judge={"tol_deg": 15.0})  # start angle varies the ridge (rot diversity)
add("knob_off", "knob", [("rotate", "H", ("value", 0.0))],
    ("Turn the {H} back to zero.", "Turn the {H} off (mark pointing to the start position).",
     "Reset the {H} to its start position."),
    start={"H": ("angle", (0.5, 1.6))}, judge={"tol_deg": 12.0})
add("dial_turn_top", "dial", [("rotate", "H", ("turn", None))],
    ("Turn the {H} on top {DIR} by about {DEG} degrees.", "Rotate the top {H} {DEG} degrees {DIR}."),
    start={"H": ("angle", (0.0, 0.6))}, judge={"tol_deg": 15.0, "face": "top"})
add("button_press", "button", [("press", "H", None)],
    ("Press the {H}.", "Push the {H}.", "Press down the {H} once."), judge={"press_share": 0.6})
add("switch_press", "button", [("press", "H", None)],
    ("Flip the {H}.", "Press the {H} on the panel.", "Toggle the {H}."), judge={"press_share": 0.6, "switch": True})
add("push_object", "none", [("slide", "O", None)],
    ("Push the {O} {DIST} cm to the {DIR}.", "Slide the {O} about {DIST} cm {DIR} without lifting it.",
     "Nudge the {O} {DIR} by about {DIST} cm."),
    judge={"pos_tol": 0.03, "max_tilt_deg": 20.0}, need_obj="pushable")
add("push_object_far", "none", [("slide", "O", None)],
    ("Push the {O} away from you by about {DIST} cm.", "Slide the {O} {DIST} cm further away along the table."),
    judge={"pos_tol": 0.03, "max_tilt_deg": 20.0, "dir": "away"}, need_obj="pushable")
add("drawer_put_close", "drawer", [("pull", "H", ("share", 0.85)), ("pick", "O", None), ("place", "IN", None),
                                   ("push", "H", ("share", 0.0))],
    ("Open the {H}, put the {O} inside and close it.", "Put the {O} into the {H} and shut the drawer.",
     "Store the {O} in the {H}: open it, drop the {O} in, close it."),
    judge={"max_share": 0.10, "obj_in": True}, combo=True, need_obj="small")
add("drawer_take_close", "drawer", [("pull", "H", ("share", 0.85)), ("pick", "O", None), ("place", "TABLE", None),
                                    ("push", "H", ("share", 0.0))],
    ("Take the {O} out of the {H}, put it on the table and close the drawer.",
     "Open the {H}, get the {O} out onto the table, then close the drawer."),
    judge={"max_share": 0.10, "obj_out": True}, combo=True, need_obj="small")
add("knob_then_button", "panel", [("rotate", "K", ("turn", None)), ("press", "B", None)],
    ("Turn the {K} {DIR} by about {DEG} degrees, then press the {B}.",
     "First rotate the {K} {DEG} degrees {DIR}, then push the {B}."),
    judge={"tol_deg": 15.0, "press_share": 0.6}, combo=True)

BENCH_LIKE = ("open the top drawer", "open the middle drawer", "close the top drawer", "open the microwave",
              "turn on the stove", "push the button", "open drawer", "close drawer", "turn on the light")


def _norm(s):
    return " ".join("".join(c.lower() if c.isalnum() else " " for c in s).split())


def bench_clash(text: str) -> bool:
    return _norm(text) in {_norm(b) for b in BENCH_LIKE}


def _pick(rng, seq):
    return seq[int(rng.integers(len(seq)))]


def instantiate(did: str, spec: dict | None, seed: int, obj_name: str | None = None) -> dict:
    """-> episode program {def, stages [{kind, skill, link, goal (joint value) | None}], start {joint: value},
    instruction, words, judge}. Raises ValueError when the definition does not fit the fixture."""
    d = DEFS[did]
    rng = np.random.default_rng([int(seed), 8081, sorted(DEFS).index(did)])
    words, start, stages = {"O": obj_name or "object", "IN": "into the drawer", "TABLE": "onto the table"}, {}, []
    links = {}
    if spec is not None:
        hs = spec["handles"]
        if d["family"] == "panel":
            links["K"] = next(l for l, h in hs.items() if h["type"] == "knob")
            links["B"] = next(l for l, h in hs.items() if h["type"] == "button")
        else:
            cand = sorted(hs)
            if d["judge"].get("face"):
                cand = [l for l in cand if hs[l].get("face") == d["judge"]["face"]]
            elif d["family"] == "knob" and did == "knob_turn":
                cand = [l for l in cand if hs[l].get("face") == "front"] or cand
            if d["judge"].get("switch"):
                cand = [l for l in cand if "switch" in hs[l]["words"]]
            elif did == "button_press":
                cand = [l for l in cand if "switch" not in hs[l]["words"]]
            if not cand:
                raise ValueError(f"{did}: no fitting part on {spec['name']}")
            links["H"] = _pick(rng, cand)
        for k, ln in links.items():
            words[k] = hs[ln]["words"]
        words["F"] = spec.get("label", "cabinet")
        if d["family"] == "slide":
            words["D"] = "to the " + ("right" if spec["handles"][links["H"]].get("side") == "left" else "left")
    for k, (kind, v) in d["start"].items():
        jn = spec["handles"][links[k]]["joint"]
        J = dict(spec["joints"][jn], name=jn)
        if kind == "share":
            start[J["name"]] = float(rng.uniform(*v)) * J["hi"]
        else:
            start[J["name"]] = float(rng.uniform(*v)) * (1 if rng.random() < 0.5 else -1)
    for kind, ref, goal in d["stages"]:
        st = {"kind": kind, "skill": STAGE_SKILL[kind], "ref": ref, "link": links.get(ref), "goal": None}
        if goal is not None and spec is not None:
            jn = spec["handles"][links[ref]]["joint"]
            J = dict(spec["joints"][jn], name=jn)
            if goal[0] == "share":
                st["goal"] = round(goal[1] * J["hi"], 4)
            elif goal[0] == "value":
                st["goal"] = float(goal[1])
            elif goal[0] == "turn":
                deg = float(_pick(rng, (30, 45, 60, 90)))
                sgn = 1 if rng.random() < 0.5 else -1
                q0 = start.get(J["name"], 0.0)
                st["goal"] = round(q0 + sgn * math.radians(deg), 4)
                words["DEG"] = str(int(deg))
                words["DIR"] = "clockwise" if sgn > 0 else "counterclockwise"
        stages.append(st)
    if d["need_obj"] == "pushable" and d["judge"].get("dir") != "away":
        words["DIR"] = _pick(rng, ("left", "right"))
    if d["need_obj"] == "pushable":
        words["DIST"] = str(int(_pick(rng, (8, 10, 12) if d["judge"].get("dir") == "away" else (8, 10, 12, 15))))
    text = None
    order = list(rng.permutation(len(d["texts"])))
    for i in order:
        t = d["texts"][int(i)].format(**{k: v for k, v in words.items()})
        if not bench_clash(t):
            text = t
            break
    if text is None:
        raise ValueError(f"{did}: every template clashes with a benchmark string")
    text = text[0].upper() + text[1:]
    return {"def": did, "family": d["family"], "stages": stages, "start": start, "instruction": text,
            "words": words, "judge": dict(d["judge"]), "links": links, "combo": d["combo"], "need_obj": d["need_obj"]}
