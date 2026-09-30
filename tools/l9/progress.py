"""L9 run progress (pod): episodes / successes / skips, per family and arm, episodes in the last hour (throughput),
jobs done. usage: python progress.py <run dir>  -> JSON on stdout"""
import glob
import json
import os
import sys
import time
from collections import Counter

R = sys.argv[1]
now = time.time()
n = ok = last_h = ok_h = 0
fam, arm = Counter(), Counter()
for m in glob.glob(os.path.join(R, "collect", "**", "meta.json"), recursive=True):
    try:
        meta = json.load(open(m))
    except Exception:  # noqa: BLE001 - a meta being written
        continue
    n += 1
    s = bool(meta.get("success"))
    ok += s
    if s:
        fam[meta.get("env_family")] += 1
        arm[meta.get("arm")] += 1
    if now - os.path.getmtime(m) < 3600:
        last_h += 1
        ok_h += s
skips = len(glob.glob(os.path.join(R, "collect", "**", "skipped.json"), recursive=True))
jobs = sum(1 for _ in open(os.path.join(R, "jobs.txt")))
done = len(os.listdir(os.path.join(R, "done"))) if os.path.isdir(os.path.join(R, "done")) else 0
print(json.dumps({"utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(now)), "episodes": n, "success": ok,
                  "skipped": skips, "last_hour_episodes": last_h, "last_hour_success": ok_h,
                  "success_by_family": dict(fam), "success_by_arm": dict(arm), "jobs": jobs, "jobs_done": done}))
