"""E-VB1 episode list and group scheduler (docs/stage3/prereg_vb1.md change 1; venv_train, no Isaac).
  eps.py build                 -> <root>/groups.json + <root>/eps/<gid>.json
        episodes = L8S prod episodes behind main35's training rows (base_main35_d-min.jsonl, control rows; the ring
        root uses another runner and is left out), each mapped to the newest collect job whose plan holds it (the job
        that rendered it, = tools/main35_closed/sched.py); groups = one job, <= GROUP_N episodes; group g0000 = smoke
        (SMOKE_N episodes of the largest job). Episode field 'sel' = VLA checkpoint-selection split.
  eps.py next <lane>           -> "<gid>" of a group with unfinished episodes and no live lock (lock taken), or NONE
  eps.py release <gid>         -> drop the lock
  eps.py touch <gid>           -> refresh the lock (heartbeat)
  eps.py status                -> one JSON line of counts (done / success / repro / left)
Output of one episode: <root>/rec/<vdir>/<task>_s<seed>/ (tools/vb1/rec.py)."""
from __future__ import annotations

import glob
import hashlib
import json
import os
import sys
import time

ROOT = os.environ.get("VB1_ROOT", "/data/harvest/out/vb1")
BASE_ROWS = "/data/harvest/out/main35/data/base_main35_d-min.jsonl"
PROD = "/data/harvest/out/teach_l8d/l8s_prod"
GROUP_N = 40
SMOKE_N = 10
LOCK_STALE_S = 1800  # a lane refreshes its group lock every minute


def is_sel(seed) -> bool:
    """VLA checkpoint-selection split (prereg_vb1 change 1): sha256('vb1|<seed>') % 100 < 3."""
    return int(hashlib.sha256(f"vb1|{int(seed)}".encode()).hexdigest(), 16) % 100 < 3


def ep_out(e: dict) -> str:
    return os.path.join(ROOT, "rec", e["vdir"], f"{e['task']}_s{e['seed']}")


def ep_done(e: dict) -> bool:
    d = ep_out(e)
    return any(os.path.exists(os.path.join(d, n)) for n in ("rec.json", "skip.json", "error.json"))


def train_episode_dirs(rows_path: str = BASE_ROWS) -> list:
    out = set()
    for line in open(rows_path, encoding="utf-8"):
        r = json.loads(line)
        cd = r.get("call_dir") or ""
        if "/calls/" not in cd:
            continue
        ep = os.path.dirname(os.path.dirname(cd))
        if ep.startswith(PROD + "/"):
            out.add(ep)
    return sorted(out)


