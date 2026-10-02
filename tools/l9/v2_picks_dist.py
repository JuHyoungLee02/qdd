"""Chosen grasp distribution of L9 v2 episodes (pure): approach family, part, label rule, arm, per robot, for successes
(default) or all episodes since an epoch. Natural-grasp checks: top share <= 50 % (spec 12.8).
usage: python tools/l9/v2_picks_dist.py <collect root>... [--since EPOCH] [--all]"""
import glob
import json
import os
import sys
from collections import Counter, defaultdict


def main():
    a = sys.argv[1:]
    since = float(a[a.index("--since") + 1]) if "--since" in a else 0.0
    every = "--all" in a
    roots = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or not a[i - 1].startswith("--"))]
    fam, part, rule, arm = defaultdict(Counter), defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
    none = defaultdict(Counter)
    for root in roots:
        for m in glob.glob(os.path.join(root, "**", "meta.json"), recursive=True):
            if os.path.getmtime(m) < since:
                continue
            meta = json.load(open(m))
            if meta.get("grasp_v2") is None or not (every or meta.get("success")):
                continue
            r = meta.get("robot", "?")
            arm[r][meta.get("arm")] += 1
            for p in meta.get("picks") or (meta.get("grasp_v2") or {}).get("picks") or []:
                fam[r][p.get("family")] += 1
                part[r][p.get("part")] += 1
                rule[r][p.get("approach_reason")] += 1
                if p.get("part") is None:  # label gap: which picks have no grasp part
                    none[r][(p.get("approach_reason"), p.get("label_rule"), p.get("category"))] += 1
    out = {}
    for r in fam:
        n = sum(fam[r].values())
        out[r] = {"picks": n, "family": dict(fam[r].most_common()),
                  "top_share": round(fam[r].get("top", 0) / max(n, 1), 3), "part": dict(part[r].most_common()),
                  "approach_reason": dict(rule[r].most_common()), "arm_episodes": dict(arm[r]),
                  "part_none_by": {str(k): v for k, v in none[r].most_common(12)}}
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
