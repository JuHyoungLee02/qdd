"""R1 evaluation driver (pod, venv_sam3, GPU 1). Pre-registration: docs/stage3/results/r1_perception.md §1.

  python -m harvest.perception.run_r1 probe   --jsel /data/harvest/data/jsel_dev --r1 /data/harvest/r1/dev --out ...
  python -m harvest.perception.run_r1 head2d  --jsel /data/harvest/data/jsel_dev --r1 /data/harvest/r1/dev --out ...
  python -m harvest.perception.run_r1 eval    --r1 /data/harvest/r1/dev --out /data/harvest/r1/out
  python -m harvest.perception.run_r1 report  --out /data/harvest/r1/out
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import time

import numpy as np

from ..e3lite import state_text
from ..labels_v2 import code_rule_v2, labels
from ..predicates import PredicateState
from ..sim.scene import OBJ_GEOM, TABLE_TOP_Z, load_realcam
from .fuse import MIN_VALID_PX, CamDet, Tracker, fuse
from .geom import backproject, intr_of, project
from .state import est_line, s1_text

HEAD, WRIST = "cam_head", "cam_wrist_right"
DMIN = {HEAD: 0.1, WRIST: 0.03}
QS = ("dir_xy", "dir_z", "mag_coarse", "target", "phase_choice")
HIT_PX = 5


def _intr():
    rc = load_realcam()
    return {n: intr_of(rc.CAMERA_SPECS[n]) for n in (HEAD, WRIST)}


def _lines(path):
    with open(path) as f:
        return [json.loads(x) for x in f]


def _img(root, rel):
    from PIL import Image
    return np.asarray(Image.open(os.path.join(root, rel)).convert("RGB"))


def _world(p_table):
    p = np.asarray(p_table, float).copy()
    p[2] += TABLE_TOP_Z
    return p


def _table(p_world):
    p = np.asarray(p_world, float).copy()
    p[..., 2] -= TABLE_TOP_Z
    return p


def _in_fov(pw, K, p, R):
    u, v, d = project(pw[None], K, p, R)
    return bool(d[0] > 0 and 0 <= u[0] < K.width and 0 <= v[0] < K.height), (float(u[0]), float(v[0]))


def _covers(mask, uv, r=HIT_PX):
    c, rr = int(uv[0]), int(uv[1])
    h, w = mask.shape
    return bool(mask[max(rr - r, 0):min(rr + r + 1, h), max(c - r, 0):min(c + r + 1, w)].any())


def load_phrases(out_dir):
    p = f"{out_dir}/phrases.json"
    return json.load(open(p)) if os.path.exists(p) else None


def head_pose_const(r1_root):
    """Head camera pose over all R1-DEV snapshots: (p, R, max deviation m / deg)."""
    P, Rs = [], []
    for f in sorted(glob.glob(f"{r1_root}/*/ep*.r1.npz")):
        z = np.load(f)
        P.append(z[f"campos_{HEAD}"])
        Rs.append(z[f"camR_{HEAD}"])
    P, Rs = np.concatenate(P), np.concatenate(Rs)
    p0, R0 = P[0], Rs[0]
    dp = float(np.abs(P - p0).max())
    ang = max(float(np.degrees(np.arccos(np.clip((np.trace(R0.T @ R) - 1) / 2, -1, 1)))) for R in Rs)
    return p0, R0, dp, ang


# ------------------------------------------------------------------------------------------ probe / head2d
def cmd_probe(a):
    from .seg import PHRASE_CANDIDATES, Sam31Image
    K = _intr()[HEAD]
    p, R, dp, ang = head_pose_const(a.r1)
    sam = Sam31Image()
    hits = {k: {ph: [0, 0] for ph in v} for k, v in PHRASE_CANDIDATES.items()}
    for kind in ("P0", "P1", "P2"):
        for s in (20, 21):
            root = f"{a.jsel}/{kind}"
            for ln in _lines(f"{root}/ep{s}.jsonl"):
                img = _img(root, ln["images"][HEAD])
                present = ln["state"]["present"]
                phr = [ph for k in present for ph in PHRASE_CANDIDATES[k]]
                res, _ = sam.segment(img, phr)
                for k in present:
                    ok, uv = _in_fov(_world(ln["state"]["obs"]["raw"]["objs"][k]["pos"]), K, p, R)
                    if not ok:
                        continue
                    for ph in PHRASE_CANDIDATES[k]:
                        hits[k][ph][1] += 1
                        if res[ph] and _covers(res[ph][0][1], uv):
                            hits[k][ph][0] += 1
    choice = {k: max(v, key=lambda ph: (v[ph][0] / max(v[ph][1], 1), -PHRASE_CANDIDATES[k].index(ph)))
              for k, v in hits.items()}
    os.makedirs(a.out, exist_ok=True)
    json.dump({"hits": hits, "choice": choice, "head_pose_dev": [dp, ang]}, open(f"{a.out}/probe.json", "w"), indent=1)
    json.dump(choice, open(f"{a.out}/phrases.json", "w"), indent=1)
    print(json.dumps({"choice": choice, "hits": hits}))


def cmd_head2d(a):
    from .seg import Sam31Image
    K = _intr()[HEAD]
    p, R, dp, ang = head_pose_const(a.r1)
    phrases = load_phrases(a.out)
    sam = Sam31Image()
    out = open(f"{a.out}/head2d.jsonl", "w")
    n = 0
    for kind in ("P0", "P1", "P2"):
        root = f"{a.jsel}/{kind}"
        for f in sorted(glob.glob(f"{root}/ep*.jsonl"), key=lambda x: int(x.split("ep")[-1].split(".")[0])):
            for ln in _lines(f):
                img = _img(root, ln["images"][HEAD])
                present = ln["state"]["present"]
                res, tm = sam.segment(img, [phrases[k] for k in present])
                rec = {"seed": ln["seed"], "kind": kind, "k": ln["k"], "phase": ln["phase"], "tm": tm, "obj": {}}
                for k in present:
                    ok, uv = _in_fov(_world(ln["state"]["obs"]["raw"]["objs"][k]["pos"]), K, p, R)
                    d = res[phrases[k]]
                    rec["obj"][k] = {"in_fov": ok, "det": bool(d), "hit": bool(d) and _covers(d[0][1], uv),
                                     "score": d[0][0] if d else None}
                out.write(json.dumps(rec) + "\n")
                n += 1
    out.close()
    print("head2d frames", n, "head pose dev", dp, ang)


# ------------------------------------------------------------------------------------------ full eval
def _cam_det(cam, dets, depth, K, p, R):
    """(CamDet or None, extra) from the phrase's detections (best first)."""
    if not dets:
        return None, {"det": False}
    sc, m = dets[0]
    pts = backproject(m, depth, K, p, R, dmin=DMIN[cam])
    ex = {"det": True, "score": sc, "n_mask": int(m.sum()), "n_valid": len(pts)}
    if len(pts) < MIN_VALID_PX:
        return CamDet(cam, sc, len(pts), None, float("nan")), ex
    c = _table(np.median(pts, axis=0))
    dd = depth[m].astype(float)
    dd = dd[np.isfinite(dd) & (dd > DMIN[cam])]
    second = None
    if len(dets) > 1:
        s2, m2 = dets[1]
        p2 = backproject(m2, depth, K, p, R, dmin=DMIN[cam])
        second = (s2, _table(np.median(p2, axis=0)) if len(p2) >= MIN_VALID_PX else None)
    return CamDet(cam, sc, len(pts), c, float(np.median(dd)), second), ex


