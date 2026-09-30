"""E-VB1 closed-loop work list (docs/stage3/prereg_vb1.md change 1; stdlib + venv_train, no Isaac).
  evalq.py build        -> <ROOT>/groups.json:
        sel60   = the VLA checkpoint-selection split: the first 60 (seed order) sel episodes of tools/vb1/eps.py whose
                  original L8S episode succeeded, minus the E-M35CL exclusions (multi-step, st__/pu__, drawer / ring),
                  grouped by collect job;
        evsmoke = the first 2 episodes of the first sel60 group (pipeline check with the smoke checkpoint);
        ood_o58, l8s_val = the E-M35CL groups (/data/harvest/out/main35_closed/groups.json, same digest).
  evalq.py next <lane>  -> a group of the served sets with unfinished episodes for the served checkpoint (lock), WAIT
                           (no server / all locked) or NONE (served sets finished)
  evalq.py release <gid> | touch <gid>
  evalq.py done         -> exit 0 when the served sets are finished for the served checkpoint
  evalq.py summary <ckpt> -> JSON per set: n, success, truth-success subset success, end reasons
  evalq.py succ <ckpt> <set> -> success count on the truth-success episodes of the set
Served checkpoint file <ROOT>/SERVER: '<url> <ckpt> <set,set>' (written by chain_eval.sh)."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

ROOT = os.environ.get("VB1_EVAL", "/data/harvest/out/vb1/eval")
M35CL = "/data/harvest/out/main35_closed/groups.json"
LOCK_STALE_S = 1800


def served():
    try:
        t = open(os.path.join(ROOT, "SERVER")).read().split()
    except OSError:
        return None
    return {"url": t[0], "ckpt": t[1], "sets": t[2].split(",")} if len(t) == 3 else None


def served_ckpt():
    s = served()
    return s["ckpt"] if s else None


def ep_dir(ckpt: str, set_: str, name: str) -> str:
    return os.path.join(ROOT, "res", ckpt, set_, name)


def ep_done(ckpt, set_, e) -> bool:
    d = ep_dir(ckpt, set_, f"{e['task']}_s{e['seed']}")
    return any(os.path.exists(os.path.join(d, n)) for n in ("result.json", "skip.json", "error.json"))


def _groups():
    return json.load(open(os.path.join(ROOT, "groups.json")))["groups"]


def group(gid):
    return next(g for g in _groups() if g["id"] == gid)


def build():
    sys.path.insert(0, os.environ.get("CODE", "."))
    from tools.main35_closed.sched import excluded
    from tools.vb1 import eps as E
    by_job = {}
    sel = []
    for g in E._groups():
        for e in E._eps(g["id"]):
            if e["sel"] and e["orig_success"] and not excluded(e["task"]):
                sel.append((e["seed"], g["job"], e))
    sel.sort(key=lambda x: x[0])
    for _, job, e in sel[:60]:
        by_job.setdefault(job, []).append({"set": "sel60", "dir": e["src"], "seed": e["seed"], "task": e["task"],
                                           "truth_success": True})
    groups = []
    for k, (job, eps) in enumerate(sorted(by_job.items())):
        groups.append({"id": f"sel60_{k:02d}", "set": "sel60", "job": job, "eps": eps})
    groups.insert(0, {"id": "evsmoke", "set": "evsmoke", "job": groups[0]["job"], "eps": groups[0]["eps"][:2]})
    m = json.load(open(M35CL))
    for g in m["groups"]:
        s = "ood_o58" if g["id"] == "ood_o58" else "l8s_val"
        groups.append({"id": g["id"], "set": s, "job": g["job"], "eps": [dict(e, set=s) for e in g["eps"]]})
    dig = hashlib.sha256(json.dumps([(g["id"], [(e["seed"], e["task"]) for e in g["eps"]])
                                     for g in m["groups"]]).encode()).hexdigest()[:16]
    os.makedirs(ROOT, exist_ok=True)
    out = {"groups": groups, "m35cl_groups_digest": dig, "m35cl_built_utc": m.get("built_utc"),
           "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    json.dump(out, open(os.path.join(ROOT, "groups.json"), "w"), indent=1)
    n = {}
    for g in groups:
        n[g["set"]] = n.get(g["set"], 0) + len(g["eps"])
    print(json.dumps({"sets": n, "m35cl_digest": dig}))


def next_group(lane: str) -> str:
    s = served()
    if not s:
        return "WAIT"
    os.makedirs(os.path.join(ROOT, "glock"), exist_ok=True)
    locked = False
    for g in _groups():
        if g["set"] not in s["sets"] or all(ep_done(s["ckpt"], g["set"], e) for e in g["eps"]):
            continue
        lk = os.path.join(ROOT, "glock", f"{s['ckpt']}_{g['id']}")
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
        open(os.path.join(lk, "owner"), "w").write(lane)
        return g["id"]
    return "WAIT" if locked else "NONE"


def _lk(gid):
    s = served()
    return os.path.join(ROOT, "glock", f"{s['ckpt'] if s else 'none'}_{gid}")


def summary(ckpt: str) -> dict:
    out = {}
    for g in _groups():
        for e in g["eps"]:
            d = ep_dir(ckpt, g["set"], f"{e['task']}_s{e['seed']}")
            if not os.path.exists(os.path.join(d, "result.json")):
                continue
            r = json.load(open(os.path.join(d, "result.json")))
            o = out.setdefault(g["set"], {"n": 0, "success": 0, "n_truth": 0, "success_truth": 0, "end": {}})
            o["n"] += 1
            o["success"] += bool(r.get("success"))
            if e.get("truth_success"):
                o["n_truth"] += 1
                o["success_truth"] += bool(r.get("success"))
            o["end"][r.get("end_reason")] = o["end"].get(r.get("end_reason"), 0) + 1
    for o in out.values():
        o["rate_truth"] = round(o["success_truth"] / o["n_truth"], 4) if o["n_truth"] else None
    return out


def main(argv):
    c = argv[0]
    if c == "build":
        build()
    elif c == "next":
        print(next_group(argv[1]))
    elif c == "release":
        import shutil
        shutil.rmtree(_lk(argv[1]), ignore_errors=True)
    elif c == "touch":
        if os.path.isdir(_lk(argv[1])):
            os.utime(_lk(argv[1]))
    elif c == "done":
        s = served()
        ok = s is not None and all(ep_done(s["ckpt"], g["set"], e) for g in _groups() if g["set"] in s["sets"]
                                   for e in g["eps"])
        sys.exit(0 if ok else 1)
    elif c == "summary":
        print(json.dumps(summary(argv[1])))
    elif c == "succ":  # succ <ckpt> <set> -> success count on the truth-success episodes
        print(summary(argv[1]).get(argv[2], {}).get("success_truth", 0))
    else:
        raise SystemExit(c)


if __name__ == "__main__":
    main(sys.argv[1:])
