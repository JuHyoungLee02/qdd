"""Auxiliary geometry labels from the sim's privileged state (canon §58: the fused model's auxiliary geometry head).

Input = a snapshot line's `state` (obs.raw in the table frame: x/y = robot base x/y, z = height above the table
top; obs.pred = the truth T1 predicates). Output = per object the offset object centre - gripper fingertip midpoint
and its length, per object pair the offset a - b, and the predicate values. Pure; no Isaac.

aux_vector gives a fixed-order float vector + mask (1 = label defined) for a regression / BCE head: absent objects
and unknown (None) predicates are masked out, never filled with a guess.
"""
from __future__ import annotations

import numpy as np

AUX_OBJS = ("o3", "o5")
AUX_PAIRS = (("o3", "o5"),)
AUX_PREDS = ("gripper_open", "holding(o3)", "lifted(o3)", "upright(o3)", "upright(o5)", "near(o3,o5)",
             "above(o3,o5)", "in_contact(o3,o5)", "on(o3,o5)")
_GEO = ("dx", "dy", "dz", "dist")


def _geo(d) -> dict:
    d = np.asarray(d, float)
    return {"delta_m": [float(v) for v in d], "dist_m": float(np.linalg.norm(d))}


def aux_labels(state: dict, pairs=AUX_PAIRS) -> dict:
    raw = state["obs"]["raw"]
    g = np.asarray(raw["grip"]["pos"], float)
    pos = {k: np.asarray(raw["objs"][k]["pos"], float) for k in state["present"] if k in raw["objs"]}
    return {"gripper": {"pos_m": [float(v) for v in g], "width_m": raw["grip"].get("w")},
            "objects": {k: _geo(p - g) for k, p in pos.items()},
            "pairs": {f"{a}-{b}": _geo(pos[a] - pos[b]) for a, b in pairs if a in pos and b in pos},
            "pred": dict(state["obs"].get("pred") or {})}


def aux_names(objs=AUX_OBJS, pairs=AUX_PAIRS, preds=AUX_PREDS) -> list[str]:
    return ([f"{k}.{c}" for k in objs for c in _GEO] + [f"{a}-{b}.{c}" for a, b in pairs for c in _GEO]
            + [f"pred.{p}" for p in preds])


def aux_vector(state: dict, objs=AUX_OBJS, pairs=AUX_PAIRS, preds=AUX_PREDS):
    """(values float32, mask float32) in aux_names order; metres for geometry, 0/1 for predicates."""
    a = aux_labels(state, pairs)
    v, m = [], []

    def put(geo):
        if geo is None:
            v.extend([0.0] * 4)
            m.extend([0.0] * 4)
        else:
            v.extend([*geo["delta_m"], geo["dist_m"]])
            m.extend([1.0] * 4)

    for k in objs:
        put(a["objects"].get(k))
    for x, y in pairs:
        put(a["pairs"].get(f"{x}-{y}"))
    for p in preds:
        val = a["pred"].get(p)
        v.append(0.0 if val is None else float(bool(val)))
        m.append(0.0 if val is None else 1.0)
    return np.asarray(v, np.float32), np.asarray(m, np.float32)
