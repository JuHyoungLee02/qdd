"""L9 scene layer (spec §2): 8 environment families x >= 5 layout rules of parametric furniture (cuboid parts, the
L8-X FX slots) with a support-node graph, a robot pose (distance to the furniture front, yaw +-20 deg) and a lift.
Pure (numpy).

Frames: the furniture is built axis-aligned in the scene frame S (x = towards the furniture's back, y = left); the
world (robot) frame is S turned by `yaw` about the robot base (the robot stands at the origin facing +x), so a robot
yaw of +-20 deg relative to the furniture front = the scene turned by -+20 deg. Nodes carry their S box; the task
layer samples world points in the arm's band and maps them back (s_of) to test node membership.

Node kinds (all reachable from above in stage 1, plan decision 2): top (a free work surface), zone (a marked
sub-area of a top: placemat / mat / tray area), seat (a dining place: plate spot + cutlery side), cubby (an open-top
compartment floor between walls / dividers), slot (a narrow open-top holder), container (an open box / basin
floor). Every node: {id, kind, part, top_z, box [[x0, x1], [y0, y1]] (S), rim_z (walls' top or None)}."""
from __future__ import annotations

import math

import numpy as np

from ..sim.assets_x.furniture import KEEP_OUT, _bounds, part
from ..sim.assets_x.reach import LIFTS, LIFT_DEFAULT
from . import arm as A
from . import reach9 as R9

N_SLOTS = 28
YAW_MAX = math.radians(20.0)
DIST = (0.15, 0.45)
EDGE = 0.03  # object centres stay this far inside a node box
WOOD = [(0.55, 0.45, 0.35), (0.62, 0.50, 0.36), (0.40, 0.30, 0.22), (0.75, 0.72, 0.66), (0.30, 0.30, 0.32),
        (0.85, 0.85, 0.82), (0.20, 0.20, 0.22), (0.66, 0.60, 0.52)]
PAINT = [(0.80, 0.80, 0.78), (0.70, 0.74, 0.78), (0.86, 0.82, 0.74), (0.60, 0.62, 0.60), (0.35, 0.45, 0.55),
         (0.55, 0.30, 0.25), (0.25, 0.35, 0.30), (0.90, 0.88, 0.80)]
METAL = [(0.55, 0.56, 0.58), (0.35, 0.36, 0.38), (0.75, 0.76, 0.78), (0.20, 0.22, 0.25)]
FABRIC = [(0.45, 0.40, 0.55), (0.30, 0.40, 0.55), (0.60, 0.35, 0.30), (0.50, 0.50, 0.45), (0.25, 0.45, 0.35)]
MAT = [(0.85, 0.80, 0.70), (0.35, 0.35, 0.40), (0.70, 0.30, 0.25), (0.25, 0.40, 0.60), (0.90, 0.90, 0.90)]


def _c(rng, pal):
    return tuple(pal[int(rng.integers(len(pal)))])


class _B:
    """Part / node builder in the scene frame."""

    def __init__(self, rng, yb: float = -0.23, sgn: int = 1):
        self.rng, self.parts, self.nodes = rng, [], []
        self.yb, self.sgn = yb, sgn  # the arm band's centre y (secondary surfaces meet the main one there), its side

    def box(self, pid, x0, x1, y0, y1, z0, z1, color, role="body", surface_kind=None):
        p = part(pid, (x0, y0, z0), (x1, y1, z1), color, role, surface_kind)
        self.parts.append(p)
        return p

    def node(self, kind, pid, top, x0, x1, y0, y1, rim=None, **extra):
        n = {"id": f"n{len(self.nodes)}_{kind}", "kind": kind, "part": pid, "top_z": round(float(top), 4),
             "box": [[round(float(x0), 4), round(float(x1), 4)], [round(float(y0), 4), round(float(y1), 4)]],
             "rim_z": None if rim is None else round(float(rim), 4)}
        n.update(extra)
        self.nodes.append(n)
        return n

    def table(self, pid, top, x0, x1, y0, y1, color, thick=0.04, leg=0.05, kind="top"):
        self.box(pid, x0, x1, y0, y1, top - thick, top, color, "top", kind)
        for i, (x, y) in enumerate(((x0, y0), (x0, y1 - leg), (x1 - leg, y0), (x1 - leg, y1 - leg))):
            self.box(f"{pid}_leg{i}", x, x + leg, y, y + leg, 0.0, top - thick, color, "leg")
        return self.node(kind, pid, top, x0, x1, y0, y1)

    def cabinet(self, pid, top, x0, x1, y0, y1, color, thick=0.03):
        """A solid body with a top board (counter / shoe cabinet / drawer unit)."""
        self.box(pid + "_body", x0 + 0.01, x1, y0, y1, 0.0, top - thick, color, "body")
        self.box(pid, x0, x1, y0, y1, top - thick, top, _c(self.rng, WOOD + PAINT), "top", "top")
        return self.node("top", pid, top, x0, x1, y0, y1)

    def open_box(self, pid, x0, x1, y0, y1, z0, wall_h, color, t=0.012, kind="container", dividers=0, axis="y"):
        """Floor + 4 walls standing on z0 (bin / basin / crate / organiser); dividers split it into cubbies."""
        self.box(pid + "_floor", x0, x1, y0, y1, z0, z0 + t, color, "bin_floor", "bin_floor")
        top = z0 + t
        rim = z0 + wall_h
        self.box(pid + "_w0", x0, x1, y0, y0 + t, z0, rim, color, "bin_wall")
        self.box(pid + "_w1", x0, x1, y1 - t, y1, z0, rim, color, "bin_wall")
        self.box(pid + "_w2", x0, x0 + t, y0 + t, y1 - t, z0, rim, color, "bin_wall")
        self.box(pid + "_w3", x1 - t, x1, y0 + t, y1 - t, z0, rim, color, "bin_wall")
        if dividers <= 0:
            return [self.node(kind, pid + "_floor", top, x0 + t, x1 - t, y0 + t, y1 - t, rim)]
        out = []
        if axis == "y":
            edges = np.linspace(y0 + t, y1 - t, dividers + 2)
            for i, e in enumerate(edges[1:-1]):
                self.box(f"{pid}_d{i}", x0 + t, x1 - t, e - t / 2, e + t / 2, z0, rim, color, "bin_wall")
            for a, b in zip(edges[:-1], edges[1:]):
                out.append(self.node("cubby", pid + "_floor", top, x0 + t, x1 - t, a + t / 2, b - t / 2, rim))
        else:
            edges = np.linspace(x0 + t, x1 - t, dividers + 2)
            for i, e in enumerate(edges[1:-1]):
                self.box(f"{pid}_d{i}", e - t / 2, e + t / 2, y0 + t, y1 - t, z0, rim, color, "bin_wall")
            for a, b in zip(edges[:-1], edges[1:]):
                out.append(self.node("cubby", pid + "_floor", top, a + t / 2, b - t / 2, y0 + t, y1 - t, rim))
        return out

    def zone(self, kind, host, x0, x1, y0, y1, color=None, pad=0.004, **extra):
        """A marked area on a host node (a thin mat part when coloured)."""
        top = host["top_z"]
        if color is not None:
            self.box(f"{host['part']}_{kind}{len(self.nodes)}", x0, x1, y0, y1, top, top + pad, color, "mat", kind)
            top += pad
        return self.node(kind, host["part"], top, x0, x1, y0, y1, host=host["id"], **extra)

    def backwall(self, x, y0, y1, color, h=2.2):
        """A plain wall behind the furniture: used only when no room background is placed (world9 drops it)."""
        self.box("wall_back", x, x + 0.05, y0, y1, 0.0, h, color, "room_wall")


