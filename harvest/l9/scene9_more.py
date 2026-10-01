"""L9 v2 environment families (spec §12.3: the 8 v1 families + >= 6 new, "as wide as possible"). Same contract as the
v1 family functions in scene9: fn(b: scene9._B, rule, d, yc) -> params dict, parts / nodes in the scene frame S
(x = towards the furniture back, front edge at x = d; y = left; the arm band is around y = b.yb). Pure (numpy).

Design rules carried over from v1 (pitfalls P141 / P142): the main work node spans the arm band (x d .. >= d + 0.38,
y yb +- 0.17); parts that rise more than 13 cm above a node near the band stay at its back / far side (the carry
clearance); boards higher than node + 0.45 m (upper shelves, hoods) do not block a node (scene9.blocked_s) and stand
over the back half where possible. Heights 0.40-1.06 m (reachable through the lift: scene9.REL_OK).
Choices of shapes / ranges are our own [hypothesis, judged by the G2 frame check and the G4 v2 diversity numbers]."""
from __future__ import annotations

import math

import numpy as np

from . import scene9 as S

STONE = [(0.85, 0.84, 0.80), (0.20, 0.20, 0.21), (0.55, 0.53, 0.50), (0.92, 0.92, 0.90), (0.40, 0.36, 0.33),
         (0.70, 0.66, 0.60)]
PLASTIC = [(0.90, 0.25, 0.20), (0.20, 0.55, 0.85), (0.95, 0.80, 0.20), (0.30, 0.70, 0.35), (0.95, 0.55, 0.15),
           (0.60, 0.35, 0.75), (0.95, 0.95, 0.95)]
APPLIANCE = [(0.95, 0.95, 0.94), (0.88, 0.89, 0.90), (0.30, 0.31, 0.33), (0.75, 0.76, 0.78)]
EPOXY = [(0.10, 0.10, 0.11), (0.16, 0.17, 0.18), (0.22, 0.25, 0.27), (0.85, 0.86, 0.86)]
OUTDOOR_WOOD = [(0.52, 0.40, 0.28), (0.45, 0.34, 0.24), (0.62, 0.55, 0.45), (0.35, 0.30, 0.25)]


def _c(rng, pal):
    return S._c(rng, pal)


def _band_y(b, half=0.20):
    """(lo, hi) of the arm band in y (S frame ~ world frame up to the scene yaw)."""
    return b.yb - half, b.yb + half


def _far_y(b, yc, w, size):
    """The y centre of an item of width `size` at the furniture end away from the arm band."""
    y0, y1 = yc - w / 2, yc + w / 2
    return (y1 - size / 2 - 0.03) if b.sgn > 0 else (y0 + size / 2 + 0.03)


def _basin_y(b, yc, w, sw):
    """Basin centre y: half the scenes next to the arm band (a usable container), half at the far end (the band
    keeps a wide top)."""
    if b.rng.random() < 0.5:
        return b.yb + b.rng.uniform(-0.06, 0.06)
    return _far_y(b, yc, w, sw + 0.06)


def _inset_basin(b, pid, top, d, back, y0, y1, sy, sw, sx0, sd, depth, ctop, cbasin, thick=0.04):
    """Counter top in four pieces around a basin opening + the two side top nodes + the basin (container)."""
    b.box(f"{pid}_a", d, back, y0, sy - sw / 2, top - thick, top, ctop, "top", "top")
    b.box(f"{pid}_b", d, back, sy + sw / 2, y1, top - thick, top, ctop, "top", "top")
    b.box(f"{pid}_c", d, sx0, sy - sw / 2, sy + sw / 2, top - thick, top, ctop, "top", "top")
    b.box(f"{pid}_d", sx0 + sd, back, sy - sw / 2, sy + sw / 2, top - thick, top, ctop, "top", "top")
    if sy - sw / 2 - y0 > 0.12:
        b.node("top", f"{pid}_a", top, d, back - 0.02, y0, sy - sw / 2)
    if y1 - sy - sw / 2 > 0.12:
        b.node("top", f"{pid}_b", top, d, back - 0.02, sy + sw / 2, y1)
    b.open_box(f"{pid}_sink", sx0, sx0 + sd, sy - sw / 2, sy + sw / 2, top - depth, depth, cbasin, kind="container")


def _stools(b, x, ys, h=0.65, pal=None):
    for i, y in enumerate(ys):
        b.box(f"stool{i}", x, x + 0.34, y - 0.17, y + 0.17, 0.0, h, _c(b.rng, pal or (S.METAL + S.WOOD)), "chair")


def _posts(b, pid, x0, x1, y0, y1, z1, color, t=0.035):
    """Four corner posts (rack / shelving uprights)."""
    for i, (x, y) in enumerate(((x0, y0), (x0, y1 - t), (x1 - t, y0), (x1 - t, y1 - t))):
        b.box(f"{pid}_post{i}", x, x + t, y, y + t, 0.0, z1, color, "leg")


# ----------------------------------------------------------------------------------------------- 9 kitchen island
def _kitchen_island(b, rule, d, yc):
    rng = b.rng
    top = rng.uniform(0.86, 0.95)
    dep, w = rng.uniform(0.72, 0.88), rng.uniform(1.20, 1.70)
    y0, y1 = yc - w / 2, yc + w / 2
    stone = _c(rng, STONE + S.WOOD)
    b.box("island_body", d + 0.10, d + dep - 0.25, y0 + 0.05, y1 - 0.05, 0.0, top - 0.04, _c(rng, S.PAINT + S.WOOD), "body")
    _stools(b, d + dep + 0.10, np.linspace(y0 + 0.30, y1 - 0.30, int(rng.integers(2, 4))))
    if rule == "prep_sink":
        sw, sd = rng.uniform(0.32, 0.42), rng.uniform(0.28, 0.34)
        sy = _basin_y(b, yc, w, sw)
        db = rng.uniform(0.10, 0.15)
        _inset_basin(b, "isl", top, d, d + dep, y0, y1, sy, sw, d + 0.10, sd, db, stone, _c(rng, S.METAL))
        return {"sink": [round(sw, 3), round(db, 3)]}
    b.box("island", d, d + dep, y0, y1, top - 0.04, top, stone, "top", "top")
    host = b.node("top", "island", top, d, d + dep, y0, y1)
    if rule == "slab":
        return {"depth": round(dep, 3)}
    if rule == "board":
        bx = d + rng.uniform(0.03, 0.10)
        by = b.yb + rng.uniform(-0.06, 0.06)
        bw, bd = rng.uniform(0.28, 0.40), rng.uniform(0.22, 0.30)
        b.zone("zone", host, bx, bx + bd, by - bw / 2, by + bw / 2, color=_c(rng, S.WOOD), pad=0.015)
        return {"board": [round(bw, 3), round(bd, 3)]}
    if rule == "bowl":
        bw = rng.uniform(0.22, 0.30)
        by = b.yb + rng.uniform(-0.10, 0.10)
        bx = d + rng.uniform(0.05, 0.15)
        b.open_box("fruitbowl", bx, bx + bw, by - bw / 2, by + bw / 2, top, rng.uniform(0.04, 0.07),
                   _c(rng, S.WOOD + PLASTIC + S.METAL))
        return {"bowl": round(bw, 3)}
    if rule == "bar_ledge":
        lt = top + rng.uniform(0.10, 0.16)
        lx = d + dep - rng.uniform(0.22, 0.30)
        b.box("ledge", lx, d + dep, y0, y1, top, lt, stone, "top", "top")
        b.node("top", "ledge", lt, lx, d + dep, y0, y1)
        host["box"][0][1] = round(lx - 0.01, 4)
        return {"ledge": round(lt, 3)}
    raise ValueError(rule)


