"""E-SR1c gate G-br (docs/stage3/prereg_sr1c.md §0): physical validity of the counterfactual branches in Isaac (CPU
PhysX, no rendering; IR_ROOT=cyclo, IR_INST=sr1c_*), GPU 0.

Selection (pure, seeded): whole far snapshots in a seeded random order until >= N branch rows (all of a snapshot's
accepted branches), from the branch files of one variant.
Per snapshot: the recorded episode is replayed from reset to the snapshot frame k (datagen.gen._replay_actions logic,
perturbation writes at their ticks; fidelity = max |q - q_rec| and max object error at k), then
  hold    the base target (action_exec[0]) for H ticks + SETTLE ticks (reference: cancels the command lead and the
          gravity sag of the recorded targets),
  branch  each branch chunk (H targets, the recorded 3 / 4-substep holds) + SETTLE ticks of its last target,
each from its own replay. Measured (table frame): finger midpoint per tick, object poses, finger-object contacts.
Per branch: track_err = |(tcp_branch_end - tcp_hold_end) - (FK(target_last) - FK(target_0))| (settled end points),
dir_ok = angle(measured branch displacement vs hold, forced unit direction) <= 45 deg, table = min pad-bottom height
(tcp z - PAD_BELOW_M) < 0 during the branch, object = a finger contact with a non-held object or a non-held object moved
> OBJ_MOVE_M relative to the hold run, near_end = stage-target distance at the settled end < 5 cm, holding_end
(held-object branches: the target still in the gripper, outside the gate).
  IR_ROOT=cyclo IR_INST=sr1c_brA ./ir_run.sh env ... /isaac-sim/python.sh tools/sr1c/replay_check.py \
      --branches DIR --variant dr --n 100 --out OUT.jsonl
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

import numpy as np  # noqa: E402

SETTLE = 10
OBJ_MOVE_M = 0.003
PAD_BELOW_M = 0.027
DIR_TOL_DEG = 45.0
NEAR_M = 0.05


def pick(rows_by_snap: dict, n: int, seed: int = 0) -> list:
    """Snapshot keys in a seeded random order until the chosen snapshots hold >= n branch rows."""
    keys = sorted(rows_by_snap)
    order = np.random.default_rng(seed).permutation(len(keys))
    out, tot = [], 0
    for i in order:
        if tot >= n:
            break
        out.append(keys[i])
        tot += len(rows_by_snap[keys[i]])
    return out


def angle_deg(a, b) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na < 1e-9 or nb < 1e-9:
        return 180.0
    return math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(a, b) / (na * nb))))))


def branch_metrics(cmd_disp, forced_unit, tcp_hold_end, tcp_br_end, tcp_br_path, contacts_nonheld, obj_move_max,
                   stage_end_dist) -> dict:
    meas = np.asarray(tcp_br_end, float) - np.asarray(tcp_hold_end, float)
    return {"track_err_mm": round(1e3 * float(np.linalg.norm(meas - np.asarray(cmd_disp, float))), 3),
            "dir_err_deg": round(angle_deg(meas, forced_unit), 2),
            "dir_ok": angle_deg(meas, forced_unit) <= DIR_TOL_DEG,
            "min_pad_z_mm": round(1e3 * float(np.min(np.asarray(tcp_br_path, float)[:, 2]) - PAD_BELOW_M), 2),
            "table": bool(np.min(np.asarray(tcp_br_path, float)[:, 2]) - PAD_BELOW_M < 0.0),
            "object": bool(contacts_nonheld) or obj_move_max > OBJ_MOVE_M,
            "obj_move_max_mm": round(1e3 * obj_move_max, 3), "contacts_nonheld": sorted(contacts_nonheld),
            "near_end": stage_end_dist < NEAR_M, "stage_end_dist_m": round(float(stage_end_dist), 4),
            "meas_disp": [round(float(v), 5) for v in meas]}


def gate(recs: list, gen_stats: dict | None = None) -> dict:
    """G-br rule: median track <= 3 mm, p90 <= 8 mm, penetration (table / object) 0, dir_ok 100 %, near_end 0;
    and (from the generator) no direction with a filter rejection rate > 50 %."""
    tr = np.array([r["track_err_mm"] for r in recs])
    out = {"n": len(recs), "track_median_mm": float(np.median(tr)), "track_p90_mm": float(np.quantile(tr, 0.9)),
           "table": sum(r["table"] for r in recs), "object": sum(r["object"] for r in recs),
           "dir_ok_rate": float(np.mean([r["dir_ok"] for r in recs])), "near_end": sum(r["near_end"] for r in recs)}
    held = [r["holding_end"] for r in recs if r.get("held")]
    out["held_n"], out["held_kept"] = len(held), (float(np.mean(held)) if held else None)
    ok = (out["track_median_mm"] <= 3.0 and out["track_p90_mm"] <= 8.0 and out["table"] == 0 and out["object"] == 0
          and out["dir_ok_rate"] == 1.0 and out["near_end"] == 0)
    if gen_stats is not None:
        acc, rej = gen_stats["by_dir"], gen_stats["rejected_by_dir"]
        rate = {d: rej.get(d, 0) / max(1, rej.get(d, 0) + acc.get(d, 0)) for d in set(acc) | set(rej)}
        out["reject_rate_by_dir"] = rate
        ok = ok and max(rate.values()) <= 0.5
    out["pass"] = bool(ok)
    return out


# ------------------------------------------------------------------------------------------ Isaac part (pod)
def _run_to(env, z, meta, k):
    from harvest.sim import snapshot as S
    ev_at = {e["k"]: e for e in meta.get("events", [])}
    for kk in range(k):
        e = ev_at.get(kk)
        if e is not None:
            env.write_object_pose(e["obj"], e["pose"][:3], tuple(e["pose"][3:]))
            if e["kind"] == "P2":
                env.present.append(e["obj"])
        S.step_partial(env, z["action"][kk], int(z["hold_n"][kk]))


def _exec(env, acts, z, k, tgt_ids):
    """Execute targets from frame k (recorded holds), then SETTLE ticks of the last one. Returns tcp path (table),
    the end tcp, finger-contact object ids, object poses at the end."""
    from harvest.datagen.timing import hold_substeps
    from harvest.sim import snapshot as S
    from harvest.sim.oracle_state import oracle_objects, to_table_frame
    path, cont = [], set()
    seq = list(acts) + [acts[-1]] * SETTLE
    for i, a in enumerate(seq):
        kk = k + i
        n = int(z["hold_n"][kk]) if kk < len(z["hold_n"]) else hold_substeps(kk)
        S.step_partial(env, np.asarray(a, np.float32), n)
        path.append(to_table_frame(env.finger_mid(), env.table_top_z))
        _, _, contacts, _ = oracle_objects(env)
        for c in contacts:
            if "gripper" in c:
                cont |= set(c) - {"gripper"}
    poses = {o: np.asarray(env.object_pose(o)[0], float) for o in tgt_ids}
    return np.array(path), path[-1], cont, poses


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--branches", required=True)
    ap.add_argument("--variant", required=True, choices=("dr", "standard"))
    ap.add_argument("--r2", default="/data/harvest/r2/train")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    from harvest.cli_pool import warmup
    from harvest.datagen.gen import _make_env
    from harvest.sim.oracle_state import to_table_frame
    from harvest.sim.tasks import TASKS
    from harvest.train import sr1c_branch as B
    from harvest.train.se2e_data import load_arm_chain
    chain = load_arm_chain("/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf", "right")
    by = {}
    for p in sorted(glob.glob(os.path.join(a.branches, f"{a.variant}_*.jsonl"))):
        for x in open(p, encoding="utf-8"):
            r = json.loads(x)
            by.setdefault((r["variant"], r["task"], r["kind"], r["seed"], r["k"]), []).append(r)
    keys = pick(by, a.n, a.seed)
    env = _make_env(a.variant)
    warmup(env)
    w = open(a.out, "w")
    t0 = time.time()
    for (v, task, kind, seed, k) in keys:
        folder = os.path.join(a.r2, v, task, kind)
        z = np.load(os.path.join(folder, f"ep{seed}.npz"))
        meta = json.load(open(os.path.join(folder, f"ep{seed}.meta.json")))
        ids = [str(o) for o in z["obj_ids"]]
        spec = TASKS[task]
        brs = by[(v, task, kind, seed, k)]
        held = brs[0]["branch"].get("held")

        def replay():
            env.set_seed(seed, task)
            env.reset()
            _run_to(env, z, meta, k)
            q = env.robot.data.joint_pos[0, env.arm_ids].cpu().numpy()
            obj = np.stack([np.concatenate(env.object_pose(o)) for o in ids])
            return (float(np.abs(q - z["q"][k]).max()),
                    float(np.linalg.norm(obj[:, :3] - z["obj_pose"][k][:, :3], axis=1).max()))
        fid = replay()
        base = [brs[0]["action_exec"][0]] * brs[0]["H"]
        _, hold_end, _, hold_poses = _exec(env, base, z, k, ids)
        for br in brs:
            fid_b = replay()
            path, end, cont, poses = _exec(env, br["action_exec"], z, k, ids)
            nonheld = {o for o in cont if o != held}
            move = max([float(np.linalg.norm(poses[o] - hold_poses[o])) for o in ids if o != held
                        and abs(hold_poses[o][0]) < 2.0] or [0.0])
            P, _ = B.fk_pose(chain, np.asarray(br["action_exec"], float)[:, :7])
            f = br["committed"]
            stage_obj = spec.target if br["phase_id"] in ("approach", "descend", "close", "lift") else spec.place
            end_dist = float(np.linalg.norm(to_table_frame(poses[stage_obj], env.table_top_z) - end))
            m = branch_metrics(P[-1] - P[0], B.direction(f["dir_xy"], f["dir_z"]), hold_end, end, path, nonheld,
                               move, end_dist)
            rec = {"id": f"{v}/{task}/{kind}/ep{seed}/k{k}", "phase": br["phase_id"], "forced": f, "held": held,
                   "fidelity_q_rad": fid_b[0], "fidelity_obj_m": fid_b[1], **m}
            if held:
                rec["holding_end"] = held in cont and float(to_table_frame(poses[held], env.table_top_z)[2]) > 0.06
            w.write(json.dumps(rec) + "\n")
            w.flush()
        print(json.dumps({"snap": f"{v}/{task}/{kind}/ep{seed}/k{k}", "n_br": len(brs), "fid": fid,
                          "elapsed_s": round(time.time() - t0, 1)}), flush=True)
    w.close()
    os._exit(0)  # SimulationApp.close() hangs in this chroot (datagen.gen)


if __name__ == "__main__":
    main()
