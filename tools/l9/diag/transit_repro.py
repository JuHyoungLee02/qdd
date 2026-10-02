"""L9 v2 diagnosis: replay failed transit dumps (rt9._dump_fail, L9V2_DEBUG_DIR/fail_*.json) with cuRobo 0.8.0 and
find WHY the pre-grasp transit failed although the pre-grasp IK passed in rt9._valid.
Plain Isaac python + /data/harvest/l9v2/pylib (PYTHONPATH=<code dir>:<pylib>), e.g.
  /isaac-sim/python.sh -m tools.l9.diag.transit_repro --profile franka_mast --arm right <fail.json> [<fail.json> ...]
Per dump and world variant (the dump holds EVERY cuboid; the runtime drops the support below the target for transits):
  ik(goal) with contact links on / off, plan_pose success, start-state world hits (robot collision spheres of the start
  joints vs the cuboids, + cuRobo's 1 cm activation distance: a hit = cuRobo refuses the start state), and the same
  for the goal IK solution. Variants: full / no_support (cuboids whose top is below the goal fingers - 2 cm dropped)
  / no_objects / empty."""
from __future__ import annotations

import json
import os
import sys

import numpy as np

from harvest.l9 import curobo9 as C9
from harvest.l9 import plan9 as P9


def qmat(q):
    w, x, y, z = (float(v) for v in q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def robot_spheres(pl, q) -> np.ndarray:
    """(N, 4) collision spheres (base frame x, y, z, r) of the joint vector q (cuRobo kinematics)."""
    st = pl.mp.compute_kinematics(pl._js(q))
    s = st.robot_spheres.reshape(-1, 4).cpu().numpy()
    return s[s[:, 3] > 0]


def hits(pl, q, scene: dict, act: float = 0.01) -> list:
    """[(cuboid, deepest sphere penetration m incl. the activation distance)] of joint state q against the scene
    cuboids (base frame). Empty = the world part of cuRobo's start-state check passes."""
    S = robot_spheres(pl, q)
    out = []
    for k, v in scene["cuboid"].items():
        c, R, h = np.asarray(v["pose"][:3], float), qmat(v["pose"][3:]), np.asarray(v["dims"], float) / 2
        p = (S[:, :3] - c) @ R
        d = np.linalg.norm(np.maximum(np.abs(p) - h, 0.0), axis=1)
        pen = S[:, 3] + act - d
        if (pen > 0).any():
            out.append((k, round(float(pen.max()), 4)))
    return out


def world_top(Tb, v) -> float:
    R = Tb[:3, :3] @ qmat(v["pose"][3:])
    c = Tb[:3, :3] @ np.asarray(v["pose"][:3], float) + Tb[:3, 3]
    return float(c[2] + np.abs(R[2]) @ (np.asarray(v["dims"], float) / 2))


def one(pl, path: str) -> dict:
    d = json.load(open(path))
    q = np.asarray(d["q"], float)
    Tb = np.asarray(d["T_world_base"], float)
    Tg_w = np.asarray(d["tcp_T"], float)
    Tg = P9.inv_T(Tb) @ Tg_w
    cub = d["scene"]["cuboid"]
    tip = Tg_w[:3, 3] - Tg_w[:3, 2] * 0.01
    low_w = min(tip[2] + s * 0.04 * Tg_w[2, 1] for s in (-1, 1))
    zb = Tb[2, 3]

    def top_w(v):  # world top z of a base-frame cuboid (the base may be tilted: R1 Pro torso lean)
        return world_top(Tb, v)
    variants = {"full": dict(cub), "no_support": {k: v for k, v in cub.items() if top_w(v) > low_w - 0.02},
                "no_objects": {k: v for k, v in cub.items() if not k.startswith("obj_") and top_w(v) > low_w - 0.02},
                "empty": {}}
    print(f"\n### {path} what={d.get('what')} goal_w {np.round(Tg_w[:3, 3], 3).tolist()} "
          f"approach {np.round(-Tg_w[:3, 2], 2).tolist()} q0 {np.round(q, 3).tolist()}")
    print("  dropped as support:", [k for k in cub if k not in variants["no_support"]])
    res = {"file": os.path.basename(path)}
    for name, sc in variants.items():
        scene = {"cuboid": sc}
        pl.world(scene)
        ok_on, qg, _ = pl.ik(Tg[None], contact_links_off=False)
        ok_off = bool(pl.ik(Tg[None])[0][0])
        Q = pl.pose(q, Tg)
        sh = hits(pl, q, scene)
        gh = hits(pl, qg[0], scene) if ok_on[0] else "no ik"
        print(f"  [{name:10s}] n={len(sc):2d} ik(on) {bool(ok_on[0])} ik(off) {ok_off} plan {'ok' if Q is not None else 'FAIL'} "
              f"start-hits {sh} goal-ik-hits {gh}")
        res[name] = {"plan": Q is not None, "start_hits": sh, "ik_on": bool(ok_on[0])}
    return res


def main():
    a = sys.argv[1:]
    prof = a[a.index("--profile") + 1] if "--profile" in a else "franka_mast"
    arm = a[a.index("--arm") + 1] if "--arm" in a else "right"
    files = [x for x in a if x.endswith(".json")]
    pl = P9.Planner9(C9.load_config(prof, arm))
    out = []
    for f in files:
        try:
            out.append(one(pl, f))
        except Exception as e:  # noqa: BLE001
            print("ERROR", f, type(e).__name__, e)
    print("\nSUMMARY")
    for r in out:
        ns = r.get("no_support", {})
        print(f"  {r['file']:28s} plan(no_support) {ns.get('plan')} start-hits {ns.get('start_hits')} "
              f"empty {r.get('empty', {}).get('plan')}")


if __name__ == "__main__":
    main()
