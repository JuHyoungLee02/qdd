"""Parametric furniture kinds and sample_scene(kind, seed) (pure; interface agreed with L8D 2026-09-27).

A scene is a list of static cuboid parts (colliders + one colour each) in the robot base / world frame (x forward,
y left, z up, metres). Its support surfaces are not hand-written: they are extracted from the same parts by
surfaces.mesh_support_surfaces, so the surface table and the collision geometry can not disagree.

Kinds (all numbers drawn from np.random.default_rng([seed, 97, KIND_CODE[kind]])):
  table            4-leg table, top 0.72-0.98, the L8 table's footprint band
  counter          kitchen counter: solid cabinet body + overhanging top 0.86-0.96 + backsplash
  counter_cabinet  counter + wall cabinet over the back part (front open, back covered)
  shelf_low        low bookcase facing the robot: open top 0.78-0.95 + a covered inner tier
  shelf_tall       tall bookcase: a covered middle tier 0.62-0.72, open top 0.92-1.12 (reachable with the lift up)
  low_table        coffee table, top 0.40-0.62 (reachable with the lift down)
  bin              table + an open bin (inner >= 12 cm, walls 6-12 cm): a container place target
  stand            table + a raised block 5-12 cm: a second, higher surface on the table
  multi_level      two tables side by side in y at heights 5-15 cm apart
  floor_bin        an open crate on a solid base on the floor: inner floor 0.20-0.35, walls 10-16 cm (lift down)
Every kind may get a back wall and a side wall (appearance / head-camera context, never reachable).
Parts never enter the robot keep-out box (KEEP_OUT) -- checked in sample_scene.
"""
from __future__ import annotations

import math

import numpy as np

from . import surfaces as S

KIND_CODE = {"table": 1, "counter": 2, "counter_cabinet": 3, "shelf_low": 4, "shelf_tall": 5, "low_table": 6,
             "bin": 7, "stand": 8, "multi_level": 9, "floor_bin": 10}
KINDS = tuple(KIND_CODE)


