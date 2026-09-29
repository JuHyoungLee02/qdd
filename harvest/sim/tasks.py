"""R2 multi-task registry (pure, no Isaac): pick-and-place tasks in the same v2 scene with the existing object set.

  mug_tray     "Put the red mug on the blue tray."        o3 (cylinder) -> o5 (tray)      the original task
  bottle_tray  "Put the green bottle on the blue tray."   o8 (thin cylinder) -> o5        new object
  mug_marker   "Put the red mug on the magenta marker."   o3 -> o11 (flat visual marker)  new place target (table spot)
  box_marker   (experimental, not generated) o9 (cuboid, yaw-aligned grasp) -> o11: grasp not tuned (0/3 on DEV)

Layouts: mug_tray = scene.sample_layout(seed) unchanged (so the standard pool / DEV runs are untouched). The other
tasks draw their own layout from (seed, task): target and place inside the right-arm top-down workspace (same rule
as the mug / tray), the mug o3 always stays on the table (as a distractor when it is not the target), the task's
extra objects appear with probability 1/2 each in the distractor band, the P2 object o10 stays parked.

The marker o11 is visual only (no collider). Its contact is virtual: an object whose bottom is on the table surface
(within oracle_state.TABLE_TOL_M) with its centre within MARKER_ON_R of the marker centre is "in contact" with it,
so the registry predicates on(a,o11) / in_contact(a,o11) and the planner's place logic work unchanged.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .scene import DISTRACTOR_X, DISTRACTOR_Y, OBJ_GEOM, WS_X, WS_Y, check_ws, sample_layout

TOP_DOWN_YAW = math.pi / 2  # = planner.TOP_DOWN_YAW (fingers close along world x)
GRIP_SQUEEZE_M = 0.014  # = planner.GRIP_SQUEEZE_M
BOX_YAW_DEV_DEG = 30.0  # box yaw = k * 90 deg + U(-30, 30) deg -> the aligned grasp yaw stays within 30 deg of pi/2
MARKER_ON_R = 0.04  # object centre within 4 cm of the marker centre (marker radius 5 cm) counts as on the marker
TABLE_TOL_M = 0.004  # = oracle_state.TABLE_TOL_M


@dataclass(frozen=True)
class Task:
    id: str
    target: str
    place: str
    instruction: str
    stage_text: dict = field(default_factory=dict)
    extras: tuple = ()  # objects that may appear as distractors (p = 1/2 each); the mug o3 is always on the table


TASKS = {
    "mug_tray": Task("mug_tray", "o3", "o5", "Put the red mug on the blue tray.",
                     {"S1": "pick up mug o3", "S2": "place mug o3 on tray o5"}),
    "bottle_tray": Task("bottle_tray", "o8", "o5", "Put the green bottle on the blue tray.",
                        {"S1": "pick up bottle o8", "S2": "place bottle o8 on tray o5"}, extras=("o9",)),
    "mug_marker": Task("mug_marker", "o3", "o11", "Put the red mug on the magenta marker.",
                       {"S1": "pick up mug o3", "S2": "place mug o3 on marker o11"}, extras=("o5", "o8", "o9")),
    # experimental (not in TASK_IDS): cuboid top-down grasp is not tuned for the copied RH-P12-RN fingers --
    # DEV 0-2 standard P0 0/3 (lift: the box turns / tilts in the pads, 64 mm pad gap on a 50 mm box, r2_datagen.md)
    "box_marker": Task("box_marker", "o9", "o11", "Put the yellow box on the magenta marker.",
                       {"S1": "pick up box o9", "S2": "place box o9 on marker o11"}, extras=("o5", "o8")),
}
TASK_IDS = ("mug_tray", "bottle_tray", "mug_marker")  # the generated task set ("all")
EXPERIMENTAL_TASKS = ("box_marker",)
TASK_CODE = {"mug_tray": 0, "bottle_tray": 1, "box_marker": 2, "mug_marker": 3}  # layout RNG stream id (fixed)

# L8-X tasks (docs/research/l8x_env_suite_design_2026-09-27.md): need scene.make_env(objset="x"); own layout rules
# (x_task_layout). support: the target starts ON that object (layout entry (x, y, yaw, support)).
X_TASKS = {
    "mug_stand": Task("mug_stand", "o3", "o12", "Put the red mug on the white stand.",
                      {"S1": "pick up mug o3", "S2": "place mug o3 on stand o12"}, extras=("o8", "o9")),
    "stand_mug_tray": Task("stand_mug_tray", "o3", "o5",
                           "Take the red mug from the white stand and put it on the blue tray.",
                           {"S1": "pick up mug o3 from stand o12", "S2": "place mug o3 on tray o5"},
                           extras=("o8",)),
    "mug_bin": Task("mug_bin", "o3", "o15", "Put the red mug in the grey bin.",
                    {"S1": "pick up mug o3", "S2": "place mug o3 in bin o15"}, extras=("o8", "o9")),
    "bottle_bin": Task("bottle_bin", "o8", "o15", "Put the green bottle in the grey bin.",
                       {"S1": "pick up bottle o8", "S2": "place bottle o8 in bin o15"}, extras=("o9",)),
    "bluemug_tray": Task("bluemug_tray", "o13", "o5", "Put the blue mug on the blue tray.",
                         {"S1": "pick up mug o13", "S2": "place mug o13 on tray o5"}, extras=("o8",)),
    "smallcup_tray": Task("smallcup_tray", "o14", "o5", "Put the small red cup on the blue tray.",
                          {"S1": "pick up cup o14", "S2": "place cup o14 on tray o5"}, extras=("o9",)),
    "mug_left_of_bottle": Task("mug_left_of_bottle", "o3", "o17",
                               "Put the red mug about 10 cm to the left of the green bottle (the robot's left).",
                               {"S1": "pick up mug o3", "S2": "place mug o3 at spot o17 left of bottle o8"}),
    "mug_right_of_bottle": Task("mug_right_of_bottle", "o3", "o18",
                                "Put the red mug about 10 cm to the right of the green bottle (the robot's right).",
                                {"S1": "pick up mug o3", "S2": "place mug o3 at spot o18 right of bottle o8"}),
    # OOD-T compositions (evaluation only in L8-X: trained parts, unseen combination; teach_l8d.spec.OOD_T_TASKS)
    "bluemug_bin": Task("bluemug_bin", "o13", "o15", "Put the blue mug in the grey bin.",
                        {"S1": "pick up mug o13", "S2": "place mug o13 in bin o15"}, extras=("o8",)),
    "bottle_stand": Task("bottle_stand", "o8", "o12", "Put the green bottle on the white stand.",
                         {"S1": "pick up bottle o8", "S2": "place bottle o8 on stand o12"}, extras=("o9",)),
    # multi-step (teach_l8d.multistep; the registry target / place = step 1)
    "mug_tray_bottle_marker": Task("mug_tray_bottle_marker", "o3", "o5",
                                   "Put the red mug on the blue tray, then put the green bottle on the magenta marker.",
                                   {"S1": "pick up mug o3, then bottle o8",
                                    "S2": "place mug o3 on tray o5, then bottle o8 on marker o11"}),
    "clear_to_bin": Task("clear_to_bin", "o3", "o15", "Put the red mug and then the green bottle in the grey bin.",
                         {"S1": "pick up mug o3, then bottle o8", "S2": "place mug o3, then bottle o8, in bin o15"}),
    # replaces mug_tray_bottle_marker (truth gate 1/3: the bottle tipped on the marker twice); appended so the
    # layout stream ids of the tasks above do not move
    "mug_tray_bluemug_marker": Task("mug_tray_bluemug_marker", "o3", "o5",
                                    "Put the red mug on the blue tray, then put the blue mug on the magenta marker.",
                                    {"S1": "pick up mug o3, then mug o13",
                                     "S2": "place mug o3 on tray o5, then mug o13 on marker o11"}),
    # furniture cross-surface task (runner --furniture): the mug on the lower surface -> the higher surface o19
    "mug_to_upper": Task("mug_to_upper", "o3", "o19", "Put the red mug on the higher surface.",
                         {"S1": "pick up mug o3", "S2": "place mug o3 on surface o19"}, extras=("o8",)),
    # furniture container task (runner --furniture): the mug -> the floor of the furniture's open box o20
    "mug_to_container": Task("mug_to_container", "o3", "o20", "Put the red mug into the open box.",
                             {"S1": "pick up mug o3", "S2": "place mug o3 in box o20"}, extras=("o8",)),
}
X_FURNITURE_TASKS = ("mug_to_upper", "mug_to_container")  # need a furniture scene with a second usable surface
# steps (target, place, place xy offset | None); a shared place gets side-by-side offsets
X_STEPS = {"mug_tray_bottle_marker": (("o3", "o5", None), ("o8", "o11", None)),
           "clear_to_bin": (("o3", "o15", (0.0, 0.04)), ("o8", "o15", (0.0, -0.04))),
           "mug_tray_bluemug_marker": (("o3", "o5", None), ("o13", "o11", None))}
# confuser tasks (prereg_l8d change 10): the base task + 1-2 same-colour, different-shape objects 8-16 cm from the
# target (CONF_POOL; the OOD-O small red cup o14 is never one). Appended last, so older layout streams are unchanged.
CONF_POOL = {"o3": ("o21", "o22", "o23"), "o8": ("o24", "o25"), "o13": ("o26",)}
CONF_TASKS = {f"cf_{b}": b for b in ("mug_tray", "bottle_tray", "mug_marker", "bluemug_tray", "mug_bin")}
for _t, _b in CONF_TASKS.items():
    _s = TASKS.get(_b) or X_TASKS[_b]
    X_TASKS[_t] = Task(_t, _s.target, _s.place, _s.instruction, dict(_s.stage_text), _s.extras)
X_TASK_IDS = tuple(X_TASKS)
X_TASK_CODE = {t: 100 + i for i, t in enumerate(X_TASK_IDS)}  # layout RNG stream ids (fixed; append new ones)
X_SUPPORT = {"stand_mug_tray": ("o12", "o3")}  # (support object, object standing on it)
X_CONFUSER = {"bluemug_tray": "o3", "smallcup_tray": "o3", "bluemug_bin": "o3",  # attribute twin, always 8-14 cm from the target
              "cf_bluemug_tray": "o3"}
X_REL = {"mug_left_of_bottle": ("o8", "o17", 0.10), "mug_right_of_bottle": ("o8", "o18", -0.10)}  # ref, spot, dy
TASKS.update(X_TASKS)


def check_task(task: str) -> str:
    if task not in TASKS:
        raise ValueError(f"task {task!r}: one of {TASK_IDS} (experimental: {EXPERIMENTAL_TASKS})")
    return task


def stages(spec: Task) -> dict:
    """Contract stages S1 (pick) / S2 (place) in the text-state format of snapshot.STAGES."""
    t, p = spec.target, spec.place
    return {"S1": {"text": spec.stage_text["S1"], "exit": f"holding({t}) lifted({t})", "invariants": []},
            "S2": {"text": spec.stage_text["S2"], "exit": f"on({t},{p})", "invariants": [f"holding({t})"]}}


def _fr(k):
    return OBJ_GEOM[k]["footprint_r"]


def task_layout(seed: int, task: str, ws=None) -> dict:
    """{obj_id: (x, y, yaw)} world xy for (seed, task); mug_tray = the standard layout. ws: optional workspace box
    for target and place (scene.check_ws, L8-D per-height box); None = WS_X / WS_Y (unchanged)."""
    check_task(task)
    if task == "mug_tray":
        return sample_layout(seed, ws=ws)
    if task in X_TASKS:
        return x_task_layout(seed, task, ws)
    wx, wy = check_ws(ws) or (WS_X, WS_Y)
    s = TASKS[task]
    rng = np.random.default_rng([int(seed), 11, 1000 + TASK_CODE[task]])
    for _ in range(10000):
        p = (rng.uniform(wx[0] + 0.02, wx[1]), rng.uniform(wy[0] + 0.03, wy[1] - 0.03))
        m = (rng.uniform(*wx), rng.uniform(*wy))
        if math.dist(p, m) >= max(0.16, _fr(s.target) + _fr(s.place) + 0.03):
            break
    else:  # pragma: no cover
        raise RuntimeError("layout")
    yaw = 0.0
    if OBJ_GEOM[s.target]["shape"] == "cuboid":
        yaw = float(rng.integers(4)) * math.pi / 2 + math.radians(rng.uniform(-BOX_YAW_DEV_DEG, BOX_YAW_DEV_DEG))
        yaw = math.atan2(math.sin(yaw), math.cos(yaw))
    out = {s.target: (float(m[0]), float(m[1]), yaw), s.place: (float(p[0]), float(p[1]), 0.0)}
    extra = ([] if s.target == "o3" else ["o3"]) + [k for k in s.extras if rng.random() < 0.5]
    for k in extra:
        for _ in range(10000):
            q = (float(rng.uniform(*DISTRACTOR_X)), float(rng.uniform(*DISTRACTOR_Y)),
                 float(rng.uniform(-math.pi, math.pi)) if OBJ_GEOM[k]["shape"] == "cuboid" else 0.0)
            ok = (math.dist(q[:2], m) >= 0.10 and math.dist(q[:2], p) >= _fr(k) + _fr(s.place) + 0.04
                  and all(math.dist(q[:2], v[:2]) >= _fr(k) + _fr(j) + 0.02 for j, v in out.items()))
            if ok:
                out[k] = q
                break
    return out


def _target_yaw(k: str, rng) -> float:
    """Layout yaw of a target: 0 for the primitive objects (no rng draw, so their layout streams are unchanged);
    licensed mesh objects are turned so their narrow side faces the fingers (objv.grasp_yaw_of) +- 10 deg."""
    g = OBJ_GEOM[k]
    if g["shape"] != "mesh":
        return 0.0
    from .objv import grasp_yaw_of
    return float(grasp_yaw_of(g) + math.radians(rng.uniform(-10.0, 10.0)))


OBJV_TASK_KINDS = {"tray": ("o5", "Put the {n} on the blue tray.", ()),
                   "bin": ("o15", "Put the {n} in the grey bin.", ("o8",)),
                   # change 14: into a furniture basket (virtual place o20 = the cyclo_lab basket floor; --furniture)
                   "basket": ("o20", "Put the {n} into the basket.", ()),
                   # change 15: relational placement next to the green bottle (spots o17 / o18, X_REL)
                   "left": ("o17", "Put the {n} to the left of the green bottle.", ()),
                   "right": ("o18", "Put the {n} to the right of the green bottle.", ()),
                   # change 15: onto another furniture surface (virtual place o19 = a higher usable surface)
                   "upper": ("o19", "Put the {n} on the higher surface.", ()),
                   # change 18: in front of / behind the bottle, between the bottle and the yellow box
                   "front": ("o27", "Put the {n} in front of the green bottle.", ()),
                   "behind": ("o28", "Put the {n} behind the green bottle.", ()),
                   "between": ("o29", "Put the {n} between the green bottle and the yellow box.", ())}
OBJV_REL = {"left": ("o8", "o17", 0.10), "right": ("o8", "o18", -0.10),
            "front": ("o8", "o27", 0.0, -0.10), "behind": ("o8", "o28", 0.0, 0.10)}  # ref, spot, dy[, dx]
OBJV_BETWEEN = {"between": ("o8", "o9", "o29")}  # refs a, b, spot (their midpoint)
X_BETWEEN: dict = {}
# change 20 (audit 2): L8S relational references are real objects (not the primitive bottle o8 / box o9)
L8S_REL_REFS = {"bottle": ("gsor_Twinlab_Premium_Creatine_Fuel_Powder", "brown bottle"),
                "box": ("gso_JarroSil_Activated_Silicon_5exdZHIeLAp", "pink box")}


def use_real_refs() -> tuple:
    """Switch the ov_* relational kinds to the L8S real references (texts, X_REL refs, spot names); -> ref ids.
    Call before registering the tasks (objv.register_for_tasks does it for real-object rel tasks)."""
    from ..astra_motion import prompts as P
    (b, bn), (x, xn) = L8S_REL_REFS["bottle"], L8S_REL_REFS["box"]
    for kind, side in (("left", "to the left of"), ("right", "to the right of"), ("front", "in front of"),
                       ("behind", "behind")):
        pl = OBJV_TASK_KINDS[kind][0]
        OBJV_TASK_KINDS[kind] = (pl, "Put the {n} " + side + " the " + bn + ".", ())
        OBJV_REL[kind] = (b,) + tuple(OBJV_REL[kind][1:])
    OBJV_TASK_KINDS["between"] = ("o29", "Put the {n} between the " + bn + " and the " + xn + ".", ())
    OBJV_BETWEEN["between"] = (b, x, "o29")
    P.REL_NAMES.update(bottle=bn, box=xn)
    for k, t in (("o17", "left of"), ("o18", "right of"), ("o27", "in front of"), ("o28", "behind")):
        P.OBJ_NAME[k] = f"spot {t} the {bn}"
    P.OBJ_NAME["o29"] = f"spot between the {bn} and the {xn}"
    return b, x


def objv_task_id(kind: str, obj: str) -> str:
    return f"ov_{kind}__{obj}"


def register_objv_tasks(ids, names: dict) -> list:
    """L8-X tasks for registered licensed mesh objects (harvest.sim.objv.register): per object 'ov_tray__<id>' (onto
    the blue tray) and 'ov_bin__<id>' (into the grey bin). Layout streams: code 5000 + a stable hash of the id."""
    import hashlib
    out = []
    for k in ids:
        for kind, (pl, text, extras) in OBJV_TASK_KINDS.items():
            t = objv_task_id(kind, k)
            if t not in TASKS:
                n = names[k]
                TASKS[t] = X_TASKS[t] = Task(t, k, pl, text.format(n=n),
                                             {"S1": f"pick up {n} {k}", "S2": f"place {n} {k} on {pl}"}, extras=extras)
                X_TASK_CODE[t] = 5000 + int(hashlib.sha256(t.encode()).hexdigest()[:6], 16) % 100000
                if kind in OBJV_REL:
                    X_REL[t] = OBJV_REL[kind]
                if kind in OBJV_BETWEEN:
                    X_BETWEEN[t] = OBJV_BETWEEN[kind]
            out.append(t)
    return out


def register_into_task(t: str, obj: str, cont: str, name: str, cname: str, kind: str) -> str:
    """L8S: put a real object into (or onto) a container (objv.register_containers); layout stream 8000 + hash."""
    import hashlib
    if t not in TASKS:
        text = f"Put the {name} into the {cname}." if kind == "into" else f"Put the {name} on the {cname}."
        TASKS[t] = X_TASKS[t] = Task(t, obj, cont, text, {"S1": f"pick up {name} {obj}",
                                                          "S2": f"place {name} {obj} in {cname} {cont}"})
        X_TASK_CODE[t] = 8000 + int(hashlib.sha256(t.encode()).hexdigest()[:6], 16) % 100000
    return t


def x_task_layout(seed: int, task: str, ws=None) -> dict:
    """L8-X task layouts (own RNG stream X_TASK_CODE). Target / place (or stand / relational reference) inside the
    workspace box by the task_layout rules; stand_mug_tray: the stand at the pick spot, the mug on it
    ((x, y, yaw, 'o12')); attribute tasks: the twin (red mug) 8-14 cm from the target; relational tasks: bottle and
    the invisible spot 10 cm to its left / right both inside the box, the mug >= 12 cm from the spot; extras by the
    task_layout rule (p = 1/2 each, the red mug always present)."""
    wx, wy = check_ws(ws) or (WS_X, WS_Y)
    if str(task).startswith("pu__"):  # L8-X push (teach_l8d.xnew, prereg_l8x_tasks 2.2): its own layout rule
        from ..teach_l8d.xnew import push_layout
        return push_layout(seed, task, (wx, wy), _fr)
    s = TASKS[task]
    rng = np.random.default_rng([int(seed), 11, X_TASK_CODE[task]])
    out: dict = {}
    if task in X_STEPS:  # every step's target and place inside the box, pairwise clear
        ids = []
        for st in X_STEPS[task]:
            ids += [k for k in st[:2] if k not in ids]
        pairs = {frozenset(st[:2]) for st in X_STEPS[task]}
        places = {st[1] for st in X_STEPS[task]}
        order = sorted(ids, key=lambda k: -_fr(k))  # sequential placement, largest first

        targets = {st[0] for st in X_STEPS[task]}

        def need(a, b):
            if frozenset((a, b)) in pairs:
                return max(0.16, _fr(a) + _fr(b) + 0.03)
            # the open fingers (10.7 cm along x) sweep around a target: keep 10 cm like task_layout's extras rule
            return max(_fr(a) + _fr(b) + 0.02, 0.10 if (a in targets or b in targets) else 0.0)

        for _ in range(20000):
            pos: dict = {}
            for k in order:
                for _ in range(300):
                    q = ((rng.uniform(wx[0] + 0.02, wx[1]), rng.uniform(wy[0] + 0.03, wy[1] - 0.03)) if k in places
                         else (rng.uniform(*wx), rng.uniform(*wy)))
                    if all(math.dist(q, v) >= need(k, j) for j, v in pos.items()):
                        pos[k] = q
                        break
                else:
                    break
            if len(pos) == len(order):
                break
        else:  # pragma: no cover
            raise RuntimeError("layout")
        return {k: (float(pos[k][0]), float(pos[k][1]), 0.0) for k in ids}
    if task in X_BETWEEN:  # change 18: the spot halfway between two references 20-26 cm apart
        ra, rb, spot = X_BETWEEN[task]
        for _ in range(100000):
            sp = (rng.uniform(wx[0] + 0.02, wx[1]), rng.uniform(wy[0] + 0.03, wy[1] - 0.03))
            half = rng.uniform(0.10, 0.13)
            ang = rng.uniform(-0.35, 0.35)  # the pair runs roughly along y
            a = (sp[0] + half * math.sin(ang), sp[1] + half * math.cos(ang))
            b = (sp[0] - half * math.sin(ang), sp[1] - half * math.cos(ang))
            m = (rng.uniform(*wx), rng.uniform(*wy))
            if (math.dist(m, sp) >= 0.12 and math.dist(m, a) >= _fr(s.target) + _fr(ra) + 0.05
                    and math.dist(m, b) >= _fr(s.target) + _fr(rb) + 0.05):
                break
        else:  # pragma: no cover
            raise RuntimeError("layout")
        out = {s.target: (float(m[0]), float(m[1]), 0.0), ra: (float(a[0]), float(a[1]), 0.0),
               rb: (float(b[0]), float(b[1]), 0.0), spot: (float(sp[0]), float(sp[1]), 0.0)}
        p = sp
    elif task in X_REL and len(X_REL[task]) > 3:  # change 18: in front of / behind (x offset); spot in the box
        ref, spot, dy, dx = X_REL[task]
        for _ in range(100000):
            sp = (rng.uniform(wx[0] + 0.02, wx[1]), rng.uniform(wy[0] + 0.03, wy[1] - 0.03))
            b = (sp[0] - dx, sp[1] - dy)
            m = (rng.uniform(*wx), rng.uniform(*wy))
            if math.dist(m, b) >= _fr(s.target) + _fr(ref) + 0.05 and math.dist(m, sp) >= 0.12:
                break
        else:  # pragma: no cover
            raise RuntimeError("layout")
        out = {s.target: (float(m[0]), float(m[1]), 0.0), ref: (float(b[0]), float(b[1]), 0.0),
               spot: (float(sp[0]), float(sp[1]), 0.0)}
        p = sp
    elif task in X_REL:
        ref, spot, dy = X_REL[task]
        for _ in range(100000):
            b = (rng.uniform(wx[0] + 0.02, wx[1]), rng.uniform(wy[0] + 0.03, wy[1] - 0.03))
            sp = (b[0], b[1] + dy)
            m = (rng.uniform(*wx), rng.uniform(*wy))
            if (wy[0] + 0.03 <= sp[1] <= wy[1] - 0.03 and math.dist(m, b) >= _fr(s.target) + _fr(ref) + 0.05
                    and math.dist(m, sp) >= 0.12):
                break
        else:  # pragma: no cover
            raise RuntimeError("layout")
        out = {s.target: (float(m[0]), float(m[1]), 0.0), ref: (float(b[0]), float(b[1]), 0.0),
               spot: (float(sp[0]), float(sp[1]), 0.0)}
        p = sp
    else:
        sup = X_SUPPORT.get(task, (None,))[0]
        fr_t = _fr(sup) if sup else _fr(s.target)
        for _ in range(100000):
            p = (rng.uniform(wx[0] + 0.02, wx[1]), rng.uniform(wy[0] + 0.03, wy[1] - 0.03))
            m = (rng.uniform(*wx), rng.uniform(*wy))
            if math.dist(p, m) >= max(0.16, fr_t + _fr(s.place) + 0.03):
                break
        else:  # pragma: no cover
            raise RuntimeError("layout")
        out[s.place] = (float(p[0]), float(p[1]), 0.0)
        if sup:
            out[sup] = (float(m[0]), float(m[1]), 0.0)
            out[s.target] = (float(m[0]), float(m[1]), 0.0, sup)
        else:
            out[s.target] = (float(m[0]), float(m[1]), _target_yaw(s.target, rng))
        tw = X_CONFUSER.get(task)
        if tw:
            for _ in range(100000):
                a, r = rng.uniform(-math.pi, math.pi), rng.uniform(0.08, 0.14)
                q = (m[0] + r * math.cos(a), m[1] + r * math.sin(a))
                if (DISTRACTOR_X[0] <= q[0] <= DISTRACTOR_X[1] and DISTRACTOR_Y[0] <= q[1] <= DISTRACTOR_Y[1]
                        and math.dist(q, p) >= _fr(tw) + _fr(s.place) + 0.04):
                    out[tw] = (float(q[0]), float(q[1]), 0.0)
                    break
            else:  # pragma: no cover
                raise RuntimeError("confuser")
        if task in CONF_TASKS:  # 1-2 same-colour confusers 8-16 cm from the target, clear of everything placed
            pool = CONF_POOL[s.target]
            n = min(len(pool), 1 + int(rng.integers(2)))
            for k in [pool[i] for i in rng.permutation(len(pool))[:n]]:
                for _ in range(100000):
                    a, r = rng.uniform(-math.pi, math.pi), rng.uniform(0.08, 0.16)
                    q = (m[0] + r * math.cos(a), m[1] + r * math.sin(a))
                    if (DISTRACTOR_X[0] <= q[0] <= DISTRACTOR_X[1] and DISTRACTOR_Y[0] <= q[1] <= DISTRACTOR_Y[1]
                            and math.dist(q, p) >= _fr(k) + _fr(s.place) + 0.04
                            and all(math.dist(q, v[:2]) >= _fr(k) + _fr(j) + 0.02 for j, v in out.items()
                                    if j != s.place)):
                        yaw = float(rng.uniform(-math.pi, math.pi)) if OBJ_GEOM[k]["shape"] == "cuboid" else 0.0
                        out[k] = (float(q[0]), float(q[1]), yaw)
                        break
                else:  # pragma: no cover
                    raise RuntimeError("confuser")
    extra = ([] if "o3" in out else ["o3"]) + [k for k in s.extras if rng.random() < 0.5 and k not in out]
    for k in extra:
        for _ in range(10000):
            q = (float(rng.uniform(*DISTRACTOR_X)), float(rng.uniform(*DISTRACTOR_Y)),
                 float(rng.uniform(-math.pi, math.pi)) if OBJ_GEOM[k]["shape"] == "cuboid" else 0.0)
            ok = (math.dist(q[:2], m) >= 0.10 and math.dist(q[:2], p) >= _fr(k) + _fr(s.place) + 0.04
                  and all(math.dist(q[:2], v[:2]) >= _fr(k) + _fr(j) + 0.02 for j, v in out.items()))
            if ok:
                out[k] = q
                break
    return out


# ---------------------------------------------------------------- two-target pair layout (MolmoAct M4, explicit option)
PAIR_TASKS = ("mug_tray", "bottle_tray")  # same layout, the instruction chooses the target (MolmoAct D.7: two bowls)
PAIR_PATHS = (("o3", "o5"), ("o8", "o5"))  # DR keep-out covers both planner paths -> the two episodes share one scene
PAIR_MIN_SEP_M = 0.13  # mug-bottle centre distance: the open fingers (107 mm along world x) clear the other target
PAIR_MIN_PX = 60.0  # the two targets' centres >= 60 px apart in the head image (readiness M4 gate)
LAYOUTS = ("task", "pair")


def pair_image_sep_px(layout: dict) -> float:
    """Head-image distance (px) between the half-height centres of the mug o3 and the bottle o8 (fixed R2 head
    camera, harvest.train.r2_ma2 constants; perception.geom.project convention)."""
    from ..train.r2_ma2 import HEAD_K, HEAD_POS, HEAD_R, TABLE_TOP_Z
    P = np.array([[*layout[k][:2], TABLE_TOP_Z + OBJ_GEOM[k]["height"] / 2] for k in ("o3", "o8")])
    Pc = (P - HEAD_POS) @ HEAD_R
    uv = np.stack([HEAD_K["cx"] - HEAD_K["fx"] * Pc[:, 1] / Pc[:, 0],
                   HEAD_K["cy"] - HEAD_K["fy"] * Pc[:, 2] / Pc[:, 0]], 1)
    return float(np.linalg.norm(uv[0] - uv[1]))


def pair_layout(seed: int) -> dict:
    """{obj_id: (x, y, yaw)}: tray o5, mug o3 and bottle o8 all inside the right-arm top-down workspace (the task_layout
    rules for target / place, applied to both targets), mug-bottle >= PAIR_MIN_SEP_M and >= PAIR_MIN_PX apart in the
    head image; the yellow box o9 appears in the distractor band with p = 1/2. Own RNG stream (code 2000)."""
    rng = np.random.default_rng([int(seed), 11, 2000])
    for _ in range(100000):
        p = (rng.uniform(WS_X[0] + 0.02, WS_X[1]), rng.uniform(WS_Y[0] + 0.03, WS_Y[1] - 0.03))
        m = (rng.uniform(*WS_X), rng.uniform(*WS_Y))
        b = (rng.uniform(*WS_X), rng.uniform(*WS_Y))
        out = {"o3": (float(m[0]), float(m[1]), 0.0), "o8": (float(b[0]), float(b[1]), 0.0),
               "o5": (float(p[0]), float(p[1]), 0.0)}
        if (math.dist(p, m) >= max(0.16, _fr("o3") + _fr("o5") + 0.03)
                and math.dist(p, b) >= max(0.16, _fr("o8") + _fr("o5") + 0.03)
                and math.dist(m, b) >= PAIR_MIN_SEP_M and pair_image_sep_px(out) >= PAIR_MIN_PX):
            break
    else:  # pragma: no cover
        raise RuntimeError("pair layout")
    if rng.random() < 0.5:
        for _ in range(10000):
            q = (float(rng.uniform(*DISTRACTOR_X)), float(rng.uniform(*DISTRACTOR_Y)),
                 float(rng.uniform(-math.pi, math.pi)))
            if all(math.dist(q[:2], v[:2]) >= _fr("o9") + _fr(j) + 0.02 for j, v in out.items()) and \
                    math.dist(q[:2], m) >= 0.10 and math.dist(q[:2], b) >= 0.10:
                out["o9"] = q
                break
    return out


def layout_for(seed: int, task: str, layout: str = "task", ws=None) -> dict:
    """The layout of (seed, task) under a layout mode: 'task' = task_layout (default), 'pair' = pair_layout (only
    for PAIR_TASKS). ws: task_layout's workspace box (L8-D)."""
    check_task(task)
    if layout == "task":
        return task_layout(seed, task, ws=ws)
    if layout == "pair":
        if task not in PAIR_TASKS:
            raise ValueError(f"layout 'pair' is for {PAIR_TASKS}, not {task!r}")
        return pair_layout(seed)
    raise ValueError(f"layout {layout!r}: one of {LAYOUTS}")


