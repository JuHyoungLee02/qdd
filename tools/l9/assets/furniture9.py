"""L9 furniture pieces (pod, pylib python: pxr + numpy): static copies + support surfaces, rows in the
assets_table.json format (category, top_kind, dst, src, collider_size, render_size, origin_offset,
render_vs_collider_mm, n_colliders, surfaces, split, license, source) + attribution / scale.
  thor   MolmoSpaces THOR furniture NOT in assets_table.json (seats, beds, sofas, fridges, toilets, washers,
         RoboTHOR IKEA pieces ...), CC BY 4.0: usd_import.make_static(mode thor) + inspect.
  objv   MolmoSpaces Objaverse furniture (licence rule of objv_select: CC0 / CC BY / CC BY-SA, SKIP_WORDS):
         select from the metadata (FURN_CATS), then per fetched package a uniform rescale so the height falls in
         the category's real range (objv9_build.write_scaled), make_static + inspect.
Curation = tools/l8x_assets/curate_thor.py rule: collider bbox vs render bbox <= 40 mm, height 0.25-2.5 m,
long side 0.25-3.5 m, at least one support surface above 5 cm. Split: 20 % "ood" by name hash (curate_thor).
usage: python -m tools.l9.assets.furniture9 thor OUT.json USD...
       python -m tools.l9.assets.furniture9 select META.json.gz ARROW.json SEL.json [--max 900]
       python -m tools.l9.assets.furniture9 objv SEL.json PKG_DIR OUT.json [--workers 12]"""
from __future__ import annotations

import gzip
import json
import os
import re
import sys
from collections import Counter
from multiprocessing import Pool

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

from tools.l8x_assets import curate_thor as CT  # noqa: E402

THOR_CAT = {  # regex (case-insensitive, on the variant name) -> (category, top_kind)
    r"arm_?chair": ("seat", "seat"), r"(office_)?chair": ("seat", "seat"), r"sofa": ("seat", "seat"),
    r"bed": ("bed", "bed"), r"fridge": ("appliance", "appliance_top"), r"toilet": ("toilet", "seat"),
    r"washing_machine|clothes_dryer": ("appliance", "counter"), r"safe": ("low", "low_table"),
    r"robothor_(side_)?table|robothor_coffee_table|robothor_dining_table": ("table", "table"),
    r"robothor_desk": ("table", "table"), r"robothor_(shelving_unit|bookcase|shelf)": ("shelf", "shelf_top"),
    r"robothor_(tv_stand|dresser|cabinet|chest)": ("shelf", "shelf_top"), r"robothor_(ottoman|stool|bench)": ("low",
                                                                                                       "low_table"),
}
FURN_CATS = {  # objaverse metadata category phrase -> (category, top_kind, height range m)
    "dining table": ("table", "table", (0.70, 0.78)), "kitchen table": ("table", "table", (0.70, 0.78)),
    "table": ("table", "table", (0.68, 0.78)), "desk": ("table", "table", (0.70, 0.77)),
    "work table": ("table", "table", (0.72, 0.92)), "workbench": ("table", "table", (0.80, 0.95)),
    "side table": ("side_table", "table", (0.45, 0.65)), "end table": ("side_table", "table", (0.45, 0.65)),
    "nightstand": ("side_table", "table", (0.45, 0.65)), "bedside table": ("side_table", "table", (0.45, 0.65)),
    "coffee table": ("low_table", "low_table", (0.35, 0.48)), "tv stand": ("shelf", "shelf_top", (0.40, 0.62)),
    "sideboard": ("counter", "counter", (0.75, 0.95)), "cabinet": ("counter", "counter", (0.75, 1.10)),
    "kitchen cabinet": ("counter", "counter", (0.85, 0.95)), "counter": ("counter", "counter", (0.85, 0.95)),
    "kitchen counter": ("counter", "counter", (0.85, 0.95)), "dresser": ("shelf", "shelf_top", (0.75, 1.10)),
    "chest of drawers": ("shelf", "shelf_top", (0.75, 1.10)), "drawer unit": ("shelf", "shelf_top", (0.55, 0.80)),
    "bookcase": ("shelf", "shelf_top", (0.80, 1.90)), "bookshelf": ("shelf", "shelf_top", (0.80, 1.90)),
    "shelving unit": ("shelf", "shelf_top", (0.80, 1.90)), "shelf": ("shelf", "shelf_top", (0.60, 1.80)),
    "storage cabinet": ("shelf", "shelf_top", (0.80, 1.60)), "console table": ("side_table", "table", (0.72, 0.85)),
    "stool": ("low", "low_table", (0.42, 0.75)), "bench": ("low", "low_table", (0.40, 0.50)),
    "ottoman": ("low", "low_table", (0.38, 0.46)), "kitchen island": ("counter", "counter", (0.88, 0.95)),
    "cart": None, "bar cart": None,
}
SOURCE_OBJV = "MolmoSpaces (allenai/molmospaces, isaac/objects/objaverse/20260128), Objaverse 1.0 (ODC-BY) models"
SOURCE_THOR = CT.SOURCE


