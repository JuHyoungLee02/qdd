"""Existing converted outputs -> point-only rows (xemb.pointlab; user-log 164/165). Sources and their projection gate:
  molmobot_rby1  molmobot50/records_P  obj_point / place_point / ee_point   exact sim camera (0 px)          ODC-BY
  molmobot_franka mbfranka/records_P   obj_point / place_point / ee_point   exact sim camera (0 px)          ODC-BY
  behavior       dh_full/behavior D (object = mask centroid, GT centre on mask) + behavior100 ee_point    MIT
  maniskill      dh_full/maniskill D (grasp point = TCP at first close, exact camera)                      (OXE, CC BY 4.0)
  rb2            rb2t4 ee_point (T4 camera) + dh_full/rb2 D grasp / place points (T4 camera)               Apache-2.0
  rb3            rb3t4v ee_point + dh_full/rb3 D (per-frame verified T4 <= 5 px)                           Apache-2.0
Point answers are read back to pixels, names re-cleaned with pointlab.clean_name (generic names dropped).
usage (pod): python -m xemb.to_points X_ROOT OUT_ROOT SOURCE [SOURCE ...]"""
from __future__ import annotations

import json
import os
import re
import sys

from . import pointlab as PL

_WH = re.compile(r"(\d+)x(\d+) px")
_PT = re.compile(r"Point to the (.+?) in image 1")
LIC = {"molmobot_rby1": "ODC-BY-1.0", "molmobot_franka": "ODC-BY-1.0", "behavior": "MIT", "maniskill": "CC BY 4.0",
       "rb2": "Apache-2.0", "rb3": "Apache-2.0"}
SRC = {"molmobot_rby1": "molmobot/rby1", "molmobot_franka": "molmobot/franka", "behavior": "behavior1k/r1pro",
       "maniskill": "oxe_maniskill/panda", "rb2": "robotis/ffw_bg2_rb2", "rb3": "robotis/ffw_bg2_rb3"}


def _rows(path):
    base = os.path.dirname(os.path.dirname(os.path.abspath(path)))
    for line in open(path):
        r = json.loads(line)
        r["images"] = [p if os.path.isabs(p) else os.path.join(base, p) for p in r["images"]]
        yield r


def _px(r):
    m = _WH.search(r["prompt"])
    W, H = int(m.group(1)), int(m.group(2))
    a = json.loads(r["answer"])
    p = a.get("point") or a.get("point_2d")
    if r.get("coords") == "n1000" or "point_2d" in a:
        return W, H, [p[0] * W / 1000.0, p[1] * H / 1000.0]
    return W, H, p


def _name(r):
    m = _PT.search(r["prompt"])
    if not m:
        return None
    n = re.sub(r"\s*\(.*?\)\s*$", "", m.group(1))
    return re.sub(r"'s TCP.*$", "", n)


def from_p(src, path, kinds, view="head"):
    out = []
    for r in _rows(path):
        k = r.get("qa_kind")
        if k not in kinds:
            continue
        W, H, uv = _px(r)
        arm = ""
        if k == "ee_point":
            m = re.search(r"(left|right) gripper", r["prompt"])
            arm = m.group(1) if m else ""
        x = PL.row(SRC[src], LIC[src], view, r["images"][0], W, H, uv, _name(r), k, f"{src}_{r['id']}", arm=arm)
        if x:
            out.append(x)
    return out


def from_d(src, path, view="head"):
    out = []
    for r in _rows(path):
        a = json.loads(r["answer"])
        k = {"grasp": "obj_point", "place": "place_point"}.get(a.get("height"), "obj_point")
        W, H, uv = _px(r)
        nm = re.sub(r" (where|that) .*$", "", _name(r) or "")
        x = PL.row(SRC[src], LIC[src], view, r["images"][0], W, H, uv, nm, k, f"{src}_{r['id']}")
        if x:
            out.append(x)
    return out


def build(X, src):
    F = f"{X}/dh_full" if os.path.exists(f"{X}/dh_full") else "/data/harvest/out/xemb/dh_full"
    if src == "molmobot_rby1":
        return from_p(src, f"{X}/molmobot50/records_P.jsonl", ("obj_point", "place_point", "ee_point"))
    if src == "molmobot_franka":
        return from_p(src, f"{X}/mbfranka/records_P.jsonl", ("obj_point", "place_point", "ee_point"))
    if src == "behavior":
        return from_d(src, f"{F}/behavior/records_D.jsonl") + from_p(src, f"{X}/behavior100/records_P.jsonl", ("ee_point",))
    if src == "maniskill":
        return from_d(src, f"{F}/maniskill/records_D.jsonl")
    if src == "rb2":
        return from_d(src, f"{F}/rb2/records_D.jsonl") + from_p(src, f"{X}/rb2t4/records_P.jsonl", ("ee_point",))
    if src == "rb3":
        return from_d(src, f"{F}/rb3/records_D.jsonl") + from_p(src, f"{X}/rb3t4v/records_P.jsonl", ("ee_point",))
    raise ValueError(src)


def main(X, out, srcs):
    for s in srcs:
        rows = build(X, s)
        d = os.path.join(out, s)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "records.jsonl"), "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in rows)
        rep = {"rows": len(rows), "by_kind": {}, "names": {}}
        for r in rows:
            rep["by_kind"][r["qa_kind"]] = rep["by_kind"].get(r["qa_kind"], 0) + 1
            if r.get("name"):
                rep["names"][r["name"]] = rep["names"].get(r["name"], 0) + 1
        rep["distinct_names"] = len(rep["names"])
        rep["names"] = dict(sorted(rep["names"].items(), key=lambda kv: -kv[1])[:20])
        json.dump(rep, open(os.path.join(d, "report.json"), "w"), indent=1)
        print(s, json.dumps({k: rep[k] for k in ("rows", "by_kind", "distinct_names")}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
