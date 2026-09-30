"""E-M35CL work list and scheduler (docs/stage3/prereg_main35_closed.md; venv_train, no Isaac).
  sched.py build              -> <root>/groups.json: one group per collect job (OOD-O58: 1; L8S held-out: per job)
  sched.py next <lane>        -> "<group id> <conds>" for this lane, or WAIT (nothing served / nothing left)
  sched.py done <ckpt>        -> exit 0 when every item of the checkpoint is finished
  sched.py summary            -> <root>/summary.json + summary.md, videos index.md
Items = checkpoint x condition x episode; base condition first for every group, then the variants.
Results: <root>/res/<ckpt>/<cond dir>/<set>/<task>_s<seed>/{result,skip,error,cl}.json."""
from __future__ import annotations

import glob
import hashlib
import json
import os
import shlex
import sys
import time

ROOT = "/data/harvest/out/main35_closed"
VID = "/data/harvest/videos/main35_closed"
OODO = "/data/harvest/out/l8x_assets/ood_o_eval"
OODO_JOB = ("--split ood_o --confirm-ood --variant drf --table-z 0.0 --ws-x 0.36,0.54 --furniture thor_low_table "
            f"--rooms --objset x --clutter 40 --plan {OODO}/plan_ood_o_eval.json")
VAL = "/data/harvest/out/main35/data/val_episodes.txt"
PLAN5 = "/data/harvest/out/teach_l8d/plan5"
# newest job lists first: an episode maps to the newest job whose plan rows hold it (that job rendered it)
JOB_FILES = ["jobs_l8s4_m.txt", "jobs_l8s4_x.txt", "jobs_l8s4_g1.txt", "jobs_l8s4_g5.txt", "jobs_l8s3_m.txt",
             "jobs_l8s3_x.txt", "jobs_l8s3_r.txt", "jobs_l8s3_mr.txt", "jobs_l8s3_g1.txt", "jobs_l8s3_g5.txt",
             "jobs_l8s2_into_m.txt", "jobs_l8s2_into_x.txt", "jobs_l8s2_m.txt", "jobs_l8s2_x.txt", "jobs_l8s.txt"]
BASE = "none"
VARIANTS = ["light:dim_warm", "head:10:15"]
CKPTS = ["f35d", "0.5", "1", "1.5", "2", "2.5", "3"]
STALE_S = 3600


def excluded(task: str) -> str | None:
    from harvest.sim.tasks import X_STEPS
    if task in X_STEPS:
        return "multi-step"
    if task.startswith(("st__", "pu__")):
        return "new-task judge (collector rows)"
    if task.startswith(("dr__", "rp_", "ring")) or "ring" in task.split("__")[0]:
        return "drawer / ring"
    return None


def cond_dir(cond: str) -> str:
    return cond.replace(":", "_").replace("+", "p").replace("-", "m")


def strip_job(line: str) -> str:
    t = shlex.split(line)
    out, i = [], 0
    while i < len(t):
        if t[i] in ("--video-seeds", "--out"):
            i += 2
            continue
        out.append(t[i])
        i += 1
    return " ".join(shlex.quote(x) for x in out)


