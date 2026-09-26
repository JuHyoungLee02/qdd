"""Select graspable, commercially usable MolmoSpaces Objaverse objects (pure; objathor metadata + the Isaac arrow table).

Licence rule (L8X-assets, 2026-09-27): keep only licences that allow commercial use AND modified copies (MolmoSpaces
re-meshed every Objaverse model): CC0 / CC-BY / CC-BY-SA. Drop NC (MolmoSpaces commercial_safe) and ND (a modified
mesh is a derivative), and any missing / unknown licence.
Size rule (L8-D objset, fingers 107 mm open, top-down grasp): height 4.5-10 cm, the smaller horizontal side
1.6-9.0 cm, the larger <= 20 cm; pick-up objects only. OOD-O: 20 % of CATEGORIES by name hash (the whole category).
usage: python tools/l8x_assets/objv_select.py META.json.gz ARROW.json --stats
       python tools/l8x_assets/objv_select.py META.json.gz ARROW.json --out sel.json --per-cat 4 --max 400"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import Counter

ALLOWED = {"by", "by-sa", "cc0", "cc-by", "cc-by-sa", "cc0-1.0", "cc-by-4.0", "cc-by-sa-4.0", "by-4.0", "by-sa-4.0"}
H_RANGE = (0.045, 0.10)
W_RANGE = (0.016, 0.090)
L_MAX = 0.20
OOD_SHARE = 0.2
SKIP_WORDS = ("bullet", "knuckle", "gun", "pistol", "rifle", "grenade", "ammunition", "weapon", "knife", "blade",
              "dagger", "sword", "syringe", "cigarette")  # no weapons / sharp / drug props as task objects


def licence_of(r: dict) -> str:
    li = r.get("license_info") or {}
    return str(li.get("license") or "").strip().lower()


def cat_split(cat: str) -> str:
    h = int(hashlib.sha256(("l8x-ood-o-objv:" + cat).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return "ood_o" if h < OOD_SHARE else "train"


def dims(r: dict):
    """(height, small horizontal, large horizontal) in metres from boundingBox (z = height: THOR / objaverse
    records agree with the annotated height in cm; width / depth are often null for objaverse)."""
    bb = r.get("boundingBox") or {}
    h, w, d = (float(bb.get(k) or 0) for k in ("z", "x", "y"))
    return h, min(w, d), max(w, d)


def candidates(meta: dict, have: set):
    for uid, r in meta.items():
        if not r.get("isObjaverse") or ("objaverse_obja_" + uid + ".tar.zst") not in have:
            continue
        yield uid, r


def select(meta: dict, have: set, per_cat: int, max_n: int):
    out, why = {}, Counter()
    per = Counter()
    for uid, r in sorted(candidates(meta, have)):
        lic = licence_of(r)
        if lic not in ALLOWED:
            why["licence:" + (lic or "none")] += 1
            continue
        if r.get("primaryProperty") != "CanPickup" or r.get("onWall") or r.get("onCeiling"):
            why["not_pickup"] += 1
            continue
        h, w, L = dims(r)
        if not (H_RANGE[0] <= h <= H_RANGE[1] and W_RANGE[0] <= w <= W_RANGE[1] and L <= L_MAX):
            why["size"] += 1
            continue
        cat = str(r.get("category") or r.get("objectType") or "?").lower()
        if any(w in cat for w in SKIP_WORDS):
            why["skip_word"] += 1
            continue
        if per[cat] >= per_cat:
            why["per_cat_cap"] += 1
            continue
        per[cat] += 1
        out[uid] = {"uid": uid, "category": cat, "split": cat_split(cat), "license": lic,
                    "license_info": r.get("license_info"), "height": round(h, 4), "grasp_width": round(w, 4),
                    "length": round(L, 4), "mass": r.get("mass"), "description": r.get("description"),
                    "name_short": (r.get("description_short") or {}).get("two_words"),
                    "package": "objaverse_obja_" + uid + ".tar.zst"}
        if len(out) >= max_n:
            break
    return out, why


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("meta")
    ap.add_argument("arrow")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--per-cat", type=int, default=4)
    ap.add_argument("--max", type=int, default=400)
    a = ap.parse_args(argv)
    with gzip.open(a.meta, "rt") as f:
        meta = json.load(f)
    have = {r["path"] for r in json.load(open(a.arrow))}
    if a.stats:
        c = Counter(licence_of(r) or "none" for _, r in candidates(meta, have))
        print("objaverse objects with an Isaac USD:", sum(c.values()))
        print("licences:", c.most_common(20))
        k = next(u for u, _ in candidates(meta, have))
        print("example keys:", sorted(meta[k].keys()))
        ex = [r for _, r in candidates(meta, have) if r.get("primaryProperty") == "CanPickup"][:5]
        for r in ex:
            print({q: r.get(q) for q in ("category", "height", "width", "depth", "boundingBox", "scale", "max_dimension")})
        return
    sel, why = select(meta, have, a.per_cat, a.max)
    sp = Counter(v["split"] for v in sel.values())
    print("selected", len(sel), dict(sp), "categories", len({v["category"] for v in sel.values()}))
    print("dropped", why.most_common(12))
    if a.out:
        with open(a.out, "w") as f:
            json.dump(sel, f, indent=1)
        with open(a.out.replace(".json", "_packages.txt"), "w") as f:
            f.write("\n".join(v["package"] for v in sel.values()) + "\n")


if __name__ == "__main__":
    main()