def _centre_corrected(point, cam_p_table, k):
    g = OBJ_GEOM[k]
    if g["shape"] != "cylinder":
        return point
    v = point[:2] - cam_p_table[:2]
    n = float(np.linalg.norm(v))
    out = point.copy()
    if n > 1e-6:
        out[:2] += g["radius"] * v / n
    return out


def _overlay(path, img, K, p, R, masks, est_w, true_w, title):
    from PIL import Image, ImageDraw
    im = Image.fromarray(img.copy())
    ov = np.array(im)
    colors = [(255, 255, 0), (0, 255, 255), (255, 0, 255), (255, 128, 0), (128, 255, 0)]
    for i, (k, m) in enumerate(masks.items()):
        if m is not None:
            ov[m] = (0.5 * ov[m] + 0.5 * np.array(colors[i % 5])).astype(np.uint8)
    im = Image.fromarray(ov)
    dr = ImageDraw.Draw(im)
    for k, pw in true_w.items():
        u, v, d = project(pw[None], K, p, R)
        if d[0] > 0:
            dr.ellipse([u[0] - 4, v[0] - 4, u[0] + 4, v[0] + 4], outline=(0, 255, 0), width=2)
            dr.text((u[0] + 5, v[0] - 12), f"{k} true", fill=(0, 255, 0))
    for k, pw in est_w.items():
        if pw is None:
            continue
        u, v, d = project(pw[None], K, p, R)
        if d[0] > 0:
            dr.line([u[0] - 6, v[0], u[0] + 6, v[0]], fill=(255, 0, 0), width=2)
            dr.line([u[0], v[0] - 6, u[0], v[0] + 6], fill=(255, 0, 0), width=2)
    dr.text((4, 4), title, fill=(255, 255, 255))
    im.save(path)