# ----------------------------------------------------------------------------------------------- 10 pantry shelf
def _pantry_shelf(b, rule, d, yc):
    rng = b.rng
    w = rng.uniform(0.90, 1.40)
    y0, y1 = yc - w / 2, yc + w / 2
    top, dep = rng.uniform(0.74, 0.95), rng.uniform(0.38, 0.48)
    col = _c(rng, S.WOOD + S.PAINT + S.METAL)
    up = top + rng.uniform(0.50, 0.62)
    b.box("side_l", d, d + dep, y0, y0 + 0.025, 0.0, up + 0.03, col, "side")
    b.box("side_r", d, d + dep, y1 - 0.025, y1, 0.0, up + 0.03, col, "side")
    b.box("board_low", d, d + dep, y0 + 0.025, y1 - 0.025, 0.12, 0.15, col, "body")
    b.box("board", d, d + dep, y0 + 0.025, y1 - 0.025, top - 0.03, top, col, "top", "top")
    b.box("board_up", d + dep * 0.45, d + dep, y0 + 0.025, y1 - 0.025, up, up + 0.03, col, "top", "top")
    b.box("back", d + dep, d + dep + 0.015, y0, y1, 0.0, up + 0.03, _c(rng, S.PAINT + S.WOOD), "wall")
    host = b.node("top", "board", top, d, d + dep, y0 + 0.025, y1 - 0.025)
    if rule == "open":
        return {"up": round(up, 3)}
    if rule == "baskets":
        n = int(rng.integers(2, 4))
        bw = (w - 0.10) / n
        for i in range(n):
            yy = y0 + 0.05 + i * bw
            b.open_box(f"pbask{i}", d + 0.04, d + 0.04 + rng.uniform(0.20, 0.28), yy + 0.01, yy + bw - 0.01, top,
                       rng.uniform(0.06, 0.10), _c(rng, S.WOOD + S.FABRIC + PLASTIC))
        return {"baskets": n}
    if rule == "jars":
        return {"holders": "forced"}
    if rule == "riser":
        rh = rng.uniform(0.08, 0.12)
        rx = d + dep - rng.uniform(0.16, 0.20)
        b.box("riser", rx, d + dep - 0.01, y0 + 0.03, y1 - 0.03, top, top + rh, col, "top", "top")
        b.node("top", "riser", top + rh, rx, d + dep - 0.01, y0 + 0.03, y1 - 0.03)
        host["box"][0][1] = round(rx - 0.01, 4)
        return {"riser": round(rh, 3)}
    if rule == "bins":
        ow = rng.uniform(0.32, 0.46)
        oy = b.yb + rng.uniform(-0.08, 0.08)
        b.open_box("pbins", d + 0.04, d + 0.04 + rng.uniform(0.22, 0.30), oy - ow / 2, oy + ow / 2, top,
                   rng.uniform(0.05, 0.08), _c(rng, PLASTIC), dividers=int(rng.integers(1, 3)))
        return {}
    raise ValueError(rule)


# ----------------------------------------------------------------------------------------------- 11 bathroom vanity
def _bathroom_vanity(b, rule, d, yc):
    rng = b.rng
    w = rng.uniform(0.90, 1.40)
    y0, y1 = yc - w / 2, yc + w / 2
    top, dep = rng.uniform(0.80, 0.90), rng.uniform(0.46, 0.56)
    stone = _c(rng, STONE)
    b.box("van_body", d + 0.02, d + dep, y0, y1, 0.0, top - 0.03, _c(rng, S.WOOD + S.PAINT), "body")
    b.box("splash", d + dep - 0.02, d + dep, y0, y1, top, top + rng.uniform(0.08, 0.12), stone, "wall")
    b.box("mirror", d + dep, d + dep + 0.02, yc - 0.35, yc + 0.35, top + 0.25, top + 1.00, _c(rng, S.METAL), "wall")
    b.backwall(d + dep + 0.02, y0 - 0.8, y1 + 0.8, _c(rng, S.PAINT + STONE))
    if rule == "basin":
        sw, sd = rng.uniform(0.34, 0.42), rng.uniform(0.26, 0.32)
        sy = _basin_y(b, yc, w, sw)
        db = rng.uniform(0.09, 0.13)
        _inset_basin(b, "van", top, d, d + dep, y0, y1, sy, sw, d + 0.07, sd, db, stone, _c(rng, APPLIANCE), thick=0.03)
        return {"basin": round(sw, 3)}
    b.box("van_top", d, d + dep, y0, y1, top - 0.03, top, stone, "top", "top")
    host = b.node("top", "van_top", top, d, d + dep - 0.02, y0, y1)
    if rule == "vessel":
        vw = rng.uniform(0.28, 0.36)
        vy = _basin_y(b, yc, w, vw)
        b.open_box("vessel", d + 0.10, d + 0.10 + vw * 0.8, vy - vw / 2, vy + vw / 2, top, rng.uniform(0.10, 0.12),
                   _c(rng, APPLIANCE + STONE), kind="container")
        return {"vessel": round(vw, 3)}
    if rule == "double":
        for i, s in enumerate((-1, 1)):
            vw = rng.uniform(0.24, 0.30)
            vy = yc + s * (w / 2 - vw / 2 - 0.05)
            b.open_box(f"vessel{i}", d + 0.10, d + 0.10 + vw * 0.8, vy - vw / 2, vy + vw / 2, top, 0.11,
                       _c(rng, APPLIANCE), kind="container")
        return {}
    if rule == "toiletry_tray":
        tw = rng.uniform(0.22, 0.30)
        ty = b.yb + rng.uniform(-0.08, 0.08)
        b.open_box("ttray", d + 0.05, d + 0.05 + rng.uniform(0.14, 0.20), ty - tw / 2, ty + tw / 2, top, 0.025,
                   _c(rng, S.METAL + S.WOOD + STONE))
        return {"tray": round(tw, 3)}
    if rule == "towel_shelf":
        sz = top + rng.uniform(0.46, 0.55)
        b.box("towel_shelf", d + dep * 0.5, d + dep, y0 + 0.05, y1 - 0.05, sz, sz + 0.025, _c(rng, S.WOOD + S.METAL),
              "top", "top")
        b.box("towels", d + dep * 0.55, d + dep - 0.02, yc - 0.2, yc + 0.2, sz + 0.025, sz + 0.12, _c(rng, S.FABRIC), "mat")
        host["box"][0][1] = round(d + dep - 0.04, 4)
        return {"shelf": round(sz, 3)}
    raise ValueError(rule)


