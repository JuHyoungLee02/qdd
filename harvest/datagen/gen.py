"""R2 sim data generator (gate R2 of docs/superpowers/plans/2026-09-25-e2e-ready.md).

Isaac modes (pod only: ir_run.sh IR_ROOT=cyclo, CPU PhysX, rendering on the GPU given by CUDA_VISIBLE_DEVICES):
  gen    --variant {standard|dr} --tasks all|a,b --kinds P0[,P1,P2] --seeds 0-5 --out DIR [--stale-s 1800]
         several processes may run the same command: items (variant, task, kind, seed) are shared through file locks
         (queue.py), done items are skipped (resumable). One Isaac env per process (the variant is fixed per env).
  replay --out DIR --variant V --task T --kind K --seed S
         re-executes the recorded action_exec (same 3/4-substep holds, same perturbation writes at the same ticks)
         after the same canonical prefix and compares object / joint trajectories with the recording.
Pure modes (any python with numpy + PIL):
  check  --out DIR     validate every episode (validate.py), stamp meta, merge the loader files, print a summary
  sheet  --out DIR --dst JPG   frames sheet (head | wrist at start / grasp / place, one row per variant x task)

Recording (timing.py): one frame per 30 Hz tick on the 10 ms physics grid; per frame head + right-wrist RGB rendered at
t_k (native 672x376 / 424x240, JPEG q90), proprio q / qd / tau(arm applied_torque) / grip, the oracle observation;
the command of tick k is held for 3 or 4 substeps. The teacher is the oracle planner (planner.OraclePlanner, task from
tasks.py); action_script = action_exec (no residual). Training variants: standard and dr only -- 'random' (TEST pool)
is refused (randomize.check_train_variant, canon §34 D35). Seeds: DEV 0-29 here; R2_TRAIN_SEEDS (canon §66) only
with --confirm-train (the large stage-B generation, not run yet).
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

from ..sim import tasks as TK
from . import queue as Q
from .timing import H_DEFAULT, PHYS_DT, hold_substeps, tick_time

DEV_SEEDS = range(0, 30)
R2_TRAIN_SEEDS = range(10000, 60000)  # canon §66: disjoint from CAL 500-549, TEST 1000-1149, TEST-P5 1300-1329,
# POOL 2000-2119 and the unit-test seed range 3000-3199
HOLD_DEBOUNCE_30 = 5  # planner HOLD_DEBOUNCE = 3 steps at 20 Hz = 0.15 s -> 5 ticks at 30 Hz (0.167 s)
CAMS = ("cam_head", "cam_wrist_right")
NO_RENDER = 10 ** 9  # render_interval: the env never renders by itself; frames are rendered on demand at t_k
PRE_RENDER = 8  # renders between reset and frame 0 (dr DEV: k0->k1 image change 9-39 grey levels, baseline 2-4)


def check_r2_seed(seed: int, allow_train: bool = False) -> int:
    s = int(seed)
    if s in DEV_SEEDS or (allow_train and s in R2_TRAIN_SEEDS):
        return s
    raise ValueError(f"seed {s}: R2 generates DEV 0-29" + (
        f" and R2_TRAIN {R2_TRAIN_SEEDS.start}-{R2_TRAIN_SEEDS.stop - 1} (--confirm-train given)" if allow_train else
        f" only (R2_TRAIN {R2_TRAIN_SEEDS.start}-{R2_TRAIN_SEEDS.stop - 1} needs --confirm-train)") +
        "; every other seed is refused (CAL / TEST / TEST-P5 / POOL are never generated)")


def split_of(seed: int) -> str:
    """dev for DEV seeds; R2 train seeds: 'fit' / 'eval' (5 % by seed) = stagea_data.SPLIT train / val."""
    if seed in DEV_SEEDS:
        return "dev"
    return "eval" if seed % 20 == 0 else "fit"


def parse_seeds(spec: str, allow_train: bool = False) -> list:
    out = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return [check_r2_seed(s, allow_train) for s in out]


# ================================================================================ Isaac part
def _planner_cls():
    from ..config import CFG
    from ..sim.planner import OraclePlanner

    class RecPlanner(OraclePlanner):
        """OraclePlanner.observe that also keeps the support map (for the text state); otherwise identical."""

        def observe(self):
            from ..sim.oracle_state import oracle_objects
            objs, grip, contacts, support = oracle_objects(self.env)
            self.pred = self.ps.update(objs, grip, contacts, support)
            self.objs, self.grip, self.contacts, self.support = objs, grip, contacts, support
            self.near_target = bool(np.linalg.norm(grip.pos - objs[self.tgt].pos) <= CFG.near_in_m)
            return self.pred
    return RecPlanner


def _grip_rate(env) -> float:
    """d(pad gap)/dt from the two finger link velocities (m/s)."""
    d = env.robot.data
    i, j = env.finger_idx[1], env.finger_idx[3]
    r = (d.body_pos_w[0, i] - d.body_pos_w[0, j]).cpu().numpy()
    v = (d.body_lin_vel_w[0, i] - d.body_lin_vel_w[0, j]).cpu().numpy()
    n = float(np.linalg.norm(r))
    return float(np.dot(r / max(n, 1e-9), v))


def prefix(env, task: str = "mug_tray") -> None:
    """The fixed PhysX history before every recorded / replayed episode: cli_pool.canonical_prefix on the mug task
    (pool.md), then -- for another task -- the same cut-at-carry run of that task (DEV seed 0), so the task's own
    target also has a canonical contact history. Without the second run a bottle episode recorded right after a
    bottle episode that ended off the table did not replay (diverged at grasp onset, r2_datagen.md)."""
    from ..cli_pool import canonical_prefix
    env.set_seed(0, "mug_tray")
    canonical_prefix(env)
    if task != "mug_tray":
        env.set_seed(0, task)  # run_snapshot_episode keeps the task (env.seed is already 0)
        canonical_prefix(env)


def record_episode(env, seed: int, task: str, kind: str, folder: str, cams=CAMS, limit_s: float = 60.0,
                   done_grace_s: float = 3.0) -> dict:
    """Run one oracle episode on the 30 Hz grid and record it (images written now, the rest returned)."""
    from PIL import Image

    from ..m4b.spec import contact_open
    from ..sim import snapshot as S
    from ..sim.oracle_state import to_table_frame
    from ..sim.perturb import apply_pending, perturb
    from ..sim.planner import FAIL_STAGE, place_metrics, randomization_meta, success_from_history, success_keys

    spec = TK.TASKS[task]
    tgt, place = spec.target, spec.place
    env.set_seed(seed, task)
    env.reset()
    perturb(env, kind, seed)
    for _ in range(PRE_RENDER):  # renderer warm-up after the reset (no physics step): a new dr seed's first frames
        env.env.sim.render()  # otherwise carry a 4-frame exposure / accumulation transient (r2_datagen.md)
    pl = _planner_cls()(env)
    pl.hold_debounce = HOLD_DEBOUNCE_30
    img_dir = f"{folder}/img/ep{seed}"
    os.makedirs(img_dir, exist_ok=True)
    rd = env.robot.data
    ids = env.arm_ids
    obj_ids = list(env.objects)
    frames, actions, hold_n, events, hist, pstream = [], [], [], [], [], []
    st = {k: [] for k in ("t", "q", "qd", "tau", "q_target", "grip", "grip_q", "grip_tau", "tcp", "obj_pose")}
    prev, k = {}, 0
    res = {"success": False, "stage": None, "info": {}, "fail_t": None}
    tm = {"render_s": 0.0, "jpeg_s": 0.0, "physics_s": 0.0, "planner_s": 0.0}
    t_wall = time.perf_counter()
    while True:
        t = env.sim_time
        if abs(t - tick_time(k)) > 1e-9:
            raise RuntimeError(f"tick {k}: sim time {t} != {tick_time(k)}")
        t0 = time.perf_counter()
        pred = pl.observe()
        objs, grip, contacts, support = pl.objs, pl.grip, pl.contacts, pl.support
        tm["planner_s"] += time.perf_counter() - t0
        t0 = time.perf_counter()
        imgs = S.capture(env, cams)
        tm["render_s"] += time.perf_counter() - t0
        t0 = time.perf_counter()
        paths = {}
        for c, im in imgs.items():
            p = f"{img_dir}/f{k:04d}_{c}.jpg"
            Image.fromarray(im).save(p, quality=90)
            paths[c] = os.path.relpath(p, folder)
        tm["jpeg_s"] += time.perf_counter() - t0
        h = pl.history
        moving = len(h) >= 2 and float(np.linalg.norm(np.asarray(h[-1][1]) - np.asarray(h[-2][1]))) > 1e-4
        ch = [c for c in pstream if c[0] >= t - 3.0] + S.pred_changes(prev, pred, t)
        pstream += S.pred_changes(prev, pred, t)
        prev = pred
        q = rd.joint_pos[0, ids].cpu().numpy()
        qd = rd.joint_vel[0, ids].cpu().numpy()
        tau = rd.applied_torque[0, ids].cpu().numpy()
        w, wd = env.gripper_width(), _grip_rate(env)
        fr = {"k": k, "t": t, "phase": pl.phase, "t_in_phase": t - pl.t_phase0, "pred": dict(pred),
              "support": dict(support), "present": list(env.present), "arm_moving": bool(moving), "changes": ch,
              "raw": S.obs_to_json(objs, grip, contacts, support),
              "near_hyst": [[a, b, bool(v)] for (a, b), v in sorted(pl.ps._near.items())], "images": paths,
              "proprio": {"q": [float(v) for v in q], "qd": [float(v) for v in qd], "tau": [float(v) for v in tau],
                          "grip": [float(w), float(wd)]},
              "contact_open": contact_open(grip.width_m, [c for c in contacts if "gripper" in c])}
        frames.append(fr)
        st["t"].append(t)
        st["q"].append(q)
        st["qd"].append(qd)
        st["tau"].append(tau)
        st["q_target"].append(rd.joint_pos_target[0, ids].cpu().numpy())
        st["grip"].append([w, wd])
        st["grip_q"].append(float(rd.joint_pos[0, env.grip_id]))
        st["grip_tau"].append(float(rd.applied_torque[0, env.grip_id]))
        st["tcp"].append(to_table_frame(env.finger_mid(), env.table_top_z))
        st["obj_pose"].append(np.stack([np.concatenate(env.object_pose(o)) for o in obj_ids]))
        hist.append((t, pred))
        if objs[tgt].pos[2] < -0.05:
            res.update(stage=FAIL_STAGE.get(pl.phase, "release"), info={"reason": "off_table", "phase": pl.phase},
                       fail_t=t)
            break
        if success_from_history(hist, tgt, place):
            res["success"] = True
            break
        if pl.phase == "fail":
            res.update(stage=pl.fail_stage, info=pl.fail_info, fail_t=pl.phase_log[-1][0])
            break
        if pl.phase == "done":
            res.setdefault("t_done", t)
            if t - res["t_done"] > done_grace_s:
                res.update(stage="release", info={"reason": "no_success_after_done",
                                                  **{x: pred.get(x) for x in success_keys(tgt, place)}})
                break
        if t >= limit_s:
            res.update(stage=FAIL_STAGE.get(pl.phase, "release"), info={"reason": "time_limit", "phase": pl.phase})
            break
        n = hold_substeps(k)
        pl.dt = n * PHYS_DT
        t0 = time.perf_counter()
        a = pl.step()
        tm["planner_s"] += time.perf_counter() - t0
        ev = apply_pending(env, t, pl.near_target, pl.phase)
        if ev:
            ev["k"] = k
            events.append(ev)
        t0 = time.perf_counter()
        S.step_partial(env, a, n)
        tm["physics_s"] += time.perf_counter() - t0
        actions.append([float(v) for v in a])
        hold_n.append(n)
        k += 1
    wall = time.perf_counter() - t_wall
    meta = dict(res, sim_time_s=round(env.sim_time, 3), wall_s=round(wall, 2),
                rtf=round(env.sim_time / max(wall, 1e-6), 3), timing_s={a: round(b, 2) for a, b in tm.items()},
                phases=[(round(a, 3), b) for a, b in pl.phase_log], events=events,
                grasp_rel_mm=[round(v * 1e3, 1) for v in pl.grasp_rel] if pl.grasp_rel else None,
                cams=list(cams), obj_ids=obj_ids, sim_device=env.sim_device, hold_debounce=pl.hold_debounce,
                **place_metrics(env, tgt, place))
    randomization_meta(env, meta)
    st["obj_ids"] = obj_ids
    return {"seed": seed, "kind": kind, "task": task, "variant": env.variant, "split": split_of(seed),
            "frames": frames, "actions": actions, "hold_n": hold_n, "stream": st, "meta": meta}


def _make_env(variant: str):
    from ..sim.randomize import check_train_variant
    from ..sim.scene import make_env
    check_train_variant(variant)
    return make_env(0, headless=True, cameras=CAMS, depth=False, variant=variant, render_interval=NO_RENDER)


def gen(out: str, variant: str, tasks, kinds, seeds, stale_s: float = 1800.0, H: int = H_DEFAULT,
        max_items: int | None = None) -> None:
    from ..cli_pool import warmup
    from ..sim.randomize import check_train_variant
    from .episode import finalize
    from .validate import stamp, validate_episode
    check_train_variant(variant)  # training data: standard / dr only, never the random TEST pool (D35)
    for kd in kinds:
        if kd not in ("P0", "P1", "P2"):
            raise SystemExit("DEV perturbations P0-P2 only")
    items = Q.plan([variant], tasks, kinds, seeds)
    env, n_done = None, 0
    chain = f"{out}/_workers/{variant}_{os.uname().nodename if hasattr(os, 'uname') else 'host'}_{os.getpid()}_" \
            f"{time.strftime('%Y%m%dT%H%M%S', time.gmtime())}.jsonl"
    seq = 0
    for it in items:
        if max_items is not None and n_done >= max_items:
            break
        if not Q.claim(out, it, stale_s):
            continue
        v, task, kind, seed = it
        folder = Q.ep_folder(out, v, task, kind)
        try:
            t0 = time.perf_counter()
            if env is None:
                env = _make_env(variant)
                warmup(env)  # the canonical run must not be the process's first run (replay exactness, pool.md)
                os.makedirs(os.path.dirname(chain), exist_ok=True)
            prefix(env, task)
            t_pre = time.perf_counter() - t0
            ep = record_episode(env, seed, task, kind, folder)
            ep["meta"].update(prefix_wall_s=round(t_pre, 2),
                              worker={"pid": os.getpid(), "gpu": os.environ.get("CUDA_VISIBLE_DEVICES"),
                                      "chain": os.path.relpath(chain, out), "seq": seq},
                              utc=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()))
            t1 = time.perf_counter()
            meta = finalize(ep, folder, H)
            with open(chain, "a") as f:  # the process history, for chain replay (replay --chain)
                f.write(json.dumps({"seq": seq, "variant": v, "task": task, "kind": kind, "seed": seed}) + "\n")
            seq += 1
            rep = validate_episode(folder, seed)
            stamp(folder, seed, rep)
            print("EP " + json.dumps({"item": Q.item_name(*it), "success": meta["success"], "stage": meta["stage"],
                                      "frames": meta["n_frames"], "sim_s": meta["sim_time_s"], "wall_s": meta["wall_s"],
                                      "prefix_s": meta["prefix_wall_s"], "write_s": round(time.perf_counter() - t1, 2),
                                      "valid": rep["valid_for_training"], "errors": rep["errors"][:3],
                                      "timing": meta["timing_s"]}), flush=True)
            n_done += 1
        finally:
            Q.release(out, it)


def _replay_actions(env, folder: str, seed: int, task: str):
    """Reset (seed, task) and re-execute an episode's recorded actions with the same 3/4-substep holds and the
    same perturbation writes at the same ticks; no planner, no rendering. Returns (object poses, arm q) per frame."""
    from ..sim import snapshot as S
    z = np.load(f"{folder}/ep{seed}.npz")
    meta = json.load(open(f"{folder}/ep{seed}.meta.json"))
    env.set_seed(seed, task)
    env.reset()
    ev_at = {e["k"]: e for e in meta.get("events", [])}
    obj_ids = [str(x) for x in z["obj_ids"]]
    pose = [np.stack([np.concatenate(env.object_pose(o)) for o in obj_ids])]
    qs = [env.robot.data.joint_pos[0, env.arm_ids].cpu().numpy()]
    for k in range(int(meta["n_actions"])):
        e = ev_at.get(k)
        if e is not None:  # the same one-shot perturbation write at the same tick
            env.write_object_pose(e["obj"], e["pose"][:3], tuple(e["pose"][3:]))
            if e["kind"] == "P2":
                env.present.append(e["obj"])
        S.step_partial(env, z["action"][k], int(z["hold_n"][k]))
        pose.append(np.stack([np.concatenate(env.object_pose(o)) for o in obj_ids]))
        qs.append(env.robot.data.joint_pos[0, env.arm_ids].cpu().numpy())
    return np.stack(pose), np.stack(qs), sorted(ev_at)


def replay(out: str, variant: str, task: str, kind: str, seed: int, chain: bool = False) -> dict:
    """Re-execute the recorded actions (no planner) and compare with the recording.
    chain=False: fresh history (warmup + canonical prefix), the pool.md convention. chain=True: first rebuild the
    generating process's history from its worker chain log (every earlier episode of that process: prefix + its
    recorded actions), so the PhysX state history before the episode is the recorded one."""
    from ..cli_pool import warmup
    folder = Q.ep_folder(out, variant, task, kind)
    z = np.load(f"{folder}/ep{seed}.npz")
    meta = json.load(open(f"{folder}/ep{seed}.meta.json"))
    K = int(meta["n_actions"])
    env = _make_env(variant)
    warmup(env)
    n_prev = 0
    if chain:
        w = meta["worker"]
        prev = [json.loads(x) for x in open(os.path.join(out, w["chain"]))][:w["seq"]]
        for p in prev:
            prefix(env, p["task"])
            _replay_actions(env, Q.ep_folder(out, p["variant"], p["task"], p["kind"]), p["seed"], p["task"])
        n_prev = len(prev)
    prefix(env, task)
    t_wall = time.perf_counter()
    pose, qs, ev_frames = _replay_actions(env, folder, seed, task)
    obj_ids = [str(x) for x in z["obj_ids"]]
    rec_pose = z["obj_pose"]
    dpos = np.linalg.norm(pose[:, :, :3] - rec_pose[:, :, :3], axis=-1)  # [K+1, n_obj] m
    spec = TK.TASKS[task]
    ti = obj_ids.index(spec.target)
    div = np.flatnonzero((dpos.max(1) > 1e-6) | (np.abs(qs - z["q"]).max(1) > 1e-6))
    out_r = {"item": Q.item_name(variant, task, kind, seed), "frames": K + 1, "chain": chain,
             "history_episodes_replayed": n_prev, "first_divergent_frame": int(div[0]) if len(div) else None,
             "event_frames": ev_frames,
             "end_target_err_mm": round(float(dpos[-1, ti]) * 1e3, 4),
             "end_any_object_err_mm": round(float(dpos[-1].max()) * 1e3, 4),
             "max_object_err_mm_over_episode": round(float(dpos.max()) * 1e3, 4),
             "max_joint_err_rad": float(np.abs(qs - z["q"]).max()),
             "time_s": round(time.perf_counter() - t_wall, 2),
             "recorded_end_target_xyz": [round(float(v), 5) for v in rec_pose[-1, ti, :3]],
             "replayed_end_target_xyz": [round(float(v), 5) for v in pose[-1, ti, :3]],
             "pass_5mm": bool(dpos[-1].max() <= 0.005)}
    os.makedirs(f"{folder}/rows", exist_ok=True)
    with open(f"{folder}/rows/ep{seed}.replay{'_chain' if chain else ''}.json", "w") as f:
        json.dump(out_r, f, indent=1)
    print("REPLAY " + json.dumps(out_r), flush=True)
    return out_r


# ================================================================================ pure modes
def check(out: str) -> dict:
    import glob
    from .episode import merge
    from .validate import stamp, validate_episode
    summ, folders = [], sorted({os.path.dirname(p) for p in glob.glob(f"{out}/*/*/*/ep*.meta.json")})
    for folder in folders:
        v, task, kind = folder.replace("\\", "/").split("/")[-3:]
        for mp in sorted(glob.glob(f"{folder}/ep*.meta.json")):
            seed = int(os.path.basename(mp)[2:-10])
            rep = validate_episode(folder, seed)
            stamp(folder, seed, rep)
            meta = json.load(open(mp))
            byt = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(f"{folder}/img/ep{seed}") for f in fs)
            for suf in (".jsonl", ".npz", ".meta.json"):
                byt += os.path.getsize(f"{folder}/ep{seed}{suf}")
            for suf in (".stageb.jsonl", ".labels_v2.jsonl"):
                byt += os.path.getsize(f"{folder}/rows/ep{seed}{suf}")
            summ.append({"variant": v, "task": task, "kind": kind, "seed": seed, "success": meta["success"],
                         "stage": meta.get("stage"), "valid": rep["valid_for_training"], "errors": rep["errors"][:2],
                         "frames": rep["frames"], "rows": rep["rows"], "decisions": rep["decisions"],
                         "sim_s": meta["sim_time_s"], "wall_s": meta["wall_s"], "prefix_s": meta.get("prefix_wall_s"),
                         "bytes": byt, "tgt_place_xy_mm": meta.get("tgt_place_xy_mm")})
        print("MERGE " + json.dumps(merge(folder)), flush=True)
    with open(f"{out}/check.json", "w") as f:
        json.dump(summ, f, indent=1)
    n = len(summ)
    tot = {"episodes": n, "success": sum(s["success"] for s in summ), "valid": sum(s["valid"] for s in summ),
           "frames": sum(s["frames"] for s in summ), "rows": sum(s["rows"] for s in summ),
           "gb": round(sum(s["bytes"] for s in summ) / 1e9, 3)}
    print("CHECK " + json.dumps(tot), flush=True)
    return tot


def sheet(out: str, dst: str, seed: int = 0, kind: str = "P0", width: int = 224) -> None:
    """One row per (variant, task): head | wrist at the first frame, at grasp (first lift) and at place (first
    open). Thumbnails keep the aspect ratio; JPEG quality lowered until the sheet is < 300 KB."""
    import glob

    from PIL import Image, ImageDraw
    rows = []
    for folder in sorted(glob.glob(f"{out}/*/*/{kind}")):
        v, task = folder.replace("\\", "/").split("/")[-3:-1]
        p = f"{folder}/ep{seed}.jsonl"
        if not os.path.exists(p):
            continue
        lines = [json.loads(x) for x in open(p)]
        pick = [0]
        for ph in ("lift", "open"):
            pick.append(next((ln["k"] for ln in lines if ln["phase"] == ph), len(lines) - 1))
        rows.append((f"{v} {task} s{seed}", [(lines[i], folder) for i in pick]))
    hh, hw = int(width * 376 / 672), int(width * 240 / 424)
    rh = max(hh, hw) + 14
    W = width * 6
    img = Image.new("RGB", (W, rh * len(rows)), (20, 20, 20))
    d = ImageDraw.Draw(img)
    for r, (name, cells) in enumerate(rows):
        for c, (ln, folder) in enumerate(cells):
            for j, cam in enumerate(CAMS):
                im = Image.open(os.path.join(folder, ln["images"][cam])).convert("RGB")
                im = im.resize((width, hh if cam == "cam_head" else hw))
                x, y = (2 * c + j) * width, r * rh + 14
                img.paste(im, (x, y))
                d.text((x + 3, y + 2), f"k{ln['k']} {ln['phase']} {'head' if j == 0 else 'wrist'}", fill=(255, 255, 0))
        d.text((3, r * rh + 1), name, fill=(255, 255, 255))
    for q in (85, 75, 65, 55, 45):
        img.save(dst, quality=q, optimize=True)
        if os.path.getsize(dst) < 300_000:
            break
    print("SHEET " + json.dumps({"dst": dst, "rows": len(rows), "bytes": os.path.getsize(dst), "quality": q}))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["gen", "replay", "check", "sheet"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--variant", default="standard", choices=["standard", "random", "dr"],
                    help="random is refused for generation (TEST pool, never training data)")
    ap.add_argument("--tasks", default="all")
    ap.add_argument("--task", default="mug_tray")
    ap.add_argument("--kinds", default="P0")
    ap.add_argument("--kind", default="P0")
    ap.add_argument("--seeds", default="0-5")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--confirm-train", action="store_true", help="allow R2_TRAIN_SEEDS (stage-B generation)")
    ap.add_argument("--chain", action="store_true", help="replay: rebuild the generating process's history first")
    ap.add_argument("--stale-s", type=float, default=1800.0)
    ap.add_argument("--max-items", type=int, default=None)
    ap.add_argument("--H", type=int, default=H_DEFAULT)
    ap.add_argument("--dst", default=None)
    a = ap.parse_args(argv)
    if a.mode == "check":
        check(a.out)
        return
    if a.mode == "sheet":
        sheet(a.out, a.dst or f"{a.out}/r2_frames.jpg", seed=a.seed, kind=a.kind)
        return
    if a.mode == "gen":
        tasks = list(TK.TASK_IDS) if a.tasks == "all" else [TK.check_task(t) for t in a.tasks.split(",")]
        gen(a.out, a.variant, tasks, a.kinds.split(","), parse_seeds(a.seeds, a.confirm_train), a.stale_s, a.H,
            a.max_items)
    else:
        check_r2_seed(a.seed, a.confirm_train)
        replay(a.out, a.variant, TK.check_task(a.task), a.kind, a.seed, a.chain)
    os._exit(0)  # SimulationApp.close() hangs in this chroot; results are already flushed


if __name__ == "__main__":
    main()
