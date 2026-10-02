"""L9 v2 episode allocation over robots and task definitions (main 10-02 02h: ~15,000 successful episodes, AI Worker
40 % / Franka / R1 Pro / G1 20 % each, >= 60 per definition summed over robots, every robot covers every family,
new families more; owner 10-02 03h: L9 v2 alone replaces L8S, so relation / put_in are no longer reduced and the
AI Worker right arm gets >= half of its rows) and plan rows / jobs for tools/l9/plan.py v2.

allocate() counts SUCCESSFUL episodes; plan_rows() turns them into plan rows with the definition's pilot yield
(rows = ceil(successes / yield)). Held-out definitions (spec §7 / owner principle 6: ~5 % by axis, never trained)
get only the floor and their rows carry split = "holdout". Pure."""
from __future__ import annotations

import hashlib
import math
from collections import defaultdict

from . import task9v2 as V2

ROBOT_SHARE = {"ffw_sg2": 0.40, "franka_mast": 0.20, "r1pro": 0.20, "g1": 0.20}
ROBOT_ARMS = {"ffw_sg2": ("right", "left"), "franka_mast": ("right",), "r1pro": ("right", "left"),
              "g1": ("right", "left")}  # Franka: right-arm rows only in stage 1 (spec §9.2)
LOW_SHARE_FAMILIES = ("relation", "put_in")  # were reduced (L8S overlap); owner 10-02 03h: same weight again
FAMILY_WEIGHT_LOW, FAMILY_WEIGHT_V1, FAMILY_WEIGHT_NEW, FAMILY_WEIGHT_RECOVERY = 1.0, 1.0, 1.5, 1.0  # [가설]
RIGHT_SHARE = {"ffw_sg2": 0.55}  # right-arm share of a two-arm robot (others 0.5); L8S was AI Worker right only
DEFAULT_YIELD, MIN_YIELD = 0.6, 0.3
CLEAN_SHARE = 0.25  # = tools/l9/plan.py style_of
HOLDOUT_SHARE = 0.05


STEP_WEIGHT = 0.5  # [가설] weight x (1 + 0.5 x (steps - 1)): more ordered multi-object episodes (owner 10-02)


def def_weight(k: str, f: str) -> float:
    d = V2.DEFS_V2.get(k)
    n = len(d.steps) if d is not None else 1
    return family_weight(f) * (1.0 + STEP_WEIGHT * (n - 1))


def family_weight(f: str) -> float:
    if f in LOW_SHARE_FAMILIES:
        return FAMILY_WEIGHT_LOW
    if f == "recovery":
        return FAMILY_WEIGHT_RECOVERY
    return FAMILY_WEIGHT_NEW if f in V2.NEW_FAMILIES else FAMILY_WEIGHT_V1


def _h(*p) -> float:
    return int(hashlib.sha256(":".join(map(str, p)).encode()).hexdigest()[:12], 16) / float(16 ** 12)


def _round_to(vals: dict, total: int) -> dict:
    """Largest remainder rounding of non-negative floats to integers summing to total (ties by key)."""
    fl = {k: int(math.floor(v)) for k, v in vals.items()}
    left = total - sum(fl.values())
    order = sorted(vals, key=lambda k: (-(vals[k] - fl[k]), k))
    for k in order[:max(left, 0)]:
        fl[k] += 1
    return fl


def unhostable(report: dict, robots=("ffw_sg2",)) -> list:
    """Definitions that never instantiated in a tools/l9/v2_hostable.py report for any of `robots` (the plan leaves
    them out: their rows would only redraw)."""
    out = []
    for k, v in report.items():
        rs = [r for r in robots if isinstance(v.get(r), dict)]
        if rs and not any(v[r].get("ok", 0) > 0 for r in rs):
            out.append(k)
    return sorted(out)


# The held-out definitions, FROZEN (owner 10-02, E-TP1 leak): the hashed choice below depends on the definition set,
# which grew after the first production plans, and the pilot planner wrote these definitions as train rows. Every
# planner, run9 and the build gate use this list; never change it (adding a definition must not move the hold-out).
HOLDOUT_FROZEN = ("in_second_container", "ins_from_block", "kit_from_sink", "line_next_to", "rel_right",
                  "sel_bigger_in", "sort_food_bowl_toy_side", "st_tower3_stand", "swap_levels", "tall_between")


def is_holdout(def_id) -> bool:
    return str(def_id) in HOLDOUT_FROZEN


# Robot-level build gate (user 10-03 01h): a robot must clear every one of its task types (single-arm pick/place,
# articulated, bimanual) at >= the 40% pilot gate before ANY of its episodes (of any task type, including ones
# already on disk) enter a training build -- a robot never sits in production for some task types and not others.
# False here does not stop or delete production; harvest.l9.run9 / art_prod / bimanual keep writing episodes (they
# are the gate evidence), only tools/l9/build_v2.py drops that robot's rows until this flips to True.
ROBOT_GATE_CLEARED = {"ffw_sg2": True, "franka_mast": True, "r1pro": False, "g1": False}


def robot_build_ready(robot) -> bool:
    return bool(ROBOT_GATE_CLEARED.get(str(robot), False))


def holdout_defs(defs: dict, share: float = HOLDOUT_SHARE) -> list:
    """The frozen hold-out definitions present in defs (HOLDOUT_FROZEN)."""
    return sorted(k for k in HOLDOUT_FROZEN if k in defs)


