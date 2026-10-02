"""autotune stage 2: sweep npz -> per-robot environment profile harvest/l9/assets9/env_profiles/<profile>.json.

Schema "l9-env-profile-v1" (agreed 10-03 with the grip-layer agent, reader/draw = harvest/l9/envprof9.py; the
common executor reads carry_clear_m). Ranges only, never single values; `cells` = the coupled feasible set
(surface x body posture x stance), draw uniformly from it. Units: m, lean rad, *_deg in degrees.

usage: make_profile.py <robots/profile.json> <sweep out dir> <profile out json> [--rel 0.7] [--band-depth 0.25]
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ranges as RG  # noqa: E402


def load_arm(out_dir: str, profile: str, arm: str) -> dict:
    """One arm's sweep; sharded runs (<arm>.s<k>of<n>.npz, disjoint rotation groups) are OR-merged."""
    import glob
    fn = os.path.join(out_dir, f"{profile}_{arm}.npz")
    files = [fn] if os.path.exists(fn) else sorted(glob.glob(os.path.join(out_dir, f"{profile}_{arm}.s*of*.npz")))
    if not files:
        raise FileNotFoundError(fn)
    z = np.load(files[0])
    d = {k: z[k] for k in z.files}
    metas = [json.load(open(f[:-4] + "_meta.json")) for f in files]
    if len(files) > 1:
        n = metas[0]["shard"][1]
        if len(files) != n:
            raise RuntimeError(f"{profile}/{arm}: {len(files)} of {n} shards")
        for f in files[1:]:
            d["reach"] = d["reach"] | np.load(f)["reach"]
    meta = dict(metas[0], n_ik=sum(m["n_ik"] for m in metas), seconds=max(m["seconds"] for m in metas))
    d.update(configs=meta["configs"], orients=meta["orients"], meta=meta)
    return d


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "-C", HERE, "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return os.path.basename(os.path.normpath(os.path.join(HERE, "..", "..", ".."))).replace("code_", "")


def build(robot: dict, arms: dict, rel: float, band_depth: float) -> dict:
    fr = RG.extract(arms, band_depth=band_depth, rel=rel)
    lat = {}
    for a, sec in fr["arms"].items():
        lo, hi = sec["lateral_m"]
        lat[a] = [lo, hi] if a != "left" else [round(-hi, 4), round(-lo, 4)]
        if a == "left":  # sweep arrays are in the right-arm convention: report the left arm's own y
            sec["work_mask"]["ys"] = [round(-v, 4) for v in sec["work_mask"]["ys"]]
    a0 = next(iter(fr["arms"].values()))
    body = fr["body"]
    torso = {j: v for j, v in body["joints"].items() if j != "root_z_rel_surface"}
    prof = {
        "schema": "l9-env-profile-v1", "profile": robot["profile"], "version": 1,
        "source": {"tool": "tools/onboard/autotune (cuRobo batch IK sweep, no render)", "sha": _git_sha(),
                   "date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
                   "n_ik": int(sum(d["meta"]["n_ik"] for d in arms.values())),
                   "selftest_fk_ik": {a: d["meta"]["selftest_success"] for a, d in arms.items()}},
        "surface_z_m": fr["surface_z_m"], "stance_x_m": fr["stance_x_m"], "lateral_m": lat,
        "body": {"joints": torso, "lean_rad": body["lean_rad"], "mount_above_surface_m": body["mount_above_surface_m"]},
        "hand": fr["hand"], "ready": fr["ready"], "lift_clear_m": fr["lift_clear_m"],
        "carry_clear_m": fr["carry_clear_m"], "head_cam": {"pitch_deg": a0["cam_pitch_deg"]},
        "cells": fr["cells"], "stats": fr["stats"], "arms": fr["arms"],
    }
    d0 = next(iter(arms.values()))
    half = {"surface_z": round(float(np.diff(d0["surfaces"]).min()) / 2, 4),
            "stance_x": round(float(np.diff(d0["xs"]).min()) / 2, 4)}
    for j in body["joints"]:
        vals = sorted({c[j] for c in d0["configs"]})
        if len(vals) > 1:
            half[f"torso.{j}"] = round(float(np.diff(vals).min()) / 2, 5)
    prof["cell_half"] = half  # draw jitter inside a cell (envprof9.draw)
    if "root_z_rel_surface" in body["joints"]:  # a stand / virtual lift: the root height over the surface
        prof["lift"] = {"root_z_rel_surface": body["joints"]["root_z_rel_surface"]}
    pj = robot["cameras"][robot.get("head_camera", "cam_head")].get("pitch_joint")
    if pj:
        popts = next(iter(arms.values()))["meta"]["pitch_options"]
        vr = a0["cam_vis_rate"]
        ok = [p for p, v in zip(popts, vr) if max(vr) > 0 and v >= 0.8 * max(vr)]
        prof["head_cam"]["pitch_joint"] = {pj: [round(min(ok), 4), round(max(ok), 4)]} if ok else None
    return prof


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("robot")
    ap.add_argument("sweep_dir")
    ap.add_argument("out")
    ap.add_argument("--rel", type=float, default=0.7)
    ap.add_argument("--band-depth", type=float, default=0.25)
    a = ap.parse_args()
    robot = json.load(open(a.robot))
    arms = {arm: load_arm(a.sweep_dir, robot["profile"], arm) for arm in robot["arms"]
            if os.path.exists(os.path.join(a.sweep_dir, f"{robot['profile']}_{arm}.npz"))}
    prof = build(robot, arms, a.rel, a.band_depth)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(prof, open(a.out, "w"), indent=1)
    s = {k: prof[k] for k in ("surface_z_m", "stance_x_m", "lateral_m", "lift_clear_m", "carry_clear_m")}
    print(json.dumps({"profile": prof["profile"], **s, "body": prof["body"], "hand": {k: prof["hand"][k] for k in (
        "yaw_deg_ok", "yaw_deg_bad", "tilt_deg")}, "ready": prof["ready"], "head_cam": prof["head_cam"],
        "stats": prof["stats"]}))


if __name__ == "__main__":
    main()
