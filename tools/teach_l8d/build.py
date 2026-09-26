"""Build L8-D JSONL files (harvest.teach_l8d.dataset.build) and print the counts.
usage: python build.py <collect root> <out dir> <split> <format[,format...]|all> [--tags] [--both-tags]
  [--self-lift] [--depth-noise PRESET] [--manifest bundle.json]
  <collect root>/<split> -> <out dir>/<split>_<format>[_tags][_lift][_<preset>].jsonl (+ .counts.json);
  --manifest: only the episodes of a frozen bundle (tools/teach_l8d/freeze.py)."""
import json
import os
import sys

from harvest.teach_l8d import dataset as D

root, out, split, fmts = sys.argv[1:5]
fmts = D.FORMATS if fmts == "all" else tuple(fmts.split(","))
tag_modes = (False, True) if "--both-tags" in sys.argv else (("--tags" in sys.argv),)
noise = sys.argv[sys.argv.index("--depth-noise") + 1] if "--depth-noise" in sys.argv else None
man = json.load(open(sys.argv[sys.argv.index("--manifest") + 1]))["episodes"] if "--manifest" in sys.argv else None
res = {}
for f in fmts:
    for t in tag_modes:
        c = D.build(os.path.join(root, split), out, split, f, tags=t, self_lift="--self-lift" in sys.argv,
                    depth_noise=noise, manifest=man)
        res[f"{f}{'_tags' if t else ''}"] = {k: c[k] for k in ("episodes", "control_unique", "control_rows",
                                                                 "aux_rows", "total")}
print(json.dumps(res, indent=1))
