"""L9 v2 diagnosis: how did each release (truth step lower_open) end, and what happened to the object (pure).
usage: python tools/l9/diag/release_check.py <collect root> [...] [--since EPOCH] [--robot NAME] [--list]
Per lower_open call: the executor result of that call's history line (reached / stopped short / BLOCKED / no path),
the hand height error, the target's z at the lower_open call and at the next call (drop = released in the air), and
whether the next call's truth step is 'tipped'. Summary table result kind x (next step, success)."""
import glob
import json
import os
import re
import sys
from collections import Counter


def kind_of(line: str) -> str:
    if "BLOCKED" in line:
        return "blocked"
    if "short of the target" in line:
        return "short"
    if "no collision-free path" in line:
        return "no_path"
    if "reached the target" in line:
        return "reached"
    return "other"


def main():
    a = sys.argv[1:]
    since = float(a[a.index("--since") + 1]) if "--since" in a else 0.0
    robot = a[a.index("--robot") + 1] if "--robot" in a else None
    roots = [x for x in a if os.path.isdir(x)]
    tab = Counter()
    for root in roots:
        for m in sorted(glob.glob(os.path.join(root, "**", "meta.json"), recursive=True)):
            if os.path.getmtime(m) < since:
                continue
            meta = json.load(open(m))
            g = meta.get("grasp_v2")
            if g is None or (robot and g.get("robot_profile") != robot):
                continue
            ep = os.path.dirname(m)
            labs = [json.loads(l) for l in open(os.path.join(ep, "labels.jsonl"))]
            calls = sorted(glob.glob(os.path.join(ep, "calls", "c*")))
            if not calls:
                continue
            h = {int(x.split(":")[0]): x for x in open(os.path.join(calls[-1], "prompt.txt"), encoding="utf-8")
                 .read().split("\n") if re.match(r"^\d+: ", x)}
            ok = bool(meta.get("success")) and (meta.get("max_dq_rad") or 0) <= 0.04
            for i, l in enumerate(labs):
                if l.get("step") != "lower_open":
                    continue
                c = int(l.get("call", i))
                line = h.get(c + 1, "")  # history line n describes call n-1's command (1-based)
                k = kind_of(line)
                nxt = labs[i + 1] if i + 1 < len(labs) else None
                z0 = (l.get("gt") or {}).get("tgt", [None] * 3)[2]
                z1 = ((nxt or {}).get("gt") or {}).get("tgt", [None] * 3)[2]
                ns = (nxt or {}).get("step") if nxt else "end"
                same = nxt is not None and nxt.get("tgt") == l.get("tgt")
                tab[(k, ns if same else "next_target/end", ok)] += 1
                if "--list" in a and k != "reached":
                    print(f"{k:8s} next={ns} ok={ok} z {z0}->{z1} {os.path.relpath(ep, root)} | {line[:170]}")
    print("\n(result, next step, episode ok): n")
    for k, v in sorted(tab.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
