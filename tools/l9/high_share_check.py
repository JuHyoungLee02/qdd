"""Offline (CPU, no Isaac) check for the L9_HIGH_SHARE lever (owner 10-03: step_info[*].place_height.band == "high"
was 0.42 % of rendered steps, 0.27 % of successful steps, success 23.5 % on "high" vs 35.8 % overall -- the scene
generator rarely creates high placements). Draws real plan rows through the actual pipeline: alloc9.allocate (same
--total/--min-per-def the production planners use) -> alloc9.plan_rows -> harvest.l9.collect9.draw (scene9.sample +
task9.instantiate, both "Pure"/no Isaac), so the measured band shares reflect BOTH halves of the lever at once:
scene9.high_share (scene-time: how often a HIGH_FIXTURES node is even offered) and alloc9's high-def reweighting
(plan-time: how often the chosen definition even targets one). A full production-size row list is built (so the
per-definition proportions match a real plan); only a `--n`-row stride sample of it is actually drawn (the slow
part), so the measurement stays representative without redrawing the whole plan.
usage: python tools/l9/high_share_check.py [--n 500] [--robots ffw_sg2,franka_mast,r1pro,g1] [--high-share 0.10]
       [--total 6000] [--min-per-def 25] [--seed0 8800000] [--out R.json]"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from harvest.l9 import alloc9 as AL  # noqa: E402
from harvest.l9 import assets9 as A9  # noqa: E402
from harvest.l9 import collect9 as C9  # noqa: E402
from harvest.l9 import reach9 as R9  # noqa: E402
from harvest.l9 import scene9 as S9  # noqa: E402
from harvest.l9 import task9v2 as V2  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan as PL  # noqa: E402


def rows_for(robot: str, total: int, min_per_def: int, start: int) -> list:
    """Same shape as tools/l9/plan_prod_v2.py main(), pure (no Isaac)."""
    use = V2.defs_for([])
    ft = PL.features()
    pairs = {k: [fr for fr in S9.all_rules("train") if PL.compat(d, ft[fr])] for k, d in use.items()}
    defs = {k: d.family for k, d in use.items() if pairs[k]}
    holdout = AL.holdout_defs(defs)
    al = AL.allocate(defs, total, min_per_def, robot_share={robot: 1.0}, holdout=holdout)
    return AL.plan_rows(al, pairs, start=start, holdout=holdout)


def sample_rows(rows: list, n: int) -> list:
    if len(rows) <= n:
        return rows
    stride = len(rows) / float(n)
    return [rows[int(i * stride)] for i in range(n)]


def draw_bands(rows: list, rm) -> dict:
    band, fail = Counter(), Counter()
    ok = 0
    for row in rows:
        try:
            _sc, ep, *_ = C9.draw(row, A9.pool_for(int(row["seed"]) % 97), rm)
        except C9.NoEpisode as ex:
            fail[str(ex)[:50]] += 1
            continue
        ok += 1
        for s in ep["step_info"]:
            band[s["place_height"]["band"]] += 1
    tot = sum(band.values()) or 1
    return {"rows_drawn": len(rows), "episodes_ok": ok, "episodes_fail": sum(fail.values()),
            "fail_top": dict(fail.most_common(5)), "steps": sum(band.values()), "band_n": dict(band),
            "band_share": {k: round(v / tot, 4) for k, v in sorted(band.items(), key=lambda x: -x[1])}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--robots", default="ffw_sg2,franka_mast,r1pro,g1")
    ap.add_argument("--high-share", default=None, help="sets env L9_HIGH_SHARE for this run; omit to use the "
                    "process env (unset = 0 = off, the current baseline)")
    ap.add_argument("--total", type=int, default=6000)
    ap.add_argument("--min-per-def", type=int, default=25)
    ap.add_argument("--seed0", type=int, default=8800000)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.high_share is not None:
        os.environ["L9_HIGH_SHARE"] = a.high_share
    rm = R9.load_default()
    rep = {"env_L9_HIGH_SHARE": os.environ.get("L9_HIGH_SHARE", "0")}
    for i, robot in enumerate(a.robots.split(",")):
        rows = sample_rows(rows_for(robot, a.total, a.min_per_def, a.seed0 + i * 1000000), a.n)
        rep[robot] = draw_bands(rows, rm)
        print(robot, json.dumps(rep[robot]), flush=True)
    if a.out:
        json.dump(rep, open(a.out, "w"), indent=1)
    print(json.dumps({r: rep[r]["band_share"] for r in rep if r != "env_L9_HIGH_SHARE"}))


if __name__ == "__main__":
    main()
