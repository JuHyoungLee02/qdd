"""Inventory of articulated THOR assets (MolmoSpaces objects_thor, CC BY 4.0; pod, pylib python: pxr + numpy) for
user-log 176: per asset variant the joints (type, axis, limits, the two bodies), the bodies that look like handles /
knobs / buttons / doors / drawers, and the render bbox size (Y-up fixed: z = height). Kinds kept: packages whose
name starts with one of PACKAGES. Output one JSON {variant: record}.
usage: python tools/l8x_assets/scan_articulated.py --root .../objects_thor/usd --out scan.json"""
from __future__ import annotations

import argparse
import json
import os

PACKAGES = ("Fridge", "Microwave", "Cabinet", "IKEACabinet", "Dresser", "Desk", "Side_Table", "Kitchen_Faucet",
            "Bathroom_Faucet", "Bathtub_Faucet", "Laptop", "Safe", "Box", "Clothes_Dryer", "Washing_Machine",
            "Toilet", "StoveKnob", "Toaster", "coffee_machine", "Shelving_Unit", "TV_Stand", "Doorway", "Blinds",
            "Television", "Floor_Lamp")
PART_WORDS = ("handle", "knob", "button", "door", "drawer", "lid", "switch", "dial")


def scan(usd: str) -> dict:
    from pxr import Usd, UsdGeom, UsdPhysics
    st = Usd.Stage.Open(usd)
    joints, parts = [], set()
    for p in st.Traverse():
        t = p.GetTypeName()
        if "Joint" in t and t != "PhysicsFixedJoint":
            j = UsdPhysics.Joint(p)
            b0, b1 = j.GetBody0Rel().GetTargets(), j.GetBody1Rel().GetTargets()
            rec = {"name": p.GetName(), "type": t.replace("Physics", "").replace("Joint", ""),
                   "b0": b0[0].name if b0 else None, "b1": b1[0].name if b1 else None}
            ax = p.GetAttribute("physics:axis")
            lo, hi = p.GetAttribute("physics:lowerLimit"), p.GetAttribute("physics:upperLimit")
            rec.update(axis=ax.Get() if ax else None, lower=lo.Get() if lo else None, upper=hi.Get() if hi else None)
            joints.append(rec)
        n = p.GetName().lower()
        if p.HasAPI(UsdPhysics.RigidBodyAPI) and any(w in n for w in PART_WORDS):
            parts.add(p.GetName())
    rg = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"]).ComputeWorldBound(
        st.GetPseudoRoot()).ComputeAlignedRange()
    lo, hi = rg.GetMin(), rg.GetMax()
    size = [round(hi[0] - lo[0], 3), round(hi[2] - lo[2], 3), round(hi[1] - lo[1], 3)]  # x, z(depth), y-up height
    return {"usd": usd, "joints": joints, "n_joints": len(joints),
            "types": sorted({j["type"] for j in joints}), "parts": sorted(parts), "size_xyz_up": size}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = {}
    for pkg in sorted(os.listdir(a.root)):
        base = pkg.replace("thor_", "")
        if not base.startswith(PACKAGES):
            continue
        for var in sorted(os.listdir(os.path.join(a.root, pkg))):
            if var.endswith(("_mesh", "_prim")) or " " in var:
                continue
            usd = os.path.join(a.root, pkg, var, var + ".usda")
            if not os.path.exists(usd):
                continue
            try:
                r = scan(usd)
            except Exception as e:  # noqa: BLE001
                r = {"usd": usd, "error": f"{type(e).__name__}: {e}"[:120]}
            if r.get("n_joints"):
                out[var] = dict(r, package=base)
    json.dump(out, open(a.out, "w"), indent=1)
    from collections import Counter
    print(len(out), "articulated;", Counter(r["package"].split("_")[0] for r in out.values()).most_common(30))
    print(Counter(t for r in out.values() for t in r["types"]))


if __name__ == "__main__":
    main()