def cmd_eval(a):
    from .seg import Sam31Image
    Ks = _intr()
    phrases = load_phrases(a.out)
    sam = Sam31Image()
    os.makedirs(f"{a.out}/frames", exist_ok=True)
    out = open(f"{a.out}/eval.jsonl", "w")
    want_frames = {(0, "P0"), (3, "P1"), (6, "P2")}
    for kind in ("P0", "P1", "P2"):
        root = f"{a.r1}/{kind}"
        for f in sorted(glob.glob(f"{root}/ep*.r1.npz"), key=lambda x: int(x.split("ep")[-1].split(".")[0])):
            seed = int(f.split("ep")[-1].split(".")[0])
            z = np.load(f)
            lines = _lines(f"{root}/ep{seed}.jsonl")
            assert list(z["k"]) == [ln["k"] for ln in lines]
            tr, ps = Tracker(), PredicateState()
            for i, ln in enumerate(lines):
                st = ln["state"]
                present = st["present"]
                truth = {k: np.asarray(st["obs"]["raw"]["objs"][k]["pos"], float) for k in present}
                rec = {"seed": seed, "kind": kind, "k": ln["k"], "phase": ln["phase"], "obj": {}, "lat": {}}
                det, masks = {}, {HEAD: {}, WRIST: {}}
                tsam = 0.0
                segs, depth, poses = {}, {}, {}
                for cam in (HEAD, WRIST):
                    img = _img(root, ln["images"][cam])
                    depth[cam] = z[f"depth_{cam}"][i].astype(np.float32)
                    poses[cam] = (z[f"campos_{cam}"][i], z[f"camR_{cam}"][i])
                    segs[cam], tm = sam.segment(img, [phrases[k] for k in present])
                    rec["lat"][cam] = tm
                    tsam += tm["encode_ms"] + tm["ground_ms"]
                t0 = time.perf_counter()
                est = {}
                for k in present:
                    per = {}
                    for cam in (HEAD, WRIST):
                        p, R = poses[cam]
                        d, ex = _cam_det(cam, segs[cam][phrases[k]], depth[cam], Ks[cam], p, R)
                        per[cam] = d
                        masks[cam][k] = segs[cam][phrases[k]][0][1] if ex["det"] else None
                        ok, _ = _in_fov(_world(truth[k]), Ks[cam], p, R)
                        ex["in_fov"] = ok
                        if d is not None and d.point is not None:
                            ex["err_m"] = (d.point - truth[k]).tolist()
                            ex["depth_med"] = d.depth_med
                            cc = _centre_corrected(d.point, _table(p), k)
                            ex["err_corr_m"] = (cc - truth[k]).tolist()
                        rec["obj"].setdefault(k, {"cams": {}})["cams"][cam] = ex
                    fz = tr.update(k, fuse(per[HEAD], per[WRIST]))
                    est[k] = fz
                    rec["obj"][k].update(source=fz["source"], occluded=fz["occluded"],
                                         id_uncertain=fz["id_uncertain"],
                                         err_m=None if fz["pos"] is None else (fz["pos"] - truth[k]).tolist())
                e = est_line(ln, est, ps)
                txt = s1_text(e)
                t1 = time.perf_counter()
                rec["lat"]["post_ms"] = (t1 - t0) * 1e3
                rec["lat"]["sam_ms"] = tsam
                rec["lat"]["total_ms"] = tsam + rec["lat"]["post_ms"]
                lab = labels(ln)
                rec["label"] = {q: lab[q] for q in QS}
                try:
                    cr = code_rule_v2(txt)
                    rec["cr_est"] = {q: cr[q] for q in QS}
                except Exception as ex:  # noqa: BLE001 - counted as wrong
                    rec["cr_est"] = {"error": repr(ex)}
                tru = {k: {"pos": truth[k], "occluded": False, "id_uncertain": False} for k in present}
                rec["cr_true_recon"] = {q: code_rule_v2(s1_text(est_line(ln, tru)))[q] for q in QS}
                rec["cr_true_orig"] = {q: code_rule_v2(state_text(ln, "S1", step_cm=0.1))[q] for q in QS}
                rec["pred_est"], rec["pred_true"] = e["pred"], ln["pred"]
                rec["s1_est"] = txt
                out.write(json.dumps(rec) + "\n")
                if (seed, kind) in want_frames and ln["k"] % 4 == 0:
                    for cam in (HEAD, WRIST):
                        p, R = poses[cam]
                        _overlay(f"{a.out}/frames/{kind}_s{seed}_k{ln['k']:03d}_{cam}.png", _img(root, ln["images"][cam]),
                                 Ks[cam], p, R, masks[cam],
                                 {k: None if est[k]["pos"] is None else _world(est[k]["pos"]) for k in present},
                                 {k: _world(truth[k]) for k in present},
                                 f"{kind} s{seed} k{ln['k']} {ln['phase']} {cam}")
            print("EP", kind, seed, len(lines), flush=True)
    out.close()