def _yc(rng, arm):
    """Furniture centre y: in front of the robot, shifted towards the working arm."""
    return A.side(arm) * -float(rng.uniform(0.05, 0.20))


HOLDER_RULES = ("pen_holder", "utensil_zone", "organiser_top", "shoe_cabinet", "narrow_table", "case_top",
                "pegboard", "centrepiece", "rack", "plain")  # rules that always get holders (others: 60 %)


def add_holders(b: _B, rule: str) -> int:
    """Small open-top holders (pen / utensil / cup holders: inner 8-10 cm, walls 3-4.5 cm so the released fingers
    stay above the rim) on the flat top nodes near the arm band; node kind "slot". -> number added (<= 2, parts
    <= 28)."""
    rng = b.rng
    hosts = [n for n in b.nodes if n["kind"] == "top" and n["rim_z"] is None]
    if not hosts or (rule not in HOLDER_RULES and rng.random() >= 0.6):
        return 0
    n = int(rng.integers(1, 3))
    added = 0
    for i in range(n):
        if len(b.parts) + 5 > N_SLOTS:
            break
        host = hosts[int(rng.integers(len(hosts)))]
        (x0, x1), (y0, y1) = host["box"]
        w, dd, hgt, t = rng.uniform(0.08, 0.10), rng.uniform(0.08, 0.10), rng.uniform(0.030, 0.045), 0.008
        cx = float(np.clip(rng.uniform(0.38, 0.56), x0 + dd / 2 + 0.02, x1 - dd / 2 - 0.02))
        cy = float(np.clip(b.yb + rng.uniform(-0.12, 0.12), y0 + w / 2 + 0.02, y1 - w / 2 - 0.02))
        if not (x0 + dd / 2 <= cx <= x1 - dd / 2 and y0 + w / 2 <= cy <= y1 - w / 2):
            continue
        if any(abs(cx - (m["box"][0][0] + m["box"][0][1]) / 2) < 0.12
               and abs(cy - (m["box"][1][0] + m["box"][1][1]) / 2) < 0.12 for m in b.nodes if m["kind"] == "slot"):
            continue
        b.open_box(f"holder{i}", cx - dd / 2, cx + dd / 2, cy - w / 2, cy + w / 2, host["top_z"], hgt,
                   _c(rng, PAINT + METAL + WOOD), t=t, kind="slot")
        added += 1
    return added


# ----------------------------------------------------------------------------------------------- families
def _shelf_front(b: _B, rule: str, d: float, yc: float):
    rng = b.rng
    w = rng.uniform(0.80, 1.20)
    y0, y1 = yc - w / 2, yc + w / 2
    col = _c(rng, WOOD)
    if rule in ("stepped2", "stepped3"):
        n = 2 if rule == "stepped2" else 3
        h0 = rng.uniform(0.70, 0.82)
        rise, depth = rng.uniform(0.08, 0.14), rng.uniform(0.16, 0.22)
        x = d
        for i in range(n):
            top = h0 + i * rise
            b.box(f"step{i}", x, x + depth, y0, y1, 0.0, top, col if i % 2 == 0 else _c(rng, WOOD), "top", "top")
            b.node("top", f"step{i}", top, x, x + depth, y0, y1, tier=i)
            x += depth
        b.backwall(x + rng.uniform(0.05, 0.30), y0 - 0.6, y1 + 0.6, _c(rng, PAINT))
        return {"tiers": n, "rise": round(rise, 3)}
    if rule == "organiser_top":
        top = rng.uniform(0.72, 0.88)
        depth = rng.uniform(0.35, 0.45)
        host = b.cabinet("shelf", top, d, d + depth, y0, y1, col)
        k = int(rng.integers(2, 5))
        ox0, ox1 = d + 0.06, d + depth - 0.06
        oy1 = yc + A.side("right") * 0.0 + rng.uniform(-0.05, 0.05)
        ow = rng.uniform(0.28, 0.42)
        b.open_box("org", ox0, ox1, oy1 - ow / 2, oy1 + ow / 2, top, rng.uniform(0.05, 0.08), _c(rng, PAINT + WOOD),
                   dividers=k - 1)
        return {"cubbies": k, "host": host["id"]}
    if rule == "bookcase_top":
        top = rng.uniform(0.86, 1.02)
        depth = rng.uniform(0.30, 0.38)
        b.cabinet("bookcase", top, d, d + depth, y0, y1, col)
        # books along the back as blocks (obstacles, not nodes)
        x = d + depth - rng.uniform(0.10, 0.14)
        yy = y0 + 0.02
        i = 0
        while yy < y1 - 0.10 and i < 5:
            bw = rng.uniform(0.08, 0.20)
            b.box(f"books{i}", x, d + depth - 0.01, yy, yy + bw, top, top + rng.uniform(0.15, 0.25), _c(rng, FABRIC + MAT))
            yy += bw + rng.uniform(0.10, 0.30)
            i += 1
        b.node("top", "bookcase", top, d, x - 0.01, y0, y1)
        return {"books": i}
    if rule == "wide_split":
        top = rng.uniform(0.74, 0.92)
        depth = rng.uniform(0.40, 0.55)
        b.cabinet("lowshelf", top, d, d + depth, y0 - 0.2, y1 + 0.2, col)
        ym = yc + rng.uniform(-0.05, 0.05)
        b.box("divider", d + 0.05, d + depth - 0.02, ym - 0.01, ym + 0.01, top, top + rng.uniform(0.04, 0.07), col)
        b.nodes[-1:] = []
        b.node("zone", "lowshelf", top, d, d + depth, y0 - 0.2, ym - 0.01, side="a")
        b.node("zone", "lowshelf", top, d, d + depth, ym + 0.01, y1 + 0.2, side="b")
        return {"split": round(ym, 3)}
    raise ValueError(rule)


