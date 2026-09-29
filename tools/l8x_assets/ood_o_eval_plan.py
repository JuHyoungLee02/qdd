"""OOD-O closed-loop eval set (coordinator 09-29): >= 30 episodes of unseen real objects, from the frozen real OOD-O
list (prereg_l8d change 11: ood_o-split objects by name hash, passed the object gate, protected seeds 70160-70289,
plan4/plan_ood_real_b4.json), rendered with the L8S rules (drf, rooms, clutter 40, thor_low_table). Takes the first K
seeds per object, checks that no object appears in the L8S training plan / targets and that no seed overlaps the
existing OOD-O closed-loop episodes (smallcup_tray 70100-70139), writes the plan and a list.
usage: python tools/l8x_assets/ood_o_eval_plan.py PLAN_OOD.json TRAIN_PLAN.json TRAIN_TARGETS.json OUT_PLAN.json K"""
from __future__ import annotations

import json
import sys

OLD_OOD_O = range(70100, 70140)  # smallcup_tray closed-loop seeds (dist8 / strip8 / final35)


def main(argv=None):
    a = argv or sys.argv[1:]
    ood, train, targets = (json.load(open(p)) for p in a[:3])
    out, k = a[3], int(a[4])
    obj = lambda t: t.split("__", 1)[1]  # noqa: E731  ov_tray__<id>
    seen = {obj(r["task"]) for r in train if "__" in r["task"]}
    seen_txt = json.dumps(train) + json.dumps(targets)
    by = {}
    for r in sorted(ood, key=lambda r: r["seed"]):
        assert r["split"] == "ood_o" and 70160 <= r["seed"] <= 70289 and r["seed"] not in OLD_OOD_O, r
        by.setdefault(obj(r["task"]), []).append(r)
    bad = sorted(o for o in by if o in seen or o in seen_txt)
    if bad:
        raise SystemExit(f"objects in the training pool: {bad}")
    plan = [r for o in sorted(by) for r in by[o][:k]]
    json.dump(plan, open(out, "w"), indent=0)
    lst = {"n": len(plan), "n_objects": len(by), "per_object": k, "seeds": [r["seed"] for r in plan],
           "objects": sorted(by), "old_ood_o_overlap": [], "train_overlap": bad}
    json.dump(lst, open(out.replace(".json", "_list.json"), "w"), indent=1)
    print(json.dumps({k2: v for k2, v in lst.items() if k2 != "seeds"}))


if __name__ == "__main__":
    main()
