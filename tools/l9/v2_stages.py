"""L9 v2 failure breakdown by stage (pure). Every failed episode gets ONE stage, the first that went wrong:
  approach   no grasp plannable / reachable (dead start, transit failure, every fallback failed)
  grasp      the close found nothing / not the object (EMPTY, WIDE without holding) and the episode never held it
  lift_carry it was held, then dropped / slipped / went off the table before any release
  place      it was released at the place but the task predicate failed (tipped, fell, off the spot) or the release
             loop never ended
  timeout    call / stage limit with no clearer stage
plus: steps (labels) of the last call, counts per stage and per task family, and the mm offset of the placed object
from the place target when available (labels 'gt').
usage: python tools/l9/v2_stages.py <collect root>... [--since EPOCH] [--robot ffw_sg2] [--clean]"""
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict

import numpy as np


def stage_of(meta: dict, steps: list, last_note: str) -> str:
    picks = (meta.get("grasp_v2") or {}).get("picks", [])
    held = any((p.get("timeline") or {}).get("outcome_lift") for p in picks) or "carry_up" in steps
    released = "lower_open" in steps
    end = meta.get("end_reason")
    if re.search(r"no (plannable|reachable) grasp|grasp pose is out of reach", last_note) or \
            (not held and steps[-2:] == ["above_target", "tipped"]):
        return "approach"
    if not held:
        if any((p.get("timeline") or {}).get("outcome_close") in ("EMPTY", "WIDE") for p in picks):
            return "grasp"
        return "approach" if end != "off_table" else "grasp"
    if held and not released:
        return "lift_carry" if end in ("off_table", "stop") else "timeout"
    if released:
        return "place"
    return "timeout"


def main():
    a = sys.argv[1:]
    since = float(a[a.index("--since") + 1]) if "--since" in a else 0.0
    robot = a[a.index("--robot") + 1] if "--robot" in a else None
    clean = "--clean" in a
    roots = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or not a[i - 1].startswith("--"))]
    st, fam_st = Counter(), defaultdict(Counter)
    n = ok = 0
    place_err = []
    for root in roots:
        for m in glob.glob(os.path.join(root, "**", "meta.json"), recursive=True):
            if os.path.getmtime(m) < since:
                continue
            meta = json.load(open(m))
            if meta.get("grasp_v2") is None or (robot and meta.get("robot") != robot) or \
                    (clean and meta.get("style") != "clean"):
                continue
            n += 1
            d = os.path.dirname(m)
            rows = [json.loads(x) for x in open(os.path.join(d, "labels.jsonl"))] if os.path.exists(
                os.path.join(d, "labels.jsonl")) else []
            steps = [r.get("step") for r in rows]
            if meta["success"] and (meta.get("max_dq_rad") or 0) <= 0.04:
                ok += 1
                continue
            calls = sorted(glob.glob(os.path.join(d, "calls", "c*")))
            note = ""
            if calls:
                t = open(os.path.join(calls[-1], "prompt.txt"), encoding="utf-8").read()
                h = [x for x in t.split("\n") if re.match(r"^\d+: ", x)]
                note = h[-1] if h else ""
            s = stage_of(meta, steps, note)
            if meta["success"]:
                s = "joint_step"
            st[s] += 1
            fam_st[meta.get("task_family")][s] += 1
            if s == "place" and rows:
                g = rows[-1].get("gt") or {}
                if g.get("tgt") and g.get("place"):
                    place_err.append(1000 * float(np.hypot(*(np.subtract(g["tgt"][:2], g["place"][:2])))))
    out = {"episodes": n, "success": ok, "yield": round(ok / max(n, 1), 3), "fail_stages": st.most_common(),
           "by_family": {f: dict(c) for f, c in fam_st.items()},
           "place_xy_offset_mm_median": round(float(np.median(place_err)), 1) if place_err else None}
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
