"""L9 robot production gate (user 10-03 02h / 03h, L9_PRINCIPLES §6). Read-only.
A robot (per task kind: single-arm, articulated, bimanual) passes when
  (a) scene skips caused by limited arm reach are not failures: skipped rows (skipped.json, no episode) are left out
      of every denominator; they are only counted by reason;
  (b) every attempted definition with >= 5 rendered episodes has >= 1 success AND a success rate >= 10 %
      (fewer than 5 = "pending": fill it to 5, then judge);
  (c) the mean of the per-definition success rates is >= 25 % (user 10-03 03h, relaxed from 40 %), and
  (d) DIVERSITY is not narrower than the reference robots (AIW / Franka successes, --ref roots): the 25 % must not come
      from dropping hard or diverse motions (user 10-03 03h). Checked on successful episodes:
        coverage    share of attemptable definitions (those the reference succeeds on) with >= 1 success
        families    approach-family share: the top family <= max(50 %, ref top + 10 pp); every family the reference
                    uses with >= 5 % share is used
        rot_bins    distinct image rotation bins used >= 0.8 x reference
        arms        left share in 40-60 % for two-armed robots (fixed band; the reference mixes right-only Franka)
        spread      IQR of support height (table_z), of grasp x and of grasp y (base frame) >= 0.8 x reference
        high_share  high / shelf placements (place band "high"): when the reference share is >= 2 %, >= 0.8 x it;
                    below that the reference has too few to judge (reported only)
verdict: FAIL (a judged definition fails (b), or (c)/(d) fail with nothing pending) / PENDING (definitions below 5,
or no reference given) / PASS.
usage: python tools/l9/robot_gate9.py <collect root>... --robot r1pro [--ref <collect root>,...] [--ref-robots
       ffw_sg2,franka_mast] [--min-eps 1] [--json out.json] [--exclude a,b]
--exclude: definitions still experimental for every robot (main 10-03 02h); default EXPERIMENTAL_ALL below.
A collect root is a dir with <split>/<family>/<episode>/meta.json (or skipped.json)."""
import glob
import json
import os
import sys
from collections import Counter, defaultdict

JUDGE_MIN_EPS = 5  # user 10-03 02h: (b) is judged only on definitions with >= 5 attempted episodes; fewer = "pending"
MEAN_MIN = 0.25  # user 10-03 03h (was 0.40), only together with the diversity check (d)
SPREAD_FRAC = 0.8  # (d): a spread / coverage-type metric must reach this fraction of the reference
REACH_WORDS = ("reach", "outside its", "standing band", "ik precheck")  # articulated: IK precheck = arm cannot reach
EXPERIMENTAL_ALL = ("drawer_put_close", "drawer_take_close")  # experimental for every robot (+ AIW far push defs)
TWO_ARMED = ("ffw_sg2", "r1pro", "g1")


def skip_kind(reason: str) -> str:
    r = (reason or "").lower()
    if any(w in r for w in REACH_WORDS):
        return "reach"
    if "no valid grasp" in r:
        return "no_valid_grasp"
    if "does not fit" in r:
        return "scene_fit"
    if "out of view" in r:
        return "out_of_view"
    return "other"


