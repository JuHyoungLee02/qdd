"""Rule adapter between the UNCHANGED upper LLM and JCR (user 10-01, NOW.md §1-0e; docs/stage3/jcr_design.md §0-3).
No learning. The upper keeps its trained output (point + height intent + gripper intent + assessment); this code turns
it into the JCR command and turns JCR's report back into the upper's existing 'previous command and result' text.
  destination xyz  : the shared point -> depth resolve (astra_solo.resolve, unchanged)
  target mask      : the 3D region around the pointed pixel in the head depth at command time (resolve's own region
                     rule), re-projected every decision into the current head and wrist cameras and drawn as a tint
                     on the JCR images (no tracking: what a code adapter can do on the real robot)
  stage            : the height intent (above / grasp / place / lift) + holding (robot self-measurement)
  gripper allowed  : the gripper intent (close / open / keep)
  pull strength    : kappa(stage, distance) -- weak while carrying, strong near grasp / place (truth.target_point)
  command age      : s since the command was issued
  continuation     : while the upper is thinking after an arrival (1-3 s) the adapter keeps JCR busy: after a
                     successful close -> lift start (+LIFT_START_M), after an open -> small retreat (+RETREAT_M)
Report text (JCR -> upper): contact / grasp success / anomaly as one sentence appended to the executor result."""
from __future__ import annotations

import numpy as np

KAPPA_CARRY, KAPPA_FAR, KAPPA_NEAR = 0.3, 0.5, 0.9
NEAR_M = 0.05
LIFT_START_M = 0.03
RETREAT_M = 0.02
MAX_PTS = 400
MASK_R_PX = 3
TINT = np.array([255, 0, 255], float)
ALPHA = 0.45
STAGES = ("above", "grasp", "place", "lift")


def kappa(height: str, holding: bool, dist_m: float) -> float:
    """Pull strength rule: grasp / place heights or within NEAR_M of the destination -> strong; carrying (holding,
    above the place) -> weak; approaching from afar -> medium; lift -> strong (no truth point; follow)."""
    if height in ("grasp", "place", "lift") or dist_m < NEAR_M:
        return KAPPA_NEAR
    return KAPPA_CARRY if holding else KAPPA_FAR


def region_points(cam, depth, prior_z: float, point_2d, tcp=None, max_n: int = MAX_PTS, seed: int = 0):
    """3D points (base frame) of the object region the point hits (resolve.py rules), or a 2 cm table disc around the
    table point; None when the ray misses. Subsampled to max_n with a fixed seed."""
    from ..astra_motion.geometry import lift_plane
    from ..astra_solo import resolve as RS
    P = RS.depth_points(cam, depth)
    plane = RS.table_plane(P, prior_z)
    hgt = P[..., 2] - plane
    above = np.isfinite(hgt) & (hgt > RS.H_MIN) & ~RS.robot_mask(hgt, plane, tcp)
    iu, iv = RS.to_pixel(point_2d, cam.W, cam.H)
    seed_px = (iv, iu)
    if not above[seed_px]:
        r0, r1 = max(0, iv - RS.SNAP_PX), min(cam.H, iv + RS.SNAP_PX + 1)
        c0, c1 = max(0, iu - RS.SNAP_PX), min(cam.W, iu + RS.SNAP_PX + 1)
        rr, cc = np.nonzero(above[r0:r1, c0:c1])
        if rr.size:
            d2 = (rr + r0 - iv) ** 2 + (cc + c0 - iu) ** 2
            k = int(np.argmin(d2))
            if d2[k] <= RS.SNAP_PX ** 2:
                seed_px = (int(rr[k] + r0), int(cc[k] + c0))
    if above[seed_px]:
        pts = P[RS._region(P, above, seed_px)]
    else:
        q = lift_plane(cam, iu, iv, plane)
        if q is None:
            return None
        a = np.linspace(0, 2 * np.pi, 24, endpoint=False)
        pts = np.concatenate([[q], np.stack([q[0] + 0.02 * np.cos(a), q[1] + 0.02 * np.sin(a),
                                             np.full_like(a, plane)], 1)])
    pts = pts[np.isfinite(pts).all(1)]
    if len(pts) > max_n:
        pts = pts[np.random.default_rng(seed).choice(len(pts), max_n, replace=False)]
    return np.asarray(pts, float)


def project_mask(cam, pts, r_px: int = MASK_R_PX) -> np.ndarray:
    """(H, W) bool mask of the region points drawn as r_px squares in camera cam (points behind it skipped)."""
    m = np.zeros((cam.H, cam.W), bool)
    if pts is None or len(pts) == 0:
        return m
    pc = (np.asarray(pts, float) - np.asarray(cam.t, float)) @ np.asarray(cam.R, float)
    ok = pc[:, 2] > 1e-6
    pc = pc[ok]
    u = np.floor(cam.fx * pc[:, 0] / pc[:, 2] + cam.cx).astype(int)
    v = np.floor(cam.fy * pc[:, 1] / pc[:, 2] + cam.cy).astype(int)
    for du in range(-r_px, r_px + 1):
        for dv in range(-r_px, r_px + 1):
            uu, vv = u + du, v + dv
            k = (uu >= 0) & (uu < cam.W) & (vv >= 0) & (vv < cam.H)
            m[vv[k], uu[k]] = True
    return m


def overlay(img, mask) -> np.ndarray:
    """RGB uint8 image with the mask tinted (TINT, ALPHA)."""
    x = np.asarray(img)[..., :3].astype(float)
    x[mask] = (1 - ALPHA) * x[mask] + ALPHA * TINT
    return x.clip(0, 255).astype(np.uint8)


def continuation(action: str, holding: bool, tcp) -> np.ndarray | None:
    """Adapter micro-command while the upper thinks after an arrival: lift start after a successful close, a small
    retreat after an open; None = hold."""
    t = np.asarray(tcp, float)
    if action == "close" and holding:
        return t + [0.0, 0.0, LIFT_START_M]
    if action == "open":
        return t + [0.0, 0.0, RETREAT_M]
    return None


def report_text(contact_p: float | None, grasp_ok: bool | None, anomalies) -> str:
    """JCR report -> one sentence for the upper's existing 'previous command and result' line."""
    parts = []
    if contact_p is not None:
        parts.append("the gripper touches the object" if contact_p >= 0.5 else "no contact with the object")
    if grasp_ok is not None:
        parts.append("grasp holds" if grasp_ok else "grasp failed")
    an = [a.replace("_", " ") for a in (anomalies or [])]
    if an:
        parts.append("anomaly: " + ", ".join(an))
    return ("JCR: " + "; ".join(parts)) if parts else ""
