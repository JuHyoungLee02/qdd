"""E-DIST8 add-on packs (user-log 141: pixel on/off at every data level A / B / C). Three packs from the converted
open streams, each with explicit counts, and the equal-total rule.

  pixel pack   gated pixel streams (RB2 tracked gripper points / traces, MolmoAct OXE traces, MolmoBot RBY1 / Franka
               points) with answers normalised to 0-1000 of the image (x right, y down), 'frame: pixel', plus
               'not visible' negatives ({"visible": false}) from calibrated frames where the named gripper is out of view
  3D pack      BEHAVIOR metric 3-D QA from real depth / GT poses (obj_center_cam where the GT centre lands on its own
               mask, table_plane_cam passing the plane gate) + C' (Franka top-down, RoboTwin, RB2 camera-unknown)
  3D+pixel     3D pack + pixel pack (the same rows)
Equal totals: every E-DIST8 arm has the L8 epoch size T = 6,521 rows; an arm with add-on packs of sizes n1, n2 takes
base_take(T, [n1, n2]) = T - n1 - n2 base rows (random, seed 0, stratified by step when the base is L8 / L8-D).
usage (pod): python -m xemb.packs OUT_DIR
"""
from __future__ import annotations

import json
import os
import re
import sys

import numpy as np

_SIZE = re.compile(r"(\d+)x(\d+) px")
N1000 = ("\nAnswer in 0-1000 normalised image coordinates (x to the right, y down). If it is not visible, answer "
         "{\"visible\": false}.\nReturn JSON only.")


def size_of(prompt: str):
    m = _SIZE.search(prompt)
    return (int(m.group(1)), int(m.group(2))) if m else None


def _n(v, n):
    return int(round(float(v) * 1000.0 / n))  # Qwen-VL convention: x / W x 1000


def to_n1000(r: dict) -> dict:
    W, H = size_of(r["prompt"])
    a = json.loads(r["answer"])
    if "point" in a:
        a = {"point": [_n(a["point"][0], W), _n(a["point"][1], H)]}
    elif "trace" in a:
        a = {"trace": [[_n(u, W), _n(v, H)] for u, v in a["trace"]]}
    elif "points" in a:
        a = {"points": [[_n(u, W), _n(v, H)] for u, v in a["points"]]}
    p = r["prompt"].replace("\nReturn JSON only.", N1000)
    return dict(r, prompt=p, answer=json.dumps(a), coords="n1000")


def negative(r: dict, image: str, rid: str) -> dict:
    return dict(r, id=rid, images=[image], answer=json.dumps({"visible": False}),
                prompt=r["prompt"].replace("\nReturn JSON only.", N1000), coords="n1000", negative=True)


def base_take(total: int, packs: list) -> int:
    return int(total - sum(packs))


def _rows(path, kinds=None):
    base = os.path.dirname(os.path.dirname(os.path.abspath(path)))
    out = []
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        if kinds and (r.get("qa_kind") or r["kind"]) not in kinds:
            continue
        r["images"] = [p if os.path.isabs(p) else os.path.join(base, p) for p in r.get("images", [])]
        if all(os.path.exists(p) for p in r["images"]):
            out.append(r)
    return out


def _take(rows, n, rng):
    return [rows[i] for i in rng.permutation(len(rows))[:n]]


def build(out, X="/data/harvest/out/xemb_proto", sizes=None, seed=0):
    rng = np.random.default_rng(seed)
    sizes = sizes or {"px_rb2_pt": 250, "px_rb2_tr": 150, "px_mact": 300, "px_rby1": 250, "px_franka": 220, "px_neg": 130,
                      "3d_obj": 1300, "3d_plane": 300, "c_franka": 500, "c_robotwin": 200, "c_rb2": 300}
    px = []
    px += [to_n1000(r) for r in _take(_rows(f"{X}/rb2/records_P.jsonl", ["ee_point_detected"]), sizes["px_rb2_pt"], rng)]
    px += [to_n1000(r) for r in _take(_rows(f"{X}/rb2/records_P.jsonl", ["ee_trace"]), sizes["px_rb2_tr"], rng)]
    px += [to_n1000(r) for r in _take(_rows(f"{X}/molmoact/records_P.jsonl"), sizes["px_mact"], rng)]
    px += [to_n1000(r) for r in _take(_rows(f"{X}/molmobot50/records_P.jsonl", ["ee_point", "obj_point", "place_point"]),
                                      sizes["px_rby1"], rng)]
    px += [to_n1000(r) for r in _take(_rows(f"{X}/mbfranka/records_P.jsonl", ["ee_point", "obj_point", "place_point"]),
                                      sizes["px_franka"], rng)]
    # negatives: MolmoBot RBY1 head frames where the named gripper is out of view (GT points all NaN)
    gt = json.load(open(f"{X}/point/gt.json"))
    tmpl = _rows(f"{X}/molmobot50/records_P.jsonl", ["ee_point"])[0]
    negs = []
    for key, g in gt.items():
        if not key.startswith("mb|"):
            continue
        pts = np.array(g["pts"], float)
        if (pts < 0).all():
            _, name, k, arm = key.split("|")
            img = f"{X}/point/img/mb_{name}_{int(k):04d}.jpg"
            if os.path.exists(img):
                p = re.sub(r"- Image 1: .*", "- Image 1: head camera, 1024x576 px; camera: unknown (no calibration).",
                           tmpl["prompt"])  # the template's calibration belongs to another frame: do not reuse it
                p = re.sub(r"Point to the \w+ gripper", f"Point to the {arm} gripper", p)
                t = dict(tmpl, prompt=p)
                negs.append(negative(t, img, f"neg_{name}_{k}_{arm}"))
    px += _take(negs, sizes["px_neg"], rng)
    d3 = []
    d3 += _take(_rows(f"{X}/behavior100/records_P.jsonl", ["obj_center_cam"]), sizes["3d_obj"], rng)
    d3 += _take(_rows(f"{X}/behavior100/records_P.jsonl", ["table_plane_cam"]), sizes["3d_plane"], rng)
    d3 += _take(_rows(f"{X}/mbfranka/records_C.jsonl"), sizes["c_franka"], rng)
    d3 += _take(_rows(f"{X}/robotwin2/records_C.jsonl"), sizes["c_robotwin"], rng)
    d3 += _take(_rows(f"{X}/rb2/records_C.jsonl"), sizes["c_rb2"], rng)
    os.makedirs(out, exist_ok=True)
    packs = {"pixel": px, "3d": d3, "3d_px": d3 + px}
    counts = {}
    for name, rows in packs.items():
        with open(os.path.join(out, f"{name}.jsonl"), "w", encoding="utf-8") as f:
            for i in rng.permutation(len(rows)):
                f.write(json.dumps(rows[i]) + "\n")
        counts[name] = {"rows": len(rows), "by_source": {}, "by_kind": {}}
        for r in rows:
            s, k = r.get("source", "?"), ("negative" if r.get("negative") else (r.get("qa_kind") or r["kind"]))
            counts[name]["by_source"][s] = counts[name]["by_source"].get(s, 0) + 1
            counts[name]["by_kind"][k] = counts[name]["by_kind"].get(k, 0) + 1
    T = 6521
    counts["equal_total_rule"] = {"T": T, "A_or_B": T, "A+px_or_B+px_base": base_take(T, [len(px)]),
                                  "C_base": base_take(T, [len(d3)]), "C+px_base": base_take(T, [len(d3), len(px)])}
    json.dump(counts, open(os.path.join(out, "counts.json"), "w"), indent=1)
    return counts


if __name__ == "__main__":
    print(json.dumps(build(sys.argv[1]), indent=1))
