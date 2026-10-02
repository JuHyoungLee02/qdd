"""L9 v2 diagnosis: verify the proposed start-state escape for cuRobo transits on failed dumps (fail_*.json).
Proposed plan9.Planner9 additions (monkeypatched here, see l9tmp/v2/diag/1_start_collision.md):
  start_hits(q)            robot collision spheres of q vs the current world cuboids (+ activation distance)
  escape(q, T_tcp_base)    short straight TCP move (3 / 6 / 10 cm; up, back along the tool z, towards the base,
                           down, sideways) ending collision-free (start_hits == [])
  pose_escape(q, T, T0)    plan_pose; when it fails AND the start is in collision: escape, then plan from there
Usage (plain Isaac python + pylib): python -m tools.l9.diag.escape_check --profile P --arm A <fail.json> ...
For each dump: the runtime world (support below the goal fingers dropped), plan without / with the escape."""
from __future__ import annotations

import json
import os
import sys

import numpy as np

from harvest.l9 import curobo9 as C9
from harvest.l9 import plan9 as P9
from harvest.l9.grasp9 import qmat
from tools.l9.diag import transit_repro as TR

ACT = 0.012  # cuRobo activation distance (1 cm) + 2 mm margin


def _world(self, scene):
    self._scene = scene
    return _orig_world(self, scene)


def start_hits(self, q, act: float = ACT) -> list:
    st = self.mp.compute_kinematics(self._js(q))
    S = st.robot_spheres.reshape(-1, 4).cpu().numpy()
    S = S[S[:, 3] > 0]
    out = []
    for k, v in (getattr(self, "_scene", None) or {}).get("cuboid", {}).items():
        c, R, h = np.asarray(v["pose"][:3], float), qmat(v["pose"][3:]), np.asarray(v["dims"], float) / 2
        d = np.linalg.norm(np.maximum(np.abs((S[:, :3] - c) @ R) - h, 0.0), axis=1)
        pen = S[:, 3] + act - d
        if (pen > 0).any():
            out.append((k, round(float(pen.max()), 4)))
    return out


def tool_T(self, q) -> np.ndarray:
    st = self.mp.compute_kinematics(self._js(q))
    p = st.tool_poses.position.reshape(-1, 3)[0].cpu().numpy()
    qq = st.tool_poses.quaternion.reshape(-1, 4)[0].cpu().numpy()
    T = np.eye(4)
    T[:3, :3], T[:3, 3] = qmat(qq), p
    return T


def escape(self, q, T0=None, steps=(0.03, 0.06, 0.10)):
    """-> (N, dof) straight TCP move from q ending collision-free, or None."""
    T0 = tool_T(self, q) if T0 is None else np.asarray(T0, float)
    dirs = [np.array([0, 0, 1.0]), T0[:3, 2], np.array([-1.0, 0, 0]), np.array([0, 0, -1.0]),
            np.array([0, 1.0, 0]), np.array([0, -1.0, 0])]
    for s in steps:
        for d in dirs:
            T1 = T0.copy()
            T1[:3, 3] = T0[:3, 3] + s * d / np.linalg.norm(d)
            Q = self.line(q, T0, T1)
            if Q is not None and not start_hits(self, Q[-1]):
                return Q
    return None


def pose_escape(self, q, T_base, T0=None):
    Q = self.pose(q, T_base)
    if Q is not None:
        return Q, "direct"
    h = start_hits(self, q)
    if not h:
        return None, "fail (start clear)"
    E = escape(self, q, T0)
    if E is None:
        return None, f"fail (start hits {h}, no escape)"
    Q = self.pose(E[-1], T_base)
    if Q is None:
        return None, f"fail after escape ({len(E)} wp)"
    return np.concatenate([E, Q[1:]]), f"escape {np.round(tool_T(self, E[-1])[:3, 3] - tool_T(self, q)[:3, 3], 3).tolist()}"


_orig_world = P9.Planner9.world
P9.Planner9.world = _world


def main():
    a = sys.argv[1:]
    prof = a[a.index("--profile") + 1] if "--profile" in a else "franka_mast"
    arm = a[a.index("--arm") + 1] if "--arm" in a else "right"
    pl = P9.Planner9(C9.load_config(prof, arm))
    n_ok = n = 0
    for f in [x for x in a if x.endswith(".json")]:
        d = json.load(open(f))
        q = np.asarray(d["q"], float)
        Tb = np.asarray(d["T_world_base"], float)
        Tg_w = np.asarray(d["tcp_T"], float)
        Tg = P9.inv_T(Tb) @ Tg_w
        tip = Tg_w[:3, 3] - Tg_w[:3, 2] * 0.01
        low_w = min(tip[2] + s * 0.04 * Tg_w[2, 1] for s in (-1, 1))
        sc = {k: v for k, v in d["scene"]["cuboid"].items()
              if TR.world_top(Tb, v) > low_w - 0.02}
        pl.world({"cuboid": sc})
        Q, how = pose_escape(pl, q, Tg)
        n += 1
        n_ok += Q is not None
        ms = P9.max_step(Q) if Q is not None else None
        print(f"RESULT {os.path.basename(f)} {'OK' if Q is not None else 'FAIL'} {how} start_hits {start_hits(pl, q)} "
              f"max_step {ms}")
    print(f"SUMMARY {n_ok}/{n} plannable with the escape")


if __name__ == "__main__":
    main()
