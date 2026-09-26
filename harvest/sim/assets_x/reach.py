"""Reachable and visible placement regions of support surfaces, and the lift per scene (pure).

ReachModel reads the L8-D reach probe (harvest.teach_l8d.probe_reach output: err_mm[y][x][z] of top-down TCP
targets at one lift command, the live head camera). The probe errors pass teach_l8d.spec.median3 first (single-step
transients are not reach limits, prereg_l8d change 1). The lift joint moves torso, arms and head rigidly in z
(probe at lift 0.0 = probe at -0.0993 shifted by +0.0993, head camera t z too -- checked 2026-09-27), so
ReachModel.at_lift(l) = the same model shifted by l - probe lift. A surface point (x, y) at height top is usable when
  reach:   every probe column bracketing (x, y) holds the TCP within ok_mm at every probed z in
           [top + Z_NEED[0], top + Z_NEED[1]] (grasp / place .. carry height of the truth plan), the band lies
           inside the probed range (no extrapolation), and no cover lies below top + Z_NEED[1] + GRIPPER_ABOVE_TCP;
  view:    the point's base and top (obj_h) project inside the head image with margin px (fixed head pitch);
  free:    no obstacle part rising above the surface within FINGER_X / FINGER_Y (open fingers close along x);
           container floors keep FINGER_X / FINGER_Y from their own rim.
placement region = the largest rectangle of usable 1 cm cells. choose_lift picks one lift per scene.
"""
from __future__ import annotations

import json

import numpy as np

from .surfaces import RES, max_rect

Z_NEED = (0.07, 0.24)  # = teach_l8d.spec.Z_NEED
OK_MM = 8.0  # = teach_l8d.spec.REACH_OK_MM
GRIPPER_ABOVE_TCP = 0.20  # [estimate] wrist + link7 height above the TCP for a top-down grasp (cover clearance)
EDGE_MARGIN = 0.03  # object centres stay >= 3 cm inside the surface box
FINGER_X = 0.065  # open pad half-gap 53.5 mm + 12 mm: keep-out along the closing axis (world x) around obstacles
FINGER_Y = 0.03  # finger half-width + margin across it
OBJ_H = 0.10  # = teach_l8d.spec.OBJ_TOP_MAX
VIEW_MARGIN_PX = 10
LIFT_DEFAULT = -0.0993  # = scene.INIT_JOINTS lift_joint
LIFT_LIMITS = (-0.50, 0.0)  # lift_joint soft limits (probe)
LIFTS = tuple([LIFT_DEFAULT] + [round(v, 2) for v in np.arange(-0.50, 0.001, 0.05)])  # default first


def median3(err):
    """= harvest.teach_l8d.spec.median3 (imported when available, same rule)."""
    try:
        from ...teach_l8d.spec import median3 as m3
        return m3(err)
    except ImportError:  # pragma: no cover
        e = np.asarray(err, float)
        out = e.copy()
        n = e.shape[-1]
        for i in range(n):
            w = e[..., max(0, i - 1):min(n, i + 2)]
            out[..., i] = np.median(w, axis=-1) if w.shape[-1] == 3 else np.max(w, axis=-1)
        return out


