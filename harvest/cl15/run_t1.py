"""E-CL15 T1 (docs/stage3/prereg_cl15.md): the E-M35CL runner (harvest.teach_pt.run_closed_l8s, unchanged) on L8S
held-out episodes, with the visual environment switched to the held-out ("ood") split of every appearance library
the L8S renders draw from: iTHOR room backgrounds (fx.room_split, 20 % by name hash), Poly Haven materials and
indoor HDRIs (materials.split_of, 20 % by id hash). L8S training renders only ever drew the "train" split
(run_collect: rooms "train" unless split ood_s, materials.pick default "train", hdr_paths(cat, "train")).
Scene geometry, objects, task and seed stay the L8S episode's. Same arguments as run_closed_l8s.
The patched draws are logged to <out>/env_used.jsonl (one line per process) for the overlap check."""
from __future__ import annotations

import json
import os
import sys

USED = {"rooms": set(), "hdr": set(), "materials": set()}


def patch(log_path: str | None = None) -> None:
    from ..sim.assets_x import materials as M
    from ..teach_l8d import fx
    rooms0, pick0, hdr0 = fx.rooms_of, M.pick, M.hdr_paths

    def rooms_ood(directory, split):
        r = rooms0(directory, "ood")
        USED["rooms"].update(r)
        return r

    def pick_ood(cat, role, seed, split="train"):
        rec = pick0(cat, role, seed, "ood")
        USED["materials"].add(rec.get("id") or rec.get("name") or str(rec.get("files", {}).get("diff")))
        return rec

    def hdr_ood(cat, split="train", root=M.ROOT):
        h = hdr0(cat, "ood", root)
        USED["hdr"].update(os.path.basename(p) for p in h)
        return h
    fx.rooms_of, M.pick, M.hdr_paths = rooms_ood, pick_ood, hdr_ood
    if log_path:
        import atexit

        def dump():
            with open(log_path, "a") as f:
                f.write(json.dumps({k: sorted(v) for k, v in USED.items()} | {"pid": os.getpid()}) + "\n")
        atexit.register(dump)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    out = argv[argv.index("--out") + 1]
    os.makedirs(out, exist_ok=True)
    patch(None)
    from ..teach_pt import run_closed_l8s as R
    _exit = os._exit

    def exit_dump(code):  # run_closed_l8s ends with os._exit (atexit would not run)
        with open(os.path.join(out, "env_used.jsonl"), "a") as f:
            f.write(json.dumps({k: sorted(v) for k, v in USED.items()} | {"pid": os.getpid()}) + "\n")
        _exit(code)
    os._exit = exit_dump
    R.main(argv)


if __name__ == "__main__":
    main()
