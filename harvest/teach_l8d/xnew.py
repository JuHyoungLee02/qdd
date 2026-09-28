"""L8-X new tasks (prereg_l8x_tasks.md, user-log 161): stacking st__<top>__<base>, pushing pu__<obj>; real objects
from harvest/sim/assets_x/objects_real.json (GSO + THOR props, objv-compatible canonical rows, name-checked).

Task registration (register_new_tasks), eligibility, the name gate of the judge stage (name_gate), the push truth
plan (plan_push: existing eef + gripper commands only, steps above_start / lower_behind / push / lift_away), the
label texts of the push steps, and the post-hoc judges success_stack / success_push over the collector rows.
Pure (the Isaac side is the existing runner through the hooks in objv / xlabels / collect)."""
from __future__ import annotations

import hashlib
import json
import math
import os

import numpy as np

REAL_TABLE = "assets_x/objects_real.json"  # under harvest/sim
STACK_TEXTS = ["Put the {a} on the {b}.", "Stack the {a} on top of the {b}.", "Place the {a} on the {b}.",
               "Set the {a} on top of the {b}.", "Put the {a} onto the {b}.", "Place the {a} on top of the {b}.",
               "Stack the {a} onto the {b}.", "Move the {a} onto the {b}.", "Lift the {a} and put it on the {b}.",
               "Pick up the {a} and set it on the {b}.", "Put the {a} so it rests on the {b}.",
               "Place the {a} onto the top of the {b}.",
               # OOD phrasings (never in training)
               "Get the {a} and stack it on the {b}.", "The {a} goes on top of the {b}.",
               "Could you put the {a} on the {b}?"]
PUSH_TEXTS = ["Push the {a} onto the magenta marker.", "Slide the {a} onto the magenta marker.",
              "Push the {a} to the magenta marker.", "Slide the {a} over to the magenta marker.",
              "Without picking it up, push the {a} onto the magenta marker.", "Nudge the {a} onto the magenta marker.",
              "Push the {a} until it sits on the magenta marker.", "Slide the {a} to the magenta marker.",
              "Move the {a} onto the magenta marker by pushing it.", "Push the {a} across to the magenta marker.",
              # OOD phrasings
              "Shove the {a} over onto the magenta marker.", "Can you slide the {a} onto the magenta marker?"]
STACK_OOD_TEXTS = (12, 13, 14)
PUSH_OOD_TEXTS = (10, 11)
MARKER = "o11"
MIN_H, MAX_H, MIN_W, MAX_W = 0.07, 0.10, 0.025, 0.085  # = objv.eligible (truth: prereg_l8d change 8)
BASE_H = (0.03, 0.10)
BASE_TOP_SHARE = 0.60
BASE_MARGIN = 0.03  # gate 35200: a 5 cm candle on a 6 cm jar top fell off; +1 cm was too tight
ROLLING_NOUNS = ("egg", "apple", "potato", "tomato", "ball")  # gate 35203/35205/35207/35209: eggs rolled off
# primitive stacking base (scene o12, the white stand 12 x 12 x 8 cm): every stack top also gets it as a base
PRIMITIVE_BASES = {"o12": {"task_name": "white stand", "noun": "stand", "colour": "white", "height": 0.08,
                           "half_extents": [0.06, 0.06, 0.04], "task_target_ok": True,
                           "name_check": {"claimed": "stand", "noun": "stand", "renamed": False, "reasons": []}}}
PUSH_STEPS = ("above_start", "lower_behind", "push", "lift_away")
PUSH_BACKOFF = 0.035  # start this far behind the object's edge
PUSH_TCP_DZ = 0.045  # TCP (pad centre) above the support while pushing: pads span ~2.5-6.5 cm, objects 7-10 cm
PUSH_STEP_MAX = 0.04
PUSH_DONE_R = 0.03
PUSH_OFFLINE_M = 0.02  # the object left the push line -> start again from behind


def _h(s: str) -> int:
    return int(hashlib.sha256(s.encode()).hexdigest()[:8], 16)


def load_real_rows(path: str | None = None) -> dict:
    p = path or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sim", REAL_TABLE)
    return json.load(open(p))["objects"]


