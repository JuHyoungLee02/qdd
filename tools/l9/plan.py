"""L9 plans + lane job files (pure; run locally or on the pod).
usage: python tools/l9/plan.py pilot  <out dir> <lanes> [--per 10] [--start 900000] [--job-size 12] [--pod DIR]
       python tools/l9/plan.py prod   <out dir> <lanes> --n N [--start 1000000] [--job-size 30] [--exclude pilot_gate.json]
       python tools/l9/plan.py smoke  <out dir> 1
Rows {seed, arm, family, rule, def, split, job, pool, rooms, style}. Each definition runs only on the (family, rule)
pairs whose scene features meet its needs (compat()); arms alternate within a definition (50 / 50); families and
layout rules are dealt round-robin (stratified). A job = up to job-size rows of one arm; every job gets its own pool
index and room-subset index (consecutive jobs rotate through the catalogs). <out>/jobs_<k>.txt: one run9 argument
line per job, jobs dealt to lanes round-robin."""
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from harvest.l9 import reach9 as R9  # noqa: E402
from harvest.l9 import scene9 as S9  # noqa: E402
from harvest.l9 import task9 as T9  # noqa: E402

CLEAN_SHARE = 0.25  # = L8 style_of: a quarter of the episodes without perturbations


def features(n_seeds: int = 4) -> dict:
    """(family, rule) -> {"second", "higher", "lower", "kinds": set} seen in sampled scenes (both arms)."""
    rm = R9.load_default()
    out = {}
    for f, r in S9.all_rules():
        ft = {"second": 0, "higher": 0, "lower": 0, "kinds": set(), "kinds2": set(), "n": 0}
        for arm in ("right", "left"):
            for s in range(n_seeds):
                sc = S9.sample(f, r, 7000 + s, arm, rm)
                us = S9.usable_nodes(sc)
                ft["n"] += 1
                flat = [n for n in us if n["kind"] in ("top", "zone", "seat")]
                zs = [n["top_z"] for n in flat]
                ft["second"] += bool(zs) and max(zs) - min(zs) >= 0.04
                kc = defaultdict(int)
                for n in us:
                    ft["kinds"].add(n["kind"])
                    kc[n["kind"]] += 1
                ft["kinds2"] |= {k for k, v in kc.items() if v >= 2}
        ft["higher"] = ft["lower"] = ft["second"]
        out[(f, r)] = ft
    return out


def compat(defn, ft) -> bool:
    for nd in defn.needs:
        if nd in ("second", "higher", "lower") and ft["second"] < 0.25 * ft["n"]:
            return False
        if nd.startswith("node:") and not set(nd[5:].split("|")) & ft["kinds"]:
            return False
        if nd.startswith("node2:") and not set(nd[6:].split("|")) & ft["kinds2"]:
            return False
    if any(o.get("on") in ("second", "higher") for o in defn.objs.values()) and ft["second"] < 0.25 * ft["n"]:
        return False
    return True


