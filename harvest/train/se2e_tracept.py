"""E-MAR-real factor A, OPT-IN `aux: trace5-point@v1` (docs/stage3/prereg_marr.md; canon §89, user-log 99 / 105):
MolmoAct's 2-D end-effector trace (arXiv 2508.07917 §2.3) as a TRAINING-ONLY auxiliary regression target on real
S-E2E rows, labelled by Molmo2-ER gripper pointing on the head frames + filter v2 (docs/stage3/molmoact_real_readiness.md).

Label of a row (episode, frame k, active arm a): trace.labels_segments over the arm's kept pointings of frames
k..e (e = the arm's next release, se2e_molmo.grip_segment_ends) = 1-5 points in MolmoAct's 0..255 image coordinates;
None after the last release or without a kept point (-> the row is masked). Target: point i -> (u, v) / 255 in [0, 1],
TRACE_SCALE units (5 % of the image = 1) like E-MA1 trace5@v1; missing points masked. The existing AuxGeomHead gets
10 more regression outputs (se2e_trace_model machinery, registered under TRACEPT_VER); nothing is generated or read at
run time -- the decision / chunk path is the default one (base_view).

No existing file is edited: install() registers the version with stageb_train / se2e_trace_model at run time (CLI
entry `python -m harvest.train.se2e_tracept train|predict|evalck ... --aux-extra trace5-point@v1 --tracept-root DIR`)
and returns an undo function; importing this module changes nothing.
"""
from __future__ import annotations

import json
import os

import numpy as np

from . import se2e_trace as TR
from . import stageb_data as D

TRACEPT_VER = "trace5-point@v1"
N_POINTS = 5
N_TRACEPT = 2 * N_POINTS
SCALE = TR.TRACE_SCALE
W_HEAD, H_HEAD = 672, 376
FILES = ("harvest/train/se2e_tracept.py",)
DEFAULT_ROOT = "/data/harvest/data/marr_real/conv"


def target(trace255) -> dict | None:
    """{"uv": [10] in [0, 1] (0 where masked), "mask": [5]} of a 1-5 point 0..255 trace; None -> None."""
    if not trace255:
        return None
    if len(trace255) > N_POINTS:
        raise ValueError(f"trace with {len(trace255)} points (max {N_POINTS})")
    uv, mask = [0.0] * N_TRACEPT, [0] * N_POINTS
    for i, (qu, qv) in enumerate(trace255):
        if not (0 <= qu <= 255 and 0 <= qv <= 255):
            raise ValueError(f"trace point {qu, qv} outside 0..255")
        uv[2 * i], uv[2 * i + 1], mask[i] = qu / 255.0, qv / 255.0, 1
    return {"uv": uv, "mask": mask}


def tracept_aux_vecs(s: dict):
    """stageb_data.aux_vecs of the sample + the 10 trace regression targets (SCALE units) and masks."""
    r, rm, c, cm = D.aux_vecs(s["aux"])
    t = s.get("tracept")
    if t is None:
        tr, tm = np.zeros(N_TRACEPT, np.float32), np.zeros(N_TRACEPT, np.float32)
    else:
        tm = np.repeat(np.asarray(t["mask"], np.float32), 2)
        tr = np.asarray(t["uv"], np.float32) / SCALE * tm
    return np.concatenate([r, tr]).astype(np.float32), np.concatenate([rm, tm]).astype(np.float32), c, cm


def labels_path(root: str, kind: str) -> str:
    return os.path.join(root, f"{kind}.tracept.jsonl")


def attach(samples, root: str) -> dict:
    """In place: s["tracept"] of every sample (None = masked). A kind with a labels file must list every row of it
    (KeyError otherwise); a kind without one (RB1: C3 violated, not labelled) is masked. Returns counts per kind."""
    counts = {}
    for kind in sorted({s["key"].split("_")[0] for s in samples}):
        p = labels_path(root, kind)
        tg = None
        if os.path.exists(p):
            tg = {}
            for x in open(p, encoding="utf-8"):
                t = json.loads(x)
                tg[t["key"]] = target(t["trace255"])
        n = lab = 0
        for s in samples:
            if s["key"].split("_")[0] != kind:
                continue
            s["tracept"] = None if tg is None else tg[s["key"]]
            n += 1
            lab += s["tracept"] is not None
        counts[kind] = {"rows": n, "labelled": lab, "file": p if tg is not None else None}
    return counts