def build():
    sys.path.insert(0, os.environ.get("CODE", "."))
    from harvest.teach_l8d.run_collect import select_plan
    from harvest.teach_pt.run_closed_l8s import job_args
    from tools.main35_closed.sched import JOB_FILES, PLAN5, strip_job
    jobs = []
    for jf in JOB_FILES:
        p = os.path.join(PLAN5, jf)
        if os.path.exists(p):
            jobs += [strip_job(ln) for ln in open(p) if ln.strip()]
    rows_of, by_job, unmapped, bad = {}, {}, [], []
    for d in train_episode_dirs():
        try:
            meta = json.load(open(os.path.join(d, "meta.json")))
        except OSError:
            bad.append(d)
            continue
        seed, task = int(meta["seed"]), meta["task"]
        vdir = os.path.basename(os.path.dirname(d))
        furn = vdir.split("_fx_", 1)[-1]
        hit = None
        for jb in jobs:
            j = job_args(jb)
            if j.furniture != furn:
                continue
            if jb not in rows_of:
                rows_of[jb] = {(int(r["seed"]), r["task"]) for r in select_plan(
                    json.load(open(j.plan)), j.variant, j.table_z, j.split, j.objset, j.lift, j.furniture,
                    bool(j.clutter))}
            if (seed, task) in rows_of[jb]:
                hit = jb
                break
        if hit is None:
            unmapped.append(d)
            continue
        by_job.setdefault(hit, []).append({
            "src": d, "vdir": vdir, "seed": seed, "task": task, "split": meta.get("split", "train"),
            "p": float(meta.get("p", 0.35)), "max_perturb": int(meta.get("max_perturb", 4)),
            "style": meta.get("style", ""), "orig_success": bool(meta.get("success")),
            "orig_n_calls": meta.get("n_calls"), "sel": is_sel(seed)})
    groups = []
    big = max(by_job, key=lambda k: len(by_job[k]))
    eps_big = sorted(by_job[big], key=lambda e: e["seed"])
    groups.append({"id": "g0000", "job": big, "eps": eps_big[:SMOKE_N], "smoke": True})
    by_job[big] = eps_big[SMOKE_N:]
    chunks = []
    for jb in sorted(by_job):
        eps = sorted(by_job[jb], key=lambda e: e["seed"])
        chunks.append([(jb, eps[i:i + GROUP_N]) for i in range(0, len(eps), GROUP_N)])
    k = 1
    while any(chunks):  # round-robin over jobs: progress spreads over furniture kinds
        for c in chunks:
            if c:
                jb, eps = c.pop(0)
                groups.append({"id": f"g{k:04d}", "job": jb, "eps": eps})
                k += 1
    os.makedirs(os.path.join(ROOT, "eps"), exist_ok=True)
    for g in groups:
        json.dump(g["eps"], open(os.path.join(ROOT, "eps", g["id"] + ".json"), "w"))
    n_ep = sum(len(g["eps"]) for g in groups)
    out = {"groups": [{"id": g["id"], "job": g["job"], "n": len(g["eps"]), "smoke": g.get("smoke", False)}
                      for g in groups],
           "n_episodes": n_ep, "n_sel": sum(e["sel"] for g in groups for e in g["eps"]),
           "unmapped": unmapped, "no_meta": bad, "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    out["digest"] = hashlib.sha256(json.dumps([(g["id"], [(e["seed"], e["task"]) for e in g["eps"]])
                                               for g in groups]).encode()).hexdigest()[:16]
    json.dump(out, open(os.path.join(ROOT, "groups.json"), "w"), indent=1)
    print(json.dumps({"groups": len(groups), "episodes": n_ep, "sel": out["n_sel"], "unmapped": len(unmapped),
                      "no_meta": len(bad), "digest": out["digest"]}))


def _groups():
    return json.load(open(os.path.join(ROOT, "groups.json")))["groups"]


def _eps(gid):
    return json.load(open(os.path.join(ROOT, "eps", gid + ".json")))


def _lock(gid):
    return os.path.join(ROOT, "glock", gid)


def next_group(lane: str) -> str:
    """A group id (lock taken), NONE (every group finished), WAIT (smoke not checked yet, or the unfinished groups
    are all locked by other lanes: a yielding lane releases its group, so waiting lanes pick it up) or
    'ALERT ...' (smoke failed)."""
    os.makedirs(os.path.join(ROOT, "glock"), exist_ok=True)
    if os.path.exists(os.path.join(ROOT, "SMOKE_FAIL")):
        return "ALERT smoke failed (" + os.path.join(ROOT, "SMOKE_FAIL") + ")"
    smoke_ok = os.path.exists(os.path.join(ROOT, "SMOKE_OK"))
    locked = False
    for g in _groups():
        if not smoke_ok and g["id"] != "g0000":
            return "WAIT"
        if all(ep_done(e) for e in _eps(g["id"])):
            continue
        lk = _lock(g["id"])
        try:
            os.mkdir(lk)
        except FileExistsError:
            if time.time() - os.path.getmtime(lk) < LOCK_STALE_S:
                locked = True
                continue
            try:
                os.rename(lk, f"{lk}.stale.{int(time.time())}")
                os.mkdir(lk)
            except OSError:
                locked = True
                continue
        open(os.path.join(lk, "owner"), "w").write(f"{lane} {time.strftime('%FT%TZ', time.gmtime())}")
        return g["id"]
    return "WAIT" if locked else "NONE"


