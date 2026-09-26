"""MolmoAct visual trace labels (plan 2026-09-26-molmoact-r2-data Task 3; readiness M1, M5).

Scope after user-log 99 / canon §89 (MolmoAct transplant on REAL data with model labels): the core rules here --
molmo_subsample, to_u255 / from_u255, labels / labels_segments (trace ends at the release, nothing after it),
TRACE_RGB / palette / draw -- take any per-frame image points, e.g. Molmo2-ER gripper pointings on S-E2E head frames
(labels_segments: per-frame segment end, missing pointings allowed). The R2 helpers (release_frame from planner phases,
project_tcp, episode_trace, build) stay for the sim episodes but are not used for MolmoAct training data.

Trace (MolmoAct arXiv 2508.07917 §2.3 / allenai/molmoact processors.Trace.subsample_to_line): per frame t a 2-D
polyline of at most 5 points in 0..255 image coordinates -- p1 = the end-effector point now, the rest evenly spaced
future end-effector points up to the END frame (included). Points outside the image are dropped (MolmoAct drops failed
pointings). Translation to R2 (readiness M1, pitfall P83): the END frame is the RELEASE = the last frame of the `open`
phase, not the episode end (R2 episodes continue with a 22 cm retreat + done); frames after the release get no label.

End-effector point = the SIMULATOR fingertip midpoint recorded per frame (npz `tcp` = env.finger_mid(), table frame),
projected with the fixed R2 head camera (harvest.train.r2_ma2 constants, perception.geom convention). Not URDF FK:
readiness G-fk measured 9.5 mm between the two.

Overlay colour (M5): MolmoAct's cyan (0, 255, 255) collides with the dr distractor colour col_cyan; TRACE_RGB is the
colour with the largest minimum RGB distance to every R2 pool / object colour (grid search, 131), drawn with a 1 px dark
outline. CLI:
  python -m harvest.datagen.trace build --src ROOT --dst DST [--all]   (valid episodes; --all = every episode)
    -> DST/<variant>/<task>/<kind>/ep<seed>.trace.json and DST/traces.jsonl (one summary line per episode)
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os

import numpy as np

W_HEAD, H_HEAD = 672, 376
K_POINTS = 5
TRACE_RGB = (110, 255, 0)  # min RGB distance 131 to every pool / object colour (col_olive nearest)
OUTLINE_RGB = (0, 0, 0)
TRACE_VER = "trace5-release@v1"
PHASE_NAMES = ("approach", "descend", "close", "lift", "carry", "place_descend", "open", "retreat", "done", "fail")


# ------------------------------------------------------------------------------------------ MolmoAct trace
def molmo_subsample(points, k: int = K_POINTS, fallback=None) -> list:
    """processors.Trace.subsample_to_line: drop None, <= k points kept as is, else k evenly spaced (np.linspace
    int indices, first and last included); no valid point -> [fallback] or []."""
    valid = [p for p in points if p is not None]
    m = len(valid)
    if m == 0:
        return [fallback] if fallback is not None else []
    if m <= k:
        return list(valid)
    return [valid[j] for j in np.linspace(0, m - 1, num=k, dtype=int)]


def to_u255(u: float, v: float, W: int = W_HEAD, H: int = H_HEAD) -> list:
    """Continuous pixel coordinate -> MolmoAct 0..255 integers (inverse of its load_image pixel = q (W - 1) / 255)."""
    qu = int(round((u - 0.5) * 255.0 / (W - 1)))
    qv = int(round((v - 0.5) * 255.0 / (H - 1)))
    return [min(max(qu, 0), 255), min(max(qv, 0), 255)]


def from_u255(q, W: int = W_HEAD, H: int = H_HEAD) -> tuple:
    return q[0] * (W - 1) / 255.0 + 0.5, q[1] * (H - 1) / 255.0 + 0.5


def release_frame(phases) -> int | None:
    """Last frame of the `open` phase (= the frame before the first `retreat` frame); None without a release."""
    for k, p in enumerate(phases):
        if p == "retreat":
            return k - 1 if k > 0 and phases[k - 1] == "open" else None
    return None


def labels(uv, k_end: int, W: int = W_HEAD, H: int = H_HEAD, k: int = K_POINTS) -> list:
    """Per frame t <= k_end: the trace over frames t..k_end; frames after k_end: None."""
    pts = [to_u255(u, v, W, H) if (np.isfinite(u) and np.isfinite(v) and 0.0 <= u < W and 0.0 <= v < H) else None
           for u, v in np.asarray(uv, float)]
    end = pts[:k_end + 1]
    return [molmo_subsample(end[t:], k) if t <= k_end else None for t in range(len(pts))]


def labels_segments(uv, seg_end, W: int = W_HEAD, H: int = H_HEAD, k: int = K_POINTS) -> list:
    """Real data (pointing labels): per frame t the trace over frames t..seg_end[t] (its segment end = the next
    release); seg_end[t] None -> no label. uv[t] may be None (pointing failure) or outside the image (dropped)."""
    pts = []
    for p in uv:
        ok = p is not None and np.isfinite(p[0]) and np.isfinite(p[1]) and 0.0 <= p[0] < W and 0.0 <= p[1] < H
        pts.append(to_u255(p[0], p[1], W, H) if ok else None)
    out = []
    for t, e in enumerate(seg_end):
        if e is None:
            out.append(None)
            continue
        if e < t or e >= len(pts):
            raise ValueError(f"frame {t}: segment end {e} outside [{t}, {len(pts) - 1}]")
        out.append(molmo_subsample(pts[t:e + 1], k))
    return out


def project_tcp(tcp_table) -> tuple:
    """Table-frame points (N, 3) -> head-image (u, v) (N, 2) and depth (N,)."""
    from ..train.r2_ma2 import HEAD_K, HEAD_POS, HEAD_R, TABLE_TOP_Z
    P = np.atleast_2d(np.asarray(tcp_table, float)) + [0.0, 0.0, TABLE_TOP_Z]
    Pc = (P - HEAD_POS) @ HEAD_R
    d = Pc[:, 0]
    uv = np.stack([HEAD_K["cx"] - HEAD_K["fx"] * Pc[:, 1] / d, HEAD_K["cy"] - HEAD_K["fy"] * Pc[:, 2] / d], 1)
    return uv, d


# ------------------------------------------------------------------------------------------ colour (M5)
OBJECT_RGB = {"o3": (0.80, 0.08, 0.08), "o5": (0.10, 0.25, 0.85), "o8": (0.10, 0.65, 0.20), "o9": (0.90, 0.80, 0.10),
              "o10": (0.55, 0.20, 0.70), "o11": (0.85, 0.0, 0.65)}  # = scene.OBJ_GEOM colours (checked in a test)


def palette() -> dict:
    """{name: (r, g, b) 0..255}: every flat colour of both randomization pools (train = dr, test = random) and the
    task objects. Textured materials are not in it (checked on rendered frames instead)."""
    from ..sim.randomize import load_pools
    out = {}

    def walk(x, path=""):
        if isinstance(x, dict):
            if isinstance(x.get("color"), list):
                out[x.get("name", path)] = tuple(float(c) * 255 for c in x["color"])
            for kk, vv in x.items():
                walk(vv, f"{path}/{kk}")
        elif isinstance(x, list):
            for i, vv in enumerate(x):
                walk(vv, f"{path}[{i}]")

    walk(load_pools())
    out.update({k: tuple(c * 255 for c in v) for k, v in OBJECT_RGB.items()})
    return out


def min_palette_distance(rgb) -> tuple:
    """(min RGB distance, nearest palette name)."""
    pal = palette()
    d = {k: math.dist(rgb, v) for k, v in pal.items()}
    k = min(d, key=d.get)
    return d[k], k


def draw(img, trace255, rgb=TRACE_RGB, thickness: int = 2, outline: int = 1):
    """Copy of img (H, W, 3 uint8 RGB) with the trace drawn MolmoAct-style (0..255 -> pixel rint(q (W - 1) / 255),
    cv2.line LINE_AA, only for >= 2 points) in `rgb` over a dark line `outline` px wider on each side."""
    import cv2
    out = np.ascontiguousarray(np.array(img, copy=True))
    if trace255 is None or len(trace255) < 2:
        return out
    h, w = out.shape[:2]
    pts = np.rint(np.asarray(trace255, np.float32) * np.array([(w - 1) / 255.0, (h - 1) / 255.0], np.float32))
    pts = pts.astype(int)
    # dark outline crisp (LINE_8, so it stays dark), colour line anti-aliased on top (MolmoAct LINE_AA)
    # the AA colour line bleeds ~1 px each side, so the dark line is 2 px wider per side than the colour line
    for col, th, lt in ((OUTLINE_RGB, thickness + 4 * outline, cv2.LINE_8), (tuple(int(c) for c in rgb), thickness,
                                                                             cv2.LINE_AA)):
        if th <= 0 or (col == OUTLINE_RGB and outline <= 0):
            continue
        for i in range(len(pts) - 1):
            cv2.line(out, tuple(int(x) for x in pts[i]), tuple(int(x) for x in pts[i + 1]), col, thickness=th,
                     lineType=lt)
    return out


# ------------------------------------------------------------------------------------------ episodes
def place_xy_of(folder: str, seed: int, meta: dict, z) -> tuple:
    """Place target centre (world xy) at the release: the recorded object pose, or the layout for the visual-only
    marker o11 (not a physics body)."""
    place = meta.get("place")
    ids = [str(x) for x in z["obj_ids"]] if "obj_ids" in z else []
    if place in ids:
        row = np.asarray(z["obj_pose"][-1][ids.index(place)], float)
        return float(row[0]), float(row[1])
    from ..sim.tasks import layout_for
    lay = layout_for(seed, meta["task"], (meta.get("molmo") or {}).get("layout", "task"))
    return float(lay[place][0]), float(lay[place][1])


def episode_trace(folder: str, seed: int, place_xy=None) -> dict:
    """Trace record of one episode (release-cut labels for every frame + the end-point checks of G-trace-end)."""
    z = np.load(f"{folder}/ep{seed}.npz", allow_pickle=False)
    meta = json.load(open(f"{folder}/ep{seed}.meta.json", encoding="utf-8"))
    tcp = np.asarray(z["tcp"], float)
    phases = [PHASE_NAMES[int(i)] if 0 <= int(i) < len(PHASE_NAMES) else "?" for i in z["phase_id"]]
    k_rel = release_frame(phases)
    uv, depth = project_tcp(tcp)
    rec = {"ver": TRACE_VER, "seed": int(seed), "task": meta.get("task"), "variant": meta.get("variant"),
           "kind": meta.get("kind"), "split": meta.get("split"), "valid": bool(meta.get("valid_for_training")),
           "mode": (meta.get("molmo") or {}).get("mode", "default"), "ee_source": "sim_tcp",
           "n_frames": len(tcp), "k_release": k_rel, "end_rule": "release",
           "phase_at_end": phases[k_rel] if k_rel is not None else None,
           "uv": [[round(float(a), 2), round(float(b), 2)] for a, b in uv],
           "depth_m": [round(float(x), 4) for x in depth]}
    if k_rel is None:
        rec["trace255"] = None
        return rec
    rec["trace255"] = labels(uv, k_rel)
    if place_xy is None:
        place_xy = place_xy_of(folder, seed, meta, z)
    puv, _ = project_tcp([[place_xy[0], place_xy[1], 0.0]])  # place centre at table level
    rec["place_xy"] = [round(float(place_xy[0]), 5), round(float(place_xy[1]), 5)]
    rec["end_xy_to_place_cm"] = round(float(np.hypot(*(tcp[k_rel, :2] - np.asarray(place_xy)))) * 100, 3)
    rec["end_z_cm"] = round(float(tcp[k_rel, 2]) * 100, 2)
    rec["end_px_to_place"] = round(float(np.linalg.norm(uv[k_rel] - puv[0])), 1)
    rec["episode_end_xy_to_place_cm"] = round(float(np.hypot(*(tcp[-1, :2] - np.asarray(place_xy)))) * 100, 3)
    rec["frames_after_release"] = len(tcp) - 1 - k_rel
    rec["current_in_image"] = round(float(np.mean([(0 <= a < W_HEAD and 0 <= b < H_HEAD) for a, b in uv])), 4)
    return rec


def build(src: str, dst: str, include_invalid: bool = False) -> dict:
    metas = sorted(glob.glob(f"{src}/*/*/*/ep*.meta.json"))
    n, n_skip, summ = 0, 0, []
    os.makedirs(dst, exist_ok=True)
    with open(f"{dst}/traces.jsonl", "w", encoding="utf-8") as fs:
        for mp in metas:
            meta = json.load(open(mp, encoding="utf-8"))
            if not include_invalid and not meta.get("valid_for_training"):
                n_skip += 1
                continue
            folder = os.path.dirname(mp)
            seed = int(os.path.basename(mp)[2:-10])
            rec = episode_trace(folder, seed)
            rel = os.path.relpath(folder, src).replace("\\", "/")
            os.makedirs(f"{dst}/{rel}", exist_ok=True)
            with open(f"{dst}/{rel}/ep{seed}.trace.json", "w", encoding="utf-8") as f:
                json.dump(rec, f)
            fs.write(json.dumps({k: v for k, v in rec.items() if k not in ("uv", "depth_m", "trace255")}
                                | {"folder": rel}) + "\n")
            n += 1
    out = {"src": src, "dst": dst, "episodes": n, "skipped_invalid": n_skip, "ver": TRACE_VER}
    print("TRACE " + json.dumps(out), flush=True)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["build"])
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    ap.add_argument("--all", action="store_true", help="also invalid episodes")
    a = ap.parse_args(argv)
    build(a.src, a.dst, a.all)


if __name__ == "__main__":
    main()
