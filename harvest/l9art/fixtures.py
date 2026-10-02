"""Procedural articulated fixtures (pure numpy + USDA text): drawer chests, hinged-door cabinets, sliding-door
cabinets, knob panels, button / switch panels and a knob + button panel. No external asset (licence risk 0).

Fixture frame F: origin at the front-bottom centre of the body, +x into the fixture (away from the robot), +y left,
+z up; the front face is the plane x = 0 and the robot stands on the -x side. Every link frame is parallel to F at
joint value 0 (the link origin = the joint origin); boxes may carry their own orientation.
Joint value q >= 0 always means "open / turned / pressed" along the joint's `axis` (unit vector in F): prismatic =
translation along axis, revolute = right-handed rotation about axis through the origin. Knob q > 0 = clockwise as
seen by the robot (front panels) or from above (top panels).

spec = sample(family, seed) is plain JSON; usda(spec) writes the articulation (root link `base` fixed by the Isaac Lab
cfg, links rigid bodies, PhysicsPrismaticJoint / PhysicsRevoluteJoint with axis X rotated onto `axis`); the kinematic
helpers (link_T, handle_frame, boxes_world) give world geometry for any joint values (planner obstacles, labels)."""
from __future__ import annotations

import math

import numpy as np

FAMILIES = ("drawer", "door", "slide", "knob", "button", "panel", "dial")  # dial = knob panel with top-mounted knobs
FAMILY_CODE = {f: i for i, f in enumerate(FAMILIES)}
WALL = 0.015
WOOD = [(0.55, 0.45, 0.35), (0.62, 0.50, 0.36), (0.40, 0.30, 0.22), (0.75, 0.72, 0.66), (0.30, 0.30, 0.32),
        (0.85, 0.85, 0.82), (0.20, 0.20, 0.22), (0.66, 0.60, 0.52)]
PAINT = [(0.80, 0.80, 0.78), (0.70, 0.74, 0.78), (0.86, 0.82, 0.74), (0.60, 0.62, 0.60), (0.35, 0.45, 0.55),
         (0.55, 0.30, 0.25), (0.25, 0.35, 0.30), (0.90, 0.88, 0.80)]
METAL = [(0.55, 0.56, 0.58), (0.35, 0.36, 0.38), (0.75, 0.76, 0.78), (0.20, 0.22, 0.25)]
KNOB_COL = {"black": (0.06, 0.06, 0.07), "silver": (0.72, 0.73, 0.75), "white": (0.92, 0.92, 0.90),
            "red": (0.75, 0.12, 0.10)}
BTN_COL = {"red": (0.80, 0.10, 0.08), "green": (0.10, 0.60, 0.20), "blue": (0.12, 0.28, 0.75),
           "yellow": (0.92, 0.78, 0.10), "black": (0.06, 0.06, 0.07), "white": (0.93, 0.93, 0.91)}
# handle clearances [가설]: the rear finger of a front grasp needs >= 3.5 cm behind the bar (L8-X b3d change 7: 2.5 cm
# jammed the AI Worker's 4.5 cm pads on the drawer front)
STANDOFF = (0.035, 0.050)
BAR_T = (0.010, 0.014)


def _r(v, n=4):
    return [round(float(x), n) for x in v]


def _box(name, c, s, col, q=None, vis="cube", coll=True):
    b = {"n": name, "c": _r(c), "s": _r(s), "col": _r(col, 3), "vis": vis, "coll": bool(coll)}
    if q is not None:
        b["q"] = _r(q, 6)
    return b


def _pick(rng, seq):
    return seq[int(rng.integers(len(seq)))]


def quat_x_to(v) -> np.ndarray:
    """Unit quaternion (w, x, y, z) rotating +x onto v."""
    v = np.asarray(v, float) / np.linalg.norm(v)
    x = np.array([1.0, 0.0, 0.0])
    d = float(x @ v)
    if d < -1 + 1e-9:
        return np.array([0.0, 0.0, 0.0, 1.0])  # 180 deg about z
    c = np.cross(x, v)
    q = np.array([1.0 + d, *c])
    return q / np.linalg.norm(q)


