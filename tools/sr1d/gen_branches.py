"""E-SR1d real-data branch generation (docs/stage3/prereg_sr1d.md §2; CPU only, numpy; no simulator).

For every S-E2E TRAIN row (se2e_c1 <kind>.stageb.jsonl) whose authority proxy is eligible (tools/sr1d/strata.py
meta: stratum 'far' = a 1; --mode all: every stratum, the registered fallback) and whose label dir_xy exists: K = 4
forced decisions (sr1c_branch.forced_decisions: 4 of the 8 directions without the label, dir_z and mag uniform; RNG
seeded by (SALT, kind, seed, k)), per decision the forced-direction chunk (sr1d_kin.ik_chunk from the row's first
recorded target, H = 5 at 10 Hz, joint step capped per joint by the dataset's recorded p99.9, URDF limits) and the
kinematic validity checks (sr1d_kin.validity: IK residual, episode floor, grasp height when closed, workspace box,
other arm, per-tick speed, end point >= 5 cm from the event points). Accepted chunks are written as stage-B rows
(sr1c_branch.branch_row) with the checks' values in row['branch']; every rejection is counted per reason and
direction. The FK direction of every accepted chunk (FK(last) - FK(first), the label / metric definition) is
compared with the forced direction.
  python tools/sr1d/gen_branches.py --rows /data/harvest/data/se2e_c1/conv --meta DIR/meta.jsonl \
      --stats DIR/stats.json --out /data/harvest/data/sr1d/branches [--mode far|all] [--limit-snaps N] [--procs 12]
Outputs <out>/<kind>_<part>.jsonl and <out>/stats.json.
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

SALT = "sr1d-branch@v1"
K = 4
URDF = "/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf"
KINDS = ("RB1", "RB2")


def snap_seed(kind, seed, k) -> int:
    return int(hashlib.sha256(f"{SALT}|{kind}|{seed}|{k}".encode()).hexdigest()[:16], 16)


def eligible(meta: dict, mode: str) -> bool:
    if meta["split"] != "train":
        return False
    return meta["stratum"] == "far" if mode == "far" else True


def plan_snapshot(chain, limits, row, meta, ds, rng, K=K):
    """[(forced, branch row or None, reason, info)] for one eligible row."""
    from harvest.train import sr1c_branch as B
    from harvest.train import sr1d_kin as S
    out = []
    q_b = np.asarray(row["action_exec"][0][:7], float)
    ee = np.asarray(meta["ee"], float)
    env = ds["envelope"][row["arm"]]
    other = meta["other_ee"]
    for f in B.forced_decisions(meta["label_xy"], rng, K):
        u = B.direction(f["dir_xy"], f["dir_z"])
        disp, scale = S.cap_disp(B.MAG_M[f["mag_coarse"]] * u, ds["chunk_cap_m"])
        Q, ik = S.ik_chunk(chain, limits, q_b, disp, ds["dq_p999"], H=row["H"])
        info = {"disp": [round(float(v), 6) for v in disp], "cap_scale": round(scale, 4),
                "ik_pos_err_mm": round(ik["pos_err_max_m"] * 1e3, 3), "ik_rot_err_deg": round(ik["rot_err_max_deg"], 3)}
        if not ik["ok"]:
            out.append((f, None, "ik", info))
            continue
        p, _ = B.fk_pose(chain, Q)
        dfk = p[-1] - p[0]
        path = ee + (p - p[0])
        end_d = min((float(np.linalg.norm(path[-1] - np.asarray(e, float))) for e in meta["ev_pts"]), default=None)
        dq = np.abs(np.diff(Q, axis=0)).max(0)
        info.update(fk_disp=[round(float(v), 6) for v in dfk], dir_err_deg=round(S.dir_err_deg(dfk, u), 3),
                    dq_max=[round(float(v), 5) for v in dq],
                    dq_ratio=round(float((dq / np.asarray(ds["dq_p999"])).max()), 4),
                    tick_speed_max=round(float(np.linalg.norm(np.diff(path, axis=0), axis=1).max()), 5),
                    path_zmin=round(float(path[:, 2].min()), 5), floor_z=meta["floor_z"], hold_z=meta["hold_z"],
                    other_min=round(float(np.linalg.norm(path - np.asarray(other, float), axis=1).min()), 5),
                    end_event_dist=None if end_d is None else round(end_d, 5),
                    jlim_viol=int(np.sum((Q < limits[:, 0][None] - 1e-9) & (Q < q_b[None] - 1e-9))
                                  + np.sum((Q > limits[:, 1][None] + 1e-9) & (Q > q_b[None] + 1e-9))))
        reason = S.validity(path, meta["floor_z"], meta["hold_z"], env["lo"], env["hi"], other,
                            ds["ee_tick_speed_p999"], end_d)
        if reason is None:
            out.append((f, B.branch_row(row, f, Q, {**info, "ok": True}), None, info))
        else:
            out.append((f, None, reason, info))
    return out


def run_part(job):
    rows_path, meta_path, stats_path, out, kind, part, nparts, mode, limit = job
    from harvest.train import sr1c_branch as B
    from harvest.train.se2e_data import load_arm_chain, needed_cams
    ds = json.load(open(stats_path))["datasets"][kind]
    chain = {arm: load_arm_chain(URDF, arm) for arm in ("left", "right")}
    limits = {arm: B.joint_limits(URDF, arm) for arm in ("left", "right")}
    meta = {}
    for x in open(meta_path, encoding="utf-8"):
        m = json.loads(x)
        if m["kind"] == kind and m["seed"] % nparts == part:
            meta[(m["seed"], m["k"])] = m
    st = {"kind": kind, "part": part, "rows": 0, "train_rows": 0, "eligible": 0, "snaps": 0, "branches": 0,
          "no_label": 0, "rejected": {}, "rejected_by_dir": {}, "by_dir": {}, "by_mag": {}, "by_z": {},
          "cap_scaled": 0, "jlim_viol": 0, "no_cams": 0, "dir_err": [], "mag": [], "dq_ratio": [],
          "tick_speed": [], "by_stratum": {}, "cand_by_dir": {}}
    dst = os.path.join(out, f"{kind}_{part:02d}.jsonl")
    with open(dst + ".part", "w", encoding="utf-8") as w:
        for x in open(rows_path, encoding="utf-8"):
            row = json.loads(x)
            if row["seed"] % nparts != part:
                continue
            st["rows"] += 1
            m = meta[(row["seed"], row["k"])]
            if m["split"] != "train":
                continue
            st["train_rows"] += 1
            if not eligible(m, mode):
                continue
            st["eligible"] += 1
            if not set(needed_cams(row)) <= set(row.get("images") or {}):
                st["no_cams"] += 1  # not a training sample (se2e_data.load_se2e skips it)
                continue
            if limit and st["snaps"] >= limit:
                continue
            if not m["label_xy"]:
                st["no_label"] += 1
                continue
            st["snaps"] += 1
            st["by_stratum"][m["stratum"]] = st["by_stratum"].get(m["stratum"], 0) + 1
            rng = np.random.default_rng(snap_seed(kind, row["seed"], row["k"]))
            for f, br, reason, info in plan_snapshot(chain[row["arm"]], limits[row["arm"]], row, m, ds, rng):
                d = f["dir_xy"]
                st["cand_by_dir"][d] = st["cand_by_dir"].get(d, 0) + 1
                if br is None:
                    st["rejected"][reason] = st["rejected"].get(reason, 0) + 1
                    st["rejected_by_dir"][d] = st["rejected_by_dir"].get(d, 0) + 1
                    continue
                br["branch"].update(label_dir_xy=m["label_xy"], stratum=m["stratum"], a=m["a"], d=m["d"],
                                    holding=m["holding"])
                st["branches"] += 1
                st["cap_scaled"] += info["cap_scale"] < 1.0
                st["jlim_viol"] += info["jlim_viol"]
                st["dir_err"].append(info["dir_err_deg"])
                st["mag"].append(float(np.linalg.norm(info["fk_disp"])))
                st["dq_ratio"].append(info["dq_ratio"])
                st["tick_speed"].append(info["tick_speed_max"])
                for key, v in (("by_dir", d), ("by_mag", f["mag_coarse"]), ("by_z", f["dir_z"])):
                    st[key][v] = st[key].get(v, 0) + 1
                w.write(json.dumps(br) + "\n")
    os.replace(dst + ".part", dst)
    return st


def q(x, ps=(50, 90, 99, 100)):
    return {str(p): float(np.percentile(x, p)) for p in ps} if len(x) else {}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", default="/data/harvest/data/se2e_c1/conv")
    ap.add_argument("--meta", required=True)
    ap.add_argument("--stats", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mode", default="far", choices=("far", "all"))
    ap.add_argument("--limit-snaps", type=int, default=0, help="first N eligible rows per part (dry run)")
    ap.add_argument("--procs", type=int, default=12)
    ap.add_argument("--parts", type=int, default=6, help="parts per dataset (episode % parts)")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    jobs = [(os.path.join(a.rows, f"{kind}.stageb.jsonl"), a.meta, a.stats, a.out, kind, p, a.parts, a.mode,
             a.limit_snaps) for kind in KINDS for p in range(a.parts)]
    with Pool(min(a.procs, len(jobs))) as pool:
        stats = pool.map(run_part, jobs)
    tot = {k: sum(s[k] for s in stats) for k in ("rows", "train_rows", "eligible", "snaps", "branches", "no_label",
                                                  "cap_scaled", "jlim_viol", "no_cams")}
    for key in ("rejected", "rejected_by_dir", "by_dir", "by_mag", "by_z", "by_stratum", "cand_by_dir"):
        tot[key] = {}
        for s in stats:
            for k2, v in s[key].items():
                tot[key][k2] = tot[key].get(k2, 0) + v
    for key in ("dir_err", "mag", "dq_ratio", "tick_speed"):
        tot[key + "_q"] = q(np.concatenate([np.asarray(s[key], float) for s in stats]))
    tot["dir_err_gt10"] = int(sum(np.sum(np.asarray(s["dir_err"]) > 10.0) for s in stats))
    tot["dir_err_gt45"] = int(sum(np.sum(np.asarray(s["dir_err"]) > 45.0) for s in stats))
    tot["reject_rate"] = 1 - tot["branches"] / max(1, K * tot["snaps"])
    tot["reject_rate_by_dir"] = {d: tot["rejected_by_dir"].get(d, 0) / n for d, n in tot["cand_by_dir"].items()}
    for s in stats:
        for key in ("dir_err", "mag", "dq_ratio", "tick_speed"):
            s.pop(key)
    res = {"salt": SALT, "K": K, "mode": a.mode, "limit_snaps": a.limit_snaps, "parts": stats, "total": tot,
           "wall_s": round(time.time() - t0, 1), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    json.dump(res, open(os.path.join(a.out, "stats.json"), "w"), indent=1)
    print(json.dumps({"total": tot, "wall_s": res["wall_s"]}), flush=True)


if __name__ == "__main__":
    main()
