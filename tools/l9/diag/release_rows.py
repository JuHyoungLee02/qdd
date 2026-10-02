"""L9 v2 diagnosis: sample-by-sample rows around one trace index (pure numpy): step, commanded / measured gap, the target
centre (world) and tilt, the TCP, and the target centre / finger bodies in the TCP frame G (mm).
usage: python tools/l9/diag/release_rows.py <trace.jsonl> <i> [--before 6] [--after 14]"""
import json
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from trace_view import qmat  # noqa: E402


def main():
    f, i0 = sys.argv[1], int(sys.argv[2])
    a = sys.argv[3:]
    b = int(a[a.index("--before") + 1]) if "--before" in a else 6
    e = int(a[a.index("--after") + 1]) if "--after" in a else 14
    for l in open(f):
        r = json.loads(l)
        if "p" not in r or not i0 - b <= r["i"] <= i0 + e:
            continue
        R, t = qmat(r["tq"]), np.asarray(r["tcp"])
        g = lambda p: np.round((R.T @ (np.asarray(p) - t)) * 1e3).astype(int).tolist()  # noqa: E731
        fx = f" fa {g(r['fa'])} fb {g(r['fb'])}" if "fa" in r else ""
        print(f"{r['i']:4d} {r['step']:11s} cmd {r['w_cmd'] * 1e3:4.0f} gap {r['gap'] * 1e3:4.0f} obj {np.round(r['p'], 3).tolist()} "
              f"tilt {r['tilt']:5.1f} vz {r.get('vz')} tcp {np.round(r['tcp'], 3).tolist()} objG {g(r['p'])}{fx}")


if __name__ == "__main__":
    main()
