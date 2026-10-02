"""L9 v2 diagnosis: read a run9_trace file (<trace dir>/<seed>.jsonl) and print, around grasp / release events, the
target's position in the TCP frame G (x, y = closing axis, z = -approach; mm), the pad gap, the commanded width and
the target's tilt. Pure numpy.
usage: python tools/l9/diag/trace_view.py <seed.jsonl> [--steps descend_close,carry_up,lower_open] [--every 1]"""
import json
import sys

import numpy as np


def qmat(q):
    w, x, y, z = (float(v) for v in q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def main():
    a = sys.argv[1:]
    steps = set(a[a.index("--steps") + 1].split(",")) if "--steps" in a else {"descend_close", "carry_up", "lower_open",
                                                                              "retreat", "reopen"}
    every = int(a[a.index("--every") + 1]) if "--every" in a else 1
    rows = [json.loads(l) for l in open(a[0])]
    prev = None
    for k, r in enumerate(rows):
        if "err" in r or r.get("step") not in steps:
            prev = r.get("step")
            continue
        if k % every and r.get("step") == prev:
            continue
        prev = r.get("step")
        s = f"{r['i']:5d} t {r.get('t')} {r.get('step'):13s} gap {r['gap'] * 1e3:5.1f} wcmd {r['w_cmd'] * 1e3:5.1f}"
        if "p" in r and "tq" in r:
            R = qmat(r["tq"])
            d = R.T @ (np.asarray(r["p"]) - np.asarray(r["tcp"]))
            w = np.asarray(r["p"]) - np.asarray(r["tcp"])
            ap = -R[:, 2]
            s += (f" obj_in_G mm x {d[0] * 1e3:6.1f} y {d[1] * 1e3:6.1f} z {d[2] * 1e3:6.1f} | world hxy {np.hypot(*w[:2]) * 1e3:5.1f}"
                  f" dz {w[2] * 1e3:6.1f} | approach {np.round(ap, 2).tolist()} tilt {r.get('tilt')} vz {r.get('vz')}")
        print(s)


if __name__ == "__main__":
    main()
