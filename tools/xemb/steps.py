"""Gripper-event segmentation of a public pick-and-place episode into our step vocabulary (pure numpy).

Our labels (harvest/teach_l8/labels.py) are: above_target -> descend_close -> carry_up -> carry_over -> lower_open ->
retreat -> done, plus the recovery 'reopen' (closed on nothing). A public episode only gives the EE path, the gripper
command / opening and (sometimes) a 'held' flag, so each step becomes a time segment whose label is the EE position at
the segment's end (a key pose of the demonstrator), in the robot's own base frame:
  close event c   (closed goes False -> True), open event o (True -> False) after it;
  pregrasp p      highest EE point of the aligned window before c (all frames within xy_tol of the grasp xy);
  above_target    [cycle start, p)  -> EE(p), keep
  descend_close   [p, c)            -> EE(c), close
  carry_up        [c, u)            -> EE(u), keep   (u = highest point while still within xy_tol of the grasp xy)
  carry_over      [u, r)            -> EE(r), keep   (r = highest point of the aligned window before o)
  lower_open      [r, o)            -> EE(o), open
  retreat         [o, e)            -> EE(e), keep   (e = highest point after o while within xy_tol)
  done            [e, N)            -> stop          (last cycle only)
A close with no 'held' within the close is an empty close: its approach is dropped (a bad label) and the closed
frames become 'reopen' (gripper open). A 'held' that ends before the open (drop / slip) truncates the cycle after
carry_up. Thresholds: xy_tol 3 cm (the pad half-width scale), lift_dz 5 cm.
"""
from __future__ import annotations

import numpy as np

XY_TOL = 0.03


def closed_from_opening(a, close_below: float = 0.8, open_above: float = 0.9) -> np.ndarray:
    """Normalised opening (1 = fully open) -> closed flags with hysteresis."""
    out, c = [], False
    for v in np.asarray(a, float):
        if not c and v < close_below:
            c = True
        elif c and v > open_above:
            c = False
        out.append(c)
    return np.array(out, bool)


def _edges(closed):
    closed = np.asarray(closed, bool)
    up = [i for i in range(1, len(closed)) if closed[i] and not closed[i - 1]]
    down = [i for i in range(1, len(closed)) if not closed[i] and closed[i - 1]]
    return up, down


def _aligned_top(ee, lo, hi, ref, tol):
    """Highest frame of the window ending at hi (exclusive) whose frames all stay within tol (xy) of ee[ref]."""
    k = hi
    while k - 1 >= lo and np.linalg.norm(ee[k - 1, :2] - ee[ref, :2]) <= tol:
        k -= 1
    if k >= hi:
        return None
    return k + int(np.argmax(ee[k:hi, 2]))


def _aligned_top_after(ee, lo, hi, ref, tol):
    k = lo
    while k < hi and np.linalg.norm(ee[k, :2] - ee[ref, :2]) <= tol:
        k += 1
    if k <= lo:
        return None
    return lo + int(np.argmax(ee[lo:k, 2]))


def _seg(step, t0, t1, ee, tgt, grip):
    return {"step": step, "t0": int(t0), "t1": int(t1),
            "target": None if tgt is None else [float(v) for v in ee[tgt]], "target_t": None if tgt is None else int(tgt),
            "gripper": grip}


def segment(ee, closed, held=None, xy_tol: float = XY_TOL) -> list:
    ee = np.asarray(ee, float)
    N = len(ee)
    ups, downs = _edges(closed)
    out = []
    start = 0
    for ci, c in enumerate(ups):
        if c < start:
            continue
        o = next((d for d in downs if d > c), N)
        nxt = ups[ci + 1] if ci + 1 < len(ups) else N
        if held is not None:
            h = np.asarray(held, bool)[c:o]
            if not h.any():  # empty close: drop the approach, label the closed frames 'reopen'
                out.append(_seg("reopen", c, o, ee, None, "open"))
                start = o
                continue
            first = c + int(np.argmax(h))
            lost = np.nonzero(~np.asarray(held, bool)[first:o])[0]
            drop = first + int(lost[0]) if len(lost) else None
        else:
            drop = None
        p = _aligned_top(ee, start, c, c, xy_tol)
        if p is None:
            p = start + int(np.argmax(ee[start:c, 2])) if c > start else c
        if p > start:
            out.append(_seg("above_target", start, p, ee, p, "keep"))
        if c > p:
            out.append(_seg("descend_close", p, c, ee, c, "close"))
        hi = min(o, drop) if drop is not None else o
        u = _aligned_top_after(ee, c, hi, c, xy_tol)
        u = c if u is None else u
        if drop is not None:
            if u > c:
                out.append(_seg("carry_up", c, u, ee, u, "keep"))
            start = nxt
            continue
        if u > c:
            out.append(_seg("carry_up", c, u, ee, u, "keep"))
        if o >= N:
            start = N
            break
        r = _aligned_top(ee, u, o, o, xy_tol)
        r = u if r is None else r
        if r > u:
            out.append(_seg("carry_over", u, r, ee, r, "keep"))
        if o > r:
            out.append(_seg("lower_open", r, o, ee, o, "open"))
        e = _aligned_top_after(ee, o, nxt, o, xy_tol)
        e = o if e is None else e
        if e > o:
            out.append(_seg("retreat", o, e, ee, e, "keep"))
        start = e
        if nxt >= N and e < N:
            out.append(_seg("done", e, N, ee, None, None))
            start = N
    return out


def sample_frames(seg: dict, n: int = 2) -> list:
    t0, t1 = seg["t0"], seg["t1"]
    return sorted({int(t0 + (t1 - t0) * i / n) for i in range(n)} & set(range(t0, t1)))
