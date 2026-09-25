"""E-MA1b data (prereg_ma1b §2): A3d targets for every se2e_c1 row from the full-rate parquet state.

  python tools/ma1/build_a3d.py --rows-root /data/harvest/data/se2e_c1/conv --out /data/harvest/data/ma1b/conv
Writes <out>/<kind>.a3d.jsonl (one line per row, same order: key, arm, d [12] m, mask [4], end, span_s,
label_check_m) and <out>/a3d_stats.json. Stops if any row's label check (FK(k + label_steps) - FK(k) vs the row's
ee_delta) exceeds LABEL_TOL -- the targets then use the same FK / frames as the decision labels. Never writes under
--rows-root. Pod python with pyarrow (/data/harvest/venv_e3st).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from multiprocessing import Pool

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import numpy as np  # noqa: E402

from harvest.train import se2e_a3d as A  # noqa: E402
from harvest.train import se2e_data as S  # noqa: E402

LABEL_TOL = 2e-5  # m; ee_delta is rounded to 1e-5 m


def _episode(args):
    import se2e_convert as C
    root, info, kind, ep, rows, urdf = args
    chain = {arm: S.load_arm_chain(urdf, arm) for arm in ("left", "right")}
    pq_path, _ = C._paths(root, info, ep)
    _, st, _ = C._read_pq(pq_path)
    return A.episode_targets(rows, st, info["features"]["observation.state"]["names"], chain, info["fps"])


def summarize(out_rows) -> dict:
    span = np.array([r["span_s"] for r in out_rows])
    m = np.array([r["mask"][0] for r in out_rows])
    d = np.array([np.linalg.norm(np.reshape(r["d"], (4, 3))[-1]) for r in out_rows if r["mask"][0]])
    return {"rows": len(out_rows), "masked_rows": int((m == 0).sum()), "span_s_median": float(np.median(span)),
            "span_s_frac_cap3s": float(np.mean(span >= 3.0 - 1e-9)),
            "end_disp_m_median": float(np.median(d)) if len(d) else None,
            "end_disp_m_p90": float(np.quantile(d, 0.9)) if len(d) else None,
            "label_check_max_m": float(max(r["label_check_m"] for r in out_rows))}


def main():
    import se2e_convert as C
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows-root", default="/data/harvest/data/se2e_c1/conv")
    ap.add_argument("--raw", default="/data/harvest/data/se2e/raw")
    ap.add_argument("--urdf", default="/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    src, out = os.path.abspath(a.rows_root), os.path.abspath(a.out)
    if out == src or out.startswith(src + os.sep):
        raise SystemExit("--out must not be under --rows-root")
    os.makedirs(out, exist_ok=True)
    stats = {}
    for kind, name in C.DATASETS.items():
        path = A.targets_path(out, kind)
        if os.path.exists(path):
            raise SystemExit(f"{path} exists (data versions are never overwritten)")
        root = os.path.join(a.raw, name)
        info, _, _ = C._meta(root)
        order = [json.loads(x) for x in open(S.rows_path(src, kind), encoding="utf-8")]
        by = {}
        for r in order:
            by.setdefault(r["seed"], []).append(r)
        jobs = [(root, info, kind, ep, rows, a.urdf) for ep, rows in by.items()]
        got = {}
        with Pool(a.workers) as p:
            for res in p.imap_unordered(_episode, jobs, chunksize=4):
                for t in res:
                    got[t["key"]] = t
        rows_out = [got[f"{r['kind']}_ep{r['seed']}_k{r['k']}"] for r in order]
        bad = [t["key"] for t in rows_out if t["label_check_m"] > LABEL_TOL]
        if bad:
            raise SystemExit(f"{kind}: {len(bad)} rows fail the label check, e.g. {bad[:3]}")
        with open(path, "w", encoding="utf-8") as f:
            for t in rows_out:
                f.write(json.dumps(t, separators=(",", ":")) + "\n")
        stats[kind] = summarize(rows_out)
        print(kind, stats[kind], flush=True)
    json.dump(stats, open(os.path.join(out, "a3d_stats.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
