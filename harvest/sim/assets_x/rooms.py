"""Room backgrounds (MolmoSpaces iTHOR, CC BY 4.0): put the robot + furniture work zone into a clear part of a room.

Pure part: from the room's collider triangles (usd_import.collider_mesh of the scene stage, metres, z up) build a
1 cm occupancy grid -- a cell is blocked when any collider face lies between CLEAR_Z[0] and CLEAR_Z[1] above the
floor, open when nothing does and the floor is under it -- and find, for each yaw k*90 deg, the largest clear
rectangle that holds the work zone ZONE (robot body + furniture, robot frame). room_pose() returns the room pose
(position, yaw) that puts that rectangle's zone around the robot. The room is spawned render-only (its physics
stripped, usd_import.make_visual): the zone is clear of every room collider by construction, so nothing in the room
can touch the robot or the furniture, and the room never changes the physics of an episode.
"""
from __future__ import annotations

import math

import numpy as np

from . import surfaces as S

ZONE = ((-0.50, 1.30), (-1.10, 0.90))  # robot-frame box that must be clear: robot body .. furniture (a 2 m counter)
CLEAR_Z = (0.03, 2.00)
FLOOR_TOL = 0.03


def occupancy(P, F, render=None):
    """-> (x0, y0, nx, ny, open [nx, ny] bool, floor z): a cell is open when a floor face lies under it and no face
    of the colliders (P, F) or of the render mesh (render = (Pr, Fr), optional: decorations without colliders)
    lies in CLEAR_Z above the floor. The floor is found on the render mesh when given (iTHOR floors carry no
    collider), else on the colliders: the most common up-facing height among the lowest 30 cm (by cell count)."""
    P = np.asarray(P, float)
    F = np.asarray(F, int)
    meshes = [(P, F)] + ([(np.asarray(render[0], float), np.asarray(render[1], int))] if render is not None else [])
    allP = np.concatenate([m[0] for m in meshes])
    x0 = math.floor(allP[:, 0].min() / S.RES) * S.RES
    y0 = math.floor(allP[:, 1].min() / S.RES) * S.RES
    nx = int(math.ceil((allP[:, 0].max() - x0) / S.RES)) + 1
    ny = int(math.ceil((allP[:, 1].max() - y0) / S.RES)) + 1
    ras = [S._raster(Pm, Fm, S._tri_normals(Pm, Fm)[0], x0, y0, nx, ny) for Pm, Fm in meshes]
    fcell, fz_, ffac, _ = ras[-1]  # floor source: the render mesh if given
    up = fz_[ffac == 1]
    if up.size:
        low = up[up <= up.min() + 0.30]
        vals, cnt = np.unique(np.round(low, 2), return_counts=True)
        floor_z = float(vals[np.argmax(cnt)])
    else:
        floor_z = 0.0
    blocked = np.zeros(nx * ny, bool)
    for cell, z, _, _ in ras:
        rel = z - floor_z
        blocked[cell[(rel > CLEAR_Z[0]) & (rel < CLEAR_Z[1])]] = True
    floor = np.zeros(nx * ny, bool)
    floor[fcell[(ffac == 1) & (np.abs(fz_ - floor_z) <= FLOOR_TOL)]] = True
    return x0, y0, nx, ny, (floor & ~blocked).reshape(nx, ny), floor_z


def room_pose(P, F, zone=ZONE, render=None):
    """-> {yaw, pos (x, y, z), clear_box (room frame), margin} or None. The robot sits at the world origin; the room
    is spawned at pos with yaw so the chosen clear rectangle contains the zone (centred in the spare room)."""
    x0, y0, nx, ny, open_, floor_z = occupancy(P, F, render)
    (zx0, zx1), (zy0, zy1) = zone
    best = None
    for k in range(4):
        yaw = k * math.pi / 2
        # the zone's extent in the room frame for this yaw (room = R(-yaw) world)
        zx, zy = (zx1 - zx0, zy1 - zy0) if k % 2 == 0 else (zy1 - zy0, zx1 - zx0)
        r = S.max_rect(open_)
        if r is None:
            continue
        i0, i1, j0, j1 = r
        w, h = (i1 - i0 + 1) * S.RES, (j1 - j0 + 1) * S.RES
        if w < zx - 1e-9 or h < zy - 1e-9:
            continue
        margin = min(w - zx, h - zy)
        if best is None or margin > best["margin"]:
            cx, cy = x0 + (i0 + i1 + 1) / 2 * S.RES, y0 + (j0 + j1 + 1) / 2 * S.RES
            # zone centre (robot frame) -> room point (cx, cy): world = R(yaw) (room - c) + zc
            zc = np.array([(zx0 + zx1) / 2, (zy0 + zy1) / 2])
            c, s = math.cos(yaw), math.sin(yaw)
            R = np.array([[c, -s], [s, c]])
            pos = zc - R @ np.array([cx, cy])
            best = {"yaw": round(yaw, 6), "pos": [round(float(pos[0]), 4), round(float(pos[1]), 4),
                                                   round(-floor_z, 4)],
                    "clear_box": [[round(x0 + i0 * S.RES, 3), round(x0 + (i1 + 1) * S.RES, 3)],
                                  [round(y0 + j0 * S.RES, 3), round(y0 + (j1 + 1) * S.RES, 3)]],
                    "margin": round(margin, 3)}
    return best


def zone_is_clear(P, F, pose, zone=ZONE, render=None) -> bool:
    """Check: room colliders (and render mesh) moved by pose leave the zone (robot frame) open."""

    def move(Q):
        Q = np.asarray(Q, float).copy()
        c, s = math.cos(pose["yaw"]), math.sin(pose["yaw"])
        Q[:, :2] = Q[:, :2] @ np.array([[c, s], [-s, c]]) + np.asarray(pose["pos"][:2])
        Q[:, 2] += pose["pos"][2]
        return Q
    x0, y0, nx, ny, open_, _ = occupancy(move(P), F, None if render is None else (move(render[0]), render[1]))
    (zx0, zx1), (zy0, zy1) = zone
    i0, i1 = int(round((zx0 - x0) / S.RES)), int(round((zx1 - x0) / S.RES))
    j0, j1 = int(round((zy0 - y0) / S.RES)), int(round((zy1 - y0) / S.RES))
    if i0 < 0 or j0 < 0 or i1 > nx or j1 > ny:
        return False
    return bool(open_[i0:i1, j0:j1].all())
