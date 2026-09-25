"""Closed-loop batch evaluation through the R5 runtime (canon §42 Inspect Robots, §45, §58; M4 §5) -- one command.

  python -m harvest.eval.closed --model <merged | adapter | zero-shot | mock> --out DIR [--backend modular|fused] \
      [--split dev] [--seeds 0-4] [--variants standard[,random,dr]] [--conditions C5[,C2,...]] [--m4-h 3|1] \
      [--clock simlat] [--max-seconds 60] [--epochs 1] [--astra mock|api|auto|none] [--isaac-gpu 1] [--gpu 3] \
      [--calibration FILE --j5-alpha 0.1] [--layout auto|H|HW] [--hb-n 5 | --hb-n 0,5,10,20]

The outer process (plain python on the pod) serves the model -- vLLM (canon §59 flags, lead) for the modular Jev-L,
runtime.fused_model (HF) for a stage-B checkpoint (see Backends below), nothing for mock -- then runs
one Isaac worker per scene variant (the aiworker embodiment is one variant per process) through tools/ir/ir_run.sh
(IR_ROOT=cyclo, CUDA_VISIBLE_DEVICES = --isaac-gpu, never GPU 2). Each worker builds the embodiment once and calls
Inspect Robots eval() once per M4 condition (conditions.py C0-C6) over all seeds x epochs: DefaultController(1),
OursPolicy, clock simlat (latency-faithful track) or sync, logging per §42 (policy_config = RuntimeConfig, per-trial
sidecar JSONL + frames + summary in trial_metadata). The outer aggregates success rate (seed-cluster bootstrap),
time to success, decision latency p50/p95, commit ratio, calls, blocked time, RTF, Astra calls, C0 stop ticks, J5
counts, the paired condition differences (C5 - Cx per variant) and the closed-loop RD = 1 - SR_variant / SR_standard
(paired by layout seed; the bootstrap resamples layout seeds with all their epochs, EVAL §4.2, canon §72). Output <out>/closed.json + closed.md + <out>/<variant>/<condition>/ (IR logs).
Backends: modular = Jev-L selector (vLLM) or the mock code rule; fused = MockFusedModel (--model mock_fused) or a REAL
stage-B checkpoint dir (stageb.json + adapter/): the outer process serves it with runtime.fused_model (HF shared-prefix
decide + verification head + CUDA-graph expert chunk) on --gpu, the Isaac worker talks to it over HTTP (FusedClient).
--verify-cal = the verification head's temperature / conformal / critic file (runtime.measure), default uncalibrated.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections import defaultdict

import numpy as np

from ..analysis.stats import N_BOOT

IR_DIR = "/data/harvest/ir"
ISAAC_GPUS = ("0", "1")  # renders only on GPU 0 / 1 (GPU 2 DEVICE_LOST when rendering, memory rule)


# ------------------------------------------------------------------------------------------ aggregation (pure)
def _mci(by_seed: dict, n_boot: int, seed: int = 0) -> dict:
    from ..analysis.stats import cluster_mean_ci
    vals = [x for v in by_seed.values() for x in v]
    if not vals:
        return {"mean": None, "ci": [None, None], "n": 0}
    lo, hi = cluster_mean_ci(by_seed, n=n_boot, seed=seed)
    return {"mean": round(float(np.mean(vals)), 4), "ci": [round(lo, 4), round(hi, 4)], "n": len(vals)}


def _med(xs):
    xs = [x for x in xs if x is not None]
    return {"median": round(float(np.median(xs)), 4) if xs else None, "n": len(xs)}


BOOT_UNIT = "layout seed (all epochs of a seed resampled together; variants / conditions paired by seed)"


def aggregate(trials, n_boot: int = N_BOOT) -> dict:
    """trials: [{variant, condition, seed, epoch, success, sim_time, termination, summary}]."""
    cells = defaultdict(list)
    for t in trials:
        cells[(t["condition"], t["variant"])].append(t)
    from .common import bootstrap_meta
    out = {"cells": {}, "condition_diff": {}, "rd": {}, "bootstrap": bootstrap_meta(n_boot, BOOT_UNIT)}
    for (c, v), ts in sorted(cells.items()):
        S = [t["summary"] or {} for t in ts]
        by = defaultdict(list)
        for t in ts:
            by[t["seed"]].append(int(bool(t["success"])))
        out["cells"][f"{c}/{v}"] = {
            "n": len(ts), "success": _mci(by, n_boot),
            "time_to_success_s": _med([t["sim_time"] for t in ts if t["success"]]),
            "terminations": {k: sum(1 for t in ts if t["termination"] == k) for k in {t["termination"] for t in ts}},
            "latency_p50_s": _med([(s.get("latency_s") or {}).get("p50") for s in S]),
            "latency_p95_s": _med([(s.get("latency_s") or {}).get("p95") for s in S]),
            "commit_ratio": {"mean": round(float(np.mean([s["commit_ratio_mean"] for s in S
                                                          if s.get("commit_ratio_mean") is not None])), 4)
                             if any(s.get("commit_ratio_mean") is not None for s in S) else None},
            "calls": sum(s.get("calls_delivered", 0) for s in S), "call_errors": sum(s.get("call_errors", 0) for s in S),
            "decisions_per_sim_s": _med([s.get("decisions_per_sim_s") for s in S]),
            "blocked_s": _med([s.get("blocked_s") for s in S]), "rtf": _med([s.get("rtf_env") for s in S]),
            "epochs_m4": _med([(s.get("m4") or {}).get("epoch") for s in S]),
            "astra_calls": sum(s.get("astra_calls", 0) for s in S),
            "stop_ticks": sum(s.get("stop_ticks", 0) or 0 for s in S),
            "j5": [s.get("j5") for s in S if s.get("j5")] or None}
    succ = {(t["condition"], t["variant"], t["seed"], t["epoch"]): int(bool(t["success"])) for t in trials}
    conds = sorted({t["condition"] for t in trials})
    variants = sorted({t["variant"] for t in trials})
    for v in variants:  # paired condition differences (same seed and epoch)
        for c in conds:
            if c == "C5" or "C5" not in conds:
                continue
            by = defaultdict(list)
            for (cc, vv, s, e), ok in succ.items():
                if cc == "C5" and vv == v and (c, v, s, e) in succ:
                    by[s].append(ok - succ[(c, v, s, e)])
            if by:
                d = _mci(by, n_boot)
                out["condition_diff"][f"C5-{c}/{v}"] = {**d, "n_pairs": d["n"]}
    if "standard" in variants:
        for c in conds:
            for v in variants:
                if v == "standard":
                    continue
                pairs = [(succ[(c, "standard", s, e)], ok) for (cc, vv, s, e), ok in succ.items()
                         if cc == c and vv == v and (c, "standard", s, e) in succ]
                if not pairs:
                    continue
                a = np.array(pairs, float)
                sr_s, sr_v = float(a[:, 0].mean()), float(a[:, 1].mean())
                ps = defaultdict(lambda: [0.0, 0.0])  # layout seed -> [std successes, variant successes]
                for (cc, vv, s, e), ok in succ.items():
                    if cc == c and vv == v and (c, "standard", s, e) in succ:
                        ps[s][0] += succ[(c, "standard", s, e)]
                        ps[s][1] += ok
                sums = np.array([ps[s] for s in sorted(ps)])
                rng = np.random.default_rng(0)
                boots = []
                for _ in range(n_boot):  # EVAL §4.2: resample the layout (seed) pairs, epochs stay with their seed
                    b = sums[rng.integers(0, len(sums), len(sums))].sum(axis=0)
                    if b[0] > 0:
                        boots.append(1 - b[1] / b[0])
                by = defaultdict(list)
                for (cc, vv, s, e), ok in succ.items():
                    if cc == c and vv == v and (c, "standard", s, e) in succ:
                        by[s].append(succ[(c, "standard", s, e)] - ok)
                out["rd"][f"{c}/{v}"] = {
                    "sr_std": round(sr_s, 4), "sr_var": round(sr_v, 4),
                    "rd": round(1 - sr_v / sr_s, 4) if sr_s > 0 else None,
                    "rd_ci": [round(float(np.quantile(boots, 0.025)), 4), round(float(np.quantile(boots, 0.975)), 4)]
                    if boots else [None, None],
                    "sr_diff": _mci(by, n_boot), "n_pairs": len(pairs), "n_seeds": len(ps)}
    return out


def run_labels(conds, hbs, modes=("K2",)) -> list:
    """(condition, heartbeat N s, cell label[, cadence]): the label carries |hbN only when N is swept (E-M8c K2-N,
    canon §45) and |K<m> only when the cadence is swept (K0-K4, runtime/astra_hb.py). N only matters for K2."""
    out = []
    for c in conds:
        for m in modes:
            for h in (hbs if m == "K2" else hbs[:1]):
                lab = c + (f"|{m}" if len(modes) > 1 else "") + (f"|hb{float(h):g}" if len(hbs) > 1 and m == "K2"
                                                                else "")
                out.append((c, float(h), lab) if tuple(modes) == ("K2",) else (c, float(h), lab, m))
    return out


# ------------------------------------------------------------------------------------------ worker launch
def m4_config(cond: str, H: int = 3) -> dict:
    """RuntimeConfig.m4 of one condition: M4Params defaults + the condition's overrides + the horizon H (decision
    steps per call; E §4.12 / M4 §4.4 "H 1과 3 비교", --m4-h, default 3 = M4Params.H)."""
    from dataclasses import asdict

    from ..runtime.conditions import condition
    from ..runtime.m4 import M4Params
    if int(H) < 1:
        raise ValueError(f"M4 H = {H}: decision steps per call must be >= 1")
    return {**asdict(M4Params()), **condition(cond)[0], "H": int(H)}


def worker_cmd(code: str, spec_path: str, gpu: str, inst: str, timeout_s: int) -> list:
    if str(gpu) not in ISAAC_GPUS:
        raise ValueError(f"Isaac GPU {gpu!r}: renders only on {ISAAC_GPUS} (GPU 2 never renders)")
    q = "/data/harvest"
    envs = [f"HOME={q}/home", f"TMPDIR={q}/tmp", f"XDG_CACHE_HOME={q}/cache", f"HF_HOME={q}/cache/hf",
            f"TORCH_HOME={q}/cache/torch", f"PIP_CACHE_DIR={q}/cache/pip", f"WARP_CACHE_PATH={q}/cache/warp",
            f"PYTHONPYCACHEPREFIX={q}/cache/pyc_r6", f"PYTHONPATH={code}:{q}/ir/pylib:{q}/ir/src/src"]
    if os.environ.get("HARVEST_ALLOW_SPLIT"):
        envs.append(f"HARVEST_ALLOW_SPLIT={os.environ['HARVEST_ALLOW_SPLIT']}")
    return ["env", "IR_ROOT=cyclo", f"IR_INST={inst}", f"CUDA_VISIBLE_DEVICES={gpu}", "timeout", str(timeout_s),
            "./ir_run.sh", "env", *envs, "/isaac-sim/python.sh", "-m", "harvest.eval.closed", "--worker", spec_path]


def run_worker(spec_path: str) -> None:
    """Inside Isaac: one embodiment (variant), one eval() per condition over all seeds x epochs."""
    spec = json.load(open(spec_path, encoding="utf-8"))
    os.environ.setdefault("HARVEST_QID_REGISTRY", os.path.join(spec["out"], "qid_registry.json"))
    from ..runtime.aiworker import AIWorkerEmbodiment
    emb = AIWorkerEmbodiment(variant=spec["variant"])
    from inspect_robots import Scene, Task, eval as ir_eval
    from inspect_robots.controller import DefaultController
    from inspect_robots.scorer import episode_length, success_at_end

    from ..runtime.astra_hb import MockAstra
    from ..runtime.conditions import condition
    from ..runtime.core import OursRuntime, RuntimeConfig
    from ..runtime.ir_policy import OursPolicy
    from ..runtime.models import JevLSelector, MockFusedModel, MockSelector
    from ..runtime.run_r5 import question_ids
    from ..sim.scene import SCENE_SPEC
    rows, t0 = [], time.monotonic()
    for lab in run_labels(spec["conditions"], spec.get("hb_n", [5.0]), tuple(spec.get("hb_mode", ["K2"]))):
        cond, hb_n, label = lab[:3]
        hb_mode = lab[3] if len(lab) > 3 else "K2"
        if spec["selector"] == "jevl":
            model = JevLSelector(spec["url"], spec["name"], layout=spec["layout"], mode=spec["mode"])
        elif spec["selector"] == "stageb":
            from ..runtime.fused_model import FusedClient
            model = FusedClient(spec["url"])
        elif spec["selector"] == "mock_fused":
            model = MockFusedModel(latency_s=spec["mock_latency"])
        else:
            model = MockSelector(latency_s=spec["mock_latency"])
        astra, amode = None, "none"
        tok = "/data/.openai_token"
        if spec["astra"] in ("auto", "api") and os.path.exists(tok):
            from ..clients.astra import AstraClient
            from ..runtime.astra_hb import MODEL as ASTRA_MODEL
            astra, amode = AstraClient(open(tok).read().strip(), ASTRA_MODEL, timeout_s=30.0), "api"
        elif spec["astra"] == "api":
            raise SystemExit("--astra api but no /data/.openai_token")
        elif spec["astra"] in ("auto", "mock"):
            astra, amode = MockAstra(3.0), "mock"
        elif spec["astra"] == "scripted":  # K3 pipeline check without a key: text-summary success detector
            from ..runtime.astra_hb import ScriptedAstra
            astra, amode = ScriptedAstra(1.0), "scripted"
        _, rto = condition(cond)
        cfg = RuntimeConfig(backend=spec["backend"], selector=spec["selector"],
                            model_id=getattr(model, "model_id", spec["name"]), model_path=spec["model_path"] or "",
                            layout=spec["layout"] if spec["selector"] == "jevl" else "",
                            call_mode=spec["mode"] if spec["selector"] == "jevl" else "", clock=spec["clock"],
                            question_ids=question_ids(spec["layout"] or "H",
                                                      "IMG" if spec["selector"] == "stageb" else "S1-1mm"),
                            astra_mode=amode, condition=cond,
                            m4=m4_config(cond, spec.get("m4_H", 3)), calibration=spec["calibration"] or "",
                            j5_alpha=spec["j5_alpha"], model_fingerprint=spec["fingerprint"], hb_N_s=hb_n,
                            verify_cal=spec.get("verify_cal") or "", hb_mode=hb_mode,
                            hb_budget=spec.get("hb_budget") if hb_mode == "K4" else None,
                            canary_id=spec.get("canary_id") or "none", **rto)
        if spec["backend"] == "fused":
            cfg.state_repr = "fused: images (head + active wrist) + task + contract summary + proprio (canon §58)"
        rt = OursRuntime(cfg, model, astra=astra)
        tag = label.replace("|", "_")
        pol = OursPolicy(rt, name=f"ours-{spec['backend']}-{spec['selector']}-{tag}",
                         checkpoint=spec["model_path"] or None)
        scenes = [Scene(id=f"{spec['split']}{s}-P0-{spec['variant']}", instruction=SCENE_SPEC["instruction"],
                        init_seed=s, metadata={"layout_seed": s, "kind": "P0", "variant": spec["variant"],
                                               "split": spec["split"].upper()}) for s in spec["seeds"]]
        task = Task(name=f"r6-{tag}-{spec['variant']}", scenes=scenes, scorer=[success_at_end(), episode_length()],
                    max_seconds=spec["max_seconds"], epochs=spec["epochs"])
        log_dir = os.path.join(spec["out"], spec["variant"], tag)
        tc = time.monotonic()
        logs = ir_eval(task, pol, emb, log_dir=log_dir, seed=0, controller=DefaultController(1),
                       environment_id=emb.info.environment_id, environment_revision=emb.info.environment_revision,
                       policy_checkpoint=spec["model_path"] or getattr(model, "model_id", None))
        log = logs[0]
        for smp in log.samples or []:
            seed = int((getattr(smp, "scene_metadata", None) or {}).get("layout_seed",
                                                                           str(smp.scene_id).split("-")[0][
                                                                               len(spec["split"]):]))
            tms = getattr(smp, "trial_metadata", None) or []
            terms = getattr(smp, "termination_reasons", None) or []
            for e, tm in enumerate(tms):
                sm = tm.get("ours_summary") or {}
                rows.append({"variant": spec["variant"], "condition": label, "hb_n": hb_n, "hb_mode": hb_mode,
                             "seed": seed, "epoch": e,
                             "success": bool(sm.get("env_success")), "sim_time": sm.get("sim_time_end"),
                             "termination": terms[e] if e < len(terms) else None, "summary": sm,
                             "sidecar": tm.get("ours_sidecar"), "frames": tm.get("ours_frames")})
        rows.append({"_cond_done": label, "wall_s": round(time.monotonic() - tc, 1), "status": log.status,
                     "error": getattr(log, "error", None) and str(log.error)[:2000], "log_dir": log_dir})
        rt.close()
    with open(os.path.join(spec["out"], f"worker_{spec['variant']}.json"), "w", encoding="utf-8") as f:
        json.dump({"rows": rows, "wall_s": round(time.monotonic() - t0, 1)}, f, indent=1, default=str)
    print("R6_WORKER_DONE", spec["variant"], flush=True)
    sys.stdout.flush()
    os._exit(0)  # SimulationApp.close() hangs after eval in this rootfs (R5); results are written


# ------------------------------------------------------------------------------------------ outer command
def _args(argv):
    ap = argparse.ArgumentParser(prog="python -m harvest.eval.closed", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, help="merged | adapter | zero-shot | mock | mock_fused")
    ap.add_argument("--out", required=True)
    ap.add_argument("--backend", default="modular", choices=["modular", "fused"])
    ap.add_argument("--split", default="dev")
    ap.add_argument("--seeds", default="0")
    ap.add_argument("--variants", default="standard")
    ap.add_argument("--conditions", default="C5")
    ap.add_argument("--m4-h", type=int, default=3, help="M4 H: decision steps per call (E §4.12 / M4 §4.4: 1 and 3)")
    ap.add_argument("--clock", default="simlat", choices=["simlat", "sync"])
    ap.add_argument("--max-seconds", type=float, default=60.0)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--astra", default="mock", choices=["auto", "api", "mock", "scripted", "none"])
    ap.add_argument("--hb-n", default="5", help="Astra heartbeat period N s; a list sweeps it (E-M8c K2-N, §45)")
    ap.add_argument("--hb-mode", default="K2", help="E-M8c cadence K0|K1|K2|K3|K4; a list sweeps it (astra_hb.py)")
    ap.add_argument("--hb-budget", type=int, default=None, help="K4: matched Astra call budget per episode")
    ap.add_argument("--isaac-gpu", default="1")
    ap.add_argument("--gpu", default="3", help="vLLM GPU")
    ap.add_argument("--gpu-util", type=float, default=0.30)
    ap.add_argument("--url", default="")
    ap.add_argument("--served-name", default="")
    ap.add_argument("--layout", default="auto")
    ap.add_argument("--mode", default="lead")
    ap.add_argument("--calibration", default="")
    ap.add_argument("--j5-alpha", type=float, default=None)
    ap.add_argument("--verify-cal", default="", help="verification-head calibration (runtime.measure verify-cal-v1)")
    ap.add_argument("--mock-latency", type=float, default=0.30)
    ap.add_argument("--timeout", type=int, default=0, help="per worker (s); 0 = auto")
    ap.add_argument("--parallel", action="store_true", help="run the variant workers at the same time (<= 3)")
    ap.add_argument("--inst-prefix", default="r6", help="Isaac kit instance prefix; give concurrent runs different ones")
    ap.add_argument("--n-boot", type=int, default=N_BOOT, help="bootstrap draws (E §1.7 / EVAL §4.2: 10,000)")
    ap.add_argument("--worker", default="", help=argparse.SUPPRESS)
    return ap.parse_args(argv)


def _md(res, meta) -> str:
    from .common import ci_str, md_table
    rows = [[k.replace("|", "\\|"), x["n"], ci_str(x["success"]), x["time_to_success_s"]["median"], x["latency_p50_s"]["median"],
             x["latency_p95_s"]["median"], x["commit_ratio"]["mean"], x["calls"], x["call_errors"],
             x["decisions_per_sim_s"]["median"], x["blocked_s"]["median"], x["rtf"]["median"], x["epochs_m4"]["median"],
             x["astra_calls"], x["stop_ticks"], json.dumps(x["terminations"])] for k, x in res["cells"].items()]
    lines = [f"# Closed loop — {meta['model']['spec']} ({meta['backend']}, clock {meta['clock']})", "",
             f"- utc {meta['utc']}, git {meta['git']}, code_sha {meta['code_sha']}, model fingerprint "
             f"{meta['model'].get('fingerprint')}, prompt_config {meta['prompt_config']['sha']} (layout "
             f"{meta['layout']}), split {meta['split']}, seeds {meta['seeds']}, epochs {meta['epochs']}, astra "
             f"{meta['astra']}, calibration {meta['calibration'] or '-'} (J5 alpha {meta['j5_alpha']})",
             f"- runtime {meta['runtime_s']}", "",
             md_table(["condition/variant", "n", "success [95% CI]", "t success (med s)", "lat p50", "lat p95",
                       "commit", "calls", "err", "dec/s", "blocked s", "RTF", "M4 epochs", "Astra", "C0 stop ticks",
                       "terminations"], rows)]
    if res["condition_diff"]:
        lines += ["", "## Paired condition differences (success, same seed)", "",
                  md_table(["pair", "diff [95% CI]", "n"], [[k, ci_str(v), v["n_pairs"]]
                                                            for k, v in res["condition_diff"].items()])]
    if res["rd"]:
        lines += ["", "## Closed-loop RD (1 - SR_variant / SR_standard, paired by seed)", "",
                  md_table(["condition/variant", "SR std", "SR var", "RD", "RD 95% CI", "SR std - SR var", "pairs"],
                           [[k, v["sr_std"], v["sr_var"], v["rd"], str(v["rd_ci"]), ci_str(v["sr_diff"]),
                             v["n_pairs"]] for k, v in res["rd"].items()])]
    return "\n".join(lines)


def run_prompt_config(selector: str, pc: dict | None, layout: str) -> dict:
    """meta.prompt_config of a run (R7 cycle 7 N7): a stage-B checkpoint runs on its own training prompt_config
    (the fused server's check_prompt refuses a mismatch with what the runtime feeds), everything else on the
    modular inference config of this layout."""
    from . import common as C
    if selector == "stageb" and pc:
        return {**pc, "source": "checkpoint stageb.json (fused server check_prompt enforces runtime equality)"}
    return C.prompt_config_eval(layout)


def run(a) -> dict:
    from . import common as C
    from .e05 import parse_seeds
    from .splits import check_seeds, check_split
    check_split(a.split)
    seeds = check_seeds(sorted(parse_seeds(a.seeds)), a.split)
    conds = [c for c in a.conditions.split(",") if c]
    from ..runtime.astra_hb import CADENCES
    modes = [m for m in a.hb_mode.split(",") if m]
    if not modes or any(m not in CADENCES for m in modes):
        raise SystemExit(f"--hb-mode {a.hb_mode!r}: from {CADENCES}")
    if "K4" in modes and a.hb_budget is None:
        raise SystemExit("--hb-mode K4 needs --hb-budget (the matched call count)")
    for c in conds:
        m4_config(c, a.m4_h)  # unknown condition or H < 1 -> refused before any worker
    if str(a.isaac_gpu) not in ISAAC_GPUS:
        raise SystemExit(f"--isaac-gpu {a.isaac_gpu}: 0 or 1 only (GPU 2 never renders)")
    t0 = time.monotonic()
    os.makedirs(a.out, exist_ok=True)
    spec_model = "mock" if a.model in ("mock", "mock_fused") else a.model
    info = C.ensure_merged(C.resolve_model(spec_model), a.out)
    if a.backend == "fused" and a.model != "mock_fused" and info["kind"] != "stageb":
        raise SystemExit("--backend fused: --model mock_fused or a stage-B checkpoint dir (stageb.json + adapter/)")
    if info["kind"] == "stageb" and a.backend != "fused":
        raise SystemExit("a stage-B checkpoint runs with --backend fused")
    selector = ("mock_fused" if a.model == "mock_fused" else "stageb" if info["kind"] == "stageb"
                else ("mock" if info["kind"] == "mock" else "jevl"))
    pc = C.training_prompt_config(info["path"]) if info["kind"] != "mock" else None
    layout = ((C.default_layout(pc) if a.layout == "auto" else a.layout) if selector == "jevl"
              else "HW" if selector == "stageb" else "H")
    fp = C.model_fingerprint(info["path"]) if info.get("path") else None
    from .canary import latest_canary  # canon §28/§42: the day's canary id on every call row (or "none")
    canary_id = latest_canary("mock" if selector in ("mock", "mock_fused") else fp)["id"]
    variants = [v for v in a.variants.split(",") if v]
    per_ep = a.max_seconds / 0.3 + 60  # RTF >= 0.3 assumed + reset
    timeout = a.timeout or int(240 + len(conds) * len(seeds) * a.epochs * per_ep)
    code = C.REPO
    wall = {}
    with C.Server(info, a.gpu, a.out, a.url, a.served_name, a.gpu_util) as srv:
        procs = []
        for v in variants:
            spec = {"out": os.path.abspath(a.out), "variant": v, "seeds": seeds, "split": a.split,
                    "conditions": conds, "backend": a.backend, "selector": selector, "url": srv.url,
                    "name": srv.name, "layout": layout, "mode": a.mode, "clock": a.clock,
                    "max_seconds": a.max_seconds, "epochs": a.epochs, "astra": a.astra,
                    "model_path": info.get("path"), "fingerprint": fp, "calibration": a.calibration,
                    "j5_alpha": a.j5_alpha, "mock_latency": a.mock_latency, "verify_cal": a.verify_cal,
                    "hb_n": [float(x) for x in a.hb_n.split(",") if x],
                    "hb_mode": [m for m in a.hb_mode.split(",") if m], "hb_budget": a.hb_budget,
                    "canary_id": canary_id, "m4_H": a.m4_h}
            sp = os.path.join(a.out, f"spec_{v}.json")
            json.dump(spec, open(sp, "w", encoding="utf-8"), indent=1)
            cmd = worker_cmd(code, os.path.abspath(sp), a.isaac_gpu, f"{a.inst_prefix}_{v}", timeout)
            logf = open(os.path.join(a.out, f"worker_{v}.log"), "w")
            tv = time.monotonic()
            p = subprocess.Popen(cmd, cwd=IR_DIR, stdout=logf, stderr=subprocess.STDOUT)
            procs.append((v, p, logf, tv))
            if not a.parallel:
                p.wait()
                wall[v] = round(time.monotonic() - tv, 1)
        for v, p, logf, tv in procs:
            p.wait()
            wall.setdefault(v, round(time.monotonic() - tv, 1))
            logf.close()
    trials, cond_runs = [], []
    for v in variants:
        wp = os.path.join(a.out, f"worker_{v}.json")
        if not os.path.exists(wp):
            raise SystemExit(f"worker {v} wrote no result, see {a.out}/worker_{v}.log")
        for r in json.load(open(wp, encoding="utf-8"))["rows"]:
            (cond_runs if "_cond_done" in r else trials).append(r)
    res = aggregate(trials, a.n_boot)
    res["trials"] = [{k: t[k] for k in ("variant", "condition", "seed", "epoch", "success", "sim_time",
                                        "termination", "sidecar")} for t in trials]
    res["eval_runs"] = cond_runs
    meta = C.run_meta("closed", info, {
        "backend": a.backend, "selector": selector, "split": a.split, "seeds": seeds, "variants": variants,
        "conditions": conds, "m4_H": a.m4_h, "clock": a.clock, "epochs": a.epochs, "max_seconds": a.max_seconds,
        "astra": a.astra,
        "layout": layout, "mode": a.mode, "prompt_config": run_prompt_config(selector, pc, layout),
        "isaac_gpu": a.isaac_gpu, "bootstrap": res["bootstrap"],
        "calibration": a.calibration, "j5_alpha": a.j5_alpha, "hb_n": a.hb_n,
        "not_in_runtime": "C2'/C2'-S/C2-match, C3', C3'', C5-A3, C-FIX, C5' (conditions.py doc)",
        "hb_mode": a.hb_mode, "hb_budget": a.hb_budget, "verify_cal": a.verify_cal or "default (uncalibrated)",
        "runtime_s": {"total": round(time.monotonic() - t0, 1), "workers": wall,
                      "vllm_ready": round(getattr(srv, "t_ready", 0.0), 1)}})
    C.write_outputs(a.out, "closed", {"meta": meta, "result": res}, _md(res, meta))
    print("CLOSED_DONE " + json.dumps({"out": a.out, "cells": {k: v["success"]["mean"] for k, v in
                                                               res["cells"].items()}, "runtime_s": meta["runtime_s"]}),
          flush=True)
    return {"meta": meta, "result": res}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv[:1] == ["--worker"]:  # the Isaac-side worker: only the spec path
        return run_worker(argv[1])
    return run(_args(argv))


if __name__ == "__main__":
    main()
