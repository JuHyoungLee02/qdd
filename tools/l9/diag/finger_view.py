"""L9 v2 diagnosis: finger bodies and target in the TCP frame G around closes (run9_trace with fa / fb / fq). Pure numpy.
usage: python tools/l9/diag/finger_view.py <seed.jsonl> [--from I] [--to I] [--every N]
Columns: i, step, gap, finger A / B (x, y, z mm in G), target centre (x, y, z mm in G), target tilt, finger joints."""
import json
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from trace_view import qmat  # noqa: E402


def main():
    a = sys.argv[1:]
    lo = int(a[a.index("--from") + 1]) if "--from" in a else 0
    hi = int(a[a.index("--to") + 1]) if "--to" in a else 10 ** 9
    ev = int(a[a.index("--every") + 1]) if "--every" in a else 1
    for k, l in enumerate(open(a[0])):
        r = json.loads(l)
        if "fa" not in r or not lo <= r["i"] <= hi or k % ev:
            continue
        R, t = qmat(r["tq"]), np.asarray(r["tcp"])
        f = lambda p: np.round((R.T @ (np.asarray(p) - t)) * 1e3, 1).tolist()  # noqa: E731
        print(f"{r['i']:4d} {r['step']:13s} gap {r['gap'] * 1e3:5.1f} A {f(r['fa'])} B {f(r['fb'])} obj {f(r['p']) if 'p' in r else None} "
              f"tilt {r.get('tilt')} fq {r.get('fq')}")


if __name__ == "__main__":
    main()
