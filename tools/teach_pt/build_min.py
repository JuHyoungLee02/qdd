"""Build E-DIST8 minimal-request rows (harvest.teach_pt.min_format.build) and print the counts.
usage: python build_min.py <collect root> <out dir> <split> <track r-min|d-min|h-min> <mode train|clean|noisy|off>"""
import json
import os
import sys

from harvest.teach_pt import min_format as MF

root, out, split, track, mode = sys.argv[1:6]
os.makedirs(out, exist_ok=True)
c = MF.build(os.path.join(root, split), out, split, track, "clean" if mode == "train" else mode)
print(json.dumps({"split": split, "track": track, "mode": mode, **c}))
