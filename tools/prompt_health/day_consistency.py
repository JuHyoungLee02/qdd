"""Same-prompt consistency across sessions: today's base answers (run_dyn / astra_spot JSONL, test grasp, variant base)
against the probe's G1 v2 answers on the same snapshots (grasp_answers_v2.jsonl, views all3, no overlay, same model).
usage: python tools/prompt_health/day_consistency.py today.jsonl g1v2.jsonl <model label today> <model label g1>"""
from __future__ import annotations

import json
import sys


def compare(today_rows, g1_rows, m_today: str, m_g1: str) -> dict:
    a = {r["snap"]: r.get("grasp_state") for r in today_rows
         if r["test"] == "grasp" and r["variant"] == "base" and not r.get("temp") and r["rep"] == 0
         and r["model"] == m_today and r.get("valid")}
    b = {r["snap"]: (r.get("answer") or {}).get("grasp_state") for r in g1_rows
         if r["views"] == "all3" and not r["overlay"] and r["rep"] == 0 and r["model"] == m_g1 and r["valid"]}
    common = sorted(set(a) & set(b))
    return {"model_today": m_today, "model_g1": m_g1, "pairs": len(common), "same": sum(a[s] == b[s] for s in common),
            "differ": [[s, b[s], a[s]] for s in common if a[s] != b[s]]}


def main():
    today, g1, m_today, m_g1 = sys.argv[1:5]
    print(json.dumps(compare(list(map(json.loads, open(today))), list(map(json.loads, open(g1))), m_today, m_g1)))


if __name__ == "__main__":
    main()
