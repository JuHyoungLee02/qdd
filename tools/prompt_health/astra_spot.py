"""Paid Astra spot check of the prompt health check (pre-registration docs/stage3/prereg_prompt_health_astra.md; cap
3,000 KRW, stop at 80 %). Two questions the free Qwen tests cannot settle:
  Q1 frame  -- R-set approach snapshots (run_dyn.frame_rows, first n): the couple-wording direction question with the
               production head overlay, without (prod_ov) / with (frame_ov) the verbal axis definition. Production
               client and image form (clients.astra.AstraClient, JPEG, 'cam:' labels, no detail field).
  Q2 grasp  -- G1 v2 snapshots (first n_neg not held + first n_pos held): the probe grasp question (all three cameras,
               no overlay) base again vs para3 (question first), in the G1 v2 form (PNG, detail high, 'Image i:').
One CostLedger (harvest/couple/cost.py) shared by both; the key file is read only through the existing code path
(harvest.eval.couple.stream_client). Q1 runs first; within each question the two arms alternate per snapshot so a
budget stop leaves complete pairs.
usage (pod): python tools/prompt_health/astra_spot.py --prices P.json --ledger L.jsonl --out O.jsonl [--mock]"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_dyn as RD  # noqa: E402
import variants as V  # noqa: E402

from harvest.astra_motion import prompts as PR  # noqa: E402
from harvest.couple.cost import CostLedger, PriceTable  # noqa: E402

MAX_OUT = 1200  # production CoupleParams.max_output_tokens
EST_IN = {"frame": 1200, "grasp": 1100}  # reservation upper bounds (probe G1 v2: ~892 input tokens with 3 images)


def frame_input(r: dict, variant: str) -> list:
    text = V.frame_prompt(variant, r["instruction"], RD.TGT_NAME[r["task"]])
    content = [{"type": "input_text", "text": text}]
    for c in ("cam_head", "cam_wrist_right"):
        b = RD.r_head_overlay(r) if (c == "cam_head" and variant.endswith("_ov")) else RD.r_image(r, c)
        content.append({"type": "input_text", "text": f"{c}:"})
        content.append({"type": "input_image", "image_url": "data:image/jpeg;base64," + base64.b64encode(b).decode()})
    return [{"role": "user", "content": content}]


def grasp_input(sd: str, meta: dict, variant: str) -> list:
    text, order = V.grasp_prompt(variant, PR.OBJ_NAME[meta["gt"]["tgt"]])
    content = [{"type": "input_text", "text": text}]
    for i, k in enumerate(order):
        png = RD.g_png(sd, k)
        content.append({"type": "input_text", "text": f"Image {i + 1}: {RD.G_LABEL[k]}"})
        content.append({"type": "input_image", "image_url": "data:image/png;base64," + base64.b64encode(png).decode(),
                        "detail": "high"})
    return [{"role": "user", "content": content}]


def plan(n_frame: int, n_neg: int, n_pos: int) -> list:
    items = []
    for r in RD.frame_rows(RD.r_rows(), 60)[:n_frame]:
        for v in ("prod_ov", "frame_ov"):
            items.append(("frame", r["id"], v, r))
    snaps = RD.g_snaps()
    neg = [s for s in snaps if not s[2]["gt"]["holding"]][:n_neg]
    pos = [s for s in snaps if s[2]["gt"]["holding"]][:n_pos]
    for key, sd, meta in sorted(neg + pos):
        for v in ("base", "para3"):
            items.append(("grasp", key, v, (sd, meta)))
    return items


def client(mock: bool):
    if mock:
        from harvest.clients.astra import AstraRecord

        class _Mock:  # fixed answer and usage, no network
            def call(self, inp, effort, max_output_tokens, meta):
                return AstraRecord(http_status=200, usage={"input_tokens": 900, "output_tokens": 80},
                                   output_text='{"delta_position_m": [0.03, 0.0, -0.02]}', effort=effort,
                                   model_field="mock", meta=dict(meta))
        return _Mock()
    from harvest.eval.couple import stream_client
    c, kind = stream_client({"astra": "api"})
    assert kind == "api"
    return c


def run(a) -> dict:
    prices = PriceTable.load(a.prices)
    ledger = CostLedger(a.ledger, a.cap_krw, prices, stop_frac=0.8, run_id="prompt_health_astra")
    c = client(a.mock)
    done = set()
    if os.path.exists(a.out):
        done = {(r["test"], r["snap"], r["variant"]) for r in map(json.loads, open(a.out))}
    stopped = False
    for i, (test, key, variant, obj) in enumerate(plan(a.n_frame, a.n_neg, a.n_pos)):
        if (test, key, variant) in done:
            continue
        est = prices.krw_upper(EST_IN[test], MAX_OUT)
        if not ledger.can_send(est):
            stopped = True
            print("BUDGET_STOP " + json.dumps(ledger.state()), flush=True)
            break
        inp = frame_input(obj, variant) if test == "frame" else grasp_input(*obj, variant)
        k = f"{test}:{key}:{variant}"
        ledger.reserve(k, est)
        rec = c.call(inp, "low", MAX_OUT, {"prompt_health": test, "snap": key, "variant": variant})
        cost = ledger.charge(k, rec.usage or None, {"snap": key, "variant": variant, "error": rec.error,
                                                    "resp_model": rec.model_field})
        row = {"test": test, "snap": key, "variant": variant, "temp": None, "rep": 0, "model": "astra-low",
               "prompt_sha": V.sha12(inp[0]["content"][0]["text"]), "raw": (rec.output_text or "")[:1500],
               "api_error": rec.error, "latency_s": round(rec.t_done - rec.t_send, 3), "usage": rec.usage,
               "cost_krw": round(cost, 3)}
        if test == "frame":
            r = obj
            row.update(truth=[round(float(r["reg"][f"g2tgt_d{x}"]), 4) for x in "xyz"], state=r["phase"],
                       **RD.parse_frame(rec.output_text or ""))
        else:
            sd, meta = obj
            row.update(truth=meta["gt"]["holding"], state=meta["gt"]["state"], **RD.parse_grasp(rec.output_text or ""))
        with open(a.out, "a") as f:
            f.write(json.dumps(row) + "\n")
        print(f"CALL {i} {test} {key} {variant} cost {cost:.2f} spent {ledger.spent:.1f}", flush=True)
    return {"stopped": stopped, "ledger": ledger.state()}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--prices", required=True)
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cap-krw", type=float, default=3000.0)
    ap.add_argument("--n-frame", type=int, default=30)
    ap.add_argument("--n-neg", type=int, default=15)
    ap.add_argument("--n-pos", type=int, default=15)
    ap.add_argument("--mock", action="store_true")
    print("END " + json.dumps(run(ap.parse_args(argv))), flush=True)


if __name__ == "__main__":
    main()