def trace_px_errors(model, enc, val, device) -> dict | None:
    """Aux head trace error on the labelled val rows: per kept point |pred - label| in head-image pixels (672 x 376)
    and in MolmoAct 0..255 units; the base-frame 'current point' (i = 0) and the END point (last kept) separately."""
    import torch
    was = model.training
    model.eval()
    err, err255, per_pt, first, last = [], [], [[] for _ in range(N_POINTS)], [], []
    with torch.no_grad():
        for s in val:
            t = s.get("tracept")
            if t is None:
                continue
            if model.shared and hasattr(enc, "p"):
                ctx, mask, _ = model.forward_shared([s], enc, device, grad=False)
            else:
                ctx, mask = model.contexts([s], enc, device, grad=False)
            pr, _ = model.aux.full(ctx, mask)
            uv = pr[0, -N_TRACEPT:].float().cpu().numpy().reshape(-1, 2) * SCALE
            tt = np.asarray(t["uv"]).reshape(-1, 2)
            ks = [i for i, ok in enumerate(t["mask"]) if ok]
            for i in ks:
                du, dv = uv[i, 0] - tt[i, 0], uv[i, 1] - tt[i, 1]
                e = float(np.hypot(du * (W_HEAD - 1), dv * (H_HEAD - 1)))
                err.append(e)
                err255.append(float(np.hypot(du * 255.0, dv * 255.0)))
                per_pt[i].append(e)
            first.append(per_pt[ks[0]][-1])
            last.append(per_pt[ks[-1]][-1])
    model.train(was)
    if not err:
        return None
    return {"n_rows": len(first), "n_points": len(err), "mean_px": float(np.mean(err)),
            "median_px": float(np.median(err)), "mean_u255": float(np.mean(err255)),
            "per_point_mean_px": [float(np.mean(x)) if x else None for x in per_pt],
            "first_point_mean_px": float(np.mean(first)), "end_point_mean_px": float(np.mean(last)),
            "end_point_median_px": float(np.median(last))}


def install():
    """Register TRACEPT_VER with stageb_train (AUX_CHOICES, AUX_FILES for the prompt_config marker, target
    attachment, --tracept-root) and se2e_trace_model (EXTRA head size / target vectors, extra_metrics adds the pixel
    error). Returns undo(). Default runs (--aux-extra none) are unchanged: every patched function falls through."""
    from . import se2e_trace_model as TM
    from . import stageb_train as B
    saved = {"AUX_CHOICES": B.AUX_CHOICES, "AUX_FILES": B.AUX_FILES, "attach_aux_targets": B.attach_aux_targets,
             "_data": B._data, "RESUME_KEYS": getattr(B, "RESUME_KEYS", None)}
    saved_tm = {"extra_metrics": TM.extra_metrics, "EXTRA": dict(TM.EXTRA)}
    orig_attach, orig_data, orig_extra = B.attach_aux_targets, B._data, TM.extra_metrics

    def attach_aux_targets(a, samples):
        if getattr(a, "aux_extra", "none") != TRACEPT_VER:
            return orig_attach(a, samples)
        counts = attach(samples, a.tracept_root)
        print(json.dumps({"event": "tracept_attach", "root": a.tracept_root, "counts": counts}), flush=True)

    def _data(p):
        orig_data(p)
        p.add_argument("--tracept-root", default=DEFAULT_ROOT,
                       help=f"--aux-extra {TRACEPT_VER}: <root>/<kind>.tracept.jsonl labels (prereg_marr)")

    def extra_metrics(model, enc, val, device, seed=0, steps=10):
        out = orig_extra(model, enc, val, device, seed=seed, steps=steps)
        if getattr(model, "aux_ver", None) == TRACEPT_VER and isinstance(model, TM.StageBTrace):
            out["tracept_px"] = trace_px_errors(model, enc, val, device)
        return out

    if TRACEPT_VER not in B.AUX_CHOICES:
        B.AUX_CHOICES = tuple(B.AUX_CHOICES) + (TRACEPT_VER,)
    B.AUX_FILES = tuple(saved["AUX_FILES"]) + tuple(f for f in FILES if f not in saved["AUX_FILES"])
    B.attach_aux_targets, B._data = attach_aux_targets, _data
    if saved["RESUME_KEYS"] is not None and "tracept_root" not in saved["RESUME_KEYS"]:
        B.RESUME_KEYS = type(saved["RESUME_KEYS"])(list(saved["RESUME_KEYS"]) + ["tracept_root"])
    TM.EXTRA[TRACEPT_VER] = (N_TRACEPT, tracept_aux_vecs)
    TM.extra_metrics = extra_metrics

    def undo():
        for k, v in saved.items():
            if v is not None:
                setattr(B, k, v)
        TM.extra_metrics = saved_tm["extra_metrics"]
        TM.EXTRA.clear()
        TM.EXTRA.update(saved_tm["EXTRA"])
    return undo


def main(argv=None):
    from . import stageb_train as B
    install()
    B.main(argv)


if __name__ == "__main__":
    main()
