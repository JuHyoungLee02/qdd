"""Runtime model back-ends behind one call interface (canon §58: "최대한 하나로 융합").

decide(ctx) -> ModelResult is called in a worker thread (never on the rollout thread). ctx is a plain dict:
  req / shown  the DecCall request (5 typed decision questions, option tables of jevcall / deccall_snap) and
               {qid: (question, options)} to map shown names back to option_keys (canon §27 R5);
  images       {"cam_head": HxWx3 uint8, "cam_wrist_right": ...} (latest frames at t_state);
  joint_pos    8-D proprioception; t_state, ds, slots, epoch.
Both back-ends feed M4 the same way (typed decision probabilities from staggered calls):
  - ModularStack (baseline row): JevLSelector = Jev-L DecCall on vLLM (M1 S1 coordinate text + images) -> M4 ->
    scripted skill S + residual-R hook. MockSelector = the labels_v2 S1 code rule (deterministic stand-in).
  - FusedModel (main row, canon §58, the R4 model): ONE backbone gives decision-token probabilities (decide(), HF backbone)
    and, conditioned on the M4-committed decisions (stage-B expert input cond["dec"]), a continuous action chunk
    (chunk(ctx, committed), HF backbone context + CUDA-graphed expert, fused_action.py). Input = images (head +
    active wrist) + task sentence + contract summary + proprioception, no S1 coordinates. MockFusedModel: decisions
    from the privileged code rule (flagged), chunk = hold -> interface / log check only.
"""
from __future__ import annotations

import asyncio
import io
import threading
import uuid
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np

from ..deccall_snap import build_snapshot_request
from ..labels_v2 import code_rule_v2
from ..options import to_option_key

DECISION_QUESTIONS = ("dir_xy", "dir_z", "mag_coarse", "target", "phase")
RULE_FIELD = {"dir_xy": "dir_xy", "dir_z": "dir_z", "mag_coarse": "mag_coarse", "target": "target",
              "phase": "phase_choice"}
NE = "NONE_ESCALATE"
WRIST_LABEL = {"cam_wrist_right": "right wrist camera (active arm):", "cam_wrist_left": "left wrist camera (active arm):"}


@dataclass
class ModelResult:
    answers: dict  # question -> {"choice": option_key, "p_chosen", "p_second", "probs": {option_key: p}}
    latency_s: float
    call_id: str = ""
    error: str | None = None
    chunk: np.ndarray | None = None  # fused: (n, 8) absolute joint targets from t_state on
    chunk_dt: float | None = None
    meta: dict = field(default_factory=dict)
    verify: dict | None = None  # fused: verification-head logits {predicate: logit} (canon §61/§64, runtime.measure)
    raw: dict | None = None  # the back-end's raw response (E §1.6 "응답 원문", logged as a blob, canon §77)


def build_live_request(ds: int, phase: str, text_s0: str, present, raw: dict, step_cm: float = 0.1,
                       state: str = "S1", last_step: str = "none"):
    """DecCall for the live state, built exactly as the stage-A / stage-B items (stagea_data.build_items): the pool
    line fields, questions restricted to the 5 decision questions. state S1 = E3-lite S1 on a 1 mm grid (canon §54,
    the modular stack); IMG = stageb_data.image_only_state of the S0 text (canon §58 fused model: no coordinates,
    no predicate facts -- the stage-B prompt_config state). last_step = the M4 (b) category line that ends the
    state (M4 §4.2 :232, canon §77; "none" = none to show)."""
    from .. import e3lite
    from ..serialize import LAST_STEP_VALUES
    if last_step not in LAST_STEP_VALUES:
        raise ValueError(f"last_step {last_step!r}: one of {LAST_STEP_VALUES}")
    line = {"ds_id": f"ds{ds}", "phase": phase, "text_state": text_s0, "last_step": last_step,
            "state": {"present": list(present), "obs": {"raw": raw}}, "oracle": defaultdict(lambda: None)}
    if state == "IMG":
        from ..train.stageb_data import image_only_state
        st = image_only_state(text_s0)
    elif state == "S1":
        st = e3lite.state_text(line, "S1", step_cm=step_cm)
    else:
        raise ValueError(f"state {state!r}: S1 | IMG")
    req, _, shown = build_snapshot_request(line, text_state=st)
    keep = {qid for qid, (q, _) in shown.items() if q in DECISION_QUESTIONS}
    req = {**req, "questions": {k: v for k, v in req["questions"].items() if k in keep}}
    return req, {k: v for k, v in shown.items() if k in keep}


def fused_state_text(instruction: str, stage: str, phase: str, joint_pos) -> str:
    """Fused-model text input (canon §58): task sentence + contract summary + proprioception, no coordinates."""
    from ..sim.snapshot import STAGES
    st = STAGES[stage]
    q = ", ".join(f"{v:.3f}" for v in np.asarray(joint_pos, float))
    return (f"task: {instruction}\ncontract: c1 stage {stage}: {st['text']} (exit: {st['exit']}) phase={phase}\n"
            f"proprio: joint_pos=[{q}] (7 right-arm joints rad, gripper width m)")


def _rule_answers(state_text: str, shown: dict) -> dict:
    rule = code_rule_v2(state_text)
    out = {}
    for qid, (q, opts) in shown.items():
        keys = [o.key for o in opts]
        k = rule.get(RULE_FIELD[q])
        k = k if k in keys else NE
        out[q] = {"choice": k, "p_chosen": 1.0, "p_second": 0.0, "probs": {k: 1.0}, "qid": qid}
    return out


