"""G split change 1 (user-log 172): of the RB2 G rows (records_verified_G.jsonl, ~5,485), keep ~1,500 in G and move the
rest to training, by EPISODE: episodes ordered by sha256('g172|rb2|<ep>') (hash stratification), taken until the G row
target is reached. Writes NEW files (old ones untouched: running experiments judge with the old G):
  <root>/rb2/records_verified_v2.jsonl    = old training rows + moved rows
  <root>/rb2/records_verified_G_v2.jsonl  = remaining G rows
  RB2_G_V2 episode list (gsplit reads it when GSPLIT_V != 1) + manifest json with a digest.
usage (pod): python -m xemb.gsplit_change1 POINTS_ROOT MANIFEST_OUT [TARGET_G_ROWS]"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys

from . import gsplit as GS


def ep_of(r):
    m = re.search(r"rb2_(\d+)_", str(r["id"]))
    return int(m.group(1)) if m else None


def main(root, man_out, target=1500):
    d = os.path.join(root, "rb2")
    g = [json.loads(x) for x in open(os.path.join(d, "records_verified_G.jsonl"))]
    tr = [json.loads(x) for x in open(os.path.join(d, "records_verified.jsonl"))]
    by = {}
    for r in g:
        by.setdefault(ep_of(r), []).append(r)
    order = sorted(by, key=lambda e: hashlib.sha256(f"g172|rb2|{e}".encode()).hexdigest())
    keep, n = [], 0
    for e in order:
        if n >= target:
            break
        keep.append(e)
        n += len(by[e])
    ks = set(keep)
    g2 = [r for r in g if ep_of(r) in ks]
    moved = [r for r in g if ep_of(r) not in ks]
    with open(os.path.join(d, "records_verified_v2.jsonl"), "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in tr + moved)
    with open(os.path.join(d, "records_verified_G_v2.jsonl"), "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in g2)
    json.dump(sorted(ks), open(GS.RB2_G_V2_FILE, "w"))
    man = {"change": "gsplit change 1 (user-log 172)", "rule": "RB2 G episodes ordered by sha256('g172|rb2|<ep>'), "
           f"kept until >= {target} G rows; the rest moved to training", "rb2_g_episodes_v2": sorted(ks),
           "rows": {"old_g": len(g), "new_g": len(g2), "moved_to_train": len(moved), "train_v2": len(tr) + len(moved)}}
    man["digest"] = hashlib.sha256(json.dumps(man["rb2_g_episodes_v2"]).encode()).hexdigest()[:16]
    json.dump(man, open(man_out, "w"), indent=1)
    print(json.dumps({k: man[k] for k in ("rows", "digest")}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], *(int(a) for a in sys.argv[3:4]))
