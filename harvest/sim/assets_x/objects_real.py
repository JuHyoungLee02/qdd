"""Real-object descriptors and the name check (pure numpy; L8-X real objects, user-log 160).

Input per object: world-frame vertices (z up, metres) in its resting pose, optional per-vertex RGB (texture samples)
and the name tokens of its source (GSO model name, THOR asset name, YCB name).
Output: size (height, grasp width = the minimal horizontal caliper, length), shape descriptors (handle score,
circularity, boxiness, sphericity), a colour word, and name_check: the noun the source name claims vs what the
geometry supports; a claim the shape contradicts is renamed (a "mug" without a handle -> "cup"; a "cup" with a
handle -> "mug"; a "can" / "bottle" that is not round -> "container"; a "ball" that is not round -> "toy"; a "box"
that is round -> "container"). The final task name is "<size> <colour> <noun>" with the size word only when the
object is in the lower / upper third of its noun's volumes (size_words).
"""
from __future__ import annotations

import math
import re

import numpy as np

NOUNS = [  # (keywords in the source name, noun) -- first match wins; name tokens before category tokens
    (("scissors", "screwdriver", "knife", "blade", "razor"), "SKIP"),  # sharp: never a task object
    (("mug",), "mug"), (("cup", "tumbler"), "cup"), (("bowl", "ramekin"), "bowl"), (("plate", "dish", "saucer"), "plate"),
    (("planter", "plant"), "planter"), (("can",), "can"), (("bottle", "jug"), "bottle"), (("jar",), "jar"),
    (("shoe", "sneaker", "ballet", "flats", "loafer", "slipper", "sandal", "boot", "moccasin", "clog"), "shoe"),
    (("moisturizer", "cream", "lipstick", "bronzer", "serum", "lotion"), "cosmetic"),
    (("caplets", "gels", "tablets", "vitamin", "capsules"), "medicine box"),
    (("cartridge",), "cartridge"), (("nintendo",), "game cartridge"),
    (("box", "carton", "pack", "kit", "sheets", "candy", "chocolate", "raisinets", "fillets"), "box"),
    (("shoe", "sneaker", "boot", "sandal", "slipper", "loafer", "oxford", "runner", "trainer", "ballet", "flats",
      "heel", "moccasin", "clog"), "shoe"),
    (("ball",), "ball"), (("block", "brick", "cube"), "block"), (("book",), "book"),
    (("railway", "train", "engine", "bus", "boat", "racer", "truck", "car", "crew", "roller"), "toy vehicle"),
    (("sheep", "ladybug", "crocodile", "rhino", "eagle", "bull", "unicorn", "whale", "snail", "bird", "turtle",
      "dinosaur", "animal", "horse", "dog", "cat", "friends"), "toy animal"),
    (("toy", "figure", "doll", "puzzle", "stack", "ring", "rattle", "maraca", "whistle", "bead"), "toy"),
    (("mouse",), "computer mouse"), (("apple",), "apple"), (("tomato",), "tomato"), (("potato",), "potato"),
    (("egg",), "egg"), (("bread",), "bread"), (("spray",), "spray bottle"), (("soap",), "soap"),
    (("shaker",), "shaker"), (("kettle",), "kettle"), (("pot",), "pot"), (("pan",), "pan"), (("hammer",), "hammer"),
    (("spatula",), "spatula"), (("speaker",), "speaker"), (("cable",), "cable"), (("usb",), "usb stick"),
    (("tracker", "band"), "wristband"), (("tape",), "tape measure"), (("card", "creditcard"), "card"),
    (("remote",), "remote"), (("phone", "cellphone"), "phone"), (("sponge",), "sponge"), (("candle",), "candle"),
    (("lego",), "toy brick"), (("hat", "cap"), "hat"), (("bag", "purse", "backpack"), "bag"), (("case",), "case"),
]
ROUND_MIN = 0.88  # circularity of a round body
ROUND_NOUNS = ("can", "bottle", "jar", "cup", "mug", "bowl", "ball", "candle", "shaker")
HANDLE_RATIO = 1.30  # a handle: vertices at mid height reaching >= 1.3 x the body radius on one side


def tokens(name: str) -> list:
    return [t for t in re.split(r"[^a-z]+", name.lower()) if t]


def claimed_noun(name: str, category: str = "") -> str | None:
    """Noun from the source name; the (coarser, sometimes wrong) source category only when the name has none."""
    for toks in (tokens(name), tokens(category)):
        for keys, noun in NOUNS:
            if any(t == k or (t.startswith(k) and len(k) >= 4) for t in toks for k in keys):
                return noun
    return None