def smoke() -> str:
    """Check group g0000 (prereg change 1: 10 episodes before the rest): every episode finished, no error, frames and
    arrays consistent. -> SMOKE_OK (json with the per-episode wall time) or SMOKE_FAIL (+ ALERT_smoke)."""
    import numpy as np
    eps, rows, bad = _eps("g0000"), [], []
    for e in eps:
        o = ep_out(e)
        if os.path.exists(os.path.join(o, "skip.json")):
            continue
        if not os.path.exists(os.path.join(o, "rec.json")):
            bad.append(f"{e['task']}_s{e['seed']}: " + ("error" if os.path.exists(os.path.join(o, "error.json"))
                                                          else "not finished"))
            continue
        r = json.load(open(os.path.join(o, "rec.json")))
        z = np.load(os.path.join(o, "vla", "vla.npz"))
        n = r["n_frames"]
        nh = len(glob.glob(os.path.join(o, "vla", "head", "*.jpg")))
        nw = len(glob.glob(os.path.join(o, "vla", "wrist", "*.jpg")))
        ok = (n >= 20 and nh == n and nw == n and z["state"].shape == (n, 11) and z["action"].shape == (n, 8)
              and np.isfinite(z["state"]).all() and np.isfinite(z["action"]).all())
        if not ok:
            bad.append(f"{e['task']}_s{e['seed']}: n={n} head={nh} wrist={nw} state={z['state'].shape} "
                       f"action={z['action'].shape}")
        rows.append(r)
    unfinished = [b for b in bad if b.endswith("not finished")]
    if unfinished and len(unfinished) == len(bad):
        return "WAIT unfinished " + str(len(unfinished))
    if bad or len(rows) < len(eps) // 2:
        txt = json.dumps({"bad": bad, "n_ok": len(rows)})
        open(os.path.join(ROOT, "SMOKE_FAIL"), "w").write(txt)
        open(os.path.join(ROOT, "ALERT_smoke"), "w").write(txt)
        return "SMOKE_FAIL " + txt[:300]
    wall = sorted(r["wall_s"] for r in rows)
    out = {"n": len(rows), "wall_s_median": wall[len(wall) // 2], "wall_s_max": wall[-1],
           "frames_median": sorted(r["n_frames"] for r in rows)[len(rows) // 2],
           "success": sum(r["success"] for r in rows), "same_success_as_orig":
               sum(r["success"] == r["orig_success"] for r in rows),
           "clutter_match": sum(bool(r["repro"].get("clutter_match")) for r in rows)}
    json.dump(out, open(os.path.join(ROOT, "SMOKE_OK"), "w"))
    return "SMOKE_OK " + json.dumps(out)


def status() -> dict:
    n = d = ok = sk = er = rp = 0
    for g in _groups():
        for e in _eps(g["id"]):
            n += 1
            o = ep_out(e)
            if os.path.exists(os.path.join(o, "rec.json")):
                d += 1
                r = json.load(open(os.path.join(o, "rec.json")))
                ok += bool(r.get("success"))
                rp += bool(r.get("success") == e["orig_success"])
            elif os.path.exists(os.path.join(o, "skip.json")):
                sk += 1
            elif os.path.exists(os.path.join(o, "error.json")):
                er += 1
    return {"episodes": n, "done": d, "success": ok, "same_success_as_orig": rp, "skip": sk, "error": er,
            "left": n - d - sk - er}


def main(argv):
    cmd = argv[0]
    if cmd == "build":
        build()
    elif cmd == "next":
        print(next_group(argv[1]))
    elif cmd == "release":
        import shutil
        shutil.rmtree(_lock(argv[1]), ignore_errors=True)
    elif cmd == "touch":
        if os.path.isdir(_lock(argv[1])):
            os.utime(_lock(argv[1]))
    elif cmd == "smoke":
        print(smoke())
    elif cmd == "status":
        print(json.dumps(status()))
    elif cmd == "job":
        print(next(g["job"] for g in _groups() if g["id"] == argv[1]))
    else:
        raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    main(sys.argv[1:])
