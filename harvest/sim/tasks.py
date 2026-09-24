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

from .scene import DISTRACTOR_X, DISTRACTOR_Y, OBJ_GEOM, WS_X, WS_Y, sample_layout

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


def task_layout(seed: int, task: str) -> dict:
    """{obj_id: (x, y, yaw)} world xy for (seed, task); mug_tray = the standard layout."""
    check_task(task)
    if task == "mug_tray":
        return sample_layout(seed)
    s = TASKS[task]
    rng = np.random.default_rng([int(seed), 11, 1000 + TASK_CODE[task]])
    for _ in range(10000):
        p = (rng.uniform(WS_X[0] + 0.02, WS_X[1]), rng.uniform(WS_Y[0] + 0.03, WS_Y[1] - 0.03))
        m = (rng.uniform(*WS_X), rng.uniform(*WS_Y))
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
    size = 2 * g["radius"] if g["shape"] == "cylinder" else g["size"][0]
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
