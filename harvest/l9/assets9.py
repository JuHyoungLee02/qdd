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
        if role == "target" and r.get("grasp_rule") == "topdown_7_10cm" and float(r["footprint_r"]) <= TARGET_R_MAX                 and r.get("l9cat") not in NOT_TARGET and k not in blocked_targets()                 and (gate_pass() is None or k in gate_pass()):
            out[k] = dict(r, role9="target")
        elif role in ("clutter", "target") and float(r["height"]) <= 0.25:  # ungated / failed targets stay as clutter
            out[k] = dict(r, role9="clutter")
    return out


def l8s_targets(split: str = "train") -> dict:
    """L8S real objects referenced by the L9 table as targets that passed the L8S target gate (task_target_ok):
    known-good grasps (role9 target, l8s_proven)."""
    here = os.path.dirname(os.path.dirname(DIR))
    out, tabs = {}, {}
    for ref in _load("objects_l9.json").get("l8s", {}).values():
        if ref.get("role") != "target" or not ref["table"].endswith("objects_real.json"):
            continue
        if ref["table"] not in tabs:
            tabs[ref["table"]] = json.load(open(os.path.join(os.path.dirname(here), ref["table"])))["objects"]
        r = tabs[ref["table"]].get(ref["id"])
        if r is None or not r.get("task_target_ok") or r.get("split", "train") != split:
            continue
        out[ref["id"]] = dict(r, role9="target", l9cat=ref.get("l9cat"), colour=ref.get("colour", r.get("colour")),
                              l8s_proven=True)
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
            ("target", "base"): 5, ("target", "any"): 4, ("container", "narrow"): 4, ("container", "wide_bowl"): 4,
            ("container", "wide_bin"): 4, ("container", "wide_other"): 3,
            ("container", "flat"): 5, ("clutter", "any"): 8}  # G1 re-pilot: "no pool object" was the main draw failure


def bucket_of(r: dict) -> tuple:
    from .task9 import DRINK, FOOD, TOYISH, flat_top, is_slender, kind_of
    if r["role9"] == "container":
        k = kind_of(r)
        if k == "wide":  # category-balanced: bowls dominate the catalog (204 of 298)
            c = r.get("l9cat")
            return ("container", "wide_bowl" if c == "bowl" else "wide_bin" if c in ("bin", "basket", "box") else "wide_other")
        return ("container", k)
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
        _CACHE[key] = {**objects(split), **l8s_targets(split), **containers(split)}
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


CONTAINER_R_MAX = {"narrow": 0.090, "wide": 0.120, "flat": 0.110}  # footprint radius after rescaling (work band)
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


def furniture_mesh(split: str = "train") -> dict:
    """Licensed mesh furniture (L9 new + the L8S tables they reference): {name: asset row (dst, collider_size,
    origin_offset, yaw?, category, license, source)}; prim-safe names."""
    import re
    key = f"fm:{split}"
    if key in _CACHE:
        return _CACHE[key]
    here = os.path.dirname(DIR)
    out = {}
    tab = _load("furniture_mesh_l9.json")
    rows = dict(tab["assets"])
    for ref in tab.get("l8s", {}).values():
        src = json.load(open(os.path.join(os.path.dirname(os.path.dirname(here)), ref["table"])))
        r = (src.get("assets") or {}).get(ref["id"])
        if r is not None:
            rows[ref["id"]] = r
    for k, r in rows.items():
        if r.get("split", "train") != split or not r.get("dst") or not licence_ok(r.get("license", "")):
            continue
        sx, sy, sz = r["collider_size"]
        if max(sx, sy) > 2.2 or sz > 2.3:
            continue
        out[re.sub(r"[^A-Za-z0-9_]", "_", k)] = dict(r, name0=k)
    for k, r in _ph_decor(split).items():  # L9 v2: Poly Haven floor pieces (render only), front (-y) to the robot
        sx, sy, sz = r["collider_size"]
        if r.get("kind") == "floor" and max(sx, sy) <= 2.2 and sz <= 2.3:
            out[k] = dict(r, yaw=-1.5707963)
    _CACHE[key] = out
    return out


MESH_TASK_CATS = ("table", "counter", "shelf", "side_table", "low_table", "seat")  # = scene9_more.MESH_RULES


def mesh_for(idx: int, n: int = 14, split: str = "train") -> dict:
    """The idx-th subset of mesh furniture pieces: one task-usable piece (with measured surfaces) per
    MESH_TASK_CATS category (L9 v2 mesh_furniture family), then n more rotating through the whole catalog (decor)."""
    from .scene9 import mesh_open_top as _open_top  # (import scene9 first: scene9_more is loaded by it)
    cat = furniture_mesh(split)
    out = {}
    for c in MESH_TASK_CATS:
        ks = sorted((k for k, r in cat.items() if r.get("category") == c and _open_top(r)),
                    key=lambda k: hashlib.sha256(f"l9mesh:{c}:{k}".encode()).hexdigest())
        if ks:
            out[ks[idx % len(ks)]] = cat[ks[idx % len(ks)]]
    order = sorted(cat, key=lambda k: hashlib.sha256(f"l9mesh:{k}".encode()).hexdigest())
    for j in range(n):
        k = order[(idx * n + j) % len(order)]
        out[k] = cat[k]
    return out


def gate_pass():
    """Targets that passed the L9 object gate (assets9/gate_targets.json "pass", tools/l9/ogate_tally.py), or None
    before the gate has run (then every catalog target is eligible)."""
    if "gate" not in _CACHE:
        p = os.path.join(DIR, "gate_targets.json")
        _CACHE["gate"] = set(json.load(open(p))["pass"]) if os.path.exists(p) else None
    return _CACHE["gate"]


# ----------------------------------------------------------------------------------------------- L9 v2 decor
TABLETOP_N = 8  # tabletop pieces per process (render-only mesh slots)


def _ph_decor(split: str) -> dict:
    """Render-only decor rows of a split, prim-safe names: Poly Haven (assets9/decor_ph.json, tools/l9v2env/
    ph_models.py; CC0) + Amazon Berkeley Objects (assets9/decor_abo.json, tools/l9v2env/abo_decor.py; CC BY 4.0)."""
    import re
    key = f"ph:{split}"
    if key not in _CACHE:
        rows = {}
        for fn in ("decor_ph.json", "decor_abo.json"):
            p = os.path.join(DIR, fn)
            if os.path.exists(p):
                rows.update(json.load(open(p, encoding="utf-8"))["assets"])
        _CACHE[key] = {re.sub(r"[^A-Za-z0-9_]", "_", k): dict(r, name0=k) for k, r in rows.items()
                       if r.get("split", "train") == split and licence_ok(r.get("license", ""))}
    return _CACHE[key]


def tabletop_decor(split: str = "train") -> dict:
    return {k: r for k, r in _ph_decor(split).items() if r.get("kind") == "tabletop"}


def tabletop_for(idx: int, n: int = TABLETOP_N, split: str = "train") -> dict:
    """The idx-th subset of n tabletop pieces (rotating through the pool)."""
    cat = tabletop_decor(split)
    if not cat:
        return {}
    order = sorted(cat, key=lambda k: hashlib.sha256(f"l9top:{k}".encode()).hexdigest())
    return {order[(idx * n + j) % len(order)]: cat[order[(idx * n + j) % len(order)]] for j in range(min(n, len(order)))}
