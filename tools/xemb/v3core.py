"""Object point labelling core, AgiBot v3 method (approved 2026-09-28) for any source:
  1. grasp (query) frame: SAM 3.1 masks of the named object (head-noun fallback); the mask nearest the projected
     end-effector point = the grasped instance (the projection only SELECTS the instance).
  2. CoTracker3 (offline) tracks N_PTS points of that mask back to the label frame (before the approach).
  3. label frame: SAM masks of the name; the one with the best IoU against the tracked-point hull.
  4. gates: tracked visibility >= TRACK_CONF, IoU >= IOU_MIN, tracked centre within HELD_TO_LABEL_PX of the mask, mask
     quality (single component >= 90 %, area 0.05-15 %), name passes pointlab.clean_name (robot part names dropped).
  5. label = top-surface centre of the label mask.
No name mask -> no row (no relaxation). Used by agb_objpts-style adapters (droid_objpts, rh20t_objpts).
"""
from __future__ import annotations

import numpy as np

TRACK_CONF, IOU_MIN, HELD_TO_LABEL_PX, N_PTS = 0.5, 0.5, 5.0, 120
AREA = (0.0005, 0.15)
_tracker = None


class Labeller:
    def __init__(self, seg=None):
        if seg is None:
            from harvest.perception.seg import Sam31Image
            seg = Sam31Image(thr=0.3)
        self.seg = seg

    def masks(self, img_bgr, name):
        for qn in [name] + ([name.split()[-1]] if len(name.split()) > 1 else []):
            res, _ = self.seg.segment(np.ascontiguousarray(img_bgr[:, :, ::-1]), [qn])
            ms = [mk.astype(bool) for sc, mk in res[qn] if sc >= 0.3]
            if ms:
                return ms
        return []

    def track_back(self, seq_bgr, held):
        """seq_bgr: frames from the label frame (first) to the query frame (last)."""
        global _tracker
        import torch
        if _tracker is None:
            _tracker = torch.hub.load("facebookresearch/co-tracker", "cotracker3_offline").cuda().eval()
        ys, xs = np.nonzero(held)
        if len(xs) < N_PTS:
            return None, None
        sel = np.random.default_rng(0).choice(len(xs), N_PTS, replace=False)
        v = torch.from_numpy(np.stack([f[:, :, ::-1] for f in seq_bgr])).permute(0, 3, 1, 2)[None].float().cuda()
        q = torch.tensor([[float(len(seq_bgr) - 1), float(xs[k]), float(ys[k])] for k in sel])[None].cuda()
        with torch.inference_mode():
            tr, vis = _tracker(v, queries=q, backward_tracking=True)
        return tr[0, 0].cpu().numpy(), vis[0, 0].cpu().numpy() > 0.5

    def label(self, seq_bgr, name, ee_uv):
        """seq_bgr[0] = label frame, seq_bgr[-1] = query (grasp) frame; ee_uv = projected end effector at the query
        frame. -> dict(ok, reason, pt, iou, conf, dist, held, best, tracks, vis)."""
        import cv2
        qimg, limg = seq_bgr[-1], seq_bgr[0]
        H, W = qimg.shape[:2]
        mb = self.masks(qimg, name)
        if not mb:
            return {"ok": False, "reason": "no_mask"}
        held = min(mb, key=lambda m: np.min(np.hypot(*(np.array(np.nonzero(m)[::-1]) - np.asarray(ee_uv)[:, None]))))
        tl, vis = self.track_back(seq_bgr, held)
        if tl is None:
            return {"ok": False, "reason": "track_fail"}
        conf = float(vis.mean())
        if conf < TRACK_CONF:
            return {"ok": False, "reason": "track_conf"}
        hull = np.zeros((H, W), np.uint8)
        if vis.sum() >= 3:
            cv2.fillConvexPoly(hull, cv2.convexHull(tl[vis].astype(np.int32)), 1)
        hull = hull.astype(bool)
        ml = self.masks(limg, name)
        if not ml:
            return {"ok": False, "reason": "no_mask_label"}
        ious = [float((hull & m).sum() / max(1, (hull | m).sum())) for m in ml]
        best, iou = ml[int(np.argmax(ious))], max(ious)
        c = tl[vis].mean(0)
        ys, xs = np.nonzero(best)
        dist = float(np.min(np.hypot(xs - c[0], ys - c[1])))
        if iou < IOU_MIN or dist > HELD_TO_LABEL_PX:
            return {"ok": False, "reason": "track_gate"}
        n, _, stats, _ = cv2.connectedComponentsWithStats(best.astype(np.uint8), connectivity=8)
        area = best.sum() / float(W * H)
        if n < 2 or stats[1:, cv2.CC_STAT_AREA].max() < 0.9 * best.sum():
            return {"ok": False, "reason": "fragmented"}
        if not (AREA[0] <= area <= AREA[1]):
            return {"ok": False, "reason": "size"}
        y0, y1 = ys.min(), ys.max()
        s = ys <= y0 + 0.3 * (y1 - y0 + 1)
        cc = np.array([xs[s].mean(), ys[s].mean()])
        i = int(np.argmin((xs - cc[0]) ** 2 + (ys - cc[1]) ** 2))
        return {"ok": True, "reason": "ok", "pt": np.array([xs[i], ys[i]], float), "iou": iou, "conf": conf,
                "dist": dist, "held": held, "best": best, "tracks": tl, "vis": vis}


def check_image(res, qimg, limg):
    """grasp (query) frame with the held mask | label frame with tracks and the label point."""
    import cv2
    g, l_ = qimg.copy(), limg.copy()
    for img, m in ((g, res["held"]), (l_, res["best"])):
        cnt, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(img, cnt, -1, (0, 255, 0), 2)
    for x, y in res["tracks"][res["vis"]]:
        cv2.circle(l_, (int(x), int(y)), 2, (255, 0, 255), -1)
    cv2.drawMarker(l_, (int(res["pt"][0]), int(res["pt"][1])), (0, 0, 255), cv2.MARKER_CROSS, 18, 2)
    return np.hstack([g, l_])
