"""S-E2E data (plan e2e-ready, user-log 61): verify the downloaded ROBOTIS AI Worker LeRobot v2.1 datasets and
convert them to stage-B rows + native-resolution JPEG frames (harvest/train/se2e_data.py).

Runs on the pod (every file under /data/harvest), CPU only, with a python that has pyarrow + av + PIL
(/data/harvest/venv_e3st):
  python tools/se2e_convert.py verify  --raw /data/harvest/data/se2e/raw --out /data/harvest/data/se2e/verify.json
  python tools/se2e_convert.py convert --raw ... --conv /data/harvest/data/se2e/conv --urdf <ffw_bg2 urdf>
         [--stride 5] [--episodes N] [--workers 16]
Output: <conv>/<kind>.stageb.jsonl (one row per sampled frame), <conv>/img/<kind>/ep<NNNNNN>/k<KKKK>_<cam>.jpg
(head + active wrist, both wrists for bimanual rows), <conv>/<kind>.stats.json.
"""
from __future__ import annotations

import argparse
import functools
import glob
import json
import os
import random
import sys
import time
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from harvest.train import se2e_data as S  # noqa: E402

DATASETS = {"RB1": "Task_0001_CoffeeClassification_lerobot", "RB2": "Task_0002_OrderPicking_lerobot"}
CAMS = ("cam_head", "cam_head_right", "cam_wrist_left", "cam_wrist_right")
NATIVE = {"cam_head": (672, 376), "cam_head_right": (672, 376), "cam_wrist_left": (424, 240),
          "cam_wrist_right": (424, 240)}
JPEG_Q = 90
# Task_0001 ("ffw_bg2_rev4_custom") stores the D405 wrist videos as portrait 240x424 with the gripper at the bottom;
# Task_0002 (and the §59 / sim wrist camera) is landscape 424x240 with the fingers entering from the left.
# Rotating Task_0001 wrist frames 90 deg clockwise gives the Task_0002 layout (checked on frames, se2e_data.md).
ROTATE_CW = {"RB1": {"cam_wrist_left", "cam_wrist_right"}}
# Opt-in kinds (never in the default run; select with --kinds). RB3 = HF Dongkkka/ffw_bg2_rev4_pickup_obj_1127_total2
# (docs/stage3/results/rb3_data.md): BG2 rev4, 16-D like RB1, 10 fps, head 672x376 + wrists 424x240. Its wrist frames
# already have the RB2 layout (fingers from the left, checked on frames) -> no ROTATE_CW entry. Its gripper joint
# closes at p99.5 1.054 / 1.066 (mean 1.06; open p0.5 0.0015), nearest existing calibration = RB1 (0.0, 1.10) ->
# rows carry grip_unit "RB1" (stageb_data.GRIP_CAL is a prompt-hash file and stays untouched). Rows also carry the
# per-episode flags of --ep-flags (release_visible: place box inside the head image at the release frame,
# head_down_f0; tools/rb3/rb3_prep.py release); episodes flagged `exclude` are not converted.
OPTIONAL = {"RB3": "ffw_bg2_rev4_pickup_obj_1127_total2"}
GRIP_UNIT = {"RB3": "RB1"}
EP_FLAGS = {"RB3": ("release_visible", "release_frame", "head_down_f0")}
# RB3's parquet task_index disagrees with meta/episodes.jsonl for 58 episodes (indices 13 / 14 are not in
# tasks.jsonl; 390-404 say 12 = "yellow bin" but are white-box episodes) -> task text = episodes.jsonl via flags
TASK_FROM_FLAGS = {"RB3"}


def flag_excluded(flags) -> list:
    """Episodes whose --ep-flags entry has a truthy `exclude` (e.g. RB3 "no_grasp": robot idle while a person resets
    the wall -- no demonstration; rb3_data.md)."""
    return sorted(e for e, f in (flags or {}).items() if f.get("exclude"))


def selected(kinds: str) -> dict:
    """{kind: dataset folder} of a --kinds value; empty = the default DATASETS (RB1, RB2) only."""
    if not kinds:
        return dict(DATASETS)
    allk = {**DATASETS, **OPTIONAL}
    bad = [k for k in kinds.split(",") if k and k not in allk]
    if bad:
        raise SystemExit(f"unknown kinds {bad}: one of {sorted(allk)}")
    want = set(kinds.split(","))
    return {k: v for k, v in allk.items() if k in want}


