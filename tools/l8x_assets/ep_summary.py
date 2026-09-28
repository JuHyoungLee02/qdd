"""One-line summaries of collected episodes: meta (success, judge, end), the label steps, last truth positions.
usage: python tools/l8x_assets/ep_summary.py EP_DIR [EP_DIR ...]"""
from __future__ import annotations

import json
import os
import sys


def main(argv=None):
    for d in argv or sys.argv[1:]:
        m = json.load(open(os.path.join(d, "meta.json")))
        rows = [json.loads(x) for x in open(os.path.join(d, "labels.jsonl"))]
        steps = [r.get("step") for r in rows]
        last = rows[-1]["gt"] if rows else {}
        res = {}
        p = os.path.join(d, "result.json")
        if os.path.exists(p):
            r = json.load(open(p))
            res = {k: r.get(k) for k in ("success", "end_reason", "fail_stage", "stage", "pred_final") if k in r}
        print(os.path.basename(d), {k: m.get(k) for k in ("success", "judge", "end_reason", "n_calls")}, steps,
              "tgt", last.get("tgt"), "place", last.get("place"), "tcp", last.get("tcp"), res)


if __name__ == "__main__":
    main()
