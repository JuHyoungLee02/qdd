"""E-ACC runner (docs/stage3/prereg_eacc.md §4): arms x snapshots -> one JSONL row per call (resumable by
(arm, snap)). Model: qwen (free local vLLM through the production LocalVLMAstra adapter, format screen only), astra
(paid: the production AstraClient, streaming, key read only through that code path; CostLedger with the registered
cap, stop at 80 %), mock (fixed answers, no network). Calls are snapshot-major (every arm of one snapshot before the
next) so a budget stop leaves complete pairs.
Sets (prereg §2.4): paid = the first valid snapshots per kind in plan order (on 10, off_a 7, off_b 7, off_c 6);
sub = the first 3 valid per kind (12, stage P2); screen = every valid snapshot.
usage (pod): python tools/eacc/run_eacc.py --bench B --set paid --arms v1,v2,v2cp --model astra --out O.jsonl \
             --ledger L.jsonl --prices P.json --cap-krw 8000"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arms as A  # noqa: E402
import bench as B  # noqa: E402
import prompt_v2 as P2  # noqa: E402

PAID_N = {"on": 10, "off_a": 7, "off_b": 7, "off_c": 6}
SUB_N = {"on": 3, "off_a": 3, "off_b": 3, "off_c": 3}
MAX_OUT = 1200  # production CoupleParams.max_output_tokens
EST_IN = 3400  # reservation upper bound of input tokens (v2 text ~2.2k + 3 images ~0.6k, margin)


def load_bench(root: str) -> list:
    """Every captured snapshot with checks ok, in plan order: (id, dir, meta)."""
    out = []
    for ep in B.plan():
        d = os.path.join(root, ep["id"])
        p = os.path.join(d, "meta.json")
        if os.path.exists(p):
            m = json.load(open(p))
            if m["checks"]["ok"]:
                out.append((ep["id"], d, m))
    return out


def select(snaps: list, which: str) -> list:
    if which == "screen":
        return list(snaps)
    quota = dict(PAID_N if which == "paid" else SUB_N)
    out = []
    for s in snaps:
        k = s[2]["kind"]
        if quota.get(k, 0) > 0:
            out.append(s)
            quota[k] -= 1
    if any(v > 0 for v in quota.values()):
        raise SystemExit(f"set {which}: not enough valid snapshots, missing {quota}")
    return out


def parse(arm: dict, text: str, cams: list) -> dict:
    """Production parser (v1) or parse_v2, then the production gate (harvest.couple.gate.gate_answer, age 1 s, no T1)
    -> the command the controller would pass on."""
    from harvest.couple import schema as CS
    from harvest.couple.gate import gate_answer
    from harvest.couple.params import CoupleParams
    seg, vu = None, None
    try:
        if arm["base"] == "v1":
            a = CS.parse_answer(text, "F0", cams, 1, 0.0, 1.0)
        else:
            a, seg, vu = P2.parse_v2(text, cams)
    except (CS.SchemaError, P2.V2Error) as e:
        return {"valid": False, "errors": e.problems[:4]}
    raw_cmd = a.command
    dp_raw = None if a.edit is None else [round(float(v), 4) for v in a.edit.dp]
    grip_raw = None if a.edit is None else a.edit.gripper
    a = gate_answer(a, CoupleParams(), {})
    return {"valid": True, "errors": [], "command_raw": raw_cmd, "command": a.command, "gate": a.gate,
            "edit_dp_raw": dp_raw, "edit_gripper_raw": grip_raw,
            "edit_dp": None if a.edit is None else [round(float(v), 4) for v in a.edit.dp],
            "execution": a.execution, "intent": a.intent, "confidence": a.confidence,
            "evidence_views": list(a.evidence_views), "segment": seg, "valid_until": vu}


def client(model: str, url: str, served: str, effort: str):
    if model == "mock":
        from harvest.clients.astra import AstraRecord

        class _Mock:
            def call(self, inp, effort, max_output_tokens, meta):
                txt = ('{"assessment": {"task_progress": {"verified_completed": [], "currently_attempting": "reach", '
                       '"remaining": ["grasp"]}, "execution": "progressing", "intent": "misaligned", "confidence": '
                       '"high", "evidence": "tip left of the mug", "evidence_views": ["cam_head"], "claims": []}, '
                       '"segment": {"now": "approach", "do": "none", "next": "descend"}, "command": "edit", "edit": '
                       '{"delta_position_m": [0.02, -0.02, 0.0], "delta_rotation_rad": [0, 0, 0], "gripper": "keep", '
                       '"valid_until": "next_answer"}, "info_request": "none"}')
                return AstraRecord(http_status=200, usage={"input_tokens": 2500, "output_tokens": 250}, output_text=txt,
                                   effort=effort, model_field="mock", meta=dict(meta), t_send=0.0, t_done=1.0)
        return _Mock()
    if model == "qwen":
        from harvest.couple.local_vlm import LocalVLMAstra
        return LocalVLMAstra(url, served, timeout_s=180.0)
    from harvest.clients.astra import AstraClient
    from harvest.runtime.astra_hb import MODEL
    tok = "/data/.openai_token"
    return AstraClient(open(tok).read().strip(), MODEL, timeout_s=120.0 if effort != "low" else 60.0)


def run(a) -> dict:
    from harvest.couple.cost import CostLedger, PriceTable
    snaps = select(load_bench(a.bench), a.set)
    if a.limit:
        snaps = snaps[:a.limit]
    arms = [A.parse_arm(x) for x in a.arms.split(",")]
    prices = PriceTable.load(a.prices) if a.model == "astra" else PriceTable.free()
    ledger = CostLedger(a.ledger if a.model == "astra" else None, a.cap_krw if a.model == "astra" else 0.0, prices,
                        stop_frac=0.8, run_id=f"eacc_{a.tag}")
    clients = {}
    done = set()
    if os.path.exists(a.out):
        done = {(r["arm"], r["snap"]) for r in map(json.loads, open(a.out))}
    stopped, n = False, 0
    for sid, sd, meta in snaps:
        for arm in arms:
            if (arm["name"], sid) in done:
                continue
            est = prices.krw_upper(EST_IN, MAX_OUT)
            if a.model == "astra" and not ledger.can_send(est):
                stopped = True
                print("BUDGET_STOP " + json.dumps(ledger.state()), flush=True)
                break
            inp, req, pid, text = A.build(sd, meta, arm)
            if a.dump and not os.path.exists(os.path.join(a.dump, f"{arm['name']}.txt")):  # one full prompt per arm
                os.makedirs(a.dump, exist_ok=True)
                with open(os.path.join(a.dump, f"{arm['name']}.txt"), "w") as f:
                    f.write(f"# {sid}\n" + text)
            cams = [c for c in arm["cams"] if c in req["cameras"]]
            if arm["effort"] not in clients:
                clients[arm["effort"]] = client(a.model, a.url, a.served, arm["effort"])
            k = f"{arm['name']}:{sid}"
            ledger.reserve(k, est)
            rec = clients[arm["effort"]].call(inp, arm["effort"], MAX_OUT, {"eacc": a.tag, "arm": arm["name"],
                                                                            "snap": sid})
            cost = ledger.charge(k, rec.usage or None, {"arm": arm["name"], "snap": sid, "error": rec.error,
                                                        "resp_model": rec.model_field}) if a.model == "astra" else 0.0
            row = {"arm": arm["name"], "snap": sid, "kind": meta["kind"], "model": a.model if a.model != "qwen"
                   else a.served, "effort": arm["effort"], "prompt_id": pid, "prompt_sha": hashlib.sha256(
                       text.encode()).hexdigest()[:12], "text_chars": len(text), "raw": (rec.output_text or "")[:3000],
                   "api_error": rec.error, "latency_s": round(rec.t_done - rec.t_send, 3),
                   "first_token_s": round((rec.t_first_token or rec.t_done) - rec.t_send, 3), "usage": rec.usage,
                   "cost_krw": round(cost, 3), "t_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            row.update(parse(arm, rec.output_text or "", cams) if rec.error is None else
                       {"valid": False, "errors": [f"api:{rec.error}"]})
            with open(a.out, "a") as f:
                f.write(json.dumps(row) + "\n")
            n += 1
            print(f"CALL {n} {arm['name']} {sid} valid={row['valid']} cmd={row.get('command')} "
                  f"lat={row['latency_s']} cost={cost:.1f} spent={ledger.spent:.1f}", flush=True)
        if stopped:
            break
    return {"calls": n, "stopped": stopped, "ledger": ledger.state()}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", default="/data/harvest/out/eacc/bench")
    ap.add_argument("--set", default="screen", choices=("screen", "paid", "sub"))
    ap.add_argument("--arms", required=True)
    ap.add_argument("--model", required=True, choices=("qwen", "astra", "mock"))
    ap.add_argument("--url", default="http://127.0.0.1:8381")
    ap.add_argument("--served", default="qwen8b_eacc")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ledger", default="/data/harvest/logs/eacc/astra_ledger.jsonl")
    ap.add_argument("--prices", default="/data/harvest/logs/eacc/prices_2026-09-26.json")
    ap.add_argument("--cap-krw", type=float, default=8000.0)
    ap.add_argument("--tag", default="main")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dump", default="", help="write the first full prompt text of each arm here (eye check)")
    print("END " + json.dumps(run(ap.parse_args(argv))), flush=True)


if __name__ == "__main__":
    main()
