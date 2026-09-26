"""Prereg change 3 (a): start a new E-ACC ledger with one carry-over row = the billed ('charge' with usage) rows of
the old ledger; the unbilled no_usage reservations of the credit-exhausted run are not carried.
usage: python tools/eacc/carry.py OLD.jsonl NEW.jsonl"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys


def carry(old: str, new: str) -> dict:
    rows = [json.loads(x) for x in open(old) if x.strip()]
    billed = [r for r in rows if r.get("kind") == "charge" and (r.get("usage") or {}).get("output_tokens")]
    tot = round(sum(float(r["cost_krw"]) for r in billed), 4)
    if os.path.exists(new):
        raise SystemExit(f"{new} exists")
    row = {"t_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "run_id": "eacc_carry",
           "model": rows[0].get("model"), "price_date": rows[0].get("price_date"), "budget_krw": 8000.0,
           "key": "carry:eacc_p1", "kind": "carry", "cost_krw": tot, "usage": {},
           "note": f"billed rows of {os.path.basename(old)}: {len(billed)} (no_usage rows not carried: "
                   f"{sum(r.get('kind') == 'no_usage' for r in rows)})"}
    with open(new, "w") as f:
        f.write(json.dumps(row) + "\n")
    return row


if __name__ == "__main__":
    print(json.dumps(carry(sys.argv[1], sys.argv[2])))
