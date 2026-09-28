"""Peek at RefSpatial Simulator metadata.json: top-level type / length and the first record (truncated), plus the
first image paths. usage: python refsp_peek.py <root>"""
import json
import os
import sys

root = sys.argv[1]
m = json.load(open(os.path.join(root, "Simulator", "metadata.json")))
print("TYPE", type(m).__name__, "LEN", len(m))
first = m[0] if isinstance(m, list) else m[next(iter(m))]
print("KEYS", list(first))
for k in first:
    if k not in ("think",):
        print(k, json.dumps(first[k])[:700])
n = 0
for dp, _, fs in os.walk(os.path.join(root, "Simulator", "image")):
    for f in fs[:3]:
        print("IMG", os.path.join(dp, f))
        n += 1
    if n >= 3:
        break