def style_of(seed: int) -> str:
    import hashlib
    u = int(hashlib.sha256(f"l9-style:{seed}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return "clean" if u < CLEAN_SHARE else ""


def rows_for(defs, per: int, start: int, ft: dict, split: str = "train") -> list:
    rows, seed = [], start
    for i, d in enumerate(defs):
        pairs = [fr for fr in S9.all_rules() if compat(d, ft[fr])]
        if not pairs:
            continue
        for j in range(per):
            f, r = pairs[(i * 7 + j) % len(pairs)]
            rows.append({"seed": seed, "arm": ("right", "left")[(i + j) % 2], "family": f, "rule": r, "def": d.id,
                         "split": split, "style": style_of(seed)})
            seed += 1
    return rows


def jobs(rows: list, job_size: int, pool0: int = 0) -> list:
    by = defaultdict(list)
    for r in rows:
        by[r["arm"]].append(r)
    out, k = [], 0
    for arm in ("right", "left"):
        rs = by[arm]
        for i in range(0, len(rs), job_size):
            chunk = rs[i:i + job_size]
            for r in chunk:
                r.update(job=f"{arm[0]}{k:05d}", pool=pool0 + k, rooms=pool0 + k)
            out.append(chunk)
            k += 1
    return out


def write(out: str, rows: list, chunks: list, lanes: int, name: str, pod: str) -> dict:
    os.makedirs(out, exist_ok=True)
    json.dump(rows, open(os.path.join(out, name), "w"))
    files = [open(os.path.join(out, f"jobs_{k}.txt"), "w", newline="\n") for k in range(lanes)]
    order = sorted(chunks, key=lambda c: c[0]["job"][1:])  # interleave arms
    for i, c in enumerate(order):
        files[i % lanes].write(f"--plan {pod}/{name} --job {c[0]['job']}\n")
    for f in files:
        f.close()
    return {"rows": len(rows), "jobs": len(chunks), "lanes": lanes}


def main():
    mode, out, lanes = sys.argv[1], sys.argv[2], int(sys.argv[3])
    arg = lambda k, d: type(d)(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d  # noqa: E731
    pod = arg("--pod", out)
    ft = features()
    defs = list(T9.DEFS.values())
    if mode == "smoke":
        names = arg("--defs", "in_wide,rel_left,up_to_higher,stack2,ins_one,line2_y").split(",")
        pick = [T9.DEFS[k] for k in names]
        rows = rows_for(pick, arg("--per", 2), arg("--start", 890000), ft)
        ch = jobs(rows, arg("--job-size", 6), arg("--pool0", 0))
        print(json.dumps(write(out, rows, ch, lanes, "plan_smoke.json", pod)))
        return
    if mode == "ogate":  # object gate: every target of the catalog slice, `--tries` clean moves each
        from harvest.l9 import assets9 as A9
        cat = A9.catalog("train")
        tg = sorted(k for k, r in cat.items() if r["role9"] == "target")
        lo, hi = arg("--from", 0), arg("--to", len(tg))
        tg = tg[lo:hi]
        rows, seed, per_job = [], arg("--start", 1900000), arg("--job-size", 24)
        for i in range(0, len(tg), per_job // arg("--tries", 2)):
            ids = tg[i:i + per_job // arg("--tries", 2)]
            for t in range(arg("--tries", 2)):
                for k in ids:
                    rows.append({"seed": seed, "arm": "right", "family": "dining", "rule": "seats2",
                                 "def": "gate_move", "split": "train", "style": "clean", "clean": True,
                                 "fixed": {"A": k}, "obj": k, "pool_ids": ids})
                    seed += 1
        ch = []
        k = 0
        for i in range(0, len(rows), per_job):
            c = rows[i:i + per_job]
            for r in c:
                r.update(job=f"g{k:05d}", pool=arg("--pool0", 5000) + k, rooms=k)
            ch.append(c)
            k += 1
        print(json.dumps(write(out, rows, ch, lanes, "plan_ogate.json", pod)))
        return
    if mode == "pilot":
        rows = rows_for(defs, arg("--per", 10), arg("--start", 900000), ft)
        ch = jobs(rows, arg("--job-size", 12), arg("--pool0", 100))
        print(json.dumps(write(out, rows, ch, lanes, "plan_pilot.json", pod)))
        return
    if mode == "prod":
        keep = None
        if "--defs" in sys.argv:
            keep = set(json.load(open(arg("--defs", "")))["pass"])
        use = [d for d in defs if keep is None or d.id in keep]
        n = arg("--n", 0)
        per = max(1, -(-n // len(use)))
        rows = rows_for(use, per, arg("--start", 1000000), ft)[:n] if n else []
        ch = jobs(rows, arg("--job-size", 30), arg("--pool0", 1000))
        print(json.dumps(write(out, rows, ch, lanes, "plan_prod.json", pod)))
        return
    raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
