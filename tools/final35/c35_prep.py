"""E-C35 (docs/stage3/prereg_c35.md) data preparation.
  ood58  <out dir>               -> manifest of the 58 new OOD-O evaluation episodes (eval_list.json)
  l8s    <n> <out dir>           -> the first <n> finished L8S production episodes (meta.json, by its mtime; main and
                                    ring roots), episode-level validation split sha256("c35|<seed>") % 100 < 3;
                                    manifests <out>/{main,ring}_{train,val}.json + counts
  pool   <verdict_fix.json> <out dir>
                                 -> open point sources (FIX pool when E-POOLV8-FIX is NONINFERIOR, else the old pool
                                    with AgiBot v3 final in place of agibot_p0), G rows removed, 3 % of rows by
                                    sha256("c35|<id>") % 100 < 3 held out -> <out>/pool_src/<src>.jsonl (train part)
                                    + <out>/val_open.jsonl (geval format, gset val_<src>)
  mix    <base jsonl> <out dir> <out jsonl>
                                 -> tools/final35/open_pool.main over <out>/pool_src (p 0.75, repeat cap 1.5)"""
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


def l8s(n, out):
    os.makedirs(out, exist_ok=True)
    eps = []
    for root in (PROD, RING):
        for m in glob.glob(os.path.join(root, "*", "*", "meta.json")):
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


def mix(base, out, out_jsonl):
    import open_pool as OP
    OP.SOURCES = {os.path.basename(p)[:-6]: p for p in sorted(glob.glob(os.path.join(out, "pool_src", "*.jsonl")))}
    OP.main(base, out_jsonl, 0.75, 1.5)


if __name__ == "__main__":
    c, a = sys.argv[1], sys.argv[2:]
    {"ood58": lambda: ood58(a[0]), "l8s": lambda: l8s(int(a[0]), a[1]), "pool": lambda: pool(a[0], a[1]),
     "mix": lambda: mix(a[0], a[1], a[2])}[c]()
