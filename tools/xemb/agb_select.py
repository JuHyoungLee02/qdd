"""AgiBot World Beta task selection (user-log 163 step 2): keep tasks whose annotated action segments include a pick /
place / grasp skill; count their episodes and the observation bytes to fetch (from the HF listing). The G split takes
~10 % of the selected tasks by hash (gsplit rule, family 'agibot', group = task id) -- evaluation only.
usage (pod): python -m xemb.agb_select ROOT OUT_JSON"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

from . import gsplit as GS

SKILLS = re.compile(r"\b(pick|place|grasp|put)\b", re.I)


def main(root, outp):
    obs = {}
    for line in open(os.path.join(root, "list_observations.txt")):
        p = line.split()
        if len(p) == 2 and p[0].startswith("observations/"):
            obs.setdefault(p[0].split("/")[1], []).append((p[0], int(p[1])))
    out = {"tasks": {}, "rejected": {}}
    for f in sorted(glob.glob(os.path.join(root, "meta", "task_info", "task_*.json"))):
        tid = os.path.basename(f)[5:-5]
        eps = json.load(open(f))
        skills, texts, n_seg = {}, set(), 0
        for e in eps:
            for a in (e.get("label_info") or {}).get("action_config") or []:
                s = str(a.get("skill", ""))
                skills[s] = skills.get(s, 0) + 1
                if SKILLS.search(s) or SKILLS.search(str(a.get("action_text", ""))):
                    n_seg += 1
                texts.add(str(a.get("action_text", ""))[:80])
        pp = sum(v for k, v in skills.items() if SKILLS.search(k))
        rec = {"episodes": len(eps), "pick_place_segments": n_seg, "skills": skills,
               "task_name": (eps[0].get("task_name") if eps else None), "example_texts": sorted(texts)[:4],
               "obs_bytes": sum(s for _, s in obs.get(tid, [])), "obs_tars": [p for p, _ in obs.get(tid, [])]}
        if pp == 0 or not obs.get(tid):
            out["rejected"][tid] = {k: rec[k] for k in ("episodes", "skills", "task_name")}
            continue
        rec["g_split"] = GS.in_g({"id": f"agb_t{tid}_x", "source": "agibot/g1"})
        out["tasks"][tid] = rec
    sel = out["tasks"]
    out["summary"] = {"tasks": len(sel), "episodes": sum(r["episodes"] for r in sel.values()),
                      "obs_TB": round(sum(r["obs_bytes"] for r in sel.values()) / 1e12, 2),
                      "g_tasks": sorted(t for t, r in sel.items() if r["g_split"]),
                      "rejected_tasks": len(out["rejected"])}
    json.dump(out, open(outp, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(out["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
