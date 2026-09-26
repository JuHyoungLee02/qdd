"""Stereo-like depth noise for the L8-X depth track (track D, user-log 146): perfect simulator z-depth -> a depth map
with the error structure of a passive / active stereo camera, applied offline to the saved head_depth.npz (the
collection keeps the perfect depth; the noisy copy is a build-time variant, deterministic per call).

Model (every constant below is either stereo geometry or marked [assumption]):
  1. Range noise: stereo triangulation z = f B / d, so a disparity error sigma_d (px) gives
       sigma_z = z^2 * sigma_d / (f * B)                                     (standard stereo error propagation)
     f = the camera's fx in px (from cams.json), B = the stereo baseline.
  2. Occlusion holes: a left-reference pixel whose right-image position x - d(x) is reached or passed by a nearer
     pixel to its right is not seen by the right camera -> invalid (NaN). Pure geometry of a rectified pair.
  3. Low-texture holes: where the RGB image has almost no local contrast, block matching fails -> invalid with
     probability p_lowtex [assumption: threshold and probability are not published; chosen to remove a fraction of
     flat, uniform surfaces, e.g. plain table tops].
  4. Range limits: z outside [z_min, z_max] -> invalid.
Presets (baselines from the vendors' published specifications; sub-pixel noise and texture rules are assumptions):
  zed_mini  B = 0.063 m (Stereolabs ZED Mini specification: 63 mm baseline), sigma_d = 0.2 px [assumption],
            z range 0.1-15 m (ZED Mini specification: 0.1-15 m) [assumption for our 672 x 376 mode]
  d405      B = 0.018 m (Intel RealSense D405 datasheet: 18 mm baseline), sigma_d = 0.08 px [assumption],
            z range 0.07-0.5 m (D405 ideal range 7-50 cm per Intel) [assumption for the far limit]
The head camera of our robot is the ZED Mini (left eye, 672 x 376, fx 367 px); the D405 preset is for the wrist
camera (its depth is not saved by the collection yet). Pure numpy."""
from __future__ import annotations

import numpy as np

PRESETS = {
    "zed_mini": {"baseline_m": 0.063, "sigma_d_px": 0.2, "z_min": 0.1, "z_max": 15.0, "lowtex_std": 2.0,
                 "p_lowtex": 0.5, "lowtex_win": 7},
    "d405": {"baseline_m": 0.018, "sigma_d_px": 0.08, "z_min": 0.07, "z_max": 0.5, "lowtex_std": 2.0,
             "p_lowtex": 0.2, "lowtex_win": 7},
}
ASSUMPTIONS = ("sigma_d_px", "lowtex_std", "p_lowtex", "lowtex_win", "z_max (zed_mini at 672x376)", "z_max (d405)")


def sigma_z(z, fx: float, baseline_m: float, sigma_d_px: float):
    return np.asarray(z, float) ** 2 * sigma_d_px / (fx * baseline_m)


def occlusion_mask(z: np.ndarray, fx: float, baseline_m: float) -> np.ndarray:
    """True where a left-reference pixel is occluded in the right image (rectified pair, right camera at +B along
    image x): its right-image column x - d(x) is >= that of some pixel to its right with a larger disparity."""
    zz = np.where(np.isfinite(z) & (z > 0), z, np.inf)
    d = fx * baseline_m / zz
    xs = np.arange(z.shape[1])[None, :]
    xr = xs - d
    # suffix minimum of xr from the right, excluding the pixel itself
    suf = np.minimum.accumulate(xr[:, ::-1], axis=1)[:, ::-1]
    nxt = np.concatenate([suf[:, 1:], np.full((z.shape[0], 1), np.inf)], axis=1)
    return xr >= nxt


def _local_std(gray: np.ndarray, win: int) -> np.ndarray:
    k = win // 2
    p = np.pad(gray.astype(float), k, mode="edge")
    c1 = np.cumsum(np.cumsum(p, 0), 1)
    c2 = np.cumsum(np.cumsum(p * p, 0), 1)
    c1 = np.pad(c1, ((1, 0), (1, 0)))
    c2 = np.pad(c2, ((1, 0), (1, 0)))
    H, W = gray.shape
    s1 = c1[win:win + H, win:win + W] - c1[:H, win:win + W] - c1[win:win + H, :W] + c1[:H, :W]
    s2 = c2[win:win + H, win:win + W] - c2[:H, win:win + W] - c2[win:win + H, :W] + c2[:H, :W]
    n = win * win
    return np.sqrt(np.maximum(s2 / n - (s1 / n) ** 2, 0.0))


def stereo_noise(depth: np.ndarray, rgb: np.ndarray | None, fx: float, preset: str = "zed_mini", seed=0,
                 **over) -> tuple:
    """-> (noisy depth with NaN holes, info {preset params, fractions of each hole kind})."""
    p = dict(PRESETS[preset], **over)
    rng = np.random.default_rng(seed)
    z = np.asarray(depth, float)
    valid = np.isfinite(z) & (z > 0)
    out = z + rng.standard_normal(z.shape) * sigma_z(np.where(valid, z, 0.0), fx, p["baseline_m"], p["sigma_d_px"])
    occ = occlusion_mask(z, fx, p["baseline_m"]) & valid
    rng_mask = valid & ((z < p["z_min"]) | (z > p["z_max"]))
    low = np.zeros_like(valid)
    if rgb is not None:
        gray = np.asarray(rgb, float)[..., :3].mean(-1)
        flat = _local_std(gray, int(p["lowtex_win"])) < p["lowtex_std"]
        low = valid & flat & (rng.random(z.shape) < p["p_lowtex"])
    bad = ~valid | occ | rng_mask | low
    out = np.where(bad, np.nan, out).astype(np.float32)
    n = max(int(valid.sum()), 1)
    info = {"preset": preset, "params": p, "frac_occluded": round(float(occ.sum()) / n, 5),
            "frac_lowtex": round(float(low.sum()) / n, 5), "frac_range": round(float(rng_mask.sum()) / n, 5),
            "frac_invalid": round(float(bad.sum()) / z.size, 5)}
    return out, info
