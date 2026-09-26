"""L8-D: the diversified L8 generator (docs/stage3/prereg_l8d.md; canon §97 supp 1, diversity_plan_2026-09-26.md §1).
Pure part: seed ranges and guards, the task / variant / height plan, the process buckets, and gate G-H arithmetic
(head-camera view band, IK reach band, verdict).

Seeds: TRAIN 30000-34999 (inside R2_TRAIN 10000-59999, clear of L8's 20000s), GATE 35000-35199 (gate G-H truth
episodes only), OOD 70000-70999 (protected; never trained; generation needs confirm_ood):
  ood_h 70000-70099  unseen table heights (E-PT / E-STRIP8 heights 0.78 0.82 0.88 0.92 + the outer gate heights)
  ood_o 70100-70299  unseen objects (phase 2/3 assets held out by name)
  ood_d 70300-70499  unseen distractor layouts / appearance (variant randx = the TEST_X pool, 3-4 distractors)
Heights: the table is a static collider, so one Isaac process = one (variant, table height). Train heights lie on a
1 cm grid strictly inside the gate range and at least OOD_GAP from every OOD-H height. The head pitch is fixed.
"""
from __future__ import annotations

import math

import numpy as np

TRAIN_SEEDS = range(30000, 35000)
GATE_SEEDS = range(35000, 35200)
OOD_SEEDS = range(70000, 71000)
OOD_SETS = {"ood_h": range(70000, 70100), "ood_o": range(70100, 70300), "ood_d": range(70300, 70500)}
SPLITS = ("train", "gate") + tuple(OOD_SETS)
PT_OOD_H = (0.78, 0.82, 0.88, 0.92)  # E-PT OOD-H (registered 0.82 / 0.88, change 2 0.78 / 0.92), reused by E-STRIP8
OOD_GAP = 0.015  # a train height is >= 1.5 cm from every OOD-H height
HEIGHT_CANDIDATES = (0.72, 0.74, 0.76, 0.78, 0.80, 0.82, 0.84, 0.85, 0.86, 0.88, 0.90, 0.92, 0.94, 0.96, 0.98)
PHASE1_TASKS = ("mug_tray", "bottle_tray", "mug_marker")
TASK_CUM = ((0.40, "mug_tray"), (0.70, "bottle_tray"), (1.00, "mug_marker"))
TRAIN_VARIANTS = ("standard", "drx")
STANDARD_SHARE = 1 / 3
CLEAN_SHARE = 0.25  # = L8
WS_Y = (-0.40, -0.06)  # = scene.WS_Y (the y band is not height dependent: the view limit is in x)
GATE_Y = (-0.40, -0.23, -0.06)
REACH_OK_MM = 8.0  # = executor REACH_TOL_M
VIEW_MARGIN_PX = 10
OBJ_TOP_MAX = 0.10  # tallest target (bottle 10 cm)
Z_NEED = (0.07, 0.24)  # TCP z above the table the truth plan uses: grasp / place (>= table + 7.7 cm) .. carry + 2 cm
GATE_MIN_W = 0.08
GATE_MIN_SUCCESS = 0.8


def _r(v, n=3):
    return round(float(v), n)


def check_seed(seed: int, split: str, confirm_ood: bool = False) -> int:
    s = int(seed)
    if split == "train" and s in TRAIN_SEEDS:
        return s
    if split == "gate" and s in GATE_SEEDS:
        return s
    if split in OOD_SETS:
        if not confirm_ood:
            raise ValueError(f"split {split} is a protected OOD set: generation needs confirm_ood (--confirm-ood)")
        if s in OOD_SETS[split]:
            return s
    raise ValueError(f"seed {s} is not a {split} seed (train {TRAIN_SEEDS.start}-{TRAIN_SEEDS.stop - 1}, gate "
                     f"{GATE_SEEDS.start}-{GATE_SEEDS.stop - 1}, OOD sets {dict((k, (r.start, r.stop - 1)) for k, r in OOD_SETS.items())})")


def task_of(seed: int) -> str:
    u = np.random.default_rng([int(seed), 21, 1]).random()
    return next(t for c, t in TASK_CUM if u < c)


def variant_of(seed: int) -> str:
    return "standard" if np.random.default_rng([int(seed), 21, 2]).random() < STANDARD_SHARE else "drx"


def heights_from_gate(lo: float, hi: float):
    """(train heights, outer OOD heights) from the gate range [lo, hi] (extreme passing candidates)."""
    lo, hi = _r(lo, 2), _r(hi, 2)
    ood = PT_OOD_H + (lo, hi)
    grid = [_r(lo + 0.01 * k, 2) for k in range(1, int(round((hi - lo) / 0.01)))]
    train = tuple(h for h in grid if all(abs(h - o) >= OOD_GAP - 1e-9 for o in ood))
    return train, (lo, hi)


def plan_train(n: int, heights, start: int = TRAIN_SEEDS.start) -> list:
    """n consecutive TRAIN seeds; heights round-robin over a fixed permutation (balanced); task / variant by seed."""
    heights = tuple(float(h) for h in heights)
    seeds = [start + i for i in range(n)]
    for s in seeds:
        check_seed(s, "train")
    perm = np.random.default_rng([21, 3, n]).permutation(n)
    out = []
    for i, s in enumerate(seeds):
        out.append({"seed": s, "split": "train", "task": task_of(s), "variant": variant_of(s),
                    "table_z": heights[int(perm[i]) % len(heights)]})
    return out


def buckets(plan: list) -> dict:
    """{(variant, table_z): [episodes]} = one Isaac process each."""
    out: dict = {}
    for e in plan:
        out.setdefault((e["variant"], e["table_z"]), []).append(e)
    return out


