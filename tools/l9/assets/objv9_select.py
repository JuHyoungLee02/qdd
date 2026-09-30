"""L9 object candidates from the MolmoSpaces Objaverse subset (pure; objathor metadata + the Isaac arrow table).

Licence rule = tools/l8x_assets/objv_select.py (ALLOWED: CC0 / CC BY / CC BY-SA; no NC / ND / unknown) and its
SKIP_WORDS (+ L9_SKIP: weapons, anatomy, buildings, vehicles, furniture: not table-top objects).
Every candidate gets an L9 category (L9_CATS phrase match on the metadata category, then on the one-word description)
or "other"; containers (L9_PLACE) are kept whatever their primaryProperty, other objects must be CanPickup /
Moveable with a plausible table-top size (metadata box <= 0.45 m). The final size comes from the USD in
objv9_build.py (uniform rescale), so no size gate here.
Order: round-robin over the L9 categories (needed ones first, cap --cap per category), then "other" (cap --per-raw
per raw metadata category), so any prefix of the list (a batch) covers the categories evenly.
usage: python tools/l9/assets/objv9_select.py META.json.gz ARROW.json --out sel.json [--cap 700] [--per-raw 8]
       [--max 16000] [--exclude uid_list.json ...]"""
from __future__ import annotations

import argparse
import gzip
import json
import re
from collections import Counter, defaultdict

from tools.l8x_assets import objv_select as S

# L9 category -> phrases (matched as whole words in the metadata category / one-word description); order = priority
L9_CATS = {
    "pen_holder": ("pen holder", "pencil holder", "pencil cup", "pen cup", "desk organizer", "pen pot"),
    "utensil_holder": ("utensil holder", "utensil crock", "cutlery holder", "toothbrush holder", "brush holder"),
    "mug": ("mug", "tankard"),
    "cup": ("cup", "teacup", "tumbler", "drinking glass", "glass cup", "paper cup", "goblet", "chalice"),
    "bowl": ("bowl",),
    "plate": ("plate", "dish", "saucer", "platter"),
    "tray": ("tray",),
    "basket": ("basket", "hamper"),
    "bin": ("bin", "trash can", "garbage can", "wastebasket", "waste basket", "bucket", "pail", "dustbin"),
    "vase": ("vase", "amphora", "urn"),
    "bottle": ("bottle", "flask"),
    "can": ("can", "soda can", "tin can", "canned food", "tin"),
    "jar": ("jar", "canister", "container", "pot", "planter", "flowerpot", "flower pot", "pitcher", "jug", "teapot",
            "kettle"),
    "box": ("box", "crate", "carton", "chest", "case"),
    "block": ("block", "cube", "die", "dice", "brick", "domino"),
    "fruit": ("fruit", "apple", "banana", "orange", "lemon", "lime", "pear", "peach", "strawberry", "grape", "grapes",
              "mango", "pineapple", "kiwi", "cherry", "plum", "avocado", "coconut", "pomegranate", "apricot",
              "watermelon", "melon", "fig", "papaya"),
    "vegetable": ("vegetable", "carrot", "tomato", "potato", "onion", "cucumber", "eggplant", "pepper", "bell pepper",
                  "broccoli", "cabbage", "lettuce", "corn", "garlic", "mushroom", "radish", "zucchini", "squash",
                  "pumpkin", "turnip", "beet", "cauliflower", "gourd"),
    "bread": ("bread", "loaf", "baguette", "croissant", "bun", "bagel", "pastry", "donut", "doughnut", "muffin",
              "cupcake", "pretzel", "toast", "cake", "cookie", "biscuit", "sandwich", "burger", "hamburger", "pie"),
    "spoon_fork": ("spoon", "fork", "spatula", "ladle", "chopsticks", "whisk", "teaspoon", "cutlery", "utensil",
                   "tongs"),
    "pen": ("pen", "pencil", "marker", "crayon", "highlighter", "fountain pen", "ballpoint pen", "paintbrush"),
    "flower": ("flower", "rose", "tulip", "sunflower", "daisy", "lily", "bouquet", "orchid", "flowers"),
    "toy": ("toy", "plush", "teddy bear", "action figure", "figurine", "rubber duck", "doll", "chess piece", "lego",
            "puppet", "yo-yo", "spinning top", "rubik"),
    "shoe": ("shoe", "sneaker", "boot", "sandal", "slipper", "high heel", "loafer", "clog"),
    "book": ("book", "notebook", "novel", "textbook", "diary", "journal", "booklet"),
}
L9_PLACE = ("pen_holder", "utensil_holder", "mug", "cup", "bowl", "plate", "tray", "basket", "bin", "vase", "box",
            "jar")