def _meta(root):
    info = json.load(open(os.path.join(root, "meta/info.json")))
    eps = [json.loads(x) for x in open(os.path.join(root, "meta/episodes.jsonl"))]
    tasks = {json.loads(x)["task_index"]: json.loads(x)["task"] for x in open(os.path.join(root, "meta/tasks.jsonl"))}
    return info, eps, tasks


def _paths(root, info, ep):
    c = ep // info["chunks_size"]
    pq = os.path.join(root, info["data_path"].format(episode_chunk=c, episode_index=ep))
    vids = {cam: os.path.join(root, info["video_path"].format(episode_chunk=c, episode_index=ep,
                                                              video_key=f"observation.images.{cam}"))
            for cam in CAMS}
    return pq, vids


def _read_pq(path):
    import pyarrow.parquet as pq
    t = pq.read_table(path).to_pydict()
    st = np.asarray(t["observation.state"], np.float64)
    act = np.asarray(t["action"], np.float64)
    return t, st, act


def _probe(path, full=False):
    import av
    with av.open(path) as c:
        s = c.streams.video[0]
        out = {"codec": s.codec_context.name, "w": s.codec_context.width, "h": s.codec_context.height,
               "frames_hdr": int(s.frames)}
        if full:
            out["frames_dec"] = sum(1 for _ in c.decode(video=0))
    return out


def _decode(path, want):
    """{frame index: PIL image} for the wanted indices (sequential decode)."""
    import av
    want, out = set(want), {}
    with av.open(path) as c:
        for i, f in enumerate(c.decode(video=0)):
            if i in want:
                out[i] = f.to_image()
            if len(out) == len(want):
                break
    return out


# ------------------------------------------------------------------------------------------ verify
def _verify_ep(args):
    root, info, ep, n_expect, full, rot = args
    pq_path, vids = _paths(root, info, ep)
    rec = {"ep": ep, "errors": []}
    try:
        t, st, act = _read_pq(pq_path)
        rec["T"] = len(st)
        if len(st) != n_expect:
            rec["errors"].append(f"parquet rows {len(st)} != episodes.jsonl {n_expect}")
        if st.shape[1] != info["features"]["observation.state"]["shape"][0] or act.shape != st.shape:
            rec["errors"].append(f"dims state {st.shape} action {act.shape}")
        if not (np.isfinite(st).all() and np.isfinite(act).all()):
            rec["errors"].append("non-finite")
        ts = np.asarray(t["timestamp"], float)
        dt = np.diff(ts)
        rec["dt_max"], rec["dt_min"] = (float(dt.max()), float(dt.min())) if len(dt) else (0.0, 0.0)
        if len(dt) and (abs(dt - 1.0 / info["fps"]) > 0.5 / info["fps"]).any():
            rec["errors"].append(f"timestamp gaps dt in [{dt.min():.3f}, {dt.max():.3f}]")
        rec["st_min"], rec["st_max"] = st.min(0).tolist(), st.max(0).tolist()
        rec["act_min"], rec["act_max"] = act.min(0).tolist(), act.max(0).tolist()
    except Exception as e:  # noqa: BLE001
        rec["errors"].append(f"parquet: {e!r}")
        return rec
    rec["video"] = {}
    for cam, p in vids.items():
        if not os.path.exists(p):
            rec["video"][cam] = None
            continue
        try:
            v = _probe(p, full)
            rec["video"][cam] = v
            n = v.get("frames_dec", v["frames_hdr"])
            if n != rec["T"]:
                rec["errors"].append(f"{cam}: {n} frames != {rec['T']} rows")
            wh = (v["h"], v["w"]) if cam in rot else (v["w"], v["h"])
            if wh != NATIVE[cam]:
                rec["errors"].append(f"{cam}: {v['w']}x{v['h']} != native {NATIVE[cam]}")
        except Exception as e:  # noqa: BLE001
            rec["errors"].append(f"{cam}: {e!r}")
    return rec


