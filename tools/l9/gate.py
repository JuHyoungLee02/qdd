"""L9 gate / audit report over a collect root (pure; pod or laptop).
usage: python tools/l9/gate.py <collect root> <out.json> [--min-yield 0.5] [--per 10]
Per task definition: episodes, successes, yield; per arm and per environment family; arm joint step (meta
max_dq_rad <= 0.04 on every episode); label parser (every labels row's pt_answer / answer parses with the runtime
parser astra_solo.pt_schema.validate, allow_eef for the behaviour answers); combination hashes unique; skipped
episodes by reason. `pass` = the definitions with >= per episodes and yield >= min-yield."""
import glob
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

ARM_DQ_MAX = 0.04


def scan(root: str) -> dict:
    from harvest.astra_solo.pt_schema import validate
    eps, skips = [], Counter()
    parser = Counter()
    for m in glob.glob(os.path.join(root, "**", "meta.json"), recursive=True):
        d = os.path.dirname(m)
        meta = json.load(open(m))
        if meta.get("gen") != "l9":
            continue
        bad = 0
        n = 0
        lab = os.path.join(d, "labels.jsonl")
        if os.path.exists(lab):
            for line in open(lab):
                r = json.loads(line)
                for key in ("pt_answer", "answer"):
                    a = r.get(key)
                    if a is None:
                        continue
                    n += 1
                    ok, err = validate(a, allow_eef=True)
                    if err:
                        bad += 1
        parser["rows"] += n
        parser["bad"] += bad
        res = json.load(open(os.path.join(d, "result.json"))) if os.path.exists(os.path.join(d, "result.json")) else {}
        eps.append({"grasp_lift": res.get("grasp_lift"), "ever_hold": res.get("ever_hold"), "fail_stage": res.get("fail_stage"),
                    "movers": [k for k, o in (meta.get("objects") or {}).items()], "dir": d, "task_id": meta.get("task_id"), "family": meta.get("env_family"),
                    "task_family": meta.get("task_family"), "arm": meta.get("arm"), "success": bool(meta.get("success")),
                    "max_dq": meta.get("max_dq_rad"), "combo": meta.get("combo_hash"), "end": meta.get("end_reason"),
                    "light": meta.get("light_family"), "layout": meta.get("layout"), "wall_s": meta.get("wall_s"),
                    "parser_bad": bad})
    for s in glob.glob(os.path.join(root, "**", "skipped.json"), recursive=True):
        why = json.load(open(s)).get("reason", "")
        skips[why.split(":")[0][:60]] += 1
    return {"episodes": eps, "skips": dict(skips), "parser": dict(parser)}


def report(sc: dict, per: int, min_yield: float) -> dict:
    eps = sc["episodes"]
    by = defaultdict(list)
    for e in eps:
        by[e["task_id"]].append(e)
    defs = {}
    for k, v in sorted(by.items()):
        s = sum(e["success"] for e in v)
        defs[k] = {"n": len(v), "success": s, "yield": round(s / len(v), 3),
                   "arms": dict(Counter(e["arm"] for e in v)), "ends": dict(Counter(e["end"] for e in v))}
    ok = sorted(k for k, v in defs.items() if v["n"] >= per and v["yield"] >= min_yield)
    jumps = [e["dir"] for e in eps if e["max_dq"] is not None and e["max_dq"] > ARM_DQ_MAX]
    combos = Counter(e["combo"] for e in eps)
    fam = defaultdict(lambda: [0, 0])
    for e in eps:
        fam[e["family"]][0] += 1
        fam[e["family"]][1] += e["success"]
    arm = Counter(e["arm"] for e in eps if e["success"])
    arm_n = Counter(e["arm"] for e in eps)
    fails = Counter(e["fail_stage"] for e in eps if not e["success"])
    wall = sorted(e["wall_s"] for e in eps if e["wall_s"])
    return {"n_episodes": len(eps), "n_success": sum(e["success"] for e in eps), "definitions": defs,
            "pass": ok, "n_pass": len(ok), "fail": sorted(set(defs) - set(ok)),
            "arm_jumps": len(jumps), "arm_jump_dirs": jumps[:20], "max_dq_max": max((e["max_dq"] or 0) for e in eps) if eps else None,
            "combo_duplicates": sum(c - 1 for c in combos.values() if c > 1),
            "families": {k: {"n": v[0], "success": v[1]} for k, v in sorted(fam.items())},
            "success_by_arm": dict(arm), "episodes_by_arm": dict(arm_n), "fail_stages": dict(fails), "lights": dict(Counter(e["light"] for e in eps)),
            "parser": sc["parser"], "skips": sc["skips"],
            "wall_s_median": wall[len(wall) // 2] if wall else None}


def main():
    root, out = sys.argv[1], sys.argv[2]
    per = int(sys.argv[sys.argv.index("--per") + 1]) if "--per" in sys.argv else 10
    my = float(sys.argv[sys.argv.index("--min-yield") + 1]) if "--min-yield" in sys.argv else 0.5
    r = report(scan(root), per, my)
    json.dump(r, open(out, "w"), indent=1)
    print(json.dumps({k: r[k] for k in ("n_episodes", "n_success", "n_pass", "arm_jumps", "max_dq_max",
                                         "combo_duplicates", "parser", "success_by_arm", "wall_s_median")}))


if __name__ == "__main__":
    main()
