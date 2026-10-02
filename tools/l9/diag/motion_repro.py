"""L9 v2 diagnosis: replay failed motion dumps of tools/l9/diag/run9_trace.py (motion_<seed>_<k>.json): every world the
runtime tried (with the attached object), plan_pose / line results, start-state hits of the start joints (with the
attached object's spheres), and two relaxations for put moves:
  above_then_line   plan to the goal raised 6 cm (attached object, same world), then a straight line down
  no_attach_line    straight line from the current TCP to the goal (what rt9 tries last)
Plain Isaac python + pylib:  python -m tools.l9.diag.motion_repro --profile P --arm A <motion_*.json> ..."""
from __future__ import annotations

import json
import os
import sys

import numpy as np

from harvest.l9 import curobo9 as C9
from harvest.l9 import plan9 as P9
from tools.l9.diag.transit_repro import hits


def main():
    a = sys.argv[1:]
    prof = a[a.index("--profile") + 1] if "--profile" in a else "ffw_sg2"
    arm = a[a.index("--arm") + 1] if "--arm" in a else "right"
    pl = P9.Planner9(C9.load_config(prof, arm))
    for f in [x for x in a if x.endswith(".json")]:
        d = json.load(open(f))
        q = np.asarray(d["q"], float)
        Tb = np.asarray(d["T_world_base"], float)
        Tg = P9.inv_T(Tb) @ np.asarray(d["tcp_T"], float)
        Tn = P9.inv_T(Tb) @ np.asarray(d["tcp_now"], float)
        print(f"\n### {os.path.basename(f)} step={d.get('step')} note={d.get('note')} tgt={d.get('tgt')}")
        print(f"  goal-now (base) {np.round(Tg[:3, 3] - Tn[:3, 3], 3).tolist()} m")
        for i, t in enumerate(d.get("tries") or []):
            pl.world(t["scene"])
            if t.get("attach"):
                try:
                    pl.attach(t["attach"]["q"], t["attach"]["names"])
                except Exception as e:  # noqa: BLE001
                    print("  attach error", e)
            ik = bool(pl.ik(Tg[None], contact_links_off=False)[0][0])
            try:
                h = hits(pl, q, t["scene"])
            except Exception as e:  # noqa: BLE001
                h = f"err {e}"
            Q = pl.pose(q, Tg, escape=False) if "escape" in P9.Planner9.pose.__code__.co_varnames else pl.pose(q, Tg)
            Tu = Tg.copy()
            Tu[2, 3] += 0.06
            Qu = pl.pose(q, Tu, escape=False) if "escape" in P9.Planner9.pose.__code__.co_varnames else pl.pose(q, Tu)
            Ql = pl.line(Qu[-1], Tu, Tg) if Qu is not None else None
            print(f"  try {i}: n={len(t['scene']['cuboid'])} attach={bool(t.get('attach'))} ik(goal) {ik} start-hits {h} "
                  f"plan {'ok' if Q is not None else 'FAIL'} above+line {'ok' if Ql is not None else ('above ok/line FAIL' if Qu is not None else 'above FAIL')}")
            pl.detach()
        if d.get("tgt_pose") and "--yaw-scan" in a:  # put yaws about the held object's centre (empty world IK)
            pl.world({"cuboid": {}})
            Tgw, Tnw = np.asarray(d["tcp_T"], float), np.asarray(d["tcp_now"], float)
            c = Tgw[:3, 3] + (np.asarray(d["tgt_pose"][0], float) - Tnw[:3, 3])
            res = []
            for yd in (0.0, 0.5236, -0.5236, 1.0472, -1.0472, 1.5708, -1.5708, 3.1416):
                Rz = np.array([[np.cos(yd), -np.sin(yd), 0], [np.sin(yd), np.cos(yd), 0], [0, 0, 1.0]])
                T = Tgw.copy()
                T[:3, :3] = Rz @ Tgw[:3, :3]
                T[:3, 3] = c + Rz @ (Tgw[:3, 3] - c)
                Tu = T.copy()
                Tu[2, 3] += 0.06
                ok = pl.ik(np.stack([P9.inv_T(Tb) @ T, P9.inv_T(Tb) @ Tu]), contact_links_off=False)[0]
                res.append(f"{np.degrees(yd):+.0f}:{'Y' if ok[0] else 'n'}{'Y' if ok[1] else 'n'}")
            print("  yaw scan (put, put+6cm) empty-world IK:", " ".join(res))
        pl.world({"cuboid": {}})
        Ql = pl.line(q, Tn, Tg)
        ikf = pl.ik(Tg[None], contact_links_off=False)
        print(f"  empty world: ik(goal) {bool(ikf[0][0])} line(now->goal) {'ok' if Ql is not None else 'FAIL'} "
              f"pose {'ok' if pl.pose(q, Tg) is not None else 'FAIL'}")


if __name__ == "__main__":
    main()