# ----------------------------------------------------------------------------------------------- 12 cafe counter
def _cafe_counter(b, rule, d, yc):
    rng = b.rng
    w = rng.uniform(1.10, 1.70)
    y0, y1 = yc - w / 2, yc + w / 2
    top, dep = rng.uniform(0.92, 1.04), rng.uniform(0.55, 0.70)
    b.cabinet("cafe", top, d, d + dep, y0, y1, _c(rng, S.WOOD + S.PAINT + STONE))
    if rule == "pickup":
        return {}
    if rule == "pastry_case":
        cw = rng.uniform(0.40, 0.55)
        cy = _far_y(b, yc, w, cw)
        if abs(cy - b.yb) < cw / 2 + 0.10:
            cy = yc + b.sgn * (w / 2 - cw / 2)
        b.box("case_base", d + 0.05, d + dep - 0.05, cy - cw / 2, cy + cw / 2, top, top + 0.06, _c(rng, S.METAL), "body")
        b.box("case_glass", d + 0.06, d + dep - 0.06, cy - cw / 2 + 0.01, cy + cw / 2 - 0.01, top + 0.06,
              top + rng.uniform(0.30, 0.40), (0.80, 0.86, 0.88), "screen")
        return {"case": round(cw, 3)}
    if rule == "condiments":
        return {"holders": "forced"}
    if rule == "tray_return":
        for i in range(int(rng.integers(1, 3))):
            tw = rng.uniform(0.28, 0.36)
            ty = b.yb + (i - 0.5) * 0.30 + rng.uniform(-0.03, 0.03)
            b.open_box(f"rtray{i}", d + 0.05 + 0.25 * i, d + 0.05 + 0.25 * i + rng.uniform(0.20, 0.24), ty - tw / 2,
                       ty + tw / 2, top, 0.025, _c(rng, PLASTIC + S.WOOD))
        return {}
    if rule == "two_level":
        lt = top + rng.uniform(0.08, 0.14)
        lx = d + dep - rng.uniform(0.20, 0.26)
        b.box("pickup_ledge", lx, d + dep, y0, y1, top, lt, _c(rng, S.WOOD + STONE), "top", "top")
        b.node("top", "pickup_ledge", lt, lx, d + dep, y0, y1)
        b.nodes[0]["box"][0][1] = round(lx - 0.01, 4)
        return {"ledge": round(lt, 3)}
    raise ValueError(rule)


# ----------------------------------------------------------------------------------------------- 13 warehouse rack
def _warehouse_rack(b, rule, d, yc):
    rng = b.rng
    if rule == "floor_crate":
        return _floor_crate(b, d, yc)
    w = rng.uniform(1.10, 1.80)
    y0, y1 = yc - w / 2, yc + w / 2
    top, dep = rng.uniform(0.70, 0.95), rng.uniform(0.60, 0.85)
    steel = _c(rng, S.METAL + [(0.85, 0.45, 0.10), (0.15, 0.30, 0.60)])
    up = top + rng.uniform(0.58, 0.72)
    _posts(b, "rack", d, d + dep, y0, y1, up + 0.05, steel, t=0.06)
    b.box("beam_f", d, d + 0.06, y0, y1, top - 0.08, top - 0.02, steel, "body")
    b.box("deck", d, d + dep, y0 + 0.06, y1 - 0.06, top - 0.02, top, _c(rng, S.WOOD + S.METAL), "top", "top")
    b.box("deck_up", d, d + dep, y0 + 0.06, y1 - 0.06, up, up + 0.03, _c(rng, S.WOOD + S.METAL), "top", "top")
    host = b.node("top", "deck", top, d, d + dep, y0 + 0.06, y1 - 0.06)
    if rule == "beam":
        return {"up": round(up, 3)}
    if rule == "totes":
        for i in range(int(rng.integers(1, 3))):
            tw = rng.uniform(0.30, 0.40)
            ty = b.yb + (0.0 if i == 0 else -b.sgn * 0.40) + rng.uniform(-0.04, 0.04)
            b.open_box(f"tote{i}", d + 0.06, d + 0.06 + rng.uniform(0.26, 0.34), ty - tw / 2, ty + tw / 2, top,
                       rng.uniform(0.08, 0.12), _c(rng, PLASTIC))
        return {}
    if rule == "cartons":
        x = d + dep - rng.uniform(0.25, 0.32)
        yy = y0 + 0.08
        i = 0
        while yy < y1 - 0.25 and i < 4:
            cw = rng.uniform(0.25, 0.40)
            b.box(f"carton{i}", x, d + dep - 0.02, yy, yy + cw, top, top + rng.uniform(0.18, 0.35),
                  _c(rng, [(0.72, 0.56, 0.38), (0.65, 0.50, 0.33), (0.80, 0.70, 0.52)]), "body")
            yy += cw + rng.uniform(0.04, 0.20)
            i += 1
        host["box"][0][1] = round(x - 0.01, 4)
        return {"cartons": i}
    if rule == "wire_bins":
        ow = rng.uniform(0.36, 0.50)
        oy = b.yb + rng.uniform(-0.08, 0.08)
        b.open_box("wbins", d + 0.05, d + 0.05 + rng.uniform(0.24, 0.32), oy - ow / 2, oy + ow / 2, top,
                   rng.uniform(0.06, 0.09), steel, dividers=int(rng.integers(1, 4)))
        return {}
    if rule == "picking_cart":
        ct = top + rng.choice([-1, 1]) * rng.uniform(0.06, 0.12)
        e = b.yb + rng.uniform(-0.04, 0.04)
        sy = (min(e, e - b.sgn * 0.48), max(e, e - b.sgn * 0.48))
        b.table("cart", ct, d - 0.02, d + 0.48, *sy, _c(rng, S.METAL + PLASTIC), thick=0.03, leg=0.03)
        return {"cart": round(ct, 3)}
    raise ValueError(rule)


# ----------------------------------------------------------------------------------------------- 14 lab bench
def _lab_bench(b, rule, d, yc):
    rng = b.rng
    w = rng.uniform(1.20, 1.80)
    y0, y1 = yc - w / 2, yc + w / 2
    top, dep = rng.uniform(0.86, 0.94), rng.uniform(0.68, 0.82)
    ep = _c(rng, EPOXY)
    b.box("lab_body", d + 0.03, d + dep, y0, y1, 0.0, top - 0.03, _c(rng, S.PAINT + S.WOOD + APPLIANCE), "body")
    if rule == "lab_sink":
        sw, sd = rng.uniform(0.30, 0.38), rng.uniform(0.24, 0.30)
        sy = _basin_y(b, yc, w, sw)
        db = rng.uniform(0.12, 0.16)
        _inset_basin(b, "lab", top, d, d + dep, y0, y1, sy, sw, d + 0.08, sd, db, ep, _c(rng, EPOXY + S.METAL), thick=0.03)
        return {}
    b.box("lab_top", d, d + dep, y0, y1, top - 0.03, top, ep, "top", "top")
    host = b.node("top", "lab_top", top, d, d + dep, y0, y1)
    if rule == "reagent_shelf":
        sz = top + rng.uniform(0.40, 0.48)
        sx = d + dep - rng.uniform(0.20, 0.26)
        _posts(b, "reag", sx, d + dep, y0 + 0.05, y1 - 0.05, sz, _c(rng, S.METAL), t=0.025)
        b.box("reag_board", sx, d + dep, y0 + 0.05, y1 - 0.05, sz, sz + 0.02, _c(rng, S.METAL + S.WOOD), "top", "top")
        host["box"][0][1] = round(sx - 0.02, 4)
        return {"shelf": round(sz, 3)}
    if rule == "tube_rack":
        return {"holders": "forced"}
    if rule == "hood":
        hz = top + rng.uniform(0.62, 0.75)
        b.box("hood_l", d + 0.02, d + dep, y0, y0 + 0.03, top, hz, _c(rng, APPLIANCE), "side")
        b.box("hood_r", d + 0.02, d + dep, y1 - 0.03, y1, top, hz, _c(rng, APPLIANCE), "side")
        b.box("hood_top", d + 0.02, d + dep, y0, y1, hz, hz + 0.20, _c(rng, APPLIANCE), "cabinet")
        b.box("hood_back", d + dep - 0.03, d + dep, y0, y1, top, hz, _c(rng, APPLIANCE + S.METAL), "wall")
        host["box"][1] = [round(y0 + 0.03, 4), round(y1 - 0.03, 4)]
        return {"hood": round(hz, 3)}
    if rule == "tray_bins":
        for i in range(2):
            tw = rng.uniform(0.24, 0.32)
            ty = b.yb + (i - 0.5) * 0.30
            b.open_box(f"ltray{i}", d + 0.05 + 0.24 * i, d + 0.05 + 0.24 * i + rng.uniform(0.18, 0.22), ty - tw / 2,
                       ty + tw / 2, top, rng.uniform(0.03, 0.05), _c(rng, APPLIANCE + PLASTIC))
        return {}
    raise ValueError(rule)