def cmd_rescore(a):
    """Re-run the state/predicate/S1/code-rule stage on the SAME detections of eval.jsonl (fused estimate =
    truth + stored err_m, flags as stored). For post-hoc fixes of the pure stage only (r1_perception.md §3)."""
    src, dst = f"{a.out}/eval.jsonl", f"{a.out}/{a.eval}"
    assert src != dst
    R = _lines(src)
    lines, cur, out = {}, None, open(dst, "w")
    for r in R:
        key = (r["kind"], r["seed"])
        if key != cur:
            cur, ps = key, PredicateState()
            lines = {ln["k"]: ln for ln in _lines(f"{a.r1}/{r['kind']}/ep{r['seed']}.jsonl")}
        ln = lines[r["k"]]
        st = ln["state"]
        truth = {k: np.asarray(st["obs"]["raw"]["objs"][k]["pos"], float) for k in st["present"]}
        est = {k: {"pos": None if o["err_m"] is None else truth[k] + np.asarray(o["err_m"]),
                   "occluded": o["occluded"], "id_uncertain": o["id_uncertain"], "source": o["source"]}
               for k, o in r["obj"].items()}
        t0 = time.perf_counter()
        e = est_line(ln, est, ps)
        txt = s1_text(e)
        r["lat"]["post_ms_rescore"] = (time.perf_counter() - t0) * 1e3
        try:
            cr = code_rule_v2(txt)
            r["cr_est"] = {q: cr[q] for q in QS}
        except Exception as ex:  # noqa: BLE001
            r["cr_est"] = {"error": repr(ex)}
        tru = {k: {"pos": truth[k], "occluded": False, "id_uncertain": False} for k in st["present"]}
        r["cr_true_recon"] = {q: code_rule_v2(s1_text(est_line(ln, tru)))[q] for q in QS}
        r["pred_est"], r["s1_est"] = e["pred"], txt
        out.write(json.dumps(r) + "\n")
    out.close()
    print("rescored", len(R), "->", dst)


