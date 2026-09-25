"""E-MA1b, OPT-IN `aux: a3d@v1` (docs/stage3/prereg_ma1b.md): MolmoAct-style future end-effector trajectory as a
TRAINING-ONLY auxiliary target, in the robot base frame (URDF FK, arm_base_link) -- no camera projection, so the
head-camera error that failed E-MA1 gate G0 does not enter.

Points p1..p5 of the active arm's end effector at frames k + i (e - k) / 4 (i = 0..4; linear interpolation of the FK
positions), e = the trace end of E-MA1 (se2e_trace.event_end: the first frame whose gripper closed/open state -- the
prompt's rule -- differs from k's, else the episode end, capped at 3 s). p1 is the current end effector, so the
target is the displacement of p2..p5 from p1 (4 x xyz = 12 values, metres), in AUX_REG_SCALE units (5 cm = 1) like
the existing privileged-geometry aux targets; masked when the trace has no future (e == k, the last frame). The aux
head gets 12 more regression outputs (se2e_trace_model, `a3d@v1`); nothing is generated or read at run time.
"""
from __future__ import annotations

import json
import os

import numpy as np

from . import se2e_data as S
from . import se2e_trace as TR
from . import stageb_data as D

A3D_VER = "a3d@v1"
A3D_POINTS = 5
N_A3D = 3 * (A3D_POINTS - 1)
A3D_SCALE = D.AUX_REG_SCALE


def a3d_target(ee, grip, k: int, fps: float = 10.0) -> dict:
    """{"d": [12] metres (p2..p5 - p1, base frame), "mask": [4], "end": frame, "span_s"}."""
    ee = np.asarray(ee, float)
    e = TR.event_end(grip, k, fps)
    ts = [k + i * (e - k) / (A3D_POINTS - 1) for i in range(A3D_POINTS)]
    P = np.stack([S.interp_at(ee, t) for t in ts])
    ok = e > k and ts[-1] <= len(ee) - 1
    d = (P[1:] - P[0]).reshape(-1) if ok else np.zeros(N_A3D)
    return {"d": [float(v) for v in d], "mask": [int(ok)] * (A3D_POINTS - 1), "end": int(e),
            "span_s": round((e - k) / fps, 6)}


def a3d_aux_vecs(s: dict):
    """stageb_data.aux_vecs of the sample + the 12 A3d regression targets (A3D_SCALE units) and masks."""
    r, rm, c, cm = D.aux_vecs(s["aux"])
    t = s.get("a3d")
    if t is None:
        tr, tm = np.zeros(N_A3D, np.float32), np.zeros(N_A3D, np.float32)
    else:
        tm = np.repeat(np.asarray(t["mask"], np.float32), 3)
        tr = np.asarray(t["d"], np.float32) / A3D_SCALE * tm
    return np.concatenate([r, tr]).astype(np.float32), np.concatenate([rm, tm]).astype(np.float32), c, cm


def episode_targets(rows, state, names, chain, fps: float = 10.0) -> list:
    """Targets of the rows of one episode (full-rate state). label_check_m = |FK(k + label_steps) - FK(k) - the row's
    ee_delta| (the same FK / frame indexing as the decision labels; ee_delta is rounded to 1e-5 m)."""
    st = np.asarray(state, float)
    names = list(names)
    ee = {a: S.fk_ee(chain[a], st[:, S.arm_index(names, a)[:7]]) for a in ("left", "right")}
    grip = {a: st[:, S.arm_index(names, a)[7]] for a in ("left", "right")}
    out = []
    for r in rows:
        k, arm = r["k"], r["arm"]
        t = a3d_target(ee[arm], grip[arm], k, fps)
        chk = S.interp_at(ee[arm], k + r["label_steps"]) - ee[arm][k] - np.asarray(r["ee_delta"])
        out.append({"key": f"{r['kind']}_ep{r['seed']}_k{k}", "arm": arm, **t,
                    "label_check_m": float(np.abs(chk).max())})
    return out


def targets_path(root: str, kind: str) -> str:
    return os.path.join(root, f"{kind}.a3d.jsonl")


def attach(samples, root: str, kind: str) -> None:
    """In place: s["a3d"] of every sample of `kind` (KeyError if a sample has no target)."""
    tg = {}
    for x in open(targets_path(root, kind), encoding="utf-8"):
        t = json.loads(x)
        tg[t["key"]] = {"d": t["d"], "mask": t["mask"]}
    for s in samples:
        if s["key"].split("_")[0] == kind:
            s["a3d"] = tg[s["key"]]
