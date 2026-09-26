"""Build the E-STRIP8 arm files from the E-PT nd-xyz rows (harvest.teach_strip8.dataset.build) and print the counts.
usage: python build.py <E-PT data dir> <out dir>
  train_s-min, train_s-drop (seed 0), dev_s-min, ood_h_s-min, ood_h_s-stale (table 0.850 written by hand)"""
import json
import os
import sys

from harvest.teach_strip8 import dataset as D

src, out = sys.argv[1], sys.argv[2]
res = {}
for split, arm in (("train", "s-min"), ("train", "s-drop"), ("dev", "s-min"), ("ood_h", "s-min"),
                   ("ood_h", "s-stale")):
    res[f"{split}_{arm}"] = D.build(os.path.join(src, f"{split}_nd-xyz.jsonl"), out, split, arm, seed=0)
print(json.dumps(res, indent=1))