def _dining(b: _B, rule: str, d: float, yc: float):
    rng = b.rng
    top = rng.uniform(0.72, 0.80)
    depth = rng.uniform(0.70, 1.00)
    w = rng.uniform(1.00, 1.60)
    y0, y1 = yc - w / 2, yc + w / 2
    host = b.table("dtable", top, d, d + depth, y0, y1, _c(rng, WOOD))
    seats = {"seats2": 2, "seats4": 4, "set_row": 3}.get(rule, 1)
    if rule in ("seats2", "seats4", "set_row"):
        mw = rng.uniform(0.28, 0.36)
        ys = np.linspace(y0 + mw / 2 + 0.05, y1 - mw / 2 - 0.05, seats)
        mc = _c(rng, MAT + FABRIC)
        for i, y in enumerate(ys):
            b.zone("seat", host, d + 0.02, d + 0.02 + rng.uniform(0.26, 0.32), y - mw / 2, y + mw / 2,
                   color=mc if rule != "seats2" else None, seat=i)
        for i, y in enumerate(ys[: min(3, seats)]):  # chairs behind the table (visual, far side)
            cx = d + depth + 0.10
            b.box(f"chair{i}", cx, cx + 0.42, y - 0.21, y + 0.21, 0.0, 0.45, _c(rng, WOOD), "chair")
            b.box(f"chair{i}_back", cx + 0.38, cx + 0.42, y - 0.21, y + 0.21, 0.45, 0.90, _c(rng, WOOD), "chair")
        return {"seats": seats}
    if rule == "centrepiece":
        cw = rng.uniform(0.15, 0.25)
        cx = d + depth * rng.uniform(0.45, 0.6)
        b.box("runner", d + 0.05, d + depth - 0.05, yc - cw / 2, yc + cw / 2, top, top + 0.004, _c(rng, FABRIC), "mat")
        b.zone("zone", host, d + 0.03, cx - 0.10, y0 + 0.05, y1 - 0.05)
        return {"runner": round(cw, 3)}
    if rule == "buffet":
        bt = top + rng.uniform(0.08, 0.18)
        e = b.yb + rng.uniform(-0.04, 0.04)
        by = (min(e, e - b.sgn * 0.45), max(e, e - b.sgn * 0.45))
        b.cabinet("buffet", bt, d + 0.03, d + 0.45, *by, _c(rng, WOOD))
        return {"buffet_top": round(bt, 3)}
    raise ValueError(rule)


def _living_low(b: _B, rule: str, d: float, yc: float):
    rng = b.rng
    top = rng.uniform(0.40, 0.56)
    depth, w = rng.uniform(0.45, 0.70), rng.uniform(0.80, 1.20)
    y0, y1 = yc - w / 2, yc + w / 2
    host = b.table("coffee", top, d, d + depth, y0, y1, _c(rng, WOOD), thick=0.05)
    sofa_x = d + depth + rng.uniform(0.35, 0.60)
    fab = _c(rng, FABRIC)
    b.box("sofa_seat", sofa_x, sofa_x + 0.80, yc - 1.0, yc + 1.0, 0.0, 0.42, fab, "sofa")
    b.box("sofa_back", sofa_x + 0.60, sofa_x + 0.80, yc - 1.0, yc + 1.0, 0.42, 0.85, fab, "sofa")
    if rule == "plain":
        return {}
    if rule == "tray":
        tw, tdp = rng.uniform(0.25, 0.40), rng.uniform(0.20, 0.30)
        tx, ty = d + rng.uniform(0.05, depth - tdp - 0.05), yc + rng.uniform(-0.15, 0.15)
        b.open_box("tray", tx, tx + tdp, ty - tw / 2, ty + tw / 2, top, 0.03, _c(rng, WOOD + METAL), kind="container")
        return {"tray": [round(tw, 3), round(tdp, 3)]}
    if rule == "side_table":
        st = top + rng.uniform(0.12, 0.25)
        e = b.yb + rng.uniform(-0.04, 0.04)
        sy = (min(e, e - b.sgn * 0.40), max(e, e - b.sgn * 0.40))
        b.table("side", st, d + 0.02, d + 0.42, *sy, _c(rng, WOOD), thick=0.03, leg=0.04)
        return {"side_top": round(st, 3)}
    if rule == "two_tables":
        t2 = top + rng.choice([-1, 1]) * rng.uniform(0.05, 0.12)
        e = b.yb + rng.uniform(-0.04, 0.04)
        sy = (min(e, e - b.sgn * 0.42), max(e, e - b.sgn * 0.42))
        b.table("coffee2", t2, d + 0.02, d + 0.40, *sy, _c(rng, WOOD), thick=0.04)
        return {"second": round(t2, 3)}
    if rule == "shelf_behind":
        st = top + rng.uniform(0.20, 0.35)
        sx = max(d + 0.22, 0.46)  # the stand's front half inside the band's x range
        b.cabinet("tvstand", st, sx, sx + 0.35, y0, y1, _c(rng, WOOD + PAINT))
        host["box"][0][1] = round(sx - 0.01, 4)
        return {"stand": round(st, 3)}
    raise ValueError(rule)