def _kind_hash(k: str) -> float:
    import hashlib
    return int(hashlib.sha256(("l8x-ood-s:" + k).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


# OOD-S (L8D seeds 70500-70699): 2 of the 9 parametric kinds held out by name hash (the plain table never: it is
# the L8 anchor); mesh kinds split per piece (assets_table "split").
OOD_S_KINDS = tuple(sorted(sorted((k for k in KINDS if k != "table"), key=_kind_hash)[:2]))
KIND_SPLIT = {k: ("ood" if k in OOD_S_KINDS else "train") for k in KINDS}
WS_Y = (-0.40, -0.06)  # = scene.WS_Y (right-arm y band)
KEEP_OUT = ((-0.40, 0.15), (-0.45, 0.45), (0.0, 2.0))  # robot body: no furniture part may enter this box
BOARD = 0.02  # shelf board / panel thickness
WOOD = [(0.55, 0.45, 0.35), (0.62, 0.50, 0.36), (0.40, 0.30, 0.22), (0.75, 0.72, 0.66), (0.30, 0.30, 0.32),
        (0.85, 0.85, 0.82), (0.50, 0.35, 0.28), (0.20, 0.22, 0.25)]
WALL = [(0.80, 0.80, 0.78), (0.70, 0.74, 0.78), (0.86, 0.82, 0.74), (0.60, 0.62, 0.60)]
BIN = [(0.15, 0.35, 0.75), (0.80, 0.25, 0.20), (0.20, 0.60, 0.30), (0.25, 0.25, 0.25), (0.90, 0.60, 0.10)]


def _r(v, n=4):
    return round(float(v), n)


def part(pid, lo, hi, color, role, surface_kind=None):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    return {"id": pid, "usd": None, "prim": "cuboid", "size": [_r(v) for v in hi - lo],
            "pos": [_r(v) for v in (hi + lo) / 2], "yaw": 0.0, "static": True, "color": [_r(c, 3) for c in color],
            "role": role, "surface_kind": surface_kind}


def _bounds(p):
    c, s = np.asarray(p["pos"]), np.asarray(p["size"])
    return c - s / 2, c + s / 2


def _pick(rng, seq):
    return seq[int(rng.integers(len(seq)))]


def _table(rng, pid, top, x_front, x_depth, y_lo, y_hi, color, kind="table", thick=0.04, leg=0.05):
    out = [part(pid, (x_front, y_lo, top - thick), (x_front + x_depth, y_hi, top), color, "top", kind)]
    for i, (x, y) in enumerate(((x_front, y_lo), (x_front, y_hi - leg), (x_front + x_depth - leg, y_lo),
                                (x_front + x_depth - leg, y_hi - leg))):
        out.append(part(f"{pid}_leg{i}", (x, y, 0.0), (x + leg, y + leg, top - thick), color, "leg"))
    return out


def _walls(rng, x_back):
    out = []
    col = _pick(rng, WALL)
    if rng.random() < 0.7:
        xb = x_back + rng.uniform(0.05, 0.40)
        out.append(part("wall_back", (xb, -1.6, 0.0), (xb + 0.05, 1.2, 2.2), col, "wall"))
    if rng.random() < 0.4:
        ys = -rng.uniform(0.85, 1.20)
        out.append(part("wall_side", (0.15, ys - 0.05, 0.0), (x_back + 0.5, ys, 2.2), col, "wall"))
    return out


def _build(kind: str, rng) -> tuple[list, dict]:
    wood = _pick(rng, WOOD)
    yc = rng.uniform(-0.15, -0.05)
    if kind == "table":
        top, xf = rng.uniform(0.72, 0.98), rng.uniform(0.15, 0.22)
        dx, dy = rng.uniform(0.55, 0.90), rng.uniform(0.80, 1.30)
        return _table(rng, "table", top, xf, dx, yc - dy / 2, yc + dy / 2, wood), dict(top=top)
    if kind in ("counter", "counter_cabinet"):
        top, xf = rng.uniform(0.86, 0.96), rng.uniform(0.15, 0.20)
        depth, dy, over = rng.uniform(0.55, 0.65), rng.uniform(1.4, 2.0), rng.uniform(0.12, 0.16)  # v2: body front 0.19-0.27 jammed the arm
        y0, y1 = yc - dy / 2, yc + dy / 2
        body = _pick(rng, WOOD)
        ps = [part("counter", (xf, y0, top - 0.04), (xf + depth, y1, top), _pick(rng, WALL + WOOD), "top",
                   "counter"),
              part("counter_body", (xf + over, y0, 0.0), (xf + depth, y1, top - 0.04), body, "body"),
              part("backsplash", (xf + depth - 0.02, y0, top), (xf + depth, y1, top + rng.uniform(0.35, 0.55)),
                   _pick(rng, WALL), "wall")]
        prm = dict(top=top, depth=depth)
        if kind == "counter_cabinet":
            cd, cz = rng.uniform(0.28, 0.36), top + rng.uniform(0.40, 0.50)
            ps.append(part("wall_cabinet", (xf + depth - cd, y0, cz), (xf + depth - 0.02, y1, cz + 0.60), body,
                           "cabinet"))
            prm.update(cabinet_depth=cd, cabinet_bottom=cz)
        return ps, prm
    if kind in ("shelf_low", "shelf_tall"):
        xf, dx, dy = rng.uniform(0.28, 0.38), rng.uniform(0.30, 0.40), rng.uniform(0.80, 1.00)
        y0, y1 = yc - dy / 2, yc + dy / 2
        if kind == "shelf_low":
            H = rng.uniform(0.78, 0.95)
            tiers = [0.08, rng.uniform(0.38, 0.48), H]
        else:
            mid = rng.uniform(0.62, 0.72)  # lift era: top 0.92-1.12 reachable at lift ~0, middle tier covered
            tiers = [0.08, rng.uniform(0.38, 0.48), mid, mid + rng.uniform(0.30, 0.40)]
            H = tiers[-1]
        ps = [part("shelf_side_r", (xf, y0 - BOARD, 0.0), (xf + dx, y0, H), wood, "side"),
              part("shelf_side_l", (xf, y1, 0.0), (xf + dx, y1 + BOARD, H), wood, "side"),
              part("shelf_back", (xf + dx, y0 - BOARD, 0.0), (xf + dx + BOARD, y1 + BOARD, H), wood, "back")]
        for i, z in enumerate(tiers):
            ps.append(part(f"shelf_tier{i}", (xf, y0, z - BOARD), (xf + dx, y1, z), wood, "tier", "shelf_tier"))
        return ps, dict(tiers=tiers, top=H)
    if kind == "low_table":
        top, xf = rng.uniform(0.40, 0.62), rng.uniform(0.18, 0.25)
        dx, dy = rng.uniform(0.45, 0.70), rng.uniform(0.70, 1.10)
        return _table(rng, "low_table", top, xf, dx, yc - dy / 2, yc + dy / 2, wood, "low_table"), dict(top=top)
    if kind in ("bin", "stand"):
        top, xf = rng.uniform(0.80, 0.90), rng.uniform(0.15, 0.22)
        dx, dy = rng.uniform(0.60, 0.85), rng.uniform(0.90, 1.20)
        ps = _table(rng, "table", top, xf, dx, yc - dy / 2, yc + dy / 2, wood)
        cx, cy = rng.uniform(0.40, 0.46), rng.uniform(-0.32, -0.15)
        if kind == "bin":
            bx, by, bh, t = rng.uniform(0.16, 0.24), rng.uniform(0.18, 0.28), rng.uniform(0.06, 0.12), 0.01
            x0, x1, y0, y1 = cx - bx / 2, cx + bx / 2, cy - by / 2, cy + by / 2
            col = _pick(rng, BIN)
            ps += [part("bin_floor", (x0, y0, top), (x1, y1, top + t), col, "bin_floor", "bin_floor"),
                   part("bin_wall0", (x0, y0, top), (x1, y0 + t, top + bh), col, "bin_wall"),
                   part("bin_wall1", (x0, y1 - t, top), (x1, y1, top + bh), col, "bin_wall"),
                   part("bin_wall2", (x0, y0, top), (x0 + t, y1, top + bh), col, "bin_wall"),
                   part("bin_wall3", (x1 - t, y0, top), (x1, y1, top + bh), col, "bin_wall")]
            return ps, dict(top=top, bin=[_r(bx), _r(by), _r(bh)])
        s, h = rng.uniform(0.12, 0.20), rng.uniform(0.05, 0.12)
        ps.append(part("stand", (cx - s / 2, cy - s / 2, top), (cx + s / 2, cy + s / 2, top + h), _pick(rng, WOOD),
                       "stand", "stand"))
        return ps, dict(top=top, stand=[_r(s), _r(h)])
    if kind == "floor_bin":  # an open crate on a solid base standing on the floor (reachable only with the lift down)
        fz, wh, t = rng.uniform(0.20, 0.35), rng.uniform(0.10, 0.16), 0.015
        bx, by = rng.uniform(0.24, 0.34), rng.uniform(0.28, 0.40)
        cx, cy = rng.uniform(0.46, 0.50), rng.uniform(-0.30, -0.16)  # front >= 0.29 (v2: nearer bodies jam the robot)
        x0, x1, y0, y1 = cx - bx / 2, cx + bx / 2, cy - by / 2, cy + by / 2
        col = _pick(rng, BIN)
        ps = [part("crate_base", (x0, y0, 0.0), (x1, y1, fz), _pick(rng, WOOD), "body", "bin_floor"),
              part("crate_wall0", (x0, y0, fz), (x1, y0 + t, fz + wh), col, "bin_wall"),
              part("crate_wall1", (x0, y1 - t, fz), (x1, y1, fz + wh), col, "bin_wall"),
              part("crate_wall2", (x0, y0, fz), (x0 + t, y1, fz + wh), col, "bin_wall"),
              part("crate_wall3", (x1 - t, y0, fz), (x1, y1, fz + wh), col, "bin_wall")]
        return ps, dict(floor=fz, wall=wh, size=[_r(bx), _r(by)])
    if kind == "multi_level":
        h1 = rng.uniform(0.78, 0.90)
        h2 = float(np.clip(h1 + rng.choice([-1, 1]) * rng.uniform(0.05, 0.15), 0.72, 0.98))
        xf, dx, ys = rng.uniform(0.15, 0.22), rng.uniform(0.60, 0.85), rng.uniform(-0.26, -0.20)
        ps = _table(rng, "table_r", h1, xf, dx, ys - 0.55, ys, wood)
        ps += _table(rng, "table_l", h2, xf, dx, ys, ys + 0.55, _pick(rng, WOOD))
        return ps, dict(top_r=h1, top_l=h2, split_y=ys)
    raise ValueError(f"kind {kind!r}: one of {KINDS}")


def _label(surfs, parts):
    """Name each extracted surface by the part whose top it is (same height, xy overlap)."""
    out = []
    for s in surfs:
        (x0, x1), (y0, y1) = s["xy_box"]
        best = None
        for p in parts:
            lo, hi = _bounds(p)
            if p["surface_kind"] and abs(hi[2] - s["top_z"]) < 0.004 and lo[0] < x1 and hi[0] > x0 \
                    and lo[1] < y1 and hi[1] > y0:
                best = p
                break
        if best is None:
            continue  # a top of a wall / side panel / cabinet: not a support surface we offer
        kind = best["surface_kind"]
        if kind == "shelf_tier" and s["covered_above"] is None:
            kind = "shelf_top"
        if kind in ("counter",) and s["covered_above"] is not None:
            kind = "counter_covered"
        out.append({"id": f"{best['id']}_{len(out)}", "kind": kind, "part": best["id"], "top_z": _r(s["top_z"]),
                    "xy_box": [[_r(v) for v in s["xy_box"][0]], [_r(v) for v in s["xy_box"][1]]],
                    "area": _r(s["area"]), "covered_above": None if s["covered_above"] is None else _r(s["covered_above"]),
                    "clearance": None if s["clearance"] is None else _r(s["clearance"]),
                    "container": s["container"], "inner_floor_z": _r(s["top_z"]) if s["container"] else None,
                    "rim_z": None if s["rim_z"] is None else _r(s["rim_z"])})
    return out


def check_keep_out(parts) -> list:
    (a0, a1), (b0, b1), (c0, c1) = KEEP_OUT
    bad = []
    for p in parts:
        lo, hi = _bounds(p)
        if lo[0] < a1 and hi[0] > a0 and lo[1] < b1 and hi[1] > b0 and lo[2] < c1 and hi[2] > c0:
            bad.append(p["id"])
    return bad


MESH_PREFIX = "thor_"
MESH_YAW = -math.pi / 2  # THOR fronts face -y after the Y-up fix; yaw -90 deg turns them to face the robot (-x)
MESH_X_FRONT = {"table": (0.15, 0.22), "side_table": (0.15, 0.22), "low_table": (0.18, 0.25), "low": (0.18, 0.25),
                "counter": (0.20, 0.28), "shelf": (0.25, 0.35), "bin": (0.30, 0.40)}


def mesh_kinds(mesh_assets: dict | None) -> tuple:
    return tuple(sorted({MESH_PREFIX + a["category"] for a in (mesh_assets or {}).values()}))


def _mesh_piece(rng, kind: str, mesh_assets: dict, split: str):
    cat = kind[len(MESH_PREFIX):]
    names = sorted(n for n, a in mesh_assets.items() if a["category"] == cat and a["split"] == split)
    if not names:
        raise ValueError(f"no {split} assets of category {cat}")
    name = names[int(rng.integers(len(names)))]
    a = mesh_assets[name]
    sx, sy, sz = a["collider_size"]
    yaw = MESH_YAW
    dx, dy = abs(math.sin(yaw)) * sy + abs(math.cos(yaw)) * sx, abs(math.sin(yaw)) * sx + abs(math.cos(yaw)) * sy
    xf = rng.uniform(*MESH_X_FRONT[cat])
    yc = rng.uniform(-0.25, -0.10)
    base = [xf + dx / 2, yc, 0.0]
    p = {"id": name, "usd": a["dst"], "asset": name, "prim": "mesh", "size": [_r(dx), _r(dy), _r(sz)],
         "pos": [_r(base[0]), _r(yc), _r(sz / 2)], "base_pos": [_r(v) for v in base], "yaw": _r(yaw, 6),
         "static": True, "color": None, "role": "mesh", "surface_kind": a["top_kind"], "category": cat,
         "license": a["license"], "source": a["source"], "split": a["split"]}
    surfs = []
    for s in a["surfaces"]:
        t = S.transform_surface(s, pos=base, yaw=yaw)
        k = a["top_kind"] if t["covered_above"] is None else "shelf_tier"
        if t["container"]:  # open container = bin floor; covered container = inside a closed drawer / cabinet
            k = "bin_floor" if t["covered_above"] is None else "enclosed"
        surfs.append({"id": f"{name}_{len(surfs)}", "kind": k, "part": name, "top_z": _r(t["top_z"]),
                      "xy_box": [[_r(v) for v in t["xy_box"][0]], [_r(v) for v in t["xy_box"][1]]],
                      "area": _r(t["area"]), "covered_above": None if t["covered_above"] is None
                      else _r(t["covered_above"]), "clearance": None if t["clearance"] is None else _r(t["clearance"]),
                      "container": t["container"], "inner_floor_z": _r(t["top_z"]) if t["container"] else None,
                      "rim_z": None if t["rim_z"] is None else _r(t["rim_z"])})
    return p, surfs, {"asset": name, "category": cat, "yaw": _r(yaw, 4), "x_front": _r(xf)}


def sample_scene(kind: str, seed: int, reach=None, mesh_assets: dict | None = None, split: str = "train",
                 lift="auto") -> dict:
    """-> {kind, seed, kind_split, params, furniture [parts], walls [parts], surfaces [...], lift, lift_usable,
    placement_regions [...]}.
    reach: optional reach.ReachModel (the L8-D probe); with it every surface gets its reachable / visible / free
    placement region at the scene's lift. lift: "auto" (reach.choose_lift: the lift in [-0.50, 0.00] that makes
    the most surfaces usable, default -0.0993 on ties), a float (fixed) or None (= default). lift_usable = per
    surface, every probed lift at which it is usable. The lift moves torso + head camera + arms rigidly in z.
    Mesh kinds (thor_<category>, mesh_kinds(assets_table)) pick one licensed piece of that category and split
    ("train" | "ood": the OOD-O held-out pieces, 20 % by name hash). kind_split: KIND_SPLIT (OOD-S kinds)."""
    if kind.startswith(MESH_PREFIX):
        rng = np.random.default_rng([int(seed), 97, 100, sum(kind.encode())])
        p, surfs, prm = _mesh_piece(rng, kind, mesh_assets or {}, split)
        walls = _walls(rng, p["pos"][0] + p["size"][0] / 2)
        bad = check_keep_out([p] + walls)
        if bad:
            raise RuntimeError(f"{kind} seed {seed}: parts in the robot keep-out box: {bad}")
        out = {"kind": kind, "seed": int(seed), "kind_split": p["split"], "params": prm, "furniture": [p],
               "walls": walls, "lift": None, "lift_usable": None,
               "surfaces": surfs, "placement_regions": []}
        if reach is not None:
            _with_lift(out, reach, obstacles_of(walls), lift)
        return out
    if kind not in KIND_CODE:
        raise ValueError(f"kind {kind!r}: one of {KINDS} or {MESH_PREFIX}<category>")
    rng = np.random.default_rng([int(seed), 97, KIND_CODE[kind]])
    furn, prm = _build(kind, rng)
    x_back = max(_bounds(p)[1][0] for p in furn)
    walls = _walls(rng, x_back)
    bad = check_keep_out(furn + walls)
    if bad:  # pragma: no cover - the bands above keep clear of it
        raise RuntimeError(f"{kind} seed {seed}: parts in the robot keep-out box: {bad}")
    P, F = S.merge_meshes([S.box_mesh(*_bounds(p)) for p in furn + walls])
    surfs = _label(S.mesh_support_surfaces(P, F), furn)
    out = {"kind": kind, "seed": int(seed), "kind_split": KIND_SPLIT[kind], "lift": None, "lift_usable": None,
           "params": {k: (_r(v) if isinstance(v, float) else v)
                                                        for k, v in prm.items()},
           "furniture": furn, "walls": walls, "surfaces": surfs, "placement_regions": []}
    if reach is not None:
        _with_lift(out, reach, obstacles_of(furn + walls), lift)
    return out


def _with_lift(out: dict, reach, obstacles, lift) -> None:
    from .reach import LIFT_DEFAULT, choose_lift, placement_regions
    if lift == "auto":
        L, regs, per = choose_lift(out["surfaces"], reach, obstacles)
    else:
        L = LIFT_DEFAULT if lift is None else float(lift)
        regs = placement_regions(out["surfaces"], reach.at_lift(L), obstacles)
        per = None
    out["lift"] = round(float(L), 4)
    out["lift_usable"] = per
    out["placement_regions"] = regs


def obstacles_of(parts) -> list:
    """[((x0, x1), (y0, y1), z_top)] of parts (axis-aligned; parametric parts have yaw 0)."""
    out = []
    for p in parts:
        lo, hi = _bounds(p)
        out.append(((float(lo[0]), float(hi[0])), (float(lo[1]), float(hi[1])), float(hi[2])))
    return out


def all_parts(scene: dict) -> list:
    return list(scene["furniture"]) + list(scene["walls"])


assert math.isclose(BOARD, 0.02)