class ReachModel:
    def __init__(self, probe: dict, ok_mm: float = OK_MM, dz: float = 0.0, smooth: bool = True):
        order = np.argsort(np.asarray(probe["zs"], float))
        self.xs = np.asarray(probe["xs"], float)
        self.ys = np.asarray(probe["ys"], float)
        err = np.asarray(probe["err_mm"], float)  # [y, x, z]
        err = median3(err) if smooth else err  # along the probe's own z order (top-down column)
        self.zs = np.asarray(probe["zs"], float)[order] + dz
        self.err = err[:, :, order]
        self.cam = None
        if probe.get("head_cam"):
            self.cam = dict(probe["head_cam"])
            self.cam["t"] = list(np.asarray(self.cam["t"], float) + np.array([0.0, 0.0, dz]))
        self.ok_mm = float(ok_mm)
        self.probe_lift = LIFT_DEFAULT if probe.get("lift_cmd") is None else float(probe["lift_cmd"])
        self.lift = self.probe_lift + dz
        self._probe = probe
        self._smooth = smooth

    @classmethod
    def load(cls, path: str, **kw):
        with open(path) as f:
            return cls(json.load(f), **kw)

    def at_lift(self, lift: float) -> "ReachModel":
        if not LIFT_LIMITS[0] - 1e-9 <= lift <= LIFT_LIMITS[1] + 1e-9:
            raise ValueError(f"lift {lift} outside {LIFT_LIMITS}")
        return ReachModel(self._probe, self.ok_mm, dz=float(lift) - self.probe_lift, smooth=self._smooth)

    def _col_ok(self, z_lo, z_hi):
        if z_lo < self.zs.min() - 1e-9 or z_hi > self.zs.max() + 1e-9:
            return np.zeros((len(self.ys), len(self.xs)), bool)
        zi = (self.zs >= z_lo - 1e-9) & (self.zs <= z_hi + 1e-9)
        return np.all(self.err[:, :, zi] <= self.ok_mm, axis=2)

    @staticmethod
    def _brackets(grid, v):
        """(lo, hi, inside) index arrays: v between grid[lo] and grid[hi] (lo == hi on a grid point)."""
        v = np.asarray(v, float)
        inside = (v >= grid[0] - 1e-9) & (v <= grid[-1] + 1e-9)
        hi = np.clip(np.searchsorted(grid, v - 1e-9), 0, len(grid) - 1)
        on = np.abs(grid[hi] - v) < 1e-9
        lo = np.where(on, hi, np.clip(hi - 1, 0, len(grid) - 1))
        return lo, hi, inside

    def reach_grid(self, xs, ys, z_lo, z_hi) -> np.ndarray:
        """[len(xs), len(ys)] bool: every bracketing probe column ok over the z band."""
        C = self._col_ok(z_lo, z_hi)  # [y, x]
        xl, xh, xin = self._brackets(self.xs, xs)
        yl, yh, yin = self._brackets(self.ys, ys)
        ok = np.ones((len(xs), len(ys)), bool)
        for a in (xl, xh):
            for b in (yl, yh):
                ok &= C[b[None, :], a[:, None]]
        return ok & xin[:, None] & yin[None, :]

    def reach_ok(self, x: float, y: float, z_lo: float, z_hi: float) -> bool:
        return bool(self.reach_grid([x], [y], z_lo, z_hi)[0, 0])

    def visible_grid(self, xs, ys, z, h: float = OBJ_H, margin: float = VIEW_MARGIN_PX) -> np.ndarray:
        X, Y = np.meshgrid(np.asarray(xs, float), np.asarray(ys, float), indexing="ij")
        if self.cam is None:
            return np.ones(X.shape, bool)
        c = self.cam
        R, t = np.asarray(c["R"], float), np.asarray(c["t"], float)
        ok = np.ones(X.shape, bool)
        for dz in (0.0, h):
            P = np.stack([X, Y, np.full(X.shape, z + dz)], -1) - t
            Pc = P @ R
            front = Pc[..., 2] > 1e-6
            zc = np.where(front, Pc[..., 2], 1.0)
            u = c["cx"] + c["fx"] * Pc[..., 0] / zc
            v = c["cy"] + c["fy"] * Pc[..., 1] / zc
            ok &= front & (u >= margin) & (u <= c["W"] - margin) & (v >= margin) & (v <= c["H"] - margin)
        return ok

    def visible(self, x: float, y: float, z: float, h: float = OBJ_H, margin: float = VIEW_MARGIN_PX) -> bool:
        return bool(self.visible_grid([x], [y], z, h, margin)[0, 0])


def surface_cells(s: dict, margin=EDGE_MARGIN):
    """1 cm cell centres inside the surface box shrunk by margin (m, or (x, y) margins)."""
    mx, my = (margin, margin) if np.isscalar(margin) else margin
    (x0, x1), (y0, y1) = s["xy_box"]
    xs = np.arange(x0 + mx + RES / 2, x1 - mx, RES)
    ys = np.arange(y0 + my + RES / 2, y1 - my, RES)
    return xs, ys


