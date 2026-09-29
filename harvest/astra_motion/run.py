"""E-Astra-motion runner: python -m harvest.astra_motion.run {run|snapshots|grasp|replay} ...

run        (pod, one Isaac process) episodes x modes for one model: none (oracle / nomodel), truth, qwen8b, astra-low,
           astra-high. Budget gate for Astra before each (episode, mode): cum + 1.25 x (mean cost of that model's
           finished episodes of that mode, else EST_KRW) must be <= --cap-krw; the ledger's hard stop (30,000 KRW,
           pre-call, in-flight calls reserved) stops everything.
snapshots  (pod, Isaac) grasp-probe snapshots (grasp_probe.snapshots).
grasp      (no Isaac) ask the grasp question on saved snapshots (grasp_probe.ask), --conds main | high.
replay     (pod, Isaac) open-loop replay of every staggered episode's logged answers through the smooth and the
           immediate executor (harness.replay) -> <episode>/replay.json. No model calls.
Episodes (prereg): 20 DEV seeds, standard variant, interleaved by task so that any prefix stays task-balanced:
  (0 mug_tray), (7 mug_marker), (14 bottle_tray), (1 ...), (8 ...), (15 ...), ... -> 7 / 7 / 6.
Smoke (pipeline check, excluded from results): DEV 25 mug_tray, 26 mug_marker, 27 bottle_tray.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import time

EPISODES = []
for _i in range(7):
    EPISODES += [(_i, "mug_tray"), (7 + _i, "mug_marker")] + ([(14 + _i, "bottle_tray")] if _i < 6 else [])
SMOKE = [(25, "mug_tray"), (26, "mug_marker"), (27, "bottle_tray")]
DEV = range(0, 30)
TOKEN = "/data/.openai_token"
LEDGER = "/data/harvest/logs/astra_motion/cost.jsonl"
OUT_DEFAULT = "/data/harvest/out/astra_motion"
EST_KRW = {("astra-low", "S"): 2600.0, ("astra-low", "S-stream-F0"): 2000.0, ("astra-low", "S-stream-F1"): 2200.0,
           ("astra-high", "S"): 5000.0}


def pick_episodes(spec: str) -> list:
    if spec == "all":
        return list(EPISODES)
    if spec == "smoke":
        return list(SMOKE)
    if spec.startswith("first:"):
        return EPISODES[:int(spec.split(":")[1])]
    out = []
    for part in spec.split(","):
        s, t = part.split(":")
        out.append((int(s), t))
    for s, _ in out:
        if s not in DEV:
            raise SystemExit(f"seed {s}: DEV 0-29 only (never CAL / TEST)")
    return out


def make_model(name: str, qwen_url: str):
    if name in ("none", "truth"):
        return None
    if name.startswith("astra-"):
        from .cost import Ledger
        from .models import AstraModel
        tok = open(TOKEN).read().strip()
        extra = {}
        ap = os.path.join(OUT_DEFAULT, "api_params.json")
        if os.path.exists(ap):  # use the determinism settings the API accepted
            acc = json.load(open(ap))
            extra = {k: v for k, v in (("temperature", 0.0), ("top_p", 1.0), ("seed", 0))
                     if acc.get(k, {}).get("accepted")}
        return AstraModel(tok, name.split("-")[1], Ledger(LEDGER), extra=extra)
    if name == "qwen8b":
        from .models import LocalVLM
        return LocalVLM(qwen_url, "Qwen3-VL-8B-Instruct", "qwen8b")
    raise SystemExit(f"model {name}?")


class _Delayed:
    def __init__(self, m, s):
        self.m, self.s, self.name = m, s, m.name

    def ask(self, text, images, meta):
        time.sleep(self.s)
        return self.m.ask(text, images, meta)


def _mean_cost_krw(out, model, mode):
    from .cost import KRW_PER_USD
    v = [json.load(open(p))["cost_usd"] * KRW_PER_USD for p in glob.glob(os.path.join(out, model, mode, "*",
                                                                                     "result.json"))]
    return sum(v) / len(v) if v else None


def run(a):
    from .cost import BudgetStop, Ledger
    from .harness import run_episode
    from .world_isaac import IsaacWorld
    eps = pick_episodes(a.episodes)
    modes = a.modes.split(",")
    model = make_model(a.model, a.qwen_url)
    world = IsaacWorld()
    video_eps = set(eps[:a.video_first])
    try:
        for ep in eps:
            for m in modes:
                od = os.path.join(a.out, a.model, m, f"s{ep[0]}_{ep[1]}")
                if os.path.exists(os.path.join(od, "result.json")):
                    continue
                if a.model.startswith("astra-"):
                    cum = Ledger(LEDGER).total_krw
                    est = _mean_cost_krw(a.out, a.model, m) or EST_KRW.get((a.model, m), 3000.0)
                    if cum + 1.25 * est > a.cap_krw:
                        print("BUDGET_GATE " + json.dumps({"episode": ep, "mode": m, "cum_krw": round(cum, 1),
                                                           "next_est_krw": round(1.25 * est, 1),
                                                           "cap_krw": a.cap_krw}), flush=True)
                        return
                mdl = model
                if a.model == "truth":
                    from .truth import TruthModel
                    mdl = TruthModel(world, m)
                    if a.truth_latency > 0:  # emulate a model's wall-clock latency (stream smoke)
                        mdl = _Delayed(mdl, a.truth_latency)
                t0 = time.perf_counter()
                res = run_episode(world, m, mdl, ep[0], ep[1], out_dir=od, video=ep in video_eps,
                                  n_sync=a.n_sync)
                print("EP " + json.dumps({k: res.get(k) for k in (
                    "seed", "task", "mode", "model", "success", "grasp_lift", "fail_stage", "end_reason", "n_calls",
                    "n_invalid", "cost_usd", "sim_t", "max_speed", "jerk_rms")} | {
                    "first_close_err_mm": (res.get("first_close") or {}).get("err_mm"),
                    "wall_s": round(time.perf_counter() - t0, 1)}), flush=True)
                if a.model.startswith("astra-") and res["n_calls"]:  # redesign rule (prereg §12): stop, do not spend
                    from .cost import KRW_PER_USD
                    per_call = res["cost_usd"] * KRW_PER_USD / res["n_calls"]
                    stage = [json.load(open(q)) for q in glob.glob(os.path.join(a.out, a.model, m.split("-F")[0] + "*",
                                                                                "*", "result.json"))]
                    inv = sum(r["n_invalid"] for r in stage) / max(sum(r["n_calls"] for r in stage), 1)  # stage level
                    if per_call > a.max_krw_per_call or inv > 0.10:
                        print("REDESIGN_STOP " + json.dumps({"episode": ep, "mode": m, "krw_per_call":
                                                             round(per_call, 1), "invalid_share": round(inv, 3)}),
                              flush=True)
                        return
    except BudgetStop as e:
        print("BUDGET_STOP " + json.dumps({"msg": str(e)}), flush=True)
    print("RUN_DONE", flush=True)


def snapshots(a):
    from .grasp_probe import snapshots as S
    from .world_isaac import IsaacWorld
    S(IsaacWorld(), pick_episodes(a.episodes), a.snaps)
    print("SNAPSHOTS_DONE", flush=True)


def grasp(a):
    from .cost import BudgetStop, Ledger
    from .grasp_probe import CONDS, CONDS_HIGH, ask
    est = {("astra-low", "main"): 3000.0, ("astra-high", "high"): 2500.0}.get((a.model, a.conds), 3000.0)
    if a.model.startswith("astra-") and Ledger(LEDGER).total_krw + 1.25 * est > a.cap_krw:
        print("BUDGET_GATE " + json.dumps({"cum_krw": Ledger(LEDGER).total_krw, "next_est_krw": 1.25 * est,
                                           "cap_krw": a.cap_krw}), flush=True)
        return
    try:
        only = [x.strip() for x in open(a.only)] if a.only else None
        ask(make_model(a.model, a.qwen_url), a.snaps, a.grasp_out, CONDS if a.conds == "main" else CONDS_HIGH, only)
    except BudgetStop as e:
        print("BUDGET_STOP " + json.dumps({"msg": str(e)}), flush=True)
    print("GRASP_DONE", flush=True)


def apiprobe(a):
    from .cost import Ledger
    from .models import api_params_probe
    res = api_params_probe(open(TOKEN).read().strip(), Ledger(LEDGER))
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "api_params.json"), "w") as f:
        json.dump(res, f, indent=1)
    print("APIPROBE " + json.dumps(res), flush=True)


def replay_all(a):
    from .harness import replay
    from .world_isaac import IsaacWorld
    world = IsaacWorld()
    for p in sorted(glob.glob(os.path.join(a.out, a.model, "S-stream-F*", "*", "result.json"))):
        dst = os.path.join(os.path.dirname(p), "replay.json")
        if os.path.exists(dst):
            continue
        res = json.load(open(p))
        out = {ex: replay(world, res, ex) for ex in ("smooth", "immediate")}
        with open(dst, "w") as f:
            json.dump(out, f)
        print("REPLAY " + json.dumps({"ep": p, **{ex: {k: v for k, v in r.items() if k != "tcp_path"}
                                                 for ex, r in out.items()}}), flush=True)
    print("REPLAY_DONE", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "snapshots", "grasp", "replay", "apiprobe"])
    ap.add_argument("--out", default="/data/harvest/out/astra_motion")
    ap.add_argument("--model", default="none", help="none | truth | qwen8b | astra-low | astra-high")
    ap.add_argument("--modes", default="oracle,nomodel")
    ap.add_argument("--episodes", default="all", help="all | smoke | first:K | seed:task,...")
    ap.add_argument("--video-first", type=int, default=3)
    ap.add_argument("--n-sync", type=int, default=30)
    ap.add_argument("--cap-krw", type=float, default=30000.0)
    ap.add_argument("--qwen-url", default="http://127.0.0.1:8341")
    ap.add_argument("--snaps", default="/data/harvest/out/astra_motion/grasp_snaps")
    ap.add_argument("--grasp-out", default="/data/harvest/out/astra_motion/grasp_answers.jsonl")
    ap.add_argument("--conds", default="main", choices=["main", "high"])
    ap.add_argument("--truth-latency", type=float, default=0.0)
    ap.add_argument("--max-krw-per-call", type=float, default=100.0)
    ap.add_argument("--only", default=None, help="grasp: file with snapshot keys to ask (targeted G2)")
    a = ap.parse_args(argv)
    code = 0
    try:
        {"run": run, "snapshots": snapshots, "grasp": grasp, "replay": replay_all, "apiprobe": apiprobe}[a.cmd](a)
    except BaseException:  # noqa: BLE001 - print, then leave without SimulationApp.close()
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)  # SimulationApp.close() hangs in this chroot; results are already flushed


if __name__ == "__main__":
    main()
