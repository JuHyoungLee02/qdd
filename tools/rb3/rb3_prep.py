"""RB3 data prep on the pod (venv_e3st: pyarrow + av + PIL), CPU only. docs/stage3/results/rb3_data.md.

  release  per-episode release frame + release_visible flag (rb3_lib), gripper range, eye-check sheets
           python tools/rb3/rb3_prep.py release --rb3 <raw>/ffw_bg2_rev4_pickup_obj_1127_total2 --out <flags.json>
  overlap  RB3 vs RB1 / RB2 (and inside RB3): exact / rounded action + state hashes, trajectory near-duplicates,
           first head frame (32x18 grey) nearest MAD
           python tools/rb3/rb3_prep.py overlap --rb3 ... --se2e-raw /data/harvest/data/se2e/raw --out <overlap.json>
  gates    converted data version counts, split, labels, release_visible, loader counts
           python tools/rb3/rb3_prep.py gates --conv <se2e_c2/conv> --out <gates.json>
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import rb3_lib as L  # noqa: E402
import se2e_convert as C  # noqa: E402

SE2E = {"RB1": "Task_0001_CoffeeClassification_lerobot", "RB2": "Task_0002_OrderPicking_lerobot"}


def _eps(root):
    info, eps, tasks = C._meta(root)
    return info, eps, tasks


# ------------------------------------------------------------------------------------------ release
def _release_ep(args):
    root, info, ep = args
    pq, vids = C._paths(root, info, ep)
    t, st, act = C._read_pq(pq)
    names = info["features"]["observation.state"]["names"]
    fr, arm = L.first_release(st, names)
    want = [0] + ([fr] if fr is not None else [])
    ims = C._decode(vids["cam_head"], want)
    y0 = L.yellow_low(np.asarray(ims[0].convert("RGB"))) if 0 in ims else None
    yr = L.yellow_low(np.asarray(ims[fr].convert("RGB"))) if fr is not None and fr in ims else None
    g = {n: st[:, names.index(n)].tolist() for n in L.GRIPS}
    return {"ep": ep, "T": len(st), "task": int(t["task_index"][0]), "release_frame": fr, "release_arm": arm,
            "yellow_low_f0": y0, "yellow_low_release": yr, "release_visible": L.release_flag(fr, yr),
            "head_down_f0": L.head_down(y0), "exclude": L.exclude_reason(st, names), "grip": g}


def _tile(im, text, w=336, h=188):
    from PIL import Image, ImageDraw
    t = Image.new("RGB", (w, h + 14), (255, 255, 255))
    t.paste(im.convert("RGB").resize((w, h)), (0, 14))
    ImageDraw.Draw(t).text((2, 1), text, fill=(0, 0, 0))
    return t


def _grid(tiles, cols, out):
    from PIL import Image
    w, h = tiles[0].size
    g = Image.new("RGB", (w * cols, h * ((len(tiles) + cols - 1) // cols)), (255, 255, 255))
    for i, t in enumerate(tiles):
        g.paste(t, ((i % cols) * w, (i // cols) * h))
    g.save(out, quality=82)


def release(a):
    info, eps, tasks = _eps(a.rb3)
    ids = [e["episode_index"] for e in eps]
    with Pool(a.workers) as p:
        recs = p.map(_release_ep, [(a.rb3, info, e) for e in ids], chunksize=4)
    grip = {n: np.concatenate([r["grip"][n] for r in recs]) for n in L.GRIPS}
    flags = {str(r["ep"]): {k: r[k] for k in ("release_visible", "release_frame", "release_arm", "yellow_low_f0",
                                               "yellow_low_release", "head_down_f0", "exclude", "T", "task")}
             for r in recs}
    text = {e["episode_index"]: e["tasks"][0] for e in eps}  # meta/episodes.jsonl (one task per episode)
    for r in recs:
        f = flags[str(r["ep"])]
        f["task_text"] = text[r["ep"]]
        f["task_index_parquet_ok"] = tasks.get(r["task"]) == text[r["ep"]]
    kept = [r for r in recs if not r["exclude"]]
    vis = [r for r in recs if r["release_visible"]]
    bins = {}
    for r in recs:
        b = f"{r['ep'] // 100 * 100:03d}-{r['ep'] // 100 * 100 + 99:03d}"
        bins.setdefault(b, [0, 0])
        bins[b][0] += r["release_visible"]
        bins[b][1] += 1
    yr = np.array([r["yellow_low_release"] for r in recs if r["yellow_low_release"] is not None])
    summ = {"episodes": len(recs), "task_index_parquet_mismatch": sorted(
                int(e) for e, f in flags.items() if not f["task_index_parquet_ok"]),
            "excluded_no_grasp": sorted(r["ep"] for r in recs if r["exclude"]),
            "kept": len(kept), "kept_release_found": sum(r["release_frame"] is not None for r in kept),
            "kept_release_visible": sum(r["release_visible"] for r in kept),
            "kept_head_down_f0": sum(r["head_down_f0"] for r in kept),
            "kept_head_down_no_release": sum(r["head_down_f0"] and r["release_frame"] is None for r in kept),
            "kept_head_up_released": sum((not r["head_down_f0"]) and r["release_frame"] is not None for r in kept),
            "release_found": sum(r["release_frame"] is not None for r in recs),
            "release_visible": len(vis), "release_visible_frac": round(len(vis) / len(recs), 4),
            "by_100_episodes": bins, "yellow_min": L.YELLOW_MIN,
            "yellow_release_hist": np.histogram(yr, bins=[0, .005, .01, .015, .02, .03, .05, .1, .2, 1])[0].tolist(),
            "first_visible_ep": min((r["ep"] for r in vis), default=None),
            "not_visible_after_180": sorted(r["ep"] for r in recs if r["ep"] >= 180 and not r["release_visible"]),
            "visible_before_180": sorted(r["ep"] for r in vis if r["ep"] < 180),
            "grip_p99_5": {n: round(float(np.percentile(v, 99.5)), 4) for n, v in grip.items()},
            "grip_p0_5": {n: round(float(np.percentile(v, 0.5)), 4) for n, v in grip.items()},
            "grip_closed_mean_p99_5": round(float(np.mean([np.percentile(v, 99.5) for v in grip.values()])), 4)}
    json.dump({"RB3": flags, "summary": summ}, open(a.out, "w"), indent=1)
    print(json.dumps(summ), flush=True)
    # eye check: 24 random episodes (seed 0), head at the release frame (or last frame), flag + yellow in the title
    rng = random.Random(0)
    pick = sorted(rng.sample(ids, 24))
    tiles = []
    for ep in pick:
        r = flags[str(ep)]
        k = r["release_frame"] if r["release_frame"] is not None else r["T"] - 1
        im = C._decode(C._paths(a.rb3, info, ep)[1]["cam_head"], [k])[k]
        tiles.append(_tile(im, f"ep{ep} k{k} {r['release_arm']} vis={int(r['release_visible'])} "
                               f"y={r['yellow_low_release'] if r['yellow_low_release'] is None else round(r['yellow_low_release'], 3)}"))
    _grid(tiles, 4, a.out.replace(".json", "_release_sheet.jpg"))
    # wrist layout: raw wrist frames of 8 episodes (both arms, early and late), at the release frame when present
    tiles = []
    for ep in sorted(rng.sample(ids, 8)):
        r = flags[str(ep)]
        for cam in ("cam_wrist_left", "cam_wrist_right"):
            k = r["release_frame"] if r["release_frame"] is not None else r["T"] // 2
            im = C._decode(C._paths(a.rb3, info, ep)[1][cam], [k])[k]
            tiles.append(_tile(im, f"ep{ep} {cam} k{k} raw {im.size[0]}x{im.size[1]}", 318, 180))
    _grid(tiles, 4, a.out.replace(".json", "_wrist_sheet.jpg"))


# ------------------------------------------------------------------------------------------ overlap
def _fp_ep(args):
    root, info, ep = args
    from PIL import Image
    pq, vids = C._paths(root, info, ep)
    t, st, act = C._read_pq(pq)
    names = info["features"]["observation.state"]["names"]
    s16, a16 = L.arm16(st, names), L.arm16(act, names)
    im = C._decode(vids["cam_head"], [0]) if os.path.exists(vids["cam_head"]) else {}
    g = np.asarray(im[0].convert("L").resize((32, 18), Image.BILINEAR), np.float32) if 0 in im else None
    return {"ep": ep, "T": len(st), "act_exact": L.exact_hash(a16), "st_exact": L.exact_hash(s16),
            "act_round": L.round_hash(a16), "st_round": L.round_hash(s16), "fp": L.traj_fp(s16), "g": g}


def overlap(a):
    srcs = {k: os.path.join(a.se2e_raw, v) for k, v in SE2E.items()}
    srcs["RB3"] = a.rb3
    fps = {}
    with Pool(a.workers) as p:
        for kind, root in srcs.items():
            info, eps, _ = _eps(root)
            fps[kind] = p.map(_fp_ep, [(root, info, e["episode_index"]) for e in eps], chunksize=4)
            print(kind, len(fps[kind]), flush=True)
    rep = {"episodes": {k: len(v) for k, v in fps.items()}}
    rb3 = fps["RB3"]
    for key in ("act_exact", "st_exact", "act_round", "st_round"):
        seen = {}
        for kind in ("RB1", "RB2"):
            for r in fps[kind]:
                seen.setdefault(r[key], []).append(f"{kind}:{r['ep']}")
        rep[f"{key}_hits_vs_RB1_RB2"] = [(r["ep"], seen[r[key]]) for r in rb3 if r[key] in seen]
        own = {}
        for r in rb3:
            own.setdefault(r[key], []).append(r["ep"])
        rep[f"{key}_dups_inside_RB3"] = [v for v in own.values() if len(v) > 1]
    A = np.stack([r["fp"] for r in rb3])
    for kind in ("RB1", "RB2"):
        B = np.stack([r["fp"] for r in fps[kind]])
        idx, dist = L.nearest(A, B)
        d = np.array(dist)
        rep[f"traj_nearest_{kind}"] = {"min": float(d.min()), "p1": float(np.percentile(d, 1)),
                                       "median": float(np.median(d)), "n_below_0.01": int((d < 0.01).sum()),
                                       "n_below_0.05": int((d < 0.05).sum()),
                                       "closest5": sorted([(float(dist[i]), rb3[i]["ep"], fps[kind][idx[i]]["ep"])
                                                           for i in range(len(rb3))])[:5]}
    # inside RB3: nearest other episode
    dd = []
    for i in range(len(A)):
        d = np.abs(A[i].reshape(1, -1) - A.reshape(len(A), -1)).max(1)
        d[i] = np.inf
        dd.append((float(d.min()), rb3[i]["ep"], rb3[int(d.argmin())]["ep"]))
    d = np.array([x[0] for x in dd])
    rep["traj_nearest_inside_RB3"] = {"min": float(d.min()), "median": float(np.median(d)),
                                      "n_below_0.01": int((d < 0.01).sum()), "closest5": sorted(dd)[:5]}
    # first head frames (same tool wall as RB2 -> small MAD is expected for different episodes; reported, not a rule)
    G3 = np.stack([r["g"] for r in rb3 if r["g"] is not None])
    for kind in ("RB1", "RB2"):
        Gk = np.stack([r["g"] for r in fps[kind] if r["g"] is not None])
        m = np.array([np.abs(G3[i][None] - Gk).mean((1, 2)).min() for i in range(len(G3))])
        rep[f"head_f0_mad_nearest_{kind}"] = {"min": float(m.min()), "p1": float(np.percentile(m, 1)),
                                              "median": float(np.median(m)), "n_below_2": int((m < 2).sum())}
    lens = {k: sorted(r["T"] for r in v) for k, v in fps.items()}
    rep["length_range"] = {k: [v[0], v[-1]] for k, v in lens.items()}
    json.dump(rep, open(a.out, "w"), indent=1)
    print(json.dumps({k: v for k, v in rep.items()})[:3000], flush=True)


# ------------------------------------------------------------------------------------------ gates
def gates(a):
    from harvest.train import se2e_data as S
    from harvest.train import stageb_data as D
    rep = {"conv": os.path.realpath(a.conv)}
    for kind in ("RB1", "RB2", "RB3"):
        rows = [json.loads(x) for x in open(S.rows_path(a.conv, kind), encoding="utf-8")]
        eps = {}
        for r in rows:
            eps.setdefault(r["seed"], []).append(r)
        lab = {}
        for r in rows:
            for q, v in r["committed"].items():
                lab.setdefault(q, {}).setdefault(v, 0)
                lab[q][v] += 1
        lab = {q: {v: round(n / len(rows), 4) for v, n in sorted(d.items())} for q, d in lab.items()}
        arms = {}
        for r in rows:
            k = r["arm"] + ("+bi" if r["bimanual"] else "")
            arms[k] = arms.get(k, 0) + 1
        ent = {"rows": len(rows), "episodes": len(eps),
               "split_rows": {s: sum(r["split"] == s for r in rows) for s in ("train", "val")},
               "split_episodes": {s: sum(v[0]["split"] == s for v in eps.values()) for s in ("train", "val")},
               "split_rule_ok": all(r["split"] == S.split_of(kind, r["seed"]) for r in rows),
               "arms_frac": {k: round(v / len(rows), 4) for k, v in sorted(arms.items())}, "labels_frac": lab,
               "hist_fields_rows": sum("motion_src" in r for r in rows),
               "velocity_eq_motion_src": sum(r.get("motion_src", {}).get("qd_bwd") == r["proprio"]["qd"] and
                                             r.get("motion_src", {}).get("grip_rate_bwd") == r["proprio"]["grip"][1]
                                             for r in rows),
               "k0_velocity_zero": all(r["proprio"]["qd"] == [0.0] * 7 for r in rows if r["k"] == 0),
               "rows_all_images_present": sum(all(os.path.exists(os.path.join(a.conv, p)) for p in r["images"].values())
                                              for r in rows)}
        if kind == "RB3":
            ent["grip_unit"] = sorted({D.grip_source(r) for r in rows})
            ent["release_visible_episodes"] = sum(v[0]["release_visible"] for v in eps.values())
            ent["release_visible_rows"] = sum(r["release_visible"] for r in rows)
            ent["head_down_f0_episodes"] = sum(v[0]["head_down_f0"] for v in eps.values())
            ent["release_visible_by_split_episodes"] = {
                s: [sum(v[0]["release_visible"] for v in eps.values() if v[0]["split"] == s),
                    sum(v[0]["split"] == s for v in eps.values())] for s in ("train", "val")}
            ent["img_rotate_cw"] = sorted({tuple(r["img_rotate_cw"]) for r in rows})
            ent["tasks"] = sorted({r["task"] for r in rows})
        samples = S.load_se2e(S.rows_path(a.conv, kind), image_root=a.conv, labels=True, wrist=True, hz=10)
        miss = sum(not os.path.exists(p if isinstance(p, str) else p[1])
                   for s in samples for p in [x for x in _img_paths(s)])
        ent["loader"] = {"samples": len(samples), "train": sum(s["split"] == "train" for s in samples),
                         "val": sum(s["split"] == "val" for s in samples), "missing_image_files": miss}
        rep[kind] = ent
        print(kind, json.dumps(ent)[:1500], flush=True)
    json.dump(rep, open(a.out, "w"), indent=1)


def _img_paths(s):
    out = []
    for im in s["context"]["images"]:
        if isinstance(im, (list, tuple)):
            out += [x for x in im if isinstance(x, str) and x.endswith(".jpg")]
        elif isinstance(im, str):
            out.append(im)
        elif isinstance(im, dict):
            out += [v for v in im.values() if isinstance(v, str) and v.endswith(".jpg")]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("release", "overlap", "gates"))
    ap.add_argument("--rb3", default="/data/harvest/data/robotis/rb3/ffw_bg2_rev4_pickup_obj_1127_total2")
    ap.add_argument("--se2e-raw", default="/data/harvest/data/se2e/raw")
    ap.add_argument("--conv", default="/data/harvest/data/se2e_c2/conv")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    {"release": release, "overlap": overlap, "gates": gates}[a.cmd](a)


if __name__ == "__main__":
    main()