def layout_paths(task: str, layout: str = "task"):
    """DR keep-out path(s): the task's (target, place) for 'task', both pair paths for 'pair'."""
    return PAIR_PATHS if layout == "pair" else (TASKS[task].target, TASKS[task].place)


def grasp_yaw(obj: str, obj_yaw: float) -> float:
    """Gripper yaw for a top-down grasp. Cylinders: TOP_DOWN_YAW. Cuboids: the yaw nearest TOP_DOWN_YAW whose
    closing axis (yaw - pi/2) is parallel to a face normal (obj_yaw + k pi/2)."""
    if OBJ_GEOM[obj]["shape"] != "cuboid":
        return TOP_DOWN_YAW
    q = math.pi / 2
    d = ((obj_yaw + q / 2) % q) - q / 2  # obj_yaw folded into [-45, 45) deg
    return TOP_DOWN_YAW + d


def close_width(obj: str) -> float:
    """Squeeze target: the grasped dimension minus GRIP_SQUEEZE_M (cylinder diameter, cuboid x side after the
    yaw alignment of grasp_yaw)."""
    g = OBJ_GEOM[obj]
    size = 2 * g["radius"] if g["shape"] == "cylinder" else (g["grasp_width"] if g["shape"] == "mesh" else g["size"][0])
    return max(0.0, size - GRIP_SQUEEZE_M)


