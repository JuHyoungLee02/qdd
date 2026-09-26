"""RB3 data prep (docs/stage3/results/rb3_data.md), pure functions: release frame, head-image visibility rule,
episode fingerprints for the RB1 / RB2 / RB3 overlap check.

release_visible (per episode): at the first release frame of the episode (the first gripper opening after a
closed period that STARTED inside the episode -- se2e_molmo.grip_segment_ends require_grasp, P95; earliest over the
two arms) the yellow place box is inside the lower 40 % of the head image: yellow fraction >= YELLOW_MIN with the
survey's colour rule (r > 150, g > 90, b < 90, r - b > 90; robotis_open_data_survey 3절). In the early episodes the
head is tilted up, the box is out of the image and the gripper leaves the image at release; once the head is down
the box and the gripper are both in view at release. No release -> not visible (release_frame None).
"""
from __future__ import annotations

import hashlib

import numpy as np

YELLOW_MIN = 0.02
LOW_FROM = 0.6  # lower 40 % of the image
GRIP_CLOSED = 0.5  # = se2e_data.GRIP_CLOSED
ARM16 = [f"arm_{a}_joint{i}" for a in ("l", "r") for i in range(1, 8)]
GRIPS = ("gripper_l_joint1", "gripper_r_joint1")


def releases(g, closed: float = GRIP_CLOSED) -> list:
    """Release frames of one gripper series (require_grasp): opening frames after a closed period that started
    inside the episode (a gripper closed at frame 0 that opens is opening to grasp)."""
    c = np.asarray(g, float) > closed
    out, grasped = [], False
    for k in range(1, len(c)):
        if not c[k - 1] and c[k]:
            grasped = True
        elif c[k - 1] and not c[k] and grasped:
            out.append(k)
            grasped = False
    return out


def first_release(state, names):
    """(frame, arm) of the earliest release over both grippers, (None, None) when there is none."""
    st = np.asarray(state, float)
    best = (None, None)
    for gname, arm in zip(GRIPS, ("left", "right")):
        r = releases(st[:, list(names).index(gname)])
        if r and (best[0] is None or r[0] < best[0]):
            best = (r[0], arm)
    return best


def yellow_low(img) -> float:
    """Fraction of yellow pixels (survey rule) in the lower 40 % of an RGB image (H, W, 3)."""
    a = np.asarray(img).astype(np.int16)
    low = a[int(a.shape[0] * LOW_FROM):]
    r, g, b = low[..., 0], low[..., 1], low[..., 2]
    return float(((r > 150) & (g > 90) & (b < 90) & (r - b > 90)).mean())


def release_flag(frame, yellow) -> bool:
    return frame is not None and yellow is not None and yellow >= YELLOW_MIN


def head_down(yellow_f0) -> bool:
    """Head tilted down at the first frame: the place box is in the lower 40 % (same colour rule)."""
    return yellow_f0 is not None and yellow_f0 >= YELLOW_MIN


def exclude_reason(state, names):
    """'no_grasp' when neither gripper ever closes (state <= GRIP_CLOSED): in RB3 these are idle recordings -- the
    robot stays still while a person resets the tool wall (frames checked, rb3_data.md) -- not demonstrations."""
    st = np.asarray(state, float)
    return None if max(st[:, list(names).index(g)].max() for g in GRIPS) > GRIP_CLOSED else "no_grasp"


# ------------------------------------------------------------------------------------------ overlap fingerprints
def arm16(x, names) -> np.ndarray:
    """The 16 arm + gripper dims (RB2's 19-D minus head / lift) in one fixed order."""
    names = list(names)
    return np.asarray(x, np.float32)[:, [names.index(n) for n in ARM16 + list(GRIPS)]]


def exact_hash(x) -> str:
    """sha1 of the float32 bytes (exact duplicate)."""
    return hashlib.sha1(np.ascontiguousarray(np.asarray(x, np.float32)).tobytes()).hexdigest()


def round_hash(x, decimals: int = 3) -> str:
    """sha1 of the values rounded to 1e-3 (re-export / float noise)."""
    return hashlib.sha1(np.round(np.asarray(x, np.float64), decimals).astype(np.float32).tobytes()).hexdigest()


def traj_fp(x, n: int = 20) -> np.ndarray:
    """(n, D) samples of a (T, D) series at n evenly spaced frames (length-independent near-duplicate key)."""
    x = np.asarray(x, np.float32)
    return x[np.linspace(0, len(x) - 1, n).round().astype(int)]


def nearest(fp_a: np.ndarray, fp_b: np.ndarray, chunk: int = 256):
    """For every a: (index of the nearest b, max-abs distance) over stacked fingerprints (Na, n, D), (Nb, n, D)."""
    idx, dist = [], []
    B = fp_b.reshape(len(fp_b), -1)
    for i in range(0, len(fp_a), chunk):
        A = fp_a[i:i + chunk].reshape(-1, 1, B.shape[1])
        d = np.abs(A - B[None]).max(-1)
        idx += d.argmin(1).tolist()
        dist += d.min(1).tolist()
    return idx, dist
