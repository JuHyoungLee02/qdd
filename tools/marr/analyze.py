"""MolmoAct real-data readiness, step 3 (CPU, pod venv_e3st): filters, trace labels, statistics, sheets, colour,
path diversity (plan docs/superpowers/plans/2026-09-26-molmoact-real-readiness.md).

  analyze.py --data D --logs L main      filters F1-F4, labels (trace.labels_segments, end = next release), stats,
                                          blind eye-check sheets (144 points, no filter info), trace sheets, colour,
                                          diversity -> L/analysis.json, L/eye_sample.json, L/*.jpg
  analyze.py --data D --logs L eye --judge J   G-rate / G-filter from the eye judgments J (json {idx: code})
Eye codes: g = on the named gripper, o = on the other arm's gripper, x = elsewhere, n = named gripper not visible.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import random
import time

import numpy as np

from harvest.datagen import trace as TR
from harvest.train import se2e_data as S
from harvest.train import se2e_molmo as M

W, H = 672, 376
CANDIDATES = {"cyan_molmoact": (0, 255, 255), "green_r2": (110, 255, 0), "magenta": (255, 0, 255),
              "yellow": (255, 255, 0)}
RAW = "/data/harvest/data/se2e/raw"
DATASETS = {"RB1": "Task_0001_CoffeeClassification_lerobot", "RB2": "Task_0002_OrderPicking_lerobot"}


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load(data):
    eps = json.load(open(f"{data}/episodes.json"))["episodes"]
    pts = {}
    for x in open(f"{data}/points.jsonl", encoding="utf-8"):
        r = json.loads(x)
        pts[(r["src"], r["ep"], r["k"], r["arm"])] = None if r["point"] is None else tuple(r["point"])
    out = []
    for e in eps:
        z = np.load(f"{data}/eps/{e['src']}_ep{e['ep']:06d}.npz")
        n = e["frames"]
        rec = dict(e, ee={"left": z["ee_l"][:n], "right": z["ee_r"][:n]}, g={"left": z["g_l"][:n], "right": z["g_r"][:n]})
        rec["uv"] = {a: [pts.get((e["src"], e["ep"], k, a), "missing") for k in range(n)] for a in ("left", "right")}
        out.append(rec)
    return out


def img_path(data, e, k):
    return f"{data}/frames/{e['src']}/ep{e['ep']:06d}/f{k:04d}.jpg"


def active_arms(e, fps=10.0):
    """se2e_data.active_arm over the next 1 s per frame."""
    n = e["frames"]
    w = int(round(S.ARM_WINDOW_S * fps))
    return [S.active_arm(e["ee"]["left"][k:k + w + 1], e["ee"]["right"][k:k + w + 1])[0] for k in range(n)]


def run_filters(eps, version="v1"):
    if version == "v2":
        nominal_uv(eps)
    for e in eps:
        if any(p == "missing" for a in e["uv"] for p in e["uv"][a]):
            raise SystemExit(f"points missing for {e['src']} ep {e['ep']}")
        if version == "v1":
            kl, wl, kr, wr, info = M.filter_episode(e["uv"]["left"], e["ee"]["left"], e["uv"]["right"],
                                                    e["ee"]["right"])
        else:
            kl, wl, kr, wr, info = M.filter_nominal(e["uv"]["left"], e["uv"]["right"], e["nom"]["left"],
                                                    e["nom"]["right"])
        e["keep"], e["why"], e["dlt"] = {"left": kl, "right": kr}, {"left": wl, "right": wr}, info
        e["ends"] = {a: M.grip_segment_ends(e["g"][a]) for a in ("left", "right")}
        kept = {a: [p if k else None for p, k in zip(e["uv"][a], e["keep"][a])] for a in ("left", "right")}
        e["labels"] = {a: TR.labels_segments(kept[a], e["ends"][a]) for a in ("left", "right")}
        e["active"] = active_arms(e)


def stats(eps):
    out = {}
    for src in ("RB1", "RB2", "all"):
        es = [e for e in eps if src == "all" or e["src"] == src]
        why = {}
        n_pts = 0
        for e in es:
            for a in ("left", "right"):
                for w in e["why"][a]:
                    why[w] = why.get(w, 0) + 1
                    n_pts += 1
        lab_active, n_fr, lens, end_kept, n_seg = 0, 0, {}, 0, 0
        for e in es:
            for k in range(e["frames"]):
                n_fr += 1
                lab = e["labels"][e["active"][k]][k]
                if lab:
                    lab_active += 1
                    lens[len(lab)] = lens.get(len(lab), 0) + 1
            for a in ("left", "right"):
                rels = sorted({x for x in e["ends"][a] if x is not None})
                n_seg += len(rels)
                end_kept += sum(e["keep"][a][r] for r in rels)
        fits = [e["dlt"] for e in es]
        out[src] = {"episodes": len(es), "frames": n_fr, "points": n_pts,
                    "reasons": {k: [v, round(v / n_pts, 4)] for k, v in sorted(why.items())},
                    "kept_frac": round(why.get("ok", 0) / max(n_pts, 1), 4),
                    "active_arm_label_frac": round(lab_active / max(n_fr, 1), 4), "label_len_hist": lens,
                    "releases": n_seg, "release_point_kept_frac": round(end_kept / max(n_seg, 1), 4),
                    "fit_episodes": sum(bool(f.get("fit", f.get("offset") is not None)) for f in fits),
                    "dlt_median_resid_px": [f.get("median_resid_px") for f in fits],
                    "dlt_inlier_frac": [f.get("inlier_frac") for f in fits],
                    "offsets": [f.get("offset") for f in fits]}
    return out


def eye_sample(eps, n_per=36, seed=0):
    """Stratified src x arm, distinct episodes first (cycled), random frame; BLIND (no filter fields)."""
    rng = random.Random(seed)
    out = []
    for src in ("RB1", "RB2"):
        es = [e for e in eps if e["src"] == src]
        for arm in ("left", "right"):
            order = es[:]
            rng.shuffle(order)
            for i in range(n_per):
                e = order[i % len(order)]
                k = rng.randrange(e["frames"])
                out.append({"idx": len(out), "src": src, "ep": e["ep"], "k": k, "arm": arm,
                            "point": e["uv"][arm][k]})
    return out


def _font():
    from PIL import ImageFont
    try:
        return ImageFont.load_default(size=14)
    except TypeError:  # older Pillow
        return ImageFont.load_default()


def eye_sheets(data, logs, sample, per=12, prefix="eye_sheet"):
    from PIL import Image, ImageDraw
    tw, th = 448, 250
    font = _font()
    names = []
    for s0 in range(0, len(sample), per):
        sheet = Image.new("RGB", (3 * tw, 4 * th), (0, 0, 0))
        for i, s in enumerate(sample[s0:s0 + per]):
            e = {"src": s["src"], "ep": s["ep"]}
            im = Image.open(img_path(data, e, s["k"])).convert("RGB")
            d = ImageDraw.Draw(im)
            if s["point"] is not None:
                u, v = s["point"]
                d.ellipse([u - 9, v - 9, u + 9, v + 9], outline=(255, 0, 255), width=3)
                d.line([u - 14, v, u + 14, v], fill=(255, 255, 0), width=1)
                d.line([u, v - 14, u, v + 14], fill=(255, 255, 0), width=1)
            im = im.resize((tw, th))
            d = ImageDraw.Draw(im)
            lab = f"#{s['idx']} {s['src']} ep{s['ep']} k{s['k']} {s['arm'].upper()}" + (" NONE" if s["point"] is None else "")
            d.rectangle([0, 0, 8 * len(lab) + 4, 17], fill=(0, 0, 0))
            d.text((2, 1), lab, fill=(255, 255, 255), font=font)
            sheet.paste(im, ((i % 3) * tw, (i // 3) * th))
        p = f"{logs}/{prefix}_{s0 // per:02d}.jpg"
        sheet.save(p, quality=85)
        names.append(p)
    return names


def trace_sheets(data, logs, eps, rgb, seed=0, sfx=""):
    """Per source 12 tiles: kept-point traces of the active arm at a segment's start / middle / just before release."""
    from PIL import Image, ImageDraw
    rng = random.Random(seed)
    tw, th = 448, 250
    font = _font()
    names, log = [], []
    for src in ("RB1", "RB2"):
        tiles = []
        es = [e for e in eps if e["src"] == src]
        rng.shuffle(es)
        for e in es:
            for a in ("left", "right"):
                rels = sorted({x for x in e["ends"][a] if x is not None})
                for r in rels:
                    ks = [k for k in range(e["frames"]) if e["ends"][a][k] == r and e["labels"][a][k]]
                    if len(ks) < 10 or len(tiles) >= 12:
                        continue
                    for k in (ks[0], ks[len(ks) // 2], ks[-3]):
                        tiles.append((e, a, k, r))
                    break
            if len(tiles) >= 12:
                break
        sheet = Image.new("RGB", (3 * tw, 4 * th), (0, 0, 0))
        for i, (e, a, k, r) in enumerate(tiles[:12]):
            im = np.asarray(Image.open(img_path(data, e, k)).convert("RGB"))
            out = TR.draw(im, e["labels"][a][k], rgb=rgb)
            pim = Image.fromarray(out)
            d = ImageDraw.Draw(pim)
            p1 = e["uv"][a][k]
            if p1 is not None:
                d.ellipse([p1[0] - 6, p1[1] - 6, p1[0] + 6, p1[1] + 6], outline=(255, 255, 255), width=2)
            pim = pim.resize((tw, th))
            d = ImageDraw.Draw(pim)
            lab = f"{src} ep{e['ep']} {a} k{k} rel{r} n{len(e['labels'][a][k])}"
            d.rectangle([0, 0, 8 * len(lab) + 4, 17], fill=(0, 0, 0))
            d.text((2, 1), lab, fill=(255, 255, 255), font=font)
            sheet.paste(pim, ((i % 3) * tw, (i // 3) * th))
            log.append({"src": src, "ep": e["ep"], "arm": a, "k": k, "release": r, "trace255": e["labels"][a][k]})
        p = f"{logs}/trace_sheet_{src}{sfx}.jpg"
        sheet.save(p, quality=85)
        names.append(p)
    # the release frames themselves: where the trace ends (point at the release frame), 12 tiles over both sources
    rel_tiles = []
    for e in eps:
        for a in ("left", "right"):
            for r in sorted({x for x in e["ends"][a] if x is not None}):
                rel_tiles.append((e, a, r))
    rng.shuffle(rel_tiles)
    sheet = Image.new("RGB", (3 * tw, 4 * th), (0, 0, 0))
    for i, (e, a, r) in enumerate(rel_tiles[:12]):
        pim = Image.open(img_path(data, e, r)).convert("RGB")
        d = ImageDraw.Draw(pim)
        p = e["uv"][a][r]
        if p is not None:
            col = (0, 255, 0) if e["keep"][a][r] else (255, 0, 0)
            d.ellipse([p[0] - 9, p[1] - 9, p[0] + 9, p[1] + 9], outline=col, width=3)
        pim = pim.resize((tw, th))
        d = ImageDraw.Draw(pim)
        lab = f"REL {e['src']} ep{e['ep']} {a} k{r} g={e['g'][a][r]:.2f} {'kept' if e['keep'][a][r] else e['why'][a][r]}"
        d.rectangle([0, 0, 8 * len(lab) + 4, 17], fill=(0, 0, 0))
        d.text((2, 1), lab, fill=(255, 255, 255), font=font)
        sheet.paste(pim, ((i % 3) * tw, (i // 3) * th))
    p = f"{logs}/release_sheet{sfx}.jpg"
    sheet.save(p, quality=85)
    names.append(p)
    json.dump(log, open(f"{logs}/trace_sheets{sfx}.json", "w"), indent=1)
    return names


def colour(data, eps, n=200, seed=0, thr=60.0):
    from PIL import Image
    rng = random.Random(seed)
    frames = [(e, rng.randrange(e["frames"])) for e in eps for _ in range(max(1, n // len(eps)))][:n]
    frac = {k: [] for k in CANDIDATES}
    for e, k in frames:
        im = np.asarray(Image.open(img_path(data, e, k)).convert("RGB"), float)
        for name, c in CANDIDATES.items():
            frac[name].append(float((np.linalg.norm(im - np.array(c, float), axis=-1) < thr).mean()))
    res = {k: {"mean": round(float(np.mean(v)), 6), "p95": round(float(np.quantile(v, 0.95)), 6),
               "max": round(float(np.max(v)), 6)} for k, v in frac.items()}
    ok = {k: v for k, v in res.items() if v["mean"] <= 0.001}
    best = min(ok, key=lambda k: ok[k]["mean"]) if ok else None
    return {"frames": len(frames), "thr_rgb": thr, "fraction_within_thr": res, "chosen": best,
            "chosen_rgb": CANDIDATES.get(best)}


def segments(e, a):
    """(start frame, release frame, kept image points of the arm over the segment)."""
    out, start = [], 0
    for r in sorted({x for x in e["ends"][a] if x is not None}):
        pts = [e["uv"][a][k] for k in range(start, r + 1) if e["keep"][a][k]]
        if len(pts) >= 5:
            out.append((start, r, np.asarray(pts, float)))
        start = r + 1
    return out


def diversity(eps, near_px=40.0):
    segs = []
    for e in eps:
        for a in ("left", "right"):
            for s0, r, p in segments(e, a):
                segs.append({"src": e["src"], "task": e["task"], "arm": a, "ep": e["ep"], "p": p})
    pairs = []
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            A, B = segs[i], segs[j]
            if (A["src"], A["task"], A["arm"]) != (B["src"], B["task"], B["arm"]) or A["ep"] == B["ep"]:
                continue
            if math.dist(A["p"][0], B["p"][0]) <= near_px and math.dist(A["p"][-1], B["p"][-1]) <= near_px:
                d = max(M.path_divergence_px(A["p"], B["p"]), M.path_divergence_px(B["p"], A["p"]))
                pairs.append({"src": A["src"], "div_px": round(d, 1)})
    out = {"segments": len(segs), "segments_by_src": {s: sum(x["src"] == s for x in segs) for s in ("RB1", "RB2")},
           "same_start_end_pairs": len(pairs)}
    for s in ("RB1", "RB2"):
        v = [p["div_px"] for p in pairs if p["src"] == s]
        out[s] = {"pairs": len(v), "median_div_px": float(np.median(v)) if v else None,
                  "p90_div_px": float(np.quantile(v, 0.9)) if v else None,
                  "frac_div_ge_40px": round(float(np.mean(np.array(v) >= 40)), 4) if v else None}
    return out


def scene_pairs(thr_list=(3.0, 5.0, 8.0)):
    """All episodes of both datasets: first cam_head frame (decoded), 84 x 47 grey, mean |diff| between every pair;
    near-identical first frames with DIFFERENT instructions = 'same scene, different target' candidates."""
    import av
    from PIL import Image
    res = {}
    for src, name in DATASETS.items():
        root = f"{RAW}/{name}"
        info = json.load(open(f"{root}/meta/info.json"))
        eps = [json.loads(x) for x in open(f"{root}/meta/episodes.jsonl")]
        tasks = {json.loads(x)["task_index"]: json.loads(x)["task"] for x in open(f"{root}/meta/tasks.jsonl")}
        import pyarrow.parquet as pq
        ims, instr, ids = [], [], []
        for e in eps:
            ep = e["episode_index"]
            c = ep // info["chunks_size"]
            vid = f"{root}/" + info["video_path"].format(episode_chunk=c, episode_index=ep,
                                                         video_key="observation.images.cam_head")
            try:
                with av.open(vid) as cont:
                    fr = next(cont.decode(video=0)).to_image()
            except Exception:  # noqa: BLE001  (a broken file is just skipped and counted)
                continue
            t = pq.read_table(f"{root}/" + info["data_path"].format(episode_chunk=c, episode_index=ep),
                              columns=["task_index"]).to_pydict()
            ims.append(np.asarray(fr.convert("L").resize((84, 47)), float))
            instr.append(tasks[int(t["task_index"][0])])
            ids.append(ep)
        X = np.stack(ims).reshape(len(ims), -1)
        n = len(X)
        dmin, near = [], {t: {"same_instr": 0, "diff_instr": 0} for t in thr_list}
        examples = []
        for i in range(n):
            d = np.abs(X - X[i]).mean(1)
            d[i] = np.inf
            dmin.append(float(d.min()))
            for j in np.nonzero(d <= max(thr_list))[0]:
                if j <= i:
                    continue
                for t in thr_list:
                    if d[j] <= t:
                        near[t]["same_instr" if instr[i] == instr[j] else "diff_instr"] += 1
                if instr[i] != instr[j] and d[j] <= thr_list[0] and len(examples) < 6:
                    examples.append({"a": ids[i], "b": ids[int(j)], "mad": round(float(d[j]), 2),
                                     "instr_a": instr[i], "instr_b": instr[int(j)]})
        res[src] = {"episodes": n, "instructions": len(set(instr)), "nn_mad_median": round(float(np.median(dmin)), 2),
                    "nn_mad_p10": round(float(np.quantile(dmin, 0.1)), 2), "near_pairs": near,
                    "diff_instr_examples": examples}
    return res


def cmd_main(a):
    """v1 (pre-registered): sample 1 (seed 0, 36 per src x arm). v2 (change 1): filter v2, NEW blind sample 2 (seed 1,
    24 per src x arm, frames of sample 1 excluded), outputs with suffix _v2."""
    t0 = time.time()
    v = a.filter
    sfx = "" if v == "v1" else "_v2"
    eps = load(a.data)
    run_filters(eps, v)
    st = stats(eps)
    if v == "v1":
        sample = eye_sample(eps)
    else:
        old = {(s["src"], s["ep"], s["k"], s["arm"]) for s in json.load(open(f"{a.logs}/eye_sample.json"))}
        sample = [s for s in eye_sample(eps, n_per=30, seed=1) if (s["src"], s["ep"], s["k"], s["arm"]) not in old]
        per = {}
        keep = []
        for s in sample:  # 24 per stratum after removing any overlap with sample 1
            key = (s["src"], s["arm"])
            if per.get(key, 0) < 24:
                per[key] = per.get(key, 0) + 1
                keep.append(s)
        sample = [dict(s, idx=i) for i, s in enumerate(keep)]
    json.dump(sample, open(f"{a.logs}/eye_sample{sfx}.json", "w"), indent=1)
    eye = eye_sheets(a.data, a.logs, sample, prefix=f"eye{sfx}_sheet")
    col = colour(a.data, eps)
    rgb = tuple(col["chosen_rgb"]) if col["chosen_rgb"] else TR.TRACE_RGB
    tr = trace_sheets(a.data, a.logs, eps, rgb, sfx=sfx)
    div = diversity(eps)
    sc = scene_pairs() if v == "v1" else None
    per_ep = [{"src": e["src"], "ep": e["ep"], "task": e["task"], "frames": e["frames"], "split": e["split"],
               "filter_info": {k: val for k, val in e["dlt"].items() if k != "M"},
               "kept": {x: int(sum(e["keep"][x])) for x in ("left", "right")},
               "releases": {x: len({y for y in e["ends"][x] if y is not None}) for x in ("left", "right")}}
              for e in eps]
    out = {"utc": utc(), "filter": v, "stats": st, "colour": col, "diversity": div, "scenes": sc, "episodes": per_ep,
           "sheets": {"eye": eye, "trace": tr}, "seconds": round(time.time() - t0, 1)}
    json.dump(out, open(f"{a.logs}/analysis{sfx}.json", "w"), indent=1)
    # keep the filter decisions for the eye evaluation (read only after the eye judgments are written)
    dec = {f"{e['src']}_{e['ep']}_{k}_{x}": [e["keep"][x][k], e["why"][x][k]] for e in eps for x in ("left", "right")
           for k in range(e["frames"])}
    json.dump(dec, open(f"{a.logs}/filter_decisions{sfx}.json", "w"))
    labels = {f"{e['src']}_ep{e['ep']:06d}": {x: e["labels"][x] for x in ("left", "right")} | {"active": e["active"]}
              for e in eps}
    json.dump(labels, open(f"{a.data}/trace_labels{sfx}.json", "w"))
    print(json.dumps({k: v for k, v in out.items() if k in ("stats", "colour", "diversity", "seconds")})[:4000])


def boot(x, n=10000, seed=0):
    x = np.asarray(x, float)
    if len(x) == 0:
        return [None, None, None]
    rng = np.random.default_rng(seed)
    m = x[rng.integers(0, len(x), (n, len(x)))].mean(1)
    return [round(float(x.mean()), 4), round(float(np.quantile(m, 0.025)), 4), round(float(np.quantile(m, 0.975)), 4)]


def cmd_eye(a):
    """--sample-sfx '' / '_v2' picks the eye sample; --filter picks the decisions evaluated (v1 or v2)."""
    sample = json.load(open(f"{a.logs}/eye_sample{a.sample_sfx}.json"))
    judge = {int(k): v for k, v in json.load(open(a.judge)).items() if not k.startswith("_")}
    dec = json.load(open(f"{a.logs}/filter_decisions{'' if a.filter == 'v1' else '_v2'}.json"))
    if set(judge) != {s["idx"] for s in sample}:
        raise SystemExit("judgments do not cover the sample exactly")
    rows = []
    for s in sample:
        keep, why = dec[f"{s['src']}_{s['ep']}_{s['k']}_{s['arm']}"]
        rows.append(dict(s, code=judge[s["idx"]], keep=keep, why=why))
    vis = [r for r in rows if r["code"] != "n"]
    err = [r["code"] != "g" for r in vis]
    other = [r["code"] == "o" for r in vis]
    kept = [r for r in vis if r["keep"]]
    correct = [r for r in vis if r["code"] == "g"]
    out = {"utc": utc(), "n": len(rows), "visible": len(vis), "codes": {c: sum(r["code"] == c for r in rows)
                                                                        for c in "goxnu"},
           "raw_error_rate": boot(err), "raw_error_rate_u_as_correct": boot([r["code"] not in "gu" for r in vis]),
           "other_arm_rate": boot(other),
           "kept": len(kept), "kept_error_rate": boot([r["code"] != "g" for r in kept]),
           "kept_error_rate_u_as_correct": boot([r["code"] not in "gu" for r in kept]),
           "kept_codes": {c: sum(r["code"] == c for r in rows if r["keep"]) for c in "goxnu"},
           "correct_retained": boot([r["keep"] for r in correct]),
           "not_visible_kept": sum(r["keep"] for r in rows if r["code"] == "n"),
           "by_src": {s: {"visible": sum(r["src"] == s for r in vis),
                          "raw_error_rate": boot([r["code"] != "g" for r in vis if r["src"] == s]),
                          "kept_error_rate": boot([r["code"] != "g" for r in kept if r["src"] == s])}
                      for s in ("RB1", "RB2")},
           "errors_by_reason": {w: sum(1 for r in vis if r["why"] == w and r["code"] != "g") for w in
                                sorted({r["why"] for r in vis})},
           "correct_by_reason": {w: sum(1 for r in vis if r["why"] == w and r["code"] == "g") for w in
                                 sorted({r["why"] for r in vis})}}
    ke, cr = out["kept_error_rate"][0], out["correct_retained"][0]
    out["G_filter_pass"] = bool(ke is not None and ke <= 0.05 + 1e-12 and cr is not None and cr >= 0.80 - 1e-12)
    json.dump({"summary": out, "rows": rows}, open(f"{a.logs}/eye_eval_{a.filter}{a.sample_sfx or '_s1'}.json", "w"), indent=1)
    print(json.dumps(out, indent=1))


BORDER_PX = 12.0  # points this close to the image border are clamped pointings of an off-image gripper


def _interior(p):
    return p is not None and BORDER_PX <= p[0] <= W - BORDER_PX and BORDER_PX <= p[1] <= H - BORDER_PX


def cmd_camfit(a):
    """Diagnosis after G-filter failed (change 1): is the head camera fixed per SOURCE? One RANSAC DLT per source over
    all episodes (interior points of both arms, no pre-filter), and per episode with the same rule."""
    eps = load(a.data)
    out = {"utc": utc(), "border_px": BORDER_PX, "src": {}, "episodes": []}
    for src in ("RB1", "RB2"):
        X, U, tag = [], [], []
        for e in eps:
            if e["src"] != src:
                continue
            for arm in ("left", "right"):
                for k, p in enumerate(e["uv"][arm]):
                    if _interior(p):
                        X.append(e["ee"][arm][k])
                        U.append(p)
                        tag.append((e["ep"], arm, k))
        X, U = np.asarray(X), np.asarray(U)
        for thr in (15.0, 30.0):
            Mf, inl, res = M.ransac_dlt(X, U, thr=thr, iters=5000, seed=0)
            per = {}
            for (ep, arm, k), ok in zip(tag, inl):
                per.setdefault(ep, []).append(bool(ok))
            out["src"].setdefault(src, {})[f"thr{int(thr)}"] = {
                "points": len(X), "inlier_frac": round(float(inl.mean()), 4),
                "median_resid_inlier_px": round(float(np.median(res[inl])), 3) if inl.any() else None,
                "per_episode_inlier_frac": {int(ep): round(float(np.mean(v)), 3) for ep, v in sorted(per.items())}}
    for e in eps:
        X, U = [], []
        for arm in ("left", "right"):
            for k, p in enumerate(e["uv"][arm]):
                if _interior(p):
                    X.append(e["ee"][arm][k])
                    U.append(p)
        Mf, inl, res = M.ransac_dlt(np.asarray(X), np.asarray(U), thr=15.0, iters=5000, seed=0)
        out["episodes"].append({"src": e["src"], "ep": e["ep"], "points": len(X), "fit": Mf is not None,
                                "inlier_frac": round(float(inl.mean()), 4) if len(X) else None,
                                "median_resid_inlier_px": round(float(np.median(res[inl])), 3) if inl.any() else None})
    json.dump(out, open(f"{a.logs}/camfit.json", "w"), indent=1)
    print(json.dumps({s: v for s, v in out["src"].items()}, indent=1)[:3000])


URDF = "/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf"


def nominal_uv(eps):
    """Nominal URDF head-camera projection (se2e_trace, head fixed at RB1_HEAD = the RB2 median) of both arms' end
    effectors, per episode: {"left": (N, 2), "right": (N, 2)}."""
    from harvest.train import se2e_trace as T
    cam = T.head_camera(T.load_head_chain(URDF), T.RB1_HEAD)
    for e in eps:
        e["nom"] = {a: T.project(cam, e["ee"][a])[0] for a in ("left", "right")}


def episode_offset(e, sep_px=40.0, iters=2):
    """Per-episode 2-D image offset of the pointings from the nominal projection: median of (point - nominal named
    arm) over interior points that are clearly nearer the named arm than the other (after the current offset)."""
    off = np.zeros(2)
    for _ in range(iters):
        d = []
        for a, b in (("left", "right"), ("right", "left")):
            for k, p in enumerate(e["uv"][a]):
                if not _interior(p):
                    continue
                pa, pb = e["nom"][a][k] + off, e["nom"][b][k] + off
                if math.dist(p, pb) - math.dist(p, pa) > sep_px:
                    d.append(np.asarray(p) - e["nom"][a][k])
        if len(d) < 10:
            return None, len(d)
        off = np.median(np.asarray(d), 0)
    return off, len(d)


def cmd_nominal(a):
    """Diagnosis (change 1): pointing vs nominal FK projection on the eye sample -- offsets, side assignment."""
    eps = load(a.data)
    nominal_uv(eps)
    by = {(e["src"], e["ep"]): e for e in eps}
    offs = {}
    for e in eps:
        o, n = episode_offset(e)
        offs[(e["src"], e["ep"])] = (o, n)
    judge = {int(k): v for k, v in json.load(open(a.judge)).items() if not k.startswith("_")}
    rows = []
    for s in json.load(open(f"{a.logs}/eye_sample.json")):
        e = by[(s["src"], s["ep"])]
        k, arm = s["k"], s["arm"]
        oth = "left" if arm == "right" else "right"
        o, n = offs[(s["src"], s["ep"])]
        r = {"idx": s["idx"], "src": s["src"], "code": judge[s["idx"]], "point": s["point"], "offset": None if o is None
             else [round(float(v), 1) for v in o], "n_off": n,
             "nom_named": [round(float(v), 1) for v in e["nom"][arm][k]],
             "nom_other": [round(float(v), 1) for v in e["nom"][oth][k]]}
        if s["point"] is not None and o is not None:
            r["d_named"] = round(math.dist(s["point"], e["nom"][arm][k] + o), 1)
            r["d_other"] = round(math.dist(s["point"], e["nom"][oth][k] + o), 1)
        rows.append(r)
    summ = {}
    for c in "goxnu":
        dn = [r["d_named"] for r in rows if r["code"] == c and "d_named" in r]
        do = [r["d_other"] for r in rows if r["code"] == c and "d_other" in r]
        summ[c] = {"n": len(dn), "d_named_median": float(np.median(dn)) if dn else None,
                   "d_named_p90": float(np.quantile(dn, 0.9)) if dn else None,
                   "d_other_median": float(np.median(do)) if do else None}
    out = {"utc": utc(), "offsets": {f"{s}_{ep}": [None if o is None else [round(float(v), 1) for v in o], n]
                                     for (s, ep), (o, n) in offs.items()}, "by_code": summ, "rows": rows}
    json.dump(out, open(f"{a.logs}/nominal_diag.json", "w"), indent=1)
    print(json.dumps({"by_code": summ, "episodes_without_offset": sum(o is None for o, _ in offs.values())}, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["main", "eye", "camfit", "nominal"])
    ap.add_argument("--data", required=True)
    ap.add_argument("--logs", required=True)
    ap.add_argument("--judge", default=None)
    ap.add_argument("--filter", default="v1", choices=["v1", "v2"])
    ap.add_argument("--sample-sfx", default="", choices=["", "_v2"])
    a = ap.parse_args()
    {"main": cmd_main, "eye": cmd_eye, "camfit": cmd_camfit, "nominal": cmd_nominal}[a.mode](a)


if __name__ == "__main__":
    main()
