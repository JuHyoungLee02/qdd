"""Short text summary of a gate_v2 json (pure): verdicts, per task family success, definitions passing / failing."""
import json
import sys

r = json.load(open(sys.argv[1]))
print("episodes", r["episodes"], "yield", r["yield"], "max_dq", r["max_dq_rad"], "verdict", r["verdict"])
print("families", json.dumps(r["task_family_success"]))
print("pass", len(r["defs_pass"]), "fail", len(r["defs_fail"]), "short", len(r["defs_short"]))
print("approach", r["approach_share"], "part", r["part_share"])
print("visible", r["visible_point"], "natural_rank0", r["natural_rank0"], "instructed", r["instructed"],
      "regrasp", r["regrasp"], "fallback", r["fallback"], "close", r["close_outcome"])
