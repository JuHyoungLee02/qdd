"""Per-piece mesh furniture gate for the realistic bundle b4 (user-log 173; pod, Isaac).

The L8-D furniture gate (prereg_l8d change 7) passes a whole kind (thor_counter, ...) on 10 clean truth episodes
with a random piece each. b4 needs to know WHICH pieces work, so this tool forces one piece per episode: the L8-D
runner world (run_collect.make_world, furniture scene of the kind, the scene's own lift and best surface, standard
variant) with furniture._mesh_piece restricted to the current piece. Per piece: the same clean truth episodes on the
L8-D furniture gate seeds (35060 / 35061 mug_tray, 35063 bottle_tray, 35064 mug_marker: the same seeds for every
piece, as the L8-D object gate does); pass = >= 3 of 4 successes (a skipped scene -- no usable surface -- counts as
a failure). Results: <out>/<piece>/<task>_s<seed>/ (L8-D episode files) and <out>/pieces_<kind>.json.
usage: python -m tools.l8x_assets.gate_pieces --kind thor_table --pieces A,B --out DIR [--reach reach_base.json]"""
from __future__ import annotations

import argparse
import json
import os
import time

GATE = ((35060, "mug_tray"), (35061, "mug_tray"), (35063, "bottle_tray"), (35064, "mug_marker"))
PASS_K = 3
WS_X = (0.36, 0.54)  # = the L8-D furniture gate command (--ws-x)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True)
    ap.add_argument("--pieces", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--reach", default="/data/harvest/out/teach_l8d/gate/reach_base.json")
    ap.add_argument("--video", action="store_true")
    a = ap.parse_args(argv)
    code = 0
    try:
        from harvest.sim.assets_x import furniture as FU
        from harvest.teach_l8d import spec as S
        from harvest.teach_l8d.collect import collect_episode
        from harvest.teach_l8d.fx import SkipScene
        from harvest.teach_l8d.run_collect import make_world
        cur = {"piece": None}
        orig = FU._mesh_piece

        def only(rng, kind, mesh_assets, split, *x, **k):
            if cur["piece"] is not None:
                mesh_assets = {cur["piece"]: mesh_assets[cur["piece"]]}
            return orig(rng, kind, mesh_assets, split, *x, **k)
        FU._mesh_piece = only
        world = make_world("standard", 0.0, S.ws_of(WS_X), None, None, a.kind, a.reach, "train", None, None)
        os.makedirs(a.out, exist_ok=True)
        res_p = os.path.join(a.out, f"pieces_{a.kind}.json")
        res = json.load(open(res_p)) if os.path.exists(res_p) else {}
        for piece in a.pieces.split(","):
            if piece in res:
                continue
            cur["piece"] = piece
            eps = []
            for seed, task in GATE:
                od = os.path.join(a.out, piece, f"{task}_s{seed}")
                t0 = time.perf_counter()
                try:
                    m = collect_episode(world, seed, task, "standard", "gate", od, 0.0, 4, 30, 120.0, "clean",
                                        video=a.video and seed == GATE[0][0])
                    used = (getattr(world, "furniture_scene", None) or {})
                    eps.append({"seed": seed, "task": task, "success": bool(m["success"]),
                                "end_reason": m["end_reason"], "table_z": m["table_z"], "lift": m["lift"],
                                "wall_s": round(time.perf_counter() - t0, 1), "surface": (used.get("surface") or {})
                                .get("id")})
                except SkipScene as ex:
                    eps.append({"seed": seed, "task": task, "success": False, "skip": str(ex)[:200]})
            k = sum(e["success"] for e in eps)
            res[piece] = {"kind": a.kind, "k": k, "n": len(eps), "pass": k >= PASS_K, "episodes": eps}
            print("PIECE " + json.dumps({"piece": piece, "k": k, "pass": k >= PASS_K}), flush=True)
            with open(res_p, "w") as f:
                json.dump(res, f, indent=1)
        print("PIECES_DONE", sum(r["pass"] for r in res.values()), "/", len(res), flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
