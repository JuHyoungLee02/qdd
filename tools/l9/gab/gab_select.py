"""L9v2-general integrated A/B (all general elements ON vs current), row selection. Read-only on the sources.
Per robot: N single-arm train rows from that robot's pilot plan, round-robin over task families (sorted), then over
definitions inside a family, arms alternating left/right for two-armed robots; order inside a group = a fixed hash of
the seed (deterministic, no RNG state). One row per job. Both arms (A, B) get the SAME rows (same seeds).
usage: python gab_select.py <ab dir> <n per robot> robot=plan.json [robot=plan.json ...]
writes <ab dir>/plan_gab.json, <ab dir>/q.txt ("<arm> <robot> <plan> <job>", rows interleaved robot by robot, A then
B for each row), <ab dir>/rows.tsv (job robot def family arm seed)."""
import hashlib
import json
import os
import sys
from collections import defaultdict

SKIP = ("bimanual", "handover", "articulated", "drawer", "door", "art_")
TWO_ARMED = ("ffw_sg2", "r1pro", "g1")


def h(seed) -> str:
    return hashlib.sha1(f"gab-{seed}".encode()).hexdigest()


def pick(rows, robot, n):
    rows = [r for r in rows if r.get("robot") == robot and r.get("split", "train") == "train"
            and not any(s in str(r.get("task_family", "")) + str(r.get("def", "")) for s in SKIP)]
    fam = defaultdict(lambda: defaultdict(list))
    for r in rows:
        fam[str(r.get("task_family"))][str(r.get("def"))].append(r)
    for f in fam.values():
        for d in f.values():
            d.sort(key=lambda r: h(r["seed"]))
    out, want_arm, k = [], 0, 0
    used = set()
    while len(out) < n and any(any(d for d in f.values()) for f in fam.values()):
        for fname in sorted(fam):
            if len(out) >= n:
                break
            defs = [d for d in sorted(fam[fname]) if fam[fname][d]]
            if not defs:
                continue
            dname = defs[k % len(defs)]
            lst = fam[fname][dname]
            arm = ("left", "right")[want_arm % 2] if robot in TWO_ARMED else None
            j = next((i for i, r in enumerate(lst) if arm is None or r.get("arm") == arm), 0)
            r = lst.pop(j)
            if r["seed"] in used:
                continue
            used.add(r["seed"])
            out.append(r)
            want_arm += 1
        k += 1
    return out


def main():
    ab, n = sys.argv[1], int(sys.argv[2])
    os.makedirs(ab, exist_ok=True)
    plan, per = [], {}
    for spec in sys.argv[3:]:
        robot, src = spec.split("=", 1)
        sel = pick(json.load(open(src)), robot, n)
        per[robot] = []
        for i, r in enumerate(sel):
            r = dict(r, job=f"gab_{robot}_{i:03d}")
            r.pop("pilot", None)
            plan.append(r)
            per[robot].append(r)
    p = os.path.join(ab, "plan_gab.json")
    json.dump(plan, open(p, "w"))
    with open(os.path.join(ab, "q.txt"), "w") as q, open(os.path.join(ab, "rows.tsv"), "w") as t:
        for i in range(max(len(v) for v in per.values())):
            for robot in per:
                if i < len(per[robot]):
                    r = per[robot][i]
                    for arm in ("A", "B"):
                        q.write(f"{arm} {robot} {p} {r['job']}\n")
                    t.write(f"{r['job']}\t{robot}\t{r.get('def')}\t{r.get('task_family')}\t{r.get('arm')}\t{r['seed']}\n")
    for robot, v in per.items():
        print(robot, len(v), "families", len({r.get("task_family") for r in v}), "defs", len({r.get("def") for r in v}),
              "left", sum(r.get("arm") == "left" for r in v))


if __name__ == "__main__":
    main()
