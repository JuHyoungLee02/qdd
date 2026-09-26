"""E-MAR-real (docs/stage3/prereg_marr.md) step 3 (CPU, pod venv_e3st): filter v2 + MolmoAct trace labels per
se2e_c1 RB2 row, statistics, a BLIND eye-check sample (gate G-label) and a trace sheet.

  labels.py --data D --logs L build [--allow-partial]
      filter v2 (se2e_molmo.filter_nominal, fixed values of the readiness document: offset 40 px, gate 150 px, border
      12 px) per episode on both arms' pointings, trace = trace.labels_segments(kept points, next release) per arm,
      row label = the row's (active) arm at the row's frame. -> D/conv/RB2.tracept.jsonl (one line per row: key, arm,
      split, trace255 or null, why), L/labels_stats.json, L/eye_sample.json (no filter fields), L/eye_sheet_NN.jpg,
      L/filter_decisions.json (read only after the judgments exist), L/trace_sheet.jpg.
      --allow-partial: episodes whose pointing is incomplete are left unlabelled (dry run only; the main labels
      refuse any missing pointing).
  labels.py --data D --logs L eye --judge J
      G-label from the eye judgments J ({idx: code}; g named gripper, o other arm's gripper, x elsewhere, n named
      gripper not visible, u on a gripper but the arm cannot be told = error): kept error <= 0.05 AND correct
      retained >= 0.80 (the G-filter rule), bootstrap 10,000 95 % -> L/eye_eval.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import random
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from harvest.datagen import trace as TR  # noqa: E402
from harvest.train import se2e_molmo as M  # noqa: E402

URDF = "/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf"
ROWS = "/data/harvest/data/se2e_c1/conv/RB2.stageb.jsonl"
CYAN = (0, 255, 255)  # MolmoAct overlay colour, safe on real frames (readiness 4.5)
EYE_PER_ARM, EYE_SEED = 48, 2
KEPT_ERR_MAX, CORRECT_KEPT_MIN = 0.05, 0.80
CMP_EPS = 1e-12


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def img_path(data, ep, k):
    return f"{data}/frames/RB2/ep{ep:06d}/f{k:04d}.jpg"


def load_points(data) -> dict:
    pts = {}
    for p in sorted(glob.glob(f"{data}/points.shard*.jsonl")):
        for x in open(p, encoding="utf-8"):
            r = json.loads(x)
            pts[(r["ep"], r["k"], r["arm"])] = None if r["point"] is None else tuple(r["point"])
    return pts


def load_rows(path=ROWS) -> dict:
    by = {}
    for x in open(path, encoding="utf-8"):
        r = json.loads(x)
        by.setdefault(int(r["seed"]), []).append({"key": f"RB2_ep{r['seed']}_k{r['k']}", "k": int(r["k"]),
                                                  "arm": r["arm"], "split": r["split"]})
    return by


def episodes(data, allow_partial=False):
    """Per episode: arrays over ALL frames (n_state) -- pointings (None where not pointed / failed), nominal
    projections, ends, filter decisions, labels."""
    from harvest.train import se2e_trace as T
    cam = T.head_camera(T.load_head_chain(URDF), T.RB1_HEAD)
    meta = json.load(open(f"{data}/episodes.json"))["episodes"]
    jobs = {}
    for x in open(f"{data}/point_jobs.jsonl", encoding="utf-8"):
        j = json.loads(x)
        jobs.setdefault(j["ep"], set()).add((j["k"], j["arm"]))
    pts = load_points(data)
    out = []
    for m in meta:
        ep = m["ep"]
        need = jobs.get(ep, set())
        missing = [q for q in need if (ep,) + q not in pts]
        e = dict(m, pointed=not missing, n_missing=len(missing))
        if missing and not allow_partial:
            raise SystemExit(f"episode {ep}: {len(missing)} pointings missing")
        if not need:
            e["labels"] = {a: [None] * m["n_state"] for a in ("left", "right")}
            e["why"] = {a: ["unneeded"] * m["n_state"] for a in ("left", "right")}
            out.append(e)
            continue
        z = np.load(f"{data}/eps/RB2_ep{ep:06d}.npz")
        n = m["n_state"]
        ee = {"left": z["ee_l"][:n], "right": z["ee_r"][:n]}
        g = {"left": z["g_l"][:n], "right": z["g_r"][:n]}
        uv = {a: [pts.get((ep, k, a)) if (k, a) in need and not missing else None for k in range(n)]
              for a in ("left", "right")}
        nom = {a: T.project(cam, ee[a])[0] for a in ("left", "right")}
        kl, wl, kr, wr, info = M.filter_nominal(uv["left"], uv["right"], nom["left"], nom["right"])
        why = {"left": wl, "right": wr}
        for a in ("left", "right"):  # frames never pointed are not 'fail' of the model
            why[a] = [("unpointed" if (k, a) not in need or missing else w) for k, w in enumerate(why[a])]
        keep = {"left": kl, "right": kr}
        ends = {a: M.grip_segment_ends(g[a]) for a in ("left", "right")}
        kept = {a: [p if kk else None for p, kk in zip(uv[a], keep[a])] for a in ("left", "right")}
        e.update(uv=uv, keep=keep, why=why, ends=ends, info=info,
                 labels={a: TR.labels_segments(kept[a], ends[a]) for a in ("left", "right")})
        out.append(e)
    return out


def row_labels(eps, rows_by) -> list:
    out = []
    by = {e["ep"]: e for e in eps}
    for ep in sorted(rows_by):
        e = by[ep]
        for r in rows_by[ep]:
            k, a = r["k"], r["arm"]
            lab = e["labels"][a][k]
            end = e.get("ends", {}).get(a, [None] * (k + 1))[k] if "ends" in e else None
            if not lab:
                reason = "no_segment" if end is None else ("unpointed" if not e["pointed"] else "no_kept_point")
            else:
                reason = "ok"
            out.append({"key": r["key"], "arm": a, "split": r["split"], "k": k, "end": end,
                        "trace255": lab if lab else None, "reason": reason, "why_k": e["why"][a][k]})
    return out


def stats(eps, rl) -> dict:
    why, n_pts = {}, 0
    for e in eps:
        if "uv" not in e:
            continue
        for a in ("left", "right"):
            for w in e["why"][a]:
                if w == "unpointed":
                    continue
                why[w] = why.get(w, 0) + 1
                n_pts += 1
    out = {"episodes": len(eps), "episodes_pointed": sum(e["pointed"] for e in eps),
           "episodes_no_offset": sum(1 for e in eps if "info" in e and e["pointed"] and e["info"]["offset"] is None),
           "pointings": n_pts, "reasons": {k: [v, round(v / max(n_pts, 1), 4)] for k, v in sorted(why.items())},
           "kept_frac": round(why.get("ok", 0) / max(n_pts, 1), 4)}
    for split in ("train", "val", "all"):
        xs = [r for r in rl if split == "all" or r["split"] == split]
        lens = {}
        for r in xs:
            if r["trace255"]:
                lens[len(r["trace255"])] = lens.get(len(r["trace255"]), 0) + 1
        reasons = {}
        for r in xs:
            reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
        out[f"rows_{split}"] = {"rows": len(xs), "labelled": sum(r["trace255"] is not None for r in xs),
                                "labelled_frac": round(sum(r["trace255"] is not None for r in xs) / max(len(xs), 1), 4),
                                "reasons": reasons, "len_hist": dict(sorted(lens.items()))}
    # the trace end: is the release-frame pointing of the row's arm kept (= the label ends AT the release)?
    by = {e["ep"]: e for e in eps}
    at_rel = [bool(by[int(r["key"].split("_ep")[1].split("_")[0])]["keep"][r["arm"]][r["end"]])
              for r in rl if r["trace255"] is not None]
    out["labelled_rows_release_point_kept_frac"] = round(float(np.mean(at_rel)), 4) if at_rel else None
    return out


def eye_sample(eps, n_per=EYE_PER_ARM, seed=EYE_SEED, exclude=()):
    """BLIND: per arm n_per (episode cycled in random order, random POINTED frame), no filter fields."""
    rng = random.Random(seed)
    out = []
    es = [e for e in eps if "uv" in e]
    for arm in ("left", "right"):
        order = es[:]
        rng.shuffle(order)
        i = 0
        while sum(s["arm"] == arm for s in out) < n_per:
            e = order[i % len(order)]
            i += 1
            ks = [k for k in range(e["n_state"]) if e["why"][arm][k] != "unpointed"]
            if not ks:
                continue
            k = rng.choice(ks)
            if (e["ep"], k, arm) in exclude:
                continue
            out.append({"idx": len(out), "src": "RB2", "ep": e["ep"], "k": k, "arm": arm, "point": e["uv"][arm][k]})
    return out


def _font():
    from PIL import ImageFont
    try:
        return ImageFont.load_default(size=14)
    except TypeError:
        return ImageFont.load_default()


def eye_sheets(data, logs, sample, per=12):
    from PIL import Image, ImageDraw
    tw, th = 448, 250
    font = _font()
    names = []
    for s0 in range(0, len(sample), per):
        sheet = Image.new("RGB", (3 * tw, 4 * th), (0, 0, 0))
        for i, s in enumerate(sample[s0:s0 + per]):
            im = Image.open(img_path(data, s["ep"], s["k"])).convert("RGB")
            d = ImageDraw.Draw(im)
            if s["point"] is not None:
                u, v = s["point"]
                d.ellipse([u - 9, v - 9, u + 9, v + 9], outline=(255, 0, 255), width=3)
                d.line([u - 14, v, u + 14, v], fill=(255, 255, 0), width=1)
                d.line([u, v - 14, u, v + 14], fill=(255, 255, 0), width=1)
            im = im.resize((tw, th))
            d = ImageDraw.Draw(im)
            lab = f"#{s['idx']} RB2 ep{s['ep']} k{s['k']} {s['arm'].upper()}" + (" NONE" if s["point"] is None else "")
            d.rectangle([0, 0, 8 * len(lab) + 4, 17], fill=(0, 0, 0))
            d.text((2, 1), lab, fill=(255, 255, 255), font=font)
            sheet.paste(im, ((i % 3) * tw, (i // 3) * th))
        p = f"{logs}/eye_sheet_{s0 // per:02d}.jpg"
        sheet.save(p, quality=85)
        names.append(p)
    return names


def trace_sheet(data, logs, eps, rl, seed=0):
    """12 random labelled rows: the row's trace drawn MolmoAct-style (cyan 2 px), white ring = its raw pointing."""
    from PIL import Image, ImageDraw
    rng = random.Random(seed)
    tw, th = 448, 250
    font = _font()
    by = {e["ep"]: e for e in eps}
    rows = [r for r in rl if r["trace255"]]
    pick = rng.sample(rows, min(12, len(rows)))
    sheet = Image.new("RGB", (3 * tw, 4 * th), (0, 0, 0))
    for i, r in enumerate(pick):
        ep = int(r["key"].split("_ep")[1].split("_")[0])
        im = np.asarray(Image.open(img_path(data, ep, r["k"])).convert("RGB"))
        pim = Image.fromarray(TR.draw(im, r["trace255"], rgb=CYAN, outline=0))
        d = ImageDraw.Draw(pim)
        p = by[ep]["uv"][r["arm"]][r["k"]]
        if p is not None:
            d.ellipse([p[0] - 6, p[1] - 6, p[0] + 6, p[1] + 6], outline=(255, 255, 255), width=2)
        pim = pim.resize((tw, th))
        d = ImageDraw.Draw(pim)
        lab = f"{r['key']} {r['arm']} end{r['end']} n{len(r['trace255'])}"
        d.rectangle([0, 0, 8 * len(lab) + 4, 17], fill=(0, 0, 0))
        d.text((2, 1), lab, fill=(255, 255, 255), font=font)
        sheet.paste(pim, ((i % 3) * tw, (i // 3) * th))
    p = f"{logs}/trace_sheet.jpg"
    sheet.save(p, quality=85)
    return p, [{"key": r["key"], "trace255": r["trace255"]} for r in pick]


def cmd_build(a):
    t0 = time.time()
    eps = episodes(a.data, a.allow_partial)
    rl = row_labels(eps, load_rows(a.rows))
    st = stats(eps, rl)
    os.makedirs(f"{a.data}/conv", exist_ok=True)
    name = "RB2.tracept.jsonl" if not a.allow_partial else "partial/RB2.tracept.jsonl"
    os.makedirs(os.path.dirname(f"{a.data}/conv/{name}"), exist_ok=True)
    with open(f"{a.data}/conv/{name}", "w", encoding="utf-8") as f:
        for r in rl:
            f.write(json.dumps({k: r[k] for k in ("key", "arm", "split", "k", "end", "trace255", "reason")}) + "\n")
    out = {"utc": utc(), "partial": a.allow_partial, "stats": st, "labels_file": f"{a.data}/conv/{name}",
           "seconds": round(time.time() - t0, 1)}
    if not a.allow_partial:
        old = set()
        for p in ("/data/harvest/logs/marr/eye_sample.json", "/data/harvest/logs/marr/eye_sample_v2.json"):
            if os.path.exists(p):
                old |= {(s["ep"], s["k"], s["arm"]) for s in json.load(open(p)) if s["src"] == "RB2"}
        sample = eye_sample(eps, exclude=old)
        json.dump(sample, open(f"{a.logs}/eye_sample.json", "w"), indent=1)
        out["eye_sheets"] = eye_sheets(a.data, a.logs, sample)
        by = {e["ep"]: e for e in eps}
        dec = {f"{s['ep']}_{s['k']}_{s['arm']}": [by[s["ep"]]["keep"][s["arm"]][s["k"]],
                                                  by[s["ep"]]["why"][s["arm"]][s["k"]]] for s in sample}
        json.dump(dec, open(f"{a.logs}/filter_decisions.json", "w"))
        out["trace_sheet"], out["trace_sheet_rows"] = trace_sheet(a.data, a.logs, eps, rl)
    json.dump(out, open(f"{a.logs}/labels_stats{'_partial' if a.allow_partial else ''}.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "trace_sheet_rows"})[:6000], flush=True)


def boot(x, n=10000, seed=0):
    x = np.asarray(x, float)
    if len(x) == 0:
        return [None, None, None]
    rng = np.random.default_rng(seed)
    m = x[rng.integers(0, len(x), (n, len(x)))].mean(1)
    return [round(float(x.mean()), 4), round(float(np.quantile(m, 0.025)), 4), round(float(np.quantile(m, 0.975)), 4)]


def cmd_eye(a):
    sample = json.load(open(f"{a.logs}/eye_sample.json"))
    judge = {int(k): v for k, v in json.load(open(a.judge)).items() if not k.startswith("_")}
    if set(judge) != {s["idx"] for s in sample} or not set(judge.values()) <= set("goxnu"):
        raise SystemExit("judgments do not cover the sample exactly / unknown code")
    dec = json.load(open(f"{a.logs}/filter_decisions.json"))
    rows = [dict(s, code=judge[s["idx"]], keep=dec[f"{s['ep']}_{s['k']}_{s['arm']}"][0],
                 why=dec[f"{s['ep']}_{s['k']}_{s['arm']}"][1]) for s in sample]
    vis = [r for r in rows if r["code"] != "n"]
    kept = [r for r in vis if r["keep"]]
    correct = [r for r in vis if r["code"] == "g"]
    out = {"utc": utc(), "n": len(rows), "visible": len(vis), "codes": {c: sum(r["code"] == c for r in rows)
                                                                        for c in "goxnu"},
           "raw_error_rate": boot([r["code"] != "g" for r in vis]),
           "other_arm_rate": boot([r["code"] == "o" for r in vis]),
           "kept": len(kept), "kept_error_rate": boot([r["code"] != "g" for r in kept]),
           "kept_error_rate_u_as_correct": boot([r["code"] not in "gu" for r in kept]),
           "kept_codes": {c: sum(r["code"] == c for r in rows if r["keep"]) for c in "goxnu"},
           "correct_retained": boot([r["keep"] for r in correct]),
           "not_visible_kept": sum(r["keep"] for r in rows if r["code"] == "n"),
           "kept_error_incl_not_visible": boot([r["code"] != "g" for r in rows if r["keep"]]),
           "errors_by_reason": {w: sum(1 for r in vis if r["why"] == w and r["code"] != "g")
                                for w in sorted({r["why"] for r in vis})},
           "correct_by_reason": {w: sum(1 for r in vis if r["why"] == w and r["code"] == "g")
                                 for w in sorted({r["why"] for r in vis})}}
    ke, cr = out["kept_error_rate"][0], out["correct_retained"][0]
    out["G_label_pass"] = bool(ke is not None and ke <= KEPT_ERR_MAX + CMP_EPS and cr is not None
                               and cr >= CORRECT_KEPT_MIN - CMP_EPS)
    json.dump({"summary": out, "rows": rows}, open(f"{a.logs}/eye_eval.json", "w"), indent=1)
    print(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["build", "eye"])
    ap.add_argument("--data", required=True)
    ap.add_argument("--logs", required=True)
    ap.add_argument("--rows", default=ROWS)
    ap.add_argument("--judge", default=None)
    ap.add_argument("--allow-partial", action="store_true")
    a = ap.parse_args()
    {"build": cmd_build, "eye": cmd_eye}[a.mode](a)


if __name__ == "__main__":
    main()
