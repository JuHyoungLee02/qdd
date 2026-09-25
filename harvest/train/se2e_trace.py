"""E-MA1, OPT-IN (docs/stage3/prereg_ma1.md; research molmoact_deepdive_2026-09-26 §4.1-§4.2, §6.1; canon §84).

MolmoAct-style end-effector traces on the S-E2E head camera, two factors on top of the motion-line samples (§83):
  A  aux: trace5@v1       auxiliary regression target (training only, never generated at run time): 5 points of the
                          active end effector in the head image, p1 = now, p2..p5 evenly spaced in time up to the next
                          gripper event (closed/open state change) or the episode end, capped at TRACE_CAP_S; image
                          coordinates in [0, 1]; a point outside the image or behind the camera is masked. The
                          existing AuxGeomHead gets 10 more regression outputs (se2e_trace_model); loss units =
                          coordinate / TRACE_SCALE (as AUX_REG_SCALE for metres), masked smooth-L1, lam_aux 0.1.
  O  layout D27v1+eetrace@v1   history overlay on the head image only: the active end effector at frames k-20..k
                          (10 Hz, 2 s, PAST ONLY) projected into the camera at k, 2 px polyline fading with age, a small
                          ring at the current point; drawn on the decoded current JPEG and saved again at q90. Training
                          drops the overlay (original frame) with p = OVERLAY_DROPOUT per sample (own RNG per
                          (seed, step)); evaluation always draws it.
Camera: URDF chain arm_base_link -> head_joint1 (pitch) -> head_joint2 (yaw) -> zed_joint -> ZED left optical frame
(the recorded cam_head = ZED Mini left rectified 672x376), nominal VGA intrinsics (canon §47: fx 367); RB2 rows carry
head_joint1/2 in the state, RB1 (16-D) does not -> RB1_HEAD fixed (= RB2 train-split median; RB2 heads barely move).
G0 (prereg §2) checks this projection against Molmo2-ER pointing; a failed check fits a 6-DoF correction in the
camera frame (fit_correction) that `project(..., corr=)` then applies.
Nothing here is read by the default training / runtime path (stageb_data / stageb_model / PROMPT_FILES untouched).
"""
from __future__ import annotations

import math
import random
import re
import xml.etree.ElementTree as ET

import numpy as np

from . import se2e_data as S
from . import stageb_data as D

AUX_VER = "trace5@v1"
OVERLAY_VER = "eetrace@v1"
LAYOUT_OVERLAY = D.CAMERA_LAYOUT + "+" + OVERLAY_VER  # "D27v1+eetrace@v1"
TRACE_POINTS = 5
TRACE_CAP_S = 3.0
TRACE_SCALE = 0.05  # [0, 1] image coordinate -> loss units (5 % of the image size = 1, like AUX_REG_SCALE's 5 cm)
HIST_STEPS = 20  # 2.0 s at 10 Hz
OVERLAY_DROPOUT = 0.3
OVERLAY_STYLE = {"rgb": [255, 32, 32], "width": 2, "alpha_new": 1.0, "alpha_old": 0.25, "ring_radius": 4,
                 "ring_width": 1, "min_z_m": 0.05, "jpeg_q": 90}
INTRINSICS = {"fx": 367.0, "fy": 367.0, "cx": 336.0, "cy": 188.0, "W": 672, "H": 376}
RB1_HEAD = (0.5492, 0.0)  # RB2 train split (16,612 rows): head_joint1 median 0.5492 (q05-q95 0.5492-0.5507), joint2 0
CAMERA_LINK = "zed_left_camera_optical_frame"
G0_MEDIAN_PX, G0_P90_PX = 12.0, 30.0
G0_MIN_VALID = 90  # of 120: fewer valid reference points -> G0 cannot be judged -> fail path
CMP_EPS = 1e-12


