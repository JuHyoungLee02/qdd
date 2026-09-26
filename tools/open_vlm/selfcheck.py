"""Self-check after the first calls (prereg_open_vlm_solo.md §2): ledger rows of one model (model field, errors, KRW
per call, tokens, latency) and the saved replies of that model's first episode (valid?, command).
usage: python selfcheck.py [n] [api model] [out dir]"""
import glob
import json
import os
import sys

n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
model = sys.argv[2] if len(sys.argv) > 2 else "gpt-5.2-2025-12-11"
out = sys.argv[3] if len(sys.argv) > 3 else "/data/harvest/out/open_vlm_proxy"
L = "/data/harvest/logs/open_vlm_proxy/ledger.jsonl"
allrows = [json.loads(x) for x in open(L) if x.strip()]
rows = [r for r in allrows if r["model"] == model][:n]
for r in rows:
    u = r.get("usage") or {}
    print("LEDGER", r["utc"], r["model"], r.get("model_field"), "err", r.get("error"), "krw", r["cost_krw"],
          "in", u.get("input_tokens"), "out", u.get("output_tokens"),
          "reason", (u.get("output_tokens_details") or {}).get("reasoning_tokens"), "lat", r.get("latency_s"))
print("MODEL_KRW", round(sum(r["cost_krw"] for r in rows), 2), "LEDGER_TOTAL_KRW",
      round(sum(r["cost_krw"] for r in allrows), 2))
for d in sorted(glob.glob(os.path.join(out, "proxy-low/standard/s0/calls/c*")))[:n]:
    fs = sorted(os.listdir(d))
    rep = [f for f in fs if f.startswith("reply")]
    txt = open(os.path.join(d, rep[0])).read() if rep else ""
    print("CALL", d.split("proxy-low/")[1], fs)
    print("  REPLY", txt[:700].replace("\n", " "))
