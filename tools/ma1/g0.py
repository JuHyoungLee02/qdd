"""E-MA1 gate G0 (docs/stage3/prereg_ma1.md §2): does the nominal head-camera model (URDF head chain + ZED Mini VGA
intrinsics, harvest/train/se2e_trace.py) project the active end effector onto the gripper in the S-E2E head frames?

  python tools/ma1/g0.py select --rows-root /data/harvest/data/se2e_c1/conv --urdf F --out frames.jsonl
      120 val frames (RB1 60 + RB2 60, left / right arm half each, seed 0): FK end effector (arm_base_link), head joint
      angles (RB1: fixed RB1_HEAD), nominal projection, calibration-half flag
  python tools/ma1/g0_point.py ...   Molmo2-ER reference pixel per frame ("point to the <arm> robot gripper")
  python tools/ma1/g0.py judge --frames frames.jsonl --points points.jsonl --urdf F --out g0.json

judge (rule fixed in the prereg): reference failures (no point) are excluded and counted (no human fallback in this
run); fewer than G0_MIN_VALID valid -> "insufficient_references" (fail -> R2). Pass <=> median pixel error <= 12 and
90th percentile <= 30 over the valid frames (672x376). Else per source a 6-DoF camera-frame correction is fitted on the
calibration half (robust soft-L1, se2e_trace.fit_correction) and the other half is judged with the same thresholds
("pass_pnp" -> the corrections become the camera model), else "fail" (-> R2 simulation data, if ready).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

import numpy as np  # noqa: E402

from harvest.train import se2e_data as S  # noqa: E402
from harvest.train import se2e_trace as TR  # noqa: E402

SOURCES = ("RB1", "RB2")
MIN_CAL_PER_SOURCE = 10


def _errors(frames, pts, chain, corr=None):
    out = []
    for f in frames:
        p = pts[f["key"]]
        c = None if corr is None else corr[f["kind"]]
        uv, _ = TR.project(TR.head_camera(chain, f["q_head"]), np.array([f["ee"]]), corr=c)
        out.append(TR.pixel_error(uv[0], p))
    return out


def _by_source(frames, err):
    st = {"all": TR.g0_stats(err)}
    for s in SOURCES:
        st[s] = TR.g0_stats([e for f, e in zip(frames, err) if f["kind"] == s])
    return st


def judge(frames, points, urdf) -> dict:
    chain = TR.load_head_chain(urdf)
    pts = {p["key"]: p["point"] for p in points if p.get("point") is not None}
    valid = [f for f in frames if f["key"] in pts]
    out = {"n_frames": len(frames), "n_valid": len(valid), "reference_failures": len(frames) - len(valid),
           "human_fallback": 0, "rule": {"median_px": TR.G0_MEDIAN_PX, "p90_px": TR.G0_P90_PX,
                                         "min_valid": TR.G0_MIN_VALID}, "camera": {"corr": None}}
    if len(valid) < TR.G0_MIN_VALID:
        return {**out, "result": "insufficient_references", "pass": False, "next": "R2"}
    err = _errors(valid, pts, chain)
    out["nominal"] = _by_source(valid, err)
    if TR.g0_pass(out["nominal"]["all"]):
        return {**out, "result": "pass_nominal", "pass": True, "next": "E-MA1 on S-E2E"}
    corr, cal_n = {}, {}
    for s in SOURCES:
        cal = [f for f in valid if f["kind"] == s and f["cal"]]
        cal_n[s] = len(cal)
        if len(cal) < MIN_CAL_PER_SOURCE:
            return {**out, "result": "fail", "pass": False, "next": "R2",
                    "pnp": {"cal_n": cal_n, "why": f"{s}: {len(cal)} calibration references"}}
        corr[s] = TR.fit_correction([TR.head_camera(chain, f["q_head"]) for f in cal], np.array([f["ee"] for f in cal]),
                                    np.array([pts[f["key"]] for f in cal]))
    test = [f for f in valid if not f["cal"]]
    cal_all = [f for f in valid if f["cal"]]
    corr_l = {s: [float(v) for v in c] for s, c in corr.items()}
    out["pnp"] = {"cal_n": cal_n, "corr": corr_l, "test": _by_source(test, _errors(test, pts, chain, corr)),
                  "cal_fit": _by_source(cal_all, _errors(cal_all, pts, chain, corr))}
    if TR.g0_pass(out["pnp"]["test"]["all"]):
        return {**out, "result": "pass_pnp", "pass": True, "next": "E-MA1 on S-E2E", "camera": {"corr": corr_l}}
    return {**out, "result": "fail", "pass": False, "next": "R2"}


def select(a):
    rows = []
    for kind in SOURCES:
        rows += [json.loads(x) for x in open(S.rows_path(a.rows_root, kind), encoding="utf-8")]
    sel = TR.g0_select(rows, a.n_per, a.seed)
    cal = TR.g0_cal_half(sel)
    arm_chain = {arm: S.load_arm_chain(a.urdf, arm) for arm in ("left", "right")}
    head = TR.load_head_chain(a.urdf)
    with open(a.out, "w", encoding="utf-8") as f:
        for r, c in zip(sel, cal):
            names = r["names_full"]
            st = np.asarray(r["state_full"], float)
            ee = S.fk_ee(arm_chain[r["arm"]], st[S.arm_index(names, r["arm"])[:7]])
            q = TR.head_q(st, names)
            uv, z = TR.project(TR.head_camera(head, q), ee[None])
            f.write(json.dumps({"key": f"{r['kind']}_ep{r['seed']}_k{r['k']}", "kind": r["kind"], "seed": r["seed"],
                                "k": r["k"], "arm": r["arm"], "cal": c, "image": os.path.join(a.rows_root,
                                                                                            r["images"]["cam_head"]),
                                "ee": ee.tolist(), "q_head": list(q), "uv_nominal": uv[0].tolist(),
                                "z_nominal": float(z[0])}) + "\n")
    print(a.out, len(sel), sum(cal))


def cmd_judge(a):
    frames = [json.loads(x) for x in open(a.frames, encoding="utf-8")]
    points = [json.loads(x) for x in open(a.points, encoding="utf-8")]
    v = judge(frames, points, a.urdf)
    json.dump(v, open(a.out, "w"), indent=1)
    print(json.dumps({k: v[k] for k in ("result", "pass", "next", "n_valid", "reference_failures")}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("select", "judge"))
    ap.add_argument("--rows-root", default="/data/harvest/data/se2e_c1/conv")
    ap.add_argument("--urdf", default="/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf")
    ap.add_argument("--n-per", type=int, default=30)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--frames", default="")
    ap.add_argument("--points", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    select(a) if a.cmd == "select" else cmd_judge(a)


if __name__ == "__main__":
    main()