# ------------------------------------------------------------------------------------------ camera
def load_head_chain(urdf: str, base: str = "arm_base_link", link: str = CAMERA_LINK) -> list:
    """Joints from `base` to the head camera optical frame: [(type, xyz, R_origin, axis, name)]."""
    root = ET.fromstring(urdf) if urdf.lstrip().startswith("<") else ET.parse(urdf).getroot()
    by_child = {j.find("child").get("link"): j for j in root.findall("joint")}
    out = []
    while link != base:
        j = by_child.get(link)
        if j is None:
            raise ValueError(f"no joint chain from {base} to the head camera (stuck at {link})")
        o = j.find("origin")
        xyz = [float(v) for v in (o.get("xyz", "0 0 0") if o is not None else "0 0 0").split()]
        rpy = [float(v) for v in (o.get("rpy", "0 0 0") if o is not None else "0 0 0").split()]
        ax = j.find("axis")
        out.append((j.get("type"), np.array(xyz), S._rpy(*rpy), [float(v) for v in ax.get("xyz").split()]
                    if ax is not None else None, j.get("name")))
        link = j.find("parent").get("link")
    return out[::-1]


def head_camera(chain: list, q_head) -> tuple:
    """(R, t): camera optical frame in arm_base_link (columns of R = camera x right, y down, z forward)."""
    q = dict(zip(("head_joint1", "head_joint2"), [float(v) for v in q_head]))
    R, t = np.eye(3), np.zeros(3)
    for typ, xyz, Ro, axis, name in chain:
        t = t + R @ xyz
        R = R @ Ro
        if typ in ("revolute", "continuous"):
            R = R @ S._axis_rot(axis, np.array([q[name]]))[0]
    return R, t


def head_q(state_row, names) -> tuple:
    names = list(names)
    if "head_joint1" in names and "head_joint2" in names:
        return (float(state_row[names.index("head_joint1")]), float(state_row[names.index("head_joint2")]))
    return RB1_HEAD


def _so3(w) -> np.ndarray:
    th = float(np.linalg.norm(w))
    if th < 1e-12:
        return np.eye(3)
    return S._axis_rot(np.asarray(w, float) / th, np.array([th]))[0]


def project(cam, P, K=INTRINSICS, corr=None):
    """(uv [N, 2] pixels, z [N] depth m) of base-frame points P [N, 3]; corr = (wx, wy, wz, tx, ty, tz) applied in the
    camera frame (p_c' = R(w) p_c + t) -- the G0 extrinsic correction (None / zeros = nominal)."""
    R, t = cam
    pc = (np.asarray(P, float).reshape(-1, 3) - t) @ R
    if corr is not None:
        pc = pc @ _so3(corr[:3]).T + np.asarray(corr[3:], float)
    z = pc[:, 2]
    zs = np.where(np.abs(z) < 1e-9, 1e-9, z)
    uv = np.stack([K["fx"] * pc[:, 0] / zs + K["cx"], K["fy"] * pc[:, 1] / zs + K["cy"]], 1)
    return uv, z


def fit_correction(cams, P, uv, K=INTRINSICS, f_scale: float = 10.0, iters: int = 100) -> np.ndarray:
    """6-DoF camera-frame correction minimizing the robust (soft-L1, f_scale px) reprojection error of reference
    pixels uv [N, 2] of base-frame points P [N, 3] seen by cameras cams[i] (Levenberg-Marquardt, numeric Jacobian)."""
    P, uv = np.asarray(P, float), np.asarray(uv, float)

    def resid(x):
        return np.concatenate([project(c, p[None], K, corr=x)[0][0] - u for c, p, u in zip(cams, P, uv)])

    def cost(r):
        e2 = (r.reshape(-1, 2) ** 2).sum(1) / f_scale ** 2
        return float((2 * (np.sqrt(1 + e2) - 1)).sum())
    x, lam = np.zeros(6), 1e-3
    for _ in range(iters):
        r = resid(x)
        w = 1.0 / np.sqrt(np.sqrt(1 + (r.reshape(-1, 2) ** 2).sum(1) / f_scale ** 2))  # IRLS weights of soft-L1
        w = np.repeat(w, 2)
        J = np.stack([(resid(x + h) - r) / 1e-6 for h in np.eye(6) * 1e-6], 1)
        A, g = (J * w[:, None] ** 2).T @ J, (J * w[:, None] ** 2).T @ r
        c0 = cost(r)
        while True:
            dx = -np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-9), g)
            if cost(resid(x + dx)) < c0:
                x, lam = x + dx, max(lam / 3, 1e-9)
                break
            lam *= 4
            if lam > 1e9:
                return x
        if np.abs(dx).max() < 1e-10:
            break
    return x


