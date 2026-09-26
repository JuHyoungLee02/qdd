"""Show a few scored answers of an eval dir next to the label (approach rows): command, label target, errors.
usage: python peek.py <eval dir> <data jsonl> [n] [step]"""
import json
import sys

d, data = sys.argv[1], sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 8
step = sys.argv[4] if len(sys.argv) > 4 else "descend_close"
rows = {}
for x in open(data):
    r = json.loads(x)
    if r["kind"] == "control":
        rows[r["id"]] = r
rep = {}
for x in open(d + "/replies.jsonl"):
    q = json.loads(x)
    rep[q["id"]] = q
k = 0
for x in open(d + "/scores.jsonl"):
    s = json.loads(x)
    if s["step"] != step:
        continue
    r = rows[s["id"]]
    try:
        cmd = json.loads(rep[s["id"]]["text"])["command"]
    except Exception:  # noqa: BLE001
        cmd = rep[s["id"]]["text"][:200]
    print(s["id"], "LABEL", json.loads(r["answer"])["command"], "PRED", cmd, "xy", s["approach_xy_mm"], "3d",
          s["approach_3d_mm"], "gz", s["grasp_z_mm"])
    k += 1
    if k >= n:
        break
