"""L9 per-robot environment profile reader (user order 10-03 03시, "로봇 키·도달에 맞춘 가구·자리 배치"; audit rows
1, 5, 9, 10, 12, 16, 17, 22). Pure. Robots differ ONLY by these measured data; the draw code is the same for all.

File: harvest/l9/assets9/env_profiles/<profile>.json, schema "l9-env-profile-v1" (written by tools/onboard/autotune
from the robot's own reach map (cuRobo IK grid) + its own camera + its body / lift joint ranges; ranges only):
  {"schema": "l9-env-profile-v1", "profile": ..., "source": {"tool", "sha", "date"},
   "body": {"joints": {joint: [lo, hi]}, "lean_rad": [lo, hi], "mount_above_surface_m": [lo, hi]},
   "surface_z_m": [lo, hi], "stance_x_m": [lo, hi],          # root x from the work surface's front edge
   "hand": {"yaw_deg_ok": [lo, hi] | [[lo, hi], ...], "yaw_deg_bad": [...], "tilt_deg": [lo, hi]},
   "ready": {"tcp_above_surface_m": [lo, hi]}, "lift_clear_m": [lo, hi], "carry_clear_m": [lo, hi],
   "head_cam": {"pitch_deg": [lo, hi]},
   "cells": [{"surface_z", "stance_x", "lean", "mount_above", "torso": {j: v}, "lift": {j: v}, "score"}, ...],
   "cell_half": {field: half width},                        # optional: jitter inside a cell
   "stats": {"feasible_frac", "n_cells"},
   optional: "lateral_m": [lo, hi] | {"right": [..], "left": [..]}, "reach_map": path, "scene_model": "mod:Class"}
draw(): one stance per EPISODE (body / lift / surface fixed for the whole episode, never planned or moved during it;
L9_PRINCIPLES (6) as corrected 10-03 03시): a uniform cell when cells exist (surface height and torso posture are
coupled -- independent marginals give infeasible pairs), jittered by +-cell_half, else every range independently.
Consumers opt in with L9_ENV_PROFILE=1 (default off: no profile is read)."""
from __future__ import annotations

import json
import os

import numpy as np

SCHEMA = "l9-env-profile-v1"
DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets9", "env_profiles")
RANGE_KEYS = ("surface_z_m", "stance_x_m", "lift_clear_m", "carry_clear_m")
_CACHE: dict = {}


def enabled() -> bool:
    return os.environ.get("L9_ENV_PROFILE") == "1"


def _is_range(v) -> bool:
    return isinstance(v, (list, tuple)) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v) and v[0] <= v[1]


def _ranges(v) -> list:
    """[lo, hi] or [[lo, hi], ...] -> list of ranges; a flat list of > 2 numbers is a grid of sampled values (each
    covers +- half the smallest grid step)."""
    if _is_range(v):
        return [list(v)]
    if isinstance(v, (list, tuple)) and len(v) > 2 and all(isinstance(x, (int, float)) for x in v):
        s = sorted(float(x) for x in v)
        h = min((b - a for a, b in zip(s, s[1:]) if b > a), default=1.0) / 2
        return [[x - h, x + h] for x in s]
    return [list(r) for r in v]


def validate(p: dict) -> list:
    """Schema problems (empty = valid)."""
    bad = []
    if p.get("schema") != SCHEMA:
        bad.append(f"schema {p.get('schema')!r} != {SCHEMA!r}")
    if not p.get("profile"):
        bad.append("no profile")
    for k in RANGE_KEYS:
        if k in p and not _is_range(p[k]):
            bad.append(f"{k} is not a [lo, hi] range")
    body = p.get("body", {})
    for k in ("lean_rad", "mount_above_surface_m"):
        if k in body and not _is_range(body[k]):
            bad.append(f"body.{k} is not a [lo, hi] range")
    for j, r in body.get("joints", {}).items():
        if not _is_range(r):
            bad.append(f"body.joints.{j} is not a [lo, hi] range")
    for k in ("yaw_deg_ok", "yaw_deg_bad"):
        if k in p.get("hand", {}):
            try:
                if not all(_is_range(r) for r in _ranges(p["hand"][k])):
                    raise ValueError
            except (TypeError, ValueError):
                bad.append(f"hand.{k} is not a range or a list of ranges")
    for i, c in enumerate(p.get("cells", [])[:1000]):
        if not isinstance(c, dict):
            bad.append(f"cells[{i}] is not an object")
            break
    if "cells" in p and not p["cells"]:
        bad.append("cells is empty (no feasible stance)")
    return bad


