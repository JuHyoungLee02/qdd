"""L9 v2 diagnosis: multi-step episodes (meta n_steps >= 2) -- which pick / step failed and how (pure).
usage: python tools/l9/diag/second_pick.py <collect root> [...] [--since EPOCH] [--robot NAME] [--hist 3]
Per failed multi-step episode: the truth step sequence compressed (above_target>descend_close>... per call), how many
targets were placed (labels: the 'tgt' key changes), per pick record (object, family, close / lift outcome, fallback
statuses, choice failure, valid stats) and the last history lines. Summary: failures by pick index and by kind."""
import glob
import json
import os
import re
import sys
from collections import Counter


def main():
    a = sys.argv[1:]
    since = float(a[a.index("--since") + 1]) if "--since" in a else 0.0
    robot = a[a.index("--robot") + 1] if "--robot" in a else None
    nh = int(a[a.index("--hist") + 1]) if "--hist" in a else 3
    roots = [x for x in a if os.path.isdir(x)]
    by_idx, kinds, n_multi, n_ok = Counter(), Counter(), 0, 0
    for root in roots:
        for m in sorted(glob.glob(os.path.join(root, "**", "meta.json"), recursive=True)):
            if os.path.getmtime(m) < since:
                continue
            meta = json.load(open(m))
            g = meta.get("grasp_v2")
            if g is None or int(meta.get("n_steps") or 1) < 2:
                continue
            if robot and g.get("robot_profile") != robot:
                continue
            n_multi += 1
            ok = bool(meta.get("success")) and (meta.get("max_dq_rad") or 0) <= 0.04
            n_ok += ok
            if ok:
                continue
            ep = os.path.dirname(m)
            labs = [json.loads(l) for l in open(os.path.join(ep, "labels.jsonl"))]
            tg_seq = []
            for l in labs:
                if not tg_seq or tg_seq[-1][0] != l.get("tgt"):
                    tg_seq.append([l.get("tgt"), []])
                tg_seq[-1][1].append(l.get("step"))
            idx = len(tg_seq) - 1
            last_steps = tg_seq[-1][1][-4:] if tg_seq else []
            calls = sorted(glob.glob(os.path.join(ep, "calls", "c*")))
            h = [x for x in open(os.path.join(calls[-1], "prompt.txt"), encoding="utf-8").read().split("\n")
                 if re.match(r"^\d+: ", x)] if calls else []
            note = h[-1] if h else ""
            kind = ("no grasp" if re.search(r"no (plannable|reachable) grasp|out of reach", note) else
                    "no path" if "no collision-free path" in note else
                    "tipped" if last_steps[-1:] == ["tipped"] else meta.get("end_reason"))
            by_idx[idx] += 1
            kinds[(idx, kind)] += 1
            print(f"== {os.path.relpath(ep, root)} steps={meta.get('n_steps')} end={meta.get('end_reason')} "
                  f"failed_pick={idx} kind={kind}")
            print("   seq", [(t[:10] if t else t, "/".join(s[:1] + s[-2:])) for t, s in tg_seq])
            for p in g.get("picks", []):
                tl = p.get("timeline", {})
                fb = [x.get("status") for x in tl.get("fallback_trace", [])]
                print(f"   pick {p.get('obj', '')[:14]} fam={p.get('family')} close={tl.get('outcome_close')} "
                      f"lift={tl.get('outcome_lift')} fb={fb[:3]}{'...' if len(fb) > 3 else ''} fail={p.get('choice_fail')} "
                      f"vs={p.get('valid_stats')}")
            for x in h[-nh:]:
                print("   |", x[:200])
    print(f"\nMULTI {n_multi} ok {n_ok}; failed by pick index {dict(by_idx)}; kinds {sorted(kinds.items())}")


if __name__ == "__main__":
    main()
