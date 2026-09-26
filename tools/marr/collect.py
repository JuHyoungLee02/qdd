"""Collect the gate evidence of the MolmoAct real-data readiness into one JSON (docs/stage3/results/marr_gates.json)."""
import json
import sys

L = "/data/harvest/logs/marr"


def j(p):
    return json.load(open(p))


out = {"eye": {}}
for name, f in (("v1_on_sample1", "eye_eval.json"), ("v2_on_sample1_dev", "eye_eval_v2_s1.json"),
                ("v2_on_sample2_validation", "eye_eval_v2_v2.json"), ("v1_on_sample2", "eye_eval_v1_v2.json")):
    out["eye"][name] = j(f"{L}/{f}")["summary"]
a1, a2 = j(f"{L}/analysis.json"), j(f"{L}/analysis_v2.json")
out["stats_v1"] = {s: {k: v for k, v in a1["stats"][s].items() if k not in ("dlt_median_resid_px", "dlt_inlier_frac",
                                                                          "offsets")} for s in a1["stats"]}
out["stats_v2"] = {s: {k: v for k, v in a2["stats"][s].items() if k not in ("dlt_median_resid_px", "dlt_inlier_frac")}
                   for s in a2["stats"]}
out["colour"] = a2["colour"]
out["diversity_v2"] = a2["diversity"]
out["scenes_first_frame"] = a1["scenes"]
out["episodes_v2"] = a2["episodes"]
cf = j(f"{L}/camfit.json")
out["camfit"] = {"source_level": {s: {t: {k: v for k, v in d.items() if k != "per_episode_inlier_frac"}
                                      for t, d in cf["src"][s].items()} for s in cf["src"]},
                 "episode_level": cf["episodes"]}
out["nominal_diag_sample1"] = j(f"{L}/nominal_diag.json")["by_code"]
out["sim_default_path"] = {"G-default": {k: v for k, v in j("/data/harvest/mar2d/gates/gdefault.json").items()
                                         if k != "rows"},
                           "G-x2": {k: v for k, v in j("/data/harvest/mar2d/gates/gx2.json").items() if k != "rows"}}
out["utc_collected"] = a2["utc"]
json.dump(out, sys.stdout, indent=1)