def _kitchen(b: _B, rule: str, d: float, yc: float):
    rng = b.rng
    top = rng.uniform(0.86, 0.96)
    depth, w = rng.uniform(0.55, 0.65), rng.uniform(1.2, 1.7)
    y0, y1 = yc - w / 2, yc + w / 2
    b.box("counter_body", d + 0.12, d + depth, y0, y1, 0.0, top - 0.04, _c(rng, WOOD + PAINT), "body")
    back = d + depth
    b.box("backsplash", back - 0.02, back, y0, y1, top, top + rng.uniform(0.35, 0.55), _c(rng, PAINT), "wall")
    ctop = _c(rng, PAINT + METAL + WOOD)
    if rule == "sink":
        sw, sd = rng.uniform(0.35, 0.50), rng.uniform(0.30, 0.38)
        sy = yc + rng.uniform(-0.10, 0.10)
        sx0 = d + 0.08
        # counter top in three pieces around the basin opening
        b.box("counter_a", d, back, y0, sy - sw / 2, top - 0.04, top, ctop, "top", "top")
        b.box("counter_b", d, back, sy + sw / 2, y1, top - 0.04, top, ctop, "top", "top")
        b.box("counter_c", d, sx0, sy - sw / 2, sy + sw / 2, top - 0.04, top, ctop, "top", "top")
        b.box("counter_d", sx0 + sd, back, sy - sw / 2, sy + sw / 2, top - 0.04, top, ctop, "top", "top")
        b.node("top", "counter_a", top, d, back - 0.02, y0, sy - sw / 2)
        b.node("top", "counter_b", top, d, back - 0.02, sy + sw / 2, y1)
        depth_b = rng.uniform(0.10, 0.16)
        b.open_box("sink", sx0, sx0 + sd, sy - sw / 2, sy + sw / 2, top - depth_b, depth_b, _c(rng, METAL),
                   kind="container")
        return {"sink": [round(sw, 3), round(sd, 3), round(depth_b, 3)]}
    b.box("counter", d, back, y0, y1, top - 0.04, top, ctop, "top", "top")
    host = b.node("top", "counter", top, d, back - 0.02, y0, y1)
    if rule == "rack":
        rw, rd = rng.uniform(0.30, 0.45), rng.uniform(0.20, 0.28)
        rx, ry = d + rng.uniform(0.05, 0.20), yc + rng.uniform(-0.25, 0.25)
        b.open_box("rack", rx, rx + rd, ry - rw / 2, ry + rw / 2, top, rng.uniform(0.06, 0.10), _c(rng, METAL + PAINT),
                   dividers=int(rng.integers(2, 5)), axis="y")
        for n in b.nodes:
            if n["kind"] == "cubby" and n["part"] == "rack_floor":
                n["kind"] = "slot"
        return {"rack": [round(rw, 3), round(rd, 3)]}
    if rule == "utensil_zone":
        b.zone("zone", host, d + 0.02, d + 0.30, yc - 0.20, yc + 0.20, color=_c(rng, MAT))
        return {}
    if rule == "wall_cabinet":
        cz = top + rng.uniform(0.45, 0.55)
        b.box("wall_cabinet", back - 0.30, back - 0.02, y0, y1, cz, cz + 0.6, _c(rng, WOOD + PAINT), "cabinet")
        return {"cabinet_bottom": round(cz, 3)}
    if rule == "island":
        for i, y in enumerate(np.linspace(y0 + 0.3, y1 - 0.3, 3)):
            sx = back + 0.25
            b.box(f"stool{i}", sx, sx + 0.35, y - 0.17, y + 0.17, 0.0, 0.65, _c(rng, METAL + WOOD), "chair")
        return {"stools": 3}
    raise ValueError(rule)


