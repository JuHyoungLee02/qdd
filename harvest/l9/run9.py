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
    out = {}
    for j in range(n):
        k = order[(idx * n + j) % len(order)]
        out[prim_safe(k)] = dict(t[k], name0=k)  # USD prim names: letters, digits, _ only (ProcTHOR names have '-')
    return out


def prim_safe(name: str) -> str:
    import re
    s = re.sub(r"[^A-Za-z0-9_]", "_", name)
    return s if s[:1].isalpha() else "r_" + s


YIELD_DIR = "/data/harvest/out/l9/yield"


def yield_file() -> str:
    """<YIELD_DIR>/<hostname>_<gpu>: when it exists, L9 processes on that card stop between episodes and lanes do
    not restart there (the card is lent; tools/l9/lend9.sh)."""
    import socket
    g = (os.environ.get("CUDA_VISIBLE_DEVICES") or "x").split(",")[0]
    return os.path.join(YIELD_DIR, f"{socket.gethostname()}_{g}")


def ep_dir(out: str, row: dict) -> str:
    rb = row.get("robot") or "ffw_sg2"
    tail = "" if rb == "ffw_sg2" else f"_{rb}"  # spec §9: another robot on the same seed gets its own folder
    return os.path.join(out, row.get("split", "train"), row["family"], f"{row['def']}_s{row['seed']}_{row['arm']}{tail}")


FRANKA_MAX_GRASP_W = 0.066  # Franka Hand opens 8 cm; close_width = width - 1.4 cm must leave the fingers room


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--job", required=True)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--video-seeds", default="")
    ap.add_argument("--p", type=float, default=0.35)
    ap.add_argument("--motion", action="store_true", help="spec §10 human-like motion (harvest.l9.motion9)")
    a = ap.parse_args(argv)
    code = 0
    import faulthandler
    import signal
    import sys
    faulthandler.register(signal.SIGUSR1, file=sys.stderr, all_threads=True)  # `kill -USR1 <pid>`: stacks to the log
    try:
        from ..teach_l8d.fx import SkipScene
        from . import assets9 as A9
        from . import reach9 as R9
        from .collect9 import NoEpisode, run_episode
        from .vary9 import ComboLedger
        from .world9 import make_world9
        if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(a.out)), "MOTION_ON")):
            a.motion = True  # run-level switch (spec §10 code swap: new episodes of a running production)
        if a.motion:
            from .motion9 import install
            install()
        rows = [r for r in json.load(open(a.plan)) if str(r["job"]) == str(a.job)]
        if not rows:
            raise ValueError(f"no rows for job {a.job}")
        arms = {r["arm"] for r in rows}
        if len(arms) != 1:
            raise ValueError(f"job {a.job}: one arm per process, got {arms}")
        robots = {r.get("robot") or "ffw_sg2" for r in rows}
        hcams = {r.get("hcam") for r in rows}
        if len(robots) != 1 or len(hcams) != 1:
            raise ValueError(f"job {a.job}: one robot / head-camera mode per process, got {robots} {hcams}")
        robot, hcam = next(iter(robots)), next(iter(hcams))
        if hcam is None and os.path.exists(os.path.join(os.path.dirname(os.path.abspath(a.out)), "HCAM_ON")):
            hcam = "coin"  # run-level switch (spec §9.3: new episodes of a running production, after the pilot gate)
            for r in rows:
                r["hcam"] = hcam
        todo = [r for r in rows if not (os.path.exists(os.path.join(ep_dir(a.out, r), "meta.json"))
                                        or os.path.exists(os.path.join(ep_dir(a.out, r), "skipped.json")))]
        print("JOB " + json.dumps({"job": a.job, "rows": len(rows), "todo": len(todo)}), flush=True)
        if not todo:
            print("RUN_DONE", flush=True)
            os._exit(0)
        from .arm import apply_arm_workspace
        from .robot9 import apply_prompts
        arm = next(iter(arms))
        apply_arm_workspace(arm)  # left: mirrored safety box / reach corner (before the episode modules load)
        apply_prompts(robot)  # spec §9.1: robot / gripper / head-camera wording of the requests
        split = rows[0].get("split", "train")
        pool = A9.pool_for(int(rows[0]["pool"]), "train" if split == "train" else "ood_o")
        if rows[0].get("pool_ids"):  # object gate jobs: exactly these targets (+ the pool's clutter / containers)
            cat = A9.catalog("train")
            pool = {k: v for k, v in pool.items() if v["role9"] != "target"}
            pool.update({k: cat[k] for k in rows[0]["pool_ids"] if k in cat})
        if robot == "franka_mast":  # targets the Franka Hand can close on; fingers / containers: its opening
            from . import task9 as T9
            T9.FINGER_OPEN = 0.08
            pool = {k: v for k, v in pool.items()
                    if v["role9"] != "target" or float(v.get("grasp_width") or 2 * float(v.get("footprint_r", 1)))
                    <= FRANKA_MAX_GRASP_W}
        rooms = rooms_for(int(rows[0]["rooms"]), "train" if split == "train" else "ood")
        mesh = A9.mesh_for(int(rows[0]["rooms"]), split="train" if split == "train" else "ood")
        world = make_world9(arm, pool, rooms, mesh=mesh, robot=robot, hcam=hcam)
        from ..teach_l8d import collect as _c  # noqa: F401  (load the episode modules, then rebind their copies)
        print("WORKSPACE " + json.dumps({"arm": arm, "rebound": apply_arm_workspace(arm), "robot": robot, "hcam": hcam,
                                         "prompts": apply_prompts(robot)}), flush=True)
        rm = R9.load_default()
        led_dir = os.path.join(a.out, "ledger")
        os.makedirs(led_dir, exist_ok=True)
        mine = os.path.join(led_dir, f"{a.job}.txt")
        ledger = ComboLedger(mine, [p for p in glob.glob(os.path.join(led_dir, "*.txt")) if p != mine])
        vids = {int(v) for v in a.video_seeds.split(",") if v.strip()}
        print("WORLD " + json.dumps({"arm": world.arm, "pool": len(pool), "rooms": sorted(rooms), "n": len(todo)}),
              flush=True)
        yf = yield_file()
        for r in todo:
            if os.path.exists(yf) and os.environ.get("IR_L9R_LENT") != "1":  # lent card: stop between episodes
                # (tools/l9/lend9.sh); IR_L9R_LENT=1 = this process IS the borrower (tools/l9r/lane_r.sh)
                print("YIELD " + yf, flush=True)
                break
            od = ep_dir(a.out, r)
            t0 = time.perf_counter()
            try:
                meta = run_episode(world, r, od, pool, rm, ledger, p=a.p, video=int(r["seed"]) in vids,
                                   motion=a.motion or bool(r.get("motion")))
            except (SkipScene, NoEpisode, ValueError) as ex:
                os.makedirs(od, exist_ok=True)
                json.dump({"row": r, "reason": f"{type(ex).__name__}: {ex}"}, open(os.path.join(od, "skipped.json"), "w"))
                print("SKIP " + json.dumps({"seed": r["seed"], "def": r["def"], "reason": str(ex)[:200]}), flush=True)
                continue
            keep = ("seed", "task_id", "arm", "robot", "env_family", "success", "end_reason", "n_calls", "max_dq_rad",
                    "wall_s")
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
