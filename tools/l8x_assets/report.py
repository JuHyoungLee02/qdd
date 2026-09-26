"""Per-kind table of a validate.py summary.json (pure).
usage: python tools/l8x_assets/report.py summary.json"""
from __future__ import annotations

import json
import sys


def table(summ: list) -> dict:
    out = {}
    for r in summ:
        d = out.setdefault(r["kind"], {"scenes": 0, "spawn_ok": 0, "surfaces": 0, "drop_n": 0, "drop_ok": 0,
                                        "usable": 0, "reach_ok": 0, "ray_n": 0, "ray_ok": 0, "tops": [],
                                        "usable_tops": []})
        d["scenes"] += 1
        d["spawn_ok"] += bool(r["spawn"]["ok"])
        for s in r["surfaces"]:
            d["surfaces"] += 1
            d["tops"].append(s["top_z"])
            for x in s.get("drop", {}).values():
                d["drop_n"] += 1
                d["drop_ok"] += bool(x["ok"])
            ray = s.get("ray", {})
            if ray.get("hit"):
                d["ray_n"] += 1
                d["ray_ok"] += abs(ray.get("dz_mm", 1e9)) <= 5.0
            if s["usable"]:
                d["usable"] += 1
                d["usable_tops"].append(s["top_z"])
                d["reach_ok"] += bool(s.get("reach", {}).get("ok"))
    return out


def main(argv=None):
    a = argv or sys.argv[1:]
    t = table(json.load(open(a[0])))
    print("kind | scenes | spawn ok | surfaces (top range) | drop ok | ray |dz|<=5mm | usable (tops) | reach ok")
    for k, d in t.items():
        ut = d["usable_tops"]
        print(f"{k} | {d['scenes']} | {d['spawn_ok']} | {d['surfaces']} ({min(d['tops']):.2f}-{max(d['tops']):.2f}) | "
              f"{d['drop_ok']}/{d['drop_n']} | {d['ray_ok']}/{d['ray_n']} | {d['usable']}"
              + (f" ({min(ut):.2f}-{max(ut):.2f})" if ut else "") + f" | {d['reach_ok']}/{d['usable']}")


if __name__ == "__main__":
    main()
