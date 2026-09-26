"""Gate G-H table (prereg_l8d.md §2). usage:
  python gate.py <reach.json> <out.json> [<gate collect root>]
Without the collect root: view / reach bands and the workspace box per candidate height (what the truth gate runs
with). With it: + clean truth success per height (meta.json of <root>/gate/standard_tz<z>/*/), the verdicts, the
passing range around 0.85, and the train / outer OOD heights (spec.heights_from_gate)."""
import glob
import json
import os
import sys

from harvest.teach_l8d import spec as S

reach = json.load(open(sys.argv[1]))
out = sys.argv[2]
root = sys.argv[3] if len(sys.argv) > 3 else None
cam = reach["head_cam"]
rows = []
for tz in S.HEIGHT_CANDIDATES:
    view = S.view_band(tz, cam)
    rb = S.reach_band(reach["xs"], reach["zs"], reach["err_mm"], (tz + S.Z_NEED[0], tz + S.Z_NEED[1]))
    n = k = 0
    if root:
        for m in glob.glob(os.path.join(root, "gate", f"standard_tz{tz:.3f}", "*", "meta.json")):
            m = json.load(open(m))
            if m["style"] == "clean":
                n += 1
                k += int(m["success"])
    g = S.gate_h(tz, view, rb, n, k) if root else dict(S.gate_h(tz, view, rb, 1, 1), note="bands only")
    rows.append(g)
    print(json.dumps(g))
res = {"reach_file": sys.argv[1], "lift_shift": reach.get("lift_shift"), "rows": rows}
if root:
    rg = S.gate_range(rows)
    res["range"] = rg
    if rg:
        tr, outer = S.heights_from_gate(*rg)
        res["train_heights"], res["outer_ood_heights"] = tr, outer
        res["ws"] = {f"{r['table_z']:.3f}": r["ws_x"] for r in rows if r["pass"]}
    print("RANGE", json.dumps({k: res.get(k) for k in ("range", "train_heights", "outer_ood_heights")}))
with open(out, "w") as f:
    json.dump(res, f, indent=1)
