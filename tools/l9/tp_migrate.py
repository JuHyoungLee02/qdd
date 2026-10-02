"""Move the third-person (external camera) files of finished L9 v2 episodes out of the ego call dirs into the
third-person tree (harvest.l9.tp9; moved, nothing deleted) and write <run>/third_person/index.jsonl.
usage: python tools/l9/tp_migrate.py <collect root>... [--dry-run]"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from harvest.l9 import tp9  # noqa: E402


def main():
    dry = "--dry-run" in sys.argv
    for root in [x for x in sys.argv[1:] if not x.startswith("--")]:
        res = tp9.migrate(root, dry_run=dry)
        idx = tp9.index(root)
        if not dry:
            p = os.path.join(os.path.dirname(os.path.normpath(root)), tp9.TP_NAME, "index.jsonl")
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as f:
                for e in idx:
                    f.write(json.dumps(e) + "\n")
        print(json.dumps(dict(res, root=root, index_entries=len(idx), legacy_left=sum(e["legacy"] for e in idx),
                              dry_run=dry)))


if __name__ == "__main__":
    main()
