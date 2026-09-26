"""E-SR1c branch generation (docs/stage3/prereg_sr1c.md §2; CPU only, no rendering).

For every R2_TRAIN view folder <root>/<variant>/<task>/<kind> except the task bottle_tray: every stage-B row of a FIT
episode (pool line split "fit") whose privileged authority is 1 (sr1c_authority.privileged: stage distance >= 10 cm,
no contact phase, no contact) gets K = 4 forced decisions (sr1c_branch.forced_decisions, label dir_xy excluded; RNG
seeded by (SALT, variant, task, kind, seed, k)) and, per decision, the forced-direction IK chunk; a branch that passes
the filters is written as a stage-B row (sr1c_branch.branch_row). Rejections are counted per reason and direction.
  python tools/sr1c/gen_branches.py --view /data/harvest/data/ma2/view --r2 /data/harvest/r2/train \
      --out /data/harvest/data/sr1c/branches [--limit-snaps N] [--folders v/t/k,...] [--procs 12]
Outputs <out>/<variant>_<task>_<kind>.jsonl (branch rows) and <out>/stats.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

import numpy as np  # noqa: E402

SALT = "sr1c-branch@v1"
K = 4
EXCLUDE_TASKS = ("bottle_tray",)
URDF = "/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf"
TABLE_TOP_Z = 0.85


def snap_seed(variant, task, kind, seed, k) -> int:
    h = hashlib.sha256(f"{SALT}|{variant}|{task}|{kind}|{seed}|{k}".encode()).hexdigest()[:16]
    return int(h, 16)


def plan_snapshot(chain, limits, row, label_xy, tcp_table, objs, held, rng, K=K):
    """[(forced, branch row or None, reason)] for one far snapshot. objs: {id: box dict} of the present objects
    (table frame); held: id of the held object or None."""
    from harvest.train import sr1c_authority as A
    from harvest.train import sr1c_branch as B
    out = []
    reg = row["aux"]["reg"]
    g2t = np.array([reg["g2tgt_dx"], reg["g2tgt_dy"], reg["g2tgt_dz"]], float)
    t2p = np.array([reg["tgt2place_dx"], reg["tgt2place_dy"], reg["tgt2place_dz"]], float)
    stage_vec = g2t if row["phase_id"] in A.PICK_PHASES else g2t - t2p  # (stage target - gripper)
    q_b = np.asarray(row["action_exec"][0][:7], float)
    for f in B.forced_decisions(label_xy, rng, K):
        disp0 = B.MAG_M[f["mag_coarse"]] * B.direction(f["dir_xy"], f["dir_z"])
        disp, scale = B.cap_disp(disp0, H=row["H"])
        Q, info = B.ik_chunk(chain, limits, q_b, disp, H=row["H"])
        info = {"disp": [round(float(v), 6) for v in disp], "cap_scale": round(scale, 4),
                "ik_pos_err_mm": round(info["pos_err_max_m"] * 1e3, 3),
                "ik_rot_err_deg": round(info["rot_err_max_deg"], 3), "ok": info["ok"]}
        if not info["ok"]:
            out.append((f, None, "ik"))
            continue
        p, _ = B.fk_pose(chain, Q)
        path = tcp_table + (p - p[0])
        reason = None
        if not B.table_ok(path):
            reason = "table"
        elif any(B.gripper_hits_box(x, box) for x in path for o, box in objs.items() if o != held):
            reason = "object"
        elif held is not None:
            hb = objs[held]
            for dd in (p - p[0]):
                moved = {"center": hb["center"] + dd, "half": hb["half"]}
                if moved["center"][2] - moved["half"][2] < B.TABLE_MARGIN_M:
                    reason = "held_table"
                    break
                if any(B.boxes_overlap(moved, box) for o, box in objs.items() if o != held):
                    reason = "held_object"
                    break
        if reason is None and float(np.linalg.norm(stage_vec - (p[-1] - p[0]))) < B.NEAR_END_M:
            reason = "near_end"
        if reason is None:
            info["end_stage_dist_m"] = round(float(np.linalg.norm(stage_vec - (p[-1] - p[0]))), 4)
            out.append((f, B.branch_row(row, f, Q, info), None))
        else:
            out.append((f, None, reason))
    return out


def run_folder(job):
    view, r2, out, fo, limit = job
    from harvest.sim.scene import OBJ_GEOM
    from harvest.train import sr1c_authority as A
    from harvest.train import sr1c_branch as B
    from harvest.train.se2e_data import load_arm_chain
    from harvest.train.stagea_data import split_of
    variant, task, kind = fo.split("/")
    chain = load_arm_chain(URDF, "right")
    limits = B.joint_limits(URDF, "right")
    base = os.path.join(view, variant, task)
    labels = {}
    for x in open(os.path.join(base, f"{kind}.labels_v2.jsonl"), encoding="utf-8"):
        r = json.loads(x)
        labels[(r["seed"], r["k"])] = r["labels_v2"]
    split = {}
    st = {"folder": fo, "rows": 0, "fit_rows": 0, "far": 0, "snaps": 0, "branches": 0, "rejected": {},
          "rejected_by_dir": {}, "by_dir": {}, "by_mag": {}, "by_z": {}, "by_phase": {}, "cap_scaled": 0,
          "no_label": 0}
    dst = os.path.join(out, f"{variant}_{task}_{kind}.jsonl")
    tmp = dst + ".part"
    npz_cache = {}
    with open(tmp, "w", encoding="utf-8") as w:
        for x in open(os.path.join(base, f"{kind}.stageb.jsonl"), encoding="utf-8"):
            row = json.loads(x)
            st["rows"] += 1
            seed = row["seed"]
            if seed not in split:
                ln = json.loads(open(os.path.join(base, kind, f"ep{seed}.jsonl"), encoding="utf-8").readline())
                split[seed] = split_of(ln)
            if split[seed] != "train":
                continue
            st["fit_rows"] += 1
            if A.privileged(row["aux"], row["phase_id"]) != 1.0:
                continue
            st["far"] += 1
            if limit and st["snaps"] >= limit:
                continue
            lab = labels.get((seed, row["k"]))
            if lab is None or lab.get("dir_xy") is None:
                st["no_label"] += 1
                continue
            if seed not in npz_cache:
                npz_cache.clear()
                npz_cache[seed] = np.load(os.path.join(r2, variant, task, kind, f"ep{seed}.npz"), allow_pickle=True)
            z = npz_cache[seed]
            k = row["k"]
            ids = [str(o) for o in z["obj_ids"]]
            objs = {}
            for i, o in enumerate(ids):
                pos = np.asarray(z["obj_pose"][k][i][:3], float) - np.array([0, 0, TABLE_TOP_Z])
                if abs(pos[0]) > 2.0 or abs(pos[1]) > 2.0 or OBJ_GEOM[o]["shape"] == "marker":
                    continue  # parked behind the robot / visual-only marker
                objs[o] = B.obj_box(pos, z["obj_pose"][k][i][3:], OBJ_GEOM[o])
            held = None
            if row["aux"]["cls"].get("holding_tgt") == 1:
                from harvest.sim.tasks import TASKS
                held = TASKS[task].target
            rng = np.random.default_rng(snap_seed(variant, task, kind, seed, k))
            st["snaps"] += 1
            st["by_phase"][row["phase_id"]] = st["by_phase"].get(row["phase_id"], 0) + 1
            for f, br, reason in plan_snapshot(chain, limits, row, lab["dir_xy"], np.asarray(z["tcp"][k], float),
                                               objs, held, rng):
                d = f["dir_xy"]
                if br is None:
                    st["rejected"][reason] = st["rejected"].get(reason, 0) + 1
                    st["rejected_by_dir"][d] = st["rejected_by_dir"].get(d, 0) + 1
                    continue
                br["branch"].update(label_dir_xy=lab["dir_xy"], held=held)
                st["branches"] += 1
                st["cap_scaled"] += br["branch"]["cap_scale"] < 1.0
                for key, v in (("by_dir", d), ("by_mag", f["mag_coarse"]), ("by_z", f["dir_z"])):
                    st[key][v] = st[key].get(v, 0) + 1
                w.write(json.dumps(br) + "\n")
    os.replace(tmp, dst)
    return st


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--view", default="/data/harvest/data/ma2/view")
    ap.add_argument("--r2", default="/data/harvest/r2/train")
    ap.add_argument("--out", required=True)
    ap.add_argument("--folders", default="", help="v/t/k,... (default: every folder without bottle_tray)")
    ap.add_argument("--limit-snaps", type=int, default=0, help="first N far snapshots per folder (dry run)")
    ap.add_argument("--procs", type=int, default=12)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    if a.folders:
        folders = a.folders.split(",")
    else:
        folders = sorted(f"{v}/{t}/{k}" for v in os.listdir(a.view) for t in os.listdir(os.path.join(a.view, v))
                         if t not in EXCLUDE_TASKS for k in ("P0", "P1", "P2")
                         if os.path.isdir(os.path.join(a.view, v, t, k)))
    t0 = time.time()
    jobs = [(a.view, a.r2, a.out, f, a.limit_snaps) for f in folders]
    with Pool(min(a.procs, len(jobs))) as pool:
        stats = pool.map(run_folder, jobs)
    tot = {k: sum(s[k] for s in stats) for k in ("rows", "fit_rows", "far", "snaps", "branches", "cap_scaled",
                                                  "no_label")}
    for key in ("rejected", "rejected_by_dir", "by_dir", "by_mag", "by_z", "by_phase"):
        tot[key] = {}
        for s in stats:
            for k2, v in s[key].items():
                tot[key][k2] = tot[key].get(k2, 0) + v
    res = {"salt": SALT, "K": K, "exclude_tasks": EXCLUDE_TASKS, "limit_snaps": a.limit_snaps, "folders": stats,
           "total": tot, "wall_s": round(time.time() - t0, 1),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    json.dump(res, open(os.path.join(a.out, "stats.json"), "w"), indent=1)
    print(json.dumps({"total": tot, "wall_s": res["wall_s"]}), flush=True)


if __name__ == "__main__":
    main()