def target_ok(r: dict, split: str = "train") -> bool:
    return (r.get("split") == split and r.get("task_target_ok") is True and r.get("pose") == "upright"
            and MIN_H - 1e-9 <= r["height"] <= MAX_H + 1e-9 and MIN_W - 1e-9 <= r["grasp_width"] <= MAX_W + 1e-9)


def base_ok(r: dict, top: dict, split: str = "train") -> bool:
    """Stacking base: stable, name-checked, 3-10 cm high, flat top >= 60 % of its box top and wider than the top
    object's footprint + 2 cm, and a different name from the top object."""
    t = r.get("top_surface")
    if not (r.get("split") == split and r.get("task_target_ok") is True and t and
            BASE_H[0] - 1e-9 <= r["height"] <= BASE_H[1] + 1e-9):
        return False
    box_area = 4 * r["half_extents"][0] * r["half_extents"][1]
    (x0, x1), (y0, y1) = t["box"]
    wt, lt = 2 * top["half_extents"][0], 2 * top["half_extents"][1]  # canonical: narrow x (both laid out narrow-x)
    # the top object stands narrow side along x on the base centre: both base top sides >= its width + 1 cm (its
    # centre and most of its footprint on the flat top; on() checks the centre inside the base box)
    return (t["area"] >= BASE_TOP_SHARE * box_area and x1 - x0 >= wt + BASE_MARGIN
            and y1 - y0 >= max(wt, 0.6 * lt) + BASE_MARGIN
            and r.get("task_name") != top.get("task_name"))


def push_ok(r: dict, split: str = "train") -> bool:
    """Pushable: a target that slides (round or box, not a ball), base >= 3 cm."""
    return (target_ok(r, split) and r.get("sphericity", 0.0) < 0.8 and r["grasp_width"] >= 0.03
            and (r.get("circularity", 0.0) >= 0.88 or r.get("boxiness", 0.0) >= 0.5))


def stack_top_ok(r: dict, split: str = "train") -> bool:
    """Stack top: a target that does not roll off (no egg / fruit / ball, sphericity < 0.6)."""
    return target_ok(r, split) and r.get("noun") not in ROLLING_NOUNS and r.get("sphericity", 0.0) < 0.6


def _row(rows: dict, k: str) -> dict:
    return PRIMITIVE_BASES[k] if k in PRIMITIVE_BASES else rows[k]


def stack_pairs(rows: dict, split: str = "train", per_top: int = 3) -> list:
    """Frozen (top, base) pairs: for each eligible top, up to per_top bases by a stable hash order."""
    tops = sorted(k for k, r in rows.items() if stack_top_ok(r, split))
    out = []
    for a in tops:
        bases = sorted((k for k, r in rows.items() if k != a and base_ok(r, rows[a], split)),
                       key=lambda k: _h(f"st:{a}:{k}"))
        out += [(a, b) for b in bases[:per_top]] + [(a, p) for p in sorted(PRIMITIVE_BASES)]
    return out


def push_objects(rows: dict, split: str = "train") -> list:
    return sorted(k for k, r in rows.items() if push_ok(r, split))


def stack_task_id(a: str, b: str) -> str:
    return f"st__{a}__{b}"


def push_task_id(a: str) -> str:
    return f"pu__{a}"


def is_new_task(t: str) -> bool:
    return str(t).startswith(("st__", "pu__"))


def parse(t: str):
    parts = str(t).split("__")
    return parts[0], parts[1:]


def text_index(t: str, seed: int, ood: bool = False) -> int:
    kind, _ = parse(t)
    n = len(STACK_TEXTS if kind == "st" else PUSH_TEXTS)
    oodset = STACK_OOD_TEXTS if kind == "st" else PUSH_OOD_TEXTS
    pool = list(oodset) if ood else [i for i in range(n) if i not in oodset]
    return pool[_h(f"{t}:{seed}") % len(pool)]


def instruction(t: str, rows: dict, idx: int = 0) -> str:
    kind, ids = parse(t)
    if kind == "st":
        return STACK_TEXTS[idx].format(a=rows[ids[0]]["task_name"], b=_row(rows, ids[1])["task_name"])
    return PUSH_TEXTS[idx].format(a=rows[ids[0]]["task_name"])