NOT_PHRASES = ("license plate", "armor plate", "plate armor", "metal plate", "name plate", "nameplate", "plate carrier",
               "forklift", "pitchfork", "cupboard", "cup holder", "trophy", "bin bag", "case fan", "pencil case",
               "satellite dish", "dish antenna", "box truck", "boxing", "gearbox", "jukebox", "mailbox", "fuse box",
               "electrical box", "control box", "pan pipe", "tin soldier", "cake stand", "dice tower", "chest plate",
               "chest armor", "treasure chest", "chest of drawers", "cell block", "engine block", "cinder block",
               "stone block", "bricks", "brick wall", "toy gun", "toy sword", "toy tank", "toy rifle")
HARD_SKIP = ("gun", "rifle", "firearm", "revolver", "shotgun", "axe", "mace", "spear", "crossbow", "machete",
             "scythe", "war hammer", "warhammer", "cannon", "turret", "missile", "bomb", "ammo", "arrowhead", "skull",
             "bone", "anatomical", "skeleton", "fossil", "jawbone", "organ", "heart model", "brain", "weapon",
             "katana", "nsfw", "cigar", "bong", "alcohol", "beer", "wine", "whiskey", "vodka", "insect", "spider")
L9_SKIP = ("building", "architectur", "terrain", "landscape", "topograph", "house", "shed", "greenhouse", "monument",
           "tombstone", "gravestone", "column", "archway", "roof", "door", "window", "wall", "ceiling", "fence",
           "barrier", "street", "lamp post", "signpost", "vehicle", "car", "truck", "van", "airplane", "aircraft",
           "helicopter", "tank", "spaceship", "spacecraft", "satellite", "rocket", "drone", "submarine", "ship",
           "boat", "person", "human", "man", "woman", "mannequin", "character", "creature", "table", "chair", "sofa",
           "couch", "cabinet", "shelf", "shelving", "dresser", "bed", "desk", "television", "arcade", "vending",
           "toilet", "bathtub", "fountain", "hydrant", "rock formation", "relief", "slab", "panel", "plaque",
           "emblem", "logo", "sign", "flag", "painting", "artwork", "poster", "chandelier", "ceiling fan",
           "pendant light", "floor lamp", "street lamp", "tree", "bush", "statue", "bust", "tire", "wheel",
           "barrel", "drum", "machine", "engine", "generator", "air conditioning", "shipping container", "piano",
           "guitar", "motorcycle", "bicycle", "scooter", "stroller", "cart", "wagon", "pallet", "ladder", "hat",
           "helmet", "armor", "shield", "dress", "shirt", "jacket", "pants", "clothing", "t-shirt", "costume",
           "pipe")
SIZE_MAX = 0.45  # metadata box, metres: larger things are not table-top objects (plates / trays / bins may be 0.45)
TOY_OVERRIDE = ("toy", "figurine", "plush", "miniature")


def words(s: str) -> str:
    return " " + re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip() + " "


def has(text: str, phrase: str) -> bool:
    return (" " + phrase + " ") in text or (" " + phrase + "s ") in text or (" " + phrase + "es ") in text