# ----------------------------------------------------------------------------------------------- 15 craft workshop
def _craft_workshop(b, rule, d, yc):
    rng = b.rng
    w = rng.uniform(1.10, 1.70)
    y0, y1 = yc - w / 2, yc + w / 2
    top, dep = rng.uniform(0.82, 0.92), rng.uniform(0.60, 0.80)
    wood = _c(rng, S.WOOD + OUTDOOR_WOOD)
    if rule == "trestle":
        top = rng.uniform(0.74, 0.86)
        b.box("board", d, d + dep, y0, y1, top - 0.035, top, wood, "top", "top")
        for i, yy in enumerate((y0 + 0.12, y1 - 0.16)):
            b.box(f"horse{i}", d + 0.05, d + dep - 0.05, yy, yy + 0.04, top - 0.12, top - 0.035, wood, "leg")
            for j, xx in enumerate((d + 0.08, d + dep - 0.12)):
                b.box(f"horse{i}_leg{j}", xx, xx + 0.04, yy, yy + 0.04, 0.0, top - 0.12, wood, "leg")
        b.node("top", "board", top, d, d + dep, y0, y1)
        return {"trestle": round(top, 3)}
    host = b.table("craft", top, d, d + dep, y0, y1, wood, thick=0.06, leg=0.07)
    b.box("stretcher", d + 0.05, d + dep - 0.05, y0 + 0.05, y1 - 0.05, 0.15, 0.18, wood, "leg")
    if rule == "vise":
        vy = _far_y(b, yc, w, 0.16)
        b.box("vise", d, d + 0.14, vy - 0.08, vy + 0.08, top, top + 0.12, _c(rng, S.METAL + [(0.20, 0.35, 0.55)]), "body")
        return {}
    if rule == "tool_wall":
        b.box("toolboard", d + dep - 0.02, d + dep, y0, y1, top, top + 0.85, _c(rng, S.WOOD + S.PAINT), "wall")
        sz = top + rng.uniform(0.48, 0.58)
        b.box("tool_shelf", d + dep - 0.20, d + dep - 0.02, y0 + 0.05, y1 - 0.05, sz, sz + 0.02, wood, "top", "top")
        return {"shelf": round(sz, 3)}
    if rule == "bins_row":
        n = int(rng.integers(2, 4))
        for i in range(n):
            bw = rng.uniform(0.14, 0.20)
            by = y0 + 0.15 + i * (w - 0.30) / max(n - 1, 1)
            if abs(by - b.yb) < 0.12:
                continue
            b.open_box(f"cbin{i}", d + dep - 0.26, d + dep - 0.06, by - bw / 2, by + bw / 2, top, 0.09, _c(rng, PLASTIC))
        return {"bins": n}
    if rule == "cutting_mat":
        mw, md = rng.uniform(0.36, 0.50), rng.uniform(0.26, 0.34)
        my = b.yb + rng.uniform(-0.05, 0.05)
        b.zone("zone", host, d + 0.03, d + 0.03 + md, my - mw / 2, my + mw / 2,
               color=_c(rng, [(0.20, 0.45, 0.30), (0.15, 0.20, 0.30), (0.30, 0.30, 0.32)]))
        return {"mat": [round(mw, 3), round(md, 3)]}
    raise ValueError(rule)


# ----------------------------------------------------------------------------------------------- 16 bedside
def _bedside(b, rule, d, yc):
    rng = b.rng
    yc = b.yb + rng.uniform(-0.04, 0.04)  # a small piece: centred on the arm band
    fab = _c(rng, S.FABRIC + S.MAT)
    if rule == "dresser":
        top, dep, w = rng.uniform(0.76, 0.92), rng.uniform(0.42, 0.50), rng.uniform(0.85, 1.20)
        y0, y1 = yc - w / 2, yc + w / 2
        b.cabinet("dresser", top, d, d + dep, y0, y1, _c(rng, S.WOOD + S.PAINT))
        b.box("dmirror", d + dep - 0.03, d + dep, yc - 0.30, yc + 0.30, top + 0.05, top + 0.80, _c(rng, S.METAL + S.WOOD), "wall")
        b.nodes[-1]["box"][0][1] = round(d + dep - 0.05, 4)
        return {"dresser": round(top, 3)}
    if rule == "vanity":
        top, dep, w = rng.uniform(0.72, 0.78), rng.uniform(0.42, 0.50), rng.uniform(0.80, 1.10)
        y0, y1 = yc - w / 2, yc + w / 2
        b.table("vdesk", top, d, d + dep, y0, y1, _c(rng, S.WOOD + S.PAINT), thick=0.03, leg=0.04)
        b.box("vmirror", d + dep - 0.03, d + dep, yc - 0.25, yc + 0.25, top + 0.05, top + 0.65, _c(rng, S.METAL), "wall")
        b.nodes[-1]["box"][0][1] = round(d + dep - 0.05, 4)
        return {}
    top, dep, w = rng.uniform(0.48, 0.64), rng.uniform(0.40, 0.48), rng.uniform(0.48, 0.62)
    y0, y1 = yc - w / 2, yc + w / 2
    host = b.cabinet("nstand", top, d, d + dep, y0, y1, _c(rng, S.WOOD + S.PAINT))
    bw = rng.uniform(0.40, 0.60)  # the visible end of a bed beside the stand (decor, dropped past the room zone)
    by0, by1 = (y0 - 0.03 - bw, y0 - 0.03) if b.sgn > 0 else (y1 + 0.03, y1 + 0.03 + bw)
    b.box("bed", d + 0.05, d + 0.85, by0, by1, 0.0, 0.50, fab, "sofa")
    b.box("pillow", d + 0.55, d + 0.80, by0 + 0.05, by1 - 0.05, 0.50, 0.62, _c(rng, S.FABRIC + APPLIANCE), "sofa")
    if rule == "nightstand":
        return {"stand": round(top, 3)}
    if rule == "stand_tray":
        tw = rng.uniform(0.20, 0.26)
        b.open_box("ntray", d + 0.05, d + 0.05 + rng.uniform(0.14, 0.18), yc - tw / 2, yc + tw / 2, top, 0.025,
                   _c(rng, S.WOOD + S.METAL + STONE))
        return {}
    if rule == "lamp":
        ly = yc + b.sgn * (w / 2 - 0.09)
        lx = d + dep - 0.16
        b.box("lamp_base", lx, lx + 0.12, ly - 0.06, ly + 0.06, top, top + 0.30, _c(rng, S.METAL + STONE), "body")
        b.box("lamp_shade", lx - 0.04, lx + 0.16, ly - 0.10, ly + 0.10, top + 0.30, top + 0.48, _c(rng, S.FABRIC + S.MAT), "mat")
        host["box"][0][1] = round(lx - 0.04, 4)
        return {}
    raise ValueError(rule)


