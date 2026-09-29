"""Per-call command accuracy of the logged E-Astra-motion probe answers (user-log 97; read-only, no model calls).
Each answer is scored against the simulator oracle of its episode: the oracle grasp point gp = the TCP of the G1 v2
'pre' snapshot of the same seed and task (grasp_snaps_v2/s<seed>_<task>/pre/meta.json: the code executor drove the
TCP to the oracle grasp point on a hard reset of the same scene; the probe episodes never touched the target before
the first close -- result.json fail_stage approach / knocked []).
Per answer with an edit (new, or F1 keep of a committed edit): angle between delta_position and gp - TCP at the send
time (state the answer was based on) and at the arrival time (when it is applied); dir_ok = angle < 60 deg (cos > 0.5,
the E-SR0 adherence tolerance); xy_ok the same on x, y only (when gp is > 2 cm away in xy). premature_close = gripper
close while |gp - TCP(arrival)| > 2 cm. stop is always wrong here (no episode succeeded).
usage (pod): python tools/prompt_health/probe_acc.py --root /data/harvest/out/astra_motion --out acc.json"""
from __future__ import annotations

import argparse
import json
import math
import os

GP_ROOT = "grasp_snaps_v2"


def tcp_at(path: list, t: float) -> list:
    best = min(path, key=lambda p: abs(p[0] - t))
    return best[1:4]


def angle(a, b) -> float | None:
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    if na < 1e-9 or nb < 1e-9:
        return None
    c = sum(x * y for x, y in zip(a, b)) / (na * nb)
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def score_edit(dp_cm, gripper, gp, tcp_send, tcp_arr) -> dict:
    dp = [v / 100.0 for v in dp_cm]
    to_s = [g - p for g, p in zip(gp, tcp_send)]
    to_a = [g - p for g, p in zip(gp, tcp_arr)]
    a_s, a_a = angle(dp, to_s), angle(dp, to_a)
    xy_far = math.hypot(to_a[0], to_a[1]) > 0.02
    a_xy = angle(dp[:2], to_a[:2]) if xy_far else None
    dist_a = math.sqrt(sum(x * x for x in to_a))
    return {"ang_send": None if a_s is None else round(a_s, 1), "ang_arr": None if a_a is None else round(a_a, 1),
            "ang_xy_arr": None if a_xy is None else round(a_xy, 1), "dist_arr_m": round(dist_a, 4),
            "dir_ok_send": a_s is not None and a_s < 60, "dir_ok_arr": a_a is not None and a_a < 60,
            "xy_ok_arr": None if a_xy is None else a_xy < 60,
            "premature_close": gripper == "close" and dist_a > 0.02, "norm_cm": round(math.sqrt(sum(v * v for v in dp_cm)), 2)}


def episode_rows(res: dict, gp: list) -> list:
    path = res["tcp_path"]
    rows = []
    if res.get("stream"):
        for a in res["stream"]["answers"]:
            eff = a.get("effective") or {}
            dec = eff.get("decision") or a.get("decision")
            r = {"send_t": a["send_t"], "arr_t": a["arr_t"], "decision": a.get("decision"), "effective": dec,
                 "valid": a.get("valid")}
            e = eff.get("edit")
            if dec == "edit" and e:
                r.update(score_edit(e["delta_position_cm"], e.get("gripper"), gp, tcp_at(path, a["send_t"]),
                                    tcp_at(path, a["arr_t"])))
            rows.append(r)
    else:  # synchronous S: the robot waits, send state = arrival state
        for c in res["calls"]:
            p = c.get("parsed") or {}
            dec = p.get("decision")
            r = {"send_t": c["t_sim"], "arr_t": c["t_sim"], "decision": dec, "effective": dec, "valid": c["valid"]}
            e = p.get("edit")
            if dec == "edit" and e:
                t = tcp_at(path, c["t_sim"])
                r.update(score_edit(e["delta_position_cm"], e.get("gripper"), gp, t, t))
            rows.append(r)
    return rows


def summarize(rows: list) -> dict:
    ed = [r for r in rows if "dir_ok_arr" in r]
    xy = [r for r in ed if r["xy_ok_arr"] is not None]
    ang = sorted(r["ang_arr"] for r in ed if r["ang_arr"] is not None)

    def rate(k, n):
        return {"k": k, "n": n, "rate": round(k / n, 3) if n else None}
    return {"answers": len(rows), "edits": len(ed), "continue": sum(r["effective"] == "continue" for r in rows),
            "keep": sum(r["decision"] == "keep" for r in rows), "stop": sum(r["effective"] == "stop" for r in rows),
            "invalid": sum(not r["valid"] for r in rows),
            "dir_ok_send": rate(sum(r["dir_ok_send"] for r in ed), len(ed)),
            "dir_ok_arr": rate(sum(r["dir_ok_arr"] for r in ed), len(ed)),
            "xy_ok_arr": rate(sum(r["xy_ok_arr"] for r in xy), len(xy)),
            "ang_arr_median": ang[len(ang) // 2] if ang else None,
            "premature_close": rate(sum(r["premature_close"] for r in ed), len(ed)),
            "norm_cm_median": sorted(r["norm_cm"] for r in ed)[len(ed) // 2] if ed else None}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/data/harvest/out/astra_motion")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = {"episodes": {}, "groups": {}}
    groups: dict = {}
    for model in sorted(os.listdir(a.root)):
        md = os.path.join(a.root, model)
        if model in ("sanity", "dbg", "none", "sheets", GP_ROOT, "grasp_snaps") or not os.path.isdir(md):
            continue
        for mode in sorted(os.listdir(md)):
            for ep in sorted(os.listdir(os.path.join(md, mode))):
                rp = os.path.join(md, mode, ep, "result.json")
                gpp = os.path.join(a.root, GP_ROOT, ep, "pre", "meta.json")
                if not (os.path.exists(rp) and os.path.exists(gpp)):
                    continue
                res = json.load(open(rp))
                gp = json.load(open(gpp))["tcp"]
                rows = episode_rows(res, gp)
                key = f"{model}|{mode}"
                out["episodes"][f"{key}|{ep}"] = {"prompt_id": res.get("prompt_id"), "gp": gp,
                                                   "summary": summarize(rows), "rows": rows}
                groups.setdefault(key, []).extend(rows)
                groups.setdefault(f"{key}|prompt={res.get('prompt_id')}", []).extend(rows)
    out["groups"] = {k: summarize(v) for k, v in groups.items()}
    with open(a.out, "w") as f:
        json.dump(out, f, indent=1)
    for k, s in out["groups"].items():
        print(k, json.dumps(s))


if __name__ == "__main__":
    main()
