"""L9 collection runner (pod, Isaac; one process = one arm x one object pool x one room subset):
python -m harvest.l9.run9 --plan plan.json --job J [--out /data/harvest/out/l9/collect] [--video-seeds s1,s2]
The plan (tools/l9/plan.py) is a JSON list of rows {seed, arm, family, rule, def, split, job, pool, rooms, style};
this process runs the rows of job J (one arm, one pool index, one room subset). Output
<out>/<split>/<family>/<def>_s<seed>_<arm>/ (the L8S episode folder + episode9.json); finished or skipped episodes
are not redone (resume). The environment-combination ledger is <out>/ledger/<job>.txt (all ledgers of the run are
read, so a combination is never used twice)."""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import time

OUT = "/data/harvest/out/l9/collect"
N_ROOMS = 6


def room_table(split: str = "train") -> dict:
    """iTHOR (L8S) + ProcTHOR (L9 assets) rooms of a split (20 % held out by name hash, as fx.room_split)."""
    from ..teach_l8d.fx import room_split
    here = os.path.dirname(os.path.abspath(__file__))
    out = {}
    for path in (os.path.join(here, "..", "sim", "assets_x", "rooms_ithor.json"), os.path.join(here, "assets9", "rooms_l9.json")):
        for n, r in json.load(open(path))["rooms"].items():
            if room_split(n) == split:
                out[n] = r
    return out


def rooms_for(idx: int, split: str = "train", n: int = N_ROOMS) -> dict:
    """The idx-th subset of n rooms (rotating through the whole table)."""
    t = room_table(split)
    order = sorted(t, key=lambda k: hashlib.sha256(f"l9room:{k}".encode()).hexdigest())
    return {order[(idx * n + j) % len(order)]: t[order[(idx * n + j) % len(order)]] for j in range(n)}


def ep_dir(out: str, row: dict) -> str:
    return os.path.join(out, row.get("split", "train"), row["family"], f"{row['def']}_s{row['seed']}_{row['arm']}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--job", required=True)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--video-seeds", default="")
    ap.add_argument("--p", type=float, default=0.35)
    a = ap.parse_args(argv)
    code = 0
    try:
        from ..teach_l8d.fx import SkipScene
        from . import assets9 as A9
        from . import reach9 as R9
        from .collect9 import NoEpisode, run_episode
        from .vary9 import ComboLedger
        from .world9 import make_world9
        rows = [r for r in json.load(open(a.plan)) if str(r["job"]) == str(a.job)]
        if not rows:
            raise ValueError(f"no rows for job {a.job}")
        arms = {r["arm"] for r in rows}
        if len(arms) != 1:
            raise ValueError(f"job {a.job}: one arm per process, got {arms}")
        todo = [r for r in rows if not (os.path.exists(os.path.join(ep_dir(a.out, r), "meta.json"))
                                        or os.path.exists(os.path.join(ep_dir(a.out, r), "skipped.json")))]
        print("JOB " + json.dumps({"job": a.job, "rows": len(rows), "todo": len(todo)}), flush=True)
        if not todo:
            print("RUN_DONE", flush=True)
            os._exit(0)
        split = rows[0].get("split", "train")
        pool = A9.pool_for(int(rows[0]["pool"]), "train" if split == "train" else "ood_o")
        rooms = rooms_for(int(rows[0]["rooms"]), "train" if split == "train" else "ood")
        world = make_world9(arms.pop(), pool, rooms)
        rm = R9.load_default()
        led_dir = os.path.join(a.out, "ledger")
        os.makedirs(led_dir, exist_ok=True)
        mine = os.path.join(led_dir, f"{a.job}.txt")
        ledger = ComboLedger(mine, [p for p in glob.glob(os.path.join(led_dir, "*.txt")) if p != mine])
        vids = {int(v) for v in a.video_seeds.split(",") if v.strip()}
        print("WORLD " + json.dumps({"arm": world.arm, "pool": len(pool), "rooms": sorted(rooms), "n": len(todo)}),
              flush=True)
        for r in todo:
            od = ep_dir(a.out, r)
            t0 = time.perf_counter()
            try:
                meta = run_episode(world, r, od, pool, rm, ledger, p=a.p, video=int(r["seed"]) in vids)
            except (SkipScene, NoEpisode, ValueError) as ex:
                os.makedirs(od, exist_ok=True)
                json.dump({"row": r, "reason": f"{type(ex).__name__}: {ex}"}, open(os.path.join(od, "skipped.json"), "w"))
                print("SKIP " + json.dumps({"seed": r["seed"], "def": r["def"], "reason": str(ex)[:200]}), flush=True)
                continue
            keep = ("seed", "task_id", "arm", "env_family", "success", "end_reason", "n_calls", "max_dq_rad", "wall_s")
            print("EP " + json.dumps(dict({k: meta.get(k) for k in keep}, wall_total_s=round(time.perf_counter() - t0, 1))),
                  flush=True)
        print("RUN_DONE", flush=True)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