def curate_row(name, r, cat, top, license_, source, extra=None):
    if "error" in r:
        return None, r["error"][:80]
    if r["render_vs_collider_mm"] > CT.MAX_RENDER_GAP_MM:
        return None, f"render_vs_collider {r['render_vs_collider_mm']} mm"
    sx, sy, sz = r["collider_size"]
    if not (0.25 <= sz <= 2.5 and 0.25 <= max(sx, sy) <= 3.5):
        return None, f"size {r['collider_size']}"
    surfs = [s for s in r["surfaces"] if s["top_z"] > 0.05]
    if not surfs:
        return None, "no_surface"
    row = {"category": cat, "top_kind": top, "dst": r["dst"], "src": r["src"], "collider_size": r["collider_size"],
           "render_size": r["render_size"], "origin_offset": r["origin_offset"],
           "render_vs_collider_mm": r["render_vs_collider_mm"], "n_colliders": r["n_colliders"], "surfaces": surfs,
           "split": CT.split_of(name), "license": license_, "source": source}
    row.update(extra or {})
    return row, None


def import_one(src):
    from harvest.sim.assets_x import usd_import as UI
    try:
        st = UI.make_static(src, mode="thor")
        return dict(src=src, **st, **UI.inspect(st["dst"]))
    except Exception as e:  # noqa: BLE001
        return {"src": src, "error": f"{type(e).__name__}: {e}"}


def thor(out, usds):
    keep, drop = {}, {}
    with Pool(12) as pool:
        for src, r in zip(usds, pool.imap(import_one, usds)):
            name = os.path.splitext(os.path.basename(src))[0]
            cat = next((v for k, v in THOR_CAT.items() if re.search(k, name, re.I)), None)
            if cat is None:
                drop[name] = "no_category"
                continue
            row, why = curate_row(name, r, cat[0], cat[1], "CC BY 4.0", SOURCE_THOR,
                                  {"attribution": "AI2-THOR / MolmoSpaces (CC BY 4.0)"})
            if row:
                keep["thor9_" + name] = row
            else:
                drop[name] = why
    json.dump({"license": "CC BY 4.0", "source": SOURCE_THOR, "assets": keep, "dropped": drop}, open(out, "w"))
    print("thor kept", len(keep), Counter(r["category"] for r in keep.values()), "dropped", len(drop),
          Counter(w.split(" ")[0] for w in drop.values()))


NOT_FURN = ("lamp", "cloth", "tennis", "clock", "tablet", "runner", "mat", "decor", "model", "miniature", "toy",
            "pool", "ping", "billiard", "set", "saw", "periodic", "top")


def fcat(raw: str):
    t = " " + re.sub(r"[^a-z0-9]+", " ", raw.lower()).strip() + " "
    if any(f" {w} " in t for w in NOT_FURN):
        return None
    for p in sorted(FURN_CATS, key=len, reverse=True):
        if f" {p} " in t or f" {p}s " in t:
            return FURN_CATS[p]
    return None


