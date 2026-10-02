"""L9 v2 diagnosis: is the place height right when the place is an OBJECT (stacking onto a block / book / box)?
(pure; needs the catalog json of the code dir)
usage: python tools/l9/diag/place_top_check.py <catalog objects_l9.json> <collect root> [...] [--since EPOCH] [--all]
Per v2 episode and placed target whose place is a catalog object resting on the table (labels 'gt'): the catalog top
(table_z + catalog height, what labels.place_top uses for objects) vs the live top estimate (2 * place centre z - table_z,
the object's real vertical size as it rests), their difference, the episode result and tipped flag."""
import glob
import json
import os
import sys
from collections import Counter


def main():
    a = sys.argv[1:]
    cat = json.load(open(a[0]))["objects"]
    since = float(a[a.index("--since") + 1]) if "--since" in a else 0.0
    c = Counter()
    for root in [x for x in a[1:] if os.path.isdir(x)]:
        for m in glob.glob(os.path.join(root, "**", "meta.json"), recursive=True):
            if os.path.getmtime(m) < since:
                continue
            meta = json.load(open(m))
            if meta.get("grasp_v2") is None:
                continue
            ep = os.path.dirname(m)
            labs = [json.loads(l) for l in open(os.path.join(ep, "labels.jsonl"))]
            res = json.load(open(os.path.join(ep, "result.json"))) if os.path.exists(os.path.join(ep, "result.json")) else {}
            seen = set()
            for l in labs:
                pl, tg = l.get("place"), l.get("tgt")
                if pl not in cat or (tg, pl) in seen or not l.get("gt"):
                    continue
                seen.add((tg, pl))
                tz = float(l.get("table_z") or meta.get("table_z"))
                pz = float(l["gt"]["place"][2])
                live = 2 * pz - tz
                if abs(pz - tz) > 0.2:  # not resting on the main surface (shelf etc.): skip
                    continue
                cat_top = tz + float(cat[pl]["height"])
                d = cat_top - live
                ok = bool(meta.get("success"))
                c[("|d|>1cm" if abs(d) > 0.01 else "|d|<=1cm", ok)] += 1
                if abs(d) > 0.01 or "--all" in a:
                    print(f"{os.path.relpath(ep, root)[:55]:55s} ok={ok} tipped={res.get('tipped')} place {cat[pl].get('category', '')[:18]:18s} "
                          f"catalog top {cat_top:.3f} live top {live:.3f} diff {d * 100:+.1f} cm (catalog h {cat[pl]['height']:.3f}, "
                          f"live h {live - tz:.3f})")
    print("\n(place height error, episode ok): n", dict(c))


if __name__ == "__main__":
    main()
