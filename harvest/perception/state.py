"""Estimated M1 state (R1): per-object centroids from vision + gripper from proprioception -> predicates, the
ser-A-min S0 text (serialize_state) and the S1 geometry block (e3lite format, step_cm = 0.1, labels_v2 §54) with occluded /
id_uncertain flags.

What vision does NOT give here, and what stands in for it (stated in r1_perception.md):
- object size: the catalog half extents of the object table (stand-in for the M2 contract / object model);
- object orientation: not estimated (no FoundationPose step) -> identity quaternion, so upright(o) = true;
- contacts: geometric (gripper: object centre within the object's half-diagonal |he| of the fingertip midpoint;
  object-object: a's bottom within STACK_GAP_M of b's top and a's centre over b's footprint) instead of the sim
  contact sensors. (v1 used a fixed 4 cm: the grasped mug centre sits 4.1-4.3 cm from the fingertip midpoint, so
  holding(o3) was never true -- found by the truth-position control, r1_perception.md §3 post-hoc 1);
- gripper position / width / effort: proprioception (joint states + FK; in the sim the link poses are that FK).
"""
from __future__ import annotations

import copy
import itertools
import re

import numpy as np

from ..e3lite import geometry_block
from ..predicates import Gripper, Obj, PredicateState
from ..sim.oracle_state import support_from_contacts
from ..sim.planner import PHASE_TIMEOUT_S
from ..sim.snapshot import text_state

STACK_GAP_M = 0.01
TABLE_TOL_EST_M = 0.015  # vs 4 mm with sim truth: centroid z noise
STEP_CM = 0.1
_IDQ = np.array([1.0, 0.0, 0.0, 0.0])


def estimate_contacts(pos: dict, he: dict, grip_pos) -> set:
    g = np.asarray(grip_pos, float)
    out = set()
    for k, p in pos.items():
        if float(np.linalg.norm(np.asarray(p) - g)) <= float(np.linalg.norm(he[k])):
            out.add(frozenset({"gripper", k}))
    for a, b in itertools.permutations(pos, 2):
        pa, pb, ha, hb = np.asarray(pos[a]), np.asarray(pos[b]), he[a], he[b]
        over = abs(pa[0] - pb[0]) <= hb[0] and abs(pa[1] - pb[1]) <= hb[1]
        if over and pa[2] > pb[2] and abs((pa[2] - ha[2]) - (pb[2] + hb[2])) <= STACK_GAP_M:
            out.add(frozenset({a, b}))
    return out


def estimate_predicates(est: dict, grip: dict, he: dict, ps: PredicateState | None = None):
    """est: {obj: {pos (table frame) or None, occluded, id_uncertain}}; grip: proprioception {w, effort, pos}.
    Returns (pred, support, contacts). ps carries the near() hysteresis across frames of one episode."""
    seen = {k: np.asarray(e["pos"], float) for k, e in est.items() if e.get("pos") is not None}
    objs = {k: Obj(id=k, pos=seen[k], quat_wxyz=_IDQ, half_extents=np.asarray(he[k], float),
                   occluded=bool(est[k].get("occluded")), id_uncertain=bool(est[k].get("id_uncertain")))
            for k in seen}
    g = Gripper(width_m=float(grip["w"]), effort=float(grip["effort"]), pos=np.asarray(grip["pos"], float))
    contacts = estimate_contacts(seen, he, g.pos)
    support = support_from_contacts(seen, {k: he[k][2] for k in seen}, contacts, table_tol=TABLE_TOL_EST_M)
    pred = (ps or PredicateState()).update(objs, g, contacts, support)
    for k in est:
        if k not in seen:  # never seen in this episode: every predicate on it is unknown
            for p in ("holding", "upright", "lifted"):
                pred[f"{p}({k})"] = None
            for j in est:
                if j != k:
                    for p in ("near", "on", "above", "in_contact"):
                        pred[f"{p}({k},{j})"] = pred[f"{p}({j},{k})"] = None
    return pred, support, contacts


def est_line(line: dict, est: dict, ps: PredicateState | None = None) -> dict:
    """A copy of a snapshot line whose observation is the estimate: obs.raw object positions, pred, text_state.
    Objects never seen are dropped from `present` (the geometry block has no line for them)."""
    st = line["state"]
    raw = st["obs"]["raw"]
    he = {k: raw["objs"][k]["he"] for k in st["present"]}
    pred, support, contacts = estimate_predicates({k: est[k] for k in st["present"]}, raw["grip"], he, ps)
    out = {k: v for k, v in line.items() if k not in ("state", "pred", "text_state")}
    s = copy.deepcopy(st)
    s["present"] = [k for k in st["present"] if est[k].get("pos") is not None]
    for k in s["present"]:
        s["obs"]["raw"]["objs"][k]["pos"] = [float(v) for v in est[k]["pos"]]
        s["obs"]["raw"]["objs"][k]["quat"] = _IDQ.tolist()
    s["obs"]["pred"] = pred
    s["obs"]["raw"]["contacts"] = [sorted(c) for c in contacts]
    s["obs"]["raw"]["support"] = support
    s["est_flags"] = {k: {"occluded": bool(est[k].get("occluded")), "id_uncertain": bool(est[k].get("id_uncertain")),
                          "source": est[k].get("source")} for k in st["present"]}
    t, phase = float(line["t"]), line["phase"]
    moving = bool(re.search(r"arm=moving", line["text_state"]))
    t_in = t - float((st.get("planner") or {}).get("t_phase0", t))
    txt = text_state(t, phase, t_in, PHASE_TIMEOUT_S.get(phase, 60.0), pred, st["present"], support,
                     bool(pred.get("gripper_open")), bool(pred.get("holding(o3)")), moving, [])
    out.update(state=s, pred=pred, text_state=txt)
    return out


def geometry_block_flags(line: dict, step_cm: float = STEP_CM) -> str:
    """e3lite.geometry_block (same format) with ' occluded' / ' id_uncertain' appended to flagged object lines."""
    flags = line["state"].get("est_flags", {})
    out = []
    for ln in geometry_block(line["state"], step_cm=step_cm).split("\n"):
        m = re.match(r"^  (o\d+) ", ln)
        if m and m.group(1) in flags:
            f = flags[m.group(1)]
            ln += "".join(f" {n}" for n in ("occluded", "id_uncertain") if f.get(n))
        out.append(ln)
    return "\n".join(out)


def s1_text(line: dict, step_cm: float = STEP_CM) -> str:
    return line["text_state"] + "\n" + geometry_block_flags(line, step_cm)
