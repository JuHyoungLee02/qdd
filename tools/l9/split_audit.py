"""L9 split audit (read-only): definition-level hold-out leak and eval_ood object/room leak.
For every run dir, every episode dir collect/<split>/<family>/<ep>/ (meta.json = rendered episode, skipped.json = no
episode) is read; reports
  - train definitions (successes) that also appear in any hold-out split, with counts and source plans/jobs
  - the canonical hold-out set (alloc9.holdout_defs over the current definition set) vs the observed one
  - eval_ood objects / rooms that appear in train episodes.
usage: python tools/l9/split_audit.py <run dir>... [--json out.json]"""
import glob
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _load(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def episodes(run_dir):
    """yield (split, meta-or-None, plan row) for every episode dir under run_dir/collect."""
    for split_dir in sorted(glob.glob(os.path.join(run_dir, "collect", "*"))):
        split = os.path.basename(split_dir)
        if split == "ledger" or not os.path.isdir(split_dir):
            continue
        for ep in glob.glob(os.path.join(split_dir, "*", "*")):
            m = _load(os.path.join(ep, "meta.json"))
            if m is not None:
                row = m.get("plan_row") or {}
                yield split, m, row
                continue
            s = _load(os.path.join(ep, "skipped.json"))
            if s is not None:
                yield split, None, s.get("row") or {}


def main():
    a = sys.argv[1:]
    out = a[a.index("--json") + 1] if "--json" in a else None
    runs = [x for x in a if not x.startswith("--") and x != out]
    by = defaultdict(lambda: defaultdict(Counter))  # split -> def -> Counter(succ, eps, rows)
    src = defaultdict(Counter)  # (def) -> plan/job prefix of train successes
    objs = defaultdict(Counter)  # split -> object id -> successes
    rooms = defaultdict(Counter)
    clut = defaultdict(Counter)
    for r in runs:
        for split, m, row in episodes(r):
            d = (m or {}).get("task_id") or row.get("def")
            c = by[split][d]
            c["rows"] += 1
            if m is None:
                continue
            c["eps"] += 1
            ok = bool(m.get("success"))
            c["succ"] += ok
            if ok or split == "eval_ood":
                for o in (m.get("objects") or {}):
                    objs[split][o] += 1
                for o in m.get("clutter") or []:
                    clut[split][o] += 1
                rm = m.get("room")
                if isinstance(rm, dict):
                    rm = rm.get("id") or rm.get("name") or json.dumps(rm, sort_keys=True)
                if rm:
                    rooms[split][str(rm)] += 1
            if ok and split == "train":
                job = str(row.get("job", "?"))
                src[d][job.split("_")[0][:3] + "|" + os.path.basename(r)] += 1
    rep = {"splits": {s: {"defs": len(v), "succ": sum(c["succ"] for c in v.values()),
                          "rows": sum(c["rows"] for c in v.values())} for s, v in by.items()}}
    ho = {d for s, v in by.items() if s == "holdout" for d in v}
    tr = {d for d, c in by.get("train", {}).items() if c["succ"] > 0}
    leak = sorted(ho & tr)
    rep["holdout_defs_observed"] = sorted(ho)
    rep["train_and_holdout"] = {d: {"train_succ": by["train"][d]["succ"], "holdout_succ": by["holdout"][d]["succ"],
                                    "train_sources": dict(src[d].most_common(8))} for d in leak}
    try:
        from harvest.l9 import alloc9 as AL
        from harvest.l9 import scene9 as S9
        from harvest.l9 import task9v2 as V2
        from tools.l9 import plan as PL
        use = V2.defs_for([])
        ft = PL.features()
        pairs = {k: [fr for fr in S9.all_rules("train") if PL.compat(d, ft[fr])] for k, d in use.items()}
        defs = {k: d.family for k, d in use.items() if pairs[k]}
        canon = AL.holdout_defs(defs)
        rep["holdout_defs_canonical_now"] = canon
        rep["canonical_in_train_succ"] = {d: by["train"][d]["succ"] for d in canon if by["train"][d]["succ"]}
    except Exception as e:  # noqa: BLE001
        rep["canonical_error"] = repr(e)
    for kind, tab in (("objects", objs), ("clutter", clut), ("rooms", rooms)):
        ev = set(tab.get("eval_ood", {}))
        trn = set(tab.get("train", {}))
        rep[f"eval_ood_{kind}"] = len(ev)
        rep[f"eval_ood_{kind}_in_train"] = len(ev & trn)
        rep[f"eval_ood_{kind}_in_train_examples"] = sorted(ev & trn)[:10]
    print(json.dumps(rep, indent=1))
    if out:
        json.dump(rep, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
