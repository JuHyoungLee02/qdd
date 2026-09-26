"""Self-check after the first calls (prereg_open_vlm_solo.md §2): ledger rows (model field, errors, KRW per call,
tokens, latency) and the saved replies of the running episode (valid?, command). usage: python selfcheck.py [n]"""
import glob
import json
import os
import sys

n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
L = "/data/harvest/logs/open_vlm_proxy/ledger.jsonl"
rows = [json.loads(x) for x in open(L) if x.strip()][:n]
for r in rows:
    u = r.get("usage") or {}
    print("LEDGER", r["utc"], r["model"], r.get("model_field"), "err", r.get("error"), "krw", r["cost_krw"],
          "in", u.get("input_tokens"), "out", u.get("output_tokens"),
          "reason", (u.get("output_tokens_details") or {}).get("reasoning_tokens"), "lat", r.get("latency_s"))
print("TOTAL_KRW", round(sum(r["cost_krw"] for r in rows), 2))
for d in sorted(glob.glob("/data/harvest/out/open_vlm_proxy/proxy-low/*/s*/calls/c*"))[:n]:
    fs = sorted(os.listdir(d))
    rep = [f for f in fs if f.startswith("reply")]
    txt = open(os.path.join(d, rep[0])).read() if rep else ""
    print("CALL", d.split("proxy-low/")[1], fs)
    print("  REPLY", txt[:700].replace("\n", " "))