def cmd_latbench(a):
    """Latency diagnostic (post-hoc): the same frames with and without cached text embeddings."""
    from .seg import Sam31Image
    phrases = load_phrases(a.out)
    sam = Sam31Image()
    res = {"as_run": [], "cache_text": []}
    frames = []
    for kind in ("P0", "P1", "P2"):
        root = f"{a.r1}/{kind}"
        for s in range(0, 10, 3):
            for ln in _lines(f"{root}/ep{s}.jsonl"):
                frames.append((root, ln))
    for mode in ("as_run", "cache_text", "as_run", "cache_text"):
        tt = []
        for root, ln in frames:
            t = 0.0
            for cam in (HEAD, WRIST):
                _, tm = sam.segment(_img(root, ln["images"][cam]), [phrases[k] for k in ln["state"]["present"]],
                                    cache_text=mode == "cache_text")
                t += tm["encode_ms"] + tm["ground_ms"]
            tt.append(t)
        res[mode] += tt[5:]
    rep = {m: {"n": len(v), "p50": round(_q(np.array(v), 50), 1), "p95": round(_q(np.array(v), 95), 1)}
           for m, v in res.items()}
    json.dump(rep, open(f"{a.out}/latbench.json", "w"), indent=1)
    print(json.dumps(rep))


# ------------------------------------------------------------------------------------------ report
def _q(x, q):
    return float(np.percentile(x, q)) if len(x) else float("nan")


def _mm(errs):
    n = np.linalg.norm(np.asarray(errs, float), axis=1) * 1e3 if errs else np.zeros(0)
    return {"n": int(len(n)), "p50": round(_q(n, 50), 1), "p95": round(_q(n, 95), 1)}


