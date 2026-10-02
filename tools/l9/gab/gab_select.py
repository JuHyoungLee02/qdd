"""L9v2-general integrated A/B (all general elements ON vs current), row selection. Read-only on the sources.
Per robot: N single-arm train rows from that robot's pilot plan, round-robin over task families (sorted), then over
definitions inside a family (arms as the plan drew them, no forced left/right balance); order inside a group = a fixed hash of
the seed (deterministic, no RNG state). GAB_ROWS_PER_JOB (default 5) rows of one robot and arm per job. Both arms (A, B) get the SAME rows (same seeds).
usage: python gab_select.py <ab dir> <n per robot> robot=<plan glob>[@<run dir glob>] ...
  @<run dir glob>: keep only rows whose seed was RENDERED there (a meta.json under <run dir>/collect): production
  prefilters rows that do not fit their scene (30-70 % skip in the raw pilot plans), so the A/B uses rows that fit.
writes <ab dir>/plan_gab.json, <ab dir>/q.txt ("<arm> <robot> <plan> <job>", rows interleaved robot by robot, A then
B for each row), <ab dir>/rows.tsv (job robot def family arm seed)."""
import glob
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
            arm = None  # no forced left/right balance (user 10-03: L/R is balanced at build time)
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
    k = int(os.environ.get("GAB_ROWS_PER_JOB", "5"))  # rows per Isaac process (one boot; same robot and arm)
    os.makedirs(ab, exist_ok=True)
    plan, per, jobs = [], {}, {}
    for spec in sys.argv[3:]:
        robot, src = spec.split("=", 1)
        pg, _, rg = src.partition("@")
        rows, seen = [], set()
        for pf in sorted(glob.glob(pg)):
            for r in json.load(open(pf)):
                if r["seed"] not in seen:
                    seen.add(r["seed"])
                    rows.append(r)
        if rg:
            rendered = set()
            for rd in glob.glob(rg):
                for m in glob.glob(os.path.join(rd, "collect", "*", "*", "*", "meta.json")):
                    try:
                        rendered.add(int(json.load(open(m))["seed"]))
                    except (OSError, ValueError, KeyError):
                        pass
            rows = [r for r in rows if int(r["seed"]) in rendered]
        sel = pick(rows, robot, n)
        per[robot] = []
        cnt = defaultdict(int)
        for r in sel:
            side = r.get("arm") or "x"
            r = dict(r, job=f"gab_{robot}_{side[0]}{cnt[side] // k:02d}")
            cnt[side] += 1
            r.pop("pilot", None)
            plan.append(r)
            per[robot].append(r)
        jobs[robot] = sorted({r["job"] for r in per[robot]})
    p = os.path.join(ab, "plan_gab.json")
    json.dump(plan, open(p, "w"))
    with open(os.path.join(ab, "q.txt"), "w") as q, open(os.path.join(ab, "rows.tsv"), "w") as t:
        for i in range(max(len(v) for v in jobs.values())):
            for robot in jobs:
                if i < len(jobs[robot]):
                    for arm in ("A", "B"):
                        q.write(f"{arm} {robot} {p} {jobs[robot][i]}\n")
        for r in plan:
            t.write("\t".join(str(x) for x in (r["job"], r["robot"], r.get("def"), r.get("task_family"), r.get("arm"),
                                               r["seed"])) + "\n")
    for robot, v in per.items():
        print(robot, len(v), "families", len({r.get("task_family") for r in v}), "defs", len({r.get("def") for r in v}),
              "left", sum(r.get("arm") == "left" for r in v))


if __name__ == "__main__":
    main()