def _entrance(b: _B, rule: str, d: float, yc: float):
    rng = b.rng
    w = rng.uniform(0.80, 1.30)
    y0, y1 = yc - w / 2, yc + w / 2
    wall = _c(rng, PAINT)
    if rule == "shoe_cabinet":
        top = rng.uniform(0.80, 1.00)
        dep = rng.uniform(0.32, 0.40)
        host = b.cabinet("shoecab", top, d, d + dep, y0, y1, _c(rng, WOOD + PAINT))
        tw = rng.uniform(0.18, 0.28)
        ty = yc + rng.uniform(-0.2, 0.2)
        b.open_box("keytray", d + 0.06, d + 0.06 + rng.uniform(0.14, 0.2), ty - tw / 2, ty + tw / 2, top, 0.025,
                   _c(rng, WOOD + METAL))
        b.backwall(d + dep + 0.02, y0 - 0.8, y1 + 0.8, wall)
        return {}
    if rule == "console_stand":
        top = rng.uniform(0.78, 0.92)
        b.table("console", top, d, d + rng.uniform(0.28, 0.38), y0, y1, _c(rng, WOOD), thick=0.03, leg=0.04)
        sw = rng.uniform(0.18, 0.24)
        sy = b.yb + rng.uniform(-0.05, 0.05)
        rim = rng.uniform(0.52, 0.66)
        fz = rim - rng.uniform(0.10, 0.14)  # sand-filled stand: the floor well above the ground
        b.box("stand_base", d + 0.36, d + 0.36 + sw, sy - sw / 2, sy + sw / 2, 0.0, fz - 0.012, _c(rng, METAL + PAINT))
        b.open_box("umbrella_stand", d + 0.36, d + 0.36 + sw, sy - sw / 2, sy + sw / 2, fz - 0.012, rim - fz + 0.012,
                   _c(rng, METAL + PAINT), kind="slot")
        b.backwall(d + 0.45, y0 - 0.8, y1 + 0.8, wall)
        return {}
    if rule == "bench_hooks":
        top = rng.uniform(0.44, 0.52)
        b.cabinet("bench", top, d, d + rng.uniform(0.35, 0.45), y0, y1, _c(rng, WOOD))
        b.box("hook_board", d + 0.50, d + 0.53, y0, y1, 1.2, 1.5, _c(rng, WOOD), "wall")
        b.backwall(d + 0.55, y0 - 0.8, y1 + 0.8, wall)
        return {}
    if rule == "narrow_table":
        top = rng.uniform(0.80, 0.95)
        b.table("hall", top, d, d + rng.uniform(0.22, 0.30), y0, y1, _c(rng, WOOD), thick=0.03, leg=0.035)
        b.backwall(d + 0.32, y0 - 0.8, y1 + 0.8, wall)
        b.box("mirror", d + 0.30, d + 0.32, yc - 0.3, yc + 0.3, top + 0.25, top + 0.95, _c(rng, METAL), "wall")
        return {}
    if rule == "cabinet_basket":
        top = rng.uniform(0.75, 0.90)
        dep = rng.uniform(0.35, 0.45)
        b.cabinet("cab", top, d, d + dep, y0, y1, _c(rng, WOOD + PAINT))
        bw = rng.uniform(0.22, 0.32)
        by = yc + rng.uniform(-0.2, 0.2)
        b.open_box("basket", d + 0.05, d + 0.05 + rng.uniform(0.20, 0.28), by - bw / 2, by + bw / 2, top,
                   rng.uniform(0.07, 0.11), _c(rng, WOOD + FABRIC))
        b.backwall(d + dep + 0.03, y0 - 0.8, y1 + 0.8, wall)
        return {}
    raise ValueError(rule)


def _office(b: _B, rule: str, d: float, yc: float):
    rng = b.rng
    top = rng.uniform(0.72, 0.78)
    dep, w = rng.uniform(0.60, 0.80), rng.uniform(1.10, 1.60)
    y0, y1 = yc - w / 2, yc + w / 2
    col = _c(rng, WOOD + PAINT)
    host = b.table("desk", top, d, d + dep, y0, y1, col, thick=0.03)
    mx = d + dep - rng.uniform(0.12, 0.20)
    my = yc + rng.uniform(-0.25, 0.25)
    b.box("monitor_foot", mx, mx + 0.10, my - 0.08, my + 0.08, top, top + 0.02, _c(rng, METAL))
    b.box("monitor", mx + 0.06, mx + 0.09, my - 0.30, my + 0.30, top + 0.12, top + 0.48, _c(rng, METAL), "screen")
    if rule == "pen_holder":
        return {}
    if rule == "l_desk":
        t2 = top + rng.choice([-1, 1]) * rng.uniform(0.04, 0.10)
        e = b.yb + rng.uniform(-0.04, 0.04)
        sy = (min(e, e - b.sgn * 0.55), max(e, e - b.sgn * 0.55))
        b.table("desk2", t2, d, d + 0.55, *sy, col, thick=0.03)
        return {}
    if rule == "file_tray":
        fw, fd = rng.uniform(0.24, 0.32), rng.uniform(0.30, 0.36)
        fy = yc + rng.uniform(-0.3, 0.3)
        b.open_box("filetray", d + 0.05, d + 0.05 + fd, fy - fw / 2, fy + fw / 2, top, rng.uniform(0.05, 0.07),
                   _c(rng, METAL + PAINT))
        return {}
    if rule == "drawer_unit":
        t2 = top + rng.uniform(0.08, 0.16)
        e = b.yb + rng.uniform(-0.04, 0.04)
        sy = (min(e, e - b.sgn * 0.42), max(e, e - b.sgn * 0.42))
        b.cabinet("pedestal", t2, d + 0.02, d + 0.50, *sy, _c(rng, METAL + PAINT))
        return {}
    if rule == "hutch":
        ht = top + rng.uniform(0.14, 0.24)
        hx = max(d + 0.20, 0.47)
        b.box("hutch_l", hx, d + dep, y0, y0 + 0.02, top, ht, col, "side")
        b.box("hutch_r", hx, d + dep, y1 - 0.02, y1, top, ht, col, "side")
        b.box("hutch_top", hx, d + dep, y0, y1, ht - 0.02, ht, col, "top", "top")
        b.node("top", "hutch_top", ht, hx, d + dep, y0, y1)
        # the desk area under the hutch is covered: keep the desk node to the front band
        host["box"][0][1] = round(hx - 0.02, 4)
        return {}
    raise ValueError(rule)