def cmd_report(a):
    R = _lines(f"{a.out}/{a.eval}")
    rep = {"n_snap": len(R)}
    # 3D error by source / camera / phase / object
    by = {}
    for r in R:
        for k, o in r["obj"].items():
            for cam, ex in o["cams"].items():
                if "err_m" in ex:
                    by.setdefault(("cam", cam, "all"), []).append(ex["err_m"])
                    by.setdefault(("cam", cam, k), []).append(ex["err_m"])
                    by.setdefault(("camcorr", cam, "all"), []).append(ex["err_corr_m"])
                    by.setdefault(("camcorr", cam, k), []).append(ex["err_corr_m"])
            if o["err_m"] is not None and not o["occluded"]:
                by.setdefault(("fused", o["source"], k), []).append(o["err_m"])
                by.setdefault(("fused", "all", k), []).append(o["err_m"])
                by.setdefault(("fused", "all", "all"), []).append(o["err_m"])
                by.setdefault(("phase", r["phase"], "all"), []).append(o["err_m"])
                by.setdefault(("phase", r["phase"], k), []).append(o["err_m"])
    rep["err"] = {"|".join(k): _mm(v) for k, v in sorted(by.items())}
    rep["axis_bias_mm"] = {"|".join(k): [round(float(x) * 1e3, 1) for x in np.median(np.asarray(v), axis=0)]
                           for k, v in sorted(by.items()) if k[0] in ("cam", "fused") and len(v)}
    # detection miss / false
    det = {}
    for r in R:
        for k, o in r["obj"].items():
            for cam, ex in o["cams"].items():
                if not ex["in_fov"]:
                    continue
                d = det.setdefault(f"{cam}|{k}", {"n": 0, "miss": 0, "far": 0})
                d["n"] += 1
                if "err_m" not in ex:
                    d["miss"] += 1
                elif np.linalg.norm(ex["err_m"]) > 0.10:
                    d["far"] += 1
    rep["det"] = det
    fl = {"occluded": 0, "id_uncertain": 0, "n": 0, "source": {}}
    for r in R:
        for k, o in r["obj"].items():
            fl["n"] += 1
            fl["occluded"] += bool(o["occluded"])
            fl["id_uncertain"] += bool(o["id_uncertain"])
            fl["source"][str(o["source"])] = fl["source"].get(str(o["source"]), 0) + 1
    rep["flags"] = fl
    # predicates
    pa = {}
    for r in R:
        for key, tv in r["pred_true"].items():
            ev = r["pred_est"].get(key, "absent")
            d = pa.setdefault(key, {"n": 0, "agree": 0, "unknown": 0})
            d["n"] += 1
            d["agree"] += ev == tv
            d["unknown"] += ev is None
    rep["pred"] = {k: dict(v, acc=round(v["agree"] / v["n"], 4)) for k, v in sorted(pa.items())}
    # code rule accuracy
    acc = {}
    for src in ("cr_est", "cr_true_recon", "cr_true_orig"):
        for q in QS:
            ok = [r[src].get(q) == r["label"][q] for r in R]
            acc.setdefault(src, {})[q] = round(float(np.mean(ok)), 4)
        acc[src]["mean5"] = round(float(np.mean([acc[src][q] for q in QS])), 4)
    rep["code_rule"] = acc
    by_phase = {}
    for r in R:
        d = by_phase.setdefault(r["phase"], {"n": 0, **{q: 0 for q in QS}})
        d["n"] += 1
        for q in QS:
            d[q] += r["cr_est"].get(q) == r["label"][q]
    rep["code_rule_est_by_phase"] = {p: {"n": d["n"], **{q: round(d[q] / d["n"], 3) for q in QS}}
                                     for p, d in by_phase.items()}
    # latency (skip the first 5 frames = warm-up)
    L = R[5:]
    lat = {}
    for key, f in (("total_ms", lambda r: r["lat"]["total_ms"]), ("sam_ms", lambda r: r["lat"]["sam_ms"]),
                   ("post_ms", lambda r: r["lat"]["post_ms"]),
                   ("head_encode_ms", lambda r: r["lat"][HEAD]["encode_ms"]),
                   ("head_ground_ms", lambda r: r["lat"][HEAD]["ground_ms"]),
                   ("wrist_encode_ms", lambda r: r["lat"][WRIST]["encode_ms"]),
                   ("wrist_ground_ms", lambda r: r["lat"][WRIST]["ground_ms"])):
        x = np.array([f(r) for r in L])
        lat[key] = {"p50": round(_q(x, 50), 1), "p95": round(_q(x, 95), 1), "max": round(float(x.max()), 1)}
    rep["latency"] = lat
    if os.path.exists(f"{a.out}/head2d.jsonl"):
        H = _lines(f"{a.out}/head2d.jsonl")
        h2 = {}
        for r in H:
            for k, o in r["obj"].items():
                if not o["in_fov"]:
                    continue
                d = h2.setdefault(k, {"n": 0, "nodet": 0, "hit": 0})
                d["n"] += 1
                d["nodet"] += not o["det"]
                d["hit"] += o["hit"]
        x = np.array([r["tm"]["encode_ms"] + r["tm"]["ground_ms"] for r in H[5:]])
        rep["head2d"] = {"n_frames": len(H), "obj": h2, "sam_ms": {"p50": round(_q(x, 50), 1),
                                                                   "p95": round(_q(x, 95), 1)}}
    json.dump(rep, open(f"{a.out}/report_{a.eval.replace('.jsonl', '')}.json", "w"), indent=1)
    print(json.dumps(rep, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["probe", "head2d", "eval", "report", "rescore", "latbench"])
    ap.add_argument("--eval", default="eval.jsonl", help="report input / rescore output file name in --out")
    ap.add_argument("--jsel", default="/data/harvest/data/jsel_dev")
    ap.add_argument("--r1", default="/data/harvest/r1/dev")
    ap.add_argument("--out", default="/data/harvest/r1/out")
    a = ap.parse_args(argv)
    assert a.out.startswith("/data/harvest/"), "every file under /data/harvest"
    os.makedirs(a.out, exist_ok=True)
    {"probe": cmd_probe, "head2d": cmd_head2d, "eval": cmd_eval, "report": cmd_report, "rescore": cmd_rescore,
     "latbench": cmd_latbench}[a.mode](a)


if __name__ == "__main__":
    main()
