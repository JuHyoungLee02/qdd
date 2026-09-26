"""Build E-DIST8 minimal-request rows (harvest.teach_pt.min_format.build) and print the counts.
usage: python build_min.py <collect root> <out dir> <split> <track r-min|d-min|h-min> <mode train|clean|noisy|off>
       [<episode dir>]   (default <collect root>/<split>; L8-X sets: split x_dev / x_ood_h / x_ood_d / ... with the
                           episode dir given explicitly, e.g. /data/harvest/out/teach_l8d/collect/ood_h)"""
import json
import os
import sys

from harvest.teach_pt import min_format as MF

root, out, split, track, mode = sys.argv[1:6]
src = sys.argv[6] if len(sys.argv) > 6 else os.path.join(root, split)
os.makedirs(out, exist_ok=True)
c = MF.build(src, out, split, track, "clean" if mode == "train" else mode)
print(json.dumps({"split": split, "track": track, "mode": mode, "src": src, **c}))
