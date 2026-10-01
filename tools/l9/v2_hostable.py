"""L9 v2 pre-Isaac check: does every definition instantiate (task9 instantiate, v2=True) on the scenes the plan would
give it, per robot gripper width? Each attempt redraws the scene up to --redraw times like collect9.draw. Pure (no
Isaac): it says nothing about execution success (that is G1).
usage: python tools/l9/v2_hostable.py --out R.json [--n 6] [--redraw 6] [--robots ffw_sg2,g1] [--caps a,b]
       [--defs x,y] [--new-only]"""
import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from harvest.l9 import assets9 as A9  # noqa: E402
from harvest.l9 import reach9 as R9  # noqa: E402
from harvest.l9 import scene9 as S9  # noqa: E402
from harvest.l9 import task9 as T9  # noqa: E402
from harvest.l9 import task9v2 as V2  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan as P  # noqa: E402


def attempt(d, f, r, base_seed, arm, robot, rm, redraw):
    """-> (episode or None, failure reason)."""
    why = "scene"
    for kk in range(redraw):
        seed = base_seed + kk * 100003
        try:
            sc = S9.sample(f, r, seed, arm, rm)
        except RuntimeError:
            continue
        ep = T9.instantiate(d, sc, A9.pool_for(seed % 97), seed, rm, tries=20, grip_max=V2.grip_max_of(robot),
                            v2=True)
        if ep is not None:
            return ep, None
        why = "no_fit"
    return None, why


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--redraw", type=int, default=6)
    ap.add_argument("--robots", default="ffw_sg2,g1")
    ap.add_argument("--caps", default="")
    ap.add_argument("--defs", default="")
    ap.add_argument("--new-only", action="store_true")
    a = ap.parse_args()
    rm = R9.load_default()
    ft = P.features(2)
    caps = [c for c in a.caps.split(",") if c]
    use = V2.defs_for(caps)
    if a.new_only:
        use = {k: d for k, d in use.items() if k in V2.NEW}
    if a.defs:
        use = {k: use[k] for k in a.defs.split(",")}
    robots = a.robots.split(",")
    rep = {}
    for i, (k, d) in enumerate(sorted(use.items())):
        pairs = [fr for fr in S9.all_rules() if P.compat(d, ft[fr])]
        row = {"family": d.family, "pairs": len(pairs), "new": k in V2.NEW}
        for robot in robots:
            ok, cons, poses, why = 0, Counter(), Counter(), Counter()
            for j in range(a.n if pairs else 0):
                f, r = pairs[(i * 7 + j) % len(pairs)]
                ep, w = attempt(d, f, r, 7700000 + i * 100 + j, ("right", "left")[j % 2], robot, rm, a.redraw)
                if ep is None:
                    why[w] += 1
                    continue
                ok += 1
                for s in ep["step_info"]:
                    cons[s["constraint"] or "none"] += 1
                    poses[s["place_pose"]["kind"]] += 1
            row[robot] = {"ok": ok, "n": a.n if pairs else 0, "constraints": dict(cons), "poses": dict(poses),
                          "fail": dict(why)}
        rep[k] = row
        print(k, {r: (row[r]["ok"], row[r]["n"]) for r in robots}, flush=True)
    json.dump(rep, open(a.out, "w"), indent=1)
    bad = {r: sorted(k for k, v in rep.items() if v[r]["ok"] == 0) for r in robots}
    print(json.dumps({"defs": len(rep), "zero_by_robot": {r: len(v) for r, v in bad.items()}, "zero": bad}))


if __name__ == "__main__":
    main()