def success_now(p: dict, tgt: str, place: str) -> bool:
    """planner._success_now for (tgt, place): on ∧ ¬holding ∧ upright; unknown (None) never counts."""
    return p.get(f"on({tgt},{place})") is True and p.get(f"holding({tgt})") is False and \
        p.get(f"upright({tgt})") is True


def lowest_z(obj: str, pos, quat_wxyz) -> float:
    """Height of the object's lowest point (same frame as pos) for its current orientation: a tilted mug rests
    on its rim, whose height is centre - (h/2 cos + r sin), not centre - h/2."""
    w, x, y, z = (float(v) for v in quat_wxyz)
    r2 = np.array([2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)])  # row 3 of R
    g = OBJ_GEOM[obj]
    he = g["half_extents"]
    if g["shape"] in ("cylinder", "marker"):
        down = abs(r2[2]) * he[2] + g["radius"] * math.hypot(r2[0], r2[1])
    else:
        down = sum(abs(r2[i]) * he[i] for i in range(3))
    return float(pos[2]) - down


def surface_contacts(pos: dict, bottom: dict, sid: str, half_xy, z_tol: float = TABLE_TOL_M) -> set:
    """Virtual contacts of a furniture surface place object sid (L8-X o19; table frame): {a, sid} when a's lowest
    point is within z_tol of the surface top (pos[sid] z + 1 mm) and its centre is inside the surface box."""
    if sid not in pos:
        return set()
    c = np.asarray(pos[sid], float)
    top = c[2] + 0.001
    out = set()
    for a, pa in pos.items():
        if a == sid:
            continue
        if abs(bottom[a] - top) <= z_tol and abs(pa[0] - c[0]) <= half_xy[0] and abs(pa[1] - c[1]) <= half_xy[1]:
            out.add(frozenset({a, sid}))
    return out