def build():
    sys.path.insert(0, os.environ.get("CODE", "."))
    from harvest.teach_l8d.run_collect import select_plan
    from harvest.teach_pt.run_closed_l8s import job_args
    groups, excl = [], []
    ev = json.load(open(f"{OODO}/eval_list.json"))
    oo = []
    for e in ev["episodes"]:
        d = f"{OODO}/render/{e['dir']}"
        why = excluded(e["task"])
        (excl.append({"set": "ood_o58", "dir": d, "why": why}) if why else
         oo.append({"set": "ood_o58", "dir": d, "seed": int(e["seed"]), "task": e["task"], "truth_success": True}))
    groups.append({"id": "ood_o58", "job": OODO_JOB, "eps": oo})
    jobs = []
    for jf in JOB_FILES:
        p = os.path.join(PLAN5, jf)
        if os.path.exists(p):
            jobs += [strip_job(ln) for ln in open(p) if ln.strip()]
    rows_of = {}
    by_job = {}
    unmapped = []
    for d in [ln.strip() for ln in open(VAL) if ln.strip()]:
        meta = json.load(open(os.path.join(d, "meta.json")))
        seed, task = int(meta["seed"]), meta["task"]
        furn = os.path.basename(os.path.dirname(d)).split("_fx_", 1)[1]
        why = excluded(task)
        if why:
            excl.append({"set": "l8s_val", "dir": d, "why": why})
            continue
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
        by_job.setdefault(hit, []).append({"set": "l8s_val", "dir": d, "seed": seed, "task": task,
                                           "truth_success": bool(meta.get("success"))})
    for k, (jb, eps) in enumerate(sorted(by_job.items())):
        groups.append({"id": f"l8s_{k:02d}_{job_args(jb).furniture}", "job": jb, "eps": eps})
    os.makedirs(ROOT, exist_ok=True)
    for g in groups:
        json.dump(g["eps"], open(os.path.join(ROOT, f"eps_{g['id']}.json"), "w"))
    out = {"groups": groups, "excluded": excl, "unmapped": unmapped, "base": BASE, "variants": VARIANTS,
           "ckpts": CKPTS, "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    json.dump(out, open(os.path.join(ROOT, "groups.json"), "w"), indent=1)
    n = {g["id"]: len(g["eps"]) for g in groups}
    print(json.dumps({"groups": n, "total": sum(n.values()), "excluded": len(excl), "unmapped": len(unmapped)}))


def item_dir(ckpt, cond, e):
    return os.path.join(ROOT, "res", ckpt, cond_dir(cond), e["set"], f"{e['task']}_s{e['seed']}")


def finished(od):
    return any(os.path.exists(os.path.join(od, n)) for n in ("result.json", "skip.json", "error.json"))


def pending(od, now):
    if finished(od):
        return False
    c = os.path.join(od, "claim")
    return not os.path.exists(c) or now - os.path.getmtime(c) >= STALE_S


def load():
    return json.load(open(os.path.join(ROOT, "groups.json")))


def current():
    p = os.path.join(ROOT, "CURRENT")
    t = open(p).read().split() if os.path.exists(p) else []
    return t if len(t) == 3 else None


def nxt(lane):
    cur = current()
    if not cur:
        print("WAIT")
        return
    ck, now, G = cur[0], time.time(), load()
    active = {}
    for f in glob.glob(os.path.join(ROOT, "lanes", "*.group")):
        if os.path.basename(f)[:-6] != lane and now - os.path.getmtime(f) < 900:
            gid = open(f).read().strip()
            active[gid] = active.get(gid, 0) + 1
    for conds in ([BASE], VARIANTS):
        best = None
        for g in G["groups"]:
            n = sum(pending(item_dir(ck, c, e), now) for c in conds for e in g["eps"])
            if n == 0:
                continue
            score = n / (1 + active.get(g["id"], 0))
            if best is None or score > best[0]:
                best = (score, g["id"])
        if best:
            print(best[1], ",".join(conds))
            return
    print("WAIT")


def ck_done(ck) -> bool:
    now, G = time.time(), load()
    conds = [BASE] + VARIANTS
    return not any(not finished(item_dir(ck, c, e)) for g in G["groups"] for c in conds for e in g["eps"])


def summary():
    G = load()
    rows = []
    for g in G["groups"]:
        for ck in CKPTS:
            for c in [BASE] + VARIANTS:
                for e in g["eps"]:
                    od = item_dir(ck, c, e)
                    if os.path.exists(os.path.join(od, "cl.json")):
                        r = json.load(open(os.path.join(od, "cl.json")))
                        r["truth_success"] = e.get("truth_success", True)
                        rows.append(r)
                    elif os.path.exists(os.path.join(od, "skip.json")) or os.path.exists(os.path.join(od, "error.json")):
                        rows.append({"ckpt": ck, "cond": c, "set": e["set"], "seed": e["seed"], "task": e["task"],
                                     "success": None, "end_reason": "skip" if os.path.exists(
                                         os.path.join(od, "skip.json")) else "error"})
    agg = {}
    for r in rows:
        k = f"{r['ckpt']}|{r['cond']}|{r['set']}"
        a = agg.setdefault(k, {"n": 0, "succ": 0, "skip_err": 0, "reasons": {}, "truth_ok_n": 0, "truth_ok_succ": 0,
                               "repro_clutter": 0})
        if r["success"] is None:
            a["skip_err"] += 1
            continue
        a["n"] += 1
        a["succ"] += int(r["success"])
        if r.get("truth_success"):
            a["truth_ok_n"] += 1
            a["truth_ok_succ"] += int(r["success"])
        if (r.get("repro") or {}).get("clutter_match"):
            a["repro_clutter"] += 1
        if not r["success"]:
            why = f"{r.get('fail_stage')}/{r.get('end_reason')}"
            a["reasons"][why] = a["reasons"].get(why, 0) + 1
    for a in agg.values():
        a["sr"] = round(a["succ"] / a["n"], 3) if a["n"] else None
    json.dump({"agg": agg, "n_rows": len(rows)}, open(os.path.join(ROOT, "summary.json"), "w"), indent=1)
    lines = ["| ckpt | cond | set | n | success | SR | truth-ok SR | skip/err | clutter repro | top fail reasons |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for k in sorted(agg):
        a = agg[k]
        top = ", ".join(f"{w} {n}" for w, n in sorted(a["reasons"].items(), key=lambda x: -x[1])[:3])
        tsr = round(a["truth_ok_succ"] / a["truth_ok_n"], 3) if a["truth_ok_n"] else None
        lines.append(f"| {' | '.join(k.split('|'))} | {a['n']} | {a['succ']} | {a['sr']} | {tsr} | {a['skip_err']} | "
                     f"{a['repro_clutter']}/{a['n']} | {top} |")
    open(os.path.join(ROOT, "summary.md"), "w").write("\n".join(lines) + "\n")
    vi = [json.loads(ln) for ln in open(os.path.join(VID, "index.jsonl"))] if os.path.exists(
        os.path.join(VID, "index.jsonl")) else []
    md = ["| ckpt | cond | set | seed | task | success | end | calls | mp4 |", "|---|---|---|---|---|---|---|---|---|"]
    md += [f"| {r['ckpt']} | {r['cond']} | {r['set']} | {r['seed']} | {r['task']} | {r['success']} | {r['end_reason']} "
           f"| {r['n_calls']} | {r['mp4']} |" for r in vi]
    open(os.path.join(VID, "index.md"), "w").write("\n".join(md) + "\n")
    print("\n".join(lines))


def digest() -> str:
    return hashlib.sha256(open(os.path.join(ROOT, "groups.json"), "rb").read()).hexdigest()[:16]


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "build":
        build()
    elif cmd == "next":
        nxt(sys.argv[2])
    elif cmd == "done":
        sys.exit(0 if ck_done(sys.argv[2]) else 1)
    elif cmd == "summary":
        summary()
    elif cmd == "digest":
        print(digest())
