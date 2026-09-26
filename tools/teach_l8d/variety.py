"""Variety count, L8 vs L8-D / L8-X (design note §1: 'about 10x'). usage:
  python variety.py <L8 collect root (train)> <L8-D/X collect root (train)> [...more L8-D/X roots]
Per dataset: episodes; distinct surface kinds, table heights, tasks (and task types), object sets (task objects +
layout objects + pool distractors on the table), appearance combos (table material x floor x HDR x light type), and
the product surfaces x heights x tasks x object sets; L8 is read from its labels.jsonl (no scene.json there)."""
import glob
import json
import os
import sys
from collections import Counter

TASK_TYPE = {"mug_tray": "place_on", "bottle_tray": "place_on", "mug_marker": "place_on_spot",
             "mug_stand": "place_on_raised", "stand_mug_tray": "pick_from_raised", "mug_bin": "place_in",
             "bottle_bin": "place_in", "bluemug_tray": "attribute_colour", "smallcup_tray": "attribute_size",
             "mug_left_of_bottle": "relational", "mug_right_of_bottle": "relational", "bluemug_bin": "place_in",
             "bottle_stand": "place_on_raised", "mug_tray_bottle_marker": "multi_step", "clear_to_bin": "multi_step", "mug_tray_bluemug_marker": "multi_step"}


def l8(root):
    eps = {}
    for p in glob.glob(os.path.join(root, "*", "*", "labels.jsonl")):
        with open(p) as f:
            r = json.loads(f.readline())
        objs = tuple(sorted({r["tgt"], r["place"], *r["gt"]["others"]}))
        eps[p] = {"surface": "table", "table_z": 0.85, "task": r["task"], "objects": objs, "appearance": r["variant"]}
    return list(eps.values())


def l8x(root):
    out = []
    for p in glob.glob(os.path.join(root, "*", "*", "scene.json")):
        s = json.load(open(p))
        r = s.get("randomization") or {}
        app = "standard" if s["variant"] == "standard" else "|".join(str((r.get(k) or {}).get("name") or (r.get(k) or {}).get("type"))
                                                                    for k in ("table_material", "floor_material", "hdr", "light"))
        objs = tuple(sorted(set(s["layout"]) | {d for d in s["distractors"]["pool_distractors"]}))
        out.append({"surface": s.get("surface", "table"), "table_z": round(s["table_z"], 3), "task": s["task"],
                    "objects": objs, "appearance": app, "n_distractors": s["distractors"]["n"]})
    return out


def count(eps):
    c = {k: len({e[k] for e in eps}) for k in ("surface", "table_z", "task", "objects", "appearance")}
    c["task_types"] = len({TASK_TYPE.get(e["task"], e["task"]) for e in eps})
    c["episodes"] = len(eps)
    c["surface_x_height_x_task_x_objects"] = len({(e["surface"], e["table_z"], e["task"], e["objects"]) for e in eps})
    c["product_axes"] = c["surface"] * c["table_z"] * c["task"] * c["objects"]
    if eps and "n_distractors" in eps[0]:
        c["distractor_count_hist"] = dict(sorted(Counter(e["n_distractors"] for e in eps).items()))
    return c


base = count(l8(sys.argv[1]))
new = []
for r in sys.argv[2:]:
    new += l8x(r)
nc = count(new)
ratio = {k: round(nc[k] / base[k], 2) for k in ("surface", "table_z", "task", "task_types", "objects", "appearance",
                                                  "surface_x_height_x_task_x_objects") if base.get(k)}
print(json.dumps({"L8": base, "L8X": nc, "ratio": ratio}, indent=1))