def holdout_defs_hashed(defs: dict, share: float = HOLDOUT_SHARE) -> list:
    """(how HOLDOUT_FROZEN was chosen) ~share of the definitions, at most one per family (families in a hashed
    order), the hashed-first definition of each: deterministic for a fixed definition set."""
    n = max(1, int(round(share * len(defs))))
    fams = sorted(set(defs.values()), key=lambda f: _h("l9v2-holdout-f", f))
    out = []
    for f in fams:
        if len(out) >= n:
            break
        ks = sorted((k for k, ff in defs.items() if ff == f), key=lambda k: _h("l9v2-holdout", k))
        if len(ks) >= 6:  # keep >= 5 trained definitions in the family
            out.append(ks[0])
    return sorted(out)


def allocate(defs: dict, total: int = 15000, min_per_def: int = 60, robot_share: dict | None = None,
             exclude=(), holdout=()) -> dict:
    """defs {id: family} -> {id: {robot: successes}}. Every definition gets >= min_per_def; the rest goes by family
    weight (held-out definitions get only the floor); each definition's count is split over the robots that may run
    it (exclude = {(robot, id)}) so the robot totals follow robot_share."""
    share = dict(robot_share or ROBOT_SHARE)
    ids = sorted(defs)
    if len(ids) * min_per_def > total:
        raise ValueError(f"{len(ids)} definitions x {min_per_def} > {total}")
    ho = set(holdout)
    w = {k: (0.0 if k in ho else def_weight(k, defs[k])) for k in ids}
    rest = total - len(ids) * min_per_def
    sw = sum(w.values()) or 1.0
    per = _round_to({k: min_per_def + rest * w[k] / sw for k in ids}, total)
    ex = set(exclude)
    ssum = sum(share.values())
    got = defaultdict(int)
    out = {}
    cum = 0
    for k in ids:
        cum += per[k]
        target = {r: share[r] / ssum * cum for r in share}  # robot totals expected after this definition
        allowed = [r for r in share if (r, k) not in ex]
        if not allowed:
            raise ValueError(f"no robot may run {k}")
        s = sum(share[r] for r in allowed)
        f = {r: per[k] * share[r] / s for r in allowed}
        n = {r: int(math.floor(v)) for r, v in f.items()}
        left = per[k] - sum(n.values())
        order = sorted(allowed, key=lambda r: (-(target[r] - got[r] - n[r]), -(f[r] - n[r]), r))
        for r in order[:left]:
            n[r] += 1
        for r, v in n.items():
            got[r] += v
        out[k] = {r: v for r, v in n.items() if v > 0}
    return out


def _arm(arms: tuple, j: int, right: float) -> str:
    """Deterministic arm deal: in every run of rows the right arm gets round(right x n) (Bresenham)."""
    if len(arms) == 1:
        return arms[0]
    return "right" if math.floor((j + 1) * right) > math.floor(j * right) else "left"


def style_of(seed: int) -> str:
    u = int(hashlib.sha256(f"l9-style:{seed}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return "clean" if u < CLEAN_SHARE else ""


def plan_rows(alloc: dict, pairs: dict, start: int = 3000000, yields: dict | None = None, holdout=()) -> list:
    """Plan rows {seed, robot, grip_max, arm, family, rule, def, task_family, split, style, v2, n_steps, recovery,
    requires}: per (definition, robot) ceil(successes / yield) rows, arms dealt by RIGHT_SHARE, (family, layout rule) pairs
    dealt round-robin from pairs[def]."""
    yields = yields or {}
    ho = set(holdout)
    rows, seed = [], int(start)
    for i, k in enumerate(sorted(alloc)):
        if not pairs.get(k):
            continue
        d = V2.DEFS_V2[k]
        prof = V2.def_profile(d)
        y = max(float(yields.get(k, DEFAULT_YIELD)), MIN_YIELD)
        j = 0
        for robot in sorted(alloc[k]):
            n = int(math.ceil(alloc[k][robot] / y))
            arms = ROBOT_ARMS[robot]
            for jj in range(n):
                f, r = pairs[k][(i * 7 + j) % len(pairs[k])]
                rows.append({"seed": seed, "robot": robot, "grip_max": V2.grip_max_of(robot),
                             "arm": _arm(arms, jj, RIGHT_SHARE.get(robot, 0.5)), "family": f, "rule": r, "def": k,
                             "task_family": d.family,
                             "split": "holdout" if k in ho else "train", "style": style_of(seed), "v2": True,
                             "n_steps": prof["n_steps"], "recovery": prof["recovery"], "requires": prof["requires"]})
                seed += 1
                j += 1
    return rows


def jobs_v2(rows: list, job_size: int, pool0: int = 0) -> list:
    """Chunks of <= job_size rows of one (robot, arm) — one Isaac process runs one robot; every job its own pool /
    room-subset index."""
    by = defaultdict(list)
    for r in rows:
        by[(r["robot"], r["arm"])].append(r)
    out, k = [], 0
    for key in sorted(by):
        rs = by[key]
        for i in range(0, len(rs), job_size):
            chunk = rs[i:i + job_size]
            for r in chunk:
                r.update(job=f"v{k:05d}_{key[0]}_{key[1][0]}", pool=pool0 + k, rooms=pool0 + k)
            out.append(chunk)
            k += 1
    return out
