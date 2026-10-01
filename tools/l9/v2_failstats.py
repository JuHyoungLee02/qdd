"""L9 v2 pilot failure breakdown (pure): end reasons, last executor notes, pick outcomes, choice failures, max dq.
usage: python tools/l9/v2_failstats.py <collect root> [--arm left|right] [--n 15]"""
import glob
import json
import os
import re
import sys
from collections import Counter


def last_lines(ep: str, k: int = 2) -> list:
    calls = sorted(glob.glob(os.path.join(ep, "calls", "c*")))
    if not calls:
        return []
    t = open(os.path.join(calls[-1], "prompt.txt"), encoding="utf-8").read()
    h = [x for x in t.split("\n") if re.match(r"^\d+: ", x)]
    return h[-k:]


def main():
    root = sys.argv[1]
    arm = sys.argv[sys.argv.index("--arm") + 1] if "--arm" in sys.argv else None
    clean = "--clean" in sys.argv
    since = float(sys.argv[sys.argv.index("--since") + 1]) if "--since" in sys.argv else 0.0
    n_show = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 15
    ends, notes, outc, fails, steps = Counter(), Counter(), Counter(), Counter(), Counter()
    n = ok = jump = 0
    by_arm = Counter()
    for m in glob.glob(os.path.join(root, "**", "meta.json"), recursive=True):
        meta = json.load(open(m))
        if meta.get("grasp_v2") is None or (arm and meta.get("arm") != arm) or os.path.getmtime(m) < since \
                or (clean and meta.get("style") != "clean"):
            continue
        n += 1
        s = bool(meta["success"]) and (meta.get("max_dq_rad") or 0) <= 0.04
        ok += s
        jump += (meta.get("max_dq_rad") or 0) > 0.04
        by_arm[(meta.get("arm"), s)] += 1
        if s:
            continue
        ends[meta.get("end_reason")] += 1
        for x in last_lines(os.path.dirname(m), 1):
            notes[re.sub(r"[-\d.]+", "#", x.split("->", 1)[-1].split(";")[0]).strip()[:90]] += 1
        for p in meta["grasp_v2"].get("picks", []):
            if p.get("choice_fail"):
                fails[p["choice_fail"]] += 1
            tl = p.get("timeline") or {}
            outc[(tl.get("outcome_close"), tl.get("outcome_lift"))] += 1
            if tl.get("fallback_trace"):
                steps["fallback"] += 1
            if tl.get("limit_rejects"):
                steps["limit_rejects"] += 1
    sk = Counter()
    for s in glob.glob(os.path.join(root, "**", "skipped.json"), recursive=True):
        sk[re.sub(r"l9o_\w+", "<obj>", json.load(open(s)).get("reason", ""))[:80]] += 1
    print(json.dumps({"episodes": n, "ok": ok, "yield": round(ok / max(n, 1), 3), "jumps>0.04": jump,
                      "by_arm_ok": {f"{a}/{b}": v for (a, b), v in by_arm.items()},
                      "end_reasons": ends.most_common(), "last_note": notes.most_common(n_show),
                      "pick_outcomes": [[str(k), v] for k, v in outc.most_common(8)], "choice_fail": fails.most_common(),
                      "flags": steps.most_common(), "skipped": sk.most_common(8)}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
