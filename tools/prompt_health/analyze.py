"""Scores of the dynamic prompt tests (run_dyn.py JSONL) for the prompt health check (user-log 96).
Per (test, model, variant): n, parse failures (answer present but schema-invalid), API errors, flip rate of each judged
field against the base variant at temperature 0 (rep 0) on the same snapshot (only pairs where both parsed), and the
truth-based rates (false 'grasped' on not-held snapshots, missed 'grasped' on held ones; frame: xy angle error and
axis sign agreement). Consistency rows: base at temperature 0 again (rep 1) and at 0.7 (reps 0..).
usage: python tools/prompt_health/analyze.py dyn.jsonl [more.jsonl] --json out.json --md out.md"""
from __future__ import annotations

import argparse
import json
import math

FIELDS = {"grasp": ("grasp_state",), "couple_g": ("execution", "intent", "command", "claim_raw"),
          "couple_r": ("execution", "intent", "command", "claim_raw")}
BASE = {"grasp": "base", "couple_g": "base", "couple_r": "base", "frame": "prod"}


def load(paths) -> list:
    rows = []
    for p in paths:
        with open(p) as f:
            rows += [json.loads(line) for line in f if line.strip()]
    return rows


def _cond(r) -> str:
    if r["temp"] == 0.0 and r["rep"] == 0:
        return r["variant"]
    return f"{r['variant']}@t{r['temp']:g}r{r['rep']}"


def angle_deg(a, b) -> float | None:
    na, nb = math.hypot(a[0], a[1]), math.hypot(b[0], b[1])
    if na < 1e-9 or nb < 1e-9:
        return None
    c = (a[0] * b[0] + a[1] * b[1]) / (na * nb)
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


MISS_FIX = (0.09, 0.0, -0.03)  # G1 'miss' snapshots: the object stays 9 cm further along +x, 3 cm below the lifted TCP


def expected_command(test: str, r: dict) -> str:
    """Per-call command accuracy (user-log 97): the oracle-correct command for a snapshot. R set = the VLA follows
    the oracle planner, so continue (stop only once the episode is done). G set = continue while the grasp is on track
    (pre / closed / grasped, and a lifted rim grasp that holds); a lifted miss that does not hold needs an edit."""
    if test == "couple_r":
        return "stop" if r.get("state") == "done" else "continue"
    return "edit" if (r.get("state") == "miss" and not r["truth"]) else "continue"


def cos3(a, b) -> float:
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (na * nb)


def _rate(k: int, n: int):
    return {"k": k, "n": n, "rate": round(k / n, 3) if n else None}