def l9_category(raw: str, one: str) -> str | None:
    """-> L9 category, "other", or None (skip)."""
    t = words(raw)
    if any(has(t, p) for p in NOT_PHRASES):
        return None
    if any(w in t for w in S.SKIP_WORDS) or any(has(t, w) for w in HARD_SKIP):
        return None
    toyish = any(has(t, w) for w in TOY_OVERRIDE)
    if any(has(t, w) for w in L9_SKIP) and not toyish:
        return None
    for src in (t, words(one)):
        for cat, phrases in L9_CATS.items():
            if any(has(src, p) for p in phrases):
                return cat
    return "other"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("meta")
    ap.add_argument("arrow")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cap", type=int, default=700)
    ap.add_argument("--per-raw", type=int, default=8)
    ap.add_argument("--max", type=int, default=16000)
    ap.add_argument("--exclude", nargs="*", default=[], help="JSON tables whose objects[*].uid are skipped")
    a = ap.parse_args(argv)
    with gzip.open(a.meta, "rt") as f:
        meta = json.load(f)
    have = {r["path"] for r in json.load(open(a.arrow))}
    skip = set()
    for p in a.exclude:
        d = json.load(open(p))
        skip |= {str(o.get("uid")) for o in (d.get("objects") or {}).values()}
    by_cat, why = defaultdict(list), Counter()
    for uid, r in sorted(S.candidates(meta, have)):
        if uid in skip:
            why["existing"] += 1
            continue
        lic = S.licence_of(r)
        if lic not in S.ALLOWED:
            why["licence"] += 1
            continue
        if r.get("onWall") or r.get("onCeiling"):
            why["wall"] += 1
            continue
        raw = str(r.get("category") or r.get("objectType") or "?").lower()
        one = (r.get("description_short") or {}).get("one_word") or ""
        cat = l9_category(raw, one)
        if cat is None:
            why["skip_word"] += 1
            continue
        h, w, L = S.dims(r)
        if not (0.005 < h and L <= SIZE_MAX and h <= SIZE_MAX):
            why["size"] += 1
            continue
        if cat not in L9_PLACE and r.get("primaryProperty") not in ("CanPickup", "Moveable"):
            why["static"] += 1
            continue
        by_cat[cat].append((uid, r, raw, lic))
    # round-robin over L9 categories (hash order inside a category), then "other" with a per-raw cap
    import hashlib
    hk = lambda u: hashlib.sha256(("l9o:" + u).encode()).hexdigest()  # noqa: E731
    queues = {c: sorted(v, key=lambda x: hk(x[0]))[:a.cap] for c, v in by_cat.items() if c != "other"}
    other, per = [], Counter()
    for x in sorted(by_cat.get("other", []), key=lambda x: hk(x[0])):
        if per[x[2]] < a.per_raw:
            per[x[2]] += 1
            other.append(x)
    order = []
    i = 0
    while any(i < len(q) for q in queues.values()):
        for c in L9_CATS:
            q = queues.get(c, [])
            if i < len(q):
                order.append((c, q[i]))
        i += 1
    # interleave "other" 1:1 after the first pass so early batches also get variety
    mixed, oi = [], 0
    for k, item in enumerate(order):
        mixed.append(item)
        if k % 2 == 1 and oi < len(other):
            mixed.append(("other", other[oi]))
            oi += 1
    mixed += [("other", x) for x in other[oi:]]
    out = []
    for c, (uid, r, raw, lic) in mixed[:a.max]:
        h, w, L = S.dims(r)
        ds = r.get("description_short") or {}
        out.append({"uid": uid, "l9cat": c, "category": raw, "split": S.cat_split(raw), "license": lic,
                    "license_info": r.get("license_info"), "meta_hwl": [round(h, 4), round(w, 4), round(L, 4)],
                    "mass": r.get("mass"), "name_short": ds.get("two_words"), "one_word": ds.get("one_word"),
                    "primary": r.get("primaryProperty"), "package": "objaverse_obja_" + uid + ".tar.zst"})
    json.dump(out, open(a.out, "w"))
    with open(a.out.replace(".json", "_packages.txt"), "w") as f:
        f.write("\n".join(o["package"] for o in out) + "\n")
    print("selected", len(out), "dropped", why.most_common())
    print("pool", sorted(((c, len(v)) for c, v in by_cat.items()), key=lambda x: -x[1]))
    print("selected by cat", Counter(o["l9cat"] for o in out).most_common())


if __name__ == "__main__":
    main()
