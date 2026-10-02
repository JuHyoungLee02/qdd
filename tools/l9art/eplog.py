"""Print an articulated episode's calls (stdlib only): python3 eplog.py <episode dir> [...]"""
import json
import os
import sys

for d in sys.argv[1:]:
    m = json.load(open(os.path.join(d, "meta.json")))
    print("==", os.path.basename(d), "success", m.get("success"), m.get("end_reason"), "dq", m.get("max_dq_rad"),
          "judge", json.dumps(m.get("judge"))[:300])
    for line in open(os.path.join(d, "labels.jsonl")):
        r = json.loads(line)
        c = r["command"]
        print(r["call"], r["sub"], c.get("mode"), c.get("skill"), c.get("point_2d"), c.get("point2"), c.get("height"),
              c.get("gripper"), c.get("approach"), c.get("rot"), {k: round(v, 3) for k, v in r["joints"].items()},
              r["grip_w"], r.get("exec_kind"), "->", r.get("outcome"))