def marker_contacts(pos: dict, bottom: dict, marker: str, on_r: float = MARKER_ON_R,
                    table_tol: float = TABLE_TOL_M) -> set:
    """Virtual contacts of the visual marker (table frame positions): {a, marker} when a's lowest point (bottom[a],
    lowest_z) is on the table surface and its centre is within on_r of the marker centre."""
    if marker not in pos:
        return set()
    c = np.asarray(pos[marker], float)
    out = set()
    for a, pa in pos.items():
        if a == marker:
            continue
        if bottom[a] <= table_tol and math.hypot(pa[0] - c[0], pa[1] - c[1]) <= on_r:
            out.add(frozenset({a, marker}))
    return out


SHAPE_NAMES = {"o3": "red cylinder", "o13": "blue cylinder", "o8": "green cylinder"}  # change 22 (audit 3)
_SHAPE_WORDS = (("red mug", "red cylinder"), ("blue mug", "blue cylinder"), ("green bottle", "green cylinder"))


def use_shape_names() -> None:
    """L8S: the primitive cylinders are called cylinders (mug / bottle names are kept for real meshes): object
    names, task instructions / stage texts and the relational reference name."""
    from ..astra_motion import prompts as P
    P.OBJ_NAME.update(SHAPE_NAMES)
    P.REL_NAMES["bottle"] = SHAPE_NAMES["o8"]
    for k in ("o17", "o18", "o27", "o28", "o29"):
        if k in P.OBJ_NAME:
            for a, b in _SHAPE_WORDS:
                P.OBJ_NAME[k] = P.OBJ_NAME[k].replace(a, b)
    for t, s in list(TASKS.items()):
        if t.startswith(("ov_", "st__", "pu__", "dr", "ai__")):
            continue
        ins, st = s.instruction, dict(s.stage_text)
        for a, b in _SHAPE_WORDS:
            ins = ins.replace(a, b)
            st = {k: v.replace(a.split()[1], b.split()[1]) for k, v in st.items()}
        TASKS[t] = s.__class__(s.id, s.target, s.place, ins, st, s.extras)
        if t in X_TASKS:
            X_TASKS[t] = TASKS[t]
