"""Astra H-cadence heartbeat (canon §45, D25): T_hb = N s after the previous Astra answer arrived, send the latest
head frame + a ledger summary and ask the closed choice ack / patch / replace. One call in flight (Gemini
"cancellation loop" warning); no answer within 15 s -> record and resend. ack never bumps premise_epoch (protects the
M4 agreement table); patch / replace bump it (the contract edit itself -- A5' check, M2 R3 boundary swap -- is not
implemented in this runtime: logged). Events (C_assume, T3a, ...) advance the next heartbeat; T_fail pauses it until
recovery end + 2 s (pause_until).

Model gpt-6-astra, effort low (canon §1 user principle). The key is read by the caller from /data/.openai_token on the
pod; without a key the MockAstra (always ack, fixed synthetic latency) runs and the log says so.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import time

from ..clients.astra import AstraRecord

MODEL, EFFORT, MAX_OUT = "gpt-6-astra", "low", 600
HB_TEMPLATE = (
    "You are the slow planner (heartbeat check) of a robot arm doing: {task}\n"
    "A fast decision layer and scripted skills are executing your contract; they do not wait for you.\n"
    "Current execution summary:\n{summary}\n"
    "Look at the head-camera image and the summary, then choose exactly one:\n"
    "- ack: execution is on track; keep the current contract.\n"
    "- patch: the current stage needs a small fix (for example a wrong object or a detection name).\n"
    "- replace: the plan no longer fits the scene and must be replaced.\n"
    'Answer with JSON only: {{"decision": "ack|patch|replace", "note": "<= 20 words"}}')
HB_PROMPT_ID = hashlib.sha256(HB_TEMPLATE.encode()).hexdigest()[:12]
TASK = "Put the red mug on the blue tray."


class HeartbeatScheduler:
    def __init__(self, N: float = 5.0, timeout_s: float = 15.0, budget: int | None = None):
        self.N, self.timeout_s, self.budget = N, timeout_s, budget
        self.next_t, self.inflight_t, self.paused_to, self.n_sent = N, None, -1.0, 0

    def due(self, now: float) -> bool:
        if self.inflight_t is not None or now < self.paused_to - 1e-9:
            return False
        if self.budget is not None and self.n_sent >= self.budget:
            return False
        return now >= self.next_t - 1e-9

    def sent(self, now: float) -> None:
        self.inflight_t, self.n_sent = now, self.n_sent + 1

    def responded(self, now: float) -> None:
        self.inflight_t, self.next_t = None, now + self.N

    def timed_out(self, now: float) -> bool:
        return self.inflight_t is not None and now - self.inflight_t > self.timeout_s

    def drop_inflight(self, now: float) -> None:
        self.inflight_t, self.next_t = None, now

    def advance(self, now: float) -> None:
        self.next_t = min(self.next_t, now)

    def pause_until(self, t: float) -> None:
        self.paused_to = t


def heartbeat_input(summary: str, head_jpeg: bytes | None, task: str = TASK) -> list:
    content = [{"type": "input_text", "text": HB_TEMPLATE.format(task=task, summary=summary)}]
    if head_jpeg:
        content.append({"type": "input_image",
                        "image_url": "data:image/jpeg;base64," + base64.b64encode(head_jpeg).decode()})
    return [{"role": "user", "content": content}]


def parse_decision(text: str) -> tuple[str, str]:
    m = re.search(r"\{.*\}", text or "", re.S)
    if m:
        try:
            d = json.loads(m.group(0))
            if d.get("decision") in ("ack", "patch", "replace"):
                return d["decision"], str(d.get("note", ""))
        except json.JSONDecodeError:
            pass
    w = re.search(r"\b(ack|patch|replace)\b", text or "")
    return (w.group(1), "") if w else ("invalid", "")


class MockAstra:
    """No-key stand-in: always ack after a fixed synthetic latency (canon §45 N estimate uses ~3 s first token)."""
    model = "mock:astra-ack"

    def __init__(self, latency_s: float = 3.0):
        self.synthetic_latency = float(latency_s)

    def call(self, inp, effort, max_output_tokens, meta) -> AstraRecord:
        t = time.monotonic()
        return AstraRecord(t_send=t, t_first_token=t, t_done=t, http_status=200, usage={},
                           output_text='{"decision": "ack", "note": "mock"}', model_field=self.model, effort=effort,
                           meta=dict(meta))