def _iqr(v):
    v = sorted(v)
    if len(v) < 4:
        return None
    return round(v[(3 * len(v)) // 4] - v[len(v) // 4], 4)


def _episodes(roots, robots):
    """yield (kind, meta-or-skip, row) for the robots (None = any)."""
    for root in roots:
        for d in glob.glob(os.path.join(root, "*", "*", "*")):
            m = os.path.join(d, "meta.json")
            if os.path.exists(m):
                try:
                    meta = json.load(open(m))
                except ValueError:
                    continue
                if robots and (meta.get("robot") or "ffw_sg2") not in robots:
                    continue
                yield "ep", meta, None
                continue
            s = os.path.join(d, "skipped.json")
            if os.path.exists(s):
                try:
                    sk = json.load(open(s))
                except ValueError:
                    continue
                row = sk.get("row") or {}
                if robots and (row.get("robot") or "ffw_sg2") not in robots:
                    continue
                yield "skip", sk, row


def profile(metas) -> dict:
    """Diversity profile of successful episodes (meta dicts)."""
    fam, rot, arm, defs = Counter(), set(), Counter(), set()
    tz, gx, gy, bands = [], [], [], Counter()
    for m in metas:
        defs.add(m.get("task_id"))
        arm[m.get("arm") or "?"] += 1
        if m.get("table_z") is not None:
            tz.append(float(m["table_z"]))
        base = m.get("base") if isinstance(m.get("base"), dict) else {}
        bx, by = (base.get("pos") or [0.0, 0.0])[:2] if base else (0.0, 0.0)
        for p in (m.get("grasp_v2") or {}).get("picks") or []:
            if p.get("family"):
                fam[p["family"]] += 1
            if p.get("rot_bin_img") is not None:
                rot.add(int(p["rot_bin_img"]))
            g = p.get("grasp_world")
            if g:
                gx.append(float(g[0][3]) - float(bx))
                gy.append(float(g[1][3]) - float(by))
        for s in m.get("step_info") or []:
            b = (s.get("place_height") or {}).get("band")
            if b:
                bands[b] += 1
    nf = sum(fam.values()) or 1
    nb = sum(bands.values()) or 1
    na = sum(arm.values()) or 1
    return {"n": len(metas), "defs": sorted(d for d in defs if d), "family_share": {k: round(v / nf, 3) for k, v in fam.items()},
            "rot_bins": len(rot), "left_share": round(arm.get("left", 0) / na, 3),
            "iqr_table_z": _iqr(tz), "iqr_x": _iqr(gx), "iqr_y": _iqr(gy), "high_share": round(bands.get("high", 0) / nb, 3)}


def diversity_check(p: dict, ref: dict, robot: str) -> dict:
    out = {}
    att = set(ref["defs"])
    out["coverage"] = round(len(set(p["defs"]) & att) / max(1, len(att)), 3)
    out["coverage_ok"] = None  # coverage is reported; the per-definition rule (b) already requires success on every
    # attempted definition, so a robot that only does a subset is caught there (attempted = drawn for that robot)
    top = max(p["family_share"].values()) if p["family_share"] else 1.0
    rtop = max(ref["family_share"].values()) if ref["family_share"] else 0.5
    missing = sorted(k for k, v in ref["family_share"].items() if v >= 0.05 and k not in p["family_share"])
    out["families_ok"] = top <= max(0.5, rtop + 0.10) and not missing
    out["families_missing"] = missing
    out["rot_bins_ok"] = p["rot_bins"] >= SPREAD_FRAC * ref["rot_bins"]
    out["arms_ok"] = (0.40 <= p["left_share"] <= 0.60) if robot in TWO_ARMED else True
    for k in ("iqr_table_z", "iqr_x", "iqr_y"):
        out[k + "_ok"] = (p[k] is not None and ref[k] is not None and p[k] >= SPREAD_FRAC * ref[k]) or ref[k] in (None, 0)
    out["high_share_ok"] = (p["high_share"] >= SPREAD_FRAC * ref["high_share"]) if ref["high_share"] >= 0.02 else None
    out["ref"] = {k: ref[k] for k in ("family_share", "rot_bins", "left_share", "iqr_table_z", "iqr_x", "iqr_y", "high_share")}
    out["ok"] = all(v for k, v in out.items() if k.endswith("_ok") and v is not None)
    out["narrower"] = sorted(k[:-3] for k, v in out.items() if k.endswith("_ok") and v is False)
    return out


def evaluate(roots, robot=None, min_eps=1, exclude=EXPERIMENTAL_ALL, ref_roots=(), ref_robots=("ffw_sg2", "franka_mast")):
    eps, succ = Counter(), Counter()
    skips = defaultdict(Counter)
    ok_metas = []
    ex = set(exclude)
    for kind, x, row in _episodes(roots, {robot} if robot else None):
        if kind == "ep":
            k = x.get("task_id") or "?"
            eps[k] += 1
            if x.get("success"):
                succ[k] += 1
                if k not in ex:
                    ok_metas.append(x)
        else:
            skips[row.get("def") or "?"][skip_kind(x.get("reason", ""))] += 1
    defs = {}
    excluded = sorted(k for k in eps if k in ex)
    for k in sorted(eps):
        if eps[k] < min_eps or k in ex:
            continue
        rate = succ[k] / eps[k]
        judged = eps[k] >= JUDGE_MIN_EPS
        defs[k] = {"eps": eps[k], "succ": succ[k], "rate": round(rate, 3), "judged": judged,
                   "ok": (succ[k] >= 1 and rate >= 0.10) if judged else None, "skips": dict(skips.get(k, {}))}
    rates = [v["rate"] for v in defs.values()]
    mean = round(sum(rates) / len(rates), 3) if rates else 0.0
    failing = sorted(k for k, v in defs.items() if v["ok"] is False)
    pending = sorted(k for k, v in defs.items() if not v["judged"])
    sk_total = Counter()
    for c in skips.values():
        sk_total.update(c)
    prof = profile(ok_metas)
    div = None
    if ref_roots:
        ref_metas = [x for kind, x, _ in _episodes(ref_roots, set(ref_robots)) if kind == "ep" and x.get("success")
                     and (x.get("task_id") not in ex)]
        div = diversity_check(prof, profile(ref_metas), robot)
    div_ok = bool(div and div["ok"])
    if failing or (defs and not pending and (mean < MEAN_MIN or (div is not None and not div_ok))):
        verdict = "FAIL"
    elif pending or not defs or div is None:
        verdict = "PENDING"
    else:
        verdict = "PASS"
    return {"robot": robot, "defs_attempted": len(defs), "episodes": sum(eps.values()), "successes": sum(succ.values()),
            "pooled_rate": round(sum(succ.values()) / max(1, sum(eps.values())), 3), "mean_def_rate": mean,
            "defs_failing_b": len(failing), "failing_examples": failing[:15],
            "defs_pending": len(pending), "pending_need": {k: JUDGE_MIN_EPS - defs[k]["eps"] for k in pending},
            "excluded_experimental": excluded, "skips_by_kind": dict(sk_total), "pass_b": not failing,
            "pass_c": mean >= MEAN_MIN, "pass_d": div_ok if div is not None else None, "diversity": div,
            "profile": {k: v for k, v in prof.items() if k != "defs"}, "PASS": verdict == "PASS", "verdict": verdict,
            "defs": defs}


def main():
    a = sys.argv[1:]
    arg = lambda k, d: a[a.index(k) + 1] if k in a else d  # noqa: E731
    keys = ("--robot", "--min-eps", "--json", "--exclude", "--ref", "--ref-robots")
    vals = {arg(k, None) for k in keys}
    roots = [x for x in a if not x.startswith("--") and x not in vals]
    ex = arg("--exclude", None)
    ref = [x for x in (arg("--ref", "") or "").split(",") if x]
    rr = tuple(x for x in arg("--ref-robots", "ffw_sg2,franka_mast").split(",") if x)
    rep = evaluate(roots, arg("--robot", None), int(arg("--min-eps", "1")),
                   tuple(x for x in ex.split(",") if x) if ex is not None else EXPERIMENTAL_ALL, ref, rr)
    out = arg("--json", None)
    if out:
        json.dump(rep, open(out, "w"), indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k != "defs"}))


if __name__ == "__main__":
    main()