def verify(a):
    rep = json.load(open(a.out)) if os.path.exists(a.out) else {}
    for kind, name in selected(a.kinds).items():
        root = os.path.join(a.raw, name)
        info, eps, tasks = _meta(root)
        n_pq = len(glob.glob(os.path.join(root, "data/*/*.parquet")))
        n_mp4 = {cam: len(glob.glob(os.path.join(root, f"videos/*/observation.images.{cam}/*.mp4"))) for cam in CAMS}
        rng = random.Random(0)
        full_set = set(rng.sample([e["episode_index"] for e in eps], min(a.full_decode, len(eps))))
        rot = ROTATE_CW.get(kind, set())
        jobs = [(root, info, e["episode_index"], e["length"], e["episode_index"] in full_set, rot) for e in eps]
        with Pool(a.workers) as p:
            recs = p.map(_verify_ep, jobs, chunksize=4)
        errs = [r for r in recs if r["errors"]]
        missing = {cam: sum(1 for r in recs if r.get("video", {}).get(cam, 0) is None) for cam in CAMS}
        st_min = np.min([r["st_min"] for r in recs if "st_min" in r], 0)
        st_max = np.max([r["st_max"] for r in recs if "st_max" in r], 0)
        act_min = np.min([r["act_min"] for r in recs if "act_min" in r], 0)
        act_max = np.max([r["act_max"] for r in recs if "act_max" in r], 0)
        codecs = sorted({(cam, v["codec"], v["w"], v["h"]) for r in recs for cam, v in r.get("video", {}).items() if v})
        rep[kind] = {"dataset": name, "robot_type": info["robot_type"], "fps": info["fps"],
                     "episodes_meta": len(eps), "frames_meta": sum(e["length"] for e in eps), "parquet": n_pq,
                     "mp4": n_mp4, "missing_video_by_cam": missing, "codecs": codecs,
                     "rotate_cw_on_convert": sorted(rot),
                     "full_decode_episodes": len(full_set),
                     "full_decode_ok": sum(1 for r in recs if r["ep"] in full_set and not r["errors"]),
                     "episodes_with_errors": len(errs), "error_examples": [(r["ep"], r["errors"][:3]) for r in errs[:200]],
                     "tasks": tasks, "names": info["features"]["observation.state"]["names"],
                     "state_min": st_min.round(4).tolist(), "state_max": st_max.round(4).tolist(),
                     "action_min": act_min.round(4).tolist(), "action_max": act_max.round(4).tolist(),
                     "length_min": min(e["length"] for e in eps), "length_max": max(e["length"] for e in eps)}
        print(kind, json.dumps({k: v for k, v in rep[kind].items() if k not in ("names",)})[:1500], flush=True)
    json.dump(rep, open(a.out, "w"), indent=1)


# ------------------------------------------------------------------------------------------ convert
def _convert_ep(args, flags=None, hist=False):
    """Rows of one episode. flags = {episode: {field: value}} (kinds in EP_FLAGS must have their episode's entry),
    hist = + se2e_temporal.hist_fields (motion-line source, as reconvert --hist). Defaults = the RB1 / RB2 rows."""
    from PIL import Image
    root, info, tasks, kind, ep, conv, urdf, stride, materialize = args
    chain = {arm: S.load_arm_chain(urdf, arm) for arm in ("left", "right")}
    pq_path, vids = _paths(root, info, ep)
    t, st, act = _read_pq(pq_path)
    # kinds in TASK_FROM_FLAGS: the parquet task_index is unreliable (RB3 merge) -> task text from the episode flags
    # (meta/episodes.jsonl); KeyError when missing
    task = (flags or {})[ep]["task_text"] if kind in TASK_FROM_FLAGS else tasks[int(t["task_index"][0])]
    rel = os.path.join("img", kind, f"ep{ep:06d}")

    def ref(k):
        return {cam: os.path.join(rel, f"k{k:04d}_{cam}.jpg") for cam in ("cam_head", "cam_wrist_left",
                                                                          "cam_wrist_right")}
    rows = S.episode_rows(st, act, info["fps"], chain, ep, kind, task, stride=stride, labels=True,
                          names=info["features"]["observation.state"]["names"], image_ref=ref,
                          timestamps=t["timestamp"])
    for r in rows:
        r["img_rotate_cw"] = sorted(ROTATE_CW.get(kind, ()))
    if kind in GRIP_UNIT:
        for r in rows:
            r["grip_unit"] = GRIP_UNIT[kind]
    if kind in EP_FLAGS:
        f = (flags or {})[ep]  # KeyError: an opt-in kind is never converted without its episode flags
        for r in rows:
            r.update({k: f[k] for k in EP_FLAGS[kind]})
    if materialize:
        os.makedirs(os.path.join(conv, rel), exist_ok=True)
        need = {"cam_head": [r["k"] for r in rows]}
        for r in rows:  # active wrist, both wrists when bimanual (§57)
            for cam in S.needed_cams(r)[1:]:
                need.setdefault(cam, []).append(r["k"])
        for cam, ks in need.items():
            if not os.path.exists(vids[cam]):
                continue
            ims = _decode(vids[cam], ks)
            for k, im in ims.items():
                if cam in ROTATE_CW.get(kind, ()):
                    im = im.transpose(Image.Transpose.ROTATE_270)  # 90 deg clockwise
                im.save(os.path.join(conv, rel, f"k{k:04d}_{cam}.jpg"), quality=JPEG_Q)
        for r in rows:  # keep only the images that exist
            r["images"] = {c: p for c, p in r["images"].items() if os.path.exists(os.path.join(conv, p))}
    if hist:  # after the image filter, as reconvert --hist (images_prev = the row's cameras)
        from harvest.train import se2e_temporal as T
        names = info["features"]["observation.state"]["names"]
        prel = os.path.join("img_prev", kind, f"ep{ep:06d}")
        for r in rows:
            r.update(T.hist_fields(r, st, info["fps"], names,
                                   lambda kp: {c: f"{prel}/k{kp:04d}_{c}.jpg".replace(os.sep, "/") for c in CAMS}))
    return rows


