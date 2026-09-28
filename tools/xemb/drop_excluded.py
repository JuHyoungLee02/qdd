"""Write IN_train.jsonl = IN.jsonl without rows marked exclude=True (for tools that do not read the flag, e.g. the
E-DIST8 mix_pack). The source file is left as it is. usage: python -m xemb.drop_excluded FILE.jsonl [...]"""
import json
import sys

for p in sys.argv[1:]:
    rows = [json.loads(x) for x in open(p, encoding="utf-8")]
    keep = [r for r in rows if not r.get("exclude")]
    out = p[:-6] + "_train.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(r) + "\n" for r in keep)
    print(out, len(keep), "of", len(rows))
