"""Support surfaces of a triangle mesh (pure numpy, no Isaac / pxr).

Method: a 1 cm heightfield ray cast. Every non-vertical triangle is rasterised onto a world xy grid (cell centres
inside the triangle) with its z at the cell centre and its facing (up / down). A support surface is a cluster of
up-facing triangles at one height. For a cell of that cluster, cast a ray upward from just above the surface:
  first hit up-facing   -> the cell is inside a solid standing on the surface (a wall, a post): blocked
  first hit down-facing -> open space under a cover (the next shelf tier): free, clearance = hit z - top
  no hit                -> open to the sky: free
free_box = the largest axis-aligned rectangle of free cells. covered_above = the lowest cover over the free box.
rim_z = for a container (bin), the lowest of the four sides' highest solid just outside the free box.
Coordinates are the mesh's own (metres, z up); transform_surface moves a result by a pose with a yaw of k*90 deg.
"""
from __future__ import annotations

import math

import numpy as np

RES = 0.01  # grid cell (m)
UP_COS = 0.97  # up-facing: normal within ~14 deg of +z
Z_TOL = 0.006  # one surface = up faces within 6 mm of each other
EPS = 0.004  # the upward ray starts this far above the surface
MIN_AREA = 0.01  # m^2 of the free box
MIN_SIDE = 0.08  # m, both sides of the free box (a 5 x 5 cm post top is not a support surface)
RIM_MIN = 0.03  # container: all four sides rise >= 3 cm above the floor
MAX_RECTS = 4  # rectangles per surface and cover mode (greedy, largest first)


def _tri_normals(P, F):
    a, b, c = P[F[:, 0]], P[F[:, 1]], P[F[:, 2]]
    n = np.cross(b - a, c - a)
    ln = np.linalg.norm(n, axis=1)
    return n, ln


def _raster(P, F, n, x0, y0, nx, ny):
    """(cell index, z at the cell centre, facing +1 up / -1 down, triangle index) for every cell centre inside a
    non-vertical triangle's xy projection."""
    cells, zs, fac, tri = [], [], [], []
    for t in np.nonzero(np.abs(n[:, 2]) > 1e-12)[0]:
        a, b, c = P[F[t]]
        lo = np.minimum(np.minimum(a, b), c)
        hi = np.maximum(np.maximum(a, b), c)
        i0 = max(int(math.ceil((lo[0] - x0) / RES - 0.5)), 0)
        i1 = min(int(math.floor((hi[0] - x0) / RES - 0.5)), nx - 1)
        j0 = max(int(math.ceil((lo[1] - y0) / RES - 0.5)), 0)
        j1 = min(int(math.floor((hi[1] - y0) / RES - 0.5)), ny - 1)
        if i1 < i0 or j1 < j0:
            continue
        ii, jj = np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1), indexing="ij")
        px = x0 + (ii.ravel() + 0.5) * RES
        py = y0 + (jj.ravel() + 0.5) * RES
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        l1 = ((b[1] - c[1]) * (px - c[0]) + (c[0] - b[0]) * (py - c[1])) / d
        l2 = ((c[1] - a[1]) * (px - c[0]) + (a[0] - c[0]) * (py - c[1])) / d
        l3 = 1.0 - l1 - l2
        k = (l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9)
        if not k.any():
            continue
        cells.append(ii.ravel()[k] * ny + jj.ravel()[k])
        zs.append(l1[k] * a[2] + l2[k] * b[2] + l3[k] * c[2])
        fac.append(np.full(int(k.sum()), 1 if n[t, 2] > 0 else -1))
        tri.append(np.full(int(k.sum()), t))
    if not cells:
        e = np.zeros(0)
        return e.astype(int), e, e.astype(int), e.astype(int)
    return np.concatenate(cells), np.concatenate(zs), np.concatenate(fac), np.concatenate(tri)


def max_rect(mask: np.ndarray):
    """Largest all-True axis-aligned rectangle -> (i0, i1, j0, j1) inclusive cell indices, or None."""
    nx, ny = mask.shape
    h = np.zeros(ny, int)
    best, bi = 0, None
    for i in range(nx):
        h = np.where(mask[i], h + 1, 0)
        st = []  # (start j, height)
        for j in range(ny + 1):
            cur = h[j] if j < ny else 0
            s = j
            while st and st[-1][1] >= cur:
                s, hh = st.pop()
                area = hh * (j - s)
                if area > best:
                    best, bi = area, (i - hh + 1, i, s, j - 1)
            st.append((s, cur))
    return bi