def qmat(q) -> np.ndarray:
    w, x, y, z = (float(v) for v in q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def rot_axis(axis, ang: float) -> np.ndarray:
    a = np.asarray(axis, float) / np.linalg.norm(axis)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * K @ K


def _carcass(W, D, H, col, front_open=True, shelf_z=None) -> list:
    t = WALL
    out = [_box("top", (D / 2, 0, H - t / 2), (D, W, t), col), _box("bottom", (D / 2, 0, t / 2), (D, W, t), col),
           _box("side_l", (D / 2, W / 2 - t / 2, H / 2), (D, t, H), col),
           _box("side_r", (D / 2, -W / 2 + t / 2, H / 2), (D, t, H), col),
           _box("back", (D - t / 2, 0, H / 2), (t, W, H), col)]
    if not front_open:
        out.append(_box("front", (t / 2, 0, H / 2), (t, W, H), col))
    if shelf_z is not None:
        out.append(_box("shelf", (D / 2, 0, shelf_z), (D - 2 * t, W - 2 * t, t), col))
    return out


def _bar(prefix, centre, along, standoff, length, thick, col) -> list:
    """A bar handle in a link frame: the bar (centre, long axis `along` = 'y' or 'z') on two posts back to x = 0."""
    c = np.asarray(centre, float)
    s = [thick, thick, thick]
    k = 1 if along == "y" else 2
    s[k] = length
    out = [_box(prefix + "_bar", c, s, col)]
    post = standoff - thick / 2
    for j, sg in enumerate((-1, 1)):
        pc = c.copy()
        pc[k] += sg * (length / 2 - thick / 2)
        pc[0] = c[0] + standoff - post / 2  # from the face (x = c + standoff) out to the bar
        out.append(_box(f"{prefix}_post{j}", pc, (post, thick * 0.9, thick * 0.9), col))
    return out


def _knob_pull(prefix, centre, col) -> tuple:
    """Mushroom knob on a drawer: stem + cap (boxes), returns (boxes, grasp centre, cap size)."""
    c = np.asarray(centre, float)
    stem_l, cap_t = 0.025, 0.016
    cap = 0.032
    out = [_box(prefix + "_stem", (c[0] - stem_l / 2, c[1], c[2]), (stem_l, 0.014, 0.014), col),
           _box(prefix + "_cap", (c[0] - stem_l - cap_t / 2, c[1], c[2]), (cap_t, cap, cap), col),
           _box(prefix + "_cap45", (c[0] - stem_l - cap_t / 2, c[1], c[2]), (cap_t, cap, cap), col,
                q=(math.cos(math.pi / 8), math.sin(math.pi / 8), 0, 0))]
    return out, np.array([c[0] - stem_l - cap_t / 2, c[1], c[2]]), cap


def _handle(rng, prefix, x_face, y0, z0, along, max_len, col) -> tuple:
    """Bar (or for horizontal bars sometimes a mushroom knob) on the face x = x_face of a link -> (boxes, handle)."""
    if along == "y" and rng.random() < 0.3:
        bx, gc, cap = _knob_pull(prefix, (x_face, y0, z0), col)
        return bx, {"type": "knob_pull", "gc": _r(gc), "along": None, "length": cap, "thick": cap,
                    "standoff": round(float(-gc[0] + x_face), 4)}
    st = float(rng.uniform(*STANDOFF))
    th = float(rng.uniform(*BAR_T))
    L = float(rng.uniform(0.08, max(0.081, max_len)))
    c = np.array([x_face - st, y0, z0])
    bx = _bar(prefix, c, along, st, L, th, col)
    return bx, {"type": "bar_h" if along == "y" else "bar_v", "gc": _r(c), "along": along, "length": round(L, 4),
                "thick": round(th, 4), "standoff": round(st, 4)}


# ------------------------------------------------------------------------------------------------ families
def _drawer(rng, spec):
    n = int(rng.choice([1, 2, 3], p=[0.3, 0.4, 0.3]))
    W, D = float(rng.uniform(0.30, 0.55)), float(rng.uniform(0.28, 0.40))
    hd = float(rng.uniform(0.11, 0.17))
    H = n * hd + 2 * WALL + (n - 1) * WALL
    body, front, hcol = _pick(rng, WOOD + PAINT), _pick(rng, WOOD + PAINT), _pick(rng, METAL)
    base = _carcass(W, D, H, body)
    zs = []
    z = WALL
    for i in range(n):
        zs.append((z, z + hd))
        z += hd
        if i < n - 1:
            base.append(_box(f"div{i}", (D / 2, 0, z + WALL / 2), (D - WALL, W - 2 * WALL, WALL), body))
            z += WALL
    spec.update(dims={"W": W, "D": D, "H": H}, base=base, body_color=_r(body, 3))
    order = list(range(n))[::-1]  # top first
    for rank, i in enumerate(order):
        z0, z1 = zs[i]
        zc, h = (z0 + z1) / 2, z1 - z0
        ln, jn = f"drawer{i}", f"drw_{i}"
        Dd = D - 0.04
        tray_h = 0.7 * h
        bx = [_box("front", (-0.009, 0, 0), (0.018, W - 0.008, h - 0.006), front),
              _box("floor", (Dd / 2, 0, -h / 2 + 0.012), (Dd, W - 2 * WALL - 0.01, 0.008), front),
              _box("wall_l", (Dd / 2, W / 2 - WALL - 0.009, -h / 2 + 0.008 + tray_h / 2), (Dd, 0.008, tray_h), front),
              _box("wall_r", (Dd / 2, -W / 2 + WALL + 0.009, -h / 2 + 0.008 + tray_h / 2), (Dd, 0.008, tray_h), front),
              _box("wall_b", (Dd - 0.004, 0, -h / 2 + 0.008 + tray_h / 2), (0.008, W - 2 * WALL - 0.01, tray_h), front)]
        y0 = float(rng.uniform(-0.12, 0.12)) * W
        hb, hd_ = _handle(rng, "h", -0.018, y0, float(rng.uniform(-0.1, 0.1)) * h, "y", min(0.18, 0.6 * W), hcol)
        travel = float(min(0.8 * Dd, rng.uniform(0.18, 0.30)))
        spec["links"][ln] = {"origin": _r((0, 0, zc)), "boxes": bx + hb, "mass": round(float(rng.uniform(0.6, 1.2)), 3)}
        spec["joints"][jn] = {"type": "prismatic", "kind": "drawer", "link": ln, "axis": [-1.0, 0.0, 0.0],
                              "origin": _r((0, 0, zc)), "lo": 0.0, "hi": round(travel, 4),
                              "drive": {"stiffness": 0.0, "damping": round(float(rng.uniform(3.0, 15.0)), 3),
                                        "friction": round(float(rng.uniform(0.0, 0.05)), 4)}}
        words = _ordinal(rank, n, ("top", "middle", "bottom"), ("upper", "lower")) + " drawer"
        spec["handles"][ln] = dict(hd_, joint=jn, link=ln, fn=[-1.0, 0.0, 0.0], words=words if n > 1 else "drawer")
        spec["interior"][ln] = {"floor_c": _r((Dd / 2, 0, -h / 2 + 0.016)), "floor_s": _r((Dd - 0.02, W - 2 * WALL - 0.03)),
                                "wall_top_rel": round(tray_h - 0.008, 4)}
    spec["label"] = "small chest of drawers" if n > 1 else "drawer box"


def _ordinal(rank, n, three, two):
    if n == 3:
        return three[rank]
    if n == 2:
        return two[rank]
    return ""


def _door(rng, spec):
    W, D, H = float(rng.uniform(0.24, 0.36)), float(rng.uniform(0.28, 0.40)), float(rng.uniform(0.26, 0.42))
    body, dcol, hcol = _pick(rng, WOOD + PAINT), _pick(rng, WOOD + PAINT), _pick(rng, METAL)
    shelf = H / 2 if rng.random() < 0.5 else None
    spec.update(dims={"W": W, "D": D, "H": H}, base=_carcass(W, D, H, body, shelf_z=shelf), body_color=_r(body, 3))
    s = 1 if rng.random() < 0.5 else -1  # hinge on the robot's left (+y) or right (-y)
    td = 0.018
    org = np.array([-td, s * W / 2, H / 2])
    bx = [_box("panel", (td / 2, -s * W / 2, 0), (td, W - 0.004, H - 0.01), dcol)]
    m = float(rng.uniform(0.03, 0.06))
    hb, hd_ = _handle(rng, "h", 0.0, -s * (W - m), float(rng.uniform(-0.2, 0.2)) * H, "z", min(0.18, 0.6 * H), hcol)
    hi = math.radians(float(rng.uniform(95, 115)))
    spec["links"]["door"] = {"origin": _r(org), "boxes": bx + hb, "mass": round(float(rng.uniform(0.5, 1.2)), 3)}
    spec["joints"]["door_0"] = {"type": "revolute", "kind": "door", "link": "door", "axis": [0.0, 0.0, float(-s)],
                                "origin": _r(org), "lo": 0.0, "hi": round(hi, 4),
                                "drive": {"stiffness": 0.0, "damping": round(float(rng.uniform(0.2, 1.0)), 3),
                                          "friction": round(float(rng.uniform(0.0, 0.03)), 4)}}
    spec["handles"]["door"] = dict(hd_, joint="door_0", link="door", fn=[-1.0, 0.0, 0.0], words="cabinet door",
                                   hinge="left" if s > 0 else "right")
    spec["interior"]["base"] = {"floor_c": _r((D / 2, 0, (shelf if shelf else 0) + WALL)), "floor_s": _r((D - 0.04, W - 0.04))}
    spec["label"] = "small cabinet with a hinged door"


def _slide(rng, spec):
    W, D, H = float(rng.uniform(0.40, 0.60)), float(rng.uniform(0.26, 0.38)), float(rng.uniform(0.24, 0.40))
    body, dcol, hcol = _pick(rng, WOOD + PAINT), _pick(rng, WOOD + PAINT + METAL), _pick(rng, METAL)
    base = _carcass(W, D, H, body)
    sg = 1 if rng.random() < 0.5 else -1  # the sliding panel starts on the +y (left) or -y half
    base.append(_box("fixed_panel", (-0.006, -sg * W / 4, H / 2), (0.012, W / 2, H - 0.02), dcol))
    base.append(_box("rail_top", (-0.02, 0, H - 0.006), (0.028, W, 0.012), body))
    base.append(_box("rail_bot", (-0.02, 0, 0.006), (0.028, W, 0.012), body))
    spec.update(dims={"W": W, "D": D, "H": H}, base=base, body_color=_r(body, 3))
    org = np.array([-0.021, sg * W / 4, H / 2])
    bx = [_box("panel", (0, 0, 0), (0.012, W / 2 + 0.01, H - 0.03), dcol)]
    hb, hd_ = _handle(rng, "h", -0.006, sg * (W / 4 - float(rng.uniform(0.03, 0.06))),
                      float(rng.uniform(-0.15, 0.15)) * H, "z", min(0.16, 0.55 * H), hcol)
    travel = W / 2 - 0.04
    spec["links"]["slide"] = {"origin": _r(org), "boxes": bx + hb, "mass": round(float(rng.uniform(0.5, 1.0)), 3)}
    spec["joints"]["sld_0"] = {"type": "prismatic", "kind": "slide", "link": "slide", "axis": [0.0, float(-sg), 0.0],
                               "origin": _r(org), "lo": 0.0, "hi": round(travel, 4),
                               "drive": {"stiffness": 0.0, "damping": round(float(rng.uniform(3.0, 12.0)), 3),
                                         "friction": round(float(rng.uniform(0.0, 0.05)), 4)}}
    spec["handles"]["slide"] = dict(hd_, joint="sld_0", link="slide", fn=[-1.0, 0.0, 0.0], words="sliding door",
                                    side="left" if sg > 0 else "right")
    spec["label"] = "cabinet with a sliding door"


def _panel_block(rng, spec, label):
    W, D, H = float(rng.uniform(0.20, 0.45)), float(rng.uniform(0.10, 0.22)), float(rng.uniform(0.14, 0.30))
    body = _pick(rng, PAINT + METAL + WOOD)
    spec.update(dims={"W": W, "D": D, "H": H}, base=[_box("block", (D / 2, 0, H / 2), (D, W, H), body)],
                body_color=_r(body, 3), label=label)
    return W, D, H


def _mount(face, W, D, H, y, z_rel):
    """(joint origin in F, outward unit vector, rotation link-canonical -> F) for a knob / button on the front face
    (outward -x) or the top face (outward +z). Canonical geometry is built with outward = -x."""
    if face == "front":
        return np.array([0.0, y, (0.55 + z_rel) * H]), np.array([-1.0, 0, 0]), np.eye(3)
    R = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], float)  # canonical -x (outward) -> +z (smoke 10-02: the sign sank top knobs into the panel)
    return np.array([D * (0.5 + z_rel * 0.6), y, H]), np.array([0, 0, 1.0]), R


