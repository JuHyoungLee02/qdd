"""Which planned episodes have no meta.json / skipped.json yet. usage: python missing.py <plan.json> <collect root>
Prints the missing (split, variant, table height, lift / furniture, task, seed) rows."""
import glob
import json
import os
import sys

plan = json.load(open(sys.argv[1]))
root = sys.argv[2]
done = set()
for p in glob.glob(os.path.join(root, "*", "*", "*", "meta.json")) + \
        glob.glob(os.path.join(root, "*", "*", "*", "skipped.json")):
    ep = os.path.dirname(p)
    done.add((ep.split(os.sep)[-3], os.path.basename(ep)))
miss = [e for e in plan if (e["split"], f"{e['task']}_s{e['seed']}") not in done]
for e in miss:
    print(e["split"], e["variant"], e["table_z"], e.get("lift"), e.get("furniture"), e["task"], e["seed"])
print("missing", len(miss), "of", len(plan))
