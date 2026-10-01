"""L9 v2 environment render-smoke rows (pure; run with the code whose families you want): every (family, rule) gets
`per` rows with a compatible task definition (tools/l9/plan.compat), arms alternating; rows are dealt to jobs of
`job_size` rows (one arm each), job k uses pool / rooms index `index0 + k` (a new room / mesh subset per job, as in
production).
usage: python tools/l9v2env/smoke_rows.py OUT.json [--per 1] [--families a,b] [--start 5000000] [--job-size 30]
       [--index0 700]"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from harvest.l9 import scene9 as S9  # noqa: E402
from harvest.l9 import task9 as T9  # noqa: E402
from tools.l9 import plan as PL  # noqa: E402

PREF = ("in_wide", "rel_left", "line2_y", "ins_one", "stack2", "up_to_higher")


def main():
    out = sys.argv[1]
    arg = lambda k, d: type(d)(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d  # noqa: E731
    per, start, size, idx0 = arg("--per", 1), arg("--start", 5000000), arg("--job-size", 30), arg("--index0", 700)
    fams = arg("--families", ",".join(S9.FAMILY_NAMES)).split(",")
    ft = PL.features(n_seeds=2)
    defs = list(T9.DEFS.values())
    rows, seed = [], start
    for f in fams:
        for r in S9.FAMILIES[f][1]:
            ok = [d for d in defs if PL.compat(d, ft[(f, r)])]
            if not ok:
                print("no def", f, r)
                continue
            ok.sort(key=lambda d: (d.id not in PREF, d.id))
            for j in range(per):
                d = ok[(seed + j) % min(len(ok), 6)]
                rows.append({"seed": seed, "arm": ("right", "left")[seed % 2], "family": f, "rule": r, "def": d.id,
                             "split": "train", "style": "clean"})
                seed += 1
    by = {"right": [r for r in rows if r["arm"] == "right"], "left": [r for r in rows if r["arm"] == "left"]}
    k = 0
    for arm in ("right", "left"):
        rs = by[arm]
        for i in range(0, len(rs), size):
            for r in rs[i:i + size]:
                r.update(job=f"s{k:03d}", pool=idx0 + k, rooms=idx0 + k)
            k += 1
    json.dump(rows, open(out, "w"), indent=0)
    print(json.dumps({"rows": len(rows), "jobs": k, "families": len(fams)}))


if __name__ == "__main__":
    main()
