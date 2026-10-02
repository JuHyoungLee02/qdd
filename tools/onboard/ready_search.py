"""(pod, cuRobo v0.8.0, outside the Isaac app) Ready-pose SEARCH: among a small candidate ladder of TCP heights
above the work surface, picks the LOWEST one that (a) cuRobo solves it (self-collision on, same call as
tools/l9/v2robot/ready_pose.py), (b) clears clutter -- TCP height above the surface >= a data-grounded threshold
(spec.clutter_height_p90(), the p90 object/container height already in assets9/objects_l9.json +
assets9/containers_l9.json -- not a guessed number), with `--margin` extra room, and (c) every solved arm joint stays
>= LIMIT_MARGIN (0.03 rad, build_curobo9.py's own convention) inside its limit.

Generalizes ready_pose.py (one human-picked xyz) + r1_posture.py (a hand grid search over the R1 Pro torso lean) into
one small search loop over the SAME cuRobo IK call; no new algorithm.

Onboarding tool (A), design doc docs/research/embodiment_onboarding_2026-10-03.md §4.1 step 6. Lesson: an early R1
Pro ready pose put the TCP about 9.4 cm above the surface -- barely above the MEDIAN L9 object height (0.09 m), so
it failed to clear most of a realistic clutter set. This script's criterion (b) is built to catch exactly that.

Height-above-surface, lean 0 only: the candidate z (torso/base-frame TCP target, same convention as ready_pose.py)
is given directly as the signed offset from the config base link to the TCP along world-up; the caller supplies the
base link's own height above the surface (`--base-above`, e.g. robot9.R1_T4_ABOVE for r1pro at lean 0, 0 for a flat
humanoid torso) so height_above_surface = base_above + z. For lean != 0 this script still finds an IK-feasible
candidate, but the caller must check height-above-surface from the real world pose instead (spawn_smoke9.py's
`tcp_above_surface_m`, which measures it in the sim, not from this formula).

usage: ready_search.py <profile> <arm> <out.json> <x> <y> <z-candidates csv, surface-relative, e.g. -0.30,-0.25,-0.20>
       [--base-above 0.0] [--clutter 0.22] [--margin-m 0.03] [--yaw 1.5708] [--lean 0.0] [--limit-margin 0.03]
"""
from __future__ import annotations

import argparse
import json
import math
import os

import numpy as np
import torch

from harvest.l9 import curobo9 as C
from curobo.types import GoalToolPose, Pose


def qmul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return [w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2]


def solve_one(profile: str, arm: str, x: float, y: float, z: float, yaw: float, lean: float) -> dict:
    """Same IK call as ready_pose.py (self-collision on, top-down yaw at the given base lean): -> ok, pos_err_mm,
    joint values + their distance to the sim limits."""
    t = [x, y, z]
    yw = yaw
    if arm == "left":
        t[1], yw = -t[1], -yaw
    q = qmul([math.cos(-lean / 2), 0, math.sin(-lean / 2), 0], [math.cos(yw / 2), 0, 0, math.sin(yw / 2)])
    ik = C.make_ik(profile, arm, num_seeds=64, max_batch_size=1)
    tf = C.tool_frame(profile, arm)
    r = ik.solve_pose(GoalToolPose.from_poses({tf: Pose(position=torch.tensor([t], device="cuda", dtype=torch.float32),
                                                          quaternion=torch.tensor([q], device="cuda", dtype=torch.float32))},
                                              num_goalset=1))
    ok = bool(r.success.view(-1)[0])
    names = list(r.js_solution.joint_names)
    sol = r.js_solution.position.view(1, -1)[0].tolist()
    arm_q = {j: sol[names.index(j)] for j in C.arm_joints(profile, arm)}
    return {"ok": ok, "pos_err_mm": round(float(r.position_error.view(-1)[0]) * 1e3, 3), "q": arm_q, "target": t,
           "quat": q, "yaw": yw, "lean": lean}


def joint_margin(profile: str, arm: str, q: dict, limit_margin: float) -> tuple:
    """-> (ok, worst_mrad_inside_limit, worst_joint). Reuses the sim/URDF limits via urdf_fk like verify_limits.py."""
    sys_path_added = False
    import os
    import sys as _sys
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "l9", "v2robot")
    if p not in _sys.path:
        _sys.path.insert(0, p)
        sys_path_added = True
    from urdf_fk import Urdf
    u = Urdf(C.load_config(profile, arm)["robot_cfg"]["kinematics"]["urdf_path"])
    worst, worst_j = -1e9, None
    for j, v in q.items():
        lo, hi = u.joints[j]["lower"], u.joints[j]["upper"]
        room = min(v - lo, hi - v) - limit_margin
        if room > worst:
            worst, worst_j = room, j
    return worst >= 0.0, worst, worst_j


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("profile")
    ap.add_argument("arm")
    ap.add_argument("out")
    ap.add_argument("x", type=float)
    ap.add_argument("y", type=float)
    ap.add_argument("--z", dest="z_candidates", required=True,
                    help="comma-separated, surface-relative z offsets (may be negative), ascending order tried first")
    ap.add_argument("--base-above", type=float, default=0.0, help="config base link height above the surface (m)")
    ap.add_argument("--clutter", type=float, default=None, help="override the clutter height threshold (m)")
    ap.add_argument("--margin-m", type=float, default=0.03, help="extra clearance above the clutter threshold (m)")
    ap.add_argument("--yaw", type=float, default=1.5708)
    ap.add_argument("--lean", type=float, default=0.0)
    ap.add_argument("--limit-margin", type=float, default=0.03)
    a = ap.parse_args()

    if a.clutter is not None:
        clutter = a.clutter
    else:
        import importlib.util
        here = os.path.dirname(os.path.abspath(__file__))
        spec_mod = importlib.util.spec_from_file_location("onboard_spec", os.path.join(here, "spec.py"))
        SPEC = importlib.util.module_from_spec(spec_mod)
        spec_mod.loader.exec_module(SPEC)
        clutter = SPEC.clutter_height_p90()

    zs = sorted(float(v) for v in a.z_candidates.split(","))
    trials, chosen = [], None
    for z in zs:
        height_above_surface = a.base_above + z
        sol = solve_one(a.profile, a.arm, a.x, a.y, z, a.yaw, a.lean)
        clears = height_above_surface >= clutter + a.margin_m
        lim_ok, worst_room, worst_j = joint_margin(a.profile, a.arm, sol["q"], a.limit_margin)
        trial = {**sol, "z_surface_relative": z, "height_above_surface_m": round(height_above_surface, 4),
                 "clears_clutter": clears, "clutter_threshold_m": round(clutter, 4),
                 "limit_margin_ok": lim_ok, "worst_joint_room_rad": round(worst_room, 4), "worst_joint": worst_j}
        trials.append(trial)
        if chosen is None and sol["ok"] and sol["pos_err_mm"] < 5.0 and clears and lim_ok:
            chosen = trial
    out = {"profile": a.profile, "arm": a.arm, "clutter_threshold_m": round(clutter, 4), "trials": trials,
          "chosen": chosen, "pass": chosen is not None}
    print(json.dumps(out, indent=1))
    json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
