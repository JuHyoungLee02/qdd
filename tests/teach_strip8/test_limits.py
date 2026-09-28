"""user-log 171 (prereg_limits.md): (A) corruption injectors for the limit map - depth holes on the object region
(10-60 %), zed_mini noise scaled 1/2/4x, lighting / colour, partial occlusion of the target in the head image; all
deterministic per seed. (B) D depth rescue in the resolver: masked median -> neighbour fill -> memory -> remeasure."""
import numpy as np

from harvest.teach_strip8 import limits as LM

from astra_motion.fakeworld import look_at

TZ = 0.85
CAM = look_at((0.08, 0.02, 1.55), (0.45, -0.15, TZ), "head", 672, 376, 367.0)


def scene(box=(0.40, 0.47, -0.30, -0.23, 0.095)):
    iu, iv = np.meshgrid(np.arange(CAM.W) + 0.5, np.arange(CAM.H) + 0.5)
    d = np.stack([(iu - CAM.cx) / CAM.fx, (iv - CAM.cy) / CAM.fy, np.ones_like(iu)], -1)
    dw = d @ np.asarray(CAM.R).T
    t = np.asarray(CAM.t)
    s = (TZ - t[2]) / dw[..., 2]
    x0, x1, y0, y1, h = box
    s2 = (TZ + h - t[2]) / dw[..., 2]
    p2 = t + dw * s2[..., None]
    inb = (p2[..., 0] >= x0) & (p2[..., 0] <= x1) & (p2[..., 1] >= y0) & (p2[..., 1] <= y1)
    return np.where(inb, s2, s)


def test_object_mask_and_holes():
    d = scene()
    m = LM.object_mask(CAM, d, TZ, [0.435, -0.265], r=0.06)
    assert m.sum() > 200
    for f in (0.1, 0.3, 0.6):
        h = LM.depth_holes(d, m, f, seed=3)
        lost = (h[m] == 0).mean()
        assert abs(lost - f) < 0.03 and (h[~m] == d[~m]).all()
    assert np.array_equal(LM.depth_holes(d, m, 0.3, seed=3), LM.depth_holes(d, m, 0.3, seed=3))


def test_noise_light_occlusion():
    d = scene()
    rgb = np.full((CAM.H, CAM.W, 3), 120, np.uint8)
    n1 = LM.depth_noise(d, rgb, CAM.fx, 1, seed=0)
    n4 = LM.depth_noise(d, rgb, CAM.fx, 4, seed=0)
    ok = np.isfinite(n1) & np.isfinite(n4)
    assert np.nanstd((n4 - d)[ok]) > 3 * np.nanstd((n1 - d)[ok])
    for lv in LM.LIGHT_LEVELS:
        out = LM.lighting(rgb, lv, seed=1)
        assert out.dtype == np.uint8 and out.shape == rgb.shape and not np.array_equal(out, rgb)
    m = LM.object_mask(CAM, d, TZ, [0.435, -0.265], r=0.06)
    occ = LM.occlude(rgb, m, 0.6, seed=2)
    ys, xs = np.nonzero(m)
    box = occ[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    assert 0.4 < (box != 120).any(-1).mean() < 0.8


def test_rescue_steps():
    d = scene()
    m = LM.object_mask(CAM, d, TZ, [0.435, -0.265], r=0.06)
    ys, xs = np.nonzero(m)
    px = [float(xs.mean()), float(ys.mean())]
    pt = [px[0] / CAM.W * 1000, px[1] / CAM.H * 1000]
    good = LM.rescue_resolve(CAM, d, TZ, pt, tcp=[0.2, 0.3, 1.2], memory=None)
    assert good["kind"] == "object" and good["rescue"] == "none"
    holed = LM.depth_holes(d, m, 0.6, seed=4)
    r = LM.rescue_resolve(CAM, holed, TZ, pt, tcp=[0.2, 0.3, 1.2], memory=None)
    assert r["kind"] == "object" and r["rescue"] in ("masked_median", "fill")
    assert abs(r["top"] - (TZ + 0.095)) < 0.01 and np.hypot(r["xy"][0] - 0.435, r["xy"][1] + 0.265) < 0.02
    gone = LM.depth_holes(d, m, 1.0, seed=4)
    r2 = LM.rescue_resolve(CAM, gone, TZ, pt, tcp=[0.2, 0.3, 1.2], memory=d)
    assert r2["rescue"] == "memory" and r2["kind"] == "object"
    r3 = LM.rescue_resolve(CAM, gone, TZ, pt, tcp=[0.2, 0.3, 1.2], memory=None)
    assert r3["kind"] == "remeasure"
