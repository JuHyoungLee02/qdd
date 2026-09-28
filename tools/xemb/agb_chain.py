"""AgiBot World Beta flow-through pipeline (user-log 163-165), resumable pod chain.
Per stage, one tar at a time: download (agb_fetch.get: disk rule 2 TB notify / 2.7 TB stop, token via hf_hub, never in
argv) -> extract only what is needed (python tarfile, one pass) -> verify -> delete that temporary tar (the only
deletion allowed; agb_fetch.release_tar refuses anything else).
  obs      per selected task, its SMALLEST observations tar: keep <ep>/videos/head_color.mp4 of every episode inside.
  proprio  every proprio_stats tar whose episode range covers kept episodes: keep those episodes' files.
  params   every parameters tar whose range covers kept episodes: keep <task>/<ep>/parameters/camera/head_* files.
State: ROOT/chain_state.json (done tars, kept episodes). Log: ROOT/chain.log. STOP_DISK -> the chain exits.
usage (pod): python -m xemb.agb_chain [obs|proprio|params|all] [MAX_TASKS]"""
from __future__ import annotations

import json
import os
import sys
import tarfile
import time

from . import agb_fetch as AF

ROOT = AF.ROOT
STATE = os.path.join(ROOT, "chain_state.json")
KEEP = os.path.join(ROOT, "keep")


def log(msg):
    with open(os.path.join(ROOT, "chain.log"), "a") as f:
        f.write(time.strftime("%Y-%m-%dT%H:%M:%SZ ", time.gmtime()) + msg + "\n")


def load_state():
    return json.load(open(STATE)) if os.path.exists(STATE) else {"done": [], "eps": {}}


def save_state(s):
    json.dump(s, open(STATE + ".tmp", "w"))
    os.replace(STATE + ".tmp", STATE)


def listing(name):
    out = []
    for line in open(os.path.join(ROOT, f"list_{name}.txt")):
        p = line.split()
        if len(p) == 2 and "/" in p[0]:
            out.append((p[0], int(p[1])))
    return out


def rng(path):
    a, b = os.path.basename(path).split(".")[0].split("-")
    return int(a), int(b)


def fetch(path, size):
    if os.path.exists(os.path.join(ROOT, "STOP_DISK")):
        log("STOP_DISK present: not fetching")
        return None
    return AF.get(path, "raw", size)


def extract(tar_path, want, dest):
    """One pass over the tar; want(member_name) -> relative output path or None. Returns written paths."""
    got = []
    with tarfile.open(tar_path, "r|*") as tf:
        for m in tf:
            if not m.isfile():
                continue
            rel = want(m.name)
            if rel is None:
                continue
            out = os.path.join(dest, rel)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            src = tf.extractfile(m)
            with open(out + ".part", "wb") as f:
                while True:
                    b = src.read(1 << 22)
                    if not b:
                        break
                    f.write(b)
            if os.path.getsize(out + ".part") != m.size:
                raise IOError(f"short member {m.name}")
            os.replace(out + ".part", out)
            got.append(out)
    return got


def stage_obs(st, max_tasks):
    sel = json.load(open(os.path.join(ROOT, "selection.json")))["tasks"]
    sizes = dict(listing("observations"))
    for i, (tid, rec) in enumerate(sorted(sel.items(), key=lambda kv: int(kv[0]))):
        if max_tasks and i >= max_tasks:
            break
        tar = min(rec["obs_tars"], key=lambda p: sizes[p])
        if tar in st["done"]:
            continue
        local = fetch(tar, sizes[tar])
        if local is None:
            return False
        got = extract(local, lambda n: n if n.endswith("/videos/head_color.mp4") else None,
                      os.path.join(KEEP, "obs", tid))
        eps = sorted({int(p.split(os.sep)[-3]) for p in got})
        ok = len(got) > 0 and all(os.path.getsize(p) > 0 for p in got)
        AF.release_tar(local, verified=ok)
        st["eps"][tid] = eps
        st["done"].append(tar)
        save_state(st)
        log(f"OBS task {tid} tar {tar} episodes {len(eps)} verified={ok}")
    return True


def _need(st):
    return {e: t for t, eps in st["eps"].items() for e in eps}


def stage_range(st, kind, name, want_fn):
    need = _need(st)
    seen = st.setdefault(f"seen_{kind}", {})  # tar -> episodes already looked for in it
    if f"found_{kind}" not in st:  # episodes already extracted by earlier runs (e.g. the task-327 sample)
        kd = os.path.join(KEEP, kind)
        st[f"found_{kind}"] = sorted({int(d) for _, ds, _ in os.walk(kd) for d in ds if d.isdigit() and int(d) > 100000})
    found_all = set(st[f"found_{kind}"])
    for tar, size in sorted(listing(name)):
        a, b = rng(tar)
        # a range tar is (re)visited only for kept episodes in its range not yet found and not yet looked for in it
        # (ranges overlap, so an episode missing from one tar may sit in another)
        done = set(seen.get(tar, []))
        cover = [e for e in need if a <= e <= b and e not in found_all and e not in done]
        if not cover:
            continue
        local = fetch(tar, size)
        if local is None:
            return False
        cs = set(cover)
        got = extract(local, lambda n: want_fn(n, cs), os.path.join(KEEP, kind))
        found = {int(x) for p in got for x in p.split(os.sep) if x.isdigit() and int(x) in cs}
        AF.release_tar(local, verified=True)  # the tar was read to the end; members written and size-checked
        seen[tar] = sorted(done | cs)
        found_all |= found
        st[f"found_{kind}"] = sorted(found_all)
        save_state(st)
        log(f"{kind.upper()} tar {tar} covered {len(cover)} found {len(found)} files {len(got)}")
    return True


def want_proprio(n, cs):
    parts = n.split("/")
    return n if any(p.isdigit() and int(p) in cs for p in parts) else None


def want_params(n, cs):
    parts = n.split("/")
    hit = any(p.isdigit() and int(p) in cs for p in parts)
    return n if hit and "/camera/" in n and os.path.basename(n).startswith("head_") and "fisheye" not in n else None


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    mt = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    s = load_state()
    ok = True
    if what in ("obs", "all"):
        ok = stage_obs(s, mt)
    if ok and what in ("proprio", "all"):
        ok = stage_range(s, "proprio", "proprio_stats", want_proprio)
    if ok and what in ("params", "all"):
        ok = stage_range(s, "params", "parameters", want_params)
    log(f"CHAIN_END what={what} ok={ok}")