# ----------------------------------------------------------------------------------------------- 17 laundry
def _laundry(b, rule, d, yc):
    rng = b.rng
    w = rng.uniform(1.20, 1.60)
    y0, y1 = yc - w / 2, yc + w / 2
    app = _c(rng, APPLIANCE)
    if rule == "washer_top":
        top, dep = rng.uniform(0.85, 0.92), rng.uniform(0.58, 0.65)
        ym = yc + rng.uniform(-0.05, 0.05)
        b.box("washer", d + 0.02, d + dep, y0, ym - 0.005, 0.0, top - 0.03, app, "body")
        b.box("dryer", d + 0.02, d + dep, ym + 0.005, y1, 0.0, top - 0.03, _c(rng, APPLIANCE), "body")
        b.box("wd_top", d, d + dep, y0, y1, top - 0.03, top, _c(rng, S.WOOD + STONE + APPLIANCE), "top", "top")
        b.node("top", "wd_top", top, d, d + dep, y0, y1)
        b.box("panel", d + dep - 0.10, d + dep, y0, y1, top, top + 0.12, app, "body")
        b.nodes[-1]["box"][0][1] = round(d + dep - 0.12, 4)
        return {}
    if rule == "folding_table":
        top = rng.uniform(0.86, 0.96)
        b.table("fold", top, d, d + rng.uniform(0.60, 0.75), y0, y1, _c(rng, APPLIANCE + S.WOOD), thick=0.03, leg=0.04)
        return {}
    if rule == "basket_shelf":
        top, dep = rng.uniform(0.78, 0.92), rng.uniform(0.40, 0.48)
        b.cabinet("lshelf", top, d, d + dep, y0, y1, _c(rng, S.WOOD + S.PAINT))
        bw = rng.uniform(0.30, 0.40)
        by = b.yb + rng.uniform(-0.06, 0.06)
        b.open_box("lbask", d + 0.04, d + 0.04 + rng.uniform(0.26, 0.34), by - bw / 2, by + bw / 2, top,
                   rng.uniform(0.08, 0.12), _c(rng, S.WOOD + S.FABRIC + PLASTIC))
        return {}
    if rule == "utility_sink":
        top, dep = rng.uniform(0.86, 0.94), rng.uniform(0.55, 0.62)
        sw = rng.uniform(0.40, 0.48)
        sy = _far_y(b, yc, w, sw + 0.06)
        b.box("usink_body", d + 0.03, d + dep, sy - sw / 2, sy + sw / 2, 0.0, top - 0.18, app, "body")
        b.open_box("usink", d, d + 0.40, sy - sw / 2, sy + sw / 2, top - 0.18, 0.18, app, kind="container")
        lo, hi = (y0, sy - sw / 2 - 0.01) if b.sgn > 0 else (sy + sw / 2 + 0.01, y1)
        b.cabinet("ucounter", top, d, d + dep, lo, hi, _c(rng, S.WOOD + APPLIANCE))
        return {}
    if rule == "ironing":
        top = rng.uniform(0.82, 0.92)
        dep = rng.uniform(0.36, 0.42)
        b.box("iron_board", d, d + dep, y0, y1, top - 0.02, top, _c(rng, S.FABRIC + S.MAT), "top", "top")
        b.box("iron_leg_a", d + 0.10, d + dep - 0.10, y0 + 0.25, y0 + 0.28, 0.0, top - 0.02, _c(rng, S.METAL), "leg")
        b.box("iron_leg_b", d + 0.10, d + dep - 0.10, y1 - 0.28, y1 - 0.25, 0.0, top - 0.02, _c(rng, S.METAL), "leg")
        b.node("top", "iron_board", top, d, d + dep, y0, y1)
        return {"board": round(dep, 3)}
    raise ValueError(rule)


# ----------------------------------------------------------------------------------------------- 18 kids play
def _kids_play(b, rule, d, yc):
    rng = b.rng
    w, dep = rng.uniform(0.90, 1.30), rng.uniform(0.55, 0.75)
    y0, y1 = yc - w / 2, yc + w / 2
    top = rng.uniform(0.44, 0.56)
    col = _c(rng, PLASTIC + S.WOOD)
    host = b.table("ptable", top, d, d + dep, y0, y1, col, thick=0.035, leg=0.05)
    for i, y in enumerate(np.linspace(y0 + 0.2, y1 - 0.2, 2)):
        cx = d + dep + 0.08
        b.box(f"kchair{i}", cx, cx + 0.30, y - 0.15, y + 0.15, 0.0, 0.30, _c(rng, PLASTIC), "chair")
    if rule == "table":
        return {}
    if rule == "toy_bins":
        for i in range(int(rng.integers(1, 3))):
            bw = rng.uniform(0.22, 0.30)
            by = b.yb + (0.0 if i == 0 else -b.sgn * 0.34) + rng.uniform(-0.03, 0.03)
            b.open_box(f"tbin{i}", d + 0.05, d + 0.05 + rng.uniform(0.20, 0.26), by - bw / 2, by + bw / 2, top,
                       rng.uniform(0.07, 0.11), _c(rng, PLASTIC))
        return {}
    if rule == "cubbies":
        ow = rng.uniform(0.36, 0.48)
        oy = b.yb + rng.uniform(-0.06, 0.06)
        b.open_box("kcub", d + 0.05, d + 0.05 + rng.uniform(0.22, 0.28), oy - ow / 2, oy + ow / 2, top,
                   rng.uniform(0.06, 0.09), _c(rng, PLASTIC), dividers=int(rng.integers(1, 3)))
        return {}
    if rule == "two_tables":
        t2 = top + rng.uniform(0.06, 0.14)
        e = b.yb + rng.uniform(-0.04, 0.04)
        sy = (min(e, e - b.sgn * 0.40), max(e, e - b.sgn * 0.40))
        b.table("ptable2", t2, d + 0.02, d + 0.42, *sy, _c(rng, PLASTIC), thick=0.03, leg=0.04)
        return {}
    if rule == "craft":
        b.zone("zone", host, d + 0.03, d + 0.33, b.yb - 0.20, b.yb + 0.20,
               color=_c(rng, [(0.95, 0.95, 0.92), (0.98, 0.90, 0.60), (0.70, 0.85, 0.95)]))
        return {}
    raise ValueError(rule)


# ----------------------------------------------------------------------------------------------- 19 picnic (outdoor)
def _picnic_outdoor(b, rule, d, yc):
    rng = b.rng
    w = rng.uniform(1.20, 1.80)
    y0, y1 = yc - w / 2, yc + w / 2
    wood = _c(rng, OUTDOOR_WOOD + S.WOOD)
    if rule == "folding":
        top, dep = rng.uniform(0.70, 0.76), rng.uniform(0.55, 0.75)
        b.table("ftable", top, d, d + dep, y0, y1, _c(rng, APPLIANCE + PLASTIC + S.METAL), thick=0.025, leg=0.03)
        return {}
    if rule == "camp_table":
        top, dep = rng.uniform(0.56, 0.68), rng.uniform(0.50, 0.65)
        b.table("ctable", top, d, d + dep, y0, y1, _c(rng, S.METAL + OUTDOOR_WOOD), thick=0.03, leg=0.03)
        return {}
    top, dep = rng.uniform(0.72, 0.78), rng.uniform(0.70, 0.85)
    n = 4
    sw = dep / n
    for i in range(n):  # slat boards with 1 cm gaps: one node over all of them
        b.box(f"slat{i}", d + i * sw, d + (i + 1) * sw - 0.01, y0, y1, top - 0.04, top, wood, "top", "top")
    b.node("top", "slat0", top, d, d + dep - 0.01, y0, y1)
    for i, yy in enumerate((y0 + 0.15, y1 - 0.19)):
        b.box(f"pleg{i}", d + 0.10, d + dep - 0.10, yy, yy + 0.04, 0.0, top - 0.04, wood, "leg")
    b.box("bench_far", d + dep + 0.15, d + dep + 0.45, y0, y1, 0.42, 0.46, wood, "chair")
    if rule == "bench_table":
        return {}
    if rule == "cooler":
        cw = rng.uniform(0.30, 0.40)
        cy = _far_y(b, yc, w, cw)
        b.open_box("cooler", d + 0.10, d + 0.10 + rng.uniform(0.24, 0.30), cy - cw / 2, cy + cw / 2, top,
                   rng.uniform(0.10, 0.12), _c(rng, PLASTIC), kind="container")
        return {}
    if rule == "basket":
        bw = rng.uniform(0.28, 0.36)
        by = b.yb + rng.uniform(-0.06, 0.06)
        b.open_box("pbasket", d + 0.05, d + 0.05 + rng.uniform(0.22, 0.28), by - bw / 2, by + bw / 2, top,
                   rng.uniform(0.08, 0.11), _c(rng, S.WOOD + OUTDOOR_WOOD))
        return {}
    if rule == "cloth":
        b.box("tablecloth", d - 0.02, d + dep + 0.02, y0 - 0.02, y1 + 0.02, top, top + 0.003,
              _c(rng, S.FABRIC + PLASTIC + S.MAT), "mat")
        b.nodes[-1]["top_z"] = round(top + 0.003, 4)
        return {"cloth": True}
    raise ValueError(rule)