def convert(a):
    os.makedirs(a.conv, exist_ok=True)
    for kind, name in selected(a.kinds).items():
        t0 = time.time()
        root = os.path.join(a.raw, name)
        info, eps, tasks = _meta(root)
        ids = [e["episode_index"] for e in eps]
        ver = json.load(open(a.out)).get(kind, {}) if os.path.exists(a.out) else {}
        bad = sorted(ep for ep, _ in ver.get("error_examples", []))
        if ver.get("episodes_with_errors", 0) > len(bad):
            raise SystemExit(f"{kind}: more verify errors than listed examples; widen error_examples")
        ids = [i for i in ids if i not in bad]
        flags = None
        if kind in EP_FLAGS:
            if not a.ep_flags:
                raise SystemExit(f"{kind}: --ep-flags FILE required (fields {EP_FLAGS[kind]})")
            flags = {int(e): v for e, v in json.load(open(a.ep_flags))[kind].items()}
            ids = [i for i in ids if i not in set(flag_excluded(flags))]
        if a.episodes:
            ids = sorted(random.Random(0).sample(ids, min(a.episodes, len(ids))))
        jobs = [(root, info, tasks, kind, ep, a.conv, a.urdf, a.stride, not a.no_images) for ep in ids]
        out = S.rows_path(a.conv, kind)
        n, n_wrist, lab, arms = 0, 0, {}, {}
        fn =functools.partial(_convert_ep, flags=flags, hist=a.hist) if (flags or a.hist) else _convert_ep
        with Pool(a.workers) as p, open(out, "w", encoding="utf-8") as f:
            for rows in p.imap(fn, jobs, chunksize=2):
                for r in rows:
                    f.write(json.dumps(r, separators=(",", ":")) + "\n")
                    n += 1
                    n_wrist += set(S.needed_cams(r)) <= set(r["images"])
                    arms[r["arm"] + ("+bi" if r["bimanual"] else "")] = arms.get(r["arm"] + ("+bi" if r["bimanual"] else ""), 0) + 1
                    for q, v in r["committed"].items():
                        lab.setdefault(q, {}).setdefault(v, 0)
                        lab[q][v] += 1
        stats = {"kind": kind, "dataset": name, "episodes": len(ids), "excluded_verify": bad, "rows": n,
                 "stride": a.stride, "rows_with_active_wrist": n_wrist,
                 "arms": arms, "labels": lab, "seconds": round(time.time() - t0, 1)}
        if flags is not None or a.hist:
            stats.update({"hist": a.hist, "ep_flags": a.ep_flags or None, "grip_unit": GRIP_UNIT.get(kind),
                          "excluded_flags": flag_excluded(flags)})
        json.dump(stats, open(os.path.join(a.conv, f"{kind}.stats.json"), "w"), indent=1)
        print(json.dumps(stats), flush=True)


# ------------------------------------------------------------------------------------------ reconvert (canon §83)
KEEP_FROM_OLD = ("images", "img_rotate_cw")  # filled by the materializing convert; the frames do not change


def _diff_keys(a, b, pre=""):
    if isinstance(a, dict) and isinstance(b, dict):
        return [x for k in sorted(set(a) | set(b)) for x in _diff_keys(a.get(k), b.get(k), f"{pre}{k}.")]
    return [] if a == b else [pre.rstrip(".")]


