"""Runtime motion line (canon §83, se2e-motion@v1): `motion: arm=<still|slow|fast> gripper=<closing|still|opening>`
from CAUSAL backward differences of the robot state over the checkpoint's data step (window_s = 1 / its hz: S-E2E
10 Hz -> 0.1 s), binned exactly like harvest.train.se2e_temporal.motion_line with the checkpoint's train-split bins
(prompt_config["motion"]). No older sample yet -> zero difference (= training row k = 0: still / still). No bins
(a checkpoint trained without the line, mock models) -> the trained unknown value."""
from __future__ import annotations

from collections import deque

import numpy as np

from ..serialize import MOTION_UNKNOWN
from ..train.stageb_data import grip_rate01

MOTION_VER = "se2e-motion@v1"


def motion_config(pc: dict | None, hz) -> tuple:
    """(RuntimeConfig.motion_bins, motion_window_s) from a stage-B checkpoint's prompt_config and data rate (stageb.json
    "hz", or the fused server's /info). A checkpoint trained without the line -> (None, 0.1): the unknown line. A
    checkpoint trained WITH it (prompt_config["motion"]) must never run with bins None: a malformed record or a missing
    rate raises (ser-A-min-3 fix round 1 item 6)."""
    bins = (pc or {}).get("motion")
    if not bins:
        return None, 0.1
    if not (isinstance(bins, dict) and bins.get("version") == MOTION_VER and "arm_speed" in bins
            and "grip_rate" in bins):
        raise ValueError(f"checkpoint prompt_config motion record {bins!r}: not {MOTION_VER} bins -- a motion-trained "
                         f"checkpoint must run with its bins (canon §83)")
    if not hz:
        raise ValueError("motion-trained checkpoint without a data rate (stageb.json 'hz'): the motion window is 1/hz")
    return bins, 1.0 / float(hz)


def bin_line(arm_speed: float, grip_rate: float, bins: dict) -> str:
    lo, hi = bins["arm_speed"]
    arm = "still" if arm_speed < lo else "slow" if arm_speed < hi else "fast"
    t = bins["grip_rate"]
    grip = "opening" if grip_rate > t else "closing" if grip_rate < -t else "still"
    return f"motion: arm={arm} gripper={grip}"


class MotionTracker:
    def __init__(self, bins: dict | None, window_s: float = 0.1, grip_src: str = "sim_width_m", keep_s: float = 1.0):
        if bins is not None and bins.get("version") != MOTION_VER:
            raise ValueError(f"motion bins version {bins.get('version')!r} != {MOTION_VER}")
        self.bins, self.window, self.src, self.keep = bins, float(window_s), grip_src, float(keep_s)
        self.h = deque()

    def add(self, t: float, q7, grip: float) -> None:
        self.h.append((float(t), np.asarray(q7, float)[:7].copy(), float(grip)))
        while self.h and self.h[0][0] < t - self.keep - 1e-9:
            self.h.popleft()

    def line(self) -> str:
        if self.bins is None or not self.h:
            return MOTION_UNKNOWN
        t1, q1, g1 = self.h[-1]
        old = [x for x in self.h if x[0] <= t1 - self.window + 1e-9]
        if not old:
            return bin_line(0.0, 0.0, self.bins)
        t0, q0, g0 = old[-1]
        dt = t1 - t0
        arm = float(np.linalg.norm((q1 - q0) / dt))
        grip = float(grip_rate01((g1 - g0) / dt, self.src))
        return bin_line(arm, grip, self.bins)
