"""Compare two point files on shared keys (batching check): same parse, point distance px."""
import json
import math
import sys

a = {json.loads(x)["key"]: json.loads(x) for x in open(sys.argv[1])}
b = {json.loads(x)["key"]: json.loads(x) for x in open(sys.argv[2])}
ks = sorted(set(a) & set(b))
same_text = sum(a[k]["text"] == b[k]["text"] for k in ks)
d = [math.dist(a[k]["point"], b[k]["point"]) for k in ks if a[k]["point"] and b[k]["point"]]
none = [(a[k]["point"] is None, b[k]["point"] is None) for k in ks]
print(json.dumps({"shared": len(ks), "same_text": same_text, "both_points": len(d),
                  "max_px": round(max(d), 2) if d else None, "none_pairs": none.count((True, True)),
                  "none_mismatch": sum(x != y for x, y in none), "examples": [a[k]["text"] for k in ks[:3]]}))
