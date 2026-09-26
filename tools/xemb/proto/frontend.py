"""Shared tracking front-end runner (GPU): one CoTracker3 cache per episode.
  mb  MolmoBot RBY1 (calibrated, GT used only for evaluation): gripper queries seeded (a) 'oracle' = GT gripper point at
      one frame, (b) 'point' = up to 3 Molmo2 pointings that pass the jump filter (needs point/points.jsonl); object
      query = GT pickup-object point at the first frame (evaluation only).
  rb2 ROBOTIS RB2 (open, uncalibrated): gripper queries = 3 filtered Molmo2 pointings per arm.
usage: frontend.py mb|rb2 OUT [MAX_EPS]"""
import glob, json, os, sys
sys.path.insert(0, "/data/harvest/out/xemb_proto/code")
sys.path.insert(0, "/data/harvest/pylib_xemb_train")
sys.path.insert(0, "/data/harvest/pylib_moge")
import cv2
import numpy as np
import torch
from xemb import track as TK

mode, out = sys.argv[1], sys.argv[2]
max_eps = int(sys.argv[3]) if len(sys.argv) > 3 else 50
os.makedirs(out, exist_ok=True)
model = torch.hub.load("facebookresearch/co-tracker", "cotracker3_offline").cuda().eval()


def run(frames, queries):
    v = torch.from_numpy(np.ascontiguousarray(frames)).permute(0, 3, 1, 2)[None].float().cuda()
    q = torch.tensor([[float(t), float(x), float(y)] for t, x, y in queries])[None].cuda()
    with torch.inference_mode():
        tr, vis = model(v, queries=q, backward_tracking=True)
    return tr[0].cpu().numpy(), vis[0].cpu().numpy() > 0.5


stats = []
if mode == "mb":
    from xemb import src_molmobot as MB
    pts = {}
    pp = "/data/harvest/out/xemb_proto/point/points.jsonl"
    if os.path.exists(pp):
        for line in open(pp):
            r = json.loads(line)
            if r["key"].startswith("mb|"):
                _, name, k, arm = r["key"].split("|")
                pts[(name, int(k), arm)] = r["point"]
    for ei, e in enumerate(MB.episodes("/data/harvest/out/xemb_proto/src/mb_rby1")):
        if ei >= max_eps:
            break
        cap = cv2.VideoCapture(e.video("head_camera"))
        fr = []
        while True:
            ok, f = cap.read()
            if not ok:
                break
            fr.append(cv2.resize(f, (512, 288))[:, :, ::-1])
        fr = np.array(fr[: e.n])
        sc = np.array([0.5, 0.5])
        names, queries = [], []
        for arm in ("left", "right"):
            gp = np.array([np.nanmean(e.pts(f"{arm}_gripper", "head_camera", k), 0) for k in range(len(fr))])
            t0 = next((k for k in range(len(fr)) if np.isfinite(gp[k]).all()), None)
            if t0 is not None:
                names.append(f"grip_{arm}|oracle")
                queries.append((t0, *(gp[t0] * sc)))
            det = np.full((len(fr), 2), np.nan)
            for (nm, k, a), p in pts.items():
                if nm == e.name and a == arm and p is not None and k < len(fr):
                    det[k] = p
            for s in TK.seeds(det, n=3, win=1, max_px=60):
                names.append(f"grip_{arm}|point")
                queries.append((s, *(det[s] * sc)))
        op = np.array([np.nanmean(e.pts("pickup_obj", "head_camera", k), 0) for k in range(len(fr))])
        t0 = next((k for k in range(len(fr)) if np.isfinite(op[k]).all()), None)
        if t0 is not None:
            names.append("obj|oracle")
            queries.append((t0, *(op[t0] * sc)))
        if not queries:
            continue
        tr, vis = run(fr, queries)
        tr = tr / sc
        fused = {}
        for key in sorted({n for n in names}):
            idx = [i for i, n in enumerate(names) if n == key]
            fused[key.replace("|", "_")] = TK.fuse(tr[:, idx], vis[:, idx])[0]
        ev = {e.arm: TK.events(1 - e.open_meas, closed_thr=0.2)}
        TK.save(os.path.join(out, f"{e.name}.npz"), {"names": names, "tracks": tr, "vis": vis, "fused": fused,
                                                      "events": ev, "meta": {"arm": e.arm, "n": int(len(fr))}})
        stats.append({"ep": e.name, "queries": len(names)})
        print(json.dumps(stats[-1]), flush=True)
else:
    from xemb import src_rb2 as R
    from xemb import selfcal as C
    root = "/data/harvest/data/marr_real"
    for e in R.load(root)[:max_eps]:
        paths = [os.path.join(root, "frames", "RB2", f"ep{e['ep']:06d}", f"f{k:04d}.jpg") for k in range(e["n"])]
        have = [os.path.exists(p) for p in paths]
        if not all(have):
            stats.append({"ep": e["ep"], "skipped": "missing frames", "missing": int(len(have) - sum(have))})
            continue
        fr = np.array([cv2.imread(p)[:, :, ::-1] for p in paths])
        names, queries = [], []
        for a in ("left", "right"):
            for s in TK.seeds(e["uv"][a], n=3):
                names.append(f"grip_{a}|point")
                queries.append((s, *e["uv"][a][s]))
        if not queries:
            continue
        tr, vis = run(fr, queries)
        fused = {}
        for a in ("left", "right"):
            idx = [i for i, n in enumerate(names) if n == f"grip_{a}|point"]
            if idx:
                fused[f"grip_{a}_point"] = TK.fuse(tr[:, idx], vis[:, idx])[0]
        ev = {a: TK.events(e["g"][a]) for a in ("left", "right")}
        TK.save(os.path.join(out, f"RB2_ep{e['ep']:06d}.npz"), {"names": names, "tracks": tr, "vis": vis,
                                                                 "fused": fused, "events": ev,
                                                                 "meta": {"n": int(e["n"])}})
        stats.append({"ep": e["ep"], "queries": len(names)})
        print(json.dumps(stats[-1]), flush=True)
json.dump(stats, open(os.path.join(out, "frontend_stats.json"), "w"))
print("done", len(stats))
