"""Gate plan for the new tasks (prereg_l8x_tasks 3): the frozen gate picks (docs/stage3/l8x_tasks_lists.json) as a
run_collect --plan list (split gate, standard, objset x, table 0.85).
usage: python tools/l8x_assets/gate_plan.py LISTS.json KIND(stack|push) OUT.json"""
from __future__ import annotations

import json
import sys


def main(argv=None):
    a = argv or sys.argv[1:]
    lists = json.load(open(a[0]))
    pre = {"stack": "st__", "push": "pu__"}[a[1]]
    rows = [{"seed": int(s), "task": t, "split": "gate", "variant": "standard", "objset": "x", "table_z": 0.85}
            for s, t in sorted(lists["gate"].items()) if t and t.startswith(pre)]
    json.dump(rows, open(a[2], "w"), indent=1)
    print(len(rows), "episodes ->", a[2])


if __name__ == "__main__":
    main()
