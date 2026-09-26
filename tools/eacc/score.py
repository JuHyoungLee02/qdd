"""E-ACC scoring and pre-registered decisions (docs/stage3/prereg_eacc.md §5-§6). Reads the call rows (run_eacc.py
JSONL) and the bench metas; no model calls.
Per arm: M1 edit direction at arrival (off snapshots; correct = valid, gated command edit, angle < 60 deg to the
oracle subgoal from the tip at t_snap + 9.3 s), M2 segment 'now' (v2 arms), M3 command (all snapshots), invalid rate,
latency p50 / p95 (wall clock), first token p50, KRW per call; secondaries (send-time direction, direction given an
edit, pre-gate command, do / next consistency, x / y sign).
Paired comparisons: difference of means over the snapshots both arms answered (invalid = wrong), 95 % percentile
bootstrap over snapshots (10,000 resamples, seed 0).
usage: python tools/eacc/score.py --bench B --rows R.jsonl [R2.jsonl ...] --json out.json [--decide]"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench as B  # noqa: E402

N_BOOT, SEED = 10000, 0
SAME_DIR_DEG = 35.0  # CoupleParams.same_dir_deg (two-answer agreement)


def load_rows(paths: list) -> list:
    out = []
    for p in paths:
        with open(p) as f:
            out += [json.loads(line) for line in f if line.strip()]
    return out


def ans_of(r: dict):
    if not r.get("valid"):
        return None
    return {"command": r["command"], "command_raw": r["command_raw"], "edit_dp": r.get("edit_dp"),
            "edit_dp_raw": r.get("edit_dp_raw"), "segment": r.get("segment")}


def scored(rows: list, metas: dict, horizon: float = B.L_ARR) -> list:
    out = []
    for r in rows:
        m = metas[r["snap"]]
        s = B.score_answer(m, ans_of(r), horizon)
        out.append({**r, "score": s})
    return out


def _rate(xs: list) -> dict:
    xs = [x for x in xs if x is not None]
    return {"k": int(sum(bool(x) for x in xs)), "n": len(xs), "rate": round(sum(bool(x) for x in xs) / len(xs), 3)
            if xs else None}


def _pct(xs, q):
    xs = [x for x in xs if x is not None]
    return round(float(np.percentile(xs, q)), 2) if xs else None


def arm_table(srows: list, metas: dict) -> dict:
    by = {}
    for r in srows:
        by.setdefault(r["arm"], []).append(r)
    out = {}
    for arm, rs in sorted(by.items()):
        off = [r for r in rs if r["kind"] != "on"]
        edits = [r for r in off if r["score"].get("valid") and r.get("command") == "edit"]
        sign_x, sign_y = [], []
        for r in edits:
            o = B.oracle(metas[r["snap"]])
            dp, d = r["edit_dp"], o["dir_arr"]
            if abs(d[0]) > 0.02:
                sign_x.append(np.sign(dp[0]) == np.sign(d[0]))
            if abs(d[1]) > 0.02:
                sign_y.append(np.sign(dp[1]) == np.sign(d[1]))
        out[arm] = {
            "n": len(rs), "invalid": _rate([not r["valid"] for r in rs]),
            "M1_dir_arr": _rate([r["score"]["dir_ok"] for r in off]),
            "M1_dir_send": _rate([r["score"]["dir_ok_send"] for r in off]),
            "M1_given_edit": _rate([r["score"]["dir_ok"] for r in edits]),
            "M1_raw_pre_gate": _rate([r["score"].get("dir_ok_raw", False) for r in off]),
            "M2_segment": _rate([r["score"]["seg_ok"] for r in rs]),
            "M2_triple": _rate([r["score"]["triple_ok"] for r in rs]),
            "M3_command": _rate([r["score"]["cmd_ok"] for r in rs]),
            "M3_on": _rate([r["score"]["cmd_ok"] for r in rs if r["kind"] == "on"]),
            "M3_off": _rate([r["score"]["cmd_ok"] for r in off]),
            "M3_raw_pre_gate": _rate([r["score"].get("cmd_raw_ok", False) for r in rs]),
            "x_sign": _rate(sign_x), "y_sign": _rate(sign_y),
            "ang_arr_median": _pct([r["score"].get("ang_arr") for r in edits], 50),
            "latency_p50": _pct([r["latency_s"] for r in rs if not r.get("api_error")], 50),
            "latency_p95": _pct([r["latency_s"] for r in rs if not r.get("api_error")], 95),
            "first_token_p50": _pct([r.get("first_token_s") for r in rs if not r.get("api_error")], 50),
            "krw_per_call": round(float(np.mean([r.get("cost_krw", 0.0) for r in rs])), 2),
            "krw_total": round(float(sum(r.get("cost_krw", 0.0) for r in rs)), 1),
            "in_tok_mean": round(float(np.mean([(r.get("usage") or {}).get("input_tokens", 0) for r in rs])), 1),
            "out_tok_mean": round(float(np.mean([(r.get("usage") or {}).get("output_tokens", 0) for r in rs])), 1),
            "gates": {g: sum(r.get("gate") == g for r in rs) for g in sorted({r.get("gate") for r in rs if r.get("gate")})},
            "commands": {c: sum(r.get("command") == c for r in rs) for c in ("continue", "edit", "stop")},
            "by_kind_M3": {k: _rate([r["score"]["cmd_ok"] for r in rs if r["kind"] == k])
                           for k in ("on", "off_a", "off_b", "off_c")},
            "by_kind_M1": {k: _rate([r["score"]["dir_ok"] for r in rs if r["kind"] == k])
                           for k in ("off_a", "off_b", "off_c")}}
    return out





def paired(srows: list, a: str, b: str, metric: str, kinds=None) -> dict:
    """mean(b) - mean(a) over snapshots with rows in both arms (invalid = wrong); bootstrap CI."""
    ra = {r["snap"]: r for r in srows if r["arm"] == a and (kinds is None or r["kind"] in kinds)}
    rb = {r["snap"]: r for r in srows if r["arm"] == b and (kinds is None or r["kind"] in kinds)}
    keys = sorted(set(ra) & set(rb))
    xa = np.array([bool(ra[k]["score"][metric]) for k in keys], float)
    xb = np.array([bool(rb[k]["score"][metric]) for k in keys], float)
    if not keys:
        return {"n": 0}
    d = xb - xa
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(keys), size=(N_BOOT, len(keys)))
    boots = d[idx].mean(1)
    return {"a": a, "b": b, "metric": metric, "n": len(keys), "mean_a": round(float(xa.mean()), 3),
            "mean_b": round(float(xb.mean()), 3), "diff": round(float(d.mean()), 3),
            "ci95": [round(float(np.percentile(boots, 2.5)), 3), round(float(np.percentile(boots, 97.5)), 3)],
            "b_only": int(((xb == 1) & (xa == 0)).sum()), "a_only": int(((xa == 1) & (xb == 0)).sum()),
            "bootstrap": {"n": N_BOOT, "seed": SEED, "unit": "snapshot"}}


OFF = ("off_a", "off_b", "off_c")


def decide(srows: list, tab: dict) -> dict:
    """Pre-registered rules (prereg §6)."""
    out = {}
    have = set(tab)
    n_off = sum(r["kind"] in OFF for r in srows)
    if n_off == 0:  # no off-plan snapshot answered: M1 does not exist, R1 / R2 cannot be decided
        out["no_off_data"] = True
        for a, b, key in (("v1", "v2", "R1_v2_vs_v1"), ("v2", "v2cp", "R2_campose")):
            if {a, b} <= have:
                out[key] = {"verdict": "not_decidable_no_off_data", "M3": paired(srows, a, b, "cmd_ok"),
                            "M2": paired(srows, a, b, "seg_ok") if a != "v1" else None}
        return out
    if {"v1", "v2"} <= have:
        m1 = paired(srows, "v1", "v2", "dir_ok", OFF)
        m3 = paired(srows, "v1", "v2", "cmd_ok")
        inv = tab["v2"]["invalid"]["rate"]
        ok = inv <= 0.10 and m1["diff"] >= -0.10 and m3["diff"] >= -0.10
        out["R1_v2_vs_v1"] = {"M1": m1, "M3": m3, "invalid_v2": inv, "adopt_v2": bool(ok),
                              "superior_M1": m1["diff"] >= 0.10 and m1["ci95"][0] > 0,
                              "superior_M3": m3["diff"] >= 0.10 and m3["ci95"][0] > 0}
    for arm, key in (("v2cp", "R2_campose"), ("v2_ax", "R2p_axisguide")):  # R2 / R2' (prereg change 4)
        if {"v2", arm} <= have:
            m1 = paired(srows, "v2", arm, "dir_ok", OFF)
            m3 = paired(srows, "v2", arm, "cmd_ok", OFF if key == "R2p_axisguide" else None)
            m2 = paired(srows, "v2", arm, "seg_ok")
            inv = tab[arm]["invalid"]["rate"]
            if m1.get("n", 0) == 0:
                out[key] = {"verdict": "not_run_on_off", "M2": m2, "M3": m3}
                continue
            if m1["diff"] >= 0.10 and m1["ci95"][0] > 0 and m3["diff"] >= -0.05 and inv <= 0.10:
                verdict = "adopt"
            elif m1["diff"] <= -0.10:
                verdict = "reject"
            else:
                verdict = "undecided"
            out[key] = {"M1": m1, "M2": m2, "M3": m3, "invalid": inv, "verdict": verdict,
                        "best_arm": arm if verdict == "adopt" else "v2"}
    best = next((out[k]["best_arm"] for k in ("R2p_axisguide", "R2_campose") if out.get(k, {}).get("best_arm")), None)
    if best:
        sub = {r["snap"] for r in srows if r["arm"] in (best + "_med", best + "_r1", best + "_2cam")}
        if best + "_med" in have:
            lat = tab[best + "_med"]
            n_low = sum(bool(r["score"]["cmd_ok"]) + bool(r["score"].get("dir_ok") or False)
                        for r in srows if r["arm"] == best and r["snap"] in sub)
            n_med = sum(bool(r["score"]["cmd_ok"]) + bool(r["score"].get("dir_ok") or False)
                        for r in srows if r["arm"] == best + "_med")
            out["R3_effort_medium"] = {"latency_p50": lat["latency_p50"], "latency_p95": lat["latency_p95"],
                                       "correct_low": n_low, "correct_med": n_med,
                                       "recommend_medium": bool(lat["latency_p95"] is not None
                                                                and lat["latency_p95"] <= 15.0 and n_med >= n_low + 2)}
        if best + "_r1" in have:
            out["R4_ask_twice"] = agreement(srows, best, best + "_r1")
        if best + "_2cam" in have:
            n3 = sum(bool(r["score"]["cmd_ok"]) + bool(r["score"].get("dir_ok") or False)
                     for r in srows if r["arm"] == best and r["snap"] in sub)
            n2 = sum(bool(r["score"]["cmd_ok"]) + bool(r["score"].get("dir_ok") or False)
                     for r in srows if r["arm"] == best + "_2cam")
            inv2 = tab[best + "_2cam"]["invalid"]["rate"]
            out["R5_two_cameras"] = {"correct_3cam": n3, "correct_2cam": n2, "invalid_2cam": inv2,
                                     "drop_left_wrist": bool(n2 >= n3 and inv2 <= 0.10)}
    out.update(stage2(srows, tab))
    if "S2A_effort_medium" in out:
        out.pop("R3_effort_medium", None)  # the registered P2 rule R3 is replaced by S2A (prereg change 5)
    return out


S2_OFF = ("off_a", "off_c")


def stage2(srows: list, tab: dict) -> dict:
    """Prereg change 5 rules. detects = gated command edit on an off_a / off_c snapshot; correct = detects and the
    arrival direction < 60 deg (M1). Both arms are compared with v2 (low) on the same snapshots."""
    out = {}
    have = set(tab)

    def detects(arm):
        rs = [r for r in srows if r["arm"] == arm and r["kind"] in S2_OFF]
        return {"n": len(rs), "detects": sum(r.get("command") == "edit" for r in rs),
                "correct": sum(bool(r["score"].get("dir_ok")) for r in rs)}
    for arm, key in (("v2_med", "S2A_effort_medium"), ("v2_gc", "S2B_goal_check")):
        if arm not in have or "v2" not in have:
            continue
        m1 = paired(srows, "v2", arm, "dir_ok", S2_OFF)
        inv = tab[arm]["invalid"]["rate"]
        rec = {"M1": m1, "v2": detects("v2"), arm: detects(arm), "invalid": inv,
               "latency_p50": tab[arm]["latency_p50"], "latency_p95": tab[arm]["latency_p95"]}
        gain = m1.get("n", 0) > 0 and m1["diff"] >= 0.25 and m1["ci95"][0] > 0 and inv <= 0.10
        if key == "S2A_effort_medium":
            rec["recommend"] = bool(gain and tab[arm]["latency_p95"] is not None and tab[arm]["latency_p95"] <= 15.0)
        else:
            on = paired(srows, "v2", arm, "cmd_ok", ("on",))
            rec["on_M3"] = on
            on_ok = on.get("n", 0) > 0 and (on["mean_b"] - on["mean_a"]) * on["n"] >= -1 - 1e-9
            rec["adopt_into_v2"] = bool(gain and on_ok)
        out[key] = rec
    return out


def agreement(srows: list, a: str, b: str) -> dict:
    ra = {r["snap"]: r for r in srows if r["arm"] == a}
    rb = {r["snap"]: r for r in srows if r["arm"] == b}
    keys = sorted(set(ra) & set(rb))
    agree, rows = 0, []
    for k in keys:
        x, y = ra[k], rb[k]
        same = bool(x.get("valid") and y.get("valid") and x["command"] == y["command"])
        if same and x["command"] == "edit":
            ang = B.angle_deg(x["edit_dp"], y["edit_dp"])
            same = ang is not None and ang < SAME_DIR_DEG
        if same and x.get("segment") and y.get("segment"):
            same = x["segment"]["now"] == y["segment"]["now"]
        agree += same
        ok_x = bool(x["score"]["cmd_ok"]) and (x["score"].get("dir_ok") is not False)
        rows.append({"snap": k, "agree": same, "correct_first": ok_x})
    ag = [r for r in rows if r["agree"]]
    return {"n": len(keys), "agree": agree, "agree_rate": round(agree / len(keys), 3) if keys else None,
            "correct_first_all": _rate([r["correct_first"] for r in rows]),
            "correct_first_when_agree": _rate([r["correct_first"] for r in ag]),
            "correct_first_when_disagree": _rate([r["correct_first"] for r in rows if not r["agree"]])}


def load_metas(bench: str) -> dict:
    out = {}
    for ep in B.plan():
        p = os.path.join(bench, ep["id"], "meta.json")
        if os.path.exists(p):
            out[ep["id"]] = json.load(open(p))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True)
    ap.add_argument("--rows", nargs="+", required=True)
    ap.add_argument("--json", required=True)
    ap.add_argument("--decide", action="store_true")
    ap.add_argument("--horizon", type=float, default=B.L_ARR)
    a = ap.parse_args(argv)
    metas = load_metas(a.bench)

    rows = load_rows(a.rows)
    keys = [(r["arm"], r["snap"]) for r in rows]
    if len(keys) != len(set(keys)):
        raise SystemExit("duplicate (arm, snap) rows")
    srows = scored(rows, metas, a.horizon)
    tab = arm_table(srows, metas)
    out = {"arms": tab, "horizon_s": a.horizon, "n_rows": len(rows)}
    if a.decide:
        out["decisions"] = decide(srows, tab)
    out["rows"] = [{k: r[k] for k in ("arm", "snap", "kind")} | {"score": r["score"]} for r in srows]
    with open(a.json, "w") as f:
        json.dump(out, f, indent=1)
    for arm, t in tab.items():
        print(arm, json.dumps({k: t[k] for k in ("n", "invalid", "M1_dir_arr", "M2_segment", "M3_command",
                                                 "latency_p50", "krw_per_call")}))
    if a.decide:
        print(json.dumps(out["decisions"], indent=1))


if __name__ == "__main__":
    main()
