"""E-TP1 smoke: 8 training and 4 hold-out episodes that have third-person renders (<run>/third_person/...)."""
import json
import os
import sys
d = json.load(open(sys.argv[1]))
has = lambda e: os.path.isdir(e["dir"].replace("/collect/", "/third_person/"))  # noqa: E731
json.dump({"train": [e for e in d["train"] if has(e)][:8], "eval": [e for e in d["eval"] if has(e)][:4]}, open(sys.argv[2], "w"))
