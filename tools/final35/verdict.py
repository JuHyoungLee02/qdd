"""Final 35B D vs H verdict (prereg_final35.md §3): per L8-X set and depth mode, the approach 3D median of H and D and the
paired snapshot bootstrap (tools/teach_pt/dist8_compare.py, 10,000, seed 0, margin 2 mm) of H - D; then the rule:
H_ADOPT = no clean WORSE and (a noisy/off BETTER or OOD-O BETTER); D_ADOPT = any clean WORSE; else SAME -> D default.
usage: python verdict.py <code dir> [eval root] [D tag] [H tag]"""
import json
import os
import subprocess
import sys

C = sys.argv[1]
R = sys.argv[2] if len(sys.argv) > 2 else "/data/harvest/out/dist8/eval"
DT = sys.argv[3] if len(sys.argv) > 3 else "f35_d"
HT = sys.argv[4] if len(sys.argv) > 4 else "f35_h"
SETS = ["x_dev", "x_ood_h", "x_ood_hl", "x_ood_d", "x_ood_o", "x_ood_s", "x_ood_t"]
rows = []
for s in SETS:
    for m in ("clean", "noisy", "off"):
        d = os.path.join(R, DT, f"{s}_d-min_{'clean' if m == 'off' else m}")
        h = os.path.join(R, HT, f"{s}_h-min_{m}")
        if not (os.path.exists(os.path.join(d, "scores.jsonl")) and os.path.exists(os.path.join(h, "scores.jsonl"))):
            continue
        out = subprocess.run([sys.executable, os.path.join(C, "tools/teach_pt/dist8_compare.py"), f"{s}_{m}", h, d, "2"],
                             capture_output=True, text=True).stdout.strip().splitlines()
        if out:
            rows.append(json.loads(out[-1]))
for r in rows:
    print(f"{r['name']:22s} n={r.get('n_pairs')} H={r.get('x_median')} D={r.get('y_median')} CI={r.get('diff_ci95')} "
          f"{r.get('verdict')} noninf={r.get('noninferior')}")
clean = [r for r in rows if r["name"].endswith("_clean")]
worse = [r["name"] for r in clean if not r.get("noninferior")]  # WORSE = not non-inferior at the 2 mm margin (prereg 3)
better_dep = [r["name"] for r in rows if not r["name"].endswith("_clean") and r.get("verdict") == "BETTER"]
better_o = [r["name"] for r in rows if r["name"].startswith("x_ood_o") and r.get("verdict") == "BETTER"]
v = "D_ADOPT" if worse else ("H_ADOPT" if (better_dep or better_o) else "SAME_D_DEFAULT")
print("VERDICT " + json.dumps({"verdict": v, "clean_worse": worse, "depth_degraded_better": better_dep,
                               "ood_o_better": better_o}))
