"""autotune range extraction (pure numpy): sweep arrays -> environment-profile ranges (never single values).

Input (one dict per arm, all in the RIGHT-arm convention -- the sweep mirrors y for the left arm):
  reach [C, S, X, Y, H, O] bool  cuRobo IK success of the tool pose at (xs[X], ys[Y], surface[S] + levels[H]) with
                                 orientation orients[O], robot body at configs[C]
  vis   [C, S, X, Y, P] bool     target point inside the robot's own head camera (P = camera pitch options)
  cam_pitch [C, S, P]            world pitch (deg, down +) of that camera option
  xs, ys, levels, surfaces, orients, configs, lean [C], mount_z [C] or [C, S] (base link z, world), mount_x [C]

Method (the only rule): a cell = (body config, surface, stance d). Its score = mean over the work band in front of
the robot (x in [d, d + band_depth], y in `lateral`) of  yaw-coverage x visible, where yaw-coverage = share of hand
yaws for which some tested tilt reaches the grasp level AND the lift level (lift_ref above it) at that point. The
robot's feasible set = cells scoring >= rel x its own best cell. Every output range is the min/max over that set,
plus the set itself (`cells`) because surface and body posture are coupled.
"""
from __future__ import annotations

import numpy as np

EPS = 1e-6
# Head-camera pitch (deg below horizontal) every robot's views must stay inside: the union of the pitches the four
# robots' accepted production views use today (AIW hcam9 rand 30-62 / neck 45+-15, R1 ZED at lean 0.8 ~67,
# G1 D435 47.6 + lean 0.1-0.4 = 53-70, Franka mast ~20-40). One constant for all robots: a body posture whose camera
# looks straight down (R1 lean >1, 85-90 deg) is outside every robot's view distribution (L9: no VLM confusion).
CAM_PITCH_BAND = (20.0, 70.0)


def with_pitch_band(d: dict, band) -> dict:
    """Copy of a sweep dict whose camera options outside the pitch band see nothing."""
    if band is None:
        return d
    cp = np.asarray(d["cam_pitch"], float)
    ok = (cp >= band[0] - EPS) & (cp <= band[1] + EPS)  # [C,S,P]
    return dict(d, vis=d["vis"] & ok[:, :, None, None, :])


def _lvl(levels, dz):
    return int(np.argmin(np.abs(np.asarray(levels) - (levels[0] + dz))))


def _point_terms(d: dict, lift_ref: float):
    reach = d["reach"]
    pl = reach[..., 0, :] & reach[..., _lvl(d["levels"], lift_ref), :]  # [C,S,X,Y,O]
    yaws = sorted({o["yaw_deg"] for o in d["orients"]})
    yaw_of = np.array([yaws.index(o["yaw_deg"]) for o in d["orients"]])
    cov_y = np.stack([pl[..., yaw_of == k].any(-1) for k in range(len(yaws))], -1)  # [C,S,X,Y,Ny]
    vis_any = d["vis"].any(-1)  # [C,S,X,Y]
    return pl, yaws, yaw_of, cov_y, vis_any


def _stances(xs, band_depth):
    xs = np.asarray(xs, float)
    return [float(v) for v in xs if v + band_depth <= xs.max() + EPS]


def _band(xs, ys, d0, band_depth, lateral):
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    mx = (xs >= d0 - EPS) & (xs <= d0 + band_depth + EPS)
    my = (ys >= lateral[0] - EPS) & (ys <= lateral[1] + EPS)
    return mx[:, None] & my[None, :]


def cell_scores(d: dict, band_depth: float, lateral, lift_ref: float) -> tuple:
    """-> (score [C, S, D], stances [D])."""
    _, _, _, cov_y, vis_any = _point_terms(d, lift_ref)
    point = cov_y.mean(-1) * vis_any  # [C,S,X,Y]
    st = _stances(d["xs"], band_depth)
    sc = np.stack([point[:, :, _band(d["xs"], d["ys"], s, band_depth, lateral)].mean(-1) for s in st], -1)
    return sc, st


def _rng(v):
    v = [float(x) for x in v]
    return [round(min(v), 4), round(max(v), 4)]


