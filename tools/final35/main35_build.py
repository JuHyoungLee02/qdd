"""Main 35B final build (docs/stage3/prereg_main35.md) from the pre-built chunks.
  base <prebuild dir> <out dir>
      -> <out>/base_main35_d-min.jsonl: every chunk's train_d-min.jsonl (main root; ring chunks too when
         <prebuild>/RING_OK exists) minus the validation episodes; validation = episode-level
         sha256("m35|<seed>") % 100 < 3 -> <out>/val_episodes.txt (<root>/train/<vdir>/<episode> dirs) + counts
  gate <E-C35 verdict_summary.json>  -> exit 0 when b_vs_f35d is NONINFERIOR, else 2
  mix  <base jsonl> <pool src dir> <out jsonl>
      -> tools/final35/open_pool.main, open = min(0.75 x base, 2.0 x pool) (user-log 197: p 0.75, repeat cap 2.0)"""
import glob
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
PROD = "/data/harvest/out/teach_l8d/l8s_prod/train"
RING = "/data/harvest/out/teach_l8d/l8s_prod_ring/train"
SEED = re.compile(r"_s(\d+)_c\d+$")


def is_val(seed):
    return int(hashlib.sha256(f"m35|{seed}".encode()).hexdigest(), 16) % 100 < 3


def base(pre, out):
    os.makedirs(out, exist_ok=True)
    files = sorted(glob.glob(os.path.join(pre, "chunks", "c*", "train_d-min.jsonl")))
    rfiles = sorted(glob.glob(os.path.join(pre, "ring_chunks", "r*", "train_d-min.jsonl"))) \
        if os.path.exists(os.path.join(pre, "RING_OK")) else []
    n_tr = n_val = 0
    val_eps = set()
    with open(os.path.join(out, "base_main35_d-min.jsonl"), "w", encoding="utf-8", newline="\n") as fo:
        for f in files + rfiles:
            root = RING if "/ring_chunks/" in f else PROD
            for line in open(f, encoding="utf-8"):
                r = json.loads(line)
                seed = str(r["seed"]) if r.get("seed") is not None else SEED.search(r["id"]).group(1)
                if is_val(seed):
                    n_val += 1
                    ep = r.get("episode", "")  # "<episode folder>_<vdir>"
                    vdir = r.get("vdir")
                    if vdir and ep.endswith("_" + vdir):
                        val_eps.add(os.path.join(root, vdir, ep[: -len(vdir) - 1]))
                    continue
                n_tr += 1
                fo.write(line if line.endswith("\n") else line + "\n")
    open(os.path.join(out, "val_episodes.txt"), "w").write("".join(sorted(e + "\n" for e in val_eps)))
    c = {"chunks": len(files), "ring_chunks": len(rfiles), "train_rows": n_tr, "val_rows_dropped": n_val,
         "val_episodes": len(val_eps)}
    json.dump(c, open(os.path.join(out, "base_counts.json"), "w"), indent=1)
    print(json.dumps(c))


def mix(base_p, srcdir, out_jsonl):
    import open_pool as OP
    OP.SOURCES = {os.path.basename(p)[:-6]: p for p in sorted(glob.glob(os.path.join(srcdir, "*.jsonl")))}
    OP.main(base_p, out_jsonl, 0.75, 2.0)


def gate(summary_p):
    """exit 0 when E-C35 arm b vs f35_d is NONINFERIOR, 2 otherwise (missing file / WORSE)."""
    try:
        v = json.load(open(summary_p))["b_vs_f35d"]["verdict"]
    except Exception as ex:  # noqa: BLE001
        print(json.dumps({"gate": "ERROR", "why": repr(ex)[:200]}))
        sys.exit(2)
    print(json.dumps({"gate": v}))
    sys.exit(0 if v == "NONINFERIOR" else 2)


if __name__ == "__main__":
    c, a = sys.argv[1], sys.argv[2:]
    {"base": lambda: base(a[0], a[1]), "mix": lambda: mix(a[0], a[1], a[2]), "gate": lambda: gate(a[0])}[c]()
