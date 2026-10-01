"""AI Worker drawn head camera (pilot) vs production standard camera on the same (definition, arm) strata: end
reasons, label-row drops by reason, rows kept per episode, and the pilot failures by head geometry bin.
usage: python tools/l9r/pilot_compare.py <pilot run dir> <production collect root>"""
import glob
import json
import os
import sys
from collections import Counter, defaultdict


def eps(root):
    for m in glob.glob(os.path.join(root, "**", "meta.json"), recursive=True):
        try:
            d = json.load(open(m))
        except (OSError, ValueError):
            continue
        if d.get("gen") == "l9" and (d.get("robot") or "ffw_sg2") == "ffw_sg2":
            yield os.path.dirname(m), d


def drops(ep):
    c = Counter()
    try:
        for x in open(os.path.join(ep, "labels.jsonl")):
            c[json.loads(x).get("drop") or "kept"] += 1
    except OSError:
        pass
    return c


def main():
    run, prod = sys.argv[1], sys.argv[2]
    pil = [(e, d) for e, d in eps(os.path.join(run, "collect")) if ((d.get("head_cam") or {}).get("draw") or {}).get("mode") == "rand"]
    want = {(d["task_id"], d["arm"]) for _, d in pil}
    base = [(e, d) for e, d in eps(prod) if (d["task_id"], d["arm"]) in want and d.get("motion_version") == "l9m-2"]
    out = {}
    for name, grp in (("pilot_rand", pil), ("prod_std", base)):
        dc, er = Counter(), Counter()
        for e, d in grp:
            dc.update(drops(e))
            er[str(d.get("end_reason"))] += 1
        n = len(grp)
        tot = sum(dc.values())
        out[name] = {"n": n, "success": round(sum(bool(d.get("success")) for _, d in grp) / n, 3),
                     "end_reason": {k: round(v / n, 3) for k, v in er.most_common()},
                     "label_rows_per_ep": round(tot / n, 1),
                     "drop_share": {k: round(v / tot, 3) for k, v in dc.most_common()}}
    by = defaultdict(lambda: [0, 0])
    for e, d in pil:
        h = d["head_cam"]
        for k, v, cut in (("pitch", h["pitch_deg"], 45), ("height", h["height_above_surface_m"], 0.55), ("hfov", h["hfov_deg"], 80)):
            key = f"{k}_{'hi' if v >= cut else 'lo'}"
            by[key][0] += 1
            by[key][1] += bool(d.get("success"))
    out["pilot_success_by_bin"] = {k: [n, round(s / n, 3)] for k, (n, s) in sorted(by.items())}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