def mesh_support_surfaces(P, F, min_area: float = MIN_AREA, min_side: float = MIN_SIDE, up_cos: float = UP_COS):
    """P (N, 3) points, F (M, 3) vertex indices (counter-clockwise seen from outside) -> list of surfaces
    {top_z, free_box [[x0, x1], [y0, y1]], xy_box (= free_box), area (m^2 of free_box), covered_above (z or None),
    clearance (covered_above - top_z or None), rim_z (z or None), container (bool), n_free_cells}, lowest first."""
    P = np.asarray(P, float)
    F = np.asarray(F, int)
    n, ln = _tri_normals(P, F)
    good = ln > 1e-12
    cos = np.zeros(len(F))
    cos[good] = n[good, 2] / ln[good]
    x0 = math.floor(P[:, 0].min() / RES) * RES - 2 * RES
    y0 = math.floor(P[:, 1].min() / RES) * RES - 2 * RES
    nx = int(math.ceil((P[:, 0].max() - x0) / RES)) + 2
    ny = int(math.ceil((P[:, 1].max() - y0) / RES)) + 2
    cell, z, fac, tri = _raster(P, F, n, x0, y0, nx, ny)
    up_tris = np.nonzero(cos >= up_cos)[0]
    if len(up_tris) == 0:
        return []
    tz = P[F[up_tris]][:, :, 2].mean(axis=1)
    order = np.argsort(tz)
    groups, cur = [], [order[0]]
    for a, b in zip(order[:-1], order[1:]):
        if tz[b] - tz[a] <= Z_TOL:
            cur.append(b)
        else:
            groups.append(cur)
            cur = [b]
    groups.append(cur)
    out = []
    for g in groups:
        top = float(np.average(tz[g]))
        members = np.zeros(len(F), bool)
        members[up_tris[g]] = True
        on = np.zeros(nx * ny, bool)
        on[cell[members[tri]]] = True
        above = z > top + EPS
        # first hit above the surface per cell
        hz = np.full(nx * ny, np.inf)
        hf = np.zeros(nx * ny, int)
        ci, zi, fi = cell[above], z[above], fac[above]
        o = np.lexsort((zi, ci))
        ci, zi, fi = ci[o], zi[o], fi[o]
        first = np.ones(len(ci), bool)
        first[1:] = ci[1:] != ci[:-1]
        hz[ci[first]] = zi[first]
        hf[ci[first]] = fi[first]
        allz = np.full(nx * ny, -np.inf)
        np.maximum.at(allz, cell[above], z[above])
        allz = allz.reshape(nx, ny)
        grid_hz, grid_hf = hz.reshape(nx, ny), hf.reshape(nx, ny)
        # open cells (nothing above) and covered cells (a cover above) are separate surfaces: a counter under a wall
        # cabinet gives an open front part and a covered back part
        rects = []
        for free0 in (on & (hf == 0), on & (hf == -1)):
            free = free0.reshape(nx, ny).copy()
            for _ in range(3 * MAX_RECTS):  # greedy: largest rectangle, remove it, again (a table around a bin)
                r = max_rect(free)
                if r is None or sum(1 for q in rects if q[1] is free0) >= MAX_RECTS:
                    break
                i0, i1, j0, j1 = r
                free[i0:i1 + 1, j0:j1 + 1] = False
                w, d = (i1 - i0 + 1) * RES, (j1 - j0 + 1) * RES
                if w >= min_side - 1e-9 and d >= min_side - 1e-9 and w * d >= min_area - 1e-9:
                    rects.append((r, free0))
        for (i0, i1, j0, j1), free0 in rects:
            w, d = (i1 - i0 + 1) * RES, (j1 - j0 + 1) * RES
            free = free0
            box = [[x0 + i0 * RES, x0 + (i1 + 1) * RES], [y0 + j0 * RES, y0 + (j1 + 1) * RES]]
            sub_z, sub_f = grid_hz[i0:i1 + 1, j0:j1 + 1], grid_hf[i0:i1 + 1, j0:j1 + 1]
            cov = sub_z[sub_f == -1]
            covered = float(cov.min()) if cov.size else None
            # rim: highest solid above the surface in the one-cell ring just outside each side of the box
            sides = []
            for ring in (allz[max(i0 - 1, 0), j0:j1 + 1], allz[min(i1 + 1, nx - 1), j0:j1 + 1],
                         allz[i0:i1 + 1, max(j0 - 1, 0)], allz[i0:i1 + 1, min(j1 + 1, ny - 1)]):
                sides.append(float(ring.max()) if ring.size else -np.inf)
            rim = min(sides)
            container = bool(np.isfinite(rim) and rim - top >= RIM_MIN)
            out.append({"top_z": top, "free_box": box, "xy_box": [list(box[0]), list(box[1])], "area": w * d,
                        "covered_above": covered, "clearance": None if covered is None else covered - top,
                        "rim_z": rim if container else None, "container": container,
                        "n_free_cells": int(free.sum())})
    return out


def transform_surface(s: dict, pos=(0.0, 0.0, 0.0), yaw: float = 0.0, scale: float = 1.0) -> dict:
    """Surface (mesh frame) -> world: p_w = R(yaw) (scale p) + pos. Only yaw = k * 90 deg (a box stays a box)."""
    k = yaw / (math.pi / 2)
    if abs(k - round(k)) > 1e-6:
        raise ValueError(f"yaw {yaw}: only multiples of 90 deg")
    c, s_ = round(math.cos(yaw)), round(math.sin(yaw))
    (bx0, bx1), (by0, by1) = s["free_box"]
    pts = np.array([[x, y] for x in (bx0, bx1) for y in (by0, by1)], float) * scale
    R = np.array([[c, -s_], [s_, c]], float)
    w = pts @ R.T + np.asarray(pos[:2], float)
    zoff = float(pos[2])
    out = dict(s)
    box = [[float(w[:, 0].min()), float(w[:, 0].max())], [float(w[:, 1].min()), float(w[:, 1].max())]]
    out.update(free_box=box, xy_box=[list(box[0]), list(box[1])], area=s["area"] * scale * scale,
               top_z=s["top_z"] * scale + zoff)
    for key in ("covered_above", "rim_z"):
        out[key] = None if s.get(key) is None else s[key] * scale + zoff
    out["clearance"] = None if out["covered_above"] is None else out["covered_above"] - out["top_z"]
    return out


def box_mesh(lo, hi):
    """Closed axis-aligned box (points, faces), outward normals -- parametric furniture parts."""
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    P = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], float)
    F = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5],
                  [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]])
    return P, F


def merge_meshes(meshes):
    Ps, Fs, k = [], [], 0
    for P, F in meshes:
        Ps.append(np.asarray(P, float))
        Fs.append(np.asarray(F, int) + k)
        k += len(P)
    return np.concatenate(Ps), np.concatenate(Fs)