def min_caliper(xy: np.ndarray, steps: int = 90):
    """(min width, max width, angle) of 2-D points over directions 0..180 deg (fingers close across the min)."""
    best = (np.inf, 0.0, 0.0)
    wmax = 0.0
    for k in range(steps):
        a = math.pi * k / steps
        d = xy @ np.array([math.cos(a), math.sin(a)])
        w = float(d.max() - d.min())
        wmax = max(wmax, w)
        if w < best[0]:
            best = (w, 0.0, a)
    return best[0], wmax, best[2]


def descriptors(V: np.ndarray) -> dict:
    V = np.asarray(V, float)
    lo, hi = V.min(0), V.max(0)
    h = float(hi[2] - lo[2])
    w, L, ang = min_caliper(V[:, :2])
    c = (lo[:2] + hi[:2]) / 2
    mid = V[(V[:, 2] > lo[2] + 0.3 * h) & (V[:, 2] < lo[2] + 0.7 * h)]
    handle, circ = 0.0, 0.0
    if len(mid) > 20:
        r = np.linalg.norm(mid[:, :2] - np.median(mid[:, :2], axis=0), axis=1)
        body = np.percentile(r, 50)
        handle = float(np.percentile(r, 99.5) / max(body, 1e-6))
        # circularity: min / max caliper of the mid-height slice (a round body ~1, a square box 0.71)
        wmin, wmax, _ = min_caliper(mid[:, :2], 60)
        circ = float(wmin / max(wmax, 1e-6))
        circ = float(1.0 - (np.percentile(r, 90) - np.percentile(r, 10)) / max(body, 1e-6))
    # sphericity: extents close to each other and radius from the centre near constant
    ctr = (lo + hi) / 2
    R = np.linalg.norm(V - ctr, axis=1)
    sph = float(1.0 - R.std() / max(R.mean(), 1e-6)) if min(h, w) > 0.7 * max(h, L) else 0.0
    # boxiness: share of vertices within 4 mm of a face of the minimal-caliper box (a box ~1, a cylinder less)
    ca, sa = math.cos(ang), math.sin(ang)
    u, v = V[:, :2] @ np.array([ca, sa]), V[:, :2] @ np.array([-sa, ca])
    near = ((np.abs(u - u.min()) < 0.004) | (np.abs(u - u.max()) < 0.004) | (np.abs(v - v.min()) < 0.004)
            | (np.abs(v - v.max()) < 0.004) | (np.abs(V[:, 2] - lo[2]) < 0.004) | (np.abs(V[:, 2] - hi[2]) < 0.004))
    box = float(near.mean())
    return {"height": round(h, 4), "grasp_width": round(w, 4), "length": round(L, 4), "grasp_yaw": round(ang, 4),
            "boxiness": round(box, 3),
            "caliper_centre": [round(float((u.min() + u.max()) / 2), 4), round(float((v.min() + v.max()) / 2), 4)],
            "handle_ratio": round(handle, 3), "circularity": round(circ, 3), "sphericity": round(sph, 3),
            "footprint_r": round(float(math.hypot(w, L) / 2), 4), "centre_xy": [round(float(v), 4) for v in c],
            "bottom_z": round(float(lo[2]), 4)}


def colour_word(rgb) -> str | None:
    if rgb is None:
        return None
    r, g, b = (float(v) / (255.0 if max(rgb) > 1.0 else 1.0) for v in rgb)
    mx, mn = max(r, g, b), min(r, g, b)
    v, s = mx, (mx - mn) / max(mx, 1e-6)
    if v < 0.18:
        return "black"
    if s < 0.18:
        return "white" if v > 0.78 else "gray"
    if mx == r:
        hue = (60 * ((g - b) / max(mx - mn, 1e-6))) % 360
    elif mx == g:
        hue = 60 * ((b - r) / max(mx - mn, 1e-6)) + 120
    else:
        hue = 60 * ((r - g) / max(mx - mn, 1e-6)) + 240
    if (hue < 20 or hue >= 340) and v < 0.55 and s < 0.75:
        return "brown"
    for lim, word in ((20, "red"), (45, "orange"), (70, "yellow"), (165, "green"), (255, "blue"), (290, "purple"),
                      (340, "pink"), (360, "red")):
        if hue < lim:
            return "brown" if word == "orange" and v < 0.6 else word
    return None


