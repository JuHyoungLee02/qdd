"""Summarise L8-D runner logs (EP / SKIP lines). usage: python logsum.py <log glob> [key: z|task|kind]
Prints episodes / successes / skips per (log file, table height, lift, task or furniture kind)."""
import glob
import json
import sys
from collections import defaultdict

pat = sys.argv[1]
key = sys.argv[2] if len(sys.argv) > 2 else "z"
c = defaultdict(lambda: [0, 0, 0])
for f in sorted(glob.glob(pat)):
    kind = None
    for line in open(f, errors="replace"):
        if line.startswith("START") and "--furniture" in line:
            kind = line.split("--furniture", 1)[1].split()[0]
        if line.startswith("EP "):
            d = json.loads(line[3:])
            k = (d["table_z"], d.get("lift")) if key == "z" else (d["task"] if key == "task" else kind)
            c[k][0] += 1
            c[k][1] += int(d["success"])
        elif line.startswith("SKIP "):
            k = "skip" if key == "z" else (json.loads(line[5:])["task"] if key == "task" else kind)
            c[k][2] += 1
for k in sorted(c, key=str):
    n, s, sk = c[k]
    print(f"{str(k):40s} episodes {n:4d} success {s:4d} skipped {sk:3d}")
