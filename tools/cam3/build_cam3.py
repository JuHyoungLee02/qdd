"""E-CAM3 (docs/stage3/prereg_cam3.md): decode the OTHER wrist frame of every S-E2E row the baseline uses.

The se2e conversion materialized head + active wrist only (tools/se2e_convert.py convert). This tool decodes the
other wrist at the same frame index k from the raw ROBOTIS videos with the SAME decoder (se2e_convert._decode),
rotation (RB1 wrist frames 90 deg clockwise) and JPEG quality (90), into
  <out>/img_cam3/<kind>/ep<NNNNNN>/k<KKKK>_<cam>.jpg          (harvest.train.se2e_cam3.frame_rel)
Identity check first: for --check-eps episodes per kind the ACTIVE wrist frames are decoded the same way and must be
byte-identical to the existing conversion's JPEGs (else stop). Rows are read only (se2e_c1 is not modified).
Pod, CPU only, python with pyarrow + av + PIL (/data/harvest/venv_e3st):
  python tools/cam3/build_cam3.py --raw /data/harvest/data/se2e/raw --rows /data/harvest/data/se2e_c1/conv \
      --out /data/harvest/data/cam3 [--workers 8] [--check-eps 20]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import random
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from harvest.train import se2e_data as S  # noqa: E402
from harvest.train.se2e_cam3 import frame_rel  # noqa: E402


def used(r) -> bool:
    """The baseline loader (se2e_data.load_se2e) keeps a row iff it has all needed cameras."""
    return set(S.needed_cams(r)) <= set(r.get("images") or {})


def plan(rows) -> dict:
    """{episode: {other wrist cam: sorted frame indices}} of the used single-arm rows."""
    out = {}
    for r in rows:
        if not used(r) or r["bimanual"]:
            continue
        cam = "cam_wrist_" + ("left" if r["arm"] == "right" else "right")
        out.setdefault(r["seed"], {}).setdefault(cam, set()).add(r["k"])
    return {ep: {c: sorted(ks) for c, ks in d.items()} for ep, d in out.items()}


def _jpeg(im, rotate):
    from PIL import Image
    if rotate:
        im = im.transpose(Image.Transpose.ROTATE_270)  # 90 deg clockwise (se2e_convert)
    b = io.BytesIO()
    im.save(b, format="JPEG", quality=C.JPEG_Q)
    return b.getvalue()


def _job(args):
    root, info, kind, ep, need, out, check = args
    _, vids = C._paths(root, info, ep)
    rot = C.ROTATE_CW.get(kind, set())
    rec = {"ep": ep, "written": 0, "checked": 0, "mismatch": [], "missing": []}
    for cam, ks in need.items():
        if check:  # identity check: active-wrist frames re-decoded == the existing conversion's files
            for k, im in C._decode(vids[cam], ks).items():
                old = os.path.join(check, "img", kind, f"ep{ep:06d}", f"k{k:04d}_{cam}.jpg")
                rec["checked"] += 1
                if open(old, "rb").read() != _jpeg(im, cam in rot):
                    rec["mismatch"].append([cam, k])
            continue
        ims = C._decode(vids[cam], ks)
        for k in ks:
            if k not in ims:
                rec["missing"].append([cam, k])
                continue
            p = os.path.join(out, frame_rel(kind, ep, k, cam))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "wb").write(_jpeg(ims[k], cam in rot))
            rec["written"] += 1
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--rows", required=True, help="se2e_c1 conv dir (<kind>.stageb.jsonl; img -> the frames)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--kinds", default="RB1,RB2")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--check-eps", type=int, default=20)
    a = ap.parse_args()
    rep = {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    for kind in a.kinds.split(","):
        t0 = time.time()
        root = os.path.join(a.raw, C.DATASETS[kind])
        info, _, _ = C._meta(root)
        rows = [json.loads(x) for x in open(S.rows_path(a.rows, kind), encoding="utf-8")]
        pl = plan(rows)
        act = {}
        for r in rows:
            if used(r) and not r["bimanual"]:
                act.setdefault(r["seed"], {}).setdefault(f"cam_wrist_{r['arm']}", []).append(r["k"])
        chk = sorted(random.Random(0).sample(sorted(act), min(a.check_eps, len(act))))
        with Pool(a.workers) as p:
            crec = p.map(_job, [(root, info, kind, ep, act[ep], a.out, a.rows) for ep in chk])
        bad = [(r["ep"], r["mismatch"][:3]) for r in crec if r["mismatch"]]
        rep[kind] = {"check_episodes": chk, "check_frames": sum(r["checked"] for r in crec), "check_mismatch": bad}
        print(kind, json.dumps(rep[kind])[:400], flush=True)
        if bad:
            json.dump(rep, open(os.path.join(a.out, "build_cam3.json"), "w"), indent=1)
            raise SystemExit(f"{kind}: re-decoded active wrist frames differ from the conversion: {bad[:3]}")
        jobs = [(root, info, kind, ep, need, a.out, None) for ep, need in sorted(pl.items())]
        with Pool(a.workers) as p:
            recs = p.map(_job, jobs, chunksize=4)
        rep[kind].update(episodes=len(jobs), frames_needed=sum(len(ks) for d in pl.values() for ks in d.values()),
                         written=sum(r["written"] for r in recs),
                         missing=[(r["ep"], r["missing"][:3]) for r in recs if r["missing"]],
                         seconds=round(time.time() - t0, 1))
        print(kind, json.dumps({k: v for k, v in rep[kind].items() if k != "check_episodes"}), flush=True)
    rep["ended_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    json.dump(rep, open(os.path.join(a.out, "build_cam3.json"), "w"), indent=1)
    if any(rep[k]["missing"] for k in a.kinds.split(",")):
        raise SystemExit("missing frames (see build_cam3.json)")


import se2e_convert as C  # noqa: E402  (tools/, after the sys.path setup)

if __name__ == "__main__":
    main()
