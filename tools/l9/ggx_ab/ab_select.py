"""GGX A/B: pick 24 existing single-arm production episodes per robot (one per definition, newest first), rebuild
their plan rows (same seed) into A/B plans, list their objects. usage: ab_select.py <out dir>"""
import glob, json, os, sys
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
SKIP = ("bimanual", "handover", "articulated", "drawer", "door", "art_")
ids = set()
for tag, rdir, robot in (("A", "/data/harvest/l9v2/pilot1", "ffw_sg2"), ("F", "/data/harvest/l9v2/pilotF", "franka_mast")):
    rows = {}
    for pf in glob.glob(rdir + "/plan_*.json"):
        try:
            for r in json.load(open(pf)):
                if (r.get("robot") or "ffw_sg2") == robot and r.get("split", "train") == "train":
                    rows[int(r["seed"])] = r
        except Exception:
            pass
    eps = []
    for m in glob.glob(rdir + "/collect/train/*/*/meta.json"):
        try:
            d = json.load(open(m))
        except Exception:
            continue
        tf = str(d.get("task_family", ""))
        if any(s in tf for s in SKIP) or int(d["seed"]) not in rows:
            continue
        eps.append((os.path.getmtime(m), d))
    eps.sort(key=lambda x: -x[0])
    seen, pick = set(), []
    for _, d in eps:
        if d["task_id"] in seen:
            continue
        seen.add(d["task_id"]); pick.append(d)
        if len(pick) >= 24:
            break
    plan = []
    for arm in ("left", "right"):
        sub = [d for d in pick if rows[int(d["seed"])]["arm"] == arm]
        for i, d in enumerate(sub):
            r = dict(rows[int(d["seed"])]); r["job"] = f"ab{tag}_{arm[0]}{i // 4}"; r.pop("pilot", None)
            plan.append(r); ids.update(d["objects"].keys())
    json.dump(plan, open(f"{out}/plan_ab{tag}.json", "w"))
    jobs = sorted({r["job"] for r in plan})
    open(f"{out}/jobs_{tag}.txt", "w").write("".join(f"--plan {out}/plan_ab{tag}.json --job {j} --v2 --p 0.15\n" for j in jobs))
    print(tag, "episodes", len(plan), "jobs", len(jobs), "defs", sorted({d['task_id'] for d in pick})[:30],
          "fams", sorted({d['task_family'] for d in pick}))
open(f"{out}/ids.txt", "w").write("\n".join(sorted(ids)) + "\n")
print("objects", len(ids))
