"""E3-ST offline stereo stability (plan Task 16).

Pipeline per episode (pod, GPU):
  left/right head frames -> Fast-FoundationStereo disparity -> depth z = fx*B/d (ZED Mini VGA fx 367, B=63 mm)
  -> Grounding DINO boxes from task-text nouns on the first frame with detections
  -> SAM 2.1 video propagation (masks, stable object ids)
  -> centroid_3d per object per frame -> stability (mm) + T1 predicates near/above -> flip_rate.

Usage (pod):
  CUDA_VISIBLE_DEVICES=1 python -m harvest.cli_e3st run --out /data/harvest/out/e3st
  python -m harvest.cli_e3st aggregate --out /data/harvest/out/e3st

SAM 3.1 variant (text prompt -> dense video tracking, replaces Grounding DINO + SAM 2.1). FFS and SAM 3.1
need different torch builds, so the disparities are cached first (venv_e3st), then segmented (venv_sam3):
  python -m harvest.cli_e3st depth --depth-cache /data/harvest/out/e3st_disp            # venv_e3st
  python -m harvest.cli_e3st run --seg sam31 --depth-cache /data/harvest/out/e3st_disp \
      --out /data/harvest/out/e3st_sam31 --ref-out /data/harvest/out/e3st         # venv_sam3

--fx (default 367 = ZED Mini VGA 672x376, HFOV 85 deg, canon §47; the first runs used 272.1 = 102 deg sensor-max
figure, reproducible with --fx 272.1). --mask-cache stores the segmentation per episode, so a rerun with another
fx reuses the masks and only redoes depth/3D/metrics.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import types

import numpy as np

from harvest.stereo.data import DEFAULT_ROOT, load_pairs
from harvest.stereo.pipeline import (
    above, centroid_3d, disparity_to_depth, fit_plane, flip_rate, intrinsics_from_fx, near_update, rank_tracks,
    stability,
)

MODELS = os.environ.get("E3ST_MODELS", "/data/harvest/models")
SRC = os.environ.get("E3ST_SRC", "/data/harvest/src")
FFS_CKPT = f"{MODELS}/ffs/weights/23-36-37/model_best_bp2_serialize.pth"
SAM2_CKPT = f"{MODELS}/sam2/sam2.1_hiera_large.pt"
SAM2_CFG = "configs/sam2.1/sam2.1_hiera_l.yaml"
GDINO = f"{MODELS}/gdino-base"
SAM31_CKPT = f"{MODELS}/sam3.1/sam3.1_multiplex.pt"

BASELINE_M = 0.063   # ZED Mini nominal [assumption]
HEAD_FX = 367.0      # ZED Mini VGA 672x376 mode, HFOV 85 deg (humanoid-challenge-env FFW_SG2_REAL_cameras.py; canon §47)
ZNEAR, ZFAR = 0.1, 9.0
MIN_AREA = 100
STATIC_PX = 1.0
STATIC_AREA = 0.05

T1 = "ROBOTIS/Task_0001_CoffeeClassification_lerobot"
T2 = "ROBOTIS/Task_0002_OrderPicking_lerobot"

T2_NOUNS = {
    "black wrench": "wrench", "yellow paint brush": "paint brush", "yellow roller": "paint roller",
    "red screwdriver": "screwdriver", "tool with the wooden handle": "tool with wooden handle",
    "red glue tube": "glue tube", "yellow pliers": "pliers", "blue scissors": "scissors",
    "red colored gloves": "gloves",
}


def prompts_for(repo: str, task_text: str):
    """[(category, text_prompt, max_instances)] from task-text nouns."""
    if repo == T1:  # "Place bottles in color-matching boxes"
        return [("bottle", "bottle", 4), ("box", "box", 4)]
    for k, noun in T2_NOUNS.items():  # "Put the <obj> into the crate."
        if k in task_text:
            return [("object", k, 1), ("crate", "crate", 1)]  # colour+noun phrase from the task text
    raise ValueError(task_text)


# ------------------------------------------------------------------ models

class FFS:
    def __init__(self, valid_iters=8, max_disp=192):
        import torch
        sys.modules.setdefault("open3d", types.ModuleType("open3d"))  # Utils imports open3d (only for point clouds)
        sys.path.insert(0, f"{SRC}/Fast-FoundationStereo")
        # No C compiler on the pod -> triton kernels cannot build; hide triton while importing `core`
        # so submodule.py takes its `triton = None` branch (we use the pure-pytorch GWC volume path).
        saved = {k: sys.modules.get(k) for k in ("triton", "triton.language")}
        sys.modules["triton"] = None
        sys.modules["triton.language"] = None
        try:
            import core.foundation_stereo  # noqa: F401
            import core.submodule  # noqa: F401
            from core.utils.utils import InputPadder  # noqa
        finally:
            for k, v in saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
        self.torch, self.InputPadder = torch, InputPadder
        torch.autograd.set_grad_enabled(False)
        self.model = torch.load(FFS_CKPT, map_location="cpu", weights_only=False)
        self.model.args.valid_iters = valid_iters
        self.model.args.max_disp = max_disp
        self.model.cuda().eval()
        self.iters = valid_iters

    def disparity(self, left, right):
        torch = self.torch
        a = torch.as_tensor(left).cuda().float()[None].permute(0, 3, 1, 2)
        b = torch.as_tensor(right).cuda().float()[None].permute(0, 3, 1, 2)
        p = self.InputPadder(a.shape, divis_by=32, force_square=False)
        a, b = p.pad(a, b)
        with torch.amp.autocast("cuda", enabled=True, dtype=torch.float16):
            d = self.model.forward(a, b, iters=self.iters, test_mode=True, optimize_build_volume="pytorch1")
        d = p.unpad(d.float())
        return d.cpu().numpy().reshape(left.shape[:2]).clip(0, None)


class Detector:
    def __init__(self):
        import torch
        from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor
        self.torch = torch
        self.proc = AutoProcessor.from_pretrained(GDINO)
        self.model = AutoModelForZeroShotObjectDetection.from_pretrained(GDINO).cuda().eval()

    def detect(self, img, text, box_thr=0.25, text_thr=0.2):
        from PIL import Image
        inp = self.proc(images=Image.fromarray(img), text=text.lower().strip(" .") + ".", return_tensors="pt").to("cuda")
        with self.torch.no_grad():
            out = self.model(**inp)
        r = self.proc.post_process_grounded_object_detection(
            out, inp.input_ids, threshold=box_thr, text_threshold=text_thr, target_sizes=[img.shape[:2]])[0]
        boxes = r["boxes"].cpu().numpy()
        scores = r["scores"].cpu().numpy()
        order = np.argsort(-scores)
        return boxes[order], scores[order]


def nms(boxes, scores, thr=0.5):
    keep = []
    for i in range(len(boxes)):
        ok = True
        for j in keep:
            xx1, yy1 = np.maximum(boxes[i][:2], boxes[j][:2])
            xx2, yy2 = np.minimum(boxes[i][2:], boxes[j][2:])
            inter = max(0, xx2 - xx1) * max(0, yy2 - yy1)
            ai = np.prod(boxes[i][2:] - boxes[i][:2]); aj = np.prod(boxes[j][2:] - boxes[j][:2])
            if inter / (ai + aj - inter + 1e-9) > thr:
                ok = False
                break
        if ok:
            keep.append(i)
    return keep


class Tracker:
    def __init__(self):
        from sam2.build_sam import build_sam2_video_predictor
        self.pred = build_sam2_video_predictor(SAM2_CFG, SAM2_CKPT, device="cuda")

    def track(self, jpg_dir, start, boxes):
        """boxes: {obj_id: xyxy} on frame `start`. Returns {frame: {obj_id: bool mask}}."""
        import torch
        out = {}
        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
            st = self.pred.init_state(video_path=jpg_dir, offload_video_to_cpu=True)
            for oid, b in boxes.items():
                self.pred.add_new_points_or_box(st, frame_idx=start, obj_id=oid, box=np.asarray(b, np.float32))
            for f, oids, logits in self.pred.propagate_in_video(st):
                out[f] = {int(o): (logits[k, 0] > 0).cpu().numpy() for k, o in enumerate(oids)}
            self.pred.reset_state(st)
        return out


class Sam31:
    """SAM 3.1 (Object Multiplex) text-prompted dense video tracking, official facebookresearch/sam3 API.

    One session per episode; per category: reset -> text prompt on frame 0 -> propagate (forward).
    The detector runs on every frame, so objects appearing later are picked up. At most `kmax` tracks
    per category are kept (rank_tracks: summed per-frame prob).
    """

    def __init__(self, use_fa3=False):
        from sam3.model_builder import build_sam3_multiplex_video_predictor
        import inspect
        self.pred = build_sam3_multiplex_video_predictor(checkpoint_path=SAM31_CKPT, use_fa3=use_fa3)
        # sam3 @2345a4a: Sam3BasePredictor.start_session passes offload_state_to_cpu, which the multiplex
        # model's init_state does not accept (TypeError). Drop kwargs it does not take (defaults are False).
        m = self.pred.model
        init, ok = m.init_state, set(inspect.signature(m.init_state).parameters)
        m.init_state = lambda **kw: init(**{k: v for k, v in kw.items() if k in ok})

    def segment(self, jpg_dir, n, cats):
        """Returns (start, labels {oid: {cat, det_score, n_frames_tracked}}, masks {frame: {oid: bool HxW}})."""
        P = self.pred
        sid = P.handle_request(dict(type="start_session", resource_path=jpg_dir))["session_id"]
        labels, masks, oid = {}, {f: {} for f in range(n)}, 0
        try:
            for cat, text, kmax in cats:
                P.handle_request(dict(type="reset_session", session_id=sid))
                P.handle_request(dict(type="add_prompt", session_id=sid, frame_index=0, text=text))
                probs, ms = {}, {}
                for r in P.handle_stream_request(dict(type="propagate_in_video", session_id=sid,
                                                      propagation_direction="forward")):
                    o, f = r["outputs"], int(r["frame_index"])
                    probs[f], ms[f] = {}, {}
                    for i, p, m in zip(o["out_obj_ids"], o["out_probs"], o["out_binary_masks"]):
                        m = np.asarray(m, bool)
                        if m.sum() >= MIN_AREA:
                            probs[f][int(i)] = float(p); ms[f][int(i)] = m
                keep = rank_tracks(probs, kmax)
                for i in keep:
                    pv = [probs[f][i] for f in probs if i in probs[f]]
                    labels[oid] = {"cat": cat, "det_score": float(np.mean(pv)), "sam31_id": i,
                                   "n_frames_tracked": len(pv)}
                    for f in ms:
                        if i in ms[f]:
                            masks[f][oid] = ms[f][i]
                    oid += 1
        finally:
            P.handle_request(dict(type="close_session", session_id=sid))
        # first frame where every category has a kept track (plane fit frame; mirrors the GDINO start frame)
        ok = [f for f in range(n) if all(any(labels[o]["cat"] == c and o in masks[f] for o in labels)
                                         for c, _, _ in cats)]
        start = ok[0] if ok else None
        return start, labels, masks


# ------------------------------------------------------------------ per episode

def disp_cache_path(cache_dir, repo, ep):
    return f"{cache_dir}/{repo.split('/')[-1]}_ep{ep:06d}.npz"


def save_masks(fn, start, labels, masks, n, H, W):
    """Segmentation cache: start frame, labels, per-object bit-packed (n, H, W) masks (absent frame = empty)."""
    oids = sorted(labels)
    arr = {}
    for o in oids:
        st = np.zeros((n, H, W), bool)
        for f in range(n):
            m = masks.get(f, {}).get(o)
            if m is not None:
                st[f] = m
        arr[f"m{o}"] = np.packbits(st)
    meta = {"start": start, "labels": {str(o): labels[o] for o in oids}, "oids": oids, "shape": [n, H, W]}
    np.savez_compressed(fn, meta=np.array(json.dumps(meta)), **arr)


def load_masks(fn):
    z = np.load(fn)
    meta = json.loads(str(z["meta"]))
    n, H, W = meta["shape"]
    labels = {int(o): v for o, v in meta["labels"].items()}
    masks = {f: {} for f in range(n)}
    for o in meta["oids"]:
        st = np.unpackbits(z[f"m{o}"], count=n * H * W).reshape(n, H, W).astype(bool)
        for f in range(n):
            masks[f][o] = st[f]
    return meta["start"], labels, masks


def run_episode(repo, ep, task_text, models, out_dir, max_frames, root, tmp, seg="gdino_sam2", depth_cache=None,
                prompt_map=None, fx=HEAD_FX, mask_cache=None):
    import cv2
    ffs, det, trk = models
    lefts, disps, t_ffs = [], [], []
    cached = np.load(disp_cache_path(depth_cache, repo, ep)) if ffs is None else None
    for i, (t, l, r) in enumerate(load_pairs(repo, ep, max_frames, root)):
        if cached is None:
            t0 = time.time(); d = ffs.disparity(l, r); models_sync(); t_ffs.append(time.time() - t0)
        else:
            d = cached["disp"][i]
        lefts.append(l); disps.append(d.astype(np.float32))
    if cached is not None:
        assert len(cached["disp"]) == len(lefts), (repo, ep, len(cached["disp"]), len(lefts))
        t_ffs = list(cached["ffs_s"])
    n = len(lefts)
    H, W = lefts[0].shape[:2]
    K = intrinsics_from_fx(W, H, fx)
    uu = np.arange(W)[None, :].repeat(H, 0)
    depths, invalid_img = [], []
    for d in disps:
        z = disparity_to_depth(d, fx, BASELINE_M)
        z[(uu - d) < 0] = np.nan  # not visible in the right image
        z[(z < ZNEAR) | (z > ZFAR)] = np.nan
        depths.append(z)
        invalid_img.append(float(np.mean(~np.isfinite(z))))

    # detection on the first frame (every 5th) that has all categories
    cats = [(c, (prompt_map or {}).get(t, t), k) for c, t, k in prompts_for(repo, task_text)]
    start, boxes, labels = None, {}, {}
    mfn = f"{mask_cache}/{repo.split('/')[-1]}_ep{ep:06d}.npz" if mask_cache else None
    have_masks = bool(mfn and os.path.exists(mfn))
    if have_masks:
        start, labels, masks = load_masks(mfn)
    for f in (range(0, n, 5) if seg == "gdino_sam2" and not have_masks else []):
        found, oid = {}, 0
        for cat, text, kmax in cats:
            b, s = det.detect(lefts[f], text)
            keep = nms(b, s)[:kmax]
            found[cat] = [(b[k], float(s[k])) for k in keep]
        if all(found[c] for c, _, _ in cats):
            start = f
            for cat, _, _ in cats:
                for bb, sc in found[cat]:
                    boxes[oid] = bb.tolist(); labels[oid] = {"cat": cat, "det_score": sc}; oid += 1
            break
    def write_jpgs():
        if os.path.isdir(tmp):
            shutil.rmtree(tmp)
        os.makedirs(tmp)
        for i, l in enumerate(lefts):
            cv2.imwrite(f"{tmp}/{i:05d}.jpg", l[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 95])

    if seg == "sam31" and not have_masks:
        write_jpgs()
        start, labels, masks = trk.segment(tmp, n, cats)
    if seg != "sam31" and not have_masks and start is not None:
        write_jpgs()
        masks = trk.track(tmp, start, boxes)
    if mfn and not have_masks:
        os.makedirs(mask_cache, exist_ok=True)
        save_masks(mfn, start, labels, masks if start is not None else {}, n, H, W)
    res = {"repo": repo, "episode": ep, "task": task_text, "n_frames": n, "H": H, "W": W, "K": K.tolist(),
           "fx": float(fx), "masks_from_cache": have_masks,
           "baseline_m": BASELINE_M, "ffs_ms_median": float(np.median(t_ffs) * 1000),
           "invalid_depth_img": float(np.mean(invalid_img)), "start_frame": start, "objects": labels, "seg": seg,
           "prompts": [t for _, t, _ in cats]}
    if start is None:
        res["skip"] = "no detection"
        return res, None

    ker = np.ones((5, 5), np.uint8)

    oids = sorted(labels)
    C = np.full((len(oids), n, 3), np.nan)
    px = np.full((len(oids), n, 2), np.nan)
    area = np.zeros((len(oids), n))
    inval_mask = []
    half_ext = np.full((len(oids), n), np.nan)
    # table/support plane on the start frame: lower 40% of the image, outside object masks
    m0 = np.zeros((H, W), bool)
    for o in oids:
        m0 |= masks.get(start, {}).get(o, np.zeros((H, W), bool))
    z0 = depths[start]
    vv, uu0 = np.mgrid[0:H, 0:W]
    sel = (~m0) & np.isfinite(z0) & (vv > 0.6 * H)
    pts = np.stack([(uu0[sel] - K[0, 2]) / fx * z0[sel], (vv[sel] - K[1, 2]) / fx * z0[sel], z0[sel]], 1)
    up_src = "camera_-y"
    up = np.array([0, -1.0, 0])
    if len(pts) > 500:
        pts = pts[np.random.default_rng(0).choice(len(pts), min(20000, len(pts)), replace=False)]
        nrm, _ = fit_plane(pts, tol=0.01)
        if nrm is not None and np.degrees(np.arccos(np.clip(nrm @ np.array([0, -1.0, 0]), -1, 1))) < 60:
            up, up_src = nrm, "ransac_plane"
    res["up"] = up.tolist(); res["up_source"] = up_src

    for f in range(n):
        for k, o in enumerate(oids):
            m = masks.get(f, {}).get(o)
            if m is None or m.sum() < MIN_AREA:
                continue
            area[k, f] = m.sum()
            vy, ux = np.nonzero(m)
            px[k, f] = [ux.mean(), vy.mean()]
            me = cv2.erode(m.astype(np.uint8), ker).astype(bool)
            if me.sum() < 20:
                me = m
            inval_mask.append(float(np.mean(~np.isfinite(depths[f][me]))))
            C[k, f] = centroid_3d(depths[f], me, K)
            ok = me & np.isfinite(depths[f])
            if ok.sum() > 20 and np.all(np.isfinite(C[k, f])):
                v2, u2 = np.nonzero(ok)
                z2 = depths[f][v2, u2]
                P = np.stack([(u2 - K[0, 2]) / fx * z2, (v2 - K[1, 2]) / fx * z2, z2], 1) - C[k, f]
                horiz = P - np.outer(P @ up, up)
                half_ext[k, f] = float(np.percentile(np.linalg.norm(horiz, axis=1), 90))

    # stability per object: all consecutive pairs, and image-static pairs
    jit_all, jit_static = [], []
    per_obj = {}
    for k, o in enumerate(oids):
        s_all = stability(list(C[k]))
        d_static = []
        for f in range(n - 1):
            if area[k, f] and area[k, f + 1] and np.all(np.isfinite(C[k, f])) and np.all(np.isfinite(C[k, f + 1])):
                dmm = float(np.linalg.norm(C[k, f + 1] - C[k, f]) * 1000)
                jit_all.append(dmm)
                if (np.linalg.norm(px[k, f + 1] - px[k, f]) < STATIC_PX
                        and abs(area[k, f + 1] / area[k, f] - 1) < STATIC_AREA):
                    d_static.append(dmm)
        jit_static += d_static
        per_obj[o] = {**labels[o], **s_all, "n_static_pairs": len(d_static),
                      "static_median_mm": float(np.median(d_static)) if d_static else None,
                      "visible_frames": int((area[k] > 0).sum()),
                      "median_depth_m": float(np.nanmedian(C[k, :, 2])) if np.isfinite(C[k, :, 2]).any() else None}
    # predicates: (small object, container) pairs
    small = [o for o in oids if labels[o]["cat"] in ("bottle", "object")]
    cont = [o for o in oids if labels[o]["cat"] in ("box", "crate")]
    preds = {}
    for a in small:
        for b in cont:
            ka, kb = oids.index(a), oids.index(b)
            near_s, above_s, prev = [], [], None
            for f in range(n):
                if not (area[ka, f] and area[kb, f] and np.all(np.isfinite(C[ka, f])) and np.all(np.isfinite(C[kb, f]))):
                    near_s.append(None); above_s.append(None); continue
                prev = near_update(prev, float(np.linalg.norm(C[ka, f] - C[kb, f])))
                near_s.append(prev)
                above_s.append(above(C[ka, f], C[kb, f], half_ext[kb, f], up) if np.isfinite(half_ext[kb, f]) else None)
            preds[f"{a}-{b}"] = {"near": near_s, "above": above_s,
                                 "near_flip": flip_rate(near_s), "above_flip": flip_rate(above_s)}
    res.update({"per_object": per_obj, "jitter_all_mm": jit_all, "jitter_static_mm": jit_static,
                "invalid_depth_mask_median": float(np.median(inval_mask)) if inval_mask else None,
                "invalid_depth_mask_mean": float(np.mean(inval_mask)) if inval_mask else None,
                "predicates": preds})
    extra = {"lefts": lefts, "depths": depths, "masks": masks, "oids": oids, "labels": labels}
    return res, extra


def models_sync():
    import torch
    torch.cuda.synchronize()


def save_example(extra, res, path, frame=None):
    import cv2
    from PIL import Image
    n = len(extra["lefts"])
    f = frame if frame is not None else min(n - 1, (res["start_frame"] or 0) + n // 2)
    l = extra["lefts"][f]
    z = extra["depths"][f]
    zf = z[np.isfinite(z)]
    lo, hi = (np.percentile(zf, 2), min(np.percentile(zf, 98), 1.5)) if zf.size else (0.3, 1.5)  # workspace range
    zn = np.clip((z - lo) / (hi - lo + 1e-9), 0, 1)
    dv = cv2.applyColorMap((255 * (1 - zn)).astype(np.uint8), cv2.COLORMAP_TURBO)[:, :, ::-1].copy()
    dv[~np.isfinite(z)] = 0
    ov = l.copy().astype(float)
    cols = [(255, 60, 60), (60, 220, 60), (60, 120, 255), (255, 200, 0), (255, 0, 255), (0, 220, 220),
            (255, 140, 0), (150, 80, 255)]
    for i, o in enumerate(extra["oids"]):
        m = extra["masks"].get(f, {}).get(o)
        if m is not None and m.any():
            ov[m] = 0.45 * ov[m] + 0.55 * np.array(cols[i % len(cols)])
    ov = ov.astype(np.uint8)
    pan = np.concatenate([l, dv, ov], 1)
    pan = cv2.resize(pan, (pan.shape[1] * 2 // 3, pan.shape[0] * 2 // 3), interpolation=cv2.INTER_AREA)
    Image.fromarray(pan).quantize(colors=128, method=Image.Quantize.MEDIANCUT).save(path, optimize=True)
    return {"frame": f, "depth_range_m": [float(lo), float(hi)]}


def cmd_depth(a):
    """Cache FFS disparities (float32, px) per selected episode so another venv can reuse them."""
    sel = json.load(open(os.path.join(a.root, "episodes_sel.json"), encoding="utf-8"))
    os.makedirs(a.depth_cache, exist_ok=True)
    ffs = FFS()
    for name, eps in sel.items():
        repo = f"ROBOTIS/{name}"
        for e in eps:
            fn = disp_cache_path(a.depth_cache, repo, e["ep"])
            if os.path.exists(fn) and not a.force:
                continue
            disp, ts = [], []
            for t, l, r in load_pairs(repo, e["ep"], a.max_frames, a.root):
                t0 = time.time(); d = ffs.disparity(l, r); models_sync(); ts.append(time.time() - t0)
                disp.append(d.astype(np.float32))
            np.savez(fn, disp=np.stack(disp), ffs_s=np.array(ts))
            print(name, e["ep"], len(disp), flush=True)


def cmd_run(a):
    sel = json.load(open(os.path.join(a.root, "episodes_sel.json"), encoding="utf-8"))
    os.makedirs(a.out, exist_ok=True)
    import torch
    if a.seg == "sam31":
        assert a.depth_cache, "--seg sam31 needs --depth-cache (FFS runs in venv_e3st)"
        models = (None, None, Sam31(use_fa3=a.fa3))
    else:  # with --depth-cache the disparities come from the cache (FFS not loaded)
        models = (None if a.depth_cache else FFS(), Detector(), Tracker())
    meta = {"gpu": torch.cuda.get_device_name(0), "torch": torch.__version__, "seg": a.seg, "fx": a.fx,
            "depth_cache": a.depth_cache, "mask_cache": a.mask_cache}
    json.dump(meta, open(f"{a.out}/run_meta.json", "w"))
    ex_plan = {T1: [0, 1], T2: [0, 1]}  # which selected-episode positions get example images
    for name, eps in sel.items():
        if a.only and a.only not in name:
            continue
        repo = f"ROBOTIS/{name}"
        for pos, e in enumerate(eps):
            fn = f"{a.out}/{name}_ep{e['ep']:06d}.json"
            if os.path.exists(fn) and not a.force:
                continue
            t0 = time.time()
            res, extra = run_episode(repo, e["ep"], e["task"], models, a.out, a.max_frames, a.root,
                                     f"{a.out}/tmp_frames", seg=a.seg, depth_cache=a.depth_cache,
                                     prompt_map=dict(kv.split("=", 1) for kv in a.prompt_map), fx=a.fx,
                                     mask_cache=a.mask_cache)
            res["wall_s"] = time.time() - t0
            if extra is not None and pos in ex_plan.get(repo, []):
                tag = "t1" if repo == T1 else "t2"
                if a.seg == "sam31":
                    tag = "sam31_" + tag
                frame = None  # same frame as the reference run's example, for side-by-side comparison
                ref = f"{a.ref_out}/{name}_ep{e['ep']:06d}.json" if a.ref_out else None
                if ref and os.path.exists(ref):
                    frame = json.load(open(ref, encoding="utf-8")).get("example", {}).get("frame")
                res["example"] = save_example(extra, res, f"{a.out}/e3st_{tag}_ep{e['ep']}.png", frame=frame)
            json.dump(res, open(fn, "w"), ensure_ascii=False)
            print(name, e["ep"], res.get("n_frames"), res.get("skip", "ok"), f"{res['wall_s']:.1f}s", flush=True)


def cmd_aggregate(a):
    import glob
    out = {}
    for name in ("Task_0001_CoffeeClassification_lerobot", "Task_0002_OrderPicking_lerobot"):
        R = [json.load(open(f, encoding="utf-8")) for f in sorted(glob.glob(f"{a.out}/{name}_ep*.json"))]
        ok = [r for r in R if "skip" not in r]
        ja = np.concatenate([r["jitter_all_mm"] for r in ok]) if ok else np.array([])
        js = np.concatenate([r["jitter_static_mm"] for r in ok]) if ok else np.array([])
        flips = {"near": [0, 0], "above": [0, 0]}
        per_pair = {"near": [], "above": []}
        for r in ok:
            for p in r["predicates"].values():
                for key in ("near", "above"):
                    v = [x for x in p[key] if x is not None]
                    if len(v) >= 2:
                        fl = sum(x != y for x, y in zip(v[:-1], v[1:]))
                        flips[key][0] += fl; flips[key][1] += len(v) - 1
                        if any(v) and not all(v):  # series where the predicate actually takes both values
                            flips.setdefault(key + "_active", [0, 0, 0])
                            flips[key + "_active"][0] += fl; flips[key + "_active"][1] += len(v) - 1
                            flips[key + "_active"][2] += 1
                        per_pair[key].append(fl / (len(v) - 1))
                        if key == "near":
                            per_pair.setdefault("near_true_frac", []).append(float(np.mean(v)))
                        else:
                            per_pair.setdefault("above_true_frac", []).append(float(np.mean(v)))
        ep_med = [float(np.median(r["jitter_all_mm"])) for r in ok if r["jitter_all_mm"]]
        ep_med_s = [float(np.median(r["jitter_static_mm"])) for r in ok if r["jitter_static_mm"]]
        out[name] = {
            "episodes": len(R), "episodes_ok": len(ok), "skipped": [r["episode"] for r in R if "skip" in r],
            "frames": int(sum(r["n_frames"] for r in R)),
            "objects_tracked": int(sum(len(r["objects"]) for r in ok)),
            "jitter_all": {"n": int(ja.size), "median_mm": float(np.median(ja)) if ja.size else None,
                           "p95_mm": float(np.percentile(ja, 95)) if ja.size else None},
            "jitter_static": {"n": int(js.size), "median_mm": float(np.median(js)) if js.size else None,
                              "p95_mm": float(np.percentile(js, 95)) if js.size else None},
            "episode_median_jitter_mm_range": [min(ep_med), max(ep_med)] if ep_med else None,
            "episode_median_static_mm_range": [min(ep_med_s), max(ep_med_s)] if ep_med_s else None,
            "flip_near": flips["near"][0] / flips["near"][1] if flips["near"][1] else None,
            "flip_above": flips["above"][0] / flips["above"][1] if flips["above"][1] else None,
            "flip_pairs_counted": {k: v[1] for k, v in flips.items()},
            "flip_active": {k: {"rate": v[0] / v[1], "flips": v[0], "pairs": v[1], "series": v[2]}
                            for k, v in flips.items() if k.endswith("_active") and v[1]},
            "n_predicate_series": len(per_pair["near"]),
            "near_true_frac_mean": float(np.mean(per_pair.get("near_true_frac", [np.nan]))),
            "above_true_frac_mean": float(np.mean(per_pair.get("above_true_frac", [np.nan]))),
            "invalid_depth_img_mean": float(np.mean([r["invalid_depth_img"] for r in R])),
            "invalid_depth_mask_median_of_eps": float(np.median([r["invalid_depth_mask_median"] for r in ok
                                                                  if r.get("invalid_depth_mask_median") is not None])),
            "invalid_depth_mask_mean": float(np.mean([r["invalid_depth_mask_mean"] for r in ok
                                                      if r.get("invalid_depth_mask_mean") is not None])),
            "object_median_depth_m": float(np.median([o["median_depth_m"] for r in ok for o in r["per_object"].values()
                                                      if o["median_depth_m"] is not None])),
            "ffs_ms_median": float(np.median([r["ffs_ms_median"] for r in R])),
            "up_source": {s: sum(r.get("up_source") == s for r in ok) for s in ("ransac_plane", "camera_-y")},
        }
    json.dump(out, open(f"{a.out}/summary.json", "w"), indent=1)
    print(json.dumps(out, indent=1))


def build_parser():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    for c in ("run", "aggregate", "depth"):
        p = sp.add_parser(c)
        p.add_argument("--out", default="/data/harvest/out/e3st")
        p.add_argument("--root", default=DEFAULT_ROOT)
        p.add_argument("--max-frames", dest="max_frames", type=int, default=300)
        p.add_argument("--force", action="store_true")
        p.add_argument("--seg", choices=("gdino_sam2", "sam31"), default="gdino_sam2")
        p.add_argument("--depth-cache", dest="depth_cache", default=None, help="dir of cached FFS disparities")
        p.add_argument("--ref-out", dest="ref_out", default=None, help="earlier run dir; reuse its example frames")
        p.add_argument("--fa3", action="store_true", help="SAM 3.1 with FlashAttention-3 (needs flash-attn-3)")
        p.add_argument("--prompt-map", dest="prompt_map", nargs="*", default=[],
                       help="replace text prompts, e.g. box=basket (category names unchanged)")
        p.add_argument("--only", default=None, help="run only datasets whose name contains this (e.g. Task_0001)")
        p.add_argument("--fx", type=float, default=HEAD_FX,
                       help="head focal length px (fx = fy, principal point = image centre); first runs used 272.1")
        p.add_argument("--mask-cache", dest="mask_cache", default=None,
                       help="dir of cached segmentation masks (reused if present, written otherwise)")
    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)
    {"run": cmd_run, "aggregate": cmd_aggregate, "depth": cmd_depth}[a.cmd](a)


if __name__ == "__main__":
    main()
