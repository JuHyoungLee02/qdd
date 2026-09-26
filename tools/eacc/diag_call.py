"""One diagnostic Astra call (E-ACC stop investigation): the same request as run_eacc for one (arm, snapshot), streamed,
printing only the SSE event types, the HTTP status and any error / incomplete / failed payload fields (never the key).
usage (pod): python tools/eacc/diag_call.py --bench B --snap on_00 --arm v1"""
from __future__ import annotations

import argparse
import json
import os
import sys

import httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arms as A  # noqa: E402

URL = "https://api.openai.com/v1/responses"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True)
    ap.add_argument("--snap", required=True)
    ap.add_argument("--arm", default="v1")
    a = ap.parse_args(argv)
    from harvest.runtime.astra_hb import MODEL
    sd = os.path.join(a.bench, a.snap)
    meta = json.load(open(os.path.join(sd, "meta.json")))
    inp, _, _, _ = A.build(sd, meta, A.parse_arm(a.arm))
    body = {"model": MODEL, "input": inp, "reasoning": {"effort": "low"}, "max_output_tokens": 1200, "stream": True}
    tok = open("/data/.openai_token").read().strip()
    types = []
    with httpx.Client(timeout=60.0, headers={"Authorization": f"Bearer {tok}"}) as c:
        with c.stream("POST", URL, json=body) as r:
            print("HTTP", r.status_code)
            if r.status_code != 200:
                r.read()
                print("BODY", r.text[:800])
                return
            for line in r.iter_lines():
                if not line.startswith("data:"):
                    continue
                ev = json.loads(line[5:].strip())
                t = ev.get("type")
                if not types or types[-1] != t:
                    types.append(t)
                if t in ("error", "response.failed", "response.incomplete", "response.completed"):
                    resp = ev.get("response") or {}
                    print(t, json.dumps({"error": ev.get("error") or resp.get("error"),
                                         "incomplete": resp.get("incomplete_details"), "status": resp.get("status"),
                                         "usage": resp.get("usage"), "message": ev.get("message"),
                                         "code": ev.get("code")})[:800])
    print("TYPES", types)


if __name__ == "__main__":
    main()
