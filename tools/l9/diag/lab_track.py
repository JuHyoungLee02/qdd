"""L9 v2 diagnosis: per call truth track of an episode (pure): step, tcp, grip_w, target / place positions, holding,
plus the history line of that call. usage: python tools/l9/diag/lab_track.py <episode dir>"""
import glob
import json
import os
import re
import sys


def main():
    ep = sys.argv[1]
    labs = [json.loads(l) for l in open(os.path.join(ep, "labels.jsonl"))]
    calls = sorted(glob.glob(os.path.join(ep, "calls", "c*")))
    h = []
    if calls:
        t = open(os.path.join(calls[-1], "prompt.txt"), encoding="utf-8").read()
        h = [x for x in t.split("\n") if re.match(r"^\d+: ", x)]
    hd = {int(x.split(":")[0]): x for x in h}
    print("table_z", labs[0].get("table_z") if labs else None)
    for l in labs:
        g = l.get("gt", {})
        c = l.get("call")
        print(f"c{c:02d} {l.get('step'):14s} tcp {g.get('tcp')} gw {g.get('grip_w')} tgt {g.get('tgt')} place {g.get('place')} "
              f"hold {(l.get('pt_state') or {}).get('holding')}")
        if c in hd:
            print("      ", hd[c][:230])


if __name__ == "__main__":
    main()
