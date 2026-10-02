"""GGX A/B report: per robot x arm (rule / ggx) over <ab>/<arm>/collect. usage: ab_report.py <ab dir> <code dir>"""
import glob, json, os, subprocess, sys
from collections import Counter
ab, code = sys.argv[1], sys.argv[2]
ROB = {"ffw_sg2": "AIW", "franka_mast": "Franka"}
res, seeds = {}, {}
for arm in ("rule", "ggx"):
    for m in glob.glob(f"{ab}/{arm}/collect/**/meta.json", recursive=True):
        d = json.load(open(m)); r = ROB.get(d.get("robot", "ffw_sg2"), d.get("robot"))
        k = (r, arm); s = res.setdefault(k, {"n": 0, "succ": 0, "succ_dq": 0, "picks": 0, "fam": Counter(), "rot_img": Counter(),
                                         "src": Counter(), "regrasp_eps": 0, "fallback": 0, "part_none": 0, "pt_vis": 0,
                                         "rule": Counter(), "fail_stage": Counter()})
        s["n"] += 1; ok = bool(d.get("success")); s["succ"] += ok
        s["succ_dq"] += ok and (d.get("max_dq_rad") or 0) <= 0.04
        seeds.setdefault(r, {}).setdefault(d["seed"], {})[arm] = ok
        gv = d.get("grasp_v2") or {}
        if (gv.get("regrasp_n") or 0) > 0 or any((p.get("regrasp_n") or 0) > 0 for p in gv.get("picks") or []):
            s["regrasp_eps"] += 1
        try:
            rj = json.load(open(os.path.join(os.path.dirname(m), "result.json")))
            if not ok: s["fail_stage"][rj.get("fail_stage")] += 1
        except Exception:
            pass
        for p in gv.get("picks") or []:
            s["picks"] += 1; s["fam"][p.get("family")] += 1; s["src"][p.get("source")] += 1; s["rule"][p.get("label_rule")] += 1
            if p.get("rot_bin_img") is not None: s["rot_img"][p["rot_bin_img"]] += 1
            s["part_none"] += p.get("part") is None; s["pt_vis"] += bool(p.get("point_px_visible"))
            s["fallback"] += bool(p.get("fallback_from"))
out = {}
for (r, arm), s in sorted(res.items()):
    n, P = s["n"], max(s["picks"], 1)
    out[f"{r}/{arm}"] = {"episodes": n, "success": s["succ"], "rate": round(s["succ"] / max(n, 1), 3),
                         "success_dq_ok": s["succ_dq"], "regrasp_episode_rate": round(s["regrasp_eps"] / max(n, 1), 3),
                         "picks": s["picks"], "top_share": round(s["fam"].get("top", 0) / P, 3), "family": dict(s["fam"]),
                         "rot_img_bins_used": len(s["rot_img"]), "source": dict(s["src"]), "label_rule": dict(s["rule"]),
                         "part_none": s["part_none"], "fallback_picks": s["fallback"], "point_visible_share": round(s["pt_vis"] / P, 3),
                         "fail_stage": dict(s["fail_stage"])}
for r, d in seeds.items():
    both = [v for v in d.values() if len(v) == 2]
    out[f"{r}/paired"] = {"pairs": len(both), "both_ok": sum(v["rule"] and v["ggx"] for v in both),
                          "rule_only": sum(v["rule"] and not v["ggx"] for v in both),
                          "ggx_only": sum(v["ggx"] and not v["rule"] for v in both)}
print(json.dumps(out, indent=1))
for arm in ("rule", "ggx"):
    subprocess.run([sys.executable, f"{code}/tools/l9/gate_v2.py", f"{ab}/gate_{arm}.json", f"{ab}/{arm}/collect", "--min-n", "1"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
