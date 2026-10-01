"""Merge finished ProcTHOR room tables (tools/l9/assets/rooms9_table.py outputs, e.g. procthor-10k-train / -test on the
pod) into harvest/l9/assets9/rooms_l9.json (run9.room_table reads it; the 20 % room hold-out is by name hash).
usage: python tools/l9v2env/merge_rooms.py ROOMS_A.json [ROOMS_B.json ...]   (local copies of the pod files)"""
import json
import os
import sys
from collections import Counter

DST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "harvest", "l9", "assets9", "rooms_l9.json")


def main():
    tab = json.load(open(DST, encoding="utf-8"))
    n0 = len(tab["rooms"])
    for p in sys.argv[1:]:
        t = json.load(open(p, encoding="utf-8"))
        for k, r in t["rooms"].items():
            if r.get("clear_checked") and k not in tab["rooms"]:
                tab["rooms"][k] = r
    json.dump(tab, open(DST, "w", encoding="utf-8", newline="\n"), separators=(",", ":"))
    print("rooms", n0, "->", len(tab["rooms"]), Counter(r.get("kind") for r in tab["rooms"].values()))


if __name__ == "__main__":
    main()
