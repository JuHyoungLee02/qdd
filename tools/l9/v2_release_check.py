"""Where was the hand when it opened at the place (pure, L9 v2 diagnosis): for each v2 episode with a lower_open call,
the put TCP of the last lower_open command vs the TCP at the open command (result.json tcp_path, timeline t_open_cmd),
plus tipped / collision / end offset. Successes and failures side by side.
usage: python tools/l9/v2_release_check.py <collect root> [--since EPOCH] [--n 30] [--fail]"""
import glob
import json
import os
import sys

import numpy as np


def tcp_at(path, t):
    if not path or t is None:
        return None
    P = np.asarray(path, float)
    i = int(np.clip(np.searchsorted(P[:, 0], t), 0, len(P) - 1))
    return P[i, 1:]


def last_with(o, key):
    """The last dict (depth-first) in o that has key (the timeline sits in grasp_v2 / picks)."""
    out = None
    if isinstance(o, dict):
        if key in o:
            out = o
        for v in o.values():
            out = last_with(v, key) or out
    elif isinstance(o, list):
        for v in o:
            out = last_with(v, key) or out
    return out


def main():
    a = sys.argv[1:]
    since = float(a[a.index("--since") + 1]) if "--since" in a else 0.0
    nmax = int(a[a.index("--n") + 1]) if "--n" in a else 30
    only_fail = "--fail" in a
    stats = {True: [], False: []}
    k = 0
    for m in sorted(glob.glob(os.path.join(a[0], "**", "meta.json"), recursive=True)):
        if os.path.getmtime(m) < since:
            continue
        meta = json.load(open(m))
        if meta.get("grasp_v2") is None or (only_fail and meta["success"]):
            continue
        d = os.path.dirname(m)
        try:
            rows = [json.loads(x) for x in open(os.path.join(d, "labels.jsonl"))]
            res = json.load(open(os.path.join(d, "result.json")))
        except (OSError, ValueError):
            continue
        lo = [r for r in rows if r.get("step") == "lower_open"]
        tl = (last_with(meta, "t_open_cmd") or {})
        if not lo or tl.get("t_open_cmd") is None:
            continue
        put = np.array(json.loads(lo[-1]["answer"])["command"]["position_m"], float)
        tcp = tcp_at(res.get("tcp_path"), tl["t_open_cmd"])
        if tcp is None:
            continue
        dz, dxy = 1000 * (tcp[2] - put[2]), 1000 * float(np.hypot(*(tcp[:2] - put[:2])))
        ok = bool(meta["success"])
        stats[ok].append((dz, dxy))
        if k < nmax and not ok:
            gl = rows[-1].get("gt") or {}
            off = 1000 * np.hypot(*np.subtract(gl["tgt"][:2], gl["place"][:2])) if gl.get("tgt") else float("nan")
            print(f"{os.path.relpath(d, a[0])}  open dz {dz:+.0f} mm dxy {dxy:.0f} mm  n_lower_open {len(lo)}"
                  f"  tipped {res.get('tipped')} collision {res.get('collision')}  end off {off:.0f} mm")
            k += 1
    for ok, v in stats.items():
        if v:
            A = np.array(v)
            print(f"{'success' if ok else 'fail'} n {len(A)}  open dz median {np.median(A[:, 0]):+.0f} mm "
                  f"p90 {np.percentile(A[:, 0], 90):+.0f}  dxy median {np.median(A[:, 1]):.0f} mm "
                  f"p90 {np.percentile(A[:, 1], 90):.0f}  dz>20mm {int((A[:, 0] > 20).sum())}")


if __name__ == "__main__":
    main()
