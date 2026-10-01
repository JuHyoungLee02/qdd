"""Where do the L9 grasp labels aim on hollow objects (cups / bowls / mugs ...)? (pure; pod venv python, PYTHONPATH=code)
For the episodes of a collect root: the target's catalog category / grasp width / opening, the 'descend_close' label
commands (TCP xy relative to the object's centre, TCP depth below its top), grasp retries, success.
usage: python tools/l9r/hollow_grasp.py <collect root> <out.json> [--max 3000]"""
import glob
import json
import os
import re
import sys
from collections import defaultdict

import numpy as np

HOLLOW = re.compile(r"bowl|mug|cup|vase|pot\b|pot$|bucket|basket|tray|goblet|pitcher|dish|jug|chalice|wastebasket|"
                    r"teapot|plate|planter|tankard|amphora|holder|container|glass|jar|bin\b|caddy|kettle|pan\b")


def main():
    root, out = sys.argv[1], sys.argv[2]
    mx = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 3000
    from harvest.l9 import assets9 as A9
    cat = {**A9.catalog("train")}
    metas = sorted(glob.glob(os.path.join(root, "**", "meta.json"), recursive=True))[:mx]
    rows = []
    for m in metas:
        d = os.path.dirname(m)
        try:
            meta = json.load(open(m))
            ep = json.load(open(os.path.join(d, "episode9.json")))["episode"]
            labs = [json.loads(x) for x in open(os.path.join(d, "labels.jsonl"))]
        except (OSError, ValueError, KeyError):
            continue
        if meta.get("gen") != "l9":
            continue
        tgt = ep["steps"][0][0]
        r = cat.get(tgt) or {}
        c = str(r.get("category", "l8s_primitive" if tgt.startswith("o") else "?"))
        dc = [x for x in labs if x.get("step") == "descend_close" and x.get("tgt") == tgt and x.get("answer")]
        offs, depth = [], []
        for x in dc:
            cmd = json.loads(x["answer"])["command"]
            p = cmd.get("position_m")
            if p is None:
                continue
            g = x["gt"]["tgt"]
            offs.append(float(np.hypot(p[0] - g[0], p[1] - g[1])))
            top = g[2] + float(r.get("height", 0.08)) / 2
            depth.append(top - p[2])
        rows.append({"cat": c, "hollow": bool(HOLLOW.search(c)), "grasp_width": r.get("grasp_width"),
                     "opening": (r.get("inside") or {}).get("opening_min_side"), "success": bool(meta.get("success")),
                     "n_descend_close": len(dc), "off_mm": [round(v * 1e3, 1) for v in offs[:3]],
                     "depth_mm": [round(v * 1e3, 1) for v in depth[:3]], "end": meta.get("end_reason")})
    agg = defaultdict(lambda: {"n": 0, "succ": 0, "retry": 0, "off": [], "w": []})
    for x in rows:
        w = x["grasp_width"] or 0
        k = ("hollow" if x["hollow"] else "solid") + ("_w>=9cm" if w >= 0.09 else "_w6-9cm" if w >= 0.06 else "_w<6cm")
        a = agg[k]
        a["n"] += 1
        a["succ"] += x["success"]
        a["retry"] += x["n_descend_close"] > 1
        a["off"] += x["off_mm"]
        a["w"].append(w)
    rep = {k: {"n": v["n"], "success": round(v["succ"] / v["n"], 3), "retry_share": round(v["retry"] / v["n"], 3),
               "label_off_centre_mm_p50_p95": [round(float(np.percentile(v["off"], q)), 1) for q in (50, 95)] if v["off"] else None,
               "width_cm_p50": round(100 * float(np.median(v["w"])), 1)} for k, v in sorted(agg.items())}
    top = defaultdict(lambda: [0, 0])
    for x in rows:
        if x["hollow"]:
            top[x["cat"]][0] += 1
            top[x["cat"]][1] += x["success"]
    rep["hollow_categories"] = {k: {"n": n, "success": round(s / n, 3)} for k, (n, s) in
                                sorted(top.items(), key=lambda kv: -kv[1][0])[:15]}
    rep["n_episodes"] = len(rows)
    json.dump({"summary": rep, "rows": rows}, open(out, "w"))
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
