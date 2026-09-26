"""Print selected parts of the analysis JSON files (read-only helper for the results doc)."""
import json
import sys

L = "/data/harvest/logs/marr"
a2 = json.load(open(f"{L}/analysis_v2.json"))
a1 = json.load(open(f"{L}/analysis.json"))
for src in ("RB1", "RB2", "all"):
    s = a2["stats"][src]
    print("V2", src, json.dumps({k: s[k] for k in ("episodes", "frames", "points", "reasons", "kept_frac",
                                                    "active_arm_label_frac", "label_len_hist", "releases",
                                                    "release_point_kept_frac", "fit_episodes")}))
    s = a1["stats"][src]
    print("V1", src, json.dumps({k: s[k] for k in ("reasons", "kept_frac", "active_arm_label_frac", "releases",
                                                    "release_point_kept_frac")}))
print("COLOUR", json.dumps(a2["colour"]))
print("DIV_V2", json.dumps(a2["diversity"]))
print("SCENES", json.dumps(a1["scenes"], ensure_ascii=False))
if len(sys.argv) > 1:
    for e in a2["episodes"]:
        print("EP", json.dumps(e))
