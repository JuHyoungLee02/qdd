"""Rescaled real objects for the realistic bundle b4 (user-log 173; pod, pylib python: pxr + numpy + Pillow).

The L8-D object gate passes objects 7-10 cm tall with a 2.5-8.5 cm grasp width (prereg_l8d changes 8 / 11: shorter
ones are not held by the truth plan; wider ones stop the pads). Google Scanned Objects outside that box are scaled
uniformly so the height becomes TARGET_H (scale 0.6-1.7 only; the scaled grasp width 3-8 cm, length <= 25 cm, upright
pose; no rolling nouns / sphericity >= 0.6 -- eggs and fruit tip on the tray, realgate 24/27 zero). A rescaled object
is a NEW row "gsor_<name>" (the existing objects_real rows and ids stay byte-identical), its own USD
model_qdd_s<scale*100>.usda (scaled scan vertices, mass from the scaled box), "scale" / "height_orig" recorded,
no size word (the scaled size is not the real one: the name check keeps noun + colour only), split by the same
noun hash. The rows then need the Isaac settle check (validate_objects -> objv_mark_stable) and the L8-D object
gate.
usage: python tools/l8x_assets/rescale_real.py --gso DIR --gso-meta models.json --table objects_real.json --out OUT.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from harvest.sim.assets_x import objects_real as OR  # noqa: E402
from tools.l8x_assets import real_table as RT  # noqa: E402

TARGET_H = 0.085
S_RANGE = (0.6, 1.7)
W_OK, L_MAX = (0.030, 0.080), 0.25
GATE_H, GATE_W = (0.07, 0.10), (0.025, 0.085)
ROLLING = ("egg", "apple", "potato", "tomato", "ball", "orange", "lemon", "lime", "peach", "fruit")


def plan_scale(d: dict):
    """-> scale or None: only objects outside the gate box that fit it after a uniform scale to TARGET_H."""
    if GATE_H[0] <= d["height"] <= GATE_H[1] and GATE_W[0] <= d["grasp_width"] <= GATE_W[1]:
        return None  # already a gate candidate at its real size
    s = TARGET_H / d["height"]
    if not S_RANGE[0] <= s <= S_RANGE[1]:
        return None
    if not (W_OK[0] <= d["grasp_width"] * s <= W_OK[1] and d["length"] * s <= L_MAX):
        return None
    if d["height"] < 0.8 * d["grasp_width"]:  # lying: not a pick target
        return None
    return round(float(s), 3)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--gso", required=True)
    ap.add_argument("--gso-meta", required=True)
    ap.add_argument("--table", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    cats = {r["name"]: (r.get("categories") or [""])[0] for r in json.load(open(a.gso_meta))}
    old = json.load(open(a.table))["objects"]
    out, drop = {}, {}
    for name in sorted(os.listdir(a.gso)):
        d0 = os.path.join(a.gso, name)
        obj = os.path.join(d0, "meshes", "model.obj")
        if not os.path.exists(obj):
            continue
        claim = OR.claimed_noun(name, cats.get(name, ""))
        if claim == "SKIP":
            continue
        try:
            V, T, F, FT = RT.read_obj(obj)
            d = OR.descriptors(OR.sample_surface(V, F))
            s = plan_scale(d)
            if s is None:
                continue
            V = V * s
            d = OR.descriptors(OR.sample_surface(V, F))
            if d["sphericity"] >= 0.6 or RT.gate(d):
                drop[name] = f"after scale {s}: sphericity {d['sphericity']} / gate {RT.gate(d)}"
                continue
            tex = os.path.join(d0, "materials", "textures", "texture.png")
            colour = OR.colour_word(RT.texture_colour(tex, T)) if os.path.exists(tex) else None
            mass = float(np.clip(d["height"] * d["grasp_width"] * d["length"] * 0.4 * 600, 0.05, 1.0))
            usd = os.path.join(d0, f"model_qdd_s{int(round(s * 100))}.usda")
            RT.write_gso_usd(usd, V, T, F, FT, "materials/textures/texture.png", mass)
            r = RT.row("Google Scanned Objects (Gazebo Fuel GoogleResearch)", name, d, colour, claim, usd,
                       [1.0, 0.0, 0.0, 0.0], {"mass": round(mass, 3), "category_src": cats.get(name, ""),
                                              "attribution": "Google LLC, Google Scanned Objects (CC BY 4.0)"},
                       V=V, F=F, body_rel="")
            if r["noun"] in ROLLING or r["noun"] in ("object",):
                drop[name] = f"noun {r['noun']}"
                continue
            k = "gsor_" + name[:36]
            if k in old:
                raise ValueError(f"id clash {k}")
            r.update(scale=s, height_orig=round(float(d["height"] / s), 4), size_word=None)
            r["task_name"] = OR.task_name(r, None)
            r["name"], r["uid"], r["split"] = r["task_name"], k, RT.split_of(r["noun"])
            out[k] = r
        except Exception as e:  # noqa: BLE001
            drop[name] = f"{type(e).__name__}: {e}"[:100]
    res = {"license": RT.LICENSE, "rescale": {"target_h": TARGET_H, "scale": S_RANGE, "grasp_width": W_OK,
                                              "length_max": L_MAX}, "objects": out, "dropped": drop}
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)
    from collections import Counter
    print("rescaled", len(out), "dropped", len(drop), dict(Counter(o["split"] for o in out.values())))
    print("nouns", Counter(o["noun"] for o in out.values()).most_common(30))


if __name__ == "__main__":
    main()
