"""Inspect T4-rig inputs: state names per RAW root, mask pixel counts and frames per episode by tag."""
import collections, json, sys
for raw in sys.argv[2:]:
    info = json.load(open(raw + "/meta/info.json"))
    print(raw.split("/")[-1], info["features"]["observation.state"]["names"])
idx = json.load(open(sys.argv[1]))
for tag in ("RB1", "RB3"):
    its = [i for i in idx if i["tag"] == tag]
    ok = [i for i in its if i["px"] >= 200]
    per = collections.Counter(i["ep"] for i in ok)
    print(tag, "frames", len(its), "mask>=200px", len(ok), "eps", len(per), "eps>=3", sum(v >= 3 for v in per.values()),
          "px median", sorted(i["px"] for i in its)[len(its) // 2] if its else None)