# ------------------------------------------------------------------------------------------------ gate G-H
def _head_cam():
    from ..train.r2_ma2 import HEAD_K, HEAD_POS, HEAD_R
    return HEAD_K, HEAD_POS, HEAD_R


def project(P, cam=None):
    """cam = (K, pos, R) in the r2_ma2 convention (R columns = camera forward / left / up in world) or a live
    probe camera dict {fx, fy, cx, cy, W, H, R (base_from_optical), t} (world_isaac.camera_pose convention)."""
    if isinstance(cam, dict):
        R, t = np.asarray(cam["R"], float), np.asarray(cam["t"], float)
        Pc = (np.atleast_2d(np.asarray(P, float)) - t) @ R  # optical x right, y down, z forward
        return np.stack([cam["cx"] + cam["fx"] * Pc[:, 0] / Pc[:, 2], cam["cy"] + cam["fy"] * Pc[:, 1] / Pc[:, 2]], 1)
    K, pos, R = cam or _head_cam()
    Pc = (np.atleast_2d(np.asarray(P, float)) - pos) @ R
    return np.stack([K["cx"] - K["fx"] * Pc[:, 1] / Pc[:, 0], K["cy"] - K["fy"] * Pc[:, 2] / Pc[:, 0]], 1)


def _wh(cam):
    if isinstance(cam, dict):
        return cam["W"], cam["H"]
    K = (cam or _head_cam())[0]
    return K["width"], K["height"]


def view_band(tz: float, cam=None, ys=GATE_Y, top=OBJ_TOP_MAX, margin=VIEW_MARGIN_PX, xs=None):
    """x band where an object's base centre and top centre (height `top`) at every y of ys project inside the head
    image with `margin` px (fixed head pitch). -> (x_lo, x_hi) or None."""
    W, H = _wh(cam)
    xs = np.round(np.arange(0.25, 0.805, 0.005), 3) if xs is None else np.asarray(xs, float)
    ok = []
    for x in xs:
        P = [[x, y, tz + dz] for y in ys for dz in (0.0, top)]
        uv = project(P, cam)
        ok.append(bool(np.all((uv[:, 0] >= margin) & (uv[:, 0] <= W - margin) & (uv[:, 1] >= margin)
                              & (uv[:, 1] <= H - margin))))
    return _run(xs, ok)


def _run(xs, ok):
    """Longest contiguous run of True -> (x_lo, x_hi) or None."""
    best, cur = None, None
    for x, g in zip(xs, ok):
        if g:
            cur = (cur[0], x) if cur else (x, x)
            if best is None or cur[1] - cur[0] > best[1] - best[0]:
                best = cur
        else:
            cur = None
    return None if best is None else (_r(best[0]), _r(best[1]))


def reach_band(xs, zs, err_mm, z_need, ok_mm: float = REACH_OK_MM):
    """err_mm[y, x, z] = settled TCP error of a top-down target (IK probe). x is reachable when every y and every
    probed z inside z_need = (z_lo, z_hi) (world) is within ok_mm. -> (x_lo, x_hi) (longest run) or None."""
    err = np.asarray(err_mm, float)
    zs = np.asarray(zs, float)
    zi = (zs >= z_need[0] - 1e-9) & (zs <= z_need[1] + 1e-9)
    ok = [bool(np.all(err[:, i, zi] <= ok_mm)) for i in range(len(xs))]
    return _run(list(xs), ok)


def gate_h(tz: float, view, reach, n_clean: int, n_success: int) -> dict:
    """Gate G-H for one height: ws x = view band ∩ reach band, width >= 8 cm and clean truth success >= 0.8."""
    out = {"table_z": _r(tz), "view": view, "reach": reach, "n_clean": int(n_clean), "n_success": int(n_success)}
    if view is None or reach is None:
        return dict(out, ws_x=None, width=0.0, **{"pass": False, "reason": "width"})
    x0, x1 = max(view[0], reach[0]), min(view[1], reach[1])
    w = max(0.0, x1 - x0)
    out.update(ws_x=(_r(x0), _r(x1)) if w > 0 else None, width=_r(w))
    if w < GATE_MIN_W - 1e-9:
        return dict(out, **{"pass": False, "reason": "width"})
    if n_clean <= 0 or n_success / n_clean < GATE_MIN_SUCCESS:
        return dict(out, **{"pass": False, "reason": "truth"})
    return dict(out, **{"pass": True, "reason": None})


def ws_of(ws_x) -> tuple:
    """Layout workspace box for scene.make_env(ws=...)."""
    return (tuple(ws_x), WS_Y)


def gate_range(results: list) -> tuple | None:
    """Contiguous passing heights around 0.85 -> (lo, hi)."""
    ok = {round(r["table_z"], 3): r["pass"] for r in results}
    hs = sorted(ok)
    if not ok.get(0.85):
        return None
    i = hs.index(0.85)
    lo = hi = i
    while lo - 1 >= 0 and ok[hs[lo - 1]]:
        lo -= 1
    while hi + 1 < len(hs) and ok[hs[hi + 1]]:
        hi += 1
    return hs[lo], hs[hi]


def dist_bin(n: int) -> str:
    return "0" if n == 0 else ("1-2" if n <= 2 else ("3-4" if n <= 4 else "5+"))


def height_bin(tz: float) -> str:
    d = round((tz - 0.85) * 100)
    return "low(<-3cm)" if d < -3 else ("mid(+-3cm)" if d <= 3 else "high(>+3cm)")


assert math.isclose(sum(1 for _ in PHASE1_TASKS), 3)
