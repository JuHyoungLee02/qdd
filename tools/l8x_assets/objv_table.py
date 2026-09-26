"""Objaverse (MolmoSpaces, CC-BY / CC-BY-SA / CC0 only) object table for the L8-D objset (pod, pxr).

Per selected object: a render-only copy (usd_import.make_visual), the size after the Y-up fix (MolmoSpaces geometry
is Y-up although the layer says Z: height = the USD y extent), and an OBJ_GEOM-like row:
  shape "mesh", usd (visual copy), usd_physics (original: rigid body + its own collider), up "Y",
  half_extents / height / grasp_width (smaller horizontal side, fingers close along world x) / length / footprint_r /
  top_z_rel, mass (metadata, clipped 0.05-1.0 kg), friction, category, name (two words), split (train / ood_o by
  category hash), licence, licence_info (creator, uri) -> attribution, source.
Objects whose USD size breaks the L8-D rule (height 4.5-10 cm, grasp side 1.6-9 cm, long side <= 20 cm) are dropped
with the reason (the metadata box and the USD box can disagree).
usage: python tools/l8x_assets/objv_table.py SELECTION.json PKG_DIR OUT.json"""
from __future__ import annotations

import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from harvest.sim.assets_x.usd_import import make_visual, render_bbox  # noqa: E402

SOURCE = "MolmoSpaces (allenai/molmospaces, isaac/objects/objaverse/20260128), Objaverse 1.0 (ODC-BY) models"


def main(argv=None):
    from pxr import Usd
    a = argv or sys.argv[1:]
    sel = json.load(open(a[0]))
    out, drop = {}, {}
    for uid, s in sorted(sel.items()):
        d = os.path.join(a[1], s["package"].replace(".tar.zst", ""), "obja_" + uid)
        src = os.path.join(d, "obja_" + uid + ".usda")
        if not os.path.exists(src):
            drop[uid] = "not fetched"
            continue
        try:
            lo, hi = render_bbox(Usd.Stage.Open(src))
            ex = hi - lo
            h, wx, wy = float(ex[1]), float(ex[0]), float(ex[2])  # Y-up: height = y; horizontal = x, z
            g, L = min(wx, wy), max(wx, wy)
            if not (0.045 <= h <= 0.10 and 0.016 <= g <= 0.090 and L <= 0.20):
                drop[uid] = f"usd size h {h:.3f} w {g:.3f} l {L:.3f}"
                continue
            vis = make_visual(src)
        except Exception as e:  # noqa: BLE001
            drop[uid] = f"{type(e).__name__}: {e}"[:120]
            continue
        li = s.get("license_info") or {}
        out["objv_" + uid[:12]] = {
            "uid": uid, "shape": "mesh", "usd": vis["visual"], "usd_physics": src, "up": "Y",
            "extent_m": [round(wx, 4), round(h, 4), round(wy, 4)],
            "bbox_usd": [[round(float(v), 4) for v in lo], [round(float(v), 4) for v in hi]],
            "spawn_quat_wxyz": [0.7071068, 0.7071068, 0.0, 0.0],  # rotateX +90: Y-up geometry stands up
            "root_above_bottom": round(float(-lo[1]), 4),  # root z = support top + this (after the rotation)
            "centre_from_root_xy": [round(float((lo[0] + hi[0]) / 2), 4), round(float(-(lo[2] + hi[2]) / 2), 4)],
            "half_extents": [round(wx / 2, 4), round(wy / 2, 4), round(h / 2, 4)],
            "height": round(h, 4), "grasp_width": round(g, 4), "length": round(L, 4),
            "footprint_r": round(math.hypot(wx, wy) / 2, 4), "top_z_rel": round(h, 4),
            "grasp_axis": "x" if wx <= wy else "z_usd (turn yaw 90 deg)",
            "mass": round(min(1.0, max(0.05, float(s.get("mass") or 0.2))), 3), "friction": [0.8, 0.8],
            "category": s["category"], "name": s.get("name_short") or s["category"], "split": s["split"],
            "license": {"by": "CC BY 4.0", "by-sa": "CC BY-SA 4.0", "cc0": "CC0 1.0"}.get(s["license"], s["license"]),
            "attribution": {"creator": li.get("creator_username"), "uri": li.get("uri")},
            "source": SOURCE}
    res = {"license_rule": "CC0 / CC BY / CC BY-SA only (no NC, no ND); attribution per object",
           "source": SOURCE, "objects": out, "dropped": drop}
    with open(a[2], "w") as f:
        json.dump(res, f, indent=1)
    sp = {}
    for v in out.values():
        sp[v["split"]] = sp.get(v["split"], 0) + 1
    print("objects", len(out), sp, "categories", len({v["category"] for v in out.values()}), "dropped", len(drop))
    reasons = {}
    for w in drop.values():
        k = w.split(" ")[0] + (" " + w.split(" ")[1] if w.startswith("usd") else "")
        reasons[k] = reasons.get(k, 0) + 1
    print("drop reasons", reasons)


if __name__ == "__main__":
    main()
