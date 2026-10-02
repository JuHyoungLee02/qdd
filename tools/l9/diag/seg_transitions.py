"""L9 v2 diagnosis: truth-step transitions between targets of multi-target episodes (pure): (last step of target k,
first step of target k+1) counts, split by episode success.
usage: python tools/l9/diag/seg_transitions.py <collect root> [...] [--since EPOCH]"""
import glob
import json
import os
import sys
from collections import Counter


def main():
    a = sys.argv[1:]
    since = float(a[a.index("--since") + 1]) if "--since" in a else 0.0
    c = Counter()
    for root in [x for x in a if os.path.isdir(x)]:
        for m in glob.glob(os.path.join(root, "**", "meta.json"), recursive=True):
            if os.path.getmtime(m) < since:
                continue
            meta = json.load(open(m))
            if meta.get("grasp_v2") is None:
                continue
            labs = [json.loads(l) for l in open(os.path.join(os.path.dirname(m), "labels.jsonl"))]
            for x, y in zip(labs, labs[1:]):
                if x.get("tgt") != y.get("tgt"):
                    c[(x.get("step"), y.get("step"), bool(meta.get("success")))] += 1
    for k, v in c.most_common():
        print(k, v)


if __name__ == "__main__":
    main()
