"""Shared point-tracking front-end (user-log 123 series: 'point tracking can go into T0, T1 and T3').

Once per episode: CoTracker3 (offline, facebookresearch/co-tracker, CVPR-workshop/2024 line; weights via torch.hub)
tracks several query points per part -- the gripper of each arm (seeded from a few filtered detections, or one GT /
FK-projected point on calibrated sets), optionally robot-body and object points -- plus the gripper close / open events
from the joints. The cache (npz) is then read by
  T0  pixel labels: grasp / place pixels = the fused gripper track at the close / open events, 2-D traces;
  T1  self-calibration: temporally consistent 2-D gripper points paired with FK 3-D (instead of per-frame detections);
  T3  3-D trajectories: tracked pixels + estimated depth, with multi-frame consistency;
  T4  (render alignment, not built here) could use the body tracks as cues.
The GPU part (the tracker itself) lives in the pod runner; this module is pure numpy + the cache format.
"""
from __future__ import annotations

import json

import numpy as np

from . import selfcal as C


def seeds(u, n: int = 3, win: int = 2, max_px: float = 40.0) -> list:
    """n seed frames spread over the episode among detections that agree with their neighbours (jump filter)."""
    u = np.asarray(u, float)
    ok = np.nonzero(C.jump_filter(u, win=win, max_px=max_px))[0]
    if len(ok) == 0:
        return []
    if len(ok) <= n:
        return [int(k) for k in ok]
    pos = np.linspace(0, len(ok) - 1, n + 2)[1:-1].round().astype(int)
    return [int(ok[i]) for i in pos]


def fuse(tracks, vis):
    """tracks (T, Q, 2) of ONE part, vis (T, Q) -> per-frame median of the visible tracks (T, 2), count (T,)."""
    tracks, vis = np.asarray(tracks, float), np.asarray(vis, bool)
    T = len(tracks)
    out = np.full((T, 2), np.nan)
    n = vis.sum(1)
    for t in range(T):
        if n[t]:
            out[t] = np.median(tracks[t, vis[t]], 0)
    return out, n


def events(g, closed_thr: float = 0.5) -> dict:
    c = np.asarray(g, float) > closed_thr
    return {"close": [k for k in range(1, len(c)) if c[k] and not c[k - 1]],
            "open": [k for k in range(1, len(c)) if not c[k] and c[k - 1]]}


def save(path: str, cache: dict) -> None:
    fused = cache.get("fused", {})
    np.savez_compressed(path, tracks=np.asarray(cache["tracks"], np.float32), vis=np.asarray(cache["vis"], bool),
                        names=np.array(json.dumps(cache["names"])), events=np.array(json.dumps(cache["events"])),
                        meta=np.array(json.dumps(cache.get("meta", {}))),
                        fused_names=np.array(json.dumps(list(fused))),
                        **{f"fused_{k}": np.asarray(v, np.float32) for k, v in fused.items()})


def load(path: str) -> dict:
    z = np.load(path)
    fnames = json.loads(str(z["fused_names"]))
    return {"tracks": z["tracks"], "vis": z["vis"], "names": json.loads(str(z["names"])),
            "events": json.loads(str(z["events"])), "meta": json.loads(str(z["meta"])),
            "fused": {k: z[f"fused_{k}"] for k in fnames}}
