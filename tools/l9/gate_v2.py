"""L9 v2 gate report over collect roots (pure; spec §12.9 + §12.11 + §12.12).
usage: python tools/l9/gate_v2.py <out.json> <collect root>... [--min-n 10] [--robot ffw_sg2]
Per definition: n, success (success & max_dq_rad <= 0.04), yield. Grasp variety over every pick of every episode:
approach family share (top must be <= 50 %), part share, rot bins used (image and base), natural rank-0 share,
label rule steps, instructed share, fallback / line-move / re-grasp rates, close outcome mix, visible-point share,
tested-candidate share, pre-open vs width, per-robot / arm counts. Verdicts: per-definition yield >= 0.5 (n >= min-n),
per-family execution success >= 0.70, top <= 0.50, every family >= 0.05, rot bins image >= 8 of 12."""
import glob
import json
import os
import sys
from collections import Counter, defaultdict


def main():
    args = [a for a in sys.argv[1:]]
    opt = lambda k, d: type(d)(args[args.index(k) + 1]) if k in args else d  # noqa: E731
    min_n, robot = opt("--min-n", 10), opt("--robot", "")
    pos = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or not args[i - 1].startswith("--"))]
    out_path, roots = pos[0], pos[1:]
    per_def = defaultdict(lambda: [0, 0])
    fam_def = {}
    fam_ok = defaultdict(lambda: [0, 0])
    picks, fams, parts, rimg, rbase, rules, outc = [], Counter(), Counter(), Counter(), Counter(), Counter(), Counter()
    n_ep = n_ok = 0
    max_dq = 0.0
    arms, robots = Counter(), Counter()
    for root in roots:
        for m in glob.glob(os.path.join(root, "**", "meta.json"), recursive=True):
            meta = json.load(open(m))
            gv = meta.get("grasp_v2")
            if meta.get("gen") != "l9" or gv is None or (robot and meta.get("robot") != robot):
                continue
            n_ep += 1
            ok = bool(meta["success"]) and (meta.get("max_dq_rad") or 0) <= 0.04
            n_ok += ok
            max_dq = max(max_dq, float(meta.get("max_dq_rad") or 0))
            k = meta["task_id"]
            per_def[k][0] += 1
            per_def[k][1] += ok
            fam_def[k] = meta.get("task_family")
            fam_ok[meta.get("task_family")][0] += 1
            fam_ok[meta.get("task_family")][1] += ok
            arms[meta.get("arm")] += 1
            robots[meta.get("robot")] += 1
            for p in gv.get("picks", []):
                picks.append(p)
                fams[p.get("family")] += 1
                parts[p.get("part")] += 1
                if p.get("rot_bin_img") is not None:
                    rimg[p["rot_bin_img"]] += 1
                rbase[p.get("rot_bin_base")] += 1
                rules[(p.get("label_rule"), p.get("rule_step"))] += 1
                outc[(p.get("timeline") or {}).get("outcome_close")] += 1
    n_p = max(len(picks), 1)
    share = lambda c: {str(k): round(v / sum(c.values()), 3) for k, v in c.most_common()} if c else {}  # noqa: E731
    defs = {k: {"family": fam_def.get(k), "n": v[0], "ok": v[1], "yield": round(v[1] / v[0], 3)}
            for k, v in sorted(per_def.items())}
    rep = {
        "episodes": n_ep, "success": n_ok, "yield": round(n_ok / max(n_ep, 1), 3), "max_dq_rad": round(max_dq, 4),
        "defs_pass": sorted(k for k, v in defs.items() if v["n"] >= min_n and v["yield"] >= 0.5),
        "defs_fail": sorted(k for k, v in defs.items() if v["n"] >= min_n and v["yield"] < 0.5),
        "defs_short": sorted(k for k, v in defs.items() if v["n"] < min_n),
        "task_family_success": {f: round(v[1] / v[0], 3) for f, v in fam_ok.items()},
        "picks": len(picks), "approach_share": share(fams), "part_share": share(parts),
        "rot_bins_img_used": len(rimg), "rot_bins_base_used": len([b for b in rbase if b is not None]),
        "rule_share": {f"{a}/{b}": round(v / n_p, 3) for (a, b), v in rules.most_common()},
        "natural_rank0": round(sum(p.get("natural_rank") == 0 for p in picks) / n_p, 3),
        "instructed": round(sum(bool(p.get("instructed_approach")) for p in picks) / n_p, 3),
        "fallback": round(sum(bool((p.get("timeline") or {}).get("fallback_trace")) for p in picks) / n_p, 3),
        "line_moves": round(sum(bool((p.get("timeline") or {}).get("line_moves")) for p in picks) / n_p, 3),
        "regrasp": round(sum((p.get("regrasp_n") or 0) > 0 for p in picks) / n_p, 3),
        "close_outcome": share(outc),
        "visible_point": round(sum(bool(p.get("point_px_visible")) for p in picks) / n_p, 3),
        "tested": round(sum(bool(p.get("tested")) for p in picks) / n_p, 3),
        "arms": dict(arms), "robots": dict(robots), "defs": defs,
    }
    top = rep["approach_share"].get("top", 0.0)
    rep["verdict"] = {
        "top_le_50": top <= 0.5,
        "every_family_ge_5": all(rep["approach_share"].get(f, 0.0) >= 0.05 for f in ("top", "oblique", "front", "side")),
        "rot_img_ge_8": rep["rot_bins_img_used"] >= 8,
        "joint_step": max_dq <= 0.04,
        "task_family_exec_ge_70": all(v >= 0.70 for v in rep["task_family_success"].values()) if fam_ok else False,
    }
    json.dump(rep, open(out_path, "w"), indent=1)
    print(json.dumps({k: rep[k] for k in ("episodes", "yield", "approach_share", "part_share", "verdict")}))


if __name__ == "__main__":
    main()
