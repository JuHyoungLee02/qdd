"""E-FUT1 change 5 re-verification verdict (prereg_fut1.md §7 + change 5): F2 vs F0 on the whole held-out pool.
P1 (pooled delta 0.5/1/2 gain >= +3 pp, CI low > 0), P2 (Delta*(F2, roll) >= 1.0 s, E-DEP1 SAFE rule), P3 (xy increase
CI high <= 2 mm), P4a (delta-0 drop <= 1 pp) are recomputed on the full pool; P4b-e (static sets, main35 judge) are
taken from result 1 (summary/summary_fut1.json: the same merged models, the sets do not change).
  python tools/fut1/rv_summary.py --root /data/harvest/out/fut1"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fut_summary as S  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/data/harvest/out/fut1")
    a = ap.parse_args(argv)
    rng = np.random.default_rng(0)
    rows = {}
    for v in ("cur", "roll"):
        for x in open(os.path.join(a.root, "data_rv", f"eval_{v}.jsonl")):
            r = json.loads(x)
            rows[r["id"]] = r
    s0 = S.load(a.root, "F0rv", "mm_cur")
    s2 = S.load(a.root, "F2rv", "mm_roll")
    res = {"curves": {"F0rv/mm_cur": S.curve(s0, rows, rng), "F2rv/mm_roll": S.curve(s2, rows, rng)}}
    sx = {i[: -len("roll")] + "cur": s for i, s in s2.items()}
    res["F2_vs_F0"] = {"pool_0.5_1_2": S.paired(sx, s0, rows, S.POOL, rng), "delta0": S.paired(sx, s0, rows, (0.0,), rng),
                       **{f"d{d}": S.paired(sx, s0, rows, (d,), rng) for d in (0.5, 1.0, 2.0, 3.0)}}
    r1 = json.load(open(os.path.join(a.root, "summary", "summary_fut1.json")))
    v1 = r1["verdict"]["F2"]
    pool, d0, cv = res["F2_vs_F0"]["pool_0.5_1_2"], res["F2_vs_F0"]["delta0"], res["curves"]["F2rv/mm_roll"]
    chk = {"P1_future_gain": pool["gain_pp"] >= 3.0 and pool["gain_ci"][0] > 0,
           "P2_delta_star_ge_1s": (cv.get("delta_star") or 0) >= 1.0,
           "P3_xy_not_worse": pool["xy_inc_ci"] is not None and pool["xy_inc_ci"][1] <= 2.0,
           "P4a_d1_static": d0["gain_pp"] >= -1.0,
           **{k: v1[k] for k in ("P4b_l8s_val_acc", "P4c_l8s_val_fail20", "P4d_g_val_hit", "P4e_judge")}}
    res["verdict_F2"] = {"status": "PASS" if all(chk.values()) else "FAIL", **chk}
    res["adopted"] = "F2" if all(chk.values()) else None
    os.makedirs(os.path.join(a.root, "summary"), exist_ok=True)
    json.dump(res, open(os.path.join(a.root, "summary", "summary_fut1_rv.json"), "w"), indent=1)
    c = res["curves"]["F2rv/mm_roll"]
    print(json.dumps({"adopted": res["adopted"], "verdict_F2": res["verdict_F2"],
                      "F2_curve": {d: [c[d]["drop_pp"], c[d]["drop_ci"], c[d]["verdict"]] for d in ("0.5", "1.0", "2.0") if d in c},
                      "delta_star_F2": c.get("delta_star"),
                      "gain": {k: [v["gain_pp"], v["gain_ci"], v["n_rows"]] for k, v in res["F2_vs_F0"].items() if v}}))


if __name__ == "__main__":
    main()