# ----------------------------------------------------------------------------------------------- 20 conference
def _conference(b, rule, d, yc):
    rng = b.rng
    w, dep = rng.uniform(1.20, 1.60), rng.uniform(0.75, 0.95)
    y0, y1 = yc - w / 2, yc + w / 2
    top = rng.uniform(0.72, 0.76)
    host = b.table("conf", top, d, d + dep, y0, y1, _c(rng, S.WOOD + STONE + S.PAINT), thick=0.04, leg=0.08)
    for i, y in enumerate(np.linspace(y0 + 0.30, y1 - 0.30, int(rng.integers(2, 4)))):
        cx = d + dep + 0.12
        b.box(f"cchair{i}", cx, cx + 0.48, y - 0.24, y + 0.24, 0.0, 0.47, _c(rng, S.FABRIC + S.METAL), "chair")
        b.box(f"cchair{i}_back", cx + 0.43, cx + 0.48, y - 0.24, y + 0.24, 0.47, 1.00, _c(rng, S.FABRIC + S.METAL), "chair")
    if rule == "long":
        return {}
    if rule == "screen":
        sy = yc + rng.uniform(-0.2, 0.2)  # a display on a foot at the table's far edge
        b.box("disp_foot", d + dep - 0.20, d + dep - 0.04, sy - 0.12, sy + 0.12, top, top + 0.02, _c(rng, S.METAL), "body")
        b.box("display", d + dep - 0.12, d + dep - 0.08, sy - 0.45, sy + 0.45, top + 0.10, top + 0.62, _c(rng, S.METAL),
              "screen")
        host["box"][0][1] = round(d + dep - 0.22, 4)
        return {}
    if rule == "coffee_tray":
        tw = rng.uniform(0.30, 0.40)
        ty = b.yb + rng.uniform(-0.06, 0.06)
        b.open_box("ctray", d + 0.05, d + 0.05 + rng.uniform(0.22, 0.28), ty - tw / 2, ty + tw / 2, top, 0.025,
                   _c(rng, S.WOOD + S.METAL + PLASTIC))
        return {}
    if rule == "cable_box":
        cy = yc + rng.uniform(-0.15, 0.15)
        b.box("cablebox", d + dep * 0.5 - 0.08, d + dep * 0.5 + 0.08, cy - 0.12, cy + 0.12, top, top + 0.03,
              _c(rng, S.METAL), "body")
        return {}
    if rule == "laptops":
        for i in range(int(rng.integers(1, 3))):
            ly = _far_y(b, yc, w, 0.34) - b.sgn * i * 0.40
            lx = d + dep - 0.30
            b.box(f"laptop{i}", lx, lx + 0.24, ly - 0.17, ly + 0.17, top, top + 0.02, _c(rng, S.METAL), "body")
            b.box(f"laptop{i}_lid", lx + 0.22, lx + 0.24, ly - 0.17, ly + 0.17, top + 0.02, top + 0.24, _c(rng, S.METAL),
                  "screen")
        host["box"][0][1] = round(d + dep - 0.32, 4)
        return {}
    raise ValueError(rule)


# ----------------------------------------------------------------------------------------------- 21 reception
def _reception(b, rule, d, yc):
    rng = b.rng
    w = rng.uniform(1.10, 1.60)
    y0, y1 = yc - w / 2, yc + w / 2
    top, dep = rng.uniform(0.72, 0.78), rng.uniform(0.55, 0.66)
    col = _c(rng, S.WOOD + S.PAINT + STONE)
    host = b.cabinet("rdesk", top, d, d + dep, y0, y1, col)
    lt = top + rng.uniform(0.28, 0.36)
    if rule != "l_shape":
        b.box("transaction", d + dep - 0.04, d + dep + 0.20, y0, y1, 0.0, lt, _c(rng, S.WOOD + S.PAINT + STONE), "body")
        host["box"][0][1] = round(d + dep - 0.06, 4)
    if rule == "ledge":
        return {"ledge": round(lt, 3)}
    if rule == "brochure":
        return {"holders": "forced"}
    if rule == "tray":
        tw = rng.uniform(0.24, 0.32)
        ty = b.yb + rng.uniform(-0.06, 0.06)
        b.open_box("intray", d + 0.05, d + 0.05 + rng.uniform(0.20, 0.26), ty - tw / 2, ty + tw / 2, top,
                   rng.uniform(0.04, 0.06), _c(rng, S.METAL + PLASTIC))
        return {}
    if rule == "l_shape":
        t2 = top + rng.uniform(0.04, 0.10)
        e = b.yb + rng.uniform(-0.04, 0.04)
        sy = (min(e, e - b.sgn * 0.50), max(e, e - b.sgn * 0.50))
        b.cabinet("rwing", t2, d + 0.02, d + 0.52, *sy, col)
        return {}
    if rule == "bell":
        by = _far_y(b, yc, w, 0.10)
        b.box("bell", d + 0.08, d + 0.16, by - 0.04, by + 0.04, top, top + 0.06, _c(rng, S.METAL), "body")
        return {}
    raise ValueError(rule)


# ----------------------------------------------------------------------------------------------- 22 garage / tool cart
def _garage_cart(b, rule, d, yc):
    rng = b.rng
    steel = _c(rng, S.METAL + [(0.75, 0.10, 0.10), (0.10, 0.25, 0.55), (0.15, 0.15, 0.16)])
    if rule == "tool_cart":
        w = rng.uniform(0.70, 1.00)
        yc = b.yb + rng.uniform(-0.05, 0.05)
        y0, y1 = yc - w / 2, yc + w / 2
        top, dep = rng.uniform(0.82, 0.95), rng.uniform(0.45, 0.55)
        b.box("cart_body", d + 0.02, d + dep, y0, y1, 0.10, top - 0.05, steel, "body")
        b.box("cart_handle", d + dep, d + dep + 0.04, y0, y1, top + 0.05, top + 0.08, _c(rng, S.METAL), "body")
        b.open_box("cart_top", d, d + dep, y0, y1, top - 0.05, 0.05, steel, kind="container")
        return {"cart": round(top, 3)}
    w = rng.uniform(1.10, 1.70)
    y0, y1 = yc - w / 2, yc + w / 2
    if rule == "shelf_unit":
        top, dep = rng.uniform(0.75, 0.95), rng.uniform(0.40, 0.55)
        up = top + rng.uniform(0.48, 0.60)
        _posts(b, "gsh", d, d + dep, y0, y1, up + 0.03, steel, t=0.035)
        b.box("gsh_low", d, d + dep, y0, y1, 0.30, 0.32, steel, "body")
        b.box("gsh_mid", d, d + dep, y0, y1, top - 0.02, top, steel, "top", "top")
        b.box("gsh_up", d, d + dep, y0, y1, up, up + 0.02, steel, "top", "top")
        b.node("top", "gsh_mid", top, d, d + dep, y0, y1)
        return {}
    top, dep = rng.uniform(0.75, 0.90), rng.uniform(0.55, 0.70)
    b.table("gbench", top, d, d + dep, y0, y1, _c(rng, S.WOOD + S.METAL), thick=0.05, leg=0.06)
    if rule == "workbench_low":
        b.box("gpeg", d + dep - 0.02, d + dep, y0, y1, top, top + 0.70, _c(rng, S.WOOD + S.PAINT), "wall")
        return {}
    if rule == "bucket_bins":
        for i in range(int(rng.integers(1, 3))):
            bw = rng.uniform(0.22, 0.30)
            by = b.yb + (0.0 if i == 0 else -b.sgn * 0.34)
            b.open_box(f"bucket{i}", d + 0.06, d + 0.06 + bw, by - bw / 2, by + bw / 2, top, rng.uniform(0.09, 0.12),
                       _c(rng, PLASTIC))
        return {}
    if rule == "paint_cans":
        x = d + dep - 0.20
        for i in range(int(rng.integers(2, 5))):
            cy = _far_y(b, yc, w, 0.14) - b.sgn * i * 0.17
            b.box(f"can{i}", x, x + 0.14, cy - 0.07, cy + 0.07, top, top + rng.uniform(0.14, 0.20), _c(rng, PLASTIC + S.METAL),
                  "body")
        b.nodes[0]["box"][0][1] = round(x - 0.02, 4)
        return {}
    raise ValueError(rule)


