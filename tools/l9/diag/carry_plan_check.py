"""L9 v2 diagnosis: does cuRobo's trajectory swing the hand during carry moves, and does a non-terminal orientation
criterion fix it? Offline replay of run9_trace segments (plain Isaac python + pylib).
usage: python -m tools.l9.diag.carry_plan_check --profile P --arm A <trace.jsonl>[:i0-i1] ... [--w 1.0]
For each trace segment of truth step carry_over / carry_up (or the given sample range): start joints = first sample's q,
goal = last sample's TCP pose (base frame from the first sample: T_world_base = T_tcp_world @ inv(FK(q))), empty world.
Plans (a) default, (b) ToolPoseCriteria non_terminal_pose_axes_weight_factor = [0, 0, 0, w, w, w]; prints the largest
TCP rotation away from the straight slerp start -> goal along each plan (deg) and the plan length."""
from __future__ import annotations

import json
import math
import sys

import numpy as np

from harvest.l9 import curobo9 as C9
from harvest.l9 import plan9 as P9
from harvest.l9.grasp9 import qmat


def T_of(p, q):
    T = np.eye(4)
    T[:3, :3], T[:3, 3] = qmat(q), np.asarray(p, float)
    return T


def rot_deg(R1, R2) -> float:
    c = (np.trace(R1.T @ R2) - 1) / 2
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def swing(pl, Q, R0, R1) -> float:
    """Largest excess rotation along the plan: max over waypoints of (angle(R0, R) + angle(R, R1) - angle(R0, R1)) / 2."""
    base = rot_deg(R0, R1)
    out = 0.0
    for q in Q[:: max(1, len(Q) // 40)]:
        R = pl.tool_T(q)[:3, :3] if hasattr(pl, "tool_T") else None
        if R is None:
            return float("nan")
        out = max(out, (rot_deg(R0, R) + rot_deg(R, R1) - base) / 2)
    return out


def main():
    a = sys.argv[1:]
    prof = a[a.index("--profile") + 1] if "--profile" in a else "franka_mast"
    arm = a[a.index("--arm") + 1] if "--arm" in a else "right"
    w = float(a[a.index("--w") + 1]) if "--w" in a else 1.0
    pl = P9.Planner9(C9.load_config(prof, arm))
    from curobo._src.cost.tool_pose_criteria import ToolPoseCriteria
    tool = pl.mp.tool_frames[0]
    for spec in [x for x in a if ".jsonl" in x]:
        f, rng = (spec.split(":") + [None])[:2]
        rows = [json.loads(l) for l in open(f)]
        rows = [r for r in rows if "tq" in r and "q" in r]
        segs = []
        if rng:
            i0, i1 = (int(v) for v in rng.split("-"))
            segs.append([r for r in rows if i0 <= r["i"] <= i1])
        else:
            cur = []
            for r in rows + [{"step": None}]:
                if cur and r.get("step") != cur[0]["step"]:
                    if cur[0]["step"] in ("carry_over",) and len(cur) > 3:
                        segs.append(cur)
                    cur = []
                if r.get("step") is not None:
                    cur.append(r)
        for s in segs:
            q0 = np.asarray(s[0]["q"], float)
            Tw0 = T_of(s[0]["tcp"], s[0]["tq"])
            Tb = Tw0 @ P9.inv_T(pl.tool_T(q0))
            Tg = P9.inv_T(Tb) @ T_of(s[-1]["tcp"], s[-1]["tq"])
            R0, R1 = pl.tool_T(q0)[:3, :3], Tg[:3, :3]
            pl.world({"cuboid": {}})
            pl.mp.update_tool_pose_criteria({tool: ToolPoseCriteria()})
            Qa = pl.pose(q0, Tg)
            pl.mp.update_tool_pose_criteria({tool: ToolPoseCriteria(non_terminal_pose_axes_weight_factor=[0, 0, 0, w, w, w])})
            Qb = pl.pose(q0, Tg)
            pl.mp.update_tool_pose_criteria({tool: ToolPoseCriteria()})
            fa = "FAIL" if Qa is None else f"swing {swing(pl, Qa, R0, R1):5.1f} deg n {len(Qa)}"
            fb = "FAIL" if Qb is None else f"swing {swing(pl, Qb, R0, R1):5.1f} deg n {len(Qb)}"
            print(f"{f.rsplit('/', 1)[-1]} i {s[0]['i']}-{s[-1]['i']} rot start->goal {rot_deg(R0, R1):5.1f} | "
                  f"executed max dev {max(rot_deg(qmat(s[0]['tq']), qmat(r['tq'])) for r in s):5.1f} | default {fa} | "
                  f"criteria w={w} {fb}")


if __name__ == "__main__":
    main()
