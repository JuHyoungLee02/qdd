"""Upper-LLM-like command noise for JCR data and the OJe evaluation arm (docs/stage3/jcr_design.md §0, §0-2; NOW.md
§1-0c). The distribution is EMPIRICAL: per-call scores of the main 35B offline evaluation (tools/jcr/upper_err_dist.py
-> upper_err_dist.json): approach / carry xy error and grasp z error of the resolved target (mm), the wrong-gripper-
action rate by label action, and the call latency. The noise is added to the resolved xyz goal (the scores already are
resolved-xyz errors), the gripper intent is flipped to 'keep' / from 'keep' with the measured error rate, and the
command is delayed by a sampled call latency. scale multiplies the point error (curriculum, DART) and scale 0 = clean."""
from __future__ import annotations

import json

import numpy as np


def load_dist(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def sample_cmd_noise(rng, dist: dict, role: str, height: str, grip: str, scale: float = 1.0) -> dict:
    """role: approach (the target object) | carry (the place) | lift (no point). -> {dxyz [m], grip, intent_err,
    delay_s}. Draw order is fixed (reproducible per rng)."""
    xs = dist["carry_xy_mm"] if role == "carry" else dist["approach_xy_mm"]
    xy_mm = float(xs[int(rng.integers(len(xs)))])
    ang = float(rng.uniform(0.0, 2.0 * np.pi))
    zs = dist["grasp_z_mm"]
    z_mm = float(zs[int(rng.integers(len(zs)))])
    u_int = float(rng.uniform())
    lat = dist["latency_s"]
    delay = float(lat[int(rng.integers(len(lat)))])
    if role == "lift" or scale <= 0.0:
        dxyz = [0.0, 0.0, 0.0]
    else:
        dxyz = [scale * xy_mm * 1e-3 * float(np.cos(ang)), scale * xy_mm * 1e-3 * float(np.sin(ang)),
                scale * z_mm * 1e-3 if height in ("grasp", "place") else 0.0]
    err = scale > 0.0 and u_int < float(dist["action_err"].get(grip, 0.0))
    g = grip
    if err:
        g = "keep" if grip in ("close", "open") else ("open" if role == "carry" else "close")
    return {"dxyz": dxyz, "grip": g, "intent_err": bool(err), "delay_s": delay}
