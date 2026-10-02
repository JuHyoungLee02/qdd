"""L9 third-person (external camera) storage, kept apart from the egocentric data (user 10-02: collect them as planned,
store them separately so one switch adds or removes them; the head + wrist data of every episode stays complete).

Layout: <run>/collect/<split>/<family>/<ep>/calls/cNNN/            egocentric (head, wrist, cams.json, labels ...)
        <run>/third_person/<split>/<family>/<ep>/calls/cNNN/       img1_external<k>.png, external<k>_depth.npz,
                                                                   external_cams.json {"external<k>": camera record}
Older episodes kept the external files and cams.json entries in the ego call dir (legacy): readers fall back to it,
migrate() moves them (nothing is deleted). Pure."""
from __future__ import annotations

import glob
import json
import os
import shutil

TP_NAME = "third_person"
CAMS = "external_cams.json"


def collect_root(call_dir: str) -> str:
    """<run>/collect of a call dir <root>/<split>/<family>/<ep>/calls/cNNN."""
    d = os.path.normpath(call_dir)
    for _ in range(5):
        d = os.path.dirname(d)
    return d


def tp_dir(call_dir: str) -> str:
    """The third-person dir of an ego call dir (sibling tree `third_person` next to the collect root)."""
    root = collect_root(call_dir)
    return os.path.join(os.path.dirname(root), TP_NAME, os.path.relpath(os.path.normpath(call_dir), root))


def external_cams(call_dir: str) -> tuple:
    """-> (dir holding the external files, {"external<k>": record}) for one call: the third-person tree, else the
    legacy ego call dir (cams.json entries); ({} when the call has no external view)."""
    t = tp_dir(call_dir)
    p = os.path.join(t, CAMS)
    if os.path.exists(p):
        return t, json.load(open(p))
    cj = os.path.join(call_dir, "cams.json")
    cams = json.load(open(cj)) if os.path.exists(cj) else {}
    return call_dir, {k: v for k, v in cams.items() if k.startswith("external")}


def write(call_dir: str, k: int, png: bytes, depth_npz_writer, rec: dict) -> str:
    """Store one external view of a call in the third-person tree (world9.ext_save): the image, the depth (via
    depth_npz_writer(path)) and the camera record in external_cams.json. -> the third-person dir."""
    t = tp_dir(call_dir)
    os.makedirs(t, exist_ok=True)
    with open(os.path.join(t, f"img1_external{k}.png"), "wb") as f:
        f.write(png)
    depth_npz_writer(os.path.join(t, f"external{k}_depth.npz"))
    p = os.path.join(t, CAMS)
    cams = json.load(open(p)) if os.path.exists(p) else {}
    cams[f"external{k}"] = rec
    with open(p, "w") as f:
        json.dump(cams, f)
    return t


def migrate_call(call_dir: str, dry_run: bool = False) -> int:
    """Move a legacy call's external files + cams.json entries into the third-person tree (moved, not deleted; the
    ego cams.json keeps head / wrist only). -> number of external views moved."""
    cj = os.path.join(call_dir, "cams.json")
    cams = json.load(open(cj)) if os.path.exists(cj) else {}
    keys = sorted(k for k in cams if k.startswith("external"))
    files = sorted(glob.glob(os.path.join(call_dir, "img1_external*.png")) +
                   glob.glob(os.path.join(call_dir, "external*_depth.npz")))
    if not keys and not files:
        return 0
    if dry_run:
        return len(keys)
    t = tp_dir(call_dir)
    os.makedirs(t, exist_ok=True)
    p = os.path.join(t, CAMS)
    old = json.load(open(p)) if os.path.exists(p) else {}
    old.update({k: cams[k] for k in keys})
    with open(p, "w") as f:
        json.dump(old, f)
    for f in files:
        shutil.move(f, os.path.join(t, os.path.basename(f)))
    if keys:
        with open(cj, "w") as f:
            json.dump({k: v for k, v in cams.items() if k not in keys}, f)
    return len(keys)


def migrate(collect: str, dry_run: bool = False) -> dict:
    """Every finished episode (meta.json) under a collect root. -> {"calls", "views"}."""
    n_calls = n_views = 0
    for m in glob.glob(os.path.join(collect, "*", "*", "*", "meta.json")):
        for c in sorted(glob.glob(os.path.join(os.path.dirname(m), "calls", "c*"))):
            v = migrate_call(c, dry_run)
            n_calls += bool(v)
            n_views += v
    return {"calls": n_calls, "views": n_views}


def index(collect: str) -> list:
    """Index of the third-person views of a collect root: one entry per (episode, call, camera) with its files and
    camera pose (legacy calls included)."""
    out = []
    for m in sorted(glob.glob(os.path.join(collect, "*", "*", "*", "meta.json"))):
        ep = os.path.dirname(m)
        for c in sorted(glob.glob(os.path.join(ep, "calls", "c*"))):
            d, cams = external_cams(c)
            for k, rec in sorted(cams.items()):
                out.append({"episode": os.path.relpath(ep, collect).replace(os.sep, "/"), "call": os.path.basename(c),
                            "camera": k, "image": os.path.join(d, f"img1_{k}.png"),
                            "depth": os.path.join(d, f"{k}_depth.npz"), "R": rec.get("R"), "t": rec.get("t"),
                            "pair": rec.get("pair"), "legacy": d == c})
    return out
