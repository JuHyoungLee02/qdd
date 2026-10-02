"""L9 v2 diagnosis: hand rotation during carry moves in run9_trace files (pure numpy).
usage: python tools/l9/diag/carry_rot.py <trace.jsonl> [...]
Per contiguous segment of truth step carry_up / carry_over / lower_open: the largest TCP rotation from the segment's
first sample (deg), the rotation between first and last sample, and the target tilt at start / max / end."""
import json
import math
import sys

import numpy as np


def ang(q1, q2) -> float:
    d = abs(float(np.dot(np.asarray(q1, float), np.asarray(q2, float))))
    return math.degrees(2 * math.acos(min(1.0, d)))


def main():
    allmax = []
    for f in sys.argv[1:]:
        rows = [json.loads(l) for l in open(f)]
        rows = [r for r in rows if "tq" in r]
        seg = []
        for r in rows + [{"step": None}]:
            if seg and r.get("step") != seg[0]["step"]:
                if seg[0]["step"] in ("carry_up", "carry_over", "lower_open") and len(seg) > 3:
                    q0 = seg[0]["tq"]
                    mx = max(ang(q0, s["tq"]) for s in seg)
                    end = ang(q0, seg[-1]["tq"])
                    tl = [s.get("tilt") or 0 for s in seg]
                    allmax.append(mx)
                    print(f"{f.rsplit('/', 1)[-1]:16s} {seg[0]['step']:11s} i {seg[0]['i']}-{seg[-1]['i']} rot max {mx:5.1f} "
                          f"end {end:5.1f} deg | tilt {tl[0]:.1f} max {max(tl):.1f} end {tl[-1]:.1f}")
                seg = []
            if r.get("step") is not None:
                seg.append(r)
    if allmax:
        a = np.array(allmax)
        print(f"segments {len(a)}: rot max median {np.median(a):.1f} deg, > 20 deg {int((a > 20).sum())}, > 45 deg {int((a > 45).sum())}")


if __name__ == "__main__":
    main()