def load(profile: str, path: str | None = None) -> dict | None:
    """The robot's profile (None when it has none). ValueError on a schema problem."""
    path = path or os.path.join(DIR, f"{profile}.json")
    if path not in _CACHE:
        if not os.path.exists(path):
            _CACHE[path] = None
        else:
            p = json.load(open(path, encoding="utf-8"))
            bad = validate(p)
            if bad:
                raise ValueError(f"{path}: {bad}")
            _CACHE[path] = p
    return _CACHE[path]


def active(profile: str) -> dict | None:
    return load(profile) if enabled() else None


def _u(rng, r) -> float:
    return float(rng.uniform(r[0], r[1]))


def draw(p: dict, seed: int, near: dict | None = None) -> dict | None:
    """One episode's stance from profile p (deterministic in seed). near ({"surface_z": z}, world9 consumer): only the
    cells within cell_half (default 0.025) of those values -- the scene's actual surface picks the coupled body
    posture; the nested body joints are then used exactly (no jitter: it would undo the surface coupling); None when
    no cell matches."""
    rng = np.random.default_rng(int(seed) & 0xFFFFFFFF)
    out = {"torso": {}, "lift": {}}
    cells = p.get("cells") or []
    half = p.get("cell_half", {})
    if cells and near:
        cells = [c for c in cells if all(k in c and abs(float(c[k]) - float(v)) <= float(half.get(k, 0.025)) + 1e-9
                                         for k, v in near.items())]
        if not cells:
            return None
    if cells:
        c = cells[int(rng.integers(len(cells)))]
        for k, v in c.items():
            if k == "score":
                continue
            if isinstance(v, dict):
                out.setdefault(k, {})
                for j, x in v.items():
                    h = 0.0 if near else float(half.get(f"{k}.{j}", 0.0))  # nested fields: "torso.<joint>"
                    out[k][j] = float(x) + (float(rng.uniform(-h, h)) if h else 0.0)
            else:
                h = float(half.get(k, 0.0))
                out[k] = float(v) + (float(rng.uniform(-h, h)) if h else 0.0)
    else:
        if "surface_z_m" in p:
            out["surface_z"] = _u(rng, p["surface_z_m"])
        if "stance_x_m" in p:
            out["stance_x"] = _u(rng, p["stance_x_m"])
        body = p.get("body", {})
        if "lean_rad" in body:
            out["lean"] = _u(rng, body["lean_rad"])
        if "mount_above_surface_m" in body:
            out["mount_above"] = _u(rng, body["mount_above_surface_m"])
        for j, r in body.get("joints", {}).items():
            out["torso"][j] = _u(rng, r)
    for k, name in (("lift_clear_m", "lift_clear"), ("carry_clear_m", "carry_clear")):
        if k in p:
            out[name] = _u(rng, p[k])
    if "tcp_above_surface_m" in p.get("ready", {}):
        out["ready_tcp_above"] = _u(rng, p["ready"]["tcp_above_surface_m"])
    if "pitch_deg" in p.get("head_cam", {}):
        out["head_pitch_deg"] = _u(rng, p["head_cam"]["pitch_deg"])
    return out


def yaw_ok(p: dict, yaw_deg: float) -> bool:
    """Is a hand yaw (deg, closing axis about world z) inside the profile's good set (and outside its bad set)?"""
    h = p.get("hand", {})
    y = float(yaw_deg)
    if "yaw_deg_bad" in h and any(r[0] <= y <= r[1] for r in _ranges(h["yaw_deg_bad"])):
        return False
    if "yaw_deg_ok" in h:
        return any(r[0] <= y <= r[1] for r in _ranges(h["yaw_deg_ok"]))
    return True


def lateral_range(p: dict, arm: str) -> list | None:
    v = p.get("lateral_m")
    if v is None:
        return None
    return list(v[arm]) if isinstance(v, dict) else list(v)
