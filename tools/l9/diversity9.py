"""Layout diversity gate per definition x robot (pure; user 10-02: robot-object placement must differ every episode,
even within one task). For gate-passing episodes (or all with --all): the first target's x, y, yaw in the robot frame
(scene.json layout; v2 robots minus their root x) and the robot pose (distance to the furniture front, yaw) ->
std and IQR of x, y, distance; circular std of the target yaw and of the robot yaw; distinct (robot pose, full layout)
combos and duplicates (must be 0). Prints per-robot medians over definitions with n >= --min-n, plus the reference
root when given (--ref, e.g. the v1 production) for comparison.
usage: python tools/l9/diversity9.py <collect root>... [--ref <collect root>] [--all] [--min-n 5] [--json out.json]"""
import glob
import json
import math
import os
import sys
from collections import defaultdict

import numpy as np

BASE_X = {"r1pro": -0.05, "g1": -0.02}  # robot9.V2_BASE_X at the time of the episode (constant root x)


def circ_std(a):
    a = np.asarray(a, float)
    if len(a) < 2:
        return 0.0
    r = math.hypot(np.mean(np.cos(a)), np.mean(np.sin(a)))
    return float(math.sqrt(max(0.0, -2.0 * math.log(max(r, 1e-12)))))


def iqr(a):
    q = np.percentile(np.asarray(a, float), [25, 75])
    return float(q[1] - q[0])


def episode_combo(d, meta):
    """(robot, task_id, vec, combo) of one episode directory (meta already loaded, as the caller has it from its
    own meta.json read) -- the per-file body of episodes() below, factored out so a per-episode caller (qmon9.py,
    the pod-side quality monitor: owner order 10-03) can reuse it without re-globbing a whole root. None when
    scene.json / episode9.json / labels.jsonl / the target's layout entry is missing."""
    try:
        sc = json.load(open(os.path.join(d, "scene.json")))
        ep = json.load(open(os.path.join(d, "episode9.json")))
        row0 = json.loads(open(os.path.join(d, "labels.jsonl")).readline())
    except (OSError, ValueError):
        return None
    robot = meta.get("robot") or "ffw_sg2"
    lay = sc.get("layout") or {}
    tg = row0.get("tgt")
    if tg not in lay:
        return None
    rp = (ep.get("scene") or {}).get("robot_pose") or meta.get("robot_pose") or {}
    bx = BASE_X.get(robot, 0.0)
    x, y, yaw = lay[tg][:3]  # some layouts carry extra fields (z, tilt) after yaw
    combo = (round(float(rp.get("distance", 0)), 3), round(float(rp.get("yaw", 0)), 3),
             tuple(sorted((k,) + tuple(round(x_, 3) if isinstance(x_, (int, float)) else str(x_) for x_ in v)
                          for k, v in lay.items())))
    return robot, meta.get("task_id"), (x - bx, y, yaw, float(rp.get("distance", np.nan)),
                                        float(rp.get("yaw", np.nan))), combo


def episodes(root, every):
    for m in glob.glob(os.path.join(root, "*", "*", "*", "meta.json")):
        d = os.path.dirname(m)
        try:
            meta = json.load(open(m))
        except (OSError, ValueError):
            continue
        ok = bool(meta.get("success")) and (meta.get("max_dq_rad") or 0) <= 0.04
        if not (ok or every):
            continue
        r = episode_combo(d, meta)
        if r is not None:
            yield r


def summarise(roots, every, min_n):
    cells = defaultdict(list)
    combos = defaultdict(list)
    for root in roots:
        for robot, task, v, combo in episodes(root, every):
            cells[(robot, task)].append(v)
            combos[(robot, task)].append(combo)
    per_cell = {}
    for k, vs in cells.items():
        A = np.array(vs, float)
        per_cell[k] = {"n": len(vs), "std_x": float(np.std(A[:, 0])), "std_y": float(np.std(A[:, 1])),
                       "iqr_x": iqr(A[:, 0]), "iqr_y": iqr(A[:, 1]), "cstd_yaw": circ_std(A[:, 2]),
                       "std_dist": float(np.nanstd(A[:, 3])), "cstd_robot_yaw": circ_std(A[~np.isnan(A[:, 4]), 4]),
                       "distinct": len(set(combos[k])), "dups": len(combos[k]) - len(set(combos[k]))}
    robots = defaultdict(list)
    for (robot, task), c in per_cell.items():
        robots[robot].append(c)
    out = {}
    for robot, cs in robots.items():
        big = [c for c in cs if c["n"] >= min_n]
        med = (lambda key: round(float(np.median([c[key] for c in big])), 3) if big else None)  # noqa: E731
        out[robot] = {"cells": len(cs), "cells_n>=min": len(big), "episodes": sum(c["n"] for c in cs),
                      "dups_total": sum(c["dups"] for c in cs),
                      "median": {k: med(k) for k in ("std_x", "std_y", "iqr_x", "iqr_y", "cstd_yaw", "std_dist",
                                                       "cstd_robot_yaw")}}
    return out, per_cell


def main():
    a = sys.argv[1:]
    arg = lambda k, d: type(d)(a[a.index(k) + 1]) if k in a else d  # noqa: E731
    flags = {"--ref", "--min-n", "--json"}
    roots = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or a[i - 1] not in flags)]
    every, min_n = "--all" in a, arg("--min-n", 5)
    res = {"l9v2": summarise(roots, every, min_n)[0]}
    if "--ref" in a:
        res["reference"] = summarise([arg("--ref", "")], every, min_n)[0]
    print(json.dumps(res, indent=1))
    if "--json" in a:
        json.dump(res, open(arg("--json", ""), "w"), indent=1)


if __name__ == "__main__":
    main()