# ------------------------------------------------------------------------------------------ trace5
def closed(g) -> np.ndarray:
    """Gripper closed/open state = the prompt's rule (se2e_data.context_text: joint value > GRIP_CLOSED)."""
    return np.asarray(g, float) > S.GRIP_CLOSED


def event_end(grip, k: int, fps: float) -> int:
    """Frame index where the trace ends: the first frame after k whose closed/open state differs from k's, else the
    episode end, capped at k + TRACE_CAP_S."""
    c = closed(grip)
    T = len(c)
    cap = min(T - 1, k + int(round(TRACE_CAP_S * fps)))
    for j in range(k + 1, cap + 1):
        if c[j] != c[k]:
            return j
    return cap


def trace5(ee, grip, k: int, cam, K=INTRINSICS, fps: float = 10.0, corr=None) -> dict:
    """{"uv": [u1, v1, ..., u5, v5] in [0, 1] (0 where masked), "mask": [5], "end": frame, "span_s"}."""
    e = event_end(grip, k, fps)
    ts = [k + i * (e - k) / (TRACE_POINTS - 1) for i in range(TRACE_POINTS)]
    P = np.stack([S.interp_at(ee, t) for t in ts])
    uv, z = project(cam, P, K, corr)
    x = uv / [K["W"], K["H"]]
    ok = (z > OVERLAY_STYLE["min_z_m"]) & (x >= 0).all(1) & (x <= 1).all(1)
    x = np.where(ok[:, None], x, 0.0)
    return {"uv": [float(v) for v in x.reshape(-1)], "mask": [int(v) for v in ok], "end": int(e),
            "span_s": round((e - k) / fps, 6)}


def trace_aux_vecs(s: dict):
    """stageb_data.aux_vecs of the sample + the 10 trace5 regression targets (TRACE_SCALE units) and masks."""
    r, rm, c, cm = D.aux_vecs(s["aux"])
    t = s.get("trace5")
    if t is None:
        tr, tm = np.zeros(2 * TRACE_POINTS, np.float32), np.zeros(2 * TRACE_POINTS, np.float32)
    else:
        m = np.repeat(np.asarray(t["mask"], np.float32), 2)
        tr = (np.asarray(t["uv"], np.float32) / TRACE_SCALE) * m
        tm = m
    return np.concatenate([r, tr]).astype(np.float32), np.concatenate([rm, tm]).astype(np.float32), c, cm


# ------------------------------------------------------------------------------------------ overlay
def history_frames(k: int, steps: int = HIST_STEPS) -> list:
    return list(range(max(0, k - steps), k + 1))


def render_overlay(img, uv, z, style=OVERLAY_STYLE):
    """Copy of the PIL image with the past path uv [n, 2] (oldest first, last = now) drawn: segment alpha falls
    linearly from alpha_new (newest) to alpha_old (oldest of HIST_STEPS), points with z <= min_z_m break the line,
    ring at the current point."""
    from PIL import Image, ImageDraw
    base = img.convert("RGBA")
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    rgb = tuple(style["rgb"])
    uv, z = np.asarray(uv, float), np.asarray(z, float)
    n = len(uv)
    ok = z > style["min_z_m"]
    for i in range(n - 1):  # segment i -> i + 1, age of its newer end = n - 2 - i frames
        if not (ok[i] and ok[i + 1]):
            continue
        age = n - 2 - i
        a = style["alpha_new"] - (style["alpha_new"] - style["alpha_old"]) * min(age, HIST_STEPS - 1) / (HIST_STEPS - 1)
        d.line([tuple(uv[i]), tuple(uv[i + 1])], fill=rgb + (int(round(255 * a)),), width=style["width"])
    if n and ok[-1]:
        r = style["ring_radius"]
        u, v = uv[-1]
        d.ellipse([u - r, v - r, u + r, v + r], outline=rgb + (255,), width=style["ring_width"])
    return Image.alpha_composite(base, layer).convert("RGB")


def _set_head(s: dict, path: str) -> dict:
    ims = [[lab, path] if i == 0 else [lab, p] for i, (lab, p) in enumerate(s["context"]["images"])]
    return {**s, "context": {**s["context"], "images": ims}, "items": [{**it, "images": ims} for it in s["items"]]}


