"""Print one episode's history, invalid-answer errors and blocked / clipped events (debugging, no model calls).
usage: python tools/astra_solo/show.py <episode dir>"""
import json
import os
import sys

res = json.load(open(os.path.join(sys.argv[1], "result.json")))
print({k: res.get(k) for k in ("success", "grasp_lift", "fail_stage", "end_reason", "n_calls", "n_invalid", "sim_t",
                               "first_close", "modes")})
for h in res["history"]:
    print("H", h)
for c in res["calls"]:
    if not c["valid"]:
        print("INVALID", c["call"], c["site"], c["attempt"], c["errors"][:3])
for e in res["events"]:
    if e["event"] in ("timeout", "clipped", "settled"):
        print("EV", e)
