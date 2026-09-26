"""MolmoAct-on-R2 readiness gates (docs/stage3/molmoact_r2_readiness.md): CPU only, read-only on R2 data.

Subcommands (pod; PYTHONPATH = a code copy of the repo + tools/mar2):
  cam    G-cam: head camera model vs rendered frames, object silhouettes at k0 of eval episodes
  fk     G-fk: URDF FK of the recorded arm joints vs the recorded sim fingertip point
  trace  G-trace: MolmoAct trace labels for every frame of eval episodes (statistics) + overlay sheets
  cond   G-cond (b): in-support alternative-target steering, re-scored from the E-SR0 R2 log (no model run)
  res    G-res: Qwen3-VL image processor on a head frame with a MolmoAct-style overlay (needs transformers)

Nothing here writes to the data folders; outputs go to --out.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mar2_lib as L  # noqa: E402

R2_ROOT = "/data/harvest/r2/train"
URDF = "/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf"
TASKS = ("mug_tray", "mug_marker", "bottle_tray")
VARIANTS = ("standard", "dr")
KINDS = ("P0", "P1", "P2")
W, H = 672, 376
TABLE_TOP_Z = 0.85
CYAN = (0, 255, 255)  # MolmoAct load_image colour on an RGB array


def head_cam():
    from harvest.train import r2_ma2 as M
    return M.HEAD_K, M.HEAD_POS, M.HEAD_R


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def episodes(root=R2_ROOT, split="eval", variants=VARIANTS, tasks=TASKS, kinds=KINDS):
    """Valid episodes (meta success) of one split, sorted by (variant, task, kind, seed)."""
    out = []
    for v in variants:
        for t in tasks:
            for k in kinds:
                for mp in sorted(glob.glob(f"{root}/{v}/{t}/{k}/ep*.meta.json")):
                    m = json.load(open(mp))
                    if not m.get("valid_for_training", m.get("success")):
                        continue
                    if split and m.get("split") != split:
                        continue
                    seed = int(os.path.basename(mp)[2:-10])
                    out.append(dict(variant=v, task=t, kind=k, seed=seed, dir=os.path.dirname(mp), meta=m))
    return out


def load_ep(e):
    z = np.load(f"{e['dir']}/ep{e['seed']}.npz", allow_pickle=True)
    return {k: z[k] for k in z.files}


def img_path(e, k, cam="cam_head"):
    return f"{e['dir']}/img/ep{e['seed']}/f{k:04d}_{cam}.jpg"


def read_img(p):
    from PIL import Image
    return np.asarray(Image.open(p).convert("RGB"))


def phase_at(meta, t):
    ph = "approach"
    for t0, name in meta["phases"]:
        if t + 1e-9 >= t0:
            ph = name
    return ph


def tcp_world(z):
    return np.asarray(z["tcp"], float) + [0.0, 0.0, TABLE_TOP_Z]


# ------------------------------------------------------------------------------------------ G-cam
GEOM = {"o11": ("cyl", 0.05, 0.002), "o3": ("cyl", 0.032, 0.095), "o8": ("cyl", 0.025, 0.10),
        "o5": ("box", (0.18, 0.14, 0.015))}


def object_pose(e, z, oid, k=0):
    if oid == "o11":
        from harvest.sim.tasks import task_layout
        lay = task_layout(e["seed"], e["task"])
        if "o11" not in lay:
            return None
        x, y = lay["o11"][:2]
        return np.array([x, y, TABLE_TOP_Z + 0.001]), np.array([1.0, 0.0, 0.0, 0.0])
    ids = [str(x) for x in z["obj_ids"]]
    if oid not in ids:
        return None
    row = np.asarray(z["obj_pose"][k][ids.index(oid)], float)
    return row[:3], row[3:7]


def on_table(p):
    return TABLE_TOP_Z - 0.01 < p[2] < TABLE_TOP_Z + 0.2 and 0.1 < p[0] < 0.9 and -0.65 < p[1] < 0.45


def silhouette(oid, pos, quat, K, cp, cR):
    g = GEOM[oid]
    P = L.cylinder_points(pos, quat, g[1], g[2]) if g[0] == "cyl" else L.cuboid_points(pos, quat, g[1])
    uvd = L.project(P, K, cp, cR)
    return uvd


def cmd_cam(a):
    K, cp, cR = head_cam()
    rules = L.COLOUR_RULES_V2 if a.rules == "v2" else L.COLOUR_RULES
    sfx = "" if a.rules == "v1" else f"_{a.rules}"
    eps = episodes(split="eval")
    recs, crops = [], []
    for e in eps:
        z = load_ep(e)
        img = read_img(img_path(e, 0))
        objs = ["o3"] + (["o11"] if e["task"] == "mug_marker" else []) + ["o8"] + (["o5"] if e["variant"] == "standard" else [])
        for oid in objs:
            po = object_pose(e, z, oid, 0)
            if po is None or not on_table(po[0]):
                continue
            uvd = silhouette(oid, po[0], po[1], K, cp, cR)
            r = dict(variant=e["variant"], task=e["task"], kind=e["kind"], seed=e["seed"], obj=oid)
            if (uvd[:, 2] <= 0).any() or not ((uvd[:, 0] >= 0) & (uvd[:, 0] < W) & (uvd[:, 1] >= 0) & (uvd[:, 1] < H)).all():
                r["excluded"] = "outside_image"
                recs.append(r)
                continue
            hull = L.convex_hull(uvd[:, :2])
            sil = L.raster_convex(hull, W, H)
            u0, v0 = np.floor(hull.min(0)).astype(int) - 25
            u1, v1 = np.ceil(hull.max(0)).astype(int) + 25
            box = np.zeros((H, W), bool)
            box[max(v0, 0):min(v1, H), max(u0, 0):min(u1, W)] = True
            seg = L.colour_mask(img, oid, rules) & box
            ratio = seg.sum() / max(sil.sum(), 1)
            r.update(sil_px=int(sil.sum()), seg_px=int(seg.sum()), area_ratio=round(float(ratio), 4))
            if not 0.5 <= ratio <= 1.5:
                r["excluded"] = "area_ratio"
                recs.append(r)
                continue
            cs, cg = L.mask_centroid(sil), L.mask_centroid(seg)
            r.update(du=round(cg[0] - cs[0], 3), dv=round(cg[1] - cs[1], 3),
                     err=round(math.hypot(cg[0] - cs[0], cg[1] - cs[1]), 3), iou=round(L.iou(sil, seg), 4),
                     depth_m=round(float(np.median(uvd[:, 2])), 4))
            recs.append(r)
            if len(crops) < 16 and (len(crops) < 4 or oid != "o3") and sum(c[1] == oid for c in crops) < 5:
                crops.append((e, oid, img, hull, seg))
    summ = {}
    for oid in GEOM:
        rr = [r for r in recs if r["obj"] == oid]
        ok = [r for r in rr if "excluded" not in r]
        ex = {}
        for r in rr:
            if "excluded" in r:
                ex[r["excluded"]] = ex.get(r["excluded"], 0) + 1
        s = dict(n_candidates=len(rr), n=len(ok), excluded=ex)
        if ok:
            err = np.array([r["err"] for r in ok])
            s.update(err_median=round(float(np.median(err)), 3), err_p90=round(float(np.quantile(err, 0.9)), 3),
                     err_max=round(float(err.max()), 3),
                     iou_median=round(float(np.median([r["iou"] for r in ok])), 4),
                     iou_p10=round(float(np.quantile([r["iou"] for r in ok], 0.1)), 4),
                     du_mean=round(float(np.mean([r["du"] for r in ok])), 3),
                     dv_mean=round(float(np.mean([r["dv"] for r in ok])), 3),
                     by_variant={v: dict(n=len([r for r in ok if r["variant"] == v]),
                                         err_median=(round(float(np.median([r["err"] for r in ok if r["variant"] == v])), 3)
                                                     if any(r["variant"] == v for r in ok) else None))
                                 for v in VARIANTS})
        summ[oid] = s

    def gate(oid, nmin):
        s = summ[oid]
        return bool(s["n"] >= nmin and s.get("err_median", 99) <= 1.5 + 1e-12 and s.get("err_p90", 99) <= 3.0 + 1e-12
                    and s.get("iou_median", 0) >= 0.85 - 1e-12)

    verdict = dict(marker=gate("o11", 30), mug=gate("o3", 30), tray=gate("o5", 20), bottle=gate("o8", 20))
    verdict["PASS"] = verdict["marker"] and verdict["mug"]
    out = dict(gate="G-cam", utc=utc(), rules=a.rules, episodes=len(eps), summary=summ, verdict=verdict,
               camera=dict(K=K, pos=[float(x) for x in cp], R=np.asarray(cR).tolist()))
    os.makedirs(a.out, exist_ok=True)
    json.dump(out, open(f"{a.out}/gcam{sfx}.json", "w"), indent=1)
    with open(f"{a.out}/gcam{sfx}_records.jsonl", "w") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")
    cam_sheet(crops, f"{a.out}/gcam{sfx}_sheet.jpg")
    print(json.dumps(dict(summary=summ, verdict=verdict), indent=1))


def cmd_camdiag(a):
    """Diagnostic crops for chosen (variant/task/kind/seed/obj) measurements (after the gate, for looking)."""
    K, cp, cR = head_cam()
    rules = L.COLOUR_RULES_V2 if a.rules == "v2" else L.COLOUR_RULES
    crops = []
    for spec in a.ids.split(","):
        v, t, k, seed, oid = spec.split("/")
        e = dict(variant=v, task=t, kind=k, seed=int(seed), dir=f"{R2_ROOT}/{v}/{t}/{k}")
        z = load_ep(e)
        img = read_img(img_path(e, 0))
        po = object_pose(e, z, oid, 0)
        uvd = silhouette(oid, po[0], po[1], K, cp, cR)
        hull = L.convex_hull(uvd[:, :2])
        crops.append((e, oid, img, hull, L.colour_mask(img, oid, rules)))
    cam_sheet(crops, f"{a.out}/gcam_diag.jpg")


def cam_sheet(crops, path, cw=200, ch=150, scale=2):
    """4x4 crops around measured objects: projected silhouette outline (yellow) and segmentation edge (cyan)."""
    from PIL import Image, ImageDraw
    sheet = Image.new("RGB", (4 * cw * scale // 2, 4 * ch * scale // 2), (0, 0, 0))
    for i, (e, oid, img, hull, seg) in enumerate(crops[:16]):
        c = np.mean(hull, 0)
        u0 = int(np.clip(c[0] - cw / 4, 0, W - cw / 2))
        v0 = int(np.clip(c[1] - ch / 4, 0, H - ch / 2))
        im = img.copy()
        edge = seg & ~(np.roll(seg, 1, 0) & np.roll(seg, -1, 0) & np.roll(seg, 1, 1) & np.roll(seg, -1, 1))
        im[edge] = (0, 255, 255)
        pim = Image.fromarray(im)
        d = ImageDraw.Draw(pim)
        d.line([tuple(p) for p in hull] + [tuple(hull[0])], fill=(255, 255, 0), width=1)
        crop = pim.crop((u0, v0, u0 + cw // 2, v0 + ch // 2)).resize((cw * scale // 2, ch * scale // 2), Image.NEAREST)
        dd = ImageDraw.Draw(crop)
        dd.text((3, 2), f"{e['variant'][:3]} {e['task']} {e['seed']} {oid}", fill=(255, 255, 255))
        sheet.paste(crop, ((i % 4) * cw * scale // 2, (i // 4) * ch * scale // 2))
    sheet.save(path, quality=85)


# ------------------------------------------------------------------------------------------ G-fk
def cmd_fk(a):
    from harvest.train.se2e_data import load_arm_chain
    chain = load_arm_chain(a.urdf, "right")
    rng = np.random.default_rng(0)
    fit_eps = episodes(split="fit")
    fit_eps = [fit_eps[i] for i in sorted(rng.choice(len(fit_eps), size=min(a.n_fit, len(fit_eps)), replace=False))]
    test_eps = episodes(split="eval")
    test_eps = [test_eps[i] for i in sorted(rng.choice(len(test_eps), size=min(a.n_test, len(test_eps)), replace=False))]

    def stack(eps, step):
        P, R, T, G = [], [], [], []
        for e in eps:
            z = load_ep(e)
            p, Rm = L.fk_pose(chain, np.asarray(z["q"], float)[::step])
            P.append(p), R.append(Rm), T.append(tcp_world(z)[::step]), G.append(np.asarray(z["grip"], float)[::step, 0])
        return np.concatenate(P), np.concatenate(R), np.concatenate(T), np.concatenate(G)

    Pf, Rf, Tf, _ = stack(fit_eps, 5)
    o, t = L.fit_offset(Pf, Rf, Tf)
    Pt, Rt, Tt, Gt = stack(test_eps, 1)
    res = np.linalg.norm(L.apply_offset(Pt, Rt, o, t) - Tt, axis=1)
    res_fit = np.linalg.norm(L.apply_offset(Pf, Rf, o, t) - Tf, axis=1)
    K, cp, cR = head_cam()
    uv_fk = L.project(L.apply_offset(Pt, Rt, o, t), K, cp, cR)
    uv_tcp = L.project(Tt, K, cp, cR)
    px = np.linalg.norm(uv_fk[:, :2] - uv_tcp[:, :2], axis=1)
    open_ = Gt > np.median(Gt)
    s = dict(gate="G-fk", utc=utc(), urdf=a.urdf, n_fit_eps=len(fit_eps), n_test_eps=len(test_eps),
             n_fit_frames=int(len(Pf)), n_test_frames=int(len(Pt)),
             offset_ee_m=[round(float(x), 5) for x in o], base_translation_m=[round(float(x), 5) for x in t],
             fit_res_mm=dict(median=round(float(np.median(res_fit)) * 1e3, 3), p95=round(float(np.quantile(res_fit, 0.95)) * 1e3, 3)),
             test_res_mm=dict(median=round(float(np.median(res)) * 1e3, 3), p95=round(float(np.quantile(res, 0.95)) * 1e3, 3),
                              max=round(float(res.max()) * 1e3, 3),
                              open_median=round(float(np.median(res[open_])) * 1e3, 3),
                              closed_median=round(float(np.median(res[~open_])) * 1e3, 3)),
             test_head_px=dict(median=round(float(np.median(px)), 3), p95=round(float(np.quantile(px, 0.95)), 3)))
    s["PASS"] = bool(s["test_res_mm"]["median"] <= 2.0 + 1e-12 and s["test_res_mm"]["p95"] <= 5.0 + 1e-12)
    # diagnosis (after the gate, not part of it): free base rotation too
    Rb, tb, ob = L.fit_rigid_offset(Pf, Rf, Tf)
    res2 = np.linalg.norm(L.apply_rigid_offset(Pt, Rt, Rb, tb, ob) - Tt, axis=1)
    ang = math.degrees(math.acos(np.clip((np.trace(Rb) - 1) / 2, -1, 1)))
    s["diag_free_rotation"] = dict(base_rot_deg=round(ang, 3), R=np.round(Rb, 5).tolist(),
                                   offset_ee_m=[round(float(x), 5) for x in ob],
                                   test_res_mm=dict(median=round(float(np.median(res2)) * 1e3, 3),
                                                    p95=round(float(np.quantile(res2, 0.95)) * 1e3, 3)))
    # 0.5 s displacement agreement (15 frames): |(FK_end(k+15) - FK_end(k)) - (tcp(k+15) - tcp(k))|, per test episode
    derr, dlen = [], []
    for e in test_eps:
        z = load_ep(e)
        q = np.asarray(z["q"], float)
        p, Rm = L.fk_pose(chain, q)
        fkp = L.apply_offset(p, Rm, o, t)
        tw = tcp_world(z)
        dfk, dtc = fkp[15:] - fkp[:-15], tw[15:] - tw[:-15]
        derr += list(np.linalg.norm(dfk - dtc, axis=1))
        dlen += list(np.linalg.norm(dtc, axis=1))
    derr, dlen = np.array(derr), np.array(dlen)
    mv = dlen >= 0.01
    s["diag_disp_0p5s_mm"] = dict(n=int(len(derr)), median=round(float(np.median(derr)) * 1e3, 3),
                                  p95=round(float(np.quantile(derr, 0.95)) * 1e3, 3),
                                  moving_ge_1cm_median=round(float(np.median(derr[mv])) * 1e3, 3),
                                  moving_rel_median=round(float(np.median(derr[mv] / dlen[mv])), 4))
    os.makedirs(a.out, exist_ok=True)
    json.dump(s, open(f"{a.out}/gfk.json", "w"), indent=1)
    print(json.dumps(s, indent=1))


# ------------------------------------------------------------------------------------------ G-trace
def ep_uv(z):
    K, cp, cR = head_cam()
    return L.project(tcp_world(z), K, cp, cR)


def cmd_trace(a):
    eps = episodes(split="eval")
    n_frames = n_in = 0
    by_phase, by_task = {}, {}
    lens, plen, drops, depth = [], [], 0, []
    end_err = []
    for e in eps:
        z = load_ep(e)
        uvd = ep_uv(z)
        tr = L.trace_labels(uvd[:, :2], W, H)
        t = np.asarray(z["t"], float)
        inside = [L.in_image(u, v, W, H) for u, v in uvd[:, :2]]
        for k in range(len(tr)):
            ph = phase_at(e["meta"], t[k])
            by_phase.setdefault(ph, [0, 0])
            by_phase[ph][0] += 1
            by_phase[ph][1] += int(inside[k])
            key = f"{e['variant']}/{e['task']}"
            by_task.setdefault(key, [0, 0])
            by_task[key][0] += 1
            by_task[key][1] += int(inside[k])
            n_valid_future = sum(inside[k:])
            lens.append((len(tr[k]), n_valid_future))
            if n_valid_future < len(inside) - k:
                drops += 1
            if len(tr[k]) >= 2:
                q = np.array([L.from_u255(p, W, H) for p in tr[k]])
                plen.append(float(np.linalg.norm(np.diff(q, axis=0), axis=1).sum()))
        n_frames += len(tr)
        n_in += sum(inside)
        depth += list(uvd[:, 2])
    L5_ok = all(l == min(5, nv) for l, nv in lens if nv > 0)
    s = dict(gate="G-trace", utc=utc(), episodes=len(eps), frames=n_frames,
             current_in_image=round(n_in / n_frames, 5),
             in_image_by_phase={k: round(v[1] / v[0], 4) for k, v in by_phase.items()},
             frames_by_phase={k: v[0] for k, v in by_phase.items()},
             in_image_by_task={k: round(v[1] / v[0], 4) for k, v in by_task.items()},
             trace_len_rule_ok=bool(L5_ok),
             trace_len_hist={str(n): int(sum(1 for l, _ in lens if l == n)) for n in range(0, 6)},
             frames_with_dropped_future=drops,
             trace_px_length=dict(median=round(float(np.median(plen)), 1), p10=round(float(np.quantile(plen, 0.1)), 1),
                                  p90=round(float(np.quantile(plen, 0.9)), 1)),
             ee_depth_m=dict(min=round(float(np.min(depth)), 3), median=round(float(np.median(depth)), 3),
                             max=round(float(np.max(depth)), 3)),
             px_per_cm_at_median_depth=round(367.0 * 0.01 / float(np.median(depth)), 2),
             quantisation_px=dict(u=round((W - 1) / 255 / 2, 3), v=round((H - 1) / 255 / 2, 3)))
    s["PASS_stats"] = bool(s["current_in_image"] >= 0.95 - 1e-12 and L5_ok)
    os.makedirs(a.out, exist_ok=True)
    json.dump(s, open(f"{a.out}/gtrace.json", "w"), indent=1)
    print(json.dumps(s, indent=1))
    trace_sheets(a)


def draw_molmo(img, trace):
    """I+ = I (+) trace exactly as MolmoAct load_image: 0..255 -> pixel index rint(q * (W - 1) / 255), cv2.line
    (0, 255, 255) RGB, thickness 2, LINE_AA, only when >= 2 points."""
    import cv2
    out = np.ascontiguousarray(img.copy())
    h, w = out.shape[:2]
    pts = np.rint(np.asarray(trace, np.float32) * np.array([(w - 1) / 255.0, (h - 1) / 255.0], np.float32)).astype(int)
    if len(pts) >= 2:
        for i in range(len(pts) - 1):
            cv2.line(out, tuple(int(x) for x in pts[i]), tuple(int(x) for x in pts[i + 1]), CYAN, thickness=2,
                     lineType=cv2.LINE_AA)
    return out, pts


def pick_frame(meta, t, phase):
    """First frame index at or after (phase start + 0.1 s), else None."""
    for t0, name in meta["phases"]:
        if name == phase:
            idx = np.nonzero(t >= t0 + 0.1 - 1e-9)[0]
            return int(idx[0]) if len(idx) else None
    return None


def trace_sheets(a):
    from PIL import Image, ImageDraw
    eps = episodes(split="eval")

    def first(v, t, k):
        c = [e for e in eps if e["variant"] == v and e["task"] == t and e["kind"] == k]
        return c[0] if c else None

    plan = {"A_standard": [first("standard", "mug_tray", "P0"), first("standard", "mug_marker", "P0"),
                           first("standard", "bottle_tray", "P0"), first("standard", "mug_tray", "P1")],
            "B_dr": [first("dr", "mug_tray", "P0"), first("dr", "mug_marker", "P0"), first("dr", "bottle_tray", "P0"),
                     first("dr", "mug_marker", "P2")]}
    phases = ("approach", "close", "carry", "open")
    rng = np.random.default_rng(0)
    rand = []
    for _ in range(16):
        e = eps[int(rng.integers(len(eps)))]
        n = len(np.load(f"{e['dir']}/ep{e['seed']}.npz")["t"])
        rand.append((e, int(rng.integers(n))))
    tiles_all = {}
    for name, eplist in plan.items():
        tiles = []
        for e in eplist:
            z = load_ep(e)
            t = np.asarray(z["t"], float)
            for ph in phases:
                k = 0 if ph == "approach" else pick_frame(e["meta"], t, ph)
                tiles.append((e, k))
        tiles_all[name] = tiles
    tiles_all["C_random"] = rand
    log = {}
    for name, tiles in tiles_all.items():
        tw, th = 448, 250
        sheet = Image.new("RGB", (4 * tw, 4 * th), (0, 0, 0))
        log[name] = []
        for i, (e, k) in enumerate(tiles):
            if k is None:
                log[name].append(dict(i=i, missing=True))
                continue
            z = load_ep(e)
            uvd = ep_uv(z)
            tr = L.trace_labels(uvd[:, :2], W, H)[k]
            img = read_img(img_path(e, k))
            out, pts = draw_molmo(img, tr)
            pim = Image.fromarray(out)
            d = ImageDraw.Draw(pim)
            u, v = uvd[k, 0], uvd[k, 1]
            d.ellipse([u - 7, v - 7, u + 7, v + 7], outline=(255, 255, 0), width=2)  # check view: p1 ring
            pim = pim.resize((tw, th), Image.BILINEAR)
            dd = ImageDraw.Draw(pim)
            ph = phase_at(e["meta"], float(np.asarray(z["t"])[k]))
            lab = f"{i:02d} {e['variant'][:3]} {e['task']} {e['kind']} {e['seed']} k{k} {ph}"
            dd.rectangle([0, 0, 7 * len(lab), 12], fill=(0, 0, 0))
            dd.text((2, 0), lab, fill=(255, 255, 255))
            sheet.paste(pim, ((i % 4) * tw, (i // 4) * th))
            log[name].append(dict(i=i, variant=e["variant"], task=e["task"], kind=e["kind"], seed=e["seed"], k=k,
                                  phase=ph, p1_uv=[round(float(u), 1), round(float(v), 1)], trace255=tr,
                                  inside=bool(L.in_image(u, v, W, H))))
        sheet.save(f"{a.out}/trace_sheet_{name}.jpg", quality=80)
    json.dump(log, open(f"{a.out}/trace_sheets.json", "w"), indent=1)
    # one exact model-view example (full resolution, no check marks)
    e, k = tiles_all["A_standard"][4]
    z = load_ep(e)
    tr = L.trace_labels(ep_uv(z)[:, :2], W, H)[k]
    out, _ = draw_molmo(read_img(img_path(e, k)), tr)
    Image.fromarray(out).save(f"{a.out}/trace_modelview.jpg", quality=90)


def cmd_traceend(a):
    """Where the MolmoAct trace ends (diagnosis after the look): episode end (MolmoAct rule, R2 episodes include
    retreat + done) vs the end of the `open` phase (release). xy distance to the place target and head-image px
    distance to the place target centre (table plane)."""
    K, cp, cR = head_cam()
    eps = episodes(split="eval")
    rows = []
    for e in eps:
        z = load_ep(e)
        t = np.asarray(z["t"], float)
        tw = tcp_world(z)
        place = e["meta"]["place"] if "place" in e["meta"] else ("o11" if e["task"] == "mug_marker" else "o5")
        po = object_pose(e, z, place, len(t) - 1)
        rel = None
        for t0, name in e["meta"]["phases"]:
            if name == "retreat":
                rel = int(np.nonzero(t >= t0 - 1e-9)[0][0]) - 1
        if po is None or rel is None:
            continue
        pc = np.array([po[0][0], po[0][1], TABLE_TOP_Z])
        uv_p = L.project(pc, K, cp, cR)[0, :2]
        r = dict(task=e["task"], variant=e["variant"])
        for name, k in (("episode_end", len(t) - 1), ("release", rel)):
            uv = L.project(tw[k], K, cp, cR)[0, :2]
            r[name] = dict(xy_cm=round(float(np.linalg.norm(tw[k][:2] - pc[:2])) * 100, 2),
                           z_cm=round(float(tw[k][2] - TABLE_TOP_Z) * 100, 2),
                           px=round(float(np.linalg.norm(uv - uv_p)), 1))
        r["frames_after_release"] = len(t) - 1 - rel
        rows.append(r)
    s = dict(gate="G-trace(end)", utc=utc(), episodes=len(rows))
    for name in ("episode_end", "release"):
        s[name] = {m: dict(median=round(float(np.median([r[name][m] for r in rows])), 2),
                           p90=round(float(np.quantile([r[name][m] for r in rows], 0.9)), 2)) for m in ("xy_cm", "z_cm", "px")}
    s["frames_after_release"] = dict(median=float(np.median([r["frames_after_release"] for r in rows])),
                                     max=int(max(r["frames_after_release"] for r in rows)))
    json.dump(s, open(f"{a.out}/gtrace_end.json", "w"), indent=1)
    print(json.dumps(s, indent=1))


def cmd_p1crops(a):
    """Zoomed crops (2x) around p1 for every sheet tile (trace_sheets.json), 8 x 6, for the p1 look."""
    from PIL import Image, ImageDraw
    log = json.load(open(f"{a.out}/trace_sheets.json"))
    tiles = [(n, r) for n in ("A_standard", "B_dr", "C_random") for r in log[n] if not r.get("missing")]
    cw, ch = 110, 80
    sheet = Image.new("RGB", (8 * cw * 2, 6 * ch * 2), (0, 0, 0))
    for i, (n, r) in enumerate(tiles[:48]):
        e = dict(variant=r["variant"], task=r["task"], kind=r["kind"], seed=r["seed"],
                 dir=f"{R2_ROOT}/{r['variant']}/{r['task']}/{r['kind']}")
        img = Image.fromarray(read_img(img_path(e, r["k"])))
        u, v = r["p1_uv"]
        d = ImageDraw.Draw(img)
        d.ellipse([u - 2, v - 2, u + 2, v + 2], outline=(255, 255, 0), width=1)
        u0, v0 = int(np.clip(u - cw / 2, 0, W - cw)), int(np.clip(v - ch / 2, 0, H - ch))
        crop = img.crop((u0, v0, u0 + cw, v0 + ch)).resize((2 * cw, 2 * ch), Image.BICUBIC)
        ImageDraw.Draw(crop).text((2, 1), f"{n[0]}{r['i']:02d}", fill=(255, 255, 0))
        sheet.paste(crop, ((i % 8) * 2 * cw, (i // 8) * 2 * ch))
    sheet.save(f"{a.out}/trace_p1_crops.jpg", quality=85)


# ------------------------------------------------------------------------------------------ G-cond (b)
def cmd_cond(a):
    """In-support alternative-target steering, re-scored from the E-SR0 R2 log (C0 checkpoint chunks per forced
    direction). Snapshot geometry (fingertip, objects) from the R2 episode at the snapshot frame."""
    snaps = [json.loads(l) for l in open(a.sr0_log) if '"event": "snap"' in l]
    rows = []
    for s in snaps:
        v, t, kind, ep, kk = s["id"].split("/")
        seed, k = int(ep[2:]), int(kk[1:])
        d = f"{R2_ROOT}/{v}/{t}/{kind}"
        z = np.load(f"{d}/ep{seed}.npz", allow_pickle=True)
        meta = json.load(open(f"{d}/ep{seed}.meta.json"))
        ids = [str(x) for x in z["obj_ids"]]
        tgt = meta["target"]
        alt = "o8" if tgt == "o3" else "o3"
        tw = tcp_world(z)[k]
        ph = phase_at(meta, float(z["t"][k]))
        r = dict(id=s["id"], task=t, variant=v, phase=ph, target=tgt, alt=alt)
        if alt not in ids:
            r["skip"] = "no_alt"
            rows.append(r)
            continue
        pa = np.asarray(z["obj_pose"][k][ids.index(alt)][:3], float)
        pt = np.asarray(z["obj_pose"][k][ids.index(tgt)][:3], float)
        if not on_table(pa):
            r["skip"] = "alt_off_table"
            rows.append(r)
            continue
        to_alt, to_tgt = (pa - tw)[:2], (pt - tw)[:2]
        dist_tgt = float(np.linalg.norm(to_tgt))
        ang = math.degrees(math.acos(np.clip(np.dot(to_alt, to_tgt) / (np.linalg.norm(to_alt) * max(dist_tgt, 1e-9)), -1, 1)))
        r.update(dist_tgt_cm=round(dist_tgt * 100, 2), dist_alt_cm=round(float(np.linalg.norm(to_alt)) * 100, 2),
                 angle_deg=round(ang, 1))
        if ph != "approach" or dist_tgt < 0.10:
            r["skip"] = "not_far"
            rows.append(r)
            continue
        if ang < 75.0:
            r["skip"] = "not_discriminable"
            rows.append(r)
            continue
        dname = L.dir8(*to_alt)
        c = s["c"].get(f"xy:{dname}")
        ctrue = s["c"].get("true")
        ua = to_alt / np.linalg.norm(to_alt)

        def hit(ch):
            xy = np.asarray(ch[:2], float)
            n = np.linalg.norm(xy)
            return int(n >= 1e-4 and float(np.dot(xy, ua)) / n > 0.5)

        r.update(forced=dname, hit=hit(c), leak=hit(ctrue),
                 cos_forced=round(float(np.dot(np.asarray(c[:2]), ua) / max(np.linalg.norm(c[:2]), 1e-12)), 4))
        rows.append(r)
    # (a) reproduction of the E-SR0 A_xy from the same log (pairs: every forced xy direction != label dir_xy)
    pairs = []
    for s in snaps:
        lab = s["labels"]["dir_xy"]
        for j, dn in enumerate(L.DIRS8):
            if dn == lab or f"xy:{dn}" not in s["c"]:
                continue
            ang = math.radians(45.0 * j)
            xy = np.asarray(s["c"][f"xy:{dn}"][:2], float)
            n = np.linalg.norm(xy)
            pairs.append(int(n >= 1e-4 and float(xy @ [math.cos(ang), math.sin(ang)]) / n > 0.5))
    axy = float(np.mean(pairs))
    ok = [r for r in rows if "skip" not in r]
    skips = {}
    for r in rows:
        if "skip" in r:
            skips[r["skip"]] = skips.get(r["skip"], 0) + 1
    hit = L.boot_ci([r["hit"] for r in ok])
    leak = L.boot_ci([r["leak"] for r in ok])
    s = dict(gate="G-cond(b)", utc=utc(), source=a.sr0_log, snapshots=len(snaps), eligible=len(ok), skipped=skips,
             esr0_axy_recount=dict(value=round(axy, 4), pairs=len(pairs)),
             steer_hit=dict(mean=round(hit[0], 4), lo=round(hit[1], 4), hi=round(hit[2], 4)),
             leak_true_decision=dict(mean=round(leak[0], 4), lo=round(leak[1], 4), hi=round(leak[2], 4)),
             by_task={t: dict(n=len([r for r in ok if r["task"] == t]),
                              hit=round(float(np.mean([r["hit"] for r in ok if r["task"] == t])), 4)
                              if any(r["task"] == t for r in ok) else None) for t in TASKS})
    os.makedirs(a.out, exist_ok=True)
    json.dump(s, open(f"{a.out}/gcond_b.json", "w"), indent=1)
    with open(f"{a.out}/gcond_b_rows.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(json.dumps(s, indent=1))


# ------------------------------------------------------------------------------------------ G-res
def cmd_resprep(a):
    """Lossless plain / MolmoAct-overlay pair for G-res (cv2 lives in venv_e3st, transformers in venv_train)."""
    from PIL import Image
    e = episodes(split="eval")[0]
    z = load_ep(e)
    img = read_img(img_path(e, 0))
    tr = L.trace_labels(ep_uv(z)[:, :2], W, H)[0]
    over, _ = draw_molmo(img, tr)
    Image.fromarray(img).save(f"{a.out}/res_plain.png")
    Image.fromarray(over).save(f"{a.out}/res_overlay.png")
    json.dump(dict(episode=f"{e['variant']}/{e['task']}/{e['kind']}/ep{e['seed']}", k=0, trace=tr),
              open(f"{a.out}/res_prep.json", "w"))


def cmd_res(a):
    from PIL import Image
    from transformers import AutoProcessor
    proc = AutoProcessor.from_pretrained(a.model)
    ip = proc.image_processor
    prep = json.load(open(f"{a.out}/res_prep.json"))
    e = dict(variant="", task="", kind="", seed=prep["episode"])
    tr = prep["trace"]
    img = np.asarray(Image.open(f"{a.out}/res_plain.png").convert("RGB"))
    over = np.asarray(Image.open(f"{a.out}/res_overlay.png").convert("RGB"))
    res = {}
    for name, im in (("plain", img), ("overlay", over)):
        x = ip(images=[Image.fromarray(im)], return_tensors="np")
        res[name] = dict(grid_thw=[int(v) for v in np.asarray(x["image_grid_thw"])[0]])
    g = res["overlay"]["grid_thw"]
    patch = int(getattr(ip, "patch_size", 16))
    merge = int(getattr(ip, "merge_size", 2))
    rh, rw = g[1] * patch, g[2] * patch
    # contrast of the line after resizing to the processor's input size (bilinear, as the processor)
    ri = np.asarray(Image.fromarray(img).resize((rw, rh), Image.BICUBIC), float)
    ro = np.asarray(Image.fromarray(over).resize((rw, rh), Image.BICUBIC), float)
    line = np.zeros((H, W), bool)
    diff0 = np.abs(over.astype(float) - img.astype(float)).sum(-1)
    line[diff0 > 60] = True
    lr = np.asarray(Image.fromarray(line.astype(np.uint8) * 255).resize((rw, rh), Image.NEAREST)) > 127
    contrast_native = float(diff0[line].mean()) if line.any() else math.nan
    dres = np.abs(ro - ri).sum(-1)
    contrast_resized = float(dres[lr].mean()) if lr.any() else math.nan
    s = dict(gate="G-res", utc=utc(), model=a.model, episode=prep["episode"],
             native=[H, W], processor_input_hw=[rh, rw], patch=patch, merge=merge,
             visual_tokens=int(g[0] * g[1] * g[2] // merge ** 2), linear_scale=round(min(rh / H, rw / W), 4),
             line_contrast_native=round(contrast_native, 2), line_contrast_resized=round(contrast_resized, 2),
             contrast_kept=round(contrast_resized / contrast_native, 4), trace=tr)
    s["PASS"] = bool(s["linear_scale"] >= 0.9 and s["contrast_kept"] >= 0.5)
    os.makedirs(a.out, exist_ok=True)
    json.dump(s, open(f"{a.out}/gres.json", "w"), indent=1)
    print(json.dumps(s, indent=1))


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=("cam", "camdiag", "fk", "trace", "traceend", "p1crops", "cond", "resprep", "res"))
    p.add_argument("--out", default="/data/harvest/logs/mar2")
    p.add_argument("--urdf", default=URDF)
    p.add_argument("--n-fit", type=int, default=60)
    p.add_argument("--n-test", type=int, default=60)
    p.add_argument("--sr0-log", default="/data/harvest/logs/sr0/sr0_c0.jsonl")
    p.add_argument("--model", default="/data/harvest/models/Qwen3-VL-4B-Instruct")
    p.add_argument("--ids", default="")
    p.add_argument("--rules", default="v1", choices=("v1", "v2"), help="G-cam colour rules (v2 = change 1)")
    a = p.parse_args(argv)
    {"cam": cmd_cam, "camdiag": cmd_camdiag, "fk": cmd_fk, "trace": cmd_trace, "p1crops": cmd_p1crops, "traceend": cmd_traceend, "cond": cmd_cond, "resprep": cmd_resprep, "res": cmd_res}[a.cmd](a)


if __name__ == "__main__":
    main()
