"""MolmoBot view tags (user decision, user-log 169): rows are tagged by the camera in the image name instead of 'head'.
  *_head                              -> view "head" (RBY1 head camera; prompt unchanged)
  *_randomized_zed2_* / droid_shoulder -> view "third", view_random True (random / shoulder third-person viewpoint;
                                          kept, a later 8B comparison decides), prompt 'head camera' -> 'camera'
  *_randomized_gopro_*                -> view "wide", exclude True, exclude_reason "wide_fisheye" (NOT trained on;
                                          rows are kept in place and listed in EXCLUDE_LIST, never deleted)
packs._rows and the training builders skip rows with exclude=True.
usage (pod): python -m xemb.mb_views FILE.jsonl [...]   (rewrites each file in place, appends ids to the exclude list)"""
from __future__ import annotations

import json
import os
import re
import sys

EXCLUDE_LIST = "/data/harvest/out/xemb_proto/points/exclude_wide_fisheye.txt"
_CAM = re.compile(r"_(randomized_gopro_analogue_\d+|randomized_zed2_analogue_\d+|droid_shoulder_light_randomization|"
                  r"head)(?:_\d+)?\.(?:jpg|png)$")


def tag(r: dict) -> dict:
    if not (str(r.get("source", "")).startswith("molmobot") or "/mb_" in str(r.get("images", [""])[0])
            or str(r.get("id", "")).startswith(("mb", "molmobot"))):
        return r
    m = _CAM.search(os.path.basename(r["images"][0]))
    if not m:
        return r
    cam = m.group(1)
    r = dict(r, camera=cam)
    if cam == "head":
        r["view"] = "head"
        return r
    r["prompt"] = r["prompt"].replace("head camera", "camera")
    if "gopro" in cam:
        r.update(view="wide", exclude=True, exclude_reason="wide_fisheye")
    else:
        r.update(view="third", view_random=True)
    return r


def main(paths):
    ex = []
    for p in paths:
        rows = [tag(json.loads(x)) for x in open(p, encoding="utf-8")]
        with open(p, "w", encoding="utf-8") as f:
            f.writelines(json.dumps(r) + "\n" for r in rows)
        n = {"head": 0, "third": 0, "wide_excluded": 0}
        for r in rows:
            v = r.get("view")
            if r.get("exclude"):
                n["wide_excluded"] += 1
                ex.append(r["id"])
            elif v in n:
                n[v] += 1
        print(p, json.dumps(n))
    with open(EXCLUDE_LIST, "a", encoding="utf-8") as f:
        f.writelines(i + "\n" for i in ex)


if __name__ == "__main__":
    main(sys.argv[1:])
