"""iTHOR room table (pod, pxr): unpack each FloorPlan, find a clear pose for the work zone (rooms.room_pose from the
scene's colliders), write a render-only flattened copy (usd_import.make_visual, .usdc) -> rooms JSON.
usage: python tools/l8x_assets/rooms_table.py SHARD.tar WORK_DIR OUT.json [--max 120]"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from harvest.sim.assets_x import rooms as RO  # noqa: E402
from harvest.sim.assets_x.usd_import import collider_mesh, make_visual, render_mesh  # noqa: E402

LICENSE = "CC BY 4.0"
SOURCE = "MolmoSpaces (allenai/molmospaces, isaac/scenes/ithor/20260121), AI2-THOR iTHOR floor plans"


def kind_of(fp: int) -> str:
    return {0: "kitchen", 2: "living_room", 3: "bedroom", 4: "bathroom"}.get(fp // 100, "kitchen")


def main(argv=None):
    from pxr import Usd
    ap = argparse.ArgumentParser()
    ap.add_argument("shard")
    ap.add_argument("work")
    ap.add_argument("out")
    ap.add_argument("--max", type=int, default=200)
    a = ap.parse_args(argv)
    names = subprocess.run(["tar", "tf", a.shard], capture_output=True, text=True, check=True).stdout.split()
    names = sorted(n for n in names if n.endswith("_physics.tar.zst"))[: a.max]
    os.makedirs(a.work, exist_ok=True)
    rows = {}
    for n in names:
        fp = n.replace("ithor_", "").replace("_physics.tar.zst", "")
        d = os.path.join(a.work, fp)
        if not os.path.isdir(d):
            os.makedirs(d)
            subprocess.run(f"tar xOf '{a.shard}' '{n}' | zstd -dc | tar xf - -C '{d}'", shell=True, check=True)
        scene = os.path.join(d, fp + "_physics", "scene.usda")
        try:
            st = Usd.Stage.Open(scene)
            P, F = collider_mesh(st, exact_mesh=True)
            Rm = render_mesh(st)
            pose = RO.room_pose(P, F, render=Rm)
            if pose is None:
                rows[fp] = {"error": "no clear zone"}
            else:
                vis = make_visual(scene, ext=".usdc")
                rows[fp] = dict(pose, usd=vis["visual"], kind=kind_of(int(fp.replace("FloorPlan", ""))),
                                clear_checked=RO.zone_is_clear(P, F, pose, render=Rm), license=LICENSE, source=SOURCE)
        except Exception as e:  # noqa: BLE001
            rows[fp] = {"error": f"{type(e).__name__}: {e}"[:160]}
        print(fp, rows[fp].get("margin"), rows[fp].get("clear_checked"), rows[fp].get("error", ""), flush=True)
    ok = {k: v for k, v in rows.items() if "error" not in v and v["clear_checked"]}
    with open(a.out, "w") as f:
        json.dump({"license": LICENSE, "source": SOURCE, "zone": RO.ZONE, "rooms": ok,
                   "dropped": {k: v.get("error", "zone check failed") for k, v in rows.items() if k not in ok}},
                  f, indent=1)
    print("rooms", len(ok), "of", len(rows))


if __name__ == "__main__":
    main()
