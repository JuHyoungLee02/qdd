"""E-GP2 follow-up (main 10-03): does the (a) label rot_bin_img match the camera of THAT call? For grasp rows of an E-GP2
build (truth_<split>.jsonl + the row file), recompute the image bin from the matched pick's contacts (grasp centre m,
closing axis c) and the call's own head camera (cams.json), with the producer's function grasp9.rot_img; also project m
to check the frame (pixel distance to the label point, 0-1000 scale). Reports agreement (exact / +-1) by step.
usage (pod python, PYTHONPATH = code dir): gp2_rotcheck.py <gp2 data dir> <split> [--n 400]"""
import json
import os
import sys
from collections import Counter

import numpy as np


def main():
    a = sys.argv[1:]
    d, split = a[0], a[1]
    n = int(a[a.index("--n") + 1]) if "--n" in a else 400
    from harvest.l9 import grasp9 as G
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gp2_build import pick_for
    truth = {}
    for x in open(os.path.join(d, f"truth_{split}.jsonl")):
        t = json.loads(x)
        truth.setdefault(t["id"], t)
    rows = {}
    for x in open(os.path.join(d, f"l9_{split}_a.jsonl"), encoding="utf-8"):
        r = json.loads(x)
        if r["id"] in truth and r["id"] not in rows:
            rows[r["id"]] = r
    ids = sorted(rows)[:: max(1, len(rows) // n)][:n]
    c, px, by = Counter(), [], Counter()
    metas = {}
    for i in ids:
        r = rows[i]
        ep = os.path.dirname(os.path.dirname(r["call_dir"]))
        if ep not in metas:
            metas[ep] = json.load(open(os.path.join(ep, "meta.json")))
        p = pick_for(r, metas[ep]["grasp_v2"].get("picks") or [])
        if p is None or not p.get("contacts_world"):
            c["no_pick"] += 1
            continue
        c1, c2 = np.asarray(p["contacts_world"][0], float), np.asarray(p["contacts_world"][1], float)
        m, ax = (c1 + c2) / 2, (c2 - c1) / max(np.linalg.norm(c2 - c1), 1e-9)
        cam = json.load(open(r["cams_path"]))["head"]
        K = np.array([[cam["fx"], 0, cam["cx"]], [0, cam["fy"], cam["cy"]], [0, 0, 1.0]])
        R, t = np.asarray(cam["R"], float), np.asarray(cam["t"], float)
        _, b = G.rot_img(m, ax, K, R, t)
        uv, z = G.project(K, R, t, m)
        lab = truth[i]["rot_bin_img"]
        e = min((b - lab) % 12, (lab - b) % 12)
        st = truth[i]["step"]
        by[(st, "n")] += 1
        by[(st, "exact")] += e == 0
        by[(st, "pm1")] += e <= 1
        pt = json.loads(r["answer"])["command"].get("point_2d")
        if pt and z[0] > 0:
            px.append(float(np.hypot(uv[0, 0] / cam["W"] * 1000 - pt[0], uv[0, 1] / cam["H"] * 1000 - pt[1])))
    res = {"checked": sum(v for k, v in by.items() if k[1] == "n"), **dict(c),
           "by_step": {s: {"n": by[(s, "n")], "exact": round(by[(s, "exact")] / max(by[(s, "n")], 1), 3),
                           "pm1": round(by[(s, "pm1")] / max(by[(s, "n")], 1), 3)} for s in sorted({k[0] for k in by})},
           "centre_vs_label_point_n1000": {"median": round(float(np.median(px)), 1) if px else None,
                                           "p90": round(float(np.percentile(px, 90)), 1) if px else None}}
    print(json.dumps(res))


if __name__ == "__main__":
    main()
