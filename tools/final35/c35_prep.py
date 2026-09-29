"""E-C35 (docs/stage3/prereg_c35.md) data preparation.
  ood58  <out dir>               -> manifest of the 58 new OOD-O evaluation episodes (eval_list.json)
  l8s    <n> <out dir> [after]   -> the first <n> finished L8S production episodes (meta.json, by its mtime, finished
                                    after <after> UTC when given; main and
                                    ring roots), episode-level validation split sha256("c35|<seed>") % 100 < 3;
                                    manifests <out>/{main,ring}_{train,val}.json + counts
  pool   <verdict_fix.json> <out dir>
                                 -> open point sources (FIX pool when E-POOLV8-FIX is NONINFERIOR, else the old pool
                                    with AgiBot v3 final in place of agibot_p0), G rows removed, 3 % of rows by
                                    sha256("c35|<id>") % 100 < 3 held out -> <out>/pool_src/<src>.jsonl (train part)
                                    + <out>/val_open.jsonl (geval format, gset val_<src>)
  strat  <n> <out dir>           -> change 3/4: stratified sample by plan share of task kind (ring 3 %), furniture round-robin
  strat_ready <n>                -> exit 0 when every stratum has its target, else 3 (prints the short strata)
  subset <out dir>               -> arm a (change 2): <out>/pool_src_a = the rows of <out>/pool_src with
                                    sha256("c35a|<id>") % <mod> == 0 (default 3; change 9: 5)
  mix    <base jsonl> <src dir> <out jsonl> [repeat guard 3.0]
                                 -> tools/final35/open_pool.main over <src dir>/*.jsonl (open = 0.75 x base)"""
import glob
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from xemb import gsplit as GS  # noqa: E402

X = "/data/harvest/out/xemb_proto/points"
PROD = "/data/harvest/out/teach_l8d/l8s_prod/train"
RING = "/data/harvest/out/teach_l8d/l8s_prod_ring/train"
EVAL58 = "/data/harvest/out/l8x_assets/ood_o_eval/eval_list.json"
OLD = {"rb2": f"{X}/rb2/records_verified_v2.jsonl", "behavior": f"{X}/behavior/records_verified.jsonl",
       "rb3": f"{X}/rb3/records_verified.jsonl", "molmobot_rby1": f"{X}/molmobot_rby1/records_verified.jsonl",
       "maniskill": f"{X}/maniskill/records_verified.jsonl", "agibot_v3": f"{X}/agibot_v3_verified/final_all.jsonl"}
FIX = dict(OLD, rb2=f"{X}/rb2_fix/records.jsonl", rb3=f"{X}/rb3_fix/records.jsonl",
           molmobot_rby1=f"{X}/molmobot_rby1_fix/records.jsonl")


def h100(s):
    return int(hashlib.sha256(s.encode()).hexdigest(), 16) % 100


def ood58(out):
    os.makedirs(out, exist_ok=True)
    eps = [e["dir"].split("/", 1)[1] for e in json.load(open(EVAL58))["episodes"]]
    json.dump({"episodes": eps}, open(os.path.join(out, "ood58.json"), "w"), indent=0)
    print(json.dumps({"ood58": len(eps)}))


def l8s(n, out, after=None):
    """after (UTC ISO, change 3): only episodes finished after the 23:20 KST relaunch with the shuffled furniture order
    (the first 481 production episodes were task-skewed: basket 62 %, simple 38 %, THOR relations 0)."""
    import datetime
    t0 = datetime.datetime.fromisoformat(after.replace("Z", "+00:00")).timestamp() if after else 0.0
    os.makedirs(out, exist_ok=True)
    eps = []
    for root in (PROD, RING):
        for m in glob.glob(os.path.join(root, "*", "*", "meta.json")):
            if os.path.getmtime(m) >= t0:
                eps.append((os.path.getmtime(m), root, os.path.relpath(os.path.dirname(m), root)))
    eps.sort()
    eps = eps[:n]
    man = {(r, s): [] for r in ("main", "ring") for s in ("train", "val")}
    for _t, root, rel in eps:
        seed = rel.rsplit("_s", 1)[-1]
        man[("main" if root == PROD else "ring", "val" if h100(f"c35|{seed}") < 3 else "train")].append(rel)
    counts = {}
    for (r, s), v in man.items():
        json.dump({"episodes": v}, open(os.path.join(out, f"{r}_{s}.json"), "w"), indent=0)
        counts[f"{r}_{s}"] = len(v)
    counts["taken"] = len(eps)
    counts["last_meta_mtime"] = eps[-1][0] if eps else None
    json.dump(counts, open(os.path.join(out, "l8s_counts.json"), "w"), indent=1)
    print(json.dumps(counts))


