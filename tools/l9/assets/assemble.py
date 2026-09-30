"""Assemble the committed L9 catalogs (pure) -> harvest/l9/assets9/{objects_l9,containers_l9,furniture_mesh_l9,
rooms_l9}.json + COUNTS.json.
objects_l9.json   "objects": the NEW L9 rows that passed the settle check (stable true), one per asset;
                  "l8s": references to the existing L8S rows that passed their checks (table, id, name, l9cat, role,
                  colour) -- load the full row from harvest/sim/assets_x/<table>.json.
containers_l9.json the L9 kinematic container rows with an inside and the container gate result (gate_pass,
                  gate_fits, gate_n, gate_inside) + "l8s" references to containers.json rows with gate_pass.
furniture_mesh_l9.json new pieces (THOR / Objaverse) + "l8s" references (assets_table / assets_ph / assets_cyclo).
rooms_l9.json      new ProcTHOR rooms (+ "l8s": rooms_ithor ids).
usage: python -m tools.l9.assets.assemble --repo REPO [--objects M.json ...] [--gate G.json ...]
       [--furniture F.json ...] [--rooms R.json ...] [--out-dir harvest/l9/assets9]"""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter

from tools.l9.assets.objv9_select import l9_category

TGT_H, TGT_W = (0.07, 0.10), (0.025, 0.085)


