"""Split a frozen L8-D bundle manifest into K parts (same schema, episodes dealt round robin) so tools/teach_l8d/build.py
can build one training format in K parallel processes; concat.py joins the parts. usage:
python split_manifest.py <bundle.json> <out dir> <K>   -> <out dir>/part<k>.json"""
import json
import os
import sys

src, out, k = sys.argv[1], sys.argv[2], int(sys.argv[3])
b = json.load(open(src))
os.makedirs(out, exist_ok=True)
for i in range(k):
    json.dump(dict(b, name=f"{b['name']}_part{i}", episodes=b["episodes"][i::k]), open(os.path.join(out, f"part{i}.json"), "w"))
print(json.dumps({"episodes": len(b["episodes"]), "parts": k}))
