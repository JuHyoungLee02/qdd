"""L9 v2 diagnosis: what happens to the placed object around the release (run9_trace files; pure numpy).
usage: python tools/l9/diag/release_trace.py <trace.jsonl> [...] [--win 40]
For every release (first sample of a lower_open segment whose commanded width rises above the closed gap, i.e. the open
command): the target's tilt / height / xy drift and the hand height at -win .. +win samples, the finger bodies
(closing-axis coordinate in G, mm) at the open, and a class:
  PRE_TILT      tilt >= 8 deg already at the open (object turned in the hand / put pose not upright)
  DESCENT_TILT  tilt grew >= 8 deg during the lowering before the open (contact with the surface / a neighbour)
  RELEASE_TILT  upright at the open, tilt grew >= 8 deg within win samples after it (pushed by fingers / dropped)
  DROP          the object fell > 8 mm after the open without tilting (released in the air)
  OK            none of the above"""
import json
import math
import sys
from collections import Counter

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from trace_view import qmat  # noqa: E402


def _quat(r):
    """target quaternion of a trace row: the run9_trace 'q' key holds the arm joints, the object quaternion is 'oq' in
    newer traces; fall back to None."""
    return r.get("oq")


def main():
    a = sys.argv[1:]
    win = int(a[a.index("--win") + 1]) if "--win" in a else 40
    cnt = Counter()
    for f in [x for x in a if x.endswith(".jsonl")]:
        rows = [json.loads(l) for l in open(f)]
        geom = {r["geom"]: np.asarray(r["he"], float) for r in rows if "geom" in r}
        rows = [r for r in rows if "p" in r and "err" not in r]
        k = 0
        while k < len(rows):
            r = rows[k]
            if r.get("step") == "lower_open" and k > 0 and r["w_cmd"] > rows[k - 1]["w_cmd"] + 1e-4 and r["w_cmd"] > r["gap"] + 0.003:
                lo, hi = max(0, k - win), min(len(rows) - 1, k + win)
                seg_pre = [s for s in rows[lo:k + 1] if s.get("tgt") == r.get("tgt")]
                post = [s for s in rows[k:hi + 1] if s.get("tgt") == r.get("tgt")]
                tilt0 = r["tilt"]
                tilt_pre_min = min(s["tilt"] for s in seg_pre if s.get("step") in ("lower_open", "carry_over"))
                tilt_post = max(s["tilt"] for s in post)
                dz = post[-1]["p"][2] - r["p"][2]
                dxy = float(np.linalg.norm(np.subtract(post[-1]["p"][:2], r["p"][:2])))
                if tilt0 >= 8:
                    c = "PRE_TILT" if tilt_pre_min >= 8 or seg_pre[0]["tilt"] >= 8 else "DESCENT_TILT"
                elif tilt_post - tilt0 >= 8:
                    c = "RELEASE_TILT"
                elif dz < -0.008:
                    c = "DROP"
                else:
                    c = "OK"
                when = next(((s["i"] - r["i"], s.get("step"), round(s["gap"] * 1e3)) for s in post
                             if s["tilt"] - tilt0 >= 8), None)
                if c == "RELEASE_TILT" and when is not None:
                    c = "RELEASE_TILT/" + ("retreat" if when[1] == "retreat" else "opening" if when[1] == "lower_open" else str(when[1]))
                cnt[c] += 1
                fy = ""
                if "fa" in r and "tq" in r:
                    R, t = qmat(r["tq"]), np.asarray(r["tcp"])
                    ya = (R.T @ (np.asarray(r["fa"]) - t))[1] * 1e3
                    yb = (R.T @ (np.asarray(r["fb"]) - t))[1] * 1e3
                    yo = (R.T @ (np.asarray(r["p"]) - t))[1] * 1e3
                    fy = f" fingers y {ya:+.0f}/{yb:+.0f} obj y {yo:+.0f} mm"
                sup = ""
                if "pp" in r and r.get("tgt") in geom:
                    Rt, Rp = qmat(r["q"]) if "q" in r and len(r["q"]) == 4 else None, qmat(r["pq"])
                    Rt = qmat(rows[k]["q"]) if False else None
                    ht = float(np.abs(qmat(_quat(r))[2]) @ geom[r["tgt"]]) if _quat(r) is not None else None
                    he = geom.get(r["pl"], np.zeros(3))  # spot markers: no extent, the marker sits on the surface
                    top = r["pp"][2] + float(np.abs(Rp[2]) @ he)
                    loc = Rp.T @ (np.asarray(r["p"]) - np.asarray(r["pp"]))
                    if ht is not None:
                        sup = (f" | bottom-over-place-top {(r['p'][2] - ht - top) * 1e3:+.0f} mm, centre in place frame "
                               f"({loc[0] * 1e3:+.0f},{loc[1] * 1e3:+.0f}) of half ({he[0] * 1e3:.0f},{he[1] * 1e3:.0f}) mm, "
                               f"place tilt {math.degrees(math.acos(max(-1, min(1, Rp[2, 2])))):.0f}")
                print(f"{f.rsplit('/', 1)[-1]:16s} i {r['i']:4d} {c:12s} tilt pre-min {tilt_pre_min:5.1f} at-open {tilt0:5.1f} "
                      f"post-max {tilt_post:5.1f} | obj dz {dz * 1e3:+6.1f} dxy {dxy * 1e3:5.1f} mm | gap {r['gap'] * 1e3:.0f} "
                      f"cmd {r['w_cmd'] * 1e3:.0f}{fy} | tilt+8 at (di, step, gap) {when}{sup}")
                k = hi
            k += 1
    print("\nCLASSES", dict(cnt))


if __name__ == "__main__":
    main()
