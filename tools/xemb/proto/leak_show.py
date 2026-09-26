"""Show replies flagged by the frame-leak checker. usage: leak_show.py REPLIES_JSONL"""
import json, sys
sys.path.insert(0, "/data/harvest/out/xemb_proto/code")
from xemb import eval_open8 as E
from xemb import fmt as F

for line in open(sys.argv[1]):
    r = json.loads(line)
    fl = [f for f in F.leak_flags(r.get("text") or "", E.OUR_BOX) if f != "not_json"]
    if fl:
        print(r["id"], fl, (r.get("text") or "")[-260:])
