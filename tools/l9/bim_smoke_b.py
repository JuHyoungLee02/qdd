"""L9 bimanual category-B (two-hand lift/carry/place) smoke (pod, Isaac): draws one scene + one target object
through the existing task9/scene9/pool path, builds a dual SimEnv, and runs
`harvest.l9.bimanual9.LiftRuntime.run_episode` end to end. Saves head + both wrist PNGs and a result.json per
episode; NOT the production collection loop (harvest/l9/bimanual9.py spec note §3).

Arm assignment is outcome-based from the first row (owner 2026-10-02 r2/r3): this script reuses
`bimanual9.probe_direction`/`choose_direction` the SAME way bim_smoke.py's --auto-direction does, except for B
there is no giver/receiver asymmetry -- "lr"/"rl" here just means which arm is `self.a` vs `self.b`
(LiftRuntime treats both symmetrically; the direction label only matters for L/R balance bookkeeping downstream).

usage: python -m tools.l9.bim_smoke_b --out DIR [--n 2] [--seed0 3951000] [--robot ffw_sg2] [--def lift_tray]
       [--pool 5000] [--rooms 5000] [--device cuda:0]
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import signal
import sys
import time


class _EpisodeTimeout(Exception):
    pass


@contextlib.contextmanager
def _episode_timeout(seconds: int):
    """Same SIGALRM-based per-episode safety net as bim_smoke.py -- see that file's copy for the rationale."""
    if seconds <= 0:
        yield
        return

    def _handler(signum, frame):
        raise _EpisodeTimeout(f"episode exceeded {seconds}s")

    old = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _jsonable(o):
    import numpy as np
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating, np.integer, np.bool_)):
        return o.item()
    return str(o)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=2)
    ap.add_argument("--seed0", type=int, default=3951000)
    ap.add_argument("--robot", default="ffw_sg2")
    ap.add_argument("--def", dest="defn_name", default="lift_tray", choices=list(
        "lift_tray lift_pot lift_big_box lift_basket lift_crate lift_bar".split()))
    ap.add_argument("--pool", type=int, default=5000)
    ap.add_argument("--pools", default=None,
                     help="comma-separated pool_for() indices to UNION together (more diversity for defs whose "
                          "category is thin/scattered across windows, e.g. basket) -- overrides --pool if given")
    ap.add_argument("--rooms", type=int, default=5000)
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--carry-dx", type=float, default=0.15)  # m, place target offset from the pick xy
    ap.add_argument("--episode-timeout-s", type=int, default=600,
                     help="hard per-episode wall-clock cap (SIGALRM); 0 disables.")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    results = []
    try:
        import numpy as np

        from harvest.l9 import assets9 as A9
        from harvest.l9 import bimanual9 as B
        from harvest.l9 import reach9 as R9
        from harvest.l9 import rt9 as RT
        from harvest.l9 import scene9 as S9
        from harvest.l9 import task9 as T9
        from harvest.l9 import vary9 as V
        from harvest.l9.world9 import make_world9
        from harvest.l9.run9 import rooms_for

        cats = B.BIM_B_DEFS[a.defn_name]["cats"]
        pool_idxs = [int(x) for x in a.pools.split(",")] if a.pools else [a.pool]
        pool = {}
        for p in pool_idxs:
            pool.update(A9.pool_for(p, "train"))
        # owner 10-03 (approved): B's "lift" objects (tray/basket/bin/etc) are tagged role9 in {container,clutter}
        # in the single-arm catalog -- task9.instantiate()'s target-role filter is role9=='target' only, hardcoded,
        # and stays UNTOUCHED (single-arm pipeline unmodified). Scoped fix instead: relabel a LOCAL COPY (not the
        # cached catalog dict -- those are the SAME objects pool_for() returns, mutating in place would corrupt
        # assets9's module-level cache for the rest of this process) of just this def's own category's
        # container/clutter items to role9="target" before calling instantiate, so the existing role=="target"
        # matching codepath picks them up unmodified. Anything already role9=="target" (e.g. "box") is untouched.
        pool = {k: (dict(v, role9="target") if (v.get("category") or "").lower() in cats
                    and v.get("role9") in ("container", "clutter") else v) for k, v in pool.items()}
        pool = {k: v for k, v in pool.items() if v.get("role9") != "target" or RT.has_candidates(a.robot, k, True)}
        n_targets = sum(1 for v in pool.values() if v.get("role9") == "target")
        print("POOL " + json.dumps({"size": len(pool), "targets_with_candidates": n_targets}), flush=True)
        rooms = rooms_for(a.rooms, "train")
        mesh = A9.mesh_for(a.rooms, split="train")
        rm = R9.load_default()
        family, rule = S9.all_rules("train")[0]
        world = make_world9("right", pool, rooms, mesh=mesh, robot=a.robot, dual=True)
        print("WORLD " + json.dumps({"arm": world.arm, "pool": len(pool), "dual": world.env.dual,
                                     "primary": world.env.primary}), flush=True)
        defn = T9.TaskDef("bim_b_smoke_" + a.defn_name, "bim_b", {"A": {"role": "target", "cats": cats}},
                          {"P": {"type": "spot", "corner": "centre"}}, (("A", "P"),), ("Lift the {A}.",) * 5)
        for i in range(a.n):
            seed = a.seed0 + i
            t0 = time.time()
            ep, sc = None, None
            for k in range(20):
                sd = seed + 100003 * k
                try:
                    sc = S9.sample(family, rule, sd, "right", rm)
                except RuntimeError:
                    continue
                ep = T9.instantiate(defn, sc, pool, sd, rm, grip_max=world.w_open)
                if ep is not None:
                    break
            if ep is None:
                results.append({"seed": seed, "ok": False, "status": "no scene / object draw"})
                continue
            light, head = V.pick_light_family(sd, "bim_b"), V.head_pose(sd)
            from harvest.l9 import collect9 as C9L
            from harvest.teach_l8d.fx import SkipScene
            C9L.register_task(ep)
            world.prepare(sc, ep, light, head, sd)
            try:
                world.reset(sd, C9L.T9_TASK)
            except SkipScene as ex:
                # production's own "this exact draw doesn't work, try another" signal -- MUST be caught per
                # episode, not left to the outer try/except, which would otherwise kill the whole remaining run
                # (found on the pod, bim_b_smoke6: a single SkipScene truncated a --n 10 run to 4 episodes).
                print("SKIP_SCENE " + json.dumps({"seed": seed, "err": str(ex)}), flush=True)
                results.append({"seed": seed, "ok": False, "status": f"SkipScene: {ex}"})
                continue
            obj_key = ep["steps"][0][0]
            print("DRAW " + json.dumps({"seed": seed, "obj": obj_key, "wall_s": round(time.time() - t0, 1)}),
                  flush=True)

            zone, _cell = B.zone_point(a.robot, world.table_z, seed, i)  # reused only as a cheap IK probe point
            scores, _rts = B.probe_direction(world, a.robot, obj_key, zone, device=a.device, allow_untested=True)
            try:
                direction = B.choose_direction(scores)
            except ValueError as ex:
                print("DIRECTION_FAIL " + json.dumps({"seed": seed, "scores": scores, "err": str(ex)},
                                                      default=_jsonable), flush=True)
                results.append({"seed": seed, "ok": False, "status": f"no direction reaches: {ex}"})
                continue
            arm_a, arm_b = ("right", "left") if direction == "rl" else ("left", "right")
            print("DIRECTION " + json.dumps({"seed": seed, "chosen": direction, "scores": scores},
                                             default=_jsonable), flush=True)

            env = world.env
            env.use_arm(arm_a)
            pick_xy = np.asarray(env.object_pose(obj_key)[0], float)[:2]
            target_xy = pick_xy + np.array([a.carry_dx, 0.0])

            lr = B.install_lift(world, a.robot, arm_a, arm_b, device=a.device, allow_untested=True)
            try:
                with _episode_timeout(a.episode_timeout_s):
                    r = lr.run_episode(obj_key, world.table_z, target_xy, seed=seed, episode_idx=i)
            except _EpisodeTimeout as ex:
                print("EPISODE_TIMEOUT " + json.dumps({"seed": seed, "err": str(ex)}), flush=True)
                r = {"ok": False, "status": "episode timeout"}
            r["seed"], r["obj"], r["direction"] = seed, obj_key, direction
            r["wall_s"] = round(time.time() - t0, 1)
            print("EP " + json.dumps({k: v for k, v in r.items() if k != "log"}, default=_jsonable), flush=True)
            results.append(r)
            try:
                from PIL import Image
                od = os.path.join(a.out, f"ep{i}")
                os.makedirs(od, exist_ok=True)
                for cam, name in (("cam_head", "head"), ("cam_wrist_right", "wrist_right"),
                                 ("cam_wrist_left", "wrist_left")):
                    Image.fromarray(world.env.camera_rgb(cam)).save(os.path.join(od, f"{name}.png"))
            except Exception as ex:  # noqa: BLE001
                print("FRAME_SAVE_FAIL " + str(ex), flush=True)
        code = 0
    except Exception as ex:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        results.append({"ok": False, "status": f"{type(ex).__name__}: {ex}"})
        code = 1
    with open(os.path.join(a.out, "result.json"), "w") as f:
        json.dump(results, f, indent=1, default=_jsonable)
    print("DONE " + json.dumps({"n": len(results), "ok": sum(1 for r in results if r.get("ok"))}), flush=True)
    print("RUN_DONE", flush=True)
    os._exit(code)


if __name__ == "__main__":
    main()
