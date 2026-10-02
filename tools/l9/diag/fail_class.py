"""L9 v2 diagnosis: classify failed episodes of collect roots by the judge's result.json + labels + v2 meta (pure).
usage: python tools/l9/diag/fail_class.py <collect root> [<root> ...] [--since EPOCH] [--all] [--robot NAME]
One line per failed episode: robot, task, seed, end reason, last truth step, result fail_stage / tipped / off_table /
collision / knocked, grasp_lift, ever_hold, number of closes, the target's z at the first and last call, the last
history note, and a class:
  DEAD_START   no grasp was ever executed (choice / fallback / transit failures)
  NO_HOLD      closes happened but the object was never lifted (EMPTY / WIDE / slips at the lift)
  DROP_CARRY   held and lost before the place
  TIPPED_PLACE released at the place and the judge says tipped
  PLACE_MISS   released, upright, but not on the spot (judge false)
  CALL_CAP     ran into the call cap while holding / re-planning
  OTHER"""
import glob
import json
import os
import re
import sys
from collections import Counter


def hist(ep):
    calls = sorted(glob.glob(os.path.join(ep, "calls", "c*")))
    if not calls:
        return []
    t = open(os.path.join(calls[-1], "prompt.txt"), encoding="utf-8").read()
    return [x for x in t.split("\n") if re.match(r"^\d+: ", x)]


def labels(ep):
    p = os.path.join(ep, "labels.jsonl")
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []


def classify(meta, res, labs, h):
    g = meta.get("grasp_v2") or {}
    picks = g.get("picks", [])
    n_close = int(res.get("n_close", 0) or 0)
    last = h[-1] if h else ""
    if meta.get("end_reason") == "stage_cap_calls":
        return "CALL_CAP"
    if n_close == 0:
        return "DEAD_START"
    if not res.get("grasp_lift") and not res.get("ever_hold"):
        return "NO_HOLD"
    steps = [l.get("step") for l in labs]
    released = any(s in ("retreat",) for s in steps) or "gripper open" in last and "reached" in last
    if res.get("tipped"):
        return "TIPPED_PLACE" if released or res.get("fail_stage") == "place" else "TIPPED_OTHER"
    if res.get("fail_stage") == "place" or released:
        return "PLACE_MISS"
    if res.get("ever_hold"):
        return "DROP_CARRY" if "pad gap 0.0" in " ".join(h[-3:]) else "HOLD_OTHER"
    return "OTHER"


def main():
    a = sys.argv[1:]
    since = float(a[a.index("--since") + 1]) if "--since" in a else 0.0
    robot = a[a.index("--robot") + 1] if "--robot" in a else None
    roots = [x for x in a if os.path.isdir(x)]
    cnt, tot = Counter(), Counter()
    for root in roots:
        for m in sorted(glob.glob(os.path.join(root, "**", "meta.json"), recursive=True)):
            if os.path.getmtime(m) < since:
                continue
            meta = json.load(open(m))
            g = meta.get("grasp_v2")
            if g is None:
                continue
            rob = g.get("robot_profile")
            if robot and rob != robot:
                continue
            ep = os.path.dirname(m)
            ok = bool(meta.get("success")) and (meta.get("max_dq_rad") or 0) <= 0.04
            tot[(rob, meta.get("style"))] += 1
            if ok and "--all" not in a:
                continue
            rp = os.path.join(ep, "result.json")
            res = json.load(open(rp)) if os.path.exists(rp) else {}
            labs, h = labels(ep), hist(ep)
            c = "OK" if ok else classify(meta, res, labs, h)
            cnt[(rob, c, meta.get("style"))] += 1
            z0 = labs[0]["gt"]["tgt"][2] if labs and labs[0].get("gt") else None
            z1 = labs[-1]["gt"]["tgt"][2] if labs and labs[-1].get("gt") else None
            print(f"{c:13s} {rob:11s} {os.path.relpath(ep, root)[:60]:60s} end={meta.get('end_reason'):15s} "
                  f"step={labs[-1].get('step') if labs else None} stage={res.get('fail_stage')} tip={res.get('tipped')} "
                  f"coll={res.get('collision')} knock={res.get('knocked')} lift={res.get('grasp_lift')} "
                  f"hold={res.get('ever_hold')} nclose={res.get('n_close')} z {z0}->{z1} | {h[-1][:150] if h else ''}")
    print("\nCOUNTS", sorted(cnt.items()), "TOTAL", dict(tot))


if __name__ == "__main__":
    main()
