"""AgiBot checks requested before the full conversion (user, 2026-09-28):
  count   : kept episodes (chain_state.json) and all selected-task episodes (task_info) inside the two range tars the
            old chain would have skipped, and the episodes the FIXED stage_range would look for in them (dry run).
  side T  : for T distinct tasks, one kept episode each inside proprio_stats/648533-713949, extract its proprio +
            head camera parameters (tars downloaded / verified / deleted as in the chain; disk rules apply).
usage (pod): python -m xemb.agb_side count | python -m xemb.agb_side side 5"""
from __future__ import annotations

import json
import os
import sys

from . import agb_chain as C

PRO, PAR = "proprio_stats/648533-713949.tar", "parameters/683867-692833.tar"


def count():
    st = C.load_state()
    kept = C._need(st)
    sel = json.load(open(os.path.join(C.ROOT, "selection.json")))["tasks"]
    all_eps = {}
    for t in sel:
        for e in json.load(open(os.path.join(C.ROOT, "meta", "task_info", f"task_{t}.json"))):
            all_eps[int(e["episode_id"])] = t
    out = {}
    for tar in (PRO, PAR):
        a, b = C.rng(tar)
        kind = "proprio" if tar == PRO else "params"
        found = set(st.get(f"found_{kind}", [])) or {int(d) for _, ds, _ in os.walk(os.path.join(C.KEEP, kind))
                                                     for d in ds if d.isdigit() and int(d) > 100000}
        seen = set(st.get(f"seen_{kind}", {}).get(tar, []))
        k_in = [e for e in kept if a <= e <= b]
        out[tar] = {"selected_episodes_in_range": sum(a <= e <= b for e in all_eps),
                    "kept_episodes_in_range_so_far": len(k_in),
                    "old_chain_would_process": 0 if tar in st.get("done", []) else len(k_in),
                    "fixed_chain_will_look_for": len([e for e in k_in if e not in found and e not in seen]),
                    "already_found": len([e for e in k_in if e in found])}
    print(json.dumps(out, indent=1))
    json.dump(out, open(os.path.join(C.ROOT, "skipcheck.json"), "w"), indent=1)


def side(n):
    st = C.load_state()
    a, b = C.rng(PRO)
    pick = {}
    for e, t in sorted(C._need(st).items()):
        if a <= e <= b and t != "327" and t not in pick.values():
            pick[e] = t
        if len(pick) >= n - 1:
            break
    pick[685076] = "327"
    eps = set(pick)
    sizes = dict(C.listing("proprio_stats"))
    local = C.fetch(PRO, sizes[PRO])
    got = C.extract(local, lambda nm: C.want_proprio(nm, eps), os.path.join(C.KEEP, "proprio"))
    C.AF.release_tar(local, verified=True)
    psz = dict(C.listing("parameters"))
    for tar in sorted(psz):
        pa, pb = C.rng(tar)
        cs = {e for e in eps if pa <= e <= pb}
        if not cs:
            continue
        loc = C.fetch(tar, psz[tar])
        C.extract(loc, lambda nm: C.want_params(nm, cs), os.path.join(C.KEEP, "params"))
        C.AF.release_tar(loc, verified=True)
    json.dump({str(k): v for k, v in pick.items()}, open(os.path.join(C.ROOT, "tcp_check_eps.json"), "w"))
    print("side episodes", pick, "proprio files", len(got))


if __name__ == "__main__":
    count() if sys.argv[1] == "count" else side(int(sys.argv[2]))
