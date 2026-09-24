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
    for n in measured:
        if n == 1 or censored_quantile(by[("S1", n)], 0.95) / base <= 1.25:
            return n if n < cand or ("S1", cand) in by else cand
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
    return {"d_p95_S1": L1, "d_p95_S3": L3, "fail_rate_S1": fail, "case": case, "N_max": _n_max(by, L1, T_c),
            "worst_slot_ratio": worst, "size_penalty_s": size_pen, "notes": notes}


def votes_per_step(lat, T_c=0.33, lead_max=1.5):
    """Answers for the same step arriving before its boundary (judgment 4, M4 §4.1 H=1 schedule)."""
    sends = np.arange(-lead_max, -lat + 1e-9, T_c)
    return int(sum(1 for s in sends if s + lat <= 0.0))


def determinism(answers_by_payload):
    """Judgment 6: share of fixed payloads whose modal answer is not identical across repeats."""
    flips = [len(set(v)) > 1 for v in answers_by_payload.values()]
    return {"flip": sum(flips) / max(1, len(flips))}
