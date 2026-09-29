"""E-MA2 data (docs/stage3/prereg_ma2.md): decision-snapshot views of R2_TRAIN, hindsight commands, the fixed
evaluation set and the arrow images. CPU only; reads /data/harvest/r2/train (never writes there).

  views    --src /data/harvest/r2/train --dst /data/harvest/data/ma2 [--max-eps N] [--workers 6]
           per folder <variant>/<task>/<kind>: <dst>/view/<v>/<t>/<kind>/ep<seed>.jsonl (decision lines only),
           img -> the source img/ (symlink), sibling <kind>.stageb.jsonl (decision rows) and <kind>.labels_v2.jsonl;
           <dst>/cmd/<v>_<t>_<kind>.jsonl one record per decision snapshot {id, seed, k, split, tcp, cmd, give};
           <dst>/views.json counts (rows = lines = labels per episode, checked)
  evalset  --dst ... [--per-stratum 200 --seed 0]   eval-split snapshots, n per (variant, task), sorted ids then a
           seeded sample -> <dst>/eval_set.json {ids, sha, ...}; eval-only rows <kind>.eval.stageb.jsonl
  arrows   --dst ... [--workers 6]    'true' arrow for every given snapshot, e0 / e90 / e180 for the eval set
  sheet    --dst ... --out JPG        projection check sheet (12 snapshots, true arrow)
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import random
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

import numpy as np  # noqa: E402

from harvest.train import r2_ma2 as M  # noqa: E402


def folders_of(src: str) -> list:
    out = []
    for p in sorted(glob.glob(os.path.join(src, "*", "*", "P*"))):
        if os.path.isdir(p):
            out.append(os.path.relpath(p, src).replace("\\", "/"))
    return out


def select_eval(recs, per: int, seed: int = 0) -> list:
    """ids of eval-split records: `per` per (variant, task) from the sorted ids with a seeded sample."""
    by = {}
    for r in sorted(recs, key=lambda r: r["id"]):
        if r["split"] == "eval":
            v, t = r["id"].split("/")[:2]
            by.setdefault((v, t), []).append(r["id"])
    rng = random.Random(seed)
    out = []
    for key in sorted(by):
        ids = by[key]
        out += sorted(ids if len(ids) <= per else rng.sample(ids, per))
    return out


def _view_folder(args):
    src, dst, rel, max_eps = args
    v, t, kind = rel.split("/")
    fo, V = os.path.join(src, rel), os.path.join(dst, "view", rel)
    os.makedirs(V, exist_ok=True)
    if not os.path.islink(os.path.join(V, "img")):
        os.symlink(os.path.join(fo, "img"), os.path.join(V, "img"))
    seeds = []
    for mp in sorted(glob.glob(f"{fo}/ep*.meta.json"), key=lambda p: int(os.path.basename(p)[2:-10])):
        meta = json.load(open(mp))
        if meta.get("valid_for_training"):
            seeds.append((meta["seed"], meta["split"]))
    if max_eps:
        seeds = seeds[:max_eps]
    keep = {s for s, _ in seeds}
    n_rows = {}
    with open(fo + ".stageb.jsonl", encoding="utf-8") as fin, open(V + ".stageb.jsonl", "w", encoding="utf-8") as fo_:
        for x in fin:
            r = json.loads(x)
            if r["decision"] and r["seed"] in keep:
                fo_.write(x)
                n_rows[r["seed"]] = n_rows.get(r["seed"], 0) + 1
    n_lab = {}
    with open(fo + ".labels_v2.jsonl", encoding="utf-8") as fin, \
            open(V + ".labels_v2.jsonl", "w", encoding="utf-8") as fo_:
        for x in fin:
            r = json.loads(x)
            if r["seed"] in keep:
                fo_.write(x)
                n_lab[r["seed"]] = n_lab.get(r["seed"], 0) + 1
    os.makedirs(os.path.join(dst, "cmd"), exist_ok=True)
    bad, n_lines = [], 0
    with open(os.path.join(dst, "cmd", f"{v}_{t}_{kind}.jsonl"), "w", encoding="utf-8") as fc:
        for seed, split in seeds:
            lines = [ln for ln in map(json.loads, open(f"{fo}/ep{seed}.jsonl", encoding="utf-8")) if ln["decision"]]
            with open(f"{V}/ep{seed}.jsonl", "w", encoding="utf-8") as f:
                for ln in lines:
                    f.write(json.dumps(ln) + "\n")
            tcp = np.load(f"{fo}/ep{seed}.npz")["tcp"]
            # rows exist for k < K (the terminal frame has no action): a decision line at K has no row
            ks = [ln["k"] for ln in lines if ln["k"] < len(tcp) - 1]
            if not (len(ks) == n_rows.get(seed, 0) == n_lab.get(seed, 0) - (len(lines) - len(ks))):
                bad.append([seed, len(lines), len(ks), n_rows.get(seed, 0), n_lab.get(seed, 0)])
            n_lines += len(lines)
            for k in ks:
                sid = f"{v}/{t}/{kind}/ep{seed}/k{k}"
                c = M.hindsight_cmd(tcp, k)
                fc.write(json.dumps({"id": sid, "seed": seed, "k": k, "split": split,
                                     "tcp": [round(float(x), 6) for x in tcp[k]],
                                     "cmd": [round(float(x), 6) for x in c], "give": M.give(sid)}) + "\n")
    return {"folder": rel, "episodes": len(seeds), "rows": sum(n_rows.values()), "labels": sum(n_lab.values()),
            "decision_lines": n_lines, "mismatch": bad,
            "seed_range": [min(keep), max(keep)] if keep else None}


def cmd_views(a):
    rels = folders_of(a.src)
    with Pool(a.workers) as p:
        res = p.map(_view_folder, [(a.src, a.dst, r, a.max_eps) for r in rels])
    out = {"src": a.src, "folders": res, "rows": sum(r["rows"] for r in res),
           "episodes": sum(r["episodes"] for r in res), "mismatch": sum(len(r["mismatch"]) for r in res)}
    json.dump(out, open(os.path.join(a.dst, "views.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "folders"}))


def read_cmds(dst: str) -> list:
    recs = []
    for f in sorted(glob.glob(os.path.join(dst, "cmd", "*.jsonl"))):
        recs += [json.loads(x) for x in open(f, encoding="utf-8")]
    return recs


def cmd_evalset(a):
    recs = read_cmds(a.dst)
    ids = select_eval(recs, a.per_stratum, a.seed)
    sha = hashlib.sha256(json.dumps(ids).encode()).hexdigest()[:12]
    by = {r["id"]: r for r in recs}
    elig = sum(np.linalg.norm(by[i]["cmd"][:2]) >= 0.01 for i in ids)
    json.dump({"ids": ids, "sha": sha, "per_stratum": a.per_stratum, "seed": a.seed,
               "n_eval_pool": sum(r["split"] == "eval" for r in recs), "n_true_xy_ge_1cm": int(elig)},
              open(os.path.join(a.dst, "eval_set.json"), "w"), indent=1)
    want = {}
    for i in ids:
        v, t, kind, ep, k = i.split("/")
        want.setdefault(f"{v}/{t}/{kind}", set()).add((int(ep[2:]), int(k[1:])))
    for rel in folders_of(os.path.join(a.dst, "view")):
        V = os.path.join(a.dst, "view", rel)
        w = want.get(rel, set())
        with open(V + ".stageb.jsonl", encoding="utf-8") as fin, \
                open(V + ".eval.stageb.jsonl", "w", encoding="utf-8") as fo:
            for x in fin:
                r = json.loads(x)
                if (r["seed"], r["k"]) in w:
                    fo.write(x)
    print(json.dumps({"n": len(ids), "sha": sha, "n_true_xy_ge_1cm": int(elig)}))


def _arrow(job):
    src, dst, tcp, c = job
    if os.path.exists(dst):
        return 0
    from PIL import Image
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    im = Image.open(src).convert("RGB")
    M.draw_arrow(im, np.asarray(tcp, float), np.asarray(c, float)).save(dst + ".tmp.jpg", quality=90)
    os.replace(dst + ".tmp.jpg", dst)
    return 1


def head_path(dst: str, sid: str) -> str:
    v, t, kind, ep, k = sid.split("/")
    return os.path.join(dst, "view", v, t, kind, "img", ep, f"f{int(k[1:]):04d}_cam_head.jpg")


def cmd_arrows(a):
    recs = read_cmds(a.dst)
    by = {r["id"]: r for r in recs}
    ids = json.load(open(os.path.join(a.dst, "eval_set.json")))["ids"]
    jobs = [(head_path(a.dst, r["id"]), os.path.join(a.dst, M.arrow_rel(r["id"], "true")), r["tcp"], r["cmd"])
            for r in recs if r["give"]]
    for i in ids:
        r = by[i]
        for tag, th in M.EVAL_ROT.items():
            jobs.append((head_path(a.dst, i), os.path.join(a.dst, M.arrow_rel(i, tag)), r["tcp"],
                         M.eval_cmd(r["cmd"], th).tolist()))
    with Pool(a.workers) as p:
        n = sum(p.imap_unordered(_arrow, jobs, chunksize=64))
    print(json.dumps({"jobs": len(jobs), "written": n, "given": sum(r["give"] for r in recs), "eval": len(ids)}))


def cmd_sheet(a):
    from PIL import Image, ImageDraw
    recs = [r for r in read_cmds(a.dst) if np.linalg.norm(r["cmd"]) > 0.02]
    rng = random.Random(1)
    pick = rng.sample(recs, 12)
    W, H = 672, 376
    sheet = Image.new("RGB", (3 * W, 4 * H))
    for j, r in enumerate(pick):
        im = M.draw_arrow(Image.open(head_path(a.dst, r["id"])).convert("RGB"), np.asarray(r["tcp"]),
                          np.asarray(r["cmd"]))
        ImageDraw.Draw(im).text((4, 4), r["id"] + " cmd " + M.cmd_line(r["cmd"])[26:], fill=(255, 255, 0))
        sheet.paste(im, ((j % 3) * W, (j // 3) * H))
    sheet.save(a.out, quality=85)
    print(a.out)


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("views")
    v.add_argument("--src", default="/data/harvest/r2/train")
    v.add_argument("--dst", default=M.MA2_ROOT)
    v.add_argument("--max-eps", type=int, default=0)
    v.add_argument("--workers", type=int, default=6)
    e = sub.add_parser("evalset")
    e.add_argument("--dst", default=M.MA2_ROOT)
    e.add_argument("--per-stratum", type=int, default=200)
    e.add_argument("--seed", type=int, default=0)
    r = sub.add_parser("arrows")
    r.add_argument("--dst", default=M.MA2_ROOT)
    r.add_argument("--workers", type=int, default=6)
    s = sub.add_parser("sheet")
    s.add_argument("--dst", default=M.MA2_ROOT)
    s.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    {"views": cmd_views, "evalset": cmd_evalset, "arrows": cmd_arrows, "sheet": cmd_sheet}[a.cmd](a)


if __name__ == "__main__":
    main()