def _arm_section(d, feas, st, band_depth, lateral, lift_ref):
    """Hand yaw/tilt, fallback order, lift/carry/ready heights, camera pitch, lateral band of ONE arm on the
    robot's feasible cells."""
    pl, yaws, yaw_of, cov_y, vis_any = _point_terms(d, lift_ref)
    reach, levels, orients = d["reach"], np.asarray(d["levels"], float), d["orients"]
    C, S, X, Y = vis_any.shape
    W = np.zeros((C, S, X, Y), bool)  # band points of feasible cells
    for c, s, k in zip(*np.nonzero(feas)):
        W[c, s] |= _band(d["xs"], d["ys"], st[k], band_depth, lateral)
    Wv = W & vis_any
    n = max(int(Wv.sum()), 1)
    yaw_rate = {int(y): round(float((cov_y[..., k] & Wv).sum()) / n, 4) for k, y in enumerate(yaws)}
    best = max(yaw_rate.values()) or 1.0
    ok_y = [y for y, r in yaw_rate.items() if r >= 0.75 * best]  # bad yaw = < 3/4 of the best yaw
    tilt_keys = sorted({(o["tilt_deg"], o["tdir_deg"]) for o in orients})
    tilt_rate = {}
    for t in tilt_keys:
        m = np.array([(o["tilt_deg"], o["tdir_deg"]) == t for o in orients])
        tilt_rate[f"{t[0]}@{t[1]}"] = round(float((pl[..., m].any(-1) & Wv).sum()) / n, 4)
    tb = max(tilt_rate.values()) or 1.0
    ok_t = [int(k.split("@")[0]) for k, r in tilt_rate.items() if r >= 0.5 * tb]
    # fallback order: nominal = tilt 0 at each yaw; which (yaw change, tilt) recovers a failed nominal most often
    period = 360 if max(yaws) >= 180 else 180
    nom = [i for i, o in enumerate(orients) if o["tilt_deg"] == 0]
    rec, den = {}, 0
    for i in nom:
        F = ~pl[..., i] & Wv
        den += int(F.sum())
        for j, o in enumerate(orients):
            if j == i:
                continue
            dy = (o["yaw_deg"] - orients[i]["yaw_deg"]) % period
            dy = dy - period if dy > period / 2 else dy
            key = (int(dy), o["tilt_deg"], o["tdir_deg"])
            rec[key] = rec.get(key, 0) + int((F & pl[..., j]).sum())
    fb = sorted(rec.items(), key=lambda kv: -kv[1])[:8]
    fallback = [{"dyaw_deg": k[0], "tilt_deg": k[1], "tdir_deg": k[2], "recover": round(v / max(den, 1), 4)}
                for k, v in fb if v > 0]
    # heights: any orientation, per point
    g_any = reach[..., 0, :].any(-1) & W
    lift = {}
    for k in range(1, len(levels)):
        up = (reach[..., 0, :] & reach[..., k, :]).any(-1) & W
        lift[round(float(levels[k] - levels[0]), 3)] = round(float(up.sum()) / max(int(g_any.sum()), 1), 4)
    lift_ok = [L for L, r in lift.items() if r >= 0.8]
    carry = {}
    base_any = reach[..., 0, :].any(-1) & W
    for k in range(1, len(levels)):
        carry[round(float(levels[k] - levels[0]), 3)] = round(
            float((reach[..., k, :].any(-1) & W).sum()) / max(int(base_any.sum()), 1), 4)
    carry_ok = [L for L, r in carry.items() if r >= 0.8]
    top = np.array([o["tilt_deg"] == 0 for o in orients])
    ready = {round(float(levels[k]), 3): round(float((reach[..., k, :][..., top].any(-1) & W).sum()) / max(int(W.sum()), 1), 4)
             for k in range(len(levels)) if levels[k] >= 0.12 - EPS}
    rb = max(ready.values()) if ready else 0.0
    ready_ok = [h for h, r in ready.items() if rb > 0 and r >= 0.8 * rb]
    # camera pitch: options whose visibility over the band is >= 0.8 x the best option
    vis, cp = d["vis"], np.asarray(d["cam_pitch"], float)
    P = vis.shape[-1]
    vr = np.array([float((vis[..., p] & W).sum()) for p in range(P)]) / max(int(W.sum()), 1)
    okp = [p for p in range(P) if vr.max() > 0 and vr[p] >= 0.8 * vr.max()]
    pitches = [cp[c, s, p] for c, s, _ in zip(*np.nonzero(feas)) for p in okp]
    # lateral band
    ys = np.asarray(d["ys"], float)
    pt = cov_y.mean(-1) * vis_any
    feas_cs = feas.any(-1)
    lat_rate = np.array([pt[feas_cs][:, :, j].mean() if feas_cs.any() else 0.0 for j in range(len(ys))])
    lat_ok = ys[lat_rate >= 0.5 * lat_rate.max()] if lat_rate.max() > 0 else ys
    # work mask: points (x, y from the robot root) the feasible cells can grasp + lift at most yaws and see
    pr = pt[feas_cs].mean(0) if feas_cs.any() else np.zeros(pt.shape[2:])
    wm = {"xs": [round(float(v), 4) for v in d["xs"]], "ys": [round(float(v), 4) for v in ys],
          "ok": (pr >= 0.5 * pr.max()).tolist() if pr.max() > 0 else (pr > 1).tolist(),
          "rule": "mean over feasible cells of yaw-coverage x visible >= 0.5 x its max"}
    return {
        "yaw_deg_ok": sorted(ok_y), "yaw_deg_bad": sorted(set(yaw_rate) - set(ok_y)), "yaw_rate": yaw_rate,
        "tilt_deg": _rng(ok_t) if ok_t else [0.0, 0.0], "tilt_rate": tilt_rate, "fallback": fallback,
        "lift_clear_m": _rng(lift_ok) if lift_ok else None, "lift_rate": lift,
        "carry_clear_m": _rng(carry_ok) if carry_ok else None, "carry_rate": carry,
        "ready_tcp_above_surface_m": _rng(ready_ok) if ready_ok else None, "ready_rate": ready,
        "cam_pitch_deg": _rng(pitches) if pitches else None, "cam_vis_rate": [round(float(v), 4) for v in vr],
        "lateral_m": _rng(lat_ok), "work_mask": wm,
    }


