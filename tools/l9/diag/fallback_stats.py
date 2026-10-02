"""L9 v2 diagnosis: fallback statuses and choice failures over all picks (pure).
usage: python tools/l9/diag/fallback_stats.py <collect root> [...] [--since EPOCH] [--robot NAME]
Counts: every fallback_trace status (per family), picks whose trace ended without a grasp (dead), choice_fail reasons,
and limit_rejects."""
import glob
import json
import os
import sys
from collections import Counter


def main():
    a = sys.argv[1:]
    since = float(a[a.index("--since") + 1]) if "--since" in a else 0.0
    robot = a[a.index("--robot") + 1] if "--robot" in a else None
    st, dead, cf, fam, lim, n_p = Counter(), Counter(), Counter(), Counter(), 0, 0
    for root in [x for x in a if os.path.isdir(x)]:
        for m in glob.glob(os.path.join(root, "**", "meta.json"), recursive=True):
            if os.path.getmtime(m) < since:
                continue
            g = json.load(open(m)).get("grasp_v2")
            if g is None or (robot and g.get("robot_profile") != robot):
                continue
            for p in g.get("picks", []):
                n_p += 1
                tl = p.get("timeline") or {}
                tr = tl.get("fallback_trace", [])
                for x in tr:
                    st[x.get("status")] += 1
                    fam[(x.get("family"), x.get("status"))] += 1
                if tr and "outcome_close" not in tl:
                    dead[tr[-1].get("status")] += 1
                if p.get("choice_fail"):
                    cf[p["choice_fail"]] += 1
                lim += int(tl.get("limit_rejects", 0) or 0)
    print("picks", n_p, "limit_rejects", lim)
    print("statuses", st.most_common())
    print("dead picks by last status", dead.most_common())
    print("choice_fail", cf.most_common())
    print("by family", sorted(fam.items(), key=lambda x: -x[1])[:12])


if __name__ == "__main__":
    main()
