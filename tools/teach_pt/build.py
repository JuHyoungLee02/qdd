"""Build the E-PT per-arm JSONL files from collected episodes (harvest.teach_pt.dataset.build) and print the counts.
usage: python build.py <collect root> <out dir> <split> [--no-repeats] [--no-aux] [--arms xyz,pt,...]
  <collect root>/<split> -> <out dir>/<split>_<arm>.jsonl"""
import json
import os
import sys

from harvest.teach_pt import dataset as DS

root, out, split = sys.argv[1], sys.argv[2], sys.argv[3]
flags = sys.argv[4:]
arms = DS.ARMS
for f in flags:
    if f.startswith("--arms="):
        arms = tuple(f.split("=", 1)[1].split(","))
res = DS.build(os.path.join(root, split), out, split, arms=arms, seed=0 if split == "train" else 1,
               repeats="--no-repeats" not in flags, aux="--no-aux" not in flags)
print(json.dumps(res, indent=1))