def _oriented(b, R):
    if np.allclose(R, np.eye(3)):
        return b
    c = R @ np.asarray(b["c"], float)
    q0 = qmat(b["q"]) if "q" in b else np.eye(3)
    out = dict(b, c=_r(c), q=_r(_mat_quat(R @ q0), 6))
    return out


def _mat_quat(R) -> np.ndarray:
    R = np.asarray(R, float)
    t = np.trace(R)
    if t > 0:
        s = math.sqrt(t + 1.0) * 2
        q = [0.25 * s, (R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s]
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
        q = [(R[2, 1] - R[1, 2]) / s, 0.25 * s, (R[0, 1] + R[1, 0]) / s, (R[0, 2] + R[2, 0]) / s]
    elif R[1, 1] > R[2, 2]:
        s = math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
        q = [(R[0, 2] - R[2, 0]) / s, (R[0, 1] + R[1, 0]) / s, 0.25 * s, (R[1, 2] + R[2, 1]) / s]
    else:
        s = math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
        q = [(R[1, 0] - R[0, 1]) / s, (R[0, 2] + R[2, 0]) / s, (R[1, 2] + R[2, 1]) / s, 0.25 * s]
    q = np.asarray(q, float)
    q /= np.linalg.norm(q)
    return q if q[0] >= 0 else -q


def _add_knob(rng, spec, i, face, y, z_rel, words):
    W, D, H = spec["dims"]["W"], spec["dims"]["D"], spec["dims"]["H"]
    org, out, R = _mount(face, W, D, H, y, z_rel)
    cname = _pick(rng, sorted(KNOB_COL))
    col = KNOB_COL[cname]
    dia, hk = float(rng.uniform(0.035, 0.05)), float(rng.uniform(0.018, 0.028))
    rh, rw = float(rng.uniform(0.024, 0.032)), float(rng.uniform(0.010, 0.014))  # a tall fin the pads can hold [가설]
    bx = [_box("body", (-hk / 2, 0, 0), (hk, dia * 0.92, dia * 0.92), col),
          _box("body45", (-hk / 2, 0, 0), (hk, dia * 0.92, dia * 0.92), col, q=(math.cos(math.pi / 8), math.sin(math.pi / 8), 0, 0)),
          _box("ridge", (-hk - rh / 2 + 0.002, 0, 0), (rh, dia * 0.95, rw), col),
          _box("mark", (-hk - rh + 0.0015, dia * 0.38, 0), (0.003, 0.008, rw * 0.6), (0.95, 0.95, 0.95), coll=False)]
    bx = [_oriented(b, R) for b in bx]
    ln, jn = f"knob{i}", f"knob_{i}"
    axis = -out  # q > 0 = clockwise seen from outside
    spec["links"][ln] = {"origin": _r(org), "boxes": bx, "mass": 0.08}
    spec["joints"][jn] = {"type": "revolute", "kind": "knob", "link": ln, "axis": _r(axis), "origin": _r(org),
                          "lo": round(-math.radians(150), 4), "hi": round(math.radians(150), 4),
                          "drive": {"stiffness": 0.0, "damping": round(float(rng.uniform(0.15, 0.40)), 4),
                                    "friction": round(float(rng.uniform(0.05, 0.15)), 4)}}  # knobs hold their angle (smoke: one spun 150 deg)
    ridge = R @ np.array([-hk - rh / 2 + 0.002, 0, 0])
    mark = R @ np.array([-hk - rh + 0.0015, dia * 0.38, 0])
    spec["handles"][ln] = {"type": "knob", "joint": jn, "link": ln, "gc": _r(ridge), "fn": _r(out),
                           "ridge_along": _r(R @ np.array([0, 1.0, 0])), "length": round(dia * 0.95, 4), "ridge_h": round(rh, 4),
                           "thick": round(rw, 4), "mark": _r(mark), "words": f"{cname} {words}".strip(),
                           "face": face, "color": cname}


def _add_button(rng, spec, i, face, y, z_rel, words, switch=False):
    W, D, H = spec["dims"]["W"], spec["dims"]["D"], spec["dims"]["H"]
    org, out, R = _mount(face, W, D, H, y, z_rel)
    cname = _pick(rng, sorted(BTN_COL))
    col = BTN_COL[cname]
    ht = float(rng.uniform(0.012, 0.018))
    sy, sz = (0.024, 0.040) if switch else ((s := float(rng.uniform(0.022, 0.04))), s)
    bx = [_box("cap", (-ht / 2, 0, 0), (ht, sy, sz), col)]
    if not switch and rng.random() < 0.5:
        bx.append(_box("cap45", (-ht / 2, 0, 0), (ht, sy, sz), col, q=(math.cos(math.pi / 8), math.sin(math.pi / 8), 0, 0)))
    bx = [_oriented(b, R) for b in bx]
    ln, jn = f"button{i}", f"btn_{i}"
    travel = float(rng.uniform(0.008, 0.012))
    spec["links"][ln] = {"origin": _r(org), "boxes": bx, "mass": 0.03}
    spec["joints"][jn] = {"type": "prismatic", "kind": "button", "link": ln, "axis": _r(-out), "origin": _r(org),
                          "lo": 0.0, "hi": round(travel, 4),
                          "drive": {"stiffness": round(float(rng.uniform(150, 400)), 1), "damping": 2.0, "friction": 0.0}}
    spec["handles"][ln] = {"type": "button", "joint": jn, "link": ln, "gc": _r(R @ np.array([-ht, 0, 0])),
                           "fn": _r(out), "length": round(max(sy, sz), 4), "thick": round(min(sy, sz), 4),
                           "words": f"{cname} {'switch' if switch else words}".strip(), "face": face, "color": cname}


def _positions(rng, n, W):
    if n == 1:
        return [float(rng.uniform(-0.15, 0.15)) * W]
    span = W * 0.6
    return [float(v) for v in np.linspace(-span / 2, span / 2, n)]


def _side_words(n, k):
    if n == 1:
        return ""
    names = ("left", "right") if n == 2 else ("left", "middle", "right")
    return names[k]


def _knobs(rng, spec, face="front"):
    W, _, _ = _panel_block(rng, spec, "control panel with knobs")
    n = int(rng.choice([1, 2, 3], p=[0.35, 0.35, 0.3]))
    ys = _positions(rng, n, W)[::-1]  # robot's left (+y) first
    for k, y in enumerate(ys):
        _add_knob(rng, spec, k, face, y, float(rng.uniform(-0.05, 0.1)) if face == "front" else 0.0,
                  (_side_words(n, k) + " knob").strip())


def _buttons(rng, spec):
    W, _, _ = _panel_block(rng, spec, "panel with buttons")
    face = "front"  # the switch + buttons panel faces the robot (top-face presses come from the panel family)
    n = int(rng.choice([2, 3], p=[0.6, 0.4]))
    sw = True  # every button panel: one switch + 1-2 buttons (button_press and switch_press both fit any job)
    if sw and n == 1:
        n = 2  # one switch + at least one button (button_press and switch_press both fit)
    ys = _positions(rng, n, W)[::-1]
    for k, y in enumerate(ys):
        _add_button(rng, spec, k, face, y, float(rng.uniform(-0.05, 0.15)) if face == "front" else 0.0,
                    (_side_words(n, k) + " button").strip(), switch=sw and k == 0)


def _panel(rng, spec):
    W, _, _ = _panel_block(rng, spec, "control panel")
    face = "front" if rng.random() < 0.6 else "top"
    a, b = (-0.22 * W, 0.22 * W) if rng.random() < 0.5 else (0.22 * W, -0.22 * W)
    _add_knob(rng, spec, 0, face, a, 0.0, "knob")
    _add_button(rng, spec, 0, face, b, 0.0, "button")


BUILDERS = {"drawer": _drawer, "door": _door, "slide": _slide, "knob": _knobs, "button": _buttons, "panel": _panel,
            "dial": lambda rng, spec: _knobs(rng, spec, "top")}


def sample(family: str, seed: int) -> dict:
    if family not in BUILDERS:
        raise ValueError(f"family {family!r}")
    rng = np.random.default_rng([int(seed), 4711, FAMILY_CODE[family]])
    spec = {"family": family, "seed": int(seed), "name": f"art_{family}_{int(seed)}", "links": {}, "joints": {},
            "handles": {}, "interior": {}, "version": "l9art-fx2"}
    BUILDERS[family](rng, spec)
    spec["dims"] = {k: round(float(v), 4) for k, v in spec["dims"].items()}
    return spec


# ------------------------------------------------------------------------------------------------ kinematics
def T_of(R, p) -> np.ndarray:
    T = np.eye(4)
    T[:3, :3], T[:3, 3] = R, np.asarray(p, float)
    return T


def link_T(spec: dict, link: str, q: dict | None = None) -> np.ndarray:
    """Pose of a link frame in F at joint values q {joint: value} (missing = 0)."""
    if link == "base":
        return np.eye(4)
    j = next((jn for jn, v in spec["joints"].items() if v["link"] == link), None)
    o = np.asarray(spec["links"][link]["origin"], float)
    if j is None:
        return T_of(np.eye(3), o)
    J = spec["joints"][j]
    v = float((q or {}).get(j, 0.0))
    ax = np.asarray(J["axis"], float)
    if J["type"] == "prismatic":
        return T_of(np.eye(3), o + ax * v)
    return T_of(rot_axis(ax, v), o)


def box_T(b: dict) -> np.ndarray:
    return T_of(qmat(b["q"]) if "q" in b else np.eye(3), b["c"])


def boxes_world(spec: dict, T_WF, q: dict | None = None, skip_links=(), skip_prefix=()) -> dict:
    """{name: (centre, size, quat_wxyz)} of every collision box in the world (planner obstacles)."""
    out = {}
    T_WF = np.asarray(T_WF, float)
    items = [("base", b) for b in spec["base"]] + [(ln, b) for ln, L in spec["links"].items() for b in L["boxes"]]
    for ln, b in items:
        if not b.get("coll", True) or ln in skip_links or any(b["n"].startswith(p) for p in skip_prefix):
            continue
        T = T_WF @ link_T(spec, ln, q) @ box_T(b)
        out[f"fx_{ln}_{b['n']}"] = (T[:3, 3].copy(), list(b["s"]), _mat_quat(T[:3, :3]))
    return out


def handle_frame(spec: dict, link: str, T_WF, q: dict | None = None) -> dict:
    """World geometry of a link's handle at joint values q: grasp centre, outward normal, bar direction, knob mark."""
    h = spec["handles"][link]
    T = np.asarray(T_WF, float) @ link_T(spec, link, q)
    R = T[:3, :3]
    out = {"gc": T[:3, :3] @ np.asarray(h["gc"], float) + T[:3, 3], "fn": R @ np.asarray(h["fn"], float),
           "type": h["type"]}
    for k in ("length", "thick", "standoff", "ridge_h"):
        if h.get(k) is not None:
            out[k] = float(h[k])
    if h.get("along") in ("y", "z"):
        out["bar"] = R @ (np.array([0, 1.0, 0]) if h["along"] == "y" else np.array([0, 0, 1.0]))
    if h.get("ridge_along") is not None:
        out["bar"] = R @ np.asarray(h["ridge_along"], float)
    if h.get("mark") is not None:
        out["mark"] = R @ np.asarray(h["mark"], float) + T[:3, 3]
    return out


def joint_world(spec: dict, joint: str, T_WF) -> tuple:
    """(origin, axis) of a joint in the world."""
    J = spec["joints"][joint]
    T = np.asarray(T_WF, float)
    return T[:3, :3] @ np.asarray(J["origin"], float) + T[:3, 3], T[:3, :3] @ np.asarray(J["axis"], float)


def footprint(spec: dict, margin: float = 0.0) -> tuple:
    """(x0, x1, y0, y1) of the fixture body in F, the front extended by the handles / knobs (+ margin)."""
    d = spec["dims"]
    x0 = -0.08 if spec["family"] in ("drawer", "door", "slide") else -0.06
    return (x0 - margin, d["D"] + margin, -d["W"] / 2 - margin, d["W"] / 2 + margin)


# ------------------------------------------------------------------------------------------------ USDA
def _f(v):
    return "(" + ", ".join(f"{float(x):.6g}" for x in v) + ")"


def _usda_box(b: dict, ind: str) -> str:
    api = ' (\n' + ind + '    prepend apiSchemas = ["PhysicsCollisionAPI"]\n' + ind + ')' if b.get("coll", True) else ""
    ops = ['"xformOp:translate"']
    lines = [f"{ind}def Cube \"{b['n']}\"{api}", f"{ind}{{", f"{ind}    double size = 1",
             f"{ind}    double3 xformOp:translate = {_f(b['c'])}"]
    if "q" in b:
        lines.append(f"{ind}    quatf xformOp:orient = {_f(b['q'])}")
        ops.append('"xformOp:orient"')
    lines += [f"{ind}    float3 xformOp:scale = {_f(b['s'])}", f"{ind}    color3f[] primvars:displayColor = [{_f(b['col'])}]"]
    ops.append('"xformOp:scale"')
    lines += [f"{ind}    uniform token[] xformOpOrder = [{', '.join(ops)}]", f"{ind}}}"]
    return "\n".join(lines)


def usda(spec: dict) -> str:
    """The articulation as USDA text (prim /fixture: ArticulationRoot; base + moving links; joints)."""
    out = ['#usda 1.0', '(', '    defaultPrim = "fixture"', '    metersPerUnit = 1', '    upAxis = "Z"', ')', '',
           'def Xform "fixture"', '{']
    rb = '    prepend apiSchemas = ["PhysicsRigidBodyAPI", "PhysicsMassAPI"]'
    # the articulation root sits on the base body (Isaac Lab fix_root_link needs a rigid root: smoke 10-02)
    rb_root = '    prepend apiSchemas = ["PhysicsRigidBodyAPI", "PhysicsMassAPI", "PhysicsArticulationRootAPI", "PhysxArticulationAPI"]'

    def link(name, origin, boxes, mass):
        s = [f'    def Xform "{name}" (', "    " + (rb_root if name == "base" else rb), '    )', '    {',
             f'        float physics:mass = {float(mass):.4g}']
        if name == "base":
            s.append('        bool physxArticulation:enabledSelfCollisions = 0')
        s += [f'        double3 xformOp:translate = {_f(origin)}', '        uniform token[] xformOpOrder = ["xformOp:translate"]']
        s += [_usda_box(b, "        ") for b in boxes]
        s.append('    }')
        return "\n".join(s)
    out.append(link("base", (0, 0, 0), spec["base"], 4.0))
    for ln, L in spec["links"].items():
        out.append(link(ln, L["origin"], L["boxes"], L["mass"]))
    for jn, J in spec["joints"].items():
        typ = "PhysicsPrismaticJoint" if J["type"] == "prismatic" else "PhysicsRevoluteJoint"
        lo, hi = (J["lo"], J["hi"]) if J["type"] == "prismatic" else (math.degrees(J["lo"]), math.degrees(J["hi"]))
        q = quat_x_to(J["axis"])
        # an explicit drive (+ joint friction) on every joint: without DriveAPI the joints had no damping / spring in
        # PhysX (diag 10-02: buttons stayed pressed, a released door kept swinging at constant speed)
        dk = "linear" if J["type"] == "prismatic" else "angular"
        d = J["drive"]
        sc_ = 1.0 if J["type"] == "prismatic" else math.pi / 180.0  # angular drive gains are per degree
        out += [f'    def {typ} "{jn}" (', f'        prepend apiSchemas = ["PhysicsDriveAPI:{dk}", "PhysxJointAPI"]', '    )',
                '    {', f'        float drive:{dk}:physics:stiffness = {float(d["stiffness"]) * sc_:.6g}',
                f'        float drive:{dk}:physics:damping = {float(d["damping"]) * sc_:.6g}',
                f'        float drive:{dk}:physics:targetPosition = 0', f'        uniform token drive:{dk}:physics:type = "force"',
                f'        float physxJoint:jointFriction = {float(d.get("friction", 0.0)):.6g}',
                '        rel physics:body0 = </fixture/base>',
                f'        rel physics:body1 = </fixture/{J["link"]}>', '        uniform token physics:axis = "X"',
                f'        float physics:lowerLimit = {lo:.6g}', f'        float physics:upperLimit = {hi:.6g}',
                f'        point3f physics:localPos0 = {_f(J["origin"])}', f'        quatf physics:localRot0 = {_f(q)}',
                '        point3f physics:localPos1 = (0, 0, 0)', f'        quatf physics:localRot1 = {_f(q)}', '    }']
    out += ['}', '']
    return "\n".join(out)