def set_overlay(s: dict, on: bool) -> None:
    """In place: head image (entry 0) = the overlay frame (on) or the original frame (off)."""
    n = _set_head(s, s["overlay_head"]["on" if on else "off"])
    s["context"], s["items"] = n["context"], n["items"]


def overlay_dropout(batch, step: int, seed: int, p: float = OVERLAY_DROPOUT) -> list:
    """Training batch with each overlay sample's head image replaced by the original frame with probability p (own RNG
    per (seed, step); samples are not modified)."""
    if p <= 0:
        return list(batch)
    rng = random.Random(f"{OVERLAY_VER}:{seed}:{step}")
    out = []
    for s in batch:
        if "overlay_head" in s and rng.random() < p:
            out.append(_set_head(s, s["overlay_head"]["off"]))
        else:
            out.append(s)
    return out


# ------------------------------------------------------------------------------------------ G0
def g0_select(rows, n_per: int = 30, seed: int = 0) -> list:
    """prereg §2: per (source, active arm) n_per val-split, non-bimanual rows with a head frame: n_per distinct
    episodes chosen at random (seed), one random row each; fewer episodes -> the rest from other rows of the chosen
    episodes. Order: RB1-left, RB1-right, RB2-left, RB2-right, each in selection order."""
    rng = random.Random(seed)
    out = []
    for kind in ("RB1", "RB2"):
        for arm in ("left", "right"):
            cand = sorted((r for r in rows if r["kind"] == kind and r["arm"] == arm and r["split"] == "val"
                           and not r.get("bimanual") and "cam_head" in (r.get("images") or {})),
                          key=lambda r: (r["seed"], r["k"]))
            by = {}
            for r in cand:
                by.setdefault(r["seed"], []).append(r)
            eps = sorted(by)
            chosen = rng.sample(eps, min(n_per, len(eps)))
            pick = [rng.choice(by[e]) for e in chosen]
            rest = [r for e in chosen for r in by[e] if r not in pick]
            pick += rng.sample(rest, min(n_per - len(pick), len(rest)))
            out += pick
    return out


def g0_cal_half(sel) -> list:
    """Calibration flags of the PnP fallback: the first half of every (source, arm) group in selection order."""
    seen, out = {}, []
    size = {}
    for r in sel:
        size[(r["kind"], r["arm"])] = size.get((r["kind"], r["arm"]), 0) + 1
    for r in sel:
        g = (r["kind"], r["arm"])
        seen[g] = seen.get(g, 0) + 1
        out.append(seen[g] <= size[g] // 2)
    return out


def g0_stats(err) -> dict:
    e = np.asarray(err, float)
    return {"n": int(len(e)), "median": float(np.median(e)) if len(e) else None,
            "p90": float(np.quantile(e, 0.9)) if len(e) else None, "mean": float(e.mean()) if len(e) else None,
            "max": float(e.max()) if len(e) else None}


def _le(x, t):
    return x <= t + CMP_EPS * max(1.0, abs(t))


def g0_pass(st: dict) -> bool:
    return st["median"] is not None and _le(st["median"], G0_MEDIAN_PX) and _le(st["p90"], G0_P90_PX)


_COORD = re.compile(r"<(?:points|tracks).*? coords=\"([0-9\t:;, .]+)\"/?>")
_FRAME = re.compile(r"(?:^|\t|:|,|;)([0-9\.]+) ([0-9\. ]+)")
_POINTS = re.compile(r"([0-9]+) ([0-9]{3,4}) ([0-9]{3,4})")


def parse_point(text: str, W: int, H: int):
    """First point of a Molmo2 answer in pixels (the model card's parser: coords scaled by 1000), None if none."""
    for coord in _COORD.finditer(text):
        for grp in _FRAME.finditer(coord.group(1)):
            for p in _POINTS.finditer(grp.group(2)):
                x, y = float(p.group(2)) / 1000 * W, float(p.group(3)) / 1000 * H
                if 0 <= x <= W and 0 <= y <= H:
                    return (x, y)
    return None


def pixel_error(a, b) -> float:
    return float(math.hypot(a[0] - b[0], a[1] - b[1]))
