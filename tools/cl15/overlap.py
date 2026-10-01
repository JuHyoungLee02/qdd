"""E-CL15 environment overlap check (docs/stage3/prereg_cl15.md §2; pod, venv_train, PYTHONPATH=code).
Training side: every episode folder of the main35 training rows (train_main35.jsonl images -> episode dir ->
scene.json: furniture.room, randomization.hdr.name; materials by the split rule). T1 side: the held-out pools the
T1 runner can draw (fx.rooms_of(.., "ood"), materials split "ood" incl. HDRIs) and what it actually drew
(<root>/res/env_used.jsonl). PASS = every intersection empty. -> <root>/overlap.json"""
from __future__ import annotations

import json
import os
import sys

TRAIN = "/data/harvest/out/main35/data/train_main35.jsonl"
ROOT = "/data/harvest/out/cl15"


def main():
    sys.path.insert(0, os.environ.get("CODE", "."))
    from harvest.sim.assets_x import materials as M
    from harvest.teach_l8d import clutter_x as CX
    from harvest.teach_l8d import fx
    eps = set()
    n_rows = 0
    for ln in open(TRAIN):
        n_rows += 1
        r = json.loads(ln)
        for im in r.get("images") or []:
            if "/calls/" in im:
                eps.add(im.split("/calls/")[0])
                break
    rooms_tr, hdr_tr, kinds_tr, miss = set(), set(), set(), 0
    for d in eps:
        try:
            s = json.load(open(os.path.join(d, "scene.json")))
        except OSError:
            miss += 1
            continue
        f = s.get("furniture") or {}
        if f.get("room"):
            rooms_tr.add(f["room"] if isinstance(f["room"], str) else (f["room"] or {}).get("name"))
        h = ((s.get("randomization") or {}).get("hdr") or {}).get("name")
        if h:
            hdr_tr.add(h)
        if f.get("kind"):
            kinds_tr.add(f["kind"])
    d = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(fx.__file__))), "sim", "assets_x")
    rooms_ood = set(fx.rooms_of(d, "ood"))
    cat = {k: r for k, r in M.usable(M.load()).items() if CX.material_ok(k, r)}
    hdr_ood = {os.path.basename(p) for p in M.hdr_paths(cat, "ood")}
    mat_ood = {k for k, r in cat.items() if r["role"] != "env" and M.split_of(k) == "ood"}
    mat_train_rule = {k for k, r in cat.items() if r["role"] != "env" and M.split_of(k) == "train"}
    used = {"rooms": set(), "hdr": set(), "materials": set()}
    p = os.path.join(ROOT, "res", "env_used.jsonl")
    if os.path.exists(p):
        for ln in open(p):
            u = json.loads(ln)
            for k in used:
                used[k].update(u.get(k) or [])
    out = {"train_rows": n_rows, "train_episode_dirs": len(eps), "scene_json_missing": miss,
           "train_rooms": len(rooms_tr), "train_hdr": len(hdr_tr), "train_furniture_kinds": sorted(kinds_tr),
           "train_rooms_split_ood": sorted(r for r in rooms_tr if fx.room_split(r) == "ood"),
           "train_hdr_split_ood": sorted(h for h in hdr_tr if h in hdr_ood),
           "pool_rooms_ood": len(rooms_ood), "pool_hdr_ood": len(hdr_ood), "pool_materials_ood": len(mat_ood),
           "rooms_overlap": sorted(rooms_ood & rooms_tr), "hdr_overlap": sorted(hdr_ood & hdr_tr),
           "materials_overlap_by_rule": sorted(mat_ood & mat_train_rule),
           "used": {k: sorted(v) for k, v in used.items()},
           "used_rooms_in_train": sorted(used["rooms"] & rooms_tr),
           "used_hdr_in_train": sorted(used["hdr"] & hdr_tr),
           "used_materials_not_ood": sorted(m for m in used["materials"] if M.split_of(m) != "ood")}
    keys = ("train_rooms_split_ood", "train_hdr_split_ood", "rooms_overlap", "hdr_overlap",
            "materials_overlap_by_rule", "used_rooms_in_train", "used_hdr_in_train", "used_materials_not_ood")
    out["PASS"] = not any(out[k] for k in keys) and len(rooms_ood) > 0 and len(hdr_ood) > 0
    json.dump(out, open(os.path.join(ROOT, "overlap.json"), "w"), indent=1)
    print(json.dumps({k: (v if not isinstance(v, list) or len(v) < 12 else f"{len(v)} items")
                      for k, v in out.items() if k != "used"}))


if __name__ == "__main__":
    main()
