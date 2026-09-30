"""L9 asset catalogs (harvest/l9/assets9/*.json, built by tools/l9/assets) and per-process pools. Pure.

Pool rows are objv-compatible (harvest.sim.objv.register / register_containers) plus `role9`:
  target     graspable top-down (grasp_rule topdown_7_10cm; thin pens are not used in stage 1)
  container  kinematic place object with an `inside` record (gate_pass): holders, bowls, bins, plates, trays
  clutter    distractors (never moved by the task)
A process pool rotates through the catalog (pool index p takes the p-th slice of every category's seeded order), so
consecutive pools cover the whole catalog before any object repeats."""
from __future__ import annotations

import hashlib
import json
import os

import numpy as np

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets9")
ALLOWED_LICENCES = ("cc0", "cc-by", "cc by", "by", "cc-by-sa", "cc by-sa", "by-sa", "apache", "cc0 1.0",
                    "cc by 4.0", "cc-by-4.0", "cc by-sa 4.0", "cc-by-sa-4.0", "cc0-1.0", "apache-2.0", "by-4.0",
                    "by-sa-4.0", "mit")
BAD = ("nc", "nd", "noncommercial", "noderivatives")
_CACHE: dict = {}
NOT_TARGET = ("shoe",)  # smoke 2026-10-01: a boot rescaled to 8.5 cm slipped out of the top-down grasp every try
TARGET_R_MAX = 0.065  # moved objects: the work band is ~0.32 x 0.34 m (larger ones stay clutter)


def licence_ok(s: str) -> bool:
    t = " ".join(str(s or "").lower().replace("_", " ").split())
    if not t:
        return False
    words = set(t.replace("-", " ").replace("/", " ").replace("(", " ").replace(")", " ").split())
    if words & set(BAD):
        return False
    return any(a in t for a in ("cc0", "cc by", "cc-by", "apache", "mit")) or t in ALLOWED_LICENCES


def _load(name: str) -> dict:
    if name not in _CACHE:
        _CACHE[name] = json.load(open(os.path.join(DIR, name), encoding="utf-8"))
    return _CACHE[name]


def objects(split: str = "train") -> dict:
    """New L9 objects (stable) of this split, with role9."""
    out = {}
    for k, r in _load("objects_l9.json")["objects"].items():
        if r.get("split") != split or not r.get("stable_upright"):
            continue
        role = r.get("role")
        if role == "target" and r.get("grasp_rule") == "topdown_7_10cm" and float(r["footprint_r"]) <= TARGET_R_MAX                 and r.get("l9cat") not in NOT_TARGET and k not in blocked_targets():
            out[k] = dict(r, role9="target")
        elif role in ("clutter", "target"):
            out[k] = dict(r, role9="clutter")
    return out


def containers(split: str = "train") -> dict:
    out = {}
    for k, r in _load("containers_l9.json")["containers"].items():
        if r.get("gate_pass") and r.get("split", "train") == split:
            out[k] = fit_container(dict(r, role9="container", l9cat=r.get("l9cat") or r.get("noun")))
    return out


def pool_quota() -> dict:
    """Pool make-up per process: (role9, bucket) -> count."""
    return {("target", "slender"): 6, ("target", "food"): 5, ("target", "toyish"): 5, ("target", "drink"): 3,
            ("target", "base"): 5, ("target", "any"): 4, ("container", "narrow"): 3, ("container", "wide"): 4,
            ("container", "flat"): 3, ("clutter", "any"): 8}


def bucket_of(r: dict) -> tuple:
    from .task9 import DRINK, FOOD, TOYISH, flat_top, is_slender, kind_of
    if r["role9"] == "container":
        return ("container", kind_of(r))
    if r["role9"] == "clutter":
        return ("clutter", "any")
    if is_slender(r):
        return ("target", "slender")
    c = r.get("l9cat")
    if c in FOOD:
        return ("target", "food")
    if flat_top(r):
        return ("target", "base")
    if c in TOYISH:
        return ("target", "toyish")
    if c in DRINK:
        return ("target", "drink")
    return ("target", "any")


def catalog(split: str = "train") -> dict:
    key = f"cat:{split}"
    if key not in _CACHE:
        _CACHE[key] = {**objects(split), **containers(split)}
    return _CACHE[key]


def pool_for(p: int, split: str = "train", quota: dict | None = None) -> dict:
    """The p-th pool: every bucket takes its next slice of a fixed seeded order (wrapping around)."""
    cat = catalog(split)
    quota = quota or pool_quota()
    by: dict = {}
    for k in sorted(cat):
        by.setdefault(bucket_of(cat[k]), []).append(k)
    out = {}
    for b, n in quota.items():
        ks = by.get(b, [])
        if not ks:
            continue
        order = sorted(ks, key=lambda k: hashlib.sha256(f"l9pool:{b}:{k}".encode()).hexdigest())
        for j in range(n):
            k = order[(p * n + j) % len(order)]
            out[k] = cat[k]
    return out


def bucket_sizes(split: str = "train") -> dict:
    from collections import Counter
    return dict(Counter(bucket_of(r) for r in catalog(split).values()))


CONTAINER_R_MAX = {"narrow": 0.090, "wide": 0.120, "flat": 0.100}  # footprint radius after rescaling (work band)
_LEN = ("half_extents", "size", "footprint_r", "root_above_bottom", "centre_from_root_xy", "height", "grasp_width",
        "length", "inner_floor_z", "rim_z", "opening_min_side", "opening_box", "inner_box", "depth", "bottom_z",
        "centre_xy", "caliper_centre", "origin_from_root")


def _mul(v, s):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return round(float(v) * s, 5)
    if isinstance(v, (list, tuple)):
        return [_mul(x, s) for x in v]
    return v


def scaled(row: dict, s: float) -> dict:
    """A kinematic container row uniformly scaled by s at spawn (spawn_scale; every length field x s)."""
    if abs(s - 1.0) < 1e-6:
        return dict(row)
    out = dict(row)
    for k in _LEN:
        if k in out and out[k] is not None:
            out[k] = _mul(out[k], s)
    ins = dict(out.get("inside") or {})
    for k in _LEN:
        if k in ins and ins[k] is not None:
            ins[k] = _mul(ins[k], s)
    out["inside"] = ins
    out["spawn_scale"] = [round(s, 5)] * 3
    out["scale_l9"] = round(s, 5)
    return out


def fit_container(row: dict) -> dict:
    """Shrink a container to CONTAINER_R_MAX of its kind (never enlarge)."""
    from .task9 import kind_of
    k = kind_of(row)
    s = min(1.0, CONTAINER_R_MAX.get(k, 0.10) / float(row["footprint_r"]))
    return scaled(row, s)


def blocked_targets() -> set:
    """Targets excluded after the pilots / audits (assets9/blocked_targets.json: never lifted in >= 2 tries)."""
    if "blocked" not in _CACHE:
        p = os.path.join(DIR, "blocked_targets.json")
        _CACHE["blocked"] = set(json.load(open(p))["ids"]) if os.path.exists(p) else set()
    return _CACHE["blocked"]
