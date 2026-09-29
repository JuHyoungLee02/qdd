"""R2 planner-demo reference for the closed-loop diagnosis (CPU): per phase of the E-MA2 / E-SR1c training rows
(stage-B rows + labels_v2), the recorded gripper width (action_exec[:, 7]) vs the T1 open threshold 80.5 mm, the
phase duration per episode, and the sub-goal geometry (labels_v2 delta_m / goal_m) at the end of 'approach'.
  python tools/vla_alone/demo_ref.py --root /data/harvest/data/ma2/view --out demo_ref.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from collections import defaultdict

import numpy as np

TH_W = 0.08050180748425541


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/data/harvest/data/ma2/view")
    ap.add_argument("--task", default="mug_tray")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = {}
    for var in ("standard", "dr"):
        wmin = defaultdict(list)
        below = defaultdict(int)
        rows_n = defaultdict(int)
        ph_k = defaultdict(lambda: defaultdict(list))
        lab = {}
        for p in sorted(glob.glob(os.path.join(a.root, var, a.task, "P*.labels_v2.jsonl"))):
            for x in open(p, encoding="utf-8"):
                r = json.loads(x)
                lab[(r["kind"], r["seed"], r["k"])] = r["labels_v2"]
        for p in sorted(glob.glob(os.path.join(a.root, var, a.task, "P?.stageb.jsonl"))):
            for x in open(p, encoding="utf-8"):
                r = json.loads(x)
                ph = r.get("phase_id")
                w = np.asarray(r["action_exec"], float)[:, 7]
                wmin[ph].append(float(w.min()))
                below[ph] += int((w < TH_W).any())
                rows_n[ph] += 1
                ph_k[(r["kind"], r["seed"])][ph].append(r["k"])
        dur = defaultdict(list)
        for ep, d in ph_k.items():
            for ph, ks in d.items():
                dur[ph].append((max(ks) - min(ks) + 10) / 30.0)
        # height of the approach goal above the grasp point: labels_v2 of the last approach row per episode
        goal_dz = []
        for (kind, seed), d in ph_k.items():
            ks = d.get("approach")
            if not ks:
                continue
            nxt = [k for ph, kk in d.items() if ph != "approach" for k in kk if k > max(ks)]
            if nxt:
                lv = lab.get((kind, seed, min(nxt)))
                if lv and lv.get("motion_phase") == "grasp":
                    goal_dz.append(float(lv["delta_m"][2]))
        out[var] = {
            "rows": dict(rows_n),
            "w_min_mm": {ph: round(1e3 * float(np.min(v)), 1) for ph, v in wmin.items()},
            "rows_with_w_below_open": dict(below),
            "phase_dur_s_median": {ph: round(float(np.median(v)), 2) for ph, v in dur.items()},
            "phase_dur_s_p90": {ph: round(float(np.percentile(v, 90)), 2) for ph, v in dur.items()},
            "descend_dz_at_grasp_start_mm_median": round(1e3 * float(np.median(goal_dz)), 1) if goal_dz else None,
            "n_eps": len(ph_k),
        }
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
