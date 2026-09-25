"""E0 judgments (E §2.7) from rows {size, N, slot, site, lat(s)|None, ok}.

Failures (429/5xx/timeout) and latencies above the 2 s cap are censored as +inf (E §2.6).
"""
import json
import math
from collections import defaultdict

import numpy as np


def censored_quantile(lat, q, cap_s=2.0):
    xs = sorted(math.inf if (x is None or x > cap_s) else x for x in lat)
    if not xs:
        return math.inf
    return xs[min(len(xs) - 1, int(math.ceil(q * len(xs))) - 1)]


def records_to_rows(jsonl_path):
    rows = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("kind") != "call":
                continue
            m = r["meta"]
            ok = r["http_status"] == 200 and r["error"] is None
            rows.append({"size": m["size"], "N": m.get("N", 1), "slot": m["slot"], "site": m["site"],
                         "phase": m.get("phase"), "ok": ok,
                         "lat": round(r["t_done"] - r["t_send"], 6) if ok else None})
    return rows


def _n_max(by, L1, T_c):
    if not math.isfinite(L1):
        return None
    cand = math.ceil(L1 / T_c) + 1
    base = censored_quantile(by.get(("S1", 1), []), 0.95)
    measured = sorted((n for (s, n) in by if s == "S1" and n <= cand), reverse=True)
    # largest measured N <= candidate whose concurrency penalty p95(N)/p95(1) is <= 1.25 (judgment 2)
    for n in measured:
        if n == 1 or censored_quantile(by[("S1", n)], 0.95) / base <= 1.25:
            return n
    return cand


def judge_e0(rows, T_c=0.33):
    pod = [r for r in rows if r.get("site", "pod") == "pod" and r.get("phase", "closed") == "closed"]
    by = defaultdict(list)
    for r in pod:
        by[(r["size"], r["N"])].append(r["lat"] if r["ok"] else None)
    s1 = [x for (s, _), v in by.items() if s == "S1" for x in v]
    s3 = [x for (s, _), v in by.items() if s == "S3" for x in v]
    L1, L3 = censored_quantile(s1, 0.95), censored_quantile(s3, 0.95)
    fail = sum(x is None for x in s1) / max(1, len(s1))
    L = max(L1, L3)
    if L > 2.0 or fail > 0.02:
        case = "e"
    elif L > 1.0:
        case = "d"
    elif L > T_c:
        case = "c"
    elif L >= T_c / 2:
        case = "b"
    else:
        case = "a"
    slots = defaultdict(list)
    for r in pod:
        if r["size"] == "S1":
            slots[r["slot"]].append(r["lat"] if r["ok"] else None)
    sp = [censored_quantile(v, 0.95) for v in slots.values()]
    worst = max(sp) / L1 if sp and math.isfinite(L1) and L1 > 0 else math.inf
    notes = []
    if worst > 1.3:
        notes.append("block-randomize closed-loop conditions by time slot (judgment 1)")
    size_pen = L3 - L1
    if size_pen > T_c:
        notes.append("H=3 latency penalty (judgment 5)")
    elif size_pen <= 0.05:
        notes.append("ignore latency in H comparison (judgment 5)")
    j4 = judgment4([r["lat"] if r["ok"] else None for r in pod if r["size"] == "S1"], T_c, L1) \
        if math.isfinite(L1) else None
    return {"d_p95_S1": L1, "d_p95_S3": L3, "fail_rate_S1": fail, "case": case, "N_max": _n_max(by, L1, T_c),
            "worst_slot_ratio": worst, "size_penalty_s": size_pen, "notes": notes, "j4": j4}


def votes_per_step(lat, T_c=0.33, lead_max=1.5):
    """Answers for the same step arriving before its boundary (judgment 4, M4 §4.1 H=1 schedule)."""
    sends = np.arange(-lead_max, -lat + 1e-9, T_c)
    return int(sum(1 for s in sends if s + lat <= 0.0))


def step_votes(lats, T_c=0.33, lead_max=1.5, d_hat=0.307) -> list:
    """E §2.6 offline replay of recorded latencies (in record order) through the H = 1 schedule: every step is asked
    at -lead_max, -lead_max + T_c, ... up to -d_hat (step start = 0); an answer counts if it arrives by the start
    (a failure / None never does). One step per consecutive block of asks; returns the votes of each full step."""
    sends = np.arange(-lead_max, -d_hat + 1e-9, T_c)
    n = len(sends)
    if n == 0:
        return []
    out = []
    for i in range(len(lats) // n):
        blk = lats[i * n:(i + 1) * n]
        out.append(int(sum(1 for s, x in zip(sends, blk) if x is not None and math.isfinite(x) and s + x <= 1e-9)))
    return out


def judgment4(lats, T_c=0.33, d_hat=0.307, leads=(1.5, 1.0)) -> dict:
    """E §2.7-4 (:197): median votes per step >= 2 at T_c 0.33, lead_max 1.5 s -> M4 (a) LA-2 can commit; also at
    lead 1.0 s (the runtime default, re-decided from this after E0: canon §75 (1), §76 N3)."""
    out = {"d_hat": d_hat, "T_c": T_c, "rule": "median votes per step >= 2 (E §2.7-4)"}
    for lead in leads:
        v = step_votes(lats, T_c, lead, d_hat)
        med = float(np.median(v)) if v else None
        out[f"lead{lead:.1f}"] ={"median": med, "n_steps": len(v), "la2_possible": med is not None and med >= 2}
    return out


def determinism(answers_by_payload):
    """Judgment 6: share of fixed payloads whose modal answer is not identical across repeats."""
    flips = [len(set(v)) > 1 for v in answers_by_payload.values()]
    return {"flip": sum(flips) / max(1, len(flips))}
