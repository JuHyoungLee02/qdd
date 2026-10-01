"""E-LIB0c (prereg_lib0.md change 3): rim grasp for hollow objects, adapter only (no training).

User (10-02 00시 KST): "컵이나 이런거를 잡을때는 컵의 옆면을 잡던지 이래야하는데 그냥 중심에다가 밀어넣어서 잡으려하니까
거긴아무것도 없으니 안되는 거라고 보면돼". The resolver puts a 'grasp' at the centre of the object's top band; for a bowl /
basket / wide cup the top band is the rim and its centre is empty space, so the pads close on nothing.

hollow(region) -- measured from the head depth (robot removed) only:
  1. top band = region pixels within TOP_BAND_M of the region top (95th percentile height);
  2. no top-band point within CENTRE_R_M of the band centre (a ring, not a lid / ridge / cap);
  3. top-band points in all four quadrants around the centre (a closed rim, not a single edge);
  4. the surface seen within CENTRE_R_M of the centre (25th percentile height) is >= DROP_M below the top (a cavity);
  5. the rim is wider along the closing axis (base y) than the open gripper (OPEN_M): narrower rims are taken
     from outside by the trained centre grasp.
rim target: on the closing-axis line through the centre (|x - cx| < LINE_M), the rim side nearer to the TCP; xy = the mean
of that side's top-band points; z = rim top - RIM_BELOW_M (the pads, +1.2 / -0.5 cm about the TCP, straddle the wall)."""
from __future__ import annotations

import numpy as np

from ..astra_solo import resolve as RS

TOP_BAND_M = 0.010
CENTRE_R_M = 0.015
DROP_M = 0.020
OPEN_M = 0.075  # Franka open gap (real m) minus a little
LINE_M = 0.012
RIM_BELOW_M = 0.015


def region_points(cam, depth, prior_z, point_2d, tcp=None):
    """The resolver's object region (same steps as resolve.resolve_point) -> (points (N, 3), plane) or (None, plane)."""
    P = RS.depth_points(cam, depth)
    plane = RS.table_plane(P, prior_z)
    hgt = P[..., 2] - plane
    above = np.isfinite(hgt) & (hgt > RS.H_MIN) & ~RS.robot_mask(hgt, plane, tcp)
    r = RS.resolve_point(cam, depth, prior_z, point_2d, tcp=tcp)
    if r.get("kind") != "object":
        return None, plane, r
    s = (r["seed"][1], r["seed"][0])
    reg = RS._region(P, above, s)
    return P[reg], plane, r


def rim_of(P: np.ndarray, tcp) -> dict:
    """-> {"hollow": bool, "why": str, ...; with hollow: "xy", "z"} for region points P (base frame)."""
    if P is None or len(P) < 30:
        return {"hollow": False, "why": "small"}
    top = float(np.percentile(P[:, 2], 95))
    band = P[P[:, 2] >= top - TOP_BAND_M]
    c = band[:, :2].mean(0)
    rb = np.linalg.norm(band[:, :2] - c, axis=1)
    out = {"top": round(top, 4), "centre": np.round(c, 4).tolist()}
    if (rb < CENTRE_R_M).any():
        return dict(out, hollow=False, why="band_at_centre")
    q = band[:, :2] - c
    quads = {(bool(a > 0), bool(b > 0)) for a, b in q}
    if len(quads) < 4:
        return dict(out, hollow=False, why="open_band")
    near = np.linalg.norm(P[:, :2] - c, axis=1) < CENTRE_R_M
    if near.sum() < 3:
        return dict(out, hollow=False, why="no_centre_view")
    drop = top - float(np.percentile(P[near][:, 2], 25))
    out["drop"] = round(drop, 4)
    if drop < DROP_M:
        return dict(out, hollow=False, why="shallow")
    line = band[np.abs(band[:, 0] - c[0]) < LINE_M]
    neg, pos = line[line[:, 1] < c[1]], line[line[:, 1] > c[1]]
    if len(neg) < 3 or len(pos) < 3:
        return dict(out, hollow=False, why="no_rim_on_axis")
    width = float(np.median(pos[:, 1]) - np.median(neg[:, 1]))
    out["width_y"] = round(width, 4)
    if width <= OPEN_M:
        return dict(out, hollow=False, why="narrow")
    side = min((neg, pos), key=lambda s: float(np.linalg.norm(s[:, :2].mean(0) - np.asarray(tcp, float)[:2])))
    xy = side[:, :2].mean(0)
    return dict(out, hollow=True, why="rim", xy=np.round(xy, 4).tolist(), z=round(top - RIM_BELOW_M, 4))
