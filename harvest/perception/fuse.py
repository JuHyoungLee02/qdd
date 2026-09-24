"""Head + active-wrist fusion of per-camera object centroids (R1).

Rule (R1 brief): when both cameras see the object, prefer the wrist (RealSense D405) inside its 7-50 cm working
range; otherwise the head (ZED Mini left). A wrist view outside its range is used only when the head misses.
Flags (M1 §4): id_uncertain = a strong runner-up instance far from the chosen one, or head and wrist centroids that
disagree by more than DISAGREE_M; occluded = no usable detection this frame (Tracker keeps the last estimate).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

WRIST_RANGE_M = (0.07, 0.50)
MIN_VALID_PX = 20  # masked pixels with a valid depth
RUNNER_UP_SCORE = 0.5  # SAM 3.1 score of a second instance of the same phrase that makes the id ambiguous
SAME_OBJ_M = 0.05  # a runner-up closer than this is the same object split in two masks
DISAGREE_M = 0.08  # head vs wrist centroid (different visible surfaces differ by up to ~2 radii)


@dataclass
class CamDet:
    cam: str
    score: float
    n_valid: int
    point: np.ndarray | None  # median centroid, table frame [m]
    depth_med: float  # median renderer depth of the masked pixels [m]
    second: tuple | None = None  # (score, point) of the best other instance, if any


def _usable(d: CamDet | None, min_valid: int) -> bool:
    return d is not None and d.point is not None and d.n_valid >= min_valid


def _runner_up_ambiguous(d: CamDet) -> bool:
    if not d.second:
        return False
    s, p = d.second
    return s >= RUNNER_UP_SCORE and p is not None and float(np.linalg.norm(np.asarray(p) - d.point)) > SAME_OBJ_M


def fuse(head: CamDet | None, wrist: CamDet | None, wrist_range=WRIST_RANGE_M, min_valid: int = MIN_VALID_PX) -> dict:
    h, w = _usable(head, min_valid), _usable(wrist, min_valid)
    seen = [d.cam for d, ok in ((head, h), (wrist, w)) if ok]
    w_in = w and wrist_range[0] <= wrist.depth_med <= wrist_range[1]
    if w_in:
        src, d = "wrist", wrist
    elif h:
        src, d = "head", head
    elif w:
        src, d = "wrist_oor", wrist
    else:
        return {"pos": None, "source": None, "seen": [], "id_uncertain": False}
    unc = _runner_up_ambiguous(d)
    if h and w and float(np.linalg.norm(head.point - wrist.point)) > DISAGREE_M:
        unc = True
    return {"pos": np.asarray(d.point, float), "source": src, "seen": seen, "id_uncertain": bool(unc)}


class Tracker:
    """Per-episode memory: an object with no usable detection keeps its last estimate and is flagged occluded."""

    def __init__(self):
        self.last: dict = {}
        self.held: dict = {}

    def update(self, obj: str, f: dict) -> dict:
        out = dict(f)
        if f["pos"] is not None:
            self.last[obj], self.held[obj] = np.asarray(f["pos"], float), 0
            out.update(occluded=False, held_frames=0)
            return out
        self.held[obj] = self.held.get(obj, 0) + 1
        out.update(pos=self.last.get(obj), occluded=True, held_frames=self.held[obj])
        return out