JOBS = tuple(f"/data/harvest/out/teach_l8d/plan5/jobs_l8s2_{k}.txt" for k in ("m", "x", "into_m", "into_x"))  # change 5
RING_SHARE = 0.0  # change 6: ring V excluded (build KeyError rp_ring in obj_height); was 0.03


def kind_of(task):
    return task.split("__", 1)[0] if "__" in task else "simple"


def plan_strata():
    """plan share per task kind (change 4) over the production job files' plan chunks."""
    import collections
    c = collections.Counter()
    for jf in JOBS:
        for line in open(jf):
            if "--plan" not in line:
                continue
            for e in json.load(open(line.split("--plan", 1)[1].split()[0])):
                c[kind_of(e["task"])] += 1  # change 4: task kind only
    tot = sum(c.values())
    return {k: v / tot for k, v in c.items()}


def finished():
    """[(stratum, root, rel, seed)] of finished episodes (meta.json) in the main and ring roots."""
    out = []
    for root in (PROD, RING):
        for m in glob.glob(os.path.join(root, "*", "*", "meta.json")):
            rel = os.path.relpath(os.path.dirname(m), root)
            vdir, ep = rel.split("/", 1)
            task, seed = ep.rsplit("_s", 1)
            st = "ring" if root == RING else kind_of(task)
            out.append((st, vdir.replace("drf_fx_", "", 1), root, rel, seed))
    return out


def strat_targets(n):
    sh = plan_strata()
    main_n = n - round(n * RING_SHARE)
    t = {k: round(main_n * v) for k, v in sh.items()}
    if RING_SHARE > 0:
        t["ring"] = round(n * RING_SHARE)
    return t


def round_robin(cands):
    """change 4: within a stratum, alternate over furniture (each furniture's episodes in sha256("c35s|<seed>")
    order) so no furniture dominates."""
    import collections
    by = collections.defaultdict(list)
    for c in cands:
        by[c[1]].append(c)
    qs = [sorted(v, key=lambda c: (h100(f"c35s|{c[4]}"), int(c[4]))) for _k, v in sorted(by.items())]
    out, i = [], 0
    while any(qs):
        q = qs[i % len(qs)]
        if q:
            out.append(q.pop(0))
        i += 1
    return out


