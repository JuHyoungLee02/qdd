"""Build the E-TEACH-L8 JSONL files from collected episodes (harvest.teach_l8.dataset.build) and print the counts.
usage: python build.py <collect root> <out dir>
  <collect root>/train -> <out dir>/train.jsonl (repeats + aux)
  <collect root>/dev   -> <out dir>/dev.jsonl (no repeats; aux kept for the perception check)"""
import json
import os
import sys

from harvest.teach_l8 import dataset as DS

root, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
res = {}
if os.path.isdir(os.path.join(root, "train")):
    res["train"] = DS.build(os.path.join(root, "train"), os.path.join(out, "train.jsonl"), "train", seed=0)
if os.path.isdir(os.path.join(root, "dev")):
    res["dev"] = DS.build(os.path.join(root, "dev"), os.path.join(out, "dev.jsonl"), "dev", seed=1, repeats=False)
print(json.dumps(res, indent=1))