def register_new_tasks(tasks, rows: dict | None = None) -> list:
    """Register the real objects and the st__ / pu__ tasks among `tasks` (objv.register + tasks.TASKS / X_TASKS /
    X_TASK_CODE; layout streams 6000 + hash (stack) / 7000 + hash (push)); idempotent -> object ids."""
    from ..sim import objv
    from ..sim import tasks as T
    new = [t for t in tasks if is_new_task(t)]
    if not new:
        return []
    rows = rows or load_real_rows()
    ids = sorted({k for t in new for k in parse(t)[1]})
    objv.register({k: rows[k] for k in ids if k not in PRIMITIVE_BASES})
    for t in new:
        if t in T.TASKS:
            continue
        kind, obj = parse(t)
        if kind == "st":
            a, b = obj
            spec = T.Task(t, a, b, instruction(t, rows),
                          {"S1": f"pick up {rows[a]['task_name']} {a}",
                           "S2": f"place {rows[a]['task_name']} {a} on {_row(rows, b)['task_name']} {b}"})
            code = 6000
        else:
            a = obj[0]
            spec = T.Task(t, a, MARKER, instruction(t, rows),
                          {"S1": f"push {rows[a]['task_name']} {a}", "S2": f"onto marker {MARKER}"})
            code = 7000
        T.TASKS[t] = T.X_TASKS[t] = spec
        T.X_TASK_CODE[t] = code + _h(t) % 900
    return ids


def name_gate(t: str, rows: dict, present_names=()) -> str | None:
    """Judge-stage name check (prereg 2.5): None = ok, else the skip reason. The instruction's objects must carry a
    shape-checked noun (not the fallback 'object'), differ from each other and from every other object present,
    and a colour word in the name must be the object's measured colour."""
    _, ids = parse(t)
    names = [_row(rows, k)["task_name"] for k in ids]
    for k in ids:
        r = _row(rows, k)
        if r.get("noun") in (None, "object", "SKIP") or not r.get("name_check"):
            return f"name check: {k} has no checked noun"
        if r.get("colour") and r["colour"] not in r["task_name"].split():
            return f"name check: {k} colour {r['colour']} not in its name"
    if len(set(names)) < len(names):
        return "name check: the two objects share a name"
    for n in present_names:
        if n in names:
            return f"name check: another object is also called '{n}'"
    return None


PUSH_DIRS = ((1.0, 0.0), (0.0, 1.0), (0.0, -1.0))  # away from the robot or sideways, never towards it
PUSH_DIST = (0.10, 0.18)


def push_layout(seed: int, task: str, ws, fr) -> dict:
    """Layout of pu__<obj>: the object and the magenta marker 10-18 cm away along +x / +-y, both inside the
    workspace box (marker centre 3 cm inside), the start spot behind the object inside the box too.
    fr: footprint radius of an object id. Stream [seed, 11, X_TASK_CODE[task]]."""
    from ..sim.tasks import X_TASK_CODE
    (x0, x1), (y0, y1) = ws
    a = parse(task)[1][0]
    r = fr(a)
    rng = np.random.default_rng([int(seed), 11, X_TASK_CODE[task]])
    for _ in range(100000):
        u = np.array(PUSH_DIRS[int(rng.integers(len(PUSH_DIRS)))])
        d = rng.uniform(*PUSH_DIST)
        m = np.array([rng.uniform(x0, x1), rng.uniform(y0, y1)])
        p = m + u * d
        s = m - u * (r + PUSH_BACKOFF)
        if (x0 + 0.03 <= p[0] <= x1 and y0 + 0.03 <= p[1] <= y1 - 0.03 and x0 - 0.04 <= s[0] <= x1
                and y0 - 0.02 <= s[1] <= y1 + 0.02):
            yaw = float(rng.uniform(-math.pi, math.pi))
            return {a: (float(m[0]), float(m[1]), yaw), MARKER: (float(p[0]), float(p[1]), 0.0)}
    raise RuntimeError("push layout")  # pragma: no cover


# --------------------------------------------------------------------------------------------- push truth plan
def _r(v):
    return [round(float(x), 4) for x in v]