def name_check(claim: str | None, d: dict) -> dict:
    """-> {claimed, noun, renamed, reasons}: geometry must support the claimed noun."""
    reasons, noun = [], claim
    round_ = d["circularity"] >= ROUND_MIN
    handle = d["handle_ratio"] >= HANDLE_RATIO
    if claim == "mug" and not handle:
        noun, reasons = "cup", ["mug without a handle (handle ratio %.2f)" % d["handle_ratio"]]
    elif claim == "cup" and handle:
        noun, reasons = "mug", ["cup with a handle (handle ratio %.2f)" % d["handle_ratio"]]
    elif claim in ("can", "bottle", "jar", "candle", "shaker") and not round_:
        noun, reasons = "container", [f"{claim} not round (circularity {d['circularity']:.2f})"]
    elif claim == "ball" and d["sphericity"] < 0.8:
        noun, reasons = "toy", ["ball not spherical (sphericity %.2f)" % d["sphericity"]]
    elif claim == "box" and round_ and d["grasp_width"] > 0.6 * d["length"]:
        noun, reasons = "container", ["box is round (circularity %.2f)" % d["circularity"]]
    elif claim is None:
        noun = ("box" if d.get("boxiness", 0) >= 0.85 else
                "cup" if round_ and not handle and d["height"] > d["grasp_width"] else "object")
        reasons = ["no noun in the source name: from shape"]
    return {"claimed": claim, "noun": noun, "renamed": noun != claim, "reasons": reasons}


def size_words(objs: dict) -> dict:
    """{id: "small" | "large" | None} by volume tertiles within each noun (needs >= 3 objects of the noun)."""
    by = {}
    for k, o in objs.items():
        by.setdefault(o["noun"], []).append((o["height"] * o["grasp_width"] * o["length"], k))
    out = {}
    for noun, rows in by.items():
        rows.sort()
        n = len(rows)
        for i, (_, k) in enumerate(rows):
            out[k] = None if n < 3 else ("small" if i < n / 3 else ("large" if i >= 2 * n / 3 else None))
    return out


def task_name(o: dict, size: str | None) -> str:
    return " ".join(w for w in (size, o.get("colour"), o["noun"]) if w)


def sample_surface(V, F, n: int = 20000, seed: int = 0) -> np.ndarray:
    """Area-weighted points on the triangle mesh (V, F): scanned meshes put few vertices on smooth sides, so the
    shape descriptors use surface samples, not vertices."""
    V, F = np.asarray(V, float), np.asarray(F, int)
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    w = np.linalg.norm(np.cross(b - a, c - a), axis=1)
    if w.sum() <= 0:
        return V
    rng = np.random.default_rng(seed)
    t = rng.choice(len(F), size=n, p=w / w.sum())
    u, v = rng.random(n), rng.random(n)
    flip = u + v > 1
    u[flip], v[flip] = 1 - u[flip], 1 - v[flip]
    return np.concatenate([V, a[t] + u[:, None] * (b[t] - a[t]) + v[:, None] * (c[t] - a[t])])


def canonical(V, d: dict):
    """Vertices in the canonical frame: turned by -grasp_yaw about the root z axis (the narrow side along x), the
    caliper box centre at x = y = 0 and the bottom at z = 0 (= objv canonical pose: the upright bbox centre, x narrow)."""
    a = d["grasp_yaw"]
    c, s = math.cos(a), math.sin(a)
    V = np.asarray(V, float)
    u = V[:, 0] * c + V[:, 1] * s
    v = -V[:, 0] * s + V[:, 1] * c
    uc, vc = d["caliper_centre"]
    return np.stack([u - uc, v - vc, V[:, 2] - d["bottom_z"]], 1)


def top_surface(Vc, F, d: dict):
    """The open support surface at the top of the object (canonical frame) or None: its box and height, for
    stacking something on it (top within 1.5 cm of the object height, at least 5 x 5 cm)."""
    from .surfaces import mesh_support_surfaces
    try:
        S = mesh_support_surfaces(Vc, F, min_area=0.0025, min_side=0.05)
    except Exception:  # noqa: BLE001
        return None
    top = [s for s in S if s["covered_above"] is None and s["top_z"] >= d["height"] - 0.015]
    if not top:
        return None
    s = max(top, key=lambda q: q["area"])
    return {"top_z": round(float(s["top_z"]), 4), "box": [[round(float(x), 4) for x in s["xy_box"][0]],
                                                          [round(float(x), 4) for x in s["xy_box"][1]]],
            "area": round(float(s["area"]), 4)}
