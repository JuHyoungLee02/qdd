"""L9 common-executor A/B (L9_COMMON_EXEC off vs on, same rows): build two run dirs from existing pilot plans and
compare them afterwards.

  mk:  python -m tools.l9.common_ab mk --out /data/harvest/l9v2/common/ab1 --n 20 \
           --src ffw_sg2=/data/harvest/l9v2/pilot1 --src franka_mast=/data/harvest/l9v2/pilotF ...
       -> <out>/off and <out>/on, each with plan_pilot_v2.json (the first n rows of that robot, job ids
          cx_<robot>_<k>, one row per job) + jobs.txt (lane.sh format) + HCAM_ON when the source has it. The 'on' dir
          gets a COMMON_EXEC marker; the lane must be started with L9_COMMON_EXEC=1 for it (isaac.sh passes it).
  cmp: python -m tools.l9.common_ab cmp --out <out>
       -> per robot: n, success, gate pass (success and max_dq_rad <= 0.04), max_dq max, SkipScene redraws."""
from __future__ import annotations

import argparse
import json
import os
import shutil

GATE = 0.04


def mk(out: str, srcs: dict, n: int, rows_per_job: int = 1) -> dict:
    counts = {}
    plans = {"off": [], "on": []}
    for robot, src in srcs.items():
        rows = [r for r in json.load(open(os.path.join(src, "plan_pilot_v2.json"))) if r.get("robot") == robot][:n]
        counts[robot] = len(rows)
        for k, r in enumerate(rows):
            for arm in plans:
                plans[arm].append(dict(r, job=f"cx_{robot}_{k // rows_per_job:03d}"))
    for arm, rows in plans.items():
        d = os.path.join(out, arm)
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, "plan_pilot_v2.json")
        json.dump(rows, open(p, "w"))
        jobs = sorted({r["job"] for r in rows})
        with open(os.path.join(d, "jobs.txt"), "w") as f:
            for j in jobs:
                f.write(f"--plan {p} --job {j} --v2 --p 0.15\n")
        if any(os.path.exists(os.path.join(s, "HCAM_ON")) for s in srcs.values()):
            shutil.copy(next(os.path.join(s, "HCAM_ON") for s in srcs.values()
                             if os.path.exists(os.path.join(s, "HCAM_ON"))), os.path.join(d, "HCAM_ON"))
        if arm == "on":
            open(os.path.join(d, "COMMON_EXEC"), "w").write("L9_COMMON_EXEC=1\n")
    return counts


def scan(run: str) -> dict:
    out: dict = {}
    for d, _, files in os.walk(os.path.join(run, "collect")):
        if "meta.json" not in files:
            continue
        try:
            m = json.load(open(os.path.join(d, "meta.json")))
        except (OSError, ValueError):
            continue
        r = out.setdefault(str(m.get("robot")), {"n": 0, "success": 0, "pass": 0, "max_dq": 0.0, "seeds": set()})
        r["n"] += 1
        ok = bool(m.get("success"))
        dq = float(m.get("max_dq_rad") or 0.0)
        r["success"] += ok
        r["pass"] += ok and dq <= GATE
        r["max_dq"] = max(r["max_dq"], dq)
        r["seeds"].add(m.get("seed"))
    return out


def cmp(out: str) -> dict:
    res = {}
    for arm in ("off", "on"):
        for robot, r in scan(os.path.join(out, arm)).items():
            res.setdefault(robot, {})[arm] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()
                                              if k != "seeds"}
            res[robot][arm]["seeds"] = sorted(s for s in r["seeds"] if s is not None)
    for robot, r in res.items():  # same-seed subset
        if "off" in r and "on" in r:
            r["common_seeds"] = len(set(r["off"]["seeds"]) & set(r["on"]["seeds"]))
        for arm in ("off", "on"):
            if arm in r:
                r[arm].pop("seeds")
    return res


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("mk", "cmp"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--rows-per-job", type=int, default=1)
    ap.add_argument("--src", action="append", default=[], help="robot=run dir with plan_pilot_v2.json")
    a = ap.parse_args(argv)
    if a.cmd == "mk":
        print(json.dumps(mk(a.out, dict(s.split("=", 1) for s in a.src), a.n, a.rows_per_job)))
    else:
        print(json.dumps(cmp(a.out), indent=1))


if __name__ == "__main__":
    main()
