"""boost2 DAgger collection summary: episodes, learner successes, learner answer share, truth fallbacks.
usage: python dagger_stats.py <collect root>"""
import glob
import json
import os
import sys

ms = [json.load(open(p)) for p in glob.glob(os.path.join(sys.argv[1], "train", "*", "*", "meta.json"))]
print(json.dumps({"episodes": len(ms), "success": sum(m["success"] for m in ms),
                  "calls_model": sum(m["n_model"] for m in ms), "calls_fallback": sum(m["n_fallback"] for m in ms),
                  "rows": sum(m["n_rows"] for m in ms), "labelled": sum(m["n_labelled"] for m in ms)}))
