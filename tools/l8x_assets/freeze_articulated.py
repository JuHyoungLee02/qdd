"""Frozen articulated fixture list (user-log 176): the gate_articulated.py passes -> docs/stage3/l8x_articulated_list.json
with, per asset, the usable joints (actuated, graspable handle), a task kind per joint, the licence and a split
(20 % of the THOR families by name hash -> ood), plus the candidate sources that were NOT imported (licence needs
consent, or conversion pending).
task kinds: prismatic + bar = drawer; revolute + bar on a door / lid = door (fridge_door / microwave_door by package);
revolute + knob = turn; prismatic + knob / lever / button = press.
usage: python tools/l8x_assets/freeze_articulated.py GATE.json SCAN.json OUT.json"""
from __future__ import annotations

import hashlib
import json
import re
import sys

LICENSE = "CC BY 4.0 (MolmoSpaces objects_thor, AI2-THOR assets)"
NOT_IMPORTED = {
    "RoboCasa fixtures (cabinets, drawers, microwaves, fridges, doors)": {
        "licence": "code MIT, assets and datasets CC BY 4.0 (robocasa README); the kitchen fixtures are the "
                   "'lightwheel fixtures' download -- confirm that bundle carries the same CC BY 4.0 before use",
        "status": "not imported: MJCF (MuJoCo) articulations, need an MJCF -> USD conversion (Isaac MJCF importer) "
                  "and a per-fixture joint check; about 10 GB with the other kitchen assets",
        "consent_needed": False},
    "PartNet-Mobility (SAPIEN)": {
        "licence": "SAPIEN / PartNet terms of use: registration and agreement, non-commercial research use",
        "status": "listed only (consent needed, not downloaded)", "consent_needed": True},
    "GAPartNet": {
        "licence": "built on PartNet-Mobility / AKB-48 models: the upstream terms apply (registration, research use)",
        "status": "listed only (consent needed, not downloaded)", "consent_needed": True},
}


def family(n: str) -> str:
    return re.sub(r"(_\d+)+$", "", n)


def split_of(n: str) -> str:
    u = int(hashlib.sha256(f"l8x-art-ood:{family(n)}:{n}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return "ood" if u < 0.2 else "train"


def kind_of(package: str, j: dict, h: dict) -> str:
    if j["type"] == "prismatic":
        return "press" if h["kind"] == "knob" else "drawer"
    if h["kind"] == "knob":
        return "turn"
    p = package.lower()
    return "fridge_door" if "fridge" in p else "microwave_door" if "microwave" in p else "door"


def main(argv=None):
    a = argv or sys.argv[1:]
    gate, scan = json.load(open(a[0])), json.load(open(a[1]))
    items = {}
    for n, r in sorted(gate.items()):
        if not r.get("pass"):
            continue
        pkg = scan.get(n, {}).get("package", family(n))
        joints = []
        for j in r["joints"]:
            hs = [h for h in j["handles"] if h["graspable"]]
            if not (j["ok"] and hs):
                continue
            h = hs[0]
            joints.append({"joint": j["joint"], "type": j["type"], "moving": j["moving"], "range": j["range"],
                           "handle": h["body"], "handle_kind": h["kind"], "handle_z": h["z"],
                           "task": kind_of(pkg, j, h)})
        items[n] = {"package": pkg, "usd": r["usd"], "license": LICENSE, "split": split_of(n), "joints": joints,
                    "tasks": sorted({j["task"] for j in joints})}
    from collections import Counter
    out = {"source": "tools/l8x_assets/gate_articulated.py (Isaac: spawn stability, actuation, handle geometry)",
           "assets": items, "not_imported": NOT_IMPORTED,
           "counts": {"assets": len(items), "by_task": dict(Counter(t for v in items.values() for t in v["tasks"])),
                      "by_package": dict(Counter(family(v["package"]) for v in items.values())),
                      "by_split": dict(Counter(v["split"] for v in items.values())),
                      "gate_tested": len(gate)}}
    out["digest"] = hashlib.sha256(json.dumps(out, sort_keys=True).encode()).hexdigest()
    json.dump(out, open(a[2], "w", newline="\n"), indent=1)
    print(json.dumps(out["counts"]))


if __name__ == "__main__":
    main()