def dump(obj, path, max_mb=20):
    s = json.dumps(obj, separators=(",", ":"))
    if len(s) <= max_mb * 1e6 or "objects" not in obj:
        open(path, "w").write(s)
        return [path]
    ks = sorted(obj["objects"])
    n = int(len(s) // (max_mb * 1e6)) + 1
    out = []
    for i in range(n):
        part = dict(obj, objects={k: obj["objects"][k] for k in ks[i::n]}, shard=[i, n])
        p = path.replace(".json", f"_{i}.json")
        open(p, "w").write(json.dumps(part, separators=(",", ":")))
        out.append(p)
    return out


def l8s_objects(repo):
    refs = {}
    A = os.path.join(repo, "harvest/sim/assets_x")
    for t in ("objects_real", "products", "objects_objv", "task_items"):
        for k, o in json.load(open(os.path.join(A, t + ".json")))["objects"].items():
            ok = o.get("stable") if t != "task_items" else True
            if not ok:
                continue
            noun = str(o.get("noun") or o.get("category") or "")
            cat = l9_category(noun, noun) or "other"
            if o.get("role") == "pen":
                cat, role = "pen", "target"
            else:
                role = "target" if (TGT_H[0] <= o["height"] <= TGT_H[1] and TGT_W[0] <= o["grasp_width"] <= TGT_W[1]) \
                    else "clutter"
            col = o.get("colour")
            refs[f"{t}:{k}"] = {"table": f"harvest/sim/assets_x/{t}.json", "id": k, "name": o.get("name"),
                                "l9cat": cat, "role": role, "colour": "grey" if col == "gray" else col,
                                "license": o.get("license")}
    return refs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--objects", nargs="*", default=[])
    ap.add_argument("--gate", nargs="*", default=[])
    ap.add_argument("--furniture", nargs="*", default=[])
    ap.add_argument("--rooms", nargs="*", default=[])
    ap.add_argument("--out-dir", default="harvest/l9/assets9")
    a = ap.parse_args(argv)
    od = os.path.join(a.repo, a.out_dir)
    os.makedirs(od, exist_ok=True)
    A = os.path.join(a.repo, "harvest/sim/assets_x")
    counts = {}
    # objects + containers
    objs, conts, rule = {}, {}, None
    for p in a.objects:
        d = json.load(open(p))
        rule = d.get("stable_rule", rule)
        for k, o in d["objects"].items():
            if o.get("stable"):
                objs[k] = o
        for k, c in d.get("containers", {}).items():
            conts[k] = c
    gate = {}
    for p in a.gate:
        gate.update(json.load(open(p)))
    for k, c in list(conts.items()):
        g = gate.get(k)
        c.update(gate_pass=bool(g and g["pass"]), gate_fits=(g or {}).get("fits", []), gate_n=(g or {}).get("n"),
                 gate_inside=(g or {}).get("inside"), gate_hung=bool((g or {}).get("hung")))
        if not c.get("object_stable"):  # the container must also stand (its dynamic twin passed the settle check)
            conts.pop(k)
    l8s = l8s_objects(a.repo)
    if objs or a.objects:
        files = dump({"license_rule": "CC0 / CC BY / CC BY-SA only (no NC, no ND); per-object source / licence / "
                                      "attribution", "stable_rule": rule, "objects": objs, "l8s": l8s},
                     os.path.join(od, "objects_l9.json"))
        c8 = {k: c for k, c in json.load(open(os.path.join(A, "containers.json")))["containers"].items()
              if c.get("gate_pass")}
        dump({"license_rule": "as objects_l9", "gate": "tools/l9/assets/gate_containers9.py (drop test, >= 75 % "
              "inside)", "containers": conts,
              "l8s": {k: {"table": "harvest/sim/assets_x/containers.json", "id": k, "role": c.get("role")}
                      for k, c in c8.items()}}, os.path.join(od, "containers_l9.json"))
        cat = Counter(o["l9cat"] for o in objs.values()) + Counter(r["l9cat"] for r in l8s.values())
        counts["objects"] = {"l9_new_stable": len(objs), "l8s_passed": len(l8s), "total": len(objs) + len(l8s),
                             "target": 6000, "files": [os.path.basename(p) for p in files], "by_l9cat": dict(cat.most_common()),
                             "by_role": dict(Counter(o["role"] for o in objs.values())
                                             + Counter(r["role"] for r in l8s.values())),
                             "by_colour_l9": dict(Counter(o["colour"] for o in objs.values()).most_common())}
        gp = {k: c for k, c in conts.items() if c["gate_pass"]}
        counts["containers"] = {"l9_gate_pass": len(gp), "l9_with_inside_stable": len(conts), "l8s_gate_pass": len(c8),
                                "total_gate_pass": len(gp) + len(c8), "target": 300,
                                "by_kind": dict(Counter(c["role"] for c in gp.values()).most_common()),
                                "place_kind": dict(Counter(c["place_kind"] for c in gp.values()))}
    if a.furniture:
        fur, drop = {}, 0
        for p in a.furniture:
            d = json.load(open(p))
            fur.update(d["assets"])
        refs = {}
        for t in ("assets_table", "assets_ph", "assets_cyclo"):
            for k, r in json.load(open(os.path.join(A, t + ".json")))["assets"].items():
                refs[f"{t}:{k}"] = {"table": f"harvest/sim/assets_x/{t}.json", "id": k, "category": r["category"]}
        dump({"license_rule": "CC0 / CC BY / CC BY-SA / Apache only; per-piece licence / source", "assets": fur,
              "l8s": refs}, os.path.join(od, "furniture_mesh_l9.json"))
        counts["furniture_mesh"] = {"l9_new": len(fur), "l8s": len(refs), "total": len(fur) + len(refs),
                                    "target_mesh": 600, "by_category": dict(Counter(
                                        r["category"] for r in list(fur.values()) + list(refs.values())).most_common())}
    if a.rooms:
        rooms = {}
        for p in a.rooms:
            rooms.update(json.load(open(p))["rooms"])
        ith = json.load(open(os.path.join(A, "rooms_ithor.json")))
        dump({"license": "CC BY 4.0 (MolmoSpaces AI2-THOR assets) / Apache 2.0 (ProcTHOR-10k layouts)",
              "zone": ith["zone"], "rooms": rooms,
              "l8s": {k: {"table": "harvest/sim/assets_x/rooms_ithor.json", "id": k} for k in ith["rooms"]}},
             os.path.join(od, "rooms_l9.json"))
        counts["rooms"] = {"l9_new": len(rooms), "l8s": len(ith["rooms"]), "target_new": 150,
                           "by_kind": dict(Counter(r["kind"] for r in rooms.values()))}
    cp = os.path.join(od, "COUNTS.json")
    old = json.load(open(cp)) if os.path.exists(cp) else {}
    old.update(counts)
    mp = os.path.join(od, "materials_l9.json")
    if os.path.exists(mp):
        m = [r for r in json.load(open(mp))["materials"].values() if r["complete"]]
        old["materials"] = {"textures": sum(r["type"] == "textures" for r in m), "target": 650,
                            "by_role": dict(Counter(r["role"] for r in m if r["type"] == "textures")),
                            "hdris": sum(r["type"] == "hdris" for r in m), "target_hdri": 140,
                            "hdri_setting": dict(Counter(r.get("setting") for r in m if r["type"] == "hdris")),
                            "root": "/data/harvest/assets_l9/materials"}
    json.dump(old, open(cp, "w"), indent=1)
    print(json.dumps({k: {q: v for q, v in d.items() if not isinstance(v, (dict, list))} for k, d in old.items()}))


if __name__ == "__main__":
    main()
