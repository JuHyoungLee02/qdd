"""E-CL15c dry run without Isaac / GPU / network (stub Responses-API stream): the Astra drop-in answers, the
ledger gets latency / tokens / cost rows, the budget gate and the hard stop write the stop file. Temp files only.
usage: PYTHONPATH=<code> python tools/cl15/stub_test.py"""
from __future__ import annotations

import io
import json
import os
import tempfile


def main():
    from PIL import Image

    from harvest.astra_motion.cost import BudgetStop
    from harvest.cl15 import run_t1 as T
    d = tempfile.mkdtemp(prefix="cl15c_stub_", dir="/data/harvest/out/cl15c" if os.path.isdir("/data/harvest/out/cl15c")
                         else None)
    led, stop = os.path.join(d, "ledger.jsonl"), os.path.join(d, "STOP")
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), (120, 120, 120)).save(buf, "PNG")
    make = T.astra_factory("low", led, 10000.0, stop, "eps_test.json", stub=True)
    m = make("http://ignored", "ignored", "qwen8b")
    r = m.ask("stub prompt", [("head", buf.getvalue())], {"call": 0})
    rows = [json.loads(x) for x in open(led)]
    ok1 = r.error is None and json.loads(r.text)["command"]["mode"] == "point" and len(rows) == 1 and \
        rows[0]["usage"]["output_tokens"] == 1500 and rows[0]["meta"]["cl15"] == "eps_test.json" and \
        rows[0]["cost_krw"] > 0 and "latency_s" in rows[0]
    # hard stop: a cap below one call's maximum -> BudgetStop + stop file
    make2 = T.astra_factory("low", os.path.join(d, "ledger2.jsonl"), 100.0, stop, "eps_test.json", stub=True)
    try:
        make2().ask("x", [], {})
        ok2 = False
    except BudgetStop:
        ok2 = os.path.exists(stop)
    # gate: cum + 1.25 x mean episode cost vs cap
    ok3 = T.budget_gate(led, 10000.0, 2500.0) is None and T.budget_gate(led, rows[0]["cost_krw"] * 1.5, 2500.0)
    print(json.dumps({"answer_and_ledger": ok1, "hard_stop": ok2, "gate": bool(ok3), "call_krw": rows[0]["cost_krw"],
                      "dir": d}))
    assert ok1 and ok2 and ok3


if __name__ == "__main__":
    main()
