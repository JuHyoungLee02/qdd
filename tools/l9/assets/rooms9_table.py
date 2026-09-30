"""L9 rooms from MolmoSpaces ProcTHOR-10k houses (pod, pylib python: pxr + numpy). Same clear-zone rule and row format
as tools/l8x_assets/rooms_table.py (rooms_ithor.json): rooms.room_pose on the scene colliders (+ render mesh),
rooms.zone_is_clear re-check, render-only flattened copy (usd_import.make_visual, .usdc).
Only procthor-10k-{train,val,test}: AI2-THOR assets (the procthor-objaverse / holodeck-objaverse sets carry
per-object Objaverse licences, some NC -> not used). Each house package is range-fetched from its shard and
unpacked (the "<house>_ceiling" variant: same layout with a ceiling). kind = the room type voted by the THOR object
categories within 2.5 m of the work-zone centre (kitchen / living_room / bedroom / bathroom / other).
usage: python -m tools.l9.assets.rooms9_table --set procthor-10k-val --arrow ARROW.json --work DIR --out OUT.json
       [--n 300] [--workers 6]"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from collections import Counter
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

HF = "https://huggingface.co/datasets/allenai/molmospaces/resolve/main/isaac/scenes"
DATE = "20260128"
LICENSE = "CC BY 4.0 (MolmoSpaces AI2-THOR assets) / Apache 2.0 (ProcTHOR-10k house layouts)"
KIND_VOTES = {
    "kitchen": ("fridge", "stoveburner", "stoveknob", "microwave", "toaster", "coffeemachine", "sinkbasin", "pot",
                "pan", "dishsponge", "kettle", "countertop"),
    "bedroom": ("bed", "alarmclock", "cd", "laptop", "teddybear", "dresser"),
    "bathroom": ("toilet", "toiletpaper", "toiletpaperhanger", "showerhead", "bathtub", "towel", "towelholder",
                 "soapbar", "handtowel", "showercurtain"),
    "living_room": ("sofa", "television", "armchair", "remotecontrol", "coffeetable", "floorlamp", "painting",
                    "houseplant", "tvstand"),
}


def kind_at(stage, meta: dict, pose: dict) -> str:
    from pxr import Usd, UsdGeom
    cats = {k: str(v.get("category") or "").lower() for k, v in meta.get("objects", {}).items()}
    bc = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"])
    (x0, x1), (y0, y1) = pose["clear_box"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    votes = Counter()
    for p in stage.Traverse():
        c = cats.get(p.GetName())
        if not c:
            continue
        r = bc.ComputeWorldBound(p).ComputeAlignedRange()
        if r.IsEmpty():
            continue
        m = (r.GetMin() + r.GetMax()) / 2
        if math.hypot(m[0] - cx, m[1] - cy) <= 2.5:
            for kind, words in KIND_VOTES.items():
                if c in words:
                    votes[kind] += 1
    return votes.most_common(1)[0][0] if votes else "other"


def one(args):
    name, row, base, work = args
    from pxr import Usd

    from harvest.sim.assets_x import rooms as RO
    from harvest.sim.assets_x.usd_import import collider_mesh, make_visual, render_mesh
    from tools.l8x_assets.range_fetch import fetch
    house = name.replace(".tar.zst", "")
    d = os.path.join(work, house)
    try:
        if not os.path.isdir(d):
            tok = open("/data/.hf_token").read().strip() if os.path.exists("/data/.hf_token") else None
            data = fetch(f"{base}/shards/{int(row['shard_id']):05d}.tar", int(row["offset"]), int(row["size"]), tok)
            os.makedirs(d + ".part", exist_ok=True)
            subprocess.run(f"zstd -dc | tar xf - -C '{d}.part'", shell=True, input=data, check=True)
            os.replace(d + ".part", d)
        sub = sorted(x for x in os.listdir(d) if os.path.isdir(os.path.join(d, x)))
        use = next((x for x in sub if x.endswith("_ceiling")), sub[0])
        scene = os.path.join(d, use, "scene.usda")
        meta = json.load(open(os.path.join(d, use, "scene_metadata.json")))
        st = Usd.Stage.Open(scene)
        P, F = collider_mesh(st, exact_mesh=True)
        Rm = render_mesh(st)
        pose = RO.room_pose(P, F, render=Rm)
        if pose is None:
            return house, {"error": "no clear zone"}
        ok = RO.zone_is_clear(P, F, pose, render=Rm)
        if not ok:
            return house, {"error": "zone check failed"}
        vis = make_visual(scene, ext=".usdc")
        return house, dict(pose, usd=vis["visual"], kind=kind_at(st, meta, pose), clear_checked=True,
                           license=LICENSE, variant=use)
    except Exception as e:  # noqa: BLE001
        return house, {"error": f"{type(e).__name__}: {e}"[:160]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True)
    ap.add_argument("--arrow", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args(argv)
    base = f"{HF}/{a.set}/{DATE}"
    rows = json.load(open(a.arrow))
    import hashlib
    rows.sort(key=lambda r: hashlib.sha256(("l9r:" + r["path"]).encode()).hexdigest())
    rows = rows[:a.n]
    source = f"MolmoSpaces (allenai/molmospaces, isaac/scenes/{a.set}/{DATE}), ProcTHOR-10k houses (AI2-THOR assets)"
    os.makedirs(a.work, exist_ok=True)
    out = {}
    with Pool(a.workers, maxtasksperchild=4) as pool:
        for house, r in pool.imap_unordered(one, [(r["path"], r, base, a.work) for r in rows]):
            if "error" not in r:
                r["source"] = source
            out[house] = r
            print(house, r.get("kind"), r.get("margin"), r.get("error", ""), flush=True)
    ok = {f"{a.set}:{k}": v for k, v in out.items() if "error" not in v}
    from harvest.sim.assets_x import rooms as RO
    json.dump({"license": LICENSE, "source": f"MolmoSpaces isaac/scenes/{a.set}/{DATE}", "zone": RO.ZONE,
               "rooms": ok, "dropped": {k: v["error"] for k, v in out.items() if "error" in v}},
              open(a.out, "w"), indent=1)
    print("rooms", len(ok), "of", len(out), Counter(v["kind"] for v in ok.values()))


if __name__ == "__main__":
    main()
