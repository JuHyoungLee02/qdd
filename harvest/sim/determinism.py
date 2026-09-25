"""Episode determinism check: the same seed must give the same per-tick physics state after any process history.

pool_replay_debug.md found that CPU PhysX carried scene-internal state across env.reset(), so one seed replayed into
one of a few discrete trajectories depending on what ran before in the process. scene.Env.reset now recreates the
PhysX scene (physx_hard_reset.md); this tool checks the result on the pod.

  python -m harvest.sim.determinism fresh --seed S --out DIR [--cameras]
      new process: make_env(S) -> episode S                                          -> DIR/fresh_S.npz
  python -m harvest.sim.determinism history --seeds 3,11 --first 5 --partial 8 --out DIR [--cameras]
      one process, make_env(first): per seed S [first full, S | partial-seed cut at k, S | S] -> DIR/hist_S_<h>.npz
  python -m harvest.sim.determinism compare --out DIR          (no Isaac) bit-identity matrix -> DIR/matrix.json

A trace is recorded after every env.step, the settle steps of the reset included: robot joint_pos / joint_vel and
every rigid object's root pose (pos + quat) and velocity, all float32 as read from the sim. "Identical" = every
value bit-equal over the whole episode (and the same length). DEV seeds only (snapshot.check_seed + DEV range).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import time

import numpy as np

KEYS = ("joint_pos", "joint_vel", "obj_pose", "obj_vel")


# ------------------------------------------------------------------------------------------------ pure
def compare_traces(a: dict, b: dict) -> dict:
    """{"identical", "len": [na, nb], "first_diff_tick", "max_abs": {key: float}} over the common length."""
    na, nb = len(a["joint_pos"]), len(b["joint_pos"])
    n = min(na, nb)
    first, mx = None, {}
    for k in KEYS:
        x, y = np.asarray(a[k][:n]), np.asarray(b[k][:n])
        d = np.abs(x.astype(np.float64) - y.astype(np.float64)).reshape(n, -1) if n else np.zeros((0, 1))
        mx[k] = float(d.max()) if d.size else 0.0
        neq = np.flatnonzero((x.reshape(n, -1) != y.reshape(n, -1)).any(axis=1)) if n else []
        if len(neq) and (first is None or int(neq[0]) < first):
            first = int(neq[0])
    same = first is None and na == nb
    return {"identical": bool(same), "len": [na, nb], "first_diff_tick": first if first is not None else (
        None if na == nb else n), "max_abs": mx}


def _dev_seed(s: int) -> int:
    from .snapshot import DEV_SEEDS, check_seed
    s = check_seed(s)
    if s not in DEV_SEEDS:
        raise SystemExit(f"determinism: DEV seeds 0-29 only (got {s})")
    return s


# ------------------------------------------------------------------------------------------ Isaac (pod)
class Tracer:
    """Records the state after every env.step of `env` (instance-level wrap of Env.step, reset settling included)."""

    def __init__(self, env):
        self.env, self.rows, self.on = env, None, False
        orig = env.step

        def step(q):
            orig(q)
            if self.on:
                self._rec()
        env.step = step

    def start(self):
        self.rows, self.on = {k: [] for k in KEYS}, True

    def stop(self) -> dict:
        self.on = False
        return {k: np.stack(v) if v else np.zeros((0,)) for k, v in self.rows.items()}

    def _rec(self):
        e = self.env
        d = e.robot.data
        self.rows["joint_pos"].append(d.joint_pos[0].cpu().numpy().copy())
        self.rows["joint_vel"].append(d.joint_vel[0].cpu().numpy().copy())
        self.rows["obj_pose"].append(np.stack([o.data.root_pose_w[0].cpu().numpy() for o in e.objects.values()]))
        self.rows["obj_vel"].append(np.stack([o.data.root_vel_w[0].cpu().numpy() for o in e.objects.values()]))


def _episode(env, tr: Tracer, seed: int, cams, cut_k: int | None = None) -> tuple[dict, dict]:
    """One P0 episode of `seed` (cli_pool.run_snapshot_episode = the pool / labeler episode), traced. cut_k: stop
    at continuous snapshot k (a partial episode). Returns (trace, info with wall / CPU seconds, reset seconds)."""
    from ..cli_pool import _Stop, run_snapshot_episode
    sim = env.env.sim
    info = {"seed": seed, "cut_k": cut_k, "hard_reset_s": []}
    orig_reset = sim.reset

    def timed_reset(*a, **kw):
        t = time.perf_counter()
        r = orig_reset(*a, **kw)
        info["hard_reset_s"].append(round(time.perf_counter() - t, 4))
        return r
    sim.reset = timed_reset
    imgs = []

    def on(env_, pl, rec, s, im):
        if im:
            imgs.append({n: int(np.frombuffer(v.tobytes(), np.uint8).astype(np.uint64).sum()) for n, v in im.items()})
        if cut_k is not None and rec["k"] >= cut_k:
            raise _Stop
        return False

    tr.start()
    w0, c0 = time.perf_counter(), time.process_time()
    try:
        res = run_snapshot_episode(env, seed, "P0", cams=cams, on_snapshot=on)
        info.update(success=bool(res["success"]), sim_time_s=res["sim_time_s"])
    except _Stop:
        info.update(success=None, sim_time_s=round(env.sim_time, 3))
    finally:
        sim.reset = orig_reset
    info.update(wall_s=round(time.perf_counter() - w0, 3), cpu_s=round(time.process_time() - c0, 3),
                img_sums=imgs)
    return tr.stop(), info


def _save(out: str, name: str, trace: dict, info: dict):
    np.savez(os.path.join(out, name + ".npz"), **trace)
    with open(os.path.join(out, name + ".json"), "w") as f:
        json.dump(info, f)
    print("DET " + json.dumps({"name": name, **{k: v for k, v in info.items() if k != "img_sums"},
                               "ticks": len(trace["joint_pos"])}), flush=True)


def _make(seed: int, cameras: bool):
    from .scene import RECORD_CAMERAS, make_env
    cams = tuple(RECORD_CAMERAS) if cameras else ()
    env = make_env(seed, headless=True, cameras=cams, depth=False)
    return env, Tracer(env), cams


def run_fresh(seed: int, out: str, cameras: bool):
    seed = _dev_seed(seed)
    env, tr, cams = _make(seed, cameras)
    _save(out, f"fresh_{seed}", *_episode(env, tr, seed, cams))


def run_history(seeds, first: int, partial: int, cut_k: int, out: str, cameras: bool):
    """make_env(first); per seed: [first full, S] -> after_full, [partial cut at cut_k, S] -> after_partial,
    [S] again -> twice. The runs in between are traced too (not compared)."""
    first, partial = _dev_seed(first), _dev_seed(partial)
    env, tr, cams = _make(first, cameras)
    for s in (_dev_seed(x) for x in seeds):
        _save(out, f"prev_{s}_full{first}", *_episode(env, tr, first, cams))
        _save(out, f"hist_{s}_after_full", *_episode(env, tr, s, cams))
        _save(out, f"prev_{s}_part{partial}", *_episode(env, tr, partial, cams, cut_k=cut_k))
        _save(out, f"hist_{s}_after_partial", *_episode(env, tr, s, cams))
        _save(out, f"hist_{s}_twice", *_episode(env, tr, s, cams))


def load_trace(path: str) -> dict:
    z = np.load(path)
    return {k: z[k] for k in KEYS}


def compare_dir(out: str) -> dict:
    rows = []
    for f in sorted(glob.glob(os.path.join(out, "fresh_*.npz"))):
        s = f.rsplit("_", 1)[1][:-4]
        ref = load_trace(f)
        for g in sorted(glob.glob(os.path.join(out, f"hist_{s}_*.npz"))):
            h = os.path.basename(g)[len(f"hist_{s}_"):-4]
            c = compare_traces(ref, load_trace(g))
            ia = json.load(open(f[:-4] + ".json")).get("img_sums")
            ib = json.load(open(g[:-4] + ".json")).get("img_sums")
            c["frames_identical"] = None if not ia else bool(ia == ib)
            rows.append({"seed": int(s), "history": h, **c})
    res = {"n": len(rows), "all_identical": bool(rows) and all(r["identical"] for r in rows), "rows": rows}
    with open(os.path.join(out, "matrix.json"), "w") as f:
        json.dump(res, f, indent=1)
    for r in rows:
        print("CMP " + json.dumps(r), flush=True)
    print("ALL_IDENTICAL", res["all_identical"], flush=True)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m harvest.sim.determinism")
    ap.add_argument("mode", choices=("fresh", "history", "compare"))
    ap.add_argument("--seed", type=int)
    ap.add_argument("--seeds", default="3,11,19,26")
    ap.add_argument("--first", type=int, default=5)
    ap.add_argument("--partial", type=int, default=8)
    ap.add_argument("--cut-k", type=int, default=8)
    ap.add_argument("--cameras", action="store_true")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.mode == "fresh":  # every seed is refused BEFORE the output folder exists (R7 cycle 14 N3)
        if a.seed is None:
            raise SystemExit("determinism fresh: --seed is required")
        _dev_seed(a.seed)
    elif a.mode == "history":
        for s in [a.first, a.partial] + [int(x) for x in a.seeds.split(",")]:
            _dev_seed(s)
    os.makedirs(a.out, exist_ok=True)
    if a.mode == "compare":
        compare_dir(a.out)
        return
    if a.mode == "fresh":
        run_fresh(a.seed, a.out, a.cameras)
    else:
        run_history([int(x) for x in a.seeds.split(",")], a.first, a.partial, a.cut_k, a.out, a.cameras)
    os._exit(0)  # Isaac's shutdown can hang; everything is written


if __name__ == "__main__":
    main()
