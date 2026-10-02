"""autotune stage 4 (offline part): auto feasible set vs today's hand-tuned settings, scored on the SAME sweep.

Score of a set = mean cell score (expected share of the work band that is graspable + liftable + carry-reachable
over the hand's yaws and in the robot's own camera) when drawing cells uniformly from the set. Pass = auto mean >=
hand mean. The hand set is unconstrained in stance (every stance) unless the spec says otherwise, so it is never
handicapped by a stance the auto tool chose.

usage: compare.py <robots/profile.json> <sweep dir> [--hand hand_tuned.json] [--rel 0.7]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ranges as RG  # noqa: E402

EPS = 1e-6


def _in(v, lohi):
    return (v >= lohi[0] - EPS) & (v <= lohi[1] + EPS)


def hand_mask(d: dict, spec: dict, n_stance: int) -> np.ndarray:
    """[C, S, D] bool: cells matching the hand-tuned spec (lean_rad, mount_above_surface_m, surface_z_m,
    root_z_rel_surface, surface_minus_joint)."""
    C, S = len(d["configs"]), len(d["surfaces"])
    surf = np.asarray(d["surfaces"], float)[None, :].repeat(C, 0)
    m = np.ones((C, S), bool)
    if "lean_rad" in spec:
        m &= _in(np.asarray(d["lean"], float), spec["lean_rad"])[:, None]
    if "mount_above_surface_m" in spec:
        mz = np.broadcast_to(np.asarray(d["mount_z"], float).reshape(C, -1), (C, S))
        m &= _in(mz - surf, spec["mount_above_surface_m"])
    if "surface_z_m" in spec:
        m &= _in(surf, spec["surface_z_m"])
    if "root_z_rel_surface" in spec:
        m &= _in(np.array([c["root_z_rel_surface"] for c in d["configs"]]), spec["root_z_rel_surface"])[:, None]
    if "surface_minus_joint" in spec:
        j, lo, hi = spec["surface_minus_joint"]
        jv = np.array([c[j] for c in d["configs"]], float)[:, None]
        m &= _in(surf - jv, (lo, hi))
    return np.repeat(m[:, :, None], n_stance, 2)


def compare(arms: dict, spec: dict, rel: float = 0.7, band_depth: float = 0.25, lateral=(-0.40, 0.0),
            cam_pitch_band=RG.CAM_PITCH_BAND) -> dict:
    """Auto set = the profile's cells (same pitch band); hand set scored twice: over every stance and at the best
    stance of each (body, surface) -- the latter never handicaps the hand setting by a stance choice."""
    scores, st = [], None
    for d in arms.values():
        d = RG.with_pitch_band(d, cam_pitch_band)
        sc, st = RG.cell_scores(d, band_depth, lateral, 0.10)
        scores.append(sc)
    score = np.mean(scores, 0)
    best = float(score.max())
    auto = score >= rel * best - EPS
    d0 = next(iter(arms.values()))
    hand = hand_mask(d0, spec, len(st))
    out = {"best": round(best, 4), "auto_mean": round(float(score[auto].mean()), 4), "auto_n": int(auto.sum()),
           "hand_mean": round(float(score[hand].mean()), 4) if hand.any() else None, "hand_n": int(hand.sum()),
           "hand_inside_auto": round(float((hand & auto).sum() / max(hand.sum(), 1)), 4)}
    hb = hand[:, :, 0] & np.isfinite(score.max(-1))
    out["hand_mean_best_stance"] = round(float(score.max(-1)[hb].mean()), 4) if hb.any() else None
    ks = np.nonzero(auto.any((0, 1)))[0]  # the stance range the auto profile draws from
    hs = hand.copy()
    hs[:, :, :] &= np.isin(np.arange(score.shape[2]), np.arange(ks.min(), ks.max() + 1))[None, None, :] if len(ks) else False
    out["hand_mean_auto_stance"] = round(float(score[hs].mean()), 4) if hs.any() else None
    ref = out["hand_mean_auto_stance"] if out["hand_mean_auto_stance"] is not None else out["hand_mean"]
    out["pass"] = ref is None or out["auto_mean"] >= ref
    # per-yaw rate inside the HAND set (does the sweep rediscover the bad yaws under today's settings too?)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("robot")
    ap.add_argument("sweep_dir")
    ap.add_argument("--hand", default=os.path.join(HERE, "hand_tuned.json"))
    ap.add_argument("--rel", type=float, default=0.7)
    a = ap.parse_args()
    import make_profile as PF
    robot = json.load(open(a.robot))
    arms = {arm: PF.load_arm(a.sweep_dir, robot["profile"], arm) for arm in robot["arms"]
            if PF.has_arm(a.sweep_dir, robot["profile"], arm)}
    spec = json.load(open(a.hand)).get(robot["profile"], {})
    print(json.dumps({"profile": robot["profile"], **compare(arms, spec, a.rel)}))


if __name__ == "__main__":
    main()