def _store(b: _B, rule: str, d: float, yc: float):
    rng = b.rng
    w = rng.uniform(1.00, 1.60)
    y0, y1 = yc - w / 2, yc + w / 2
    if rule == "stepped_display":
        h0, rise, dep = rng.uniform(0.72, 0.82), rng.uniform(0.08, 0.14), rng.uniform(0.15, 0.20)
        x = d
        for i in range(3):
            b.box(f"disp{i}", x, x + dep, y0, y1, 0.0, h0 + i * rise, _c(rng, WOOD + PAINT), "top", "top")
            b.node("top", f"disp{i}", h0 + i * rise, x, x + dep, y0, y1, tier=i)
            x += dep
        return {}
    if rule == "gondola_baskets":
        top = rng.uniform(0.82, 0.95)
        b.cabinet("gondola", top, d, d + rng.uniform(0.40, 0.50), y0, y1, _c(rng, METAL + PAINT))
        n = int(rng.integers(2, 4))
        bw = (w - 0.1) / n
        for i in range(n):
            yy = y0 + 0.05 + i * bw
            b.open_box(f"bask{i}", d + 0.04, d + 0.04 + rng.uniform(0.22, 0.30), yy + 0.01, yy + bw - 0.01, top,
                       rng.uniform(0.06, 0.10), _c(rng, METAL + WOOD + FABRIC))
        return {"baskets": n}
    if rule == "checkout":
        top = rng.uniform(0.88, 0.98)
        b.cabinet("checkout", top, d, d + rng.uniform(0.50, 0.60), y0, y1, _c(rng, PAINT + METAL))
        b.box("register", d + 0.35, d + 0.50, yc - 0.15, yc + 0.15, top, top + 0.12, _c(rng, METAL))
        return {}
    if rule == "crate_table":
        top = rng.uniform(0.74, 0.86)
        b.table("disptable", top, d, d + rng.uniform(0.60, 0.80), y0, y1, _c(rng, WOOD))
        cw = rng.uniform(0.28, 0.36)
        cy = yc + rng.uniform(-0.25, 0.25)
        b.open_box("crate", d + 0.05, d + 0.05 + rng.uniform(0.24, 0.32), cy - cw / 2, cy + cw / 2, top,
                   rng.uniform(0.08, 0.12), _c(rng, WOOD))
        return {}
    if rule == "case_top":
        top = rng.uniform(0.90, 1.00)
        dep = rng.uniform(0.45, 0.55)
        b.cabinet("case", top, d, d + dep, y0, y1, _c(rng, METAL + PAINT))
        for i in range(int(rng.integers(1, 3))):
            sx, sy = d + dep - 0.12, y0 + 0.15 + i * 0.4
            b.box(f"stand{i}", sx, sx + 0.10, sy, sy + 0.10, top, top + rng.uniform(0.10, 0.18), _c(rng, PAINT))
        return {}
    raise ValueError(rule)


def _workbench(b: _B, rule: str, d: float, yc: float):
    rng = b.rng
    w = rng.uniform(1.00, 1.50)
    y0, y1 = yc - w / 2, yc + w / 2
    top = rng.uniform(0.85, 0.95)
    dep = rng.uniform(0.60, 0.75)
    if rule == "two_height":
        ym = b.yb + rng.uniform(-0.04, 0.04)
        t2 = top + rng.choice([-1, 1]) * rng.uniform(0.06, 0.14)
        b.table("bench_a", top, d, d + dep, y0, ym, _c(rng, WOOD + METAL), thick=0.05, leg=0.06)
        b.table("bench_b", t2, d, d + dep, ym, y1, _c(rng, WOOD + METAL), thick=0.05, leg=0.06)
        return {"tops": [round(top, 3), round(t2, 3)]}
    b.table("bench", top, d, d + dep, y0, y1, _c(rng, WOOD + METAL), thick=0.05, leg=0.06)
    if rule == "crates":
        for i in range(int(rng.integers(1, 3))):
            cw = rng.uniform(0.26, 0.34)
            cy = y0 + 0.25 + i * (w - 0.5) / 1.5
            b.open_box(f"crate{i}", d + 0.06, d + 0.06 + rng.uniform(0.22, 0.30), cy - cw / 2, cy + cw / 2, top,
                       rng.uniform(0.08, 0.12), _c(rng, WOOD + PAINT))
        return {}
    if rule == "pegboard":
        b.box("pegboard", d + dep - 0.02, d + dep, y0, y1, top, top + 0.8, _c(rng, WOOD + PAINT), "wall")
        bw = rng.uniform(0.20, 0.28)
        b.open_box("bin", d + 0.08, d + 0.08 + rng.uniform(0.18, 0.24), yc - bw / 2, yc + bw / 2, top, 0.08,
                   _c(rng, PAINT))
        return {}
    if rule == "organiser":
        ow = rng.uniform(0.30, 0.44)
        oy = yc + rng.uniform(-0.2, 0.2)
        b.open_box("parts", d + 0.06, d + 0.06 + rng.uniform(0.18, 0.26), oy - ow / 2, oy + ow / 2, top,
                   rng.uniform(0.04, 0.07), _c(rng, PAINT + METAL), dividers=int(rng.integers(1, 4)))
        return {}
    if rule == "tote_stack":
        tw = rng.uniform(0.28, 0.36)
        ty = b.yb - b.sgn * (tw / 2 + rng.uniform(0.0, 0.04))
        tz = top + rng.uniform(-0.20, -0.08)
        b.parts = [p for p in b.parts if p["id"] != "bench"]  # the bench top stops at the tote
        e = ty + b.sgn * tw / 2
        by = (min(y0, e), max(y0, e)) if b.sgn < 0 else (min(e, y1), max(e, y1))
        b.parts.insert(0, part("bench", (d, by[0], top - 0.05), (d + dep, by[1], top), _c(rng, WOOD + METAL), "top", "top"))
        b.nodes[0]["box"][1] = [round(by[0], 4), round(by[1], 4)]
        b.box("tote_base", d + 0.05, d + 0.05 + 0.30, ty - tw / 2, ty + tw / 2, 0.0, tz, _c(rng, METAL + PAINT))
        b.open_box("tote", d + 0.05, d + 0.05 + 0.30, ty - tw / 2, ty + tw / 2, tz, rng.uniform(0.08, 0.12),
                   _c(rng, PAINT))
        return {}
    raise ValueError(rule)


