"""Fast L9 throughput metric from the lane logs (pure): episodes and gate-passing successes (success and max_dq_rad
<= 0.04) per 10-minute window, per pod (START host=) and robot. EP lines carry no clock: a line's time = its job's
START + boot + the running sum of EP wall_total_s / SKIP wall_s, boot = (EXIT - START) - sum (finished jobs) or the
median boot of finished jobs (running jobs). Does not read meta.json mtimes (rewritten files inflate them).
usage: python tools/l9/rate9.py [--hours 1] [--win 10] [--logs /data/harvest/logs/l9]"""
import glob
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

START = re.compile(r"^START (\S+) host=(\S+) gpu=(\d+) harvest\.l9\.run9")
EXIT = re.compile(r"^EXIT -?\d+ (\S+)")


def ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()


def jobs_of(path):
    """-> list of jobs: {start, host, gpu, end, rows: [(kind, wall, robot, ok)]}."""
    out, cur = [], None
    for line in open(path, errors="replace"):
        m = START.match(line)
        if m:
            cur = {"start": ts(m.group(1)), "host": m.group(2), "gpu": m.group(3), "end": None, "rows": []}
            out.append(cur)
            continue
        if cur is None:
            continue
        if line.startswith("EP {"):
            try:
                d = json.loads(line[3:])
            except ValueError:
                continue
            ok = bool(d.get("success")) and (d.get("max_dq_rad") or 0) <= 0.04
            cur["rows"].append(("EP", float(d.get("wall_total_s") or 0), d.get("robot") or "?", ok))
        elif line.startswith("SKIP {"):
            try:
                d = json.loads(line[5:])
            except ValueError:
                continue
            cur["rows"].append(("SKIP", float(d.get("wall_s") or 0), None, False))
        else:
            m = EXIT.match(line)
            if m:
                cur["end"] = ts(m.group(1))
    return out


def main():
    a = sys.argv[1:]
    arg = lambda k, d: type(d)(a[a.index(k) + 1]) if k in a else d  # noqa: E731
    hours, win, logs = arg("--hours", 1.0), arg("--win", 10) * 60, arg("--logs", "/data/harvest/logs/l9")
    now = time.time()
    t_min = now - hours * 3600
    jobs = []
    for p in glob.glob(os.path.join(logs, "*.log")):
        if os.path.getmtime(p) < t_min - 7200:
            continue
        jobs += [j for j in jobs_of(p) if (j["end"] or now) >= t_min]
    boots = sorted((j["end"] - j["start"]) - sum(r[1] for r in j["rows"]) for j in jobs if j["end"] and j["rows"])
    boot0 = boots[len(boots) // 2] if boots else 60.0
    W = defaultdict(lambda: [0, 0])  # (window, pod, robot) -> [eps, succ]
    for j in jobs:
        boot = max(0.0, (j["end"] - j["start"]) - sum(r[1] for r in j["rows"])) if j["end"] else boot0
        t = j["start"] + boot
        pod = j["host"].replace("juhyoung-", "")
        for kind, wall, robot, ok in j["rows"]:
            t += wall
            if kind != "EP" or t < t_min or t > now:
                continue
            w = int((now - t) // win)
            W[(w, pod, robot)][0] += 1
            W[(w, pod, robot)][1] += ok
    per_h = 3600.0 / win
    tot = defaultdict(lambda: [0, 0])
    print(f"window {win // 60} min, newest first; succ/h = gate-passing successes per hour; boot median {boot0:.0f} s")
    for w in sorted({k[0] for k in W}):
        e = sum(v[0] for k, v in W.items() if k[0] == w)
        s = sum(v[1] for k, v in W.items() if k[0] == w)
        pods = defaultdict(lambda: [0, 0])
        for (ww, pod, robot), v in W.items():
            if ww == w:
                pods[pod][0] += v[0]
                pods[pod][1] += v[1]
                tot[(pod, robot)][0] += v[0]
                tot[(pod, robot)][1] += v[1]
        ps = " ".join(f"{p}:{v[1] * per_h:.0f}" for p, v in sorted(pods.items()))
        print(f"-{w * win // 60 + win // 60:3d}..-{w * win // 60:3d} min  eps/h {e * per_h:5.0f}  succ/h {s * per_h:5.0f}  | {ps}")
    print("per pod / robot over the whole span (succ/h):")
    for (pod, robot), v in sorted(tot.items()):
        print(f"  {pod:16s} {robot:12s} eps {v[0]:4d} succ {v[1]:4d}  succ/h {v[1] / hours:6.1f}  yield {v[1] / max(v[0], 1):.2f}")


if __name__ == "__main__":
    main()