def push_geometry(st: dict, info: dict, support_z: float):
    tg = info["tgt"]
    c = np.asarray(st["obj"][tg], float)
    m = np.asarray(st["obj"][info["place"]], float)
    d = m[:2] - c[:2]
    dist = float(np.linalg.norm(d))
    u = d / max(dist, 1e-9)
    from ..sim.scene import OBJ_GEOM
    r = float(OBJ_GEOM[tg]["footprint_r"]) if tg in OBJ_GEOM else 0.04
    start = c[:2] - u * (r + PUSH_BACKOFF)
    return c, m, u, dist, r, start


def plan_push(st: dict, info: dict, table_z: float, w_open: float):
    """Push truth: closed fingers behind the object, TCP PUSH_TCP_DZ above the support, push along the object
    -> marker line in <= 4 cm steps until the centre is within 3 cm of the marker, then lift away; the object off
    the line by > 2 cm -> back behind it. -> (step, command)."""
    sz = float(info.get("sup_tgt", table_z))
    pred = st["pred"]
    tcp = np.asarray(st["tcp"], float)
    c, m, u, dist, r, start = push_geometry(st, info, sz)
    z_push = sz + PUSH_TCP_DZ
    z_above = z_push + 0.10
    if pred.get(f"on({info['tgt']},{info['place']})") is True and dist <= PUSH_DONE_R:
        if tcp[2] < z_above - 0.02:
            return "lift_away", {"mode": "eef", "position_m": _r([tcp[0], tcp[1], z_above]), "gripper": "keep"}
        return "done", {"mode": "stop"}
    if pred.get(f"upright({info['tgt']})") is False:
        return "tipped", None
    # pushing when the fingers are low, behind the object and on its line
    rel = tcp[:2] - c[:2]
    along = float(rel @ u)
    off = float(abs(rel @ np.array([-u[1], u[0]])))
    low = tcp[2] <= z_push + 0.015
    if low and along < -(r - 0.01) and off <= PUSH_OFFLINE_M:
        goal = c[:2] + u * min(dist, PUSH_STEP_MAX) - u * r
        return "push", {"mode": "eef", "position_m": _r([goal[0], goal[1], z_push]), "gripper": "keep"}
    if np.linalg.norm(tcp[:2] - start) <= 0.01 and tcp[2] <= z_above + 0.01:
        return "lower_behind", {"mode": "eef", "position_m": _r([start[0], start[1], z_push]), "gripper": "keep"}
    if tcp[2] < z_above - 0.02:  # low but not behind the object: rise first (never sweep through it)
        return "lift_away", {"mode": "eef", "position_m": _r([tcp[0], tcp[1], z_above]), "gripper": "keep"}
    return "above_start", {"mode": "eef", "position_m": _r([start[0], start[1], z_above]), "gripper": "close"}


def texts(step: str, tn: str, pn: str):
    """(doing, remaining, done) label texts of the push steps (= teach_l8.labels._texts shape)."""
    lower, push, lift = (f"lower the closed fingers behind the {tn}", f"push the {tn} onto the {pn}",
                         "lift the gripper away")
    table = {"above_start": (f"move the closed gripper above the spot behind the {tn}", [lower, push, lift], []),
             "lower_behind": (lower, [push, lift], []),
             "push": (push, [lift], [lower]),
             "lift_away": (lift, [], [f"push the {tn} onto the {pn}"])}
    return table[step]


# ------------------------------------------------------------------------------------------------- judges
def never_held(rows: list) -> bool:
    """Push judge: the target was never held (grip on it) during the episode (labels rows carry the truth pred)."""
    return not any(r.get("held") for r in rows)


def success_stack(rows: list, max_base_move: float = 0.02) -> bool:
    """Stack judge (on top of success_now): the base stayed where it was (<= 2 cm) over the episode."""
    ps = [np.asarray(r["gt"]["place"], float) for r in rows if r.get("gt") and r["gt"].get("place") is not None]
    if len(ps) < 2:
        return True
    return float(np.linalg.norm(ps[-1][:2] - ps[0][:2])) <= max_base_move


def success_push(rows: list) -> bool:
    return never_held(rows)


assert math.isclose(PUSH_TCP_DZ, 0.045)