def free_of_obstacles(xs, ys, top: float, obstacles) -> np.ndarray:
    """Cells where the open gripper can go down: no obstacle part (xy box, top z) rising above the surface within
    FINGER_X (fingers close along world x) / FINGER_Y of the cell. obstacles: [((x0, x1), (y0, y1), z_top)]."""
    F = np.ones((len(xs), len(ys)), bool)
    for (ox0, ox1), (oy0, oy1), oz in obstacles:
        if oz <= top + 0.005:
            continue
        bx = (xs[:, None] > ox0 - FINGER_X) & (xs[:, None] < ox1 + FINGER_X)
        by = (ys[None, :] > oy0 - FINGER_Y) & (ys[None, :] < oy1 + FINGER_Y)
        F &= ~(bx & by)
    return F


def region_of(s: dict, rm: ReachModel, obj_h: float = OBJ_H, obstacles=()) -> dict:
    """-> {surface, lift, reach_frac, view_frac, usable_frac, region [[x0, x1], [y0, y1]] | None, reason}."""
    top = s["top_z"]
    z_lo, z_hi = top + Z_NEED[0], top + Z_NEED[1]
    xs, ys = surface_cells(s, margin=(FINGER_X, FINGER_Y) if s.get("container") else EDGE_MARGIN)
    out = {"surface": s["id"], "top_z": top, "lift": round(rm.lift, 4), "n_cells": int(len(xs) * len(ys))}
    if len(xs) == 0 or len(ys) == 0:
        return dict(out, reach_frac=0.0, view_frac=0.0, usable_frac=0.0, region=None, area=0.0, reason="small")
    cov = s.get("covered_above")
    if cov is not None and cov < z_hi + GRIPPER_ABOVE_TCP:
        return dict(out, reach_frac=0.0, view_frac=0.0, usable_frac=0.0, region=None, area=0.0, reason="covered")
    R = rm.reach_grid(xs, ys, z_lo, z_hi)
    V = rm.visible_grid(xs, ys, top, obj_h)
    F = free_of_obstacles(xs, ys, top, obstacles)
    U = R & V & F
    r = max_rect(U)
    reg, reason, area = None, None, 0.0
    if r is not None:
        i0, i1, j0, j1 = r
        reg = [[round(float(xs[i0] - RES / 2), 3), round(float(xs[i1] + RES / 2), 3)],
               [round(float(ys[j0] - RES / 2), 3), round(float(ys[j1] + RES / 2), 3)]]
        area = round((i1 - i0 + 1) * (j1 - j0 + 1) * RES * RES, 4)
    else:
        reason = "reach" if not R.any() else ("view" if not V.any() else (
            "reach_and_view_disjoint" if not (R & V).any() else "obstacle"))
    return dict(out, reach_frac=round(float(R.mean()), 3), view_frac=round(float(V.mean()), 3),
                usable_frac=round(float(U.mean()), 3), region=reg, area=area, reason=reason)


def placement_regions(surfs: list, rm: ReachModel, obstacles=()) -> list:
    return [region_of(s, rm, obstacles=obstacles) for s in surfs]


def choose_lift(surfs: list, rm: ReachModel, obstacles=(), lifts=LIFTS, targets=None):
    """One lift for the scene: the most usable surfaces (of `targets` ids if given, else all), then the largest
    usable area, then the default lift, then the lift nearest the default. -> (lift, regions at that lift,
    {surface id: [lifts where it is usable]})."""
    best, per = None, {s["id"]: [] for s in surfs}
    for L in lifts:
        regs = placement_regions(surfs, rm.at_lift(L), obstacles)
        for p in regs:
            if p["region"] is not None:
                per[p["surface"]].append(round(float(L), 4))
        use = [p for p in regs if p["region"] is not None and (targets is None or p["surface"] in targets)]
        key = (len(use), round(sum(p["area"] for p in use), 3), L == LIFT_DEFAULT, -abs(L - LIFT_DEFAULT))
        if best is None or key > best[0]:
            best = (key, L, regs)
    return best[1], best[2], per
