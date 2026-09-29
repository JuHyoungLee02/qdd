"""prereg_marr §3 C0 reuse checks (1) and (3), and the prediction comparison used by (2) and the §4 view check.

  reuse_check.py args C0_LOG A_LOG            (1) config.args equal outside run / out_root / aux_extra / a3d_root /
                                                  tracept_root
  reuse_check.py code OLD_CODE NEW_CODE        (3) training-path files: content equal after CR stripping (the
                                                  se2e_confirm copy is CRLF, P21); stageb_train.py is listed separately
  reuse_check.py pred A.jsonl B.jsonl [--ignore k1,k2]
                                               records equal field by field outside utc (+ ignored keys); on a
                                               difference also the item-level argmax agreement and max |d log-prob|
"""
from __future__ import annotations

import argparse
import json
import os

EXCLUDE_ARGS = {"run", "out_root", "aux_extra", "a3d_root", "tracept_root"}
TRAIN_FILES = ("harvest/train/stageb_data.py", "harvest/train/stageb_model.py", "harvest/train/stageb_expert.py",
               "harvest/train/prefix_share.py", "harvest/train/se2e_data.py", "harvest/train/se2e_temporal.py",
               "harvest/train/se2e_temporal_model.py", "harvest/train/stagea_train.py", "harvest/train/stagea_loss.py",
               "harvest/train/stagea_data.py", "harvest/clients/jevl.py", "harvest/deccall_snap.py",
               "harvest/jevcall.py", "harvest/options.py", "harvest/e3lite.py", "harvest/serialize.py")
OPTION_FILES = ("harvest/train/stageb_train.py",)


def cmd_args(c0_log, a_log):
    c0 = json.loads(open(c0_log).readline())["args"]
    a = json.loads(open(a_log).readline())["args"]
    keys = (set(c0) | set(a)) - EXCLUDE_ARGS
    diff = {k: [c0.get(k, "<missing>"), a.get(k, "<missing>")] for k in sorted(keys) if c0.get(k) != a.get(k)}
    return {"check": "args", "c0": c0_log, "a": a_log, "excluded": sorted(EXCLUDE_ARGS), "equal": not diff,
            "diff": diff}


def _norm(p):
    return open(p, "rb").read().replace(b"\r\n", b"\n")


def cmd_code(old, new):
    res = {}
    for f in TRAIN_FILES + OPTION_FILES:
        po, pn = os.path.join(old, f), os.path.join(new, f)
        if not (os.path.exists(po) and os.path.exists(pn)):
            res[f] = "missing"
            continue
        res[f] = "equal" if _norm(po) == _norm(pn) else "different"
    core_equal = all(res[f] == "equal" for f in TRAIN_FILES)
    return {"check": "code", "old": old, "new": new, "files": res, "train_files_equal": core_equal,
            "option_files": {f: res[f] for f in OPTION_FILES}}


def cmd_pred(a_path, b_path, ignore=()):
    ign = {"utc"} | set(ignore)

    def load(p):
        return [{k: v for k, v in json.loads(x).items() if k not in ign} for x in open(p)]
    ra, rb = load(a_path), load(b_path)
    diff = [i for i, (x, y) in enumerate(zip(ra, rb)) if x != y]
    out = {"check": "pred", "a": a_path, "b": b_path, "n_a": len(ra), "n_b": len(rb),
           "items": sum(r.get("event") == "item" for r in ra), "ignored": sorted(ign),
           "identical": len(ra) == len(rb) and not diff, "n_diff": len(diff)}
    if diff:
        ia = [r for r in ra if r.get("event") == "item"]
        ib = [r for r in rb if r.get("event") == "item"]
        same_key = all(x["key"] == y["key"] and x["question"] == y["question"] for x, y in zip(ia, ib))
        agree = sum(x.get("pred") == y.get("pred") for x, y in zip(ia, ib))
        dlp = max((abs(x["lp"][k] - y["lp"][k]) for x, y in zip(ia, ib) for k in x.get("lp", {}) if k in y.get("lp", {})),
                  default=None)
        out.update(same_item_order=same_key, argmax_agree=agree, argmax_agree_frac=agree / max(len(ia), 1),
                   max_abs_dlogprob=dlp, first_diff=[ra[diff[0]], rb[diff[0]]])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["args", "code", "pred"])
    ap.add_argument("x")
    ap.add_argument("y")
    ap.add_argument("--ignore", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if a.mode == "args":
        r = cmd_args(a.x, a.y)
    elif a.mode == "code":
        r = cmd_code(a.x, a.y)
    else:
        r = cmd_pred(a.x, a.y, [k for k in a.ignore.split(",") if k])
    s = json.dumps(r, indent=1)
    if a.out:
        open(a.out, "w").write(s)
    print(s[:6000])


if __name__ == "__main__":
    main()
