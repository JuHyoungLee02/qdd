"""L9 v2 diagnosis: one line per episode (+ per pick) for a collect root (pure, pod or laptop).
usage: python tools/l9/diag/ep_table.py <collect root> [--since EPOCH] [--fail] [--hist N]
Per episode: task, seed, success, end reason, last history lines; per pick: object, family, w_contact, pre_open,
close outcome / final gap, lift outcome, fallback statuses, regrasp trace, valid stats, choice failures."""
import glob
import json
import os
import re
import sys


def hist(ep: str) -> list:
    calls = sorted(glob.glob(os.path.join(ep, "calls", "c*")))
    if not calls:
        return []
    t = open(os.path.join(calls[-1], "prompt.txt"), encoding="utf-8").read()
    return [x for x in t.split("\n") if re.match(r"^\d+: ", x)]


def main():
    root = sys.argv[1]
    since = float(sys.argv[sys.argv.index("--since") + 1]) if "--since" in sys.argv else 0.0
    nh = int(sys.argv[sys.argv.index("--hist") + 1]) if "--hist" in sys.argv else 3
    only_fail = "--fail" in sys.argv
    for m in sorted(glob.glob(os.path.join(root, "**", "meta.json"), recursive=True)):
        if os.path.getmtime(m) < since:
            continue
        meta = json.load(open(m))
        g = meta.get("grasp_v2")
        if g is None:
            continue
        ok = bool(meta.get("success"))
        if only_fail and ok:
            continue
        ep = os.path.dirname(m)
        print(f"== {os.path.relpath(ep, root)} ok={ok} end={meta.get('end_reason')} calls={meta.get('n_calls')} "
              f"dq={meta.get('max_dq_rad')} style={meta.get('style')}")
        for p in g.get("picks", []):
            tl = p.get("timeline", {})
            fb = [f"{x.get('family')}:{x.get('status')}" for x in tl.get("fallback_trace", [])]
            print(f"   pick obj={p.get('obj')} cat={p.get('category')!r} fam={p.get('family')} part={p.get('part')} "
                  f"w={p.get('w_contact', p.get('width_m'))} pre={p.get('pre_open_w', p.get('pre_open_m'))} "
                  f"pad={p.get('pad_drop_m')} close={tl.get('outcome_close')} gap={tl.get('final_gap')} "
                  f"lift={tl.get('outcome_lift')} slip={tl.get('slip_mm')} yaw={tl.get('place_yaw_delta', '-')} "
                  f"nvalid={p.get('n_valid')} vs={p.get('valid_stats')} fail={p.get('choice_fail')}")
            if fb:
                print(f"     fallback {fb}")
            for k in ("regrasp_trace", "carry_fallback", "line_moves", "limit_rejects", "close_off_pose"):
                if tl.get(k):
                    print(f"     {k} {tl[k]}")
        for h in hist(ep)[-nh:]:
            print("   |", h[:220])


if __name__ == "__main__":
    main()
