"""Onboarding tool (A) spec glue (pure, no GPU). Design doc docs/research/embodiment_onboarding_2026-10-03.md §4.1.

A new robot's input is the SAME small dict shape tools/l9/v2robot/robots_v2.ROBOTS[robot] already uses (URDF path,
base link, per-arm joints/fingers/parent/approach/tcp_rule) -- onboarding a robot is editing one such dict entry (as
GR00T's NEW_EMBODIMENT + modality.json does: a short declarative mapping a human writes once, the rest is code), not
a new format. This module does NOT re-author that schema; it (a) validates an entry is complete enough to run the
chain, and (b) gives the ready-pose clutter-clearance threshold a real, data-grounded number instead of a guess.
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
L9_ASSETS = os.path.join(HERE, "..", "..", "harvest", "l9", "assets9")

REQUIRED_ARM_KEYS = ("joints", "parent", "approach", "fingers")


def validate(robots_dict: dict, robot: str) -> list:
    """-> list of problem strings (empty = OK). Checks the robots_v2.ROBOTS[robot] entry has what build_curobo9.py /
    width_table.py / ready_search.py need, before spending GPU time on it."""
    problems = []
    if robot not in robots_dict:
        return [f"{robot!r} not in the robots dict"]
    s = robots_dict[robot]
    for k in ("src_dir", "src_urdf", "base", "arms", "tcp_rule"):
        if k not in s:
            problems.append(f"{robot}: missing {k!r}")
    for arm, a in s.get("arms", {}).items():
        for k in REQUIRED_ARM_KEYS:
            if k not in a:
                problems.append(f"{robot}.{arm}: missing {k!r}")
        if "joints" in a and len(a["joints"]) == 0:
            problems.append(f"{robot}.{arm}: no joints")
        if "fingers" in a and len(a["fingers"]) < 2:
            problems.append(f"{robot}.{arm}: fewer than 2 finger links ({a.get('fingers')}) -- width_table needs "
                            f"at least a pinch pair")
    return problems


def _heights(fn: str, key: str) -> list:
    d = json.load(open(fn))
    items = d.get(key) or {}
    if isinstance(items, dict):
        items = items.items()
    out = []
    for _, v in items:
        h = v.get("height")
        if isinstance(h, (int, float)):
            out.append(float(h))
    return out


def clutter_height_p90(p: float = 0.90) -> float:
    """p-th percentile object/container height (m) actually used in the L9 asset catalogue (assets9/objects_l9.json
    + assets9/containers_l9.json) -- the data-grounded "typical clutter height" a ready pose must clear, in place of
    a guessed number. n ~= 9000 items (2026-10-03): p50 0.09 m, p90 0.22 m, p95 0.267 m, max 0.35 m -- the design
    doc's "9.4 cm was too low" R1 Pro lesson is the MEDIAN height, which is why it failed on most real clutter."""
    hs = sorted(_heights(os.path.join(L9_ASSETS, "objects_l9.json"), "objects")
               + _heights(os.path.join(L9_ASSETS, "containers_l9.json"), "containers"))
    if not hs:
        raise RuntimeError("no object/container heights found -- check L9_ASSETS path")
    i = min(len(hs) - 1, int(p * len(hs)))
    return hs[i]


if __name__ == "__main__":
    import sys

    sys.path.insert(0, os.path.join(HERE, "..", "l9", "v2robot"))
    import robots_v2 as RV

    for r in sorted(RV.ROBOTS):
        probs = validate(RV.ROBOTS, r)
        print(r, "OK" if not probs else probs)
    print("clutter_height_p90 =", round(clutter_height_p90(), 4), "m")
