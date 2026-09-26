"""Curate the THOR furniture import (usd_import output) into harvest/sim/assets_x/assets_table.json (pure).

Keeps a piece when: no import error; the collider bbox matches the render bbox within MAX_RENDER_GAP_MM (else the
support heights would not match what the camera sees); height and footprint are furniture-sized; it has at least
one support surface. Each kept piece gets its surface-kind label from its category, an OOD split by name hash (20 %
of the pieces of every category, never trained on) and its licence / source line.
usage: python tools/l8x_assets/curate_thor.py RAW.json OUT.json"""
from __future__ import annotations

import hashlib
import json
import re
import sys

CATEGORY = {  # name prefix -> (category, surface kind of its top-most open surface)
    "Countertop": ("counter", "counter"), "Cabinet": ("counter", "counter"), "IKEACabinet": ("counter", "counter"),
    "Dining_Table": ("table", "table"), "Desk": ("table", "table"), "Side_Table": ("side_table", "table"),
    "Coffee_Table": ("low_table", "low_table"), "Shelving_Unit": ("shelf", "shelf_top"),
    "TV_Stand": ("shelf", "shelf_top"), "Dresser": ("shelf", "shelf_top"), "bin": ("bin", "bin_floor"),
    "Laundry_Hamper": ("bin", "bin_floor"), "Stool": ("low", "low_table"), "Footstool": ("low", "low_table"),
    "Ottoman": ("low", "low_table"),
}
SKIP = ("Sink", "Cart")  # a sink basin needs its counter; a cart has wheels / handles
MAX_RENDER_GAP_MM = 40.0
LICENSE = "CC BY 4.0"
SOURCE = "MolmoSpaces (allenai/molmospaces, isaac/objects/thor/20260128), AI2-THOR assets"
OOD_SHARE = 0.2


def category(name: str):
    for pre, v in CATEGORY.items():
        if re.match(pre + r"(_|\d|$)", name):
            return v
    return None


def split_of(name: str) -> str:
    h = int(hashlib.sha256(("l8x-ood-o:" + name).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return "ood" if h < OOD_SHARE else "train"


def curate(raw: dict) -> dict:
    keep, drop = {}, {}
    for name, r in sorted(raw.items()):
        if name.startswith(SKIP):
            drop[name] = "skip_category"
            continue
        cat = category(name)
        if cat is None:
            drop[name] = "no_category"
            continue
        if "error" in r:
            drop[name] = r["error"][:80]
            continue
        if r["render_vs_collider_mm"] > MAX_RENDER_GAP_MM:
            drop[name] = f"render_vs_collider {r['render_vs_collider_mm']} mm"
            continue
        sx, sy, sz = r["collider_size"]
        if not (0.25 <= sz <= 2.5 and 0.25 <= max(sx, sy) <= 3.5):
            drop[name] = f"size {r['collider_size']}"
            continue
        surfs = [s for s in r["surfaces"] if s["top_z"] > 0.05]
        if not surfs:
            drop[name] = "no_surface"
            continue
        keep[name] = {"category": cat[0], "top_kind": cat[1], "dst": r["dst"], "src": r["src"],
                      "collider_size": r["collider_size"], "render_size": r["render_size"],
                      "origin_offset": r["origin_offset"], "render_vs_collider_mm": r["render_vs_collider_mm"],
                      "n_colliders": r["n_colliders"], "surfaces": surfs, "split": split_of(name),
                      "license": LICENSE, "source": SOURCE}
    return {"license": LICENSE, "source": SOURCE, "inventory": INVENTORY, "assets": keep, "dropped": drop}


INVENTORY = {  # checked 2026-09-27 (L8X-assets); pod Isaac Sim 5.1.0-rc.19 + Isaac Lab 2.3.0
    "used": {
        "molmospaces_thor_objects_usd": {
            "license": "CC BY 4.0 (HF card: all non-Objaverse subsets)", "download": "1.10 GB tar, 382 packages",
            "path": "/data/harvest/assets_x/molmospaces/objects_thor", "isaac": "Isaac Sim 5.1 / Lab 2.3.1 USD; "
            "geometry Y-up although upAxis=Z (rotateX 90 wrapper), articulated doors frozen (static copy)"},
        "parametric_cuboids": {"license": "ours", "note": "furniture.py kinds, no external asset"},
    },
    "downloaded_not_yet_used": {
        "molmospaces_ithor_scenes_usd": {"license": "CC BY 4.0", "download": "0.23 GB, 120 floor plans",
                                          "path": "/data/harvest/assets_x/molmospaces/scenes_ithor"},
    },
    "available_not_imported": {
        "cyclo_lab_42dcd82_objects": {"license": "Apache-2.0", "items": "robotis_aiworker_table, robotis_net_table, "
                                      "robotis_omy_table, plastic_basket, plastic_basket2 (+ small tools)",
                                      "path": "/data/harvest/cyclo_lab_42dcd82/source/cyclo_lab/data/object"},
    },
    "excluded": {
        "molmospaces_objaverse": "per-object licences, some CC BY-NC / BY-NC-SA; unused until filtered with "
                                 "MLSPACES_LICENSE_POLICY=commercial_safe and the per-object table",
        "behavior_1k_assets": "code MIT, but the asset bundle has its own EULA: encrypted, no extraction / reverse "
                              "engineering, no redistribution, the user must accept it -- not usable in our scenes",
        "isaac_nucleus_props": "NVIDIA asset licence; no Nucleus mirror on the pod -- not used",
    },
}


def main(argv=None):
    a = argv or sys.argv[1:]
    raw = json.load(open(a[0]))
    t = curate(raw)
    with open(a[1], "w") as f:
        json.dump(t, f, indent=1)
    by = {}
    for n, r in t["assets"].items():
        d = by.setdefault(r["category"], {"n": 0, "ood": 0, "tops": []})
        d["n"] += 1
        d["ood"] += r["split"] == "ood"
        d["tops"].append(max(s["top_z"] for s in r["surfaces"] if s["covered_above"] is None)
                         if any(s["covered_above"] is None for s in r["surfaces"]) else None)
    for c, d in sorted(by.items()):
        tops = [x for x in d["tops"] if x is not None]
        print(f"{c:12s} kept {d['n']:3d} (ood {d['ood']:2d}) open-top {min(tops):.3f}-{max(tops):.3f}")
    reasons = {}
    for n, why in t["dropped"].items():
        k = why.split(" ")[0]
        reasons[k] = reasons.get(k, 0) + 1
    print("dropped", len(t["dropped"]), reasons)


if __name__ == "__main__":
    main()
