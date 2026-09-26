"""Astra call cadence (canon §45, D25; E-M8c conditions K0-K4). One Astra call in flight at a time (Gemini
"cancellation loop" warning); no answer within 15 s -> record and resend.

  K0  events only: the existing event calls (T_fail, T_j5 escalation, M7 critic / hard channel, (b) CONTRADICT, ...)
      pull a call forward; no periodic heartbeat, no boundary query.
  K1  K0 + T_sub: when a contract stage completes (skill S1 -> S2, and done) ask asynchronously "does the next stage
      contract still fit the scene?" (ack / patch / replace); the next stage starts without waiting.
  K2  K1 + T_hb heartbeat N s after the previous Astra answer arrived (latest head frame + ledger summary, closed
      choice ack / patch / replace) -- the §45 H-cadence decision (runtime default, N swept by --hb-n = K2-N).
  K3  Gemini Robotics-ER streaming heartbeat, faithful variant: opportunistic 1 Hz cadence while waiting for each turn
      to complete (next send = max(previous send + 1 s, previous answer)), latest frame + a short prompt forcing an
      explicit decision ack (in progress) / run_instruction (step done -> next step) / reset (goal achieved). The
      runtime applies run_instruction / reset only when the code safety predicates hold (skill.astra_advance).
  K4  event-only control with a matched call budget: K1's triggers, at most `budget` calls per episode (set it to the
      mean call count of the K2-N cell it is matched to).
ack never bumps premise_epoch (protects the M4 agreement table); patch / replace bump it (the contract edit itself --
A5' check, M2 R3 boundary swap -- is not implemented in this runtime: logged). T_fail pause = pause_until.

Model gpt-6-astra, effort low (canon §1 user principle). The key is read by the caller from /data/.openai_token on the
pod; without a key the MockAstra (always ack, fixed synthetic latency) runs and the log says so.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import re
import time

from ..clients.astra import AstraRecord

MODEL, EFFORT, MAX_OUT = "gpt-6-astra", "low", 600
CADENCES = ("K0", "K1", "K2", "K3", "K4")
OURS_CHOICES = ("ack", "patch", "replace")
GEMINI_CHOICES = ("ack", "run_instruction", "reset")
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
TSUB_TEMPLATE = (
    "You are the slow planner of a robot arm doing: {task}\n"
    "A contract stage has just been completed; the next stage has already started and does not wait for you.\n"
    "Current execution summary:\n{summary}\n"
    "Look at the head-camera image: does the next stage of the contract still fit the scene? Choose exactly one:\n"
    "- ack: the next stage fits; keep the contract.\n"
    "- patch: the next stage needs a small fix (for example a wrong object or a detection name).\n"
    "- replace: the plan no longer fits the scene and must be replaced.\n"
    'Answer with JSON only: {{"decision": "ack|patch|replace", "note": "<= 20 words"}}')
GEMINI_TEMPLATE = (
    "You are supervising a robot arm doing: {task}\n"
    "The robot keeps executing its current instruction until you give the next one.\n"
    "Current step summary:\n{summary}\n"
    "Inspect the latest camera frame and make an explicit decision, exactly one of:\n"
    "- ack: the current step is still in progress.\n"
    "- run_instruction: the current step is complete; run the next step.\n"
    "- reset: the goal has been achieved.\n"
    'Answer with JSON only: {{"decision": "ack|run_instruction|reset", "note": "<= 20 words"}}')
TASK = "Put the red mug on the blue tray."


def _pid(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()[:12]


def prompt_for(mode: str, kind: str):
    """(template, allowed choices, prompt id) of a call kind ("hb" | "sub") under a cadence mode."""
    if mode == "K3":
        return GEMINI_TEMPLATE, GEMINI_CHOICES, _pid(GEMINI_TEMPLATE)
    if kind == "sub":
        return TSUB_TEMPLATE, OURS_CHOICES, _pid(TSUB_TEMPLATE)
    return HB_TEMPLATE, OURS_CHOICES, HB_PROMPT_ID


class HeartbeatScheduler:
    def __init__(self, N: float = 5.0, timeout_s: float = 15.0, budget: int | None = None, mode: str = "K2",
                 k3_period_s: float = 1.0):
        if mode not in CADENCES:
            raise ValueError(f"cadence {mode!r}: {CADENCES}")
        self.N, self.timeout_s, self.budget, self.mode, self.k3_period = N, timeout_s, budget, mode, k3_period_s
        self.next_t = N if mode == "K2" else (0.0 if mode == "K3" else math.inf)
        self.inflight_t, self.paused_to, self.n_sent = None, -1.0, 0
        self.last_send, self.sub_pending = None, False
        self.n_by_kind = {}

    # ------------------------------------------------------------------ what to send now
    def next_kind(self, now: float):
        """"sub" (a pending boundary query), "hb" (heartbeat / event call) or None."""
        if self.inflight_t is not None or now < self.paused_to - 1e-9:
            return None
        if self.budget is not None and self.n_sent >= self.budget:
            return None
        if self.sub_pending:
            return "sub"
        return "hb" if now >= self.next_t - 1e-9 else None

    def due(self, now: float) -> bool:
        return self.next_kind(now) is not None

    def sent(self, now: float, kind: str = "hb") -> None:
        self.inflight_t, self.n_sent, self.last_send = now, self.n_sent + 1, now
        self.n_by_kind[kind] = self.n_by_kind.get(kind, 0) + 1
        if kind == "sub":
            self.sub_pending = False
        elif self.mode != "K2" and self.mode != "K3":
            self.next_t = math.inf  # event call consumed

    def responded(self, now: float) -> None:
        self.inflight_t = None
        if self.mode == "K2":
            self.next_t = now + self.N
        elif self.mode == "K3":  # opportunistic 1 Hz, waiting for each turn
            self.next_t = max((self.last_send if self.last_send is not None else now) + self.k3_period, now)
        # K0 / K1 / K4: the next call needs a new event (or a boundary)

    def timed_out(self, now: float) -> bool:
        return self.inflight_t is not None and now - self.inflight_t > self.timeout_s

    def drop_inflight(self, now: float) -> None:
        self.inflight_t, self.next_t = None, now

    def advance(self, now: float) -> None:
        """An event call (T_fail, T_j5, M7 alarm, (b) CONTRADICT, ...): send at the next free moment. In K3 the 1 Hz
        heartbeat already runs, so an event changes nothing."""
        if self.mode != "K3":
            self.next_t = min(self.next_t, now)

    def boundary(self, now: float) -> None:
        """A contract stage completed (T_sub): K1 / K2 / K4 queue the boundary query (sent when nothing is in flight)."""
        if self.mode in ("K1", "K2", "K4"):
            self.sub_pending = True

    def pause_until(self, t: float) -> None:
        self.paused_to = t


def heartbeat_input(summary: str, head_jpeg: bytes | None, task: str = TASK, template: str = HB_TEMPLATE) -> list:
    content = [{"type": "input_text", "text": template.format(task=task, summary=summary)}]
    if head_jpeg:
        content.append({"type": "input_image",
                        "image_url": "data:image/jpeg;base64," + base64.b64encode(head_jpeg).decode()})
    return [{"role": "user", "content": content}]


def parse_decision_ex(text: str, allowed=OURS_CHOICES) -> tuple[str, str, str]:
    """Like parse_decision, plus parse_mode (F20, prompt_health.md): "fenced_json" (```json ... ``` block),
    "json" (bare {...} object), "regex_fallback" (no valid JSON, a bare allowed word found in the prose) or
    "failed" (no decision recognized at all). A failure never turns into a default answer -- it comes back as
    ("invalid", "", "failed") and the caller logs it (with the raw text, already kept in astra_log) instead of
    silently treating it like an "ack"."""
    text = text or ""
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fence:
        try:
            d = json.loads(fence.group(1))
            if d.get("decision") in allowed:
                return d["decision"], str(d.get("note", "")), "fenced_json"
        except json.JSONDecodeError:
            pass
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            d = json.loads(m.group(0))
            if d.get("decision") in allowed:
                return d["decision"], str(d.get("note", "")), "json"
        except json.JSONDecodeError:
            pass
    w = re.search(r"\b(" + "|".join(re.escape(a) for a in allowed) + r")\b", text)
    if w:
        return w.group(1), "", "regex_fallback"
    return "invalid", "", "failed"


def parse_decision(text: str, allowed=OURS_CHOICES) -> tuple[str, str]:
    dec, note, _mode = parse_decision_ex(text, allowed)
    return dec, note


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


class ScriptedAstra(MockAstra):
    """Test / smoke stand-in for K3: reads the text summary it is sent (never the image) and answers like a success
    detector -- run_instruction when the summary shows the mug held and lifted in stage S1, reset once stage S2 shows
    the gripper open with the mug released, else ack."""
    model = "mock:astra-scripted-gemini"

    def call(self, inp, effort, max_output_tokens, meta) -> AstraRecord:
        text = inp[-1]["content"][0]["text"]
        dec = "ack"
        if "stage=S1" in text and "'holding(o3)': True" in text and "'lifted_holding(o3)': True" in text:
            dec = "run_instruction"
        elif "stage=S2" in text and "gripper_open=True" in text and "phase=retreat" in text:
            dec = "reset"
        t = time.monotonic()
        return AstraRecord(t_send=t, t_first_token=t, t_done=t, http_status=200, usage={},
                           output_text=json.dumps({"decision": dec, "note": "scripted"}), model_field=self.model,
                           effort=effort, meta=dict(meta))