class MockSelector:
    """Deterministic ModularStack selector: the labels_v2 S1 code rule, with a fixed synthetic latency."""
    kind, name = "modular", "mock_code_rule_v2"

    def __init__(self, latency_s: float = 0.30):
        self.synthetic_latency = float(latency_s)
        self.model_id = "mock:labels_v2.code_rule_v2"

    def decide(self, ctx: dict) -> ModelResult:
        ans = _rule_answers(ctx["req"]["state"], ctx["shown"])
        return ModelResult(ans, self.synthetic_latency, call_id=uuid.uuid4().hex, meta={"mock": True},
                           raw={"mock": self.name, "answers": ans})

    def close(self):
        pass


class MockFusedModel(MockSelector):
    """FusedModel stand-in (interface / log check only). decide(): decisions from the PRIVILEGED S1 code rule (mock
    only, flagged); chunk(ctx, committed): hold the current joints for H = 15 rows at 30 Hz (stageb_data HZ / H)."""
    kind, name = "fused", "mock_fused_hold"

    def __init__(self, latency_s: float = 0.30, chunk_latency_s: float = 0.12, H: int = 15, chunk_dt: float = 1 / 30):
        super().__init__(latency_s)
        self.synthetic_chunk_latency, self.H, self.chunk_dt = float(chunk_latency_s), H, chunk_dt
        self.model_id = "mock:fused(code_rule_v2 decisions + hold chunk)"

    def decide(self, ctx: dict) -> ModelResult:
        ans = _rule_answers(ctx["privileged_s1"], ctx["shown"])
        return ModelResult(ans, self.synthetic_latency, call_id=uuid.uuid4().hex,
                           meta={"mock": True, "privileged_decisions": True},
                           raw={"mock": self.name, "answers": ans})

    def chunk(self, ctx: dict, committed: dict) -> ModelResult:
        c = np.tile(np.asarray(ctx["joint_pos"], float), (self.H, 1))
        return ModelResult({}, self.synthetic_chunk_latency, call_id=uuid.uuid4().hex, chunk=c,
                           chunk_dt=self.chunk_dt, meta={"mock": True, "committed": dict(committed)})


def jpeg_bytes(img, q: int = 90) -> bytes:
    """Frames are sent as JPEG q90, the encoding of the pool images the stage-A model was trained on."""
    from PIL import Image
    b = io.BytesIO()
    Image.fromarray(np.asarray(img, np.uint8)).save(b, format="JPEG", quality=q)
    return b.getvalue()


class JevLSelector:
    """Jev-L DecCall on a vLLM server (clients/jevl.py acall_mm). layout H = head only (the stage-A training
    format), HW = head + active wrist with labels (canon §59); mode lead (canon §59) or base."""
    kind, name = "modular", "jevl"
    synthetic_latency = None

    def __init__(self, base_url: str, model: str, layout: str = "HW", mode: str = "lead", timeout_s: float = 5.0,
                 wrist: str = "cam_wrist_right"):
        from ..clients.jevl import JevLClient
        self.layout, self.mode, self.wrist, self.model_id = layout, mode, wrist, model
        self._loop = asyncio.new_event_loop()
        self._th = threading.Thread(target=self._loop.run_forever, daemon=True, name="jevl-loop")
        self._th.start()
        self.client = JevLClient(base_url, model, timeout_s=timeout_s, image_mime="image/jpeg")

    def _images(self, ctx):
        ims = ctx.get("images") or {}
        out = []
        if ims.get("cam_head") is not None:
            out.append(("head camera:", jpeg_bytes(ims["cam_head"])))
        if self.layout == "HW" and ims.get(self.wrist) is not None:
            out.append((WRIST_LABEL[self.wrist], jpeg_bytes(ims[self.wrist])))
        return out

    def decide(self, ctx: dict) -> ModelResult:
        imgs = self._images(ctx)
        fut = asyncio.run_coroutine_threadsafe(
            self.client.acall_mm(ctx["req"], {"experiment": "R5", "ds": ctx.get("ds")}, imgs, mode=self.mode,
                                 layout=self.layout), self._loop)
        r = fut.result()
        lat = (r.t_done - r.t_send) if r.t_done else 0.0
        raw = {"call_id": r.call_id, "model": r.model, "http_status": r.http_status, "error": r.error,
               "input_tokens": r.input_tokens, "output_tokens": r.output_tokens, "answers": r.answers,
               "raw_response": r.raw_response, "t_send": r.t_send, "t_first_byte": r.t_first_byte, "t_done": r.t_done}
        if r.error:
            return ModelResult({}, lat, call_id=r.call_id, error=r.error, meta={"input_tokens": r.input_tokens},
                               raw=raw)
        answers = {}
        for qid, a in r.answers.items():
            q, opts = ctx["shown"][qid]
            probs = {to_option_key(opts, n): p for n, p in a["probabilities"].items()}
            answers[q] = {"choice": to_option_key(opts, a["choice"]), "p_chosen": a["confidence"],
                          "p_second": a["p_second"], "probs": probs, "qid": qid}
        return ModelResult(answers, lat, call_id=r.call_id,
                           meta={"input_tokens": r.input_tokens, "n_seq": r.output_tokens, "model": r.model,
                                 "model_ok": r.model_ok, "n_images": len(imgs), "t_wall_send": r.t_send,
                                 "mode": self.mode, "layout": self.layout}, raw=raw)

    def close(self):
        try:
            asyncio.run_coroutine_threadsafe(self.client.aclose(), self._loop).result(timeout=5)
        finally:
            self._loop.call_soon_threadsafe(self._loop.stop)