# ----------------------------------------------------------------------------------------------- 23 potting bench (outdoor)
def _potting_bench(b, rule, d, yc):
    rng = b.rng
    w = rng.uniform(1.00, 1.50)
    y0, y1 = yc - w / 2, yc + w / 2
    top, dep = rng.uniform(0.80, 0.90), rng.uniform(0.55, 0.70)
    wood = _c(rng, OUTDOOR_WOOD + S.WOOD)
    host = b.table("pot_bench", top, d, d + dep, y0, y1, wood, thick=0.04, leg=0.06)
    b.box("pot_back", d + dep - 0.02, d + dep, y0, y1, top, top + 0.30, wood, "wall")
    host["box"][0][1] = round(d + dep - 0.03, 4)
    if rule == "plain":
        return {}
    if rule == "soil_tray":
        tw = rng.uniform(0.36, 0.48)
        ty = b.yb + rng.uniform(-0.05, 0.05)
        b.open_box("soil", d + 0.04, d + 0.04 + rng.uniform(0.28, 0.36), ty - tw / 2, ty + tw / 2, top,
                   rng.uniform(0.05, 0.08), _c(rng, PLASTIC + [(0.25, 0.20, 0.15)]))
        return {}
    if rule == "pots":
        for i in range(int(rng.integers(2, 4))):
            pw = rng.uniform(0.14, 0.18)
            py = _far_y(b, yc, w, pw) - b.sgn * i * 0.20
            b.open_box(f"pot{i}", d + dep - 0.25, d + dep - 0.25 + pw, py - pw / 2, py + pw / 2, top, 0.11,
                       _c(rng, [(0.72, 0.38, 0.25), (0.60, 0.32, 0.22), (0.30, 0.30, 0.30)]), kind="container")
        return {}
    if rule == "upper_shelf":
        sz = top + rng.uniform(0.48, 0.56)
        b.box("pot_shelf", d + dep - 0.22, d + dep, y0, y1, sz, sz + 0.025, wood, "top", "top")
        b.box("pot_post_l", d + dep - 0.04, d + dep, y0, y0 + 0.04, top, sz, wood, "leg")
        b.box("pot_post_r", d + dep - 0.04, d + dep, y1 - 0.04, y1, top, sz, wood, "leg")
        return {}
    if rule == "seed_trays":
        ow = rng.uniform(0.36, 0.50)
        oy = b.yb + rng.uniform(-0.06, 0.06)
        b.open_box("seeds", d + 0.04, d + 0.04 + rng.uniform(0.22, 0.30), oy - ow / 2, oy + ow / 2, top,
                   rng.uniform(0.04, 0.06), _c(rng, PLASTIC), dividers=int(rng.integers(1, 4)))
        return {}
    raise ValueError(rule)


# ----------------------------------------------------------------------------------------------- 24 library / study
def _library_study(b, rule, d, yc):
    rng = b.rng
    w, dep = rng.uniform(1.00, 1.50), rng.uniform(0.60, 0.80)
    y0, y1 = yc - w / 2, yc + w / 2
    top = rng.uniform(0.72, 0.78)
    col = _c(rng, S.WOOD)
    host = b.table("study", top, d, d + dep, y0, y1, col, thick=0.035, leg=0.05)
    b.box("bookcase_back", d + dep + 0.35, d + dep + 0.70, y0 - 0.30, y1 + 0.30, 0.0, rng.uniform(1.6, 2.1),
          _c(rng, S.WOOD + S.PAINT), "decor")
    if rule == "reading_table":
        return {}
    if rule == "carrel":
        for i, yy in enumerate((y0, y1 - 0.02)):
            b.box(f"carrel{i}", d + 0.15, d + dep, yy, yy + 0.02, top, top + 0.40, _c(rng, S.WOOD + S.FABRIC), "side")
        b.box("carrel_back", d + dep - 0.02, d + dep, y0, y1, top, top + 0.40, _c(rng, S.WOOD + S.FABRIC), "wall")
        host["box"][1] = [round(y0 + 0.02, 4), round(y1 - 0.02, 4)]
        return {}
    if rule == "stacks":
        x = d + dep - rng.uniform(0.18, 0.24)
        yy, i = y0 + 0.03, 0
        while yy < y1 - 0.15 and i < 4:
            bw = rng.uniform(0.14, 0.24)
            if abs(yy + bw / 2 - b.yb) > 0.16:
                b.box(f"stack{i}", x, x + 0.17, yy, yy + bw, top, top + rng.uniform(0.06, 0.12), _c(rng, S.FABRIC + S.MAT + PLASTIC),
                      "body")
                i += 1
            yy += bw + rng.uniform(0.05, 0.20)
        host["box"][0][1] = round(x - 0.01, 4)
        return {"stacks": i}
    if rule == "lamp_desk":
        ly = _far_y(b, yc, w, 0.14)
        lx = d + dep - 0.18
        b.box("dlamp_base", lx, lx + 0.14, ly - 0.07, ly + 0.07, top, top + 0.03, _c(rng, S.METAL), "body")
        b.box("dlamp_arm", lx + 0.05, lx + 0.08, ly - 0.015, ly + 0.015, top + 0.03, top + 0.42, _c(rng, S.METAL), "body")
        b.box("dlamp_head", lx - 0.10, lx + 0.08, ly - 0.06, ly + 0.06, top + 0.42, top + 0.48, _c(rng, S.METAL + PLASTIC), "body")
        return {}
    if rule == "book_cart":
        ct = top + rng.uniform(0.04, 0.12)
        e = b.yb + rng.uniform(-0.04, 0.04)
        sy = (min(e, e - b.sgn * 0.45), max(e, e - b.sgn * 0.45))
        b.cabinet("bcart", ct, d + 0.02, d + 0.42, *sy, _c(rng, S.WOOD + S.METAL))
        return {"cart": round(ct, 3)}
    raise ValueError(rule)


# ----------------------------------------------------------------------------------------------- 25 mesh furniture
MESH_RULES = ("table", "counter", "shelf", "side_table", "low_table", "seat")
MESH_YAW = -math.pi / 2  # = assets_x.furniture.MESH_YAW: THOR fronts turn to face the robot