FAMILIES = {
    "shelf_front": (_shelf_front, ("stepped2", "stepped3", "organiser_top", "bookcase_top", "wide_split")),
    "dining": (_dining, ("seats2", "seats4", "set_row", "centrepiece", "buffet")),
    "living_low": (_living_low, ("plain", "tray", "side_table", "two_tables", "shelf_behind")),
    "kitchen": (_kitchen, ("sink", "rack", "utensil_zone", "wall_cabinet", "island")),
    "entrance": (_entrance, ("shoe_cabinet", "console_stand", "bench_hooks", "narrow_table", "cabinet_basket")),
    "office": (_office, ("pen_holder", "l_desk", "file_tray", "drawer_unit", "hutch")),
    "store": (_store, ("stepped_display", "gondola_baskets", "checkout", "crate_table", "case_top")),
    "workbench": (_workbench, ("two_height", "crates", "pegboard", "organiser", "tote_stack")),
}
FAMILY_NAMES = tuple(FAMILIES)
FAMILY_CODE = {f: i + 1 for i, f in enumerate(FAMILY_NAMES)}
ROOM_KINDS = {"shelf_front": ("living", "bedroom", "other"), "dining": ("kitchen", "living", "other"),
              "living_low": ("living", "bedroom"), "kitchen": ("kitchen",), "entrance": ("other", "living"),
              "office": ("bedroom", "other", "living"), "store": ("other", "kitchen"), "workbench": ("other",)}


# ----------------------------------------------------------------------------------------------- frames
def rot(yaw: float):
    c, s = math.cos(yaw), math.sin(yaw)
    return np.array([[c, -s], [s, c]])


def world_of(xy, yaw: float) -> np.ndarray:
    return rot(yaw) @ np.asarray(xy, float)[:2]


def s_of(xy, yaw: float) -> np.ndarray:
    return rot(-yaw) @ np.asarray(xy, float)[:2]


def to_world_part(p: dict, yaw: float) -> dict:
    q = dict(p)
    c = world_of(p["pos"][:2], yaw)
    q["pos"] = [round(float(c[0]), 4), round(float(c[1]), 4), p["pos"][2]]
    q["yaw"] = round(float(p.get("yaw", 0.0) + yaw), 6)
    return q


def world_corners(p: dict, yaw: float) -> np.ndarray:
    lo, hi = _bounds(p)
    pts = np.array([[lo[0], lo[1]], [lo[0], hi[1]], [hi[0], lo[1]], [hi[0], hi[1]]])
    return (rot(yaw) @ pts.T).T


def keep_out_hits(parts, yaw: float) -> list:
    (a0, a1), (b0, b1), (c0, c1) = KEEP_OUT
    bad = []
    for p in parts:
        lo, hi = _bounds(p)
        if hi[2] <= c0 or lo[2] >= c1:
            continue
        W = world_corners(p, yaw)
        # separating-axis test of the rotated box footprint against the keep-out rectangle
        if W[:, 0].max() <= a0 or W[:, 0].min() >= a1 or W[:, 1].max() <= b0 or W[:, 1].min() >= b1:
            continue
        box = np.array([[a0, b0], [a0, b1], [a1, b0], [a1, b1]])
        Bs = (rot(-yaw) @ box.T).T
        if Bs[:, 0].max() <= lo[0] or Bs[:, 0].min() >= hi[0] or Bs[:, 1].max() <= lo[1] or Bs[:, 1].min() >= hi[1]:
            continue
        bad.append(p["id"])
    return bad


def aabb_world(parts, yaw: float):
    """World xy AABBs of the parts (room zone check)."""
    out = []
    for p in parts:
        W = world_corners(p, yaw)
        out.append(((float(W[:, 0].min()), float(W[:, 0].max())), (float(W[:, 1].min()), float(W[:, 1].max()))))
    return out


DECOR = ("chair", "sofa")  # dropped when they would stand outside the room's clear zone
ZONE = ((-0.50, 1.30), (-1.10, 0.90))  # = assets_x.rooms.ZONE (every room keeps this box clear around the robot)


def in_zone(parts, yaw: float) -> bool:
    (zx0, zx1), (zy0, zy1) = ZONE
    return all(zx0 <= x0 and x1 <= zx1 and zy0 <= y0 and y1 <= zy1 for (x0, x1), (y0, y1) in aabb_world(parts, yaw))


# ----------------------------------------------------------------------------------------------- usability
FINGER_X, FINGER_Y = 0.065, 0.03  # = assets_x.reach (open fingers close along world x)
GRIPPER_ABOVE = 0.20 + 0.24
TALL, TALL_MARGIN = 0.12, 0.09  # pilot 1: carried objects / the wrist hit parts taller than the carry clearance  # carry band top above the node + wrist height (reach.GRIPPER_ABOVE_TCP + Z_NEED[1])


def blocked_s(pts_s: np.ndarray, top: float, parts, own=()) -> np.ndarray:
    """Points (S) where a part rises above `top` within the finger keep-out, or a part covers them below the gripper
    band (not top-accessible)."""
    out = np.zeros(len(pts_s), bool)
    for p in parts:
        if p["id"] in own:
            continue
        lo, hi = _bounds(p)
        if hi[2] <= top + 0.005:
            continue
        if lo[2] > top + GRIPPER_ABOVE:
            continue
        mx = FINGER_X if lo[2] <= top + 0.25 else 0.0  # high parts (cabinets) only block straight below them
        my = FINGER_Y if lo[2] <= top + 0.25 else 0.0
        if lo[2] <= top + 0.25 and hi[2] > top + TALL:  # tall parts (monitor, backsplash, books, dividers of a
            mx, my = max(mx, TALL_MARGIN), max(my, TALL_MARGIN)  # higher tier): the carried object / wrist need room
        out |= ((pts_s[:, 0] > lo[0] - mx) & (pts_s[:, 0] < hi[0] + mx) & (pts_s[:, 1] > lo[1] - my)
                & (pts_s[:, 1] < hi[1] + my))
    return out


