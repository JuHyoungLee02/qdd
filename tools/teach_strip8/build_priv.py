"""E-PRIV8 data: train_m1 / train_m3 from the L8D b1 nd-xyz rows, M1-keep evaluation rows (estimate request on every
control row) for L8-X dev_x / ood_h and the old DEV / OOD-H (E-PT nd-xyz rows).
usage: python build_priv.py <out dir>"""
import json
import os
import sys

from harvest.teach_strip8 import priv as P

out = sys.argv[1]
b1 = "/data/harvest/out/teach_l8d/data/b1/train_nd-xyz.jsonl"
ev = "/data/harvest/out/teach_l8d/data/eval"
pt = "/data/harvest/out/teach_pt/data"
res = {"train_m1": P.build(b1, out, "train", "m1", seed=0), "train_m3": P.build(b1, out, "train", "m3", seed=0)}
for name, src in (("dev_x", f"{ev}/dev_x_nd-xyz.jsonl"), ("ood_hx", f"{ev}/ood_h_nd-xyz.jsonl"),
                  ("dev", f"{pt}/dev_nd-xyz.jsonl"), ("ood_h", f"{pt}/ood_h_nd-xyz.jsonl")):
    c = P.build(src, os.path.join(out, "ev_" + name), "dev", "m1", seed=1)
    res[name] = c
print("BUILD_PRIV " + json.dumps(res))