def _mesh_furniture(b, rule, d, yc):
    """A licensed mesh piece (MolmoSpaces THOR / Objaverse CC BY rows of furniture_mesh, the L8S mesh kinds) as the
    task furniture: its measured support surfaces become nodes (open -> top, open container -> container with the
    rim, covered -> compartment: front approach). The pool is scene9.mesh_pool() (the process's loaded pieces in a
    world, the whole train catalog otherwise)."""
    from ..sim.assets_x import surfaces as SU
    rng = b.rng
    pool = S.mesh_pool()
    names = sorted(n for n, a in pool.items() if a.get("category") == rule and _open_top(a))
    if not names:
        raise S.NoMesh(f"no mesh piece of category {rule}")
    name = names[int(rng.integers(len(names)))]
    a = pool[name]
    yaw = float(a.get("yaw", MESH_YAW))
    k = round(yaw / (math.pi / 2))
    yaw = k * math.pi / 2
    sx, sy, sz = a["collider_size"]
    dx, dy = (sx, sy) if k % 2 == 0 else (sy, sx)
    base = [d + dx / 2, yc, 0.0]
    b.parts.append({"id": name, "usd": a["dst"], "asset": name, "prim": "mesh", "size": [round(dx, 4), round(dy, 4),
                    round(sz, 4)], "pos": [round(base[0], 4), round(base[1], 4), round(sz / 2, 4)],
                    "base_pos": [round(v, 4) for v in base], "yaw": round(yaw, 6), "static": True, "color": None,
                    "role": "mesh", "surface_kind": a.get("top_kind"), "category": rule, "license": a.get("license"),
                    "source": a.get("source"), "split": a.get("split", "train")})
    n_nodes = 0
    for s in a["surfaces"]:
        t = SU.transform_surface(s, pos=base, yaw=yaw)
        (x0, x1), (y0, y1) = t["xy_box"]
        if x1 - x0 < 0.10 or y1 - y0 < 0.10:
            continue
        if t.get("container"):
            if t.get("covered_above") is not None:
                continue
            b.node("container", name, t["top_z"], x0, x1, y0, y1, rim=t["rim_z"], mesh=name)
        elif t.get("covered_above") is not None:
            b.node("compartment", name, t["top_z"], x0, x1, y0, y1, mesh=name,
                   covered_above=round(float(t["covered_above"]), 4))
        else:
            b.node("top", name, t["top_z"], x0, x1, y0, y1, mesh=name)
        n_nodes += 1
    return {"asset": a.get("name0", name), "category": rule, "yaw": round(yaw, 4), "nodes": n_nodes}


def _open_top(a: dict) -> bool:
    """A mesh piece with an open (not covered, not container) surface of >= 0.25 x 0.25 m at a reachable height."""
    for s in a.get("surfaces") or []:
        (x0, x1), (y0, y1) = s["xy_box"]
        if s.get("covered_above") is None and not s.get("container") and 0.38 <= s["top_z"] <= 1.06 \
                and x1 - x0 >= 0.25 and y1 - y0 >= 0.25:
            return True
    return False


def _floor_crate(b, d, yc):
    """L8S floor_bin: an open crate on a solid base standing on the floor (floor 0.28-0.40 m, the lift down), a rack
    deck behind it."""
    rng = b.rng
    fz, wh, t = rng.uniform(0.28, 0.40), rng.uniform(0.10, 0.16), 0.015
    bx, by = rng.uniform(0.30, 0.38), rng.uniform(0.24, 0.32)
    x0 = max(d, 0.29) + rng.uniform(0.0, 0.02)
    cy = b.yb + rng.uniform(-0.05, 0.05)
    b.box("crate_base", x0, x0 + bx, cy - by / 2, cy + by / 2, 0.0, fz, _c(rng, S.WOOD + OUTDOOR_WOOD), "body")
    b.open_box("fcrate", x0, x0 + bx, cy - by / 2, cy + by / 2, fz, wh, _c(rng, PLASTIC + S.WOOD), t=t)
    rd = x0 + bx + 0.06
    dep = min(rng.uniform(0.45, 0.60), 1.25 - rd)
    top = rng.uniform(0.75, 0.95)
    w = rng.uniform(1.0, 1.5)
    steel = _c(rng, S.METAL)
    _posts(b, "rackb", rd, rd + dep, yc - w / 2, yc + w / 2, top + 0.6, steel, t=0.05)
    b.box("deckb", rd, rd + dep, yc - w / 2 + 0.05, yc + w / 2 - 0.05, top - 0.02, top, _c(rng, S.WOOD + S.METAL), "top", "top")
    b.node("top", "deckb", top, rd, rd + dep, yc - w / 2 + 0.05, yc + w / 2 - 0.05)
    return {"floor": round(fz, 3), "wall": round(wh, 3)}


MORE_FAMILIES = {
    "kitchen_island": (_kitchen_island, ("slab", "board", "bowl", "bar_ledge", "prep_sink")),
    "pantry_shelf": (_pantry_shelf, ("open", "baskets", "jars", "riser", "bins")),
    "bathroom_vanity": (_bathroom_vanity, ("basin", "vessel", "double", "toiletry_tray", "towel_shelf")),
    "cafe_counter": (_cafe_counter, ("pickup", "pastry_case", "condiments", "tray_return", "two_level")),
    "warehouse_rack": (_warehouse_rack, ("beam", "totes", "cartons", "wire_bins", "picking_cart", "floor_crate")),
    "lab_bench": (_lab_bench, ("reagent_shelf", "tube_rack", "lab_sink", "hood", "tray_bins")),
    "craft_workshop": (_craft_workshop, ("trestle", "vise", "tool_wall", "bins_row", "cutting_mat")),
    "bedside": (_bedside, ("nightstand", "dresser", "vanity", "stand_tray", "lamp")),
    "laundry": (_laundry, ("washer_top", "folding_table", "basket_shelf", "utility_sink", "ironing")),
    "kids_play": (_kids_play, ("table", "toy_bins", "cubbies", "two_tables", "craft")),
    "picnic_outdoor": (_picnic_outdoor, ("bench_table", "folding", "camp_table", "cooler", "basket", "cloth")),
    "conference": (_conference, ("long", "screen", "coffee_tray", "cable_box", "laptops")),
    "reception": (_reception, ("ledge", "brochure", "tray", "l_shape", "bell")),
    "garage_cart": (_garage_cart, ("tool_cart", "shelf_unit", "workbench_low", "bucket_bins", "paint_cans")),
    "potting_bench": (_potting_bench, ("plain", "soil_tray", "pots", "upper_shelf", "seed_trays")),
    "library_study": (_library_study, ("reading_table", "carrel", "stacks", "lamp_desk", "book_cart")),
    "mesh_furniture": (_mesh_furniture, MESH_RULES),
}
MORE_ROOM_KINDS = {"kitchen_island": ("kitchen",), "pantry_shelf": ("kitchen", "other"),
                   "bathroom_vanity": ("bathroom", "other"), "cafe_counter": ("other", "kitchen"),
                   "warehouse_rack": ("other",), "lab_bench": ("other",), "craft_workshop": ("other",),
                   "bedside": ("bedroom",), "laundry": ("bathroom", "other"), "kids_play": ("living", "bedroom"),
                   "picnic_outdoor": (), "conference": ("other", "living"), "reception": ("other", "living"),
                   "garage_cart": ("other",), "potting_bench": (), "library_study": ("living", "bedroom", "other"),
                   "mesh_furniture": ("living", "kitchen", "bedroom", "other")}
OUTDOOR = ("picnic_outdoor", "potting_bench")  # no room background: an outdoor HDRI + a ground slab
FORCED_HOLDERS = ("jars", "condiments", "tube_rack", "brochure")