def extract(arms, band_depth: float = 0.25, lateral=(-0.40, 0.0), lift_ref: float = 0.10, rel: float = 0.7,
            max_cells: int = 400, cam_pitch_band=CAM_PITCH_BAND, core_rel: float = 0.9) -> dict:
    """arms: one sweep dict or {arm name: sweep dict} (same configs / surfaces / grids). -> profile fragment."""
    if not isinstance(arms, dict) or "reach" in arms:
        arms = {"right": arms}
    arms = {a: with_pitch_band(d, cam_pitch_band) for a, d in arms.items()}
    names = list(arms)
    d0 = arms[names[0]]
    scores = []
    for a in names:
        sc, st = cell_scores(arms[a], band_depth, lateral, lift_ref)
        scores.append(sc)
    score = np.mean(scores, 0)  # [C,S,D]
    best = float(score.max())
    feas = score >= rel * best - EPS if best > 0 else np.zeros_like(score, bool)
    C, S, D = score.shape
    surf = np.asarray(d0["surfaces"], float)
    mz = np.broadcast_to(np.asarray(d0["mount_z"], float).reshape(C, -1), (C, S))
    idx = list(zip(*np.nonzero(feas)))
    joints = sorted(d0["configs"][0]) if d0["configs"] else []
    cells = sorted(({"surface_z": round(float(surf[s]), 4), "stance_x": round(float(st[k]), 4),
                     "lean": round(float(d0["lean"][c]), 4), "mount_above": round(float(mz[c, s] - surf[s]), 4),
                     "torso": {j: d0["configs"][c][j] for j in joints}, "score": round(float(score[c, s, k]), 4)}
                    for c, s, k in idx), key=lambda r: -r["score"])
    prof = {
        "surface_z_m": _rng(surf[[s for _, s, _ in idx]]) if idx else None,
        "stance_x_m": _rng([st[k] for _, _, k in idx]) if idx else None,
        "body": {"joints": {j: _rng([d0["configs"][c][j] for c, _, _ in idx]) for j in joints} if idx else {},
                 "lean_rad": _rng([d0["lean"][c] for c, _, _ in idx]) if idx else None,
                 "mount_above_surface_m": _rng([mz[c, s] - surf[s] for c, s, _ in idx]) if idx else None},
        "cells": cells[:max_cells],
        "stats": {"best_score": round(best, 4), "n_feasible": len(idx), "n_cells": int(score.size), "rel": rel,
                  "band_depth_m": band_depth, "lateral_m": list(lateral), "lift_ref_m": lift_ref},
        "arms": {a: _arm_section(arms[a], feas, st, band_depth, lateral, lift_ref) for a in names},
    }
    core = list(zip(*np.nonzero(score >= core_rel * best - EPS))) if best > 0 else []
    prof["core"] = {"rel": core_rel, "n": len(core),
                    "surface_z_m": _rng(surf[[s for _, s, _ in core]]) if core else None,
                    "stance_x_m": _rng([st[k] for _, _, k in core]) if core else None,
                    "lean_rad": _rng([d0["lean"][c] for c, _, _ in core]) if core else None,
                    "mount_above_surface_m": _rng([mz[c, s] - surf[s] for c, s, _ in core]) if core else None}
    prof["stats"]["cam_pitch_band_deg"] = list(cam_pitch_band) if cam_pitch_band else None
    a0 = prof["arms"][names[0]]
    prof["hand"] = {"yaw_deg_ok": a0["yaw_deg_ok"], "yaw_deg_bad": a0["yaw_deg_bad"], "tilt_deg": a0["tilt_deg"],
                    "fallback": a0["fallback"]}
    prof["lift_clear_m"] = a0["lift_clear_m"]
    prof["carry_clear_m"] = a0["carry_clear_m"]
    prof["ready"] = {"tcp_above_surface_m": a0["ready_tcp_above_surface_m"]}
    return prof
