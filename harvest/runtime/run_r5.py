"""R5: one DEV episode end to end through Inspect Robots eval() (pod, Isaac via ir_run.sh IR_ROOT=cyclo).

  python -m harvest.runtime.run_r5 --out /data/harvest/out/r5/<tag> --backend modular --selector mock
  python -m harvest.runtime.run_r5 --out ... --selector jevl --url http://127.0.0.1:PORT --model NAME \
      --model-path /data/harvest/ckpt/stageA/sftA_pool_v1/merged --layout H --mode lead
  python -m harvest.runtime.run_r5 --out ... --backend fused --selector mock_fused --max-seconds 5

Astra heartbeat: --astra auto = the API (gpt-6-astra, effort low) when /data/.openai_token exists, else the ack mock.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time


def question_ids(layout: str, state: str = "S1-1mm") -> dict:
    """question_id@vN of the 5 decision questions (canon §28 J1), ds / stage templated, camera layout in the legend
    (canon §59)."""
    import numpy as np  # noqa: F401
    from ..qid import question_id
    from .models import build_live_request
    raw = {"grip": {"pos": [0.3, -0.1, 0.25], "w": 0.107, "effort": 0.0},
           "objs": {k: {"pos": [0.4, -0.2, 0.05], "quat": [1, 0, 0, 0], "he": [0.03, 0.03, 0.05]} for k in ("o3", "o5")},
           "contacts": [], "support": {}}
    req, shown = build_live_request(0, "approach", "stage: S1\ngripper=open", ["o3", "o5"], raw)
    out = {}
    for qid, (q, opts) in shown.items():
        text = re.sub(r"stage S\d", "stage {stage}", re.sub(r"ds\d+", "{ds}", req["questions"][qid]["instructions"]))
        out[q] = question_id(text, [o.key for o in opts], {o.key: o.desc for o in opts}, {o.key: o.name for o in opts},
                             f"cameras={layout};state={state}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--backend", default="modular", choices=["modular", "fused"])
    ap.add_argument("--selector", default="mock", choices=["mock", "jevl", "mock_fused", "stageb"],
                    help="stageb = a real stage-B checkpoint served by runtime.fused_model serve (--url)")
    ap.add_argument("--hb-mode", default="K2", help="E-M8c cadence K0..K4 (astra_hb.py)")
    ap.add_argument("--hb-budget", type=int, default=None)
    ap.add_argument("--verify-cal", default="")
    ap.add_argument("--url", default="http://127.0.0.1:8131")
    ap.add_argument("--model", default="")
    ap.add_argument("--model-path", default="")
    ap.add_argument("--layout", default="HW", choices=["H", "HW"])
    ap.add_argument("--mode", default="lead", choices=["lead", "base"])
    ap.add_argument("--astra", default="auto", choices=["auto", "api", "mock", "scripted", "none"])
    ap.add_argument("--clock", default="simlat", choices=["simlat", "sync"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--kind", default="P0")
    ap.add_argument("--variant", default="standard")
    ap.add_argument("--max-seconds", type=float, default=60.0)
    ap.add_argument("--mock-latency", type=float, default=0.30)
    ap.add_argument("--tag", default="")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    os.environ.setdefault("HARVEST_QID_REGISTRY", os.path.join(a.out, "qid_registry.json"))

    from .aiworker import AIWorkerEmbodiment
    emb = AIWorkerEmbodiment(variant=a.variant)  # boots Isaac (GPU from CUDA_VISIBLE_DEVICES)

    from inspect_robots import Scene, Task, eval as ir_eval
    from inspect_robots.controller import DefaultController
    from inspect_robots.scorer import episode_length, success_at_end

    from .astra_hb import MODEL as ASTRA_MODEL, MockAstra
    from .core import OursRuntime, RuntimeConfig
    from .ir_policy import OursPolicy
    from .models import JevLSelector, MockFusedModel, MockSelector

    if a.selector == "jevl":
        model = JevLSelector(a.url, a.model, layout=a.layout, mode=a.mode)
    elif a.selector == "stageb":
        from .fused_model import FusedClient
        model = FusedClient(a.url)
    elif a.selector == "mock_fused":
        model = MockFusedModel(latency_s=a.mock_latency)
    else:
        model = MockSelector(latency_s=a.mock_latency)
    tok = "/data/.openai_token"
    astra, astra_mode = None, "none"
    if a.astra in ("auto", "api") and os.path.exists(tok):
        from ..clients.astra import AstraClient
        astra, astra_mode = AstraClient(open(tok).read().strip(), ASTRA_MODEL, timeout_s=30.0), "api"
    elif a.astra == "api":
        raise SystemExit("--astra api but no /data/.openai_token")
    elif a.astra in ("auto", "mock"):
        astra, astra_mode = MockAstra(3.0), "mock"
    elif a.astra == "scripted":
        from .astra_hb import ScriptedAstra
        astra, astra_mode = ScriptedAstra(1.0), "scripted"
    cfg = RuntimeConfig(backend=a.backend, selector=a.selector, model_id=getattr(model, "model_id", a.model),
                        model_path=a.model_path, layout=a.layout if a.selector == "jevl" else "",
                        call_mode=a.mode if a.selector == "jevl" else "", clock=a.clock,
                        question_ids=question_ids(a.layout, "IMG" if a.selector == "stageb" else "S1-1mm"),
                        astra_mode=astra_mode, hb_mode=a.hb_mode, hb_budget=a.hb_budget, verify_cal=a.verify_cal)
    if a.backend == "fused":
        cfg.state_repr = "fused: images (head + active wrist) + task + contract summary + proprio (canon §58)"
    rt = OursRuntime(cfg, model, astra=astra)
    pol = OursPolicy(rt, name=f"ours-{a.backend}-{a.selector}", checkpoint=a.model_path or None)
    from ..sim.scene import SCENE_SPEC
    scene = Scene(id=f"dev{a.seed}-{a.kind}-{a.variant}", instruction=SCENE_SPEC["instruction"], init_seed=a.seed,
                  metadata={"layout_seed": a.seed, "kind": a.kind, "variant": a.variant, "split": "DEV"})
    task = Task(name=f"r5-{a.tag or a.backend}", scenes=[scene], scorer=[success_at_end(), episode_length()],
                max_seconds=a.max_seconds, epochs=1)
    t0 = time.monotonic()
    logs = ir_eval(task, pol, emb, log_dir=a.out, seed=0, controller=DefaultController(1),
                   environment_id=emb.info.environment_id, environment_revision=emb.info.environment_revision,
                   policy_checkpoint=a.model_path or getattr(model, "model_id", None))
    wall = time.monotonic() - t0
    log = logs[0]
    tm = log.samples[0].trial_metadata[0] if log.samples and log.samples[0].trial_metadata else {}
    res = {"status": log.status, "wall_s": round(wall, 1), "metrics": log.results.metrics if log.results else None,
           "termination": log.samples[0].termination_reasons if log.samples else None, "summary": tm.get("ours_summary"),
           "sidecar": tm.get("ours_sidecar"), "frames": tm.get("ours_frames"),
           "error": getattr(log, "error", None) and str(log.error)[:2000]}
    with open(os.path.join(a.out, "r5_result.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=str)
    print("R5_RESULT " + json.dumps(res, default=str)[:4000], flush=True)
    rt.close()
    sys.stdout.flush()
    os._exit(0)  # SimulationApp.close() hangs in this rootfs after eval (R5 smoke); results are already written


if __name__ == "__main__":
    main()