def strat(n, out, check_only=False):
    """change 3/4: stratified sample of n episodes by plan share of task kind (ring 3 %); within a stratum, furniture
    round-robin, each furniture in sha256("c35s|<seed>") order. Not ready (exit 3) while a stratum is short of its target."""
    import collections
    t = strat_targets(n)
    eps = collections.defaultdict(list)
    for c in finished():
        eps[c[0]].append(c)
    short = {k: [len(eps.get(k, [])), v] for k, v in t.items() if len(eps.get(k, [])) < v}
    if short:
        print(json.dumps({"ready": False, "short": short}))
        sys.exit(3)
    if check_only:
        print(json.dumps({"ready": True}))
        return
    os.makedirs(out, exist_ok=True)
    man = {(r, s): [] for r in ("main", "ring") for s in ("train", "val")}
    furn = collections.Counter()
    for k, v in t.items():
        for _st, fu, root, rel, seed in round_robin(eps[k])[:v]:
            furn[f"{k}|{fu}"] += 1
            man[("main" if root == PROD else "ring", "val" if h100(f"c35|{seed}") < 3 else "train")].append(rel)
    counts = {"targets": t, "by_kind_furniture": dict(furn)}
    for (r, s), v in man.items():
        json.dump({"episodes": v}, open(os.path.join(out, f"{r}_{s}.json"), "w"), indent=0)
        counts[f"{r}_{s}"] = len(v)
    json.dump(counts, open(os.path.join(out, "l8s_counts.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in counts.items() if k != "targets"}))


def split_man(man, k, out):
    """change 7: split a manifest into k round-robin chunks <out>/part<i>.json (parallel build.py, ~27 s/episode)."""
    eps = json.load(open(man))["episodes"]
    os.makedirs(out, exist_ok=True)
    for i in range(k):
        json.dump({"episodes": eps[i::k]}, open(os.path.join(out, f"part{i}.json"), "w"), indent=0)
    print(json.dumps({"episodes": len(eps), "parts": k}))


def pool(verdict_p, out):
    v = json.load(open(verdict_p)).get("verdict") if os.path.exists(verdict_p) else None
    src = FIX if v == "NONINFERIOR" else OLD
    d = os.path.join(out, "pool_src")
    os.makedirs(d, exist_ok=True)
    excl = {x.strip() for x in open(f"{X}/exclude_wide_fisheye.txt") if x.strip()}
    val, counts = [], {"fix_verdict": v, "pool": "FIX" if src is FIX else "OLD+agibot_v3"}
    for name, path in src.items():
        rows = [json.loads(x) for x in open(path, encoding="utf-8")]
        rows = [r for r in rows if r.get("answer") and r.get("images")]
        rows = [r for r in rows if r["id"] not in excl and r.get("view", "head") in ("head", None)]
        rows, _g = GS.split(rows)
        tr = [r for r in rows if h100(f"c35|{r['id']}") >= 3]
        va = [r for r in rows if h100(f"c35|{r['id']}") < 3]
        with open(os.path.join(d, f"{name}.jsonl"), "w", encoding="utf-8", newline="\n") as f:
            f.writelines(json.dumps(r) + "\n" for r in tr)
        for r in va:
            val.append({"id": "val_" + r["id"], "kind": "gpoint", "gset": f"val_{name}", "prompt": r["prompt"],
                        "images": r["images"][:1], "answer": r["answer"], "score": "label"})
        counts[name] = {"train": len(tr), "val": len(va)}
    GS.guard(val, "c35 val_open")
    with open(os.path.join(out, "val_open.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        f.writelines(json.dumps(r) + "\n" for r in val)
    json.dump(counts, open(os.path.join(out, "pool_counts.json"), "w"), indent=1)
    print(json.dumps(counts))


def subset(out, mod=3):
    d, a = os.path.join(out, "pool_src"), os.path.join(out, "pool_src_a")
    os.makedirs(a, exist_ok=True)
    counts = {}
    for p in sorted(glob.glob(os.path.join(d, "*.jsonl"))):
        n = k = 0
        with open(os.path.join(a, os.path.basename(p)), "w", encoding="utf-8", newline="\n") as f:
            for line in open(p, encoding="utf-8"):
                n += 1
                if int(hashlib.sha256(("c35a|" + json.loads(line)["id"]).encode()).hexdigest(), 16) % mod == 0:
                    k += 1
                    f.write(line)
        counts[os.path.basename(p)[:-6]] = {"pool": n, "subset": k}
    json.dump(counts, open(os.path.join(out, "subset_a_counts.json"), "w"), indent=1)
    print(json.dumps(counts))


def mix(base, srcdir, out_jsonl, cap=3.0):
    """open rows = 0.75 x base rows exactly (user-log 195, prereg_c35 change 1); the repeat cap is only a guard
    -- the build log / .counts.json records the repeat actually used."""
    import open_pool as OP
    OP.SOURCES = {os.path.basename(p)[:-6]: p for p in sorted(glob.glob(os.path.join(srcdir, "*.jsonl")))}
    OP.main(base, out_jsonl, 0.75, cap)


if __name__ == "__main__":
    c, a = sys.argv[1], sys.argv[2:]
    {"ood58": lambda: ood58(a[0]), "l8s": lambda: l8s(int(a[0]), a[1], a[2] if len(a) > 2 else None), "pool": lambda: pool(a[0], a[1]),
     "strat": lambda: strat(int(a[0]), a[1]), "strat_ready": lambda: strat(int(a[0]), None, True),
     "subset": lambda: subset(a[0], int(a[1]) if len(a) > 1 else 3), "split_man": lambda: split_man(a[0], int(a[1]), a[2]),
     "mix": lambda: mix(a[0], a[1], a[2], float(a[3]) if len(a) > 3 else 3.0)}[c]()
