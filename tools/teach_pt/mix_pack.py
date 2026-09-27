"""E-DIST8 +px / C training files (prereg_dist8.md §1.2, change 3): the base arm file plus open-data pack rows so that
the packs make up the given share of all rows (the trainer's 816 steps then draw that share of samples). Pack rows
(作戦T qa_xemb, with their source: / frame: tags) become 'aux' rows (the trainer reads 'prompt' / 'images' /
'answer'); sampled without replacement, repeated when the pack is smaller than needed; seeded.
usage: python mix_pack.py <base jsonl> <out jsonl> <pack jsonl>:<share> [<pack jsonl>:<share> ...]"""
import json
import sys

import numpy as np

base_p, out_p = sys.argv[1], sys.argv[2]
packs = [(s.rsplit(":", 1)[0], float(s.rsplit(":", 1)[1])) for s in sys.argv[3:]]
base = open(base_p, encoding="utf-8").read().splitlines()
tot_share = sum(sh for _, sh in packs)
n_total = int(round(len(base) / (1 - tot_share)))
rng = np.random.default_rng(8)
out, counts = list(base), {"base_rows": len(base)}
for p, sh in packs:
    rows = [json.loads(x) for x in open(p, encoding="utf-8")]
    need = int(round(n_total * sh))
    idx = np.concatenate([rng.permutation(len(rows)) for _ in range(need // len(rows) + 1)])[:need]
    for i in idx:
        r = rows[int(i)]
        out.append(json.dumps(dict(r, kind="aux", aux_kind="open_" + r.get("qa_kind", "qa"))))
    counts[p] = {"pack_rows": len(rows), "used": need, "share": sh}
order = rng.permutation(len(out))
with open(out_p, "w", encoding="utf-8", newline="\n") as f:
    for i in order:
        f.write(out[int(i)] + "\n")
counts["total_rows"] = len(out)
json.dump(counts, open(out_p + ".counts.json", "w"), indent=1)
print(json.dumps(counts))