def truth_stats(test: str, rs: list) -> dict:
    ok = [r for r in rs if r.get("valid")]
    if test == "grasp":
        neg = [r for r in ok if not r["truth"]]
        pos = [r for r in ok if r["truth"]]
        return {"false_grasped": _rate(sum(r["grasp_state"] == "grasped" for r in neg), len(neg)),
                "missed_grasped": _rate(sum(r["grasp_state"] != "grasped" for r in pos), len(pos)),
                "uncertain": sum(r["grasp_state"] == "uncertain" for r in ok),
                "correct": _rate(sum((r["grasp_state"] == "grasped") == bool(r["truth"]) for r in ok), len(ok))}
    if test in ("couple_g", "couple_r"):
        neg = [r for r in ok if not r["truth"]]
        pos = [r for r in ok if r["truth"]]
        exp = [expected_command(test, r) for r in ok]
        miss_edits = [r for r in ok if test == "couple_g" and r.get("state") == "miss" and not r["truth"]
                      and r.get("edit_dp")]
        return {"cmd_acc_raw": _rate(sum(r["command_raw"] == e for r, e in zip(ok, exp)), len(ok)),
                "cmd_acc_gated": _rate(sum(r["command"] == e for r, e in zip(ok, exp)), len(ok)),
                "miss_edit_dir_ok": _rate(sum(cos3(r["edit_dp"], MISS_FIX) > 0.5 for r in miss_edits), len(miss_edits)),
                "false_claim_raw": _rate(sum(r["claim_raw"] == "grasped" for r in neg), len(neg)),
                "false_claim_gated": _rate(sum(r["claim_gated"] == "grasped" for r in neg), len(neg)),
                "missed_claim_raw": _rate(sum(r["claim_raw"] != "grasped" for r in pos), len(pos)),
                "no_claim": sum(r["claim_raw"] == "none" for r in ok),
                "edit_raw": sum(r["command_raw"] == "edit" for r in ok),
                "stop_raw": sum(r["command_raw"] == "stop" for r in ok),
                "edit_after_gate": sum(r["command"] == "edit" for r in ok),
                "gates": {g: sum(r["gate"] == g for r in ok) for g in sorted({r["gate"] for r in ok})}}
    if test == "frame":
        errs, sx, sy = [], [], []
        for r in ok:
            dp, t = r["dp"], r["truth"]
            e = angle_deg(dp, t)
            if e is not None:
                errs.append(e)
            if abs(t[0]) > 0.01:
                sx.append((dp[0] > 0) == (t[0] > 0))
            if abs(t[1]) > 0.01:
                sy.append((dp[1] > 0) == (t[1] > 0))
        errs.sort()
        med = errs[len(errs) // 2] if errs else None
        return {"xy_err_deg_median": None if med is None else round(med, 1),
                "xy_err_gt90": _rate(sum(e > 90 for e in errs), len(errs)),
                "x_sign_agree": _rate(sum(sx), len(sx)), "y_sign_agree": _rate(sum(sy), len(sy)),
                "zero_xy": len(ok) - len(errs)}
    raise ValueError(test)


def flips(test: str, base: dict, rs: list) -> dict:
    out = {}
    if test == "frame":
        d = []
        for r in rs:
            b = base.get(r["snap"])
            if b and b.get("valid") and r.get("valid"):
                e = angle_deg(r["dp"], b["dp"])
                if e is not None:
                    d.append(e > 90)
        return {"dir_flip_gt90_vs_base": _rate(sum(d), len(d))}
    for f in FIELDS[test]:
        k = n = 0
        for r in rs:
            b = base.get(r["snap"])
            if b and b.get("valid") and r.get("valid"):
                n += 1
                k += b[f] != r[f]
        out[f] = _rate(k, n)
    return out


def score(rows: list) -> dict:
    res = {}
    groups: dict = {}
    for r in rows:
        groups.setdefault((r["test"], r["model"]), []).append(r)
    for (test, model), rs in sorted(groups.items()):
        base = {r["snap"]: r for r in rs if r["variant"] == BASE[test] and r["temp"] == 0.0 and r["rep"] == 0}
        conds: dict = {}
        for r in rs:
            conds.setdefault(_cond(r), []).append(r)
        out = {}
        for c, cr in conds.items():
            n = len(cr)
            api = sum(bool(r.get("api_error")) for r in cr)
            bad = sum((not r.get("valid")) and not r.get("api_error") for r in cr)
            out[c] = {"n": n, "api_error": api, "parse_fail": _rate(bad, n - api), "truth": truth_stats(test, cr),
                      "flip_vs_base": flips(test, base, cr) if c != BASE[test] else None,
                      "prompt_sha": sorted({r.get("prompt_sha") for r in cr})}
            if c == f"{BASE[test]}@t0r1":
                same = sum(1 for r in cr if base.get(r["snap"]) and base[r["snap"]]["raw"] == r["raw"])
                out[c]["identical_text_vs_rep0"] = _rate(same, n)
        res[f"{test}|{model}"] = out
    return res


def summary_table(res: dict) -> str:
    lines = ["| 시험 · 모델 | 조건 | n | 파싱 실패 | 뒤집힘(기준 대비) | 진실 기준 |", "|---|---|---|---|---|---|"]
    for key, out in res.items():
        for c, s in out.items():
            fl = s["flip_vs_base"]
            ftxt = "—" if fl is None else ", ".join(f"{f} {v['k']}/{v['n']}" for f, v in fl.items())
            t = s["truth"]
            parts = []
            for name, v in t.items():
                if isinstance(v, dict) and "k" in v:
                    parts.append(f"{name} {v['k']}/{v['n']}")
                elif not isinstance(v, dict):
                    parts.append(f"{name} {v}")
            pf = s["parse_fail"]
            lines.append(f"| {key} | {c} | {s['n']} | {pf['k']}/{pf['n']} | {ftxt} | {'; '.join(parts)} |")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl", nargs="+")
    ap.add_argument("--json")
    ap.add_argument("--md")
    a = ap.parse_args(argv)
    res = score(load(a.jsonl))
    if a.json:
        with open(a.json, "w") as f:
            json.dump(res, f, indent=1)
    md = summary_table(res)
    if a.md:
        with open(a.md, "w", encoding="utf-8") as f:
            f.write(md + "\n")
    print(md)


if __name__ == "__main__":
    main()
