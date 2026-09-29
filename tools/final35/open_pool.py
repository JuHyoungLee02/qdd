"""Final 35B main-training open point pool + mix (controller 09-29): the verified full packs, point labels only, head
views only (wide / fisheye excluded), G rows removed and guarded, ids unique; mixed additively into the L8-X base with a
repeat cap. usage: python open_pool.py <base d-min jsonl> <out jsonl> [p 0.75] [max repeat 1.5]
Sources: RB2 records_verified_v2 (G change 1), BEHAVIOR, RB3, MolmoBot RBY1 (head), ManiSkill records_verified (the old
verified sets; E-POOLV8 WORSE, E-POOLV8-FIX WORSE -> kept), AgiBot v3 final 1,384 rows in place of agibot_p0 (controller
09-29; the swap alone was not tested separately — indirectly checked by E-C35 vs f35_d). Open rows = round(p x base), capped at
max_repeat x pool; prints rows per source, the open share and the repeat factor (also <out>.counts.json)."""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from xemb import gsplit as GS  # noqa: E402

X = "/data/harvest/out/xemb_proto/points"
SOURCES = {"rb2": f"{X}/rb2/records_verified_v2.jsonl", "behavior": f"{X}/behavior/records_verified.jsonl",
           "rb3": f"{X}/rb3/records_verified.jsonl", "molmobot_rby1": f"{X}/molmobot_rby1/records_verified.jsonl",
           "maniskill": f"{X}/maniskill/records_verified.jsonl", "agibot_v3": f"{X}/agibot_v3_verified/final_all.jsonl"}
EXCLUDE = f"{X}/exclude_wide_fisheye.txt"


def main(base_p, out_p, p=0.75, cap=1.5):
    excl = {x.strip() for x in open(EXCLUDE) if x.strip()}
    pool, srcs, seen, counts = [], [], set(), {}
    for name, path in SOURCES.items():
        rows = [json.loads(x) for x in open(path, encoding="utf-8")] if os.path.exists(path) else []
        c = {"file": path, "read": len(rows)}
        rows = [r for r in rows if r.get("answer") and r.get("images")]
        rows = [r for r in rows if r["id"] not in excl and r.get("view", "head") in ("head", None)]
        c["head_not_excluded"] = len(rows)
        rows, g = GS.split(rows)
        c["g_dropped"] = len(g)
        kept = []
        for r in rows:
            if r["id"] not in seen:
                seen.add(r["id"])
                kept.append(dict(r, kind="aux", aux_kind="open_" + r.get("qa_kind", "qa")))
        c["pool"] = len(kept)
        counts[name] = c
        pool += kept
        srcs += [name] * len(kept)
    GS.guard(pool, "final35 open pool")
    base = open(base_p, encoding="utf-8").read().splitlines()
    need = int(round(len(base) * p))
    need = min(need, int(round(cap * len(pool))))
    rng = np.random.default_rng(8)
    idx = np.concatenate([rng.permutation(len(pool)) for _ in range(need // len(pool) + 1)])[:need]
    used = {}
    for i in idx:
        src = srcs[int(i)]
        used[src] = used.get(src, 0) + 1
    rows = base + [json.dumps(pool[int(i)]) for i in idx]
    order = np.random.default_rng([8, 75]).permutation(len(rows))
    with open(out_p, "w", encoding="utf-8", newline="\n") as f:
        for i in order:
            f.write(rows[int(i)] + "\n")
    for name, c in counts.items():
        c["used"] = used.get(name, 0)
        c["repeat"] = round(c["used"] / c["pool"], 2) if c["pool"] else None
    summ = {"sources": counts, "pool": len(pool), "base": len(base), "open": need, "open_over_base": round(need / len(base), 3),
            "open_share_of_file": round(need / len(rows), 3), "repeat": round(need / max(len(pool), 1), 3),
            "total": len(rows), "p_requested": p, "repeat_cap": cap}
    json.dump(summ, open(out_p + ".counts.json", "w"), indent=1)
    print(json.dumps(summ))


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], float(a[2]) if len(a) > 2 else 0.75, float(a[3]) if len(a) > 3 else 1.5)
