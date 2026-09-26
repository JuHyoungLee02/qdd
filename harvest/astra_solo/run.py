"""Astra-solo runner: python -m harvest.astra_solo.run {run|reask|summary} ...

run      (pod, one Isaac process = one scene variant) --model truth | qwen8b | astra-low | astra-medium, --variant
         standard | dr, --seeds 0,1,2 (DEV 0-19 only). Paid models: before each episode the budget gate
         cum + 1.25 x (mean KRW of this model's finished episodes, else --est-krw) <= --cap-krw; the ledger's hard stop
         (pre-call, in-flight reserved) = --cap-krw; after each episode the redesign stop (prereg §5): invalid share
         of the stage > 10 % or KRW per call > 2 x the estimate.
reask    (no Isaac) re-send saved first-attempt inputs of scored calls to --model (paired effort comparison).
summary  (no Isaac) print summarize() of every result.json under --out/<model>.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import time

TOKEN = "/data/.openai_token"
OUT = "/data/harvest/out/astra_solo"
LEDGER = "/data/harvest/logs/astra_solo/ledger.jsonl"


def seeds_of(spec: str) -> list:
    s = [int(x) for x in spec.split(",") if x.strip()]
    if any(not 0 <= v <= 19 for v in s):
        raise SystemExit("DEV layout seeds 0-19 only (never CAL / TEST)")
    return s


def make_model(name: str, a):
    if name == "truth":
        return None
    if name.startswith("astra-"):
        from ..astra_motion.cost import Ledger
        from .models import SoloAstra
        return SoloAstra(open(TOKEN).read().strip(), name.split("-", 1)[1], Ledger(a.ledger, hard_krw=a.cap_krw))
    if name == "qwen8b":
        from .models import LocalVLM
        return LocalVLM(a.qwen_url, a.qwen_name, "qwen8b")
    raise SystemExit(f"model {name}?")


def _results(out, model):
    return [json.load(open(p)) for p in sorted(glob.glob(os.path.join(out, model, "*", "s*", "result.json")))]


def run(a):
    from ..astra_motion.cost import BudgetStop, Ledger
    from .episode import ApiStop, run_episode
    from .truth import SoloTruth
    from .world import SoloWorld
    model = make_model(a.model, a)
    world = SoloWorld(a.variant)
    paid = a.model.startswith("astra-")
    for k, s in enumerate(seeds_of(a.seeds)):
        od = os.path.join(a.out, a.model, a.variant, f"s{s}")
        if os.path.exists(os.path.join(od, "result.json")):
            continue
        if paid:
            done = _results(a.out, a.model)
            cum = Ledger(a.ledger).total_krw
            est = (sum(r["cost_krw"] for r in done) / len(done)) if done else a.est_krw
            if cum + 1.25 * est > a.cap_krw:
                print("BUDGET_GATE " + json.dumps({"seed": s, "cum_krw": round(cum, 1), "next": round(1.25 * est, 1),
                                                   "cap_krw": a.cap_krw}), flush=True)
                return
        mdl = SoloTruth(world) if a.model == "truth" else model
        t0 = time.perf_counter()
        try:
            res = run_episode(world, mdl, s, "mug_tray", out_dir=od, max_calls=a.max_calls,
                              motion_limit_s=a.motion_limit, video=k < a.video_first, variant=a.variant,
                              stop_calls=a.stop_calls, stop_motion_s=a.stop_motion)
        except BudgetStop as e:
            print("BUDGET_STOP " + json.dumps({"msg": str(e)}), flush=True)
            return
        except ApiStop as e:  # quota / repeated empty answers: stop everything; the episode is rerun later
            p = os.path.join(od, "result.json")
            if os.path.exists(p):
                os.replace(p, os.path.join(od, f"result_api_stop_{int(time.time())}.json"))
            print("API_STOP " + json.dumps({"seed": s, "variant": a.variant, "msg": str(e)[:300]}), flush=True)
            return
        print("EP " + json.dumps({k2: res.get(k2) for k2 in (
            "seed", "variant", "model", "success", "grasp_lift", "fail_stage", "end_reason", "n_calls", "n_invalid",
            "cost_krw", "t_success", "sim_t", "wall_s", "n_clipped", "n_blocked")} | {
            "first_close_xy_mm": (res.get("first_close") or {}).get("err_xy_mm"),
            "wall_total_s": round(time.perf_counter() - t0, 1)}), flush=True)
        if paid and res["n_calls"]:
            stage = _results(a.out, a.model)
            inv = sum(r["n_invalid"] for r in stage) / max(sum(r["n_calls"] for r in stage), 1)
            per_call = res["cost_krw"] / res["n_calls"]
            if inv > 0.10 or per_call > 2 * a.est_krw_per_call:
                print("REDESIGN_STOP " + json.dumps({"seed": s, "invalid_share": round(inv, 3),
                                                     "krw_per_call": round(per_call, 1)}), flush=True)
                return
    print("RUN_DONE", flush=True)


def reask_cmd(a):
    from ..astra_motion.cost import BudgetStop
    from .reask import episode_dirs, reask
    eps = episode_dirs(os.path.join(a.out, a.src_model))
    model = make_model(a.model, a)
    os.makedirs(os.path.dirname(os.path.abspath(a.reask_out)), exist_ok=True)
    try:
        rows = reask(eps, model, a.max_reask, a.reask_out)
        print("REASK_DONE " + json.dumps({"n": len(rows)}), flush=True)
    except BudgetStop as e:
        print("BUDGET_STOP " + json.dumps({"msg": str(e)}), flush=True)


def summary_cmd(a):
    from .analyze import summarize
    rs = _results(a.out, a.model)
    by = {}
    for r in rs:
        by.setdefault(r["variant"], []).append(r)
    print(json.dumps({"all": summarize(rs), **{v: summarize(x) for v, x in by.items()}}, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "reask", "summary"])
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--model", default="truth")
    ap.add_argument("--variant", default="standard", choices=["standard", "dr"])
    ap.add_argument("--seeds", default="0")
    ap.add_argument("--max-calls", type=int, default=40)
    ap.add_argument("--motion-limit", type=float, default=180.0)
    ap.add_argument("--stop-calls", type=int, default=None, help="runner-side early end (prompt unchanged)")
    ap.add_argument("--stop-motion", type=float, default=None, help="runner-side early end, motion s")
    ap.add_argument("--video-first", type=int, default=1)
    ap.add_argument("--cap-krw", type=float, default=5000.0)
    ap.add_argument("--ledger", default=LEDGER)
    ap.add_argument("--est-krw", type=float, default=900.0)
    ap.add_argument("--est-krw-per-call", type=float, default=60.0)
    ap.add_argument("--qwen-url", default="http://127.0.0.1:8391")
    ap.add_argument("--qwen-name", default="qwen8b_solo")
    ap.add_argument("--src-model", default="astra-low")
    ap.add_argument("--max-reask", type=int, default=12)
    ap.add_argument("--reask-out", default="/data/harvest/out/astra_solo/reask.jsonl")
    a = ap.parse_args(argv)
    code = 0
    try:
        {"run": run, "reask": reask_cmd, "summary": summary_cmd}[a.cmd](a)
    except BaseException:  # noqa: BLE001 - print, then leave without SimulationApp.close()
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)  # SimulationApp.close() hangs in this chroot (probe run.py); results are already flushed


if __name__ == "__main__":
    main()
