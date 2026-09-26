"""E-ACC format gate G-fmt (prereg §4.1): per arm invalid rate and the share of v2-only errors (segment /
valid_until) in the Qwen screen rows; also the command and segment answer counts (format sanity, not accuracy).
usage: python tools/eacc/fmt.py rows.jsonl [...]"""
from __future__ import annotations

import json
import sys
from collections import Counter


def gate(rows: list) -> dict:
    by: dict = {}
    for r in rows:
        by.setdefault(r["arm"], []).append(r)
    out = {}
    v1 = by.get("v1", [])
    inv_v1 = sum(not r["valid"] for r in v1) / len(v1) if v1 else 0.0
    for arm, rs in sorted(by.items()):
        n = len(rs)
        inv = sum(not r["valid"] for r in rs) / n
        v2err = sum(any(("segment" in e or "valid_until" in e) for e in r.get("errors", [])) for r in rs) / n
        errs = Counter(e.split(":")[0] for r in rs for e in r.get("errors", []))
        ok = True if arm == "v1" else (inv <= max(0.10, inv_v1 + 0.05) and v2err <= 0.05)
        out[arm] = {"n": n, "invalid": round(inv, 3), "v2_only_err": round(v2err, 3), "pass": ok,
                    "errors": dict(errs.most_common(6)),
                    "commands": dict(Counter(r.get("command_raw") for r in rs if r["valid"])),
                    "seg_now": dict(Counter((r.get("segment") or {}).get("now") for r in rs if r["valid"]))}
    return out


def main(argv=None):
    rows = []
    for p in (argv or sys.argv[1:]):
        rows += [json.loads(x) for x in open(p) if x.strip()]
    res = gate(rows)
    for arm, g in res.items():
        print(arm, json.dumps(g))
    print("G_FMT", "PASS" if all(g["pass"] for g in res.values()) else "FAIL")


if __name__ == "__main__":
    main()