def node_points(node: dict, yaw: float, step: float = 0.02, margin: float = EDGE):
    """World grid points (step) inside the node box shrunk by margin (containers: the finger keep-out from the
    walls) -> (world pts [N, 2], S pts [N, 2])."""
    (x0, x1), (y0, y1) = node["box"]
    mx, my = (FINGER_X, FINGER_Y) if node.get("rim_z") is not None else (margin, margin)
    xs = np.arange(x0 + mx, x1 - mx + 1e-9, step)
    ys = np.arange(y0 + my, y1 - my + 1e-9, step)
    if len(xs) == 0 or len(ys) == 0:  # narrow containers / slots: their centre line
        xs = xs if len(xs) else np.array([(x0 + x1) / 2])
        ys = ys if len(ys) else np.array([(y0 + y1) / 2])
        if node.get("rim_z") is None:
            return np.zeros((0, 2)), np.zeros((0, 2))
    S = np.array([[x, y] for x in xs for y in ys], float)
    return (rot(yaw) @ S.T).T, S


def usable(node: dict, scene: dict, rm, lift: float, reach: bool = True) -> np.ndarray:
    """World points of the node the arm can use at this lift (reach + view + free of parts); reach=False: every
    visible, free point of the node (objects that are only looked at: references, decoys, distractors)."""
    W, S = node_points(node, scene["yaw"])
    if len(W) == 0:
        return W
    m = rm.at_lift(lift)
    own = {node["part"]}
    if reach:
        ok = R9.usable_points(m, scene["arm"], W[:, 0], W[:, 1], node["top_z"])
    else:
        ok = R9.visible_points(m, W[:, 0], W[:, 1], node["top_z"])
    if node.get("rim_z") is None:
        ok &= ~blocked_s(S, node["top_z"], scene["parts_s"], own)
    else:  # inside a container: only parts above its rim block (its own walls are handled by the margin)
        ok &= ~blocked_s(S, node["rim_z"], scene["parts_s"], own)
    return W[ok]


def choose_lift(scene: dict, rm, lifts=LIFTS, min_pts: int = 4):
    """The lift with the most usable nodes (>= min_pts points each), then the most points, then the default."""
    best = None
    for L in lifts:
        per = {n["id"]: len(usable(n, scene, rm, L)) for n in scene["nodes"]}
        n_ok = sum(v >= min_pts for v in per.values())
        key = (n_ok, sum(per.values()), L == LIFT_DEFAULT, -abs(L - LIFT_DEFAULT))
        if best is None or key > best[0]:
            best = (key, L, per)
    return best[1], best[2]


# ----------------------------------------------------------------------------------------------- sampling
def sample(family: str, rule: str, seed: int, arm: str, rm=None, tries: int = 24) -> dict:
    """One scene: parts (S and world), nodes, robot pose, lift, usable point counts per node.
    Redraws (new sub-seed) while parts enter the robot keep-out box or no node is usable; RuntimeError after
    `tries`."""
    fn, rules = FAMILIES[family]
    if rule not in rules:
        raise ValueError(f"{family}: rule {rule!r} not in {rules}")
    A.check_arm(arm)
    rm = rm or R9.load_default()
    last = None
    for k in range(tries):
        rng = np.random.default_rng([int(seed), 909, FAMILY_CODE[family], rules.index(rule), k])
        d = float(rng.uniform(*DIST))
        yaw = float(rng.uniform(-YAW_MAX, YAW_MAX))
        b = _B(rng, yb=A.side(arm) * -0.23, sgn=A.side(arm))
        params = fn(b, rule, d, _yc(rng, arm))
        params["holders"] = add_holders(b, rule)
        if len(b.parts) > N_SLOTS:
            last = f"{len(b.parts)} parts > {N_SLOTS}"
            continue
        bad = keep_out_hits(b.parts, yaw)
        if bad:
            last = f"keep-out {bad}"
            continue
        b.parts = [p for p in b.parts if p["role"] not in DECOR or in_zone([p], yaw)]  # decor past the room zone
        if not in_zone([p for p in b.parts if p["role"] != "room_wall"], yaw):
            last = "outside the room zone"
            continue
        sc = {"family": family, "rule": rule, "seed": int(seed), "arm": arm, "try": k, "yaw": round(yaw, 5),
              "robot_pose": {"distance": round(d, 4), "yaw": round(-yaw, 5)}, "params": params,
              "parts_s": b.parts, "nodes": b.nodes}
        lift, per = choose_lift(sc, rm)
        if max(per.values(), default=0) < 4:
            last = f"no usable node {per}"
            continue
        sc.update(lift=round(float(lift), 4), usable_n=per,
                  furniture=[to_world_part(p, yaw) for p in b.parts], walls=[])
        return sc
    raise RuntimeError(f"{family}/{rule} seed {seed}: {last}")


def usable_nodes(scene: dict, min_pts: int = 4) -> list:
    return [n for n in scene["nodes"] if scene["usable_n"].get(n["id"], 0) >= min_pts]


def all_rules() -> list:
    return [(f, r) for f, (_, rs) in FAMILIES.items() for r in rs]


def tall_parts(scene: dict, top: float) -> list:
    """S-frame xy boxes of the parts rising more than TALL above `top` (and starting below top + 0.25)."""
    out = []
    for p in scene["parts_s"]:
        lo, hi = _bounds(p)
        if hi[2] > top + TALL and lo[2] <= top + 0.25:
            out.append(((lo[0], hi[0]), (lo[1], hi[1])))
    return out


def seg_box_dist(a, b, box, n: int = 12) -> float:
    """Smallest distance (S frame, xy) from the segment a-b to an axis-aligned box (sampled)."""
    (x0, x1), (y0, y1) = box
    best = 9.0
    for t in np.linspace(0.0, 1.0, n):
        q = np.asarray(a, float) * (1 - t) + np.asarray(b, float) * t
        dx = max(x0 - q[0], 0.0, q[0] - x1)
        dy = max(y0 - q[1], 0.0, q[1] - y1)
        best = min(best, float(np.hypot(dx, dy)))
    return best