def select(meta_p, arrow_p, out, max_n=900):
    from tools.l8x_assets import objv_select as S
    meta = json.load(gzip.open(meta_p, "rt"))
    have = {r["path"] for r in json.load(open(arrow_p))}
    sel, per = [], Counter()
    import hashlib
    for uid, r in sorted(S.candidates(meta, have), key=lambda x: hashlib.sha256(("l9f:" + x[0]).encode()).hexdigest()):
        lic = S.licence_of(r)
        raw = str(r.get("category") or "").lower()
        if lic not in S.ALLOWED or any(w in raw for w in S.SKIP_WORDS):
            continue
        c = fcat(raw)
        if c is None or per[c[0]] >= max_n // 4:
            continue
        per[c[0]] += 1
        li = r.get("license_info") or {}
        sel.append({"uid": uid, "category_raw": raw, "category": c[0], "top_kind": c[1], "h_range": c[2],
                    "license": lic, "attribution": {"creator": li.get("creator_username"), "uri": li.get("uri")},
                    "package": "objaverse_obja_" + uid + ".tar.zst"})
        if len(sel) >= max_n:
            break
    json.dump(sel, open(out, "w"))
    open(out.replace(".json", "_packages.txt"), "w").write("\n".join(s["package"] for s in sel) + "\n")
    print("furniture candidates", len(sel), per)


def objv_one(args):
    s, pkg = args
    from pxr import Usd

    from harvest.sim.assets_x import usd_import as UI
    from tools.l9.assets.objv9_build import licence_name, write_scaled
    uid = s["uid"]
    d0 = os.path.join(pkg, s["package"].replace(".tar.zst", ""), "obja_" + uid)
    src = os.path.join(d0, f"obja_{uid}.usda")
    if not os.path.exists(src):
        return uid, None, "not fetched"
    try:
        lo, hi = UI.render_bbox(Usd.Stage.Open(src))
        h = float(hi[1] - lo[1])  # Y-up geometry
        a, b = s["h_range"]
        sc = 1.0 if a <= h <= b else ((a + b) / 2) / max(h, 1e-6)
        if not 0.05 <= sc <= 20:
            return uid, None, f"scale {sc:.2f}"
        use = src if sc == 1.0 else write_scaled(src, os.path.join(d0, f"obja_{uid}_l9f{int(round(sc * 1000))}.usda"),
                                                 sc)
        r = import_one(use)
        row, why = curate_row("objv_" + uid, r, s["category"], s["top_kind"], licence_name(s["license"]),
                              SOURCE_OBJV, {"attribution": s["attribution"], "scale": round(sc, 4),
                                            "category_raw": s["category_raw"], "uid": uid})
        return uid, row, why
    except Exception as e:  # noqa: BLE001
        return uid, None, f"{type(e).__name__}: {e}"[:120]


def objv(sel_p, pkg, out, workers=12):
    sel = json.load(open(sel_p))
    keep, drop = {}, {}
    with Pool(workers, maxtasksperchild=20) as pool:
        for uid, row, why in pool.imap(objv_one, [(s, pkg) for s in sel]):
            if row:
                keep["objvf_" + uid[:16]] = row
            else:
                drop[uid] = why
    json.dump({"license": "CC0 / CC BY / CC BY-SA per piece", "source": SOURCE_OBJV, "assets": keep, "dropped": drop},
              open(out, "w"))
    print("objv furniture kept", len(keep), Counter(r["category"] for r in keep.values()), "dropped", len(drop),
          Counter(w.split(" ")[0] for w in drop.values()).most_common(8))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "thor":
        thor(a[1], a[2:])
    elif a[0] == "select":
        select(a[1], a[2], a[3], int(a[5]) if len(a) > 5 else 900)
    else:
        objv(a[1], a[2], a[3], int(a[5]) if len(a) > 5 else 12)