def merge_reconverted(old: list, new: list, state=None, fps=None, names=None, kind=None) -> list:
    """Rows of one episode re-derived with the causal velocity (se2e_data.finite_velocity): the new rows (json round
    trip) + the old rows' image refs / rotation flag. Only proprio.qd and proprio.grip[1] may differ from the old
    rows (ValueError otherwise). With `state`, each row also gets se2e_temporal.hist_fields (motion-line source,
    past-frame refs img_prev/<kind>/ep<N>/k<K>_<cam>.jpg as in tools/se2e_temporal.py)."""
    new = json.loads(json.dumps(new))
    if [r["k"] for r in old] != [r["k"] for r in new]:
        raise ValueError(f"frames differ: old {[r['k'] for r in old][:5]}.. new {[r['k'] for r in new][:5]}..")
    out = []
    for o, n in zip(old, new):
        want = json.loads(json.dumps(o))
        want["proprio"]["qd"] = n["proprio"]["qd"]
        want["proprio"]["grip"][1] = n["proprio"]["grip"][1]
        got = {**n, **{k: o[k] for k in KEEP_FROM_OLD if k in o}}
        if got != want:
            raise ValueError(f"ep{o['seed']} k{o['k']}: changed fields {_diff_keys(want, got)}")
        out.append(got)
    if state is not None:
        from harvest.train import se2e_temporal as T
        for r in out:
            rel = os.path.join("img_prev", kind, f"ep{r['seed']:06d}")
            r.update(T.hist_fields(r, state, fps, names,
                                   lambda kp: {c: f"{rel}/k{kp:04d}_{c}.jpg".replace(os.sep, "/") for c in CAMS}))
    return out


def _reconvert_ep(args):
    root, info, tasks, kind, ep, old, urdf, stride, hist = args
    chain = {arm: S.load_arm_chain(urdf, arm) for arm in ("left", "right")}
    pq_path, _ = _paths(root, info, ep)
    t, st, act = _read_pq(pq_path)
    names = info["features"]["observation.state"]["names"]
    new = S.episode_rows(st, act, info["fps"], chain, ep, kind, tasks[int(t["task_index"][0])], stride=stride,
                         labels=True, names=names, timestamps=t["timestamp"])
    kw = {"state": st, "fps": info["fps"], "names": names, "kind": kind} if hist else {}
    return merge_reconverted(old, new, **kw)


def reconvert(a):
    """New data version from an existing conversion (rows only): same rows / order / frames (<conv>/img -> <src>/img
    symlink), velocity fields re-derived causally, + hist_fields (--hist). Never writes under --src."""
    src, conv = os.path.abspath(a.src), os.path.abspath(a.conv)
    for p in (src, os.path.dirname(src)):
        if conv == p or conv.startswith(p + os.sep):
            raise SystemExit(f"--conv {conv} must not be under {p}")
    os.makedirs(conv, exist_ok=True)
    rep = {"src": src, "stride": a.stride, "hist": a.hist}
    for kind, name in selected(a.kinds).items():
        out = S.rows_path(conv, kind)
        if os.path.exists(out):
            raise SystemExit(f"{out} exists (new data versions are never overwritten)")
        t0 = time.time()
        root = os.path.join(a.raw, name)
        info, _, tasks = _meta(root)
        order = [json.loads(x) for x in open(S.rows_path(src, kind), encoding="utf-8")]
        by = {}
        for r in order:
            by.setdefault(r["seed"], []).append(r)
        jobs = [(root, info, tasks, kind, ep, rows, a.urdf, a.stride, a.hist) for ep, rows in by.items()]
        got = {}
        with Pool(a.workers) as p:
            for rows in p.imap_unordered(_reconvert_ep, jobs, chunksize=2):
                for r in rows:
                    got[(r["seed"], r["k"])] = r
        n, changed, dq = 0, 0, []
        with open(out, "w", encoding="utf-8") as f:
            for o in order:
                r = got[(o["seed"], o["k"])]
                changed += r["proprio"]["qd"] != o["proprio"]["qd"] or r["proprio"]["grip"] != o["proprio"]["grip"]
                dq.append(float(np.abs(np.subtract(r["proprio"]["qd"], o["proprio"]["qd"])).max()))
                f.write(json.dumps(r, separators=(",", ":")) + "\n")
                n += 1
        st_old = os.path.join(src, f"{kind}.stats.json")
        if os.path.exists(st_old):
            json.dump({**json.load(open(st_old)), "reconverted_from": src}, open(os.path.join(conv, f"{kind}.stats.json"), "w"),
                      indent=1)
        rep[kind] = {"rows": n, "episodes": len(by), "rows_velocity_changed": changed,
                     "qd_abs_change_max": max(dq), "qd_abs_change_median": float(np.median(dq)),
                     "seconds": round(time.time() - t0, 1)}
        print(kind, rep[kind], flush=True)
    img = os.path.join(conv, "img")
    if not os.path.lexists(img):
        os.symlink(os.path.join(src, "img"), img)
    rep["img"] = os.path.realpath(img)
    json.dump(rep, open(os.path.join(conv, "reconvert.json"), "w"), indent=1)


def sheet(a):
    """Contact sheet: per chosen episode one strip of 6 rows (head over active wrist) with arm / labels."""
    from PIL import Image, ImageDraw
    strips = []
    for spec in a.sheet_eps.split(","):
        kind, ep = spec.split(":")
        rows = [json.loads(x) for x in open(S.rows_path(a.conv, kind)) if f'"seed":{int(ep)},' in x]
        rows = [r for r in rows if r["seed"] == int(ep)]
        pick = [rows[int(i)] for i in np.linspace(0, len(rows) - 1, 6)]
        tiles = []
        for r in pick:
            head = Image.open(os.path.join(a.conv, r["images"]["cam_head"])).convert("RGB").resize((336, 188))
            wc = f"cam_wrist_{r['arm']}"
            wr = Image.open(os.path.join(a.conv, r["images"][wc])).convert("RGB").resize((212, 120)) \
                if wc in r["images"] else Image.new("RGB", (212, 120))
            t = Image.new("RGB", (336, 188 + 120 + 30), (255, 255, 255))
            t.paste(head, (0, 0))
            t.paste(wr, (62, 188))
            c = r["committed"]
            d = ImageDraw.Draw(t)
            d.text((2, 2), f"{kind} ep{r['seed']} k{r['k']} t={r['t_src']:.1f}s", fill=(255, 255, 0))
            d.text((2, 310), f"{r['arm']}{'+bi' if r['bimanual'] else ''} {c['dir_xy']} {c['dir_z']} {c['mag_coarse']}"
                   f" g={r['proprio']['grip'][0]:.2f}", fill=(0, 0, 0))
            d.text((2, 322), r["task"][:52], fill=(80, 80, 80))
            tiles.append(t)
        strip = Image.new("RGB", (336 * 6, 338), (255, 255, 255))
        for i, t in enumerate(tiles):
            strip.paste(t, (i * 336, 0))
        strips.append(strip)
    out = Image.new("RGB", (336 * 6, 338 * len(strips)), (255, 255, 255))
    for i, s in enumerate(strips):
        out.paste(s, (0, i * 338))
    out = out.resize((out.width * 3 // 5, out.height * 3 // 5))
    q = 80
    while True:
        out.save(a.sheet_out, quality=q)
        if os.path.getsize(a.sheet_out) < 290_000 or q <= 30:
            break
        q -= 10
    print(a.sheet_out, os.path.getsize(a.sheet_out), q)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("verify", "convert", "sheet", "reconvert"))
    ap.add_argument("--src", default="/data/harvest/data/se2e/conv", help="reconvert: the existing conversion (read)")
    ap.add_argument("--hist", action="store_true",
                    help="reconvert / convert: + se2e_temporal.hist_fields (motion source, causal, §83)")
    ap.add_argument("--ep-flags", default="", help="convert: JSON {kind: {episode: {field: value}}} for EP_FLAGS kinds")
    ap.add_argument("--sheet-eps", default="")
    ap.add_argument("--sheet-out", default="/data/harvest/data/se2e/se2e_frames.jpg")
    ap.add_argument("--raw", default="/data/harvest/data/se2e/raw")
    ap.add_argument("--out", default="/data/harvest/data/se2e/verify.json")
    ap.add_argument("--conv", default="/data/harvest/data/se2e/conv")
    ap.add_argument("--urdf", default="/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf")
    ap.add_argument("--stride", type=int, default=5)
    ap.add_argument("--episodes", type=int, default=0)
    ap.add_argument("--kinds", default="")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--full-decode", type=int, default=40)
    ap.add_argument("--no-images", action="store_true")
    a = ap.parse_args()
    {"verify": verify, "convert": convert, "sheet": sheet, "reconvert": reconvert}[a.cmd](a)


if __name__ == "__main__":
    main()
