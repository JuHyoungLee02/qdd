"""CoupleDriver: the Astra–VLA coupling inside OursRuntime (spec 2026-09-26 §11-§16, canon §84 supplement 2).
Per tick (tick): trace -> timeout -> maybe send (one in flight, budget, optional pause) -> offset step x authority a
(TickView.authority, canon §84 supplement 8: the runtime's E-SR1c a, None = 1; OffsetApplier scales the commanded
velocity before its limits; the stream / request / prompt carry no authority logic) -> no-progress.
Deliveries (on_delivery, through the runtime DeliveryQueue, meta kind "couple"): charge -> late? -> parse -> gate ->
layer -> offset. Per decision step (on_step): VLA fast check against the offset. The runtime asks irrev_allowed()
before an irreversible transition and forwards its event calls with flag(). The request carries the flow state (F1),
the VLA's current committed decision and motion line, the predicted tip at arrival (spec §3), the MolmoAct trace
polylines and the pending events; images (three cameras, overlay drawn in the worker thread) are labelled by name.

Chunk-level adherence (canon §84 supplement 4, plan Task 9 controller ruling C2): on_step takes an optional
chunk_vec, the executed motion of the current expert chunk (fused backend: chunk TCP displacement, a 3-vector;
None on the modular backend, where the committed decision is what skills execute directly). The VLA fast check --
and the offset-adherence log -- use vla_vec = chunk_vec if given, else committed_vector(committed); a decision
token is never assumed to steer the chunk on its own (canon §84 supplement 4-5, E-MA2/E-SR0).

Plan Task 21 (couple_dry.md B6/B7, book 02 P108): flag() is edge-triggered with a per-name refractory window
(event_refractory_s; clear() re-arms a name), suppressed repeats are counted (summary events_suppressed), and only
edges refresh the pause clock (fix round 1: persisting re-flags ride the next request, events_persisting); the
episode's never-answered requests are reported apart (summary unanswered); an API error without usage costs 0
(ledger no_usage) and insufficient_quota is fatal: the ledger records it and no request is sent again (hold fatal,
summary fatal).

astra-couple@v2 (plan 2026-09-26 Task 18, CoupleParams.prompt_version, default "v2"; "v1" keeps the old request and
prompt byte for byte): the prompt is prompt_v2.build (the E-ACC adopted text) with a legend of only the elements
drawn (overlay.drawn_elements) and the optional AxisGuide / extra instruction; the committed arrow and
vla_now.next_motion_m are the executed motion (committed_arrow: the chunk displacement from on_step on the fused
backend, else the decision centre capped by the skill's 0.5 s travel), not the decision-token centre; the request
carries since_last_request (canon §91: previous answered command + segment plan, tip displacement and phases since
its state time); answers carry a segment plan, agreed in the layer (two answers, a = 0 freeze with the authority at
delivery) and exposed as the VLA segment line by segment_intent() (intent.PLAN_TO_LINE for now, do / next from
intent.SEGMENT_PLAN -- Astra's raw do / next are logged only); an edit with valid_until segment_end is dropped when
the policy phase changes (the plan names map 1:1 to the phases).

Plan Task 19 (canon §91, controller rulings N2 / R19): predicted_ee_at_arrival = tip now + the executing chunk
displacement (committed_arrow) + remaining correction (predict_mode "chunk"; the old 0.5 s velocity x latency
extrapolation, book 02 P113, stays selectable as "extrapolate"), labelled in the request. Every valid delivered
answer is reconciled BEFORE the gate (reconcile.classify: done / valid / changed / conflict from the state at its
t_state vs now and the VLA's own motion since = tip displacement minus the offset applied meanwhile; the per-step
execution trace, gripper events, fast-check contradictions and the prediction error are logged with it); a valid
verdict lifts the gate's stale drop (the stale rule is subsumed), changed / conflict drop / hold the command, done
shrinks or skips it; the offset's authority a still multiplies (a = 0 -> nothing applied, verdict logged). The
verdict and the raw command ride the next request (since_last_request.previous_request). reconcile_apply False =
verdicts logged only."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

import numpy as np

from ..intent import PLAN_TO_LINE, SEGMENT_PLAN
from ..runtime.models import jpeg_bytes
from ..runtime.reqhash import request_body
from ..serialize import SEGMENT_UNKNOWN, segment_line
from . import prompt_v2 as V2
from .cost import estimate_input_tokens
from .gate import gate_answer
from .layer import AstraLayer
from .offset import OffsetApplier
from .overlay import CamModel, EETrace, draw_axisguide, draw_overlay, drawn_elements, polylines
from .prompt import PROMPT_ID, build_input
from .reconcile import classify, grip_state
from .schema import SCHEMA_IDS, SchemaError, parse_answer
from .stream import SerialStream
from .twolayer import NoProgress, TwoLayerGate, VlaFastCheck, adherence_cos, committed_vector, follows

CONTACT_PHASES = ("descend", "close", "place_descend", "open")
FATAL_ERRORS = ("insufficient_quota",)  # plan Task 21 D1 (book 02 P108): API errors that end the run's paid calls
MAG_CENTER_M = {"tiny": 0.005, "small": 0.01, "medium": 0.02, "large": 0.04, "xlarge": 0.08}


def _r(x):
    return [round(float(v), 4) for v in x]


def _r1(x):
    return None if x is None else round(float(x), 4)


@dataclass
class TickView:
    now: float
    dt: float
    tcp_p: np.ndarray
    phase: str
    stage: str
    near: bool
    committed: dict
    frames: dict
    cams: object = None
    t1: dict = field(default_factory=dict)
    motion: str | None = None
    # canon §84 supplement 8 (plan Task 17): authority a in [0, 1] on the offset (None = 1.0, backward compatible);
    # authority_src names where the runtime took it from (aux / rule), logged only
    authority: float | None = None
    authority_src: str | None = None


@dataclass
class TickOut:
    step6: np.ndarray
    speed_scale: float


def next_motion_vec(committed: dict):
    v = committed_vector(committed)
    if v is None:
        return None
    return v / float(np.linalg.norm(v)) * MAG_CENTER_M.get(committed.get("mag_coarse"), 0.0)


ARROW_S = 0.5  # the committed arrow = the tip motion over the next 0.5 s (v2 legend)


def committed_arrow(chunk_vec, committed: dict, phase: str, backend: str | None = None):
    """(vector or None, source) of the v2 committed arrow (prompt health F3): the executed chunk displacement when the
    fused backend gave one at the last decision step; on the fused backend without one (no chunk, held, FK failure,
    < 0.1 mm) NO arrow (source "none" -- the legend calls the arrow executed motion, so a decision centre must not
    stand in, Task 18 fix I1); modular / unknown backend: the decision centre (MAG_CENTER_M) capped by what the skill
    travels in ARROW_S at its phase speed (skills.V; 0 in close / open / done -> no arrow)."""
    if chunk_vec is not None:
        return np.asarray(chunk_vec, float), "chunk"
    if backend == "fused":
        return None, "none"
    from ..runtime.skills import V as SKILL_V
    v = committed_vector(committed)
    n = min(MAG_CENTER_M.get(committed.get("mag_coarse"), 0.0), SKILL_V.get(phase, 0.0) * ARROW_S)
    if v is None or n <= 0.0:
        return None, "decision"
    return v / float(np.linalg.norm(v)) * n, "decision"


def predict_ee(trace: list, horizon: float, cap: float, extra) -> np.ndarray:
    """predict_mode "extrapolate" (the pre-Task-19 predicted state): the last 0.5 s tip velocity x the latency
    horizon, capped, + the remaining correction. Not the default: over 9.3 s it jumped 6-9 cm near stops and segment
    changes and caused needless Astra edits (E-ACC stage 2, book 02 P113)."""
    (t0, p0), (t1, p1) = trace[0], trace[-1]
    d = (p1 - p0) / (t1 - t0) * horizon if t1 > t0 else np.zeros(3)
    n = float(np.linalg.norm(d))
    if n > cap:
        d = d * (cap / n)
    return p1 + d + np.asarray(extra, float)


def predict_chunk(tip, chunk_disp, extra) -> np.ndarray:
    """predict_mode "chunk" (default, controller ruling R19; E-ACC B' f54cc88: reference = current tip + committed
    arrow removed the false edits, on-plan 5/5): tip now + the currently executing chunk displacement (the committed
    arrow: fused = the runtime's chunk vector, modular = the decision centre capped by the skill's 0.5 s travel, None
    = no motion) + the remaining correction; no extrapolation over the latency horizon."""
    d = np.zeros(3) if chunk_disp is None else np.asarray(chunk_disp, float)
    return np.asarray(tip, float) + d + np.asarray(extra, float)


def gripper_word(phase: str, t1: dict) -> str:
    if phase == "close":
        return "closing"
    if phase == "open":
        return "opening"
    g = t1.get("gripper_open")
    return "open" if g is True else "closed" if g is False else "unknown"


class CoupleDriver:
    def __init__(self, p, astra, ledger, submit, task: str, episode: int = 1, backend: str | None = None):
        """backend: the runtime's backend ("fused" / "modular"; None = unknown, the modular arrow rule) -- decides
        the v2 committed arrow when no chunk vector is given (committed_arrow)."""
        self.p, self.astra, self.ledger, self.submit, self.task, self.episode = p, astra, ledger, submit, task, episode
        self.backend = backend
        self.stream = SerialStream(p, ledger)
        self.layer, self.offset, self.gate = AstraLayer(p), OffsetApplier(p), TwoLayerGate(p)
        self.fast, self.stag = VlaFastCheck(p), NoProgress(p)
        self.trace = EETrace(keep_s=max(p.trace_s, 0.5) + 1.0)
        self.last, self.last_t = None, None
        self.log, self.events, self.blobs = [], [], {}
        self.est_text_tokens = p.est_text_tokens
        self.budget_hit, self.stop_confirmed_t, self._hold = False, None, None
        self.auth_s, self._auth_last = {"a0": 0.0, "band": 0.0, "a1": 0.0}, None
        self._ev_last, self._ev_armed, self.events_suppressed = {}, set(), Counter()
        self._ev_call, self.events_persisting = {}, Counter()
        self.unanswered_closed = (0, 0.0)
        # astra-couple@v2 (plan Task 18)
        self.v2 = p.prompt_version == "v2"
        self.chunk_vec_last = None  # the last decision step's executed chunk displacement (on_step), None = none
        self.a_now = 1.0  # authority a of the last tick (the plan freeze reads it at delivery)
        self._phases, self._t0, self._tip0, self._tip_at = [], None, None, {}
        self._vu_phase = None  # the phase an applied valid_until=segment_end edit belongs to
        # canon §91 reconciliation (plan Task 19): the state at each request's t_state, the per-step execution trace
        # (t, executed chunk given), gripper events, fast-check contradictions, the last tick's tip / applied offset
        self._sent_state, self._exec, self._grip_ev, self._contra_t = {}, [], [], []
        self._grip_last, self._tip_now, self._applied_now = None, None, np.zeros(3)
        self._rc = {}  # request_no -> {"edit": raw edit json, "reconcile": verdict summary} for the next request

    def prompt_id(self, axisguide: bool | None = None) -> str:
        """The logged prompt id: v1 PROMPT_ID[mode]; v2 prompt_v2.variant_id (+ax when the axis guide is in the
        text -- by default when the flag is on --, +x<sha6> with an extra instruction)."""
        if not self.v2:
            return PROMPT_ID[self.p.request_mode]
        ax = self.p.axis_guide if axisguide is None else axisguide
        return V2.variant_id(self.p.request_mode, axisguide=ax, extra=self.p.extra_instruction)

    def segment_intent(self) -> str:
        """The VLA segment-intent line from the agreed plan (brief §3 ruling): now = PLAN_TO_LINE[plan now], do / next
        = SEGMENT_PLAN[that line segment] (the trained line vocabulary); unknown before the first agreed plan."""
        plan = self.layer.plan
        if plan is None:
            return SEGMENT_UNKNOWN
        now = PLAN_TO_LINE[plan["now"]]
        return segment_line(now, *SEGMENT_PLAN[now])

    def _build(self, req: dict, images: dict, drawn, horizon_s: float | None = None) -> list:
        """The model input (v1 prompt.build_input / v2 prompt_v2.build); horizon_s = the latency estimate at send
        (the v2 'arrives about N s' sentence; default the current estimate)."""
        p = self.p
        if not self.v2:
            return build_input(req, images, p, self.task)
        h = self.stream.L_hat if horizon_s is None else horizon_s
        return V2.build(req, images, list(p.cameras), self.task, mode=p.request_mode, arm=p.active_arm,
                        trace_s=p.trace_s, horizon_s=h, drawn=drawn, extra=p.extra_instruction)

    def _since(self, v) -> dict:
        """canon §91 context: the previous answered request's command and segment plan, the tip displacement and
        the policy phases since its state time (since the episode start before the first answer)."""
        last = self.last
        t0 = self._t0 if last is None else last.t_state
        tip0 = self._tip0 if last is None else self._tip_at.get(last.request_no, self._tip0)
        ph = [q for t, q in self._phases if t > t0 + 1e-9]
        before = [q for t, q in self._phases if t <= t0 + 1e-9]
        phases = ([before[-1]] if before else []) + ph
        out = {"vla_tip_moved_m": _r(np.asarray(v.tcp_p, float) - tip0), "vla_phases": phases,
               # plan Task 19: the execution summary since t0 (decision steps, steps with an executed chunk, gripper
               # changes) -- request data inside the registered since_last_request block
               "vla_steps": sum(1 for t, _ in self._exec if t >= t0 - 1e-9),
               "vla_chunks": sum(1 for t, c in self._exec if c and t >= t0 - 1e-9),
               "vla_gripper_events": [{"t": round(t, 3), "gripper": w} for t, w in self._grip_ev if t > t0 + 1e-9]}
        if last is None:
            out.update(previous_request=None, since_episode_start_s=round(v.now - self._t0, 1))
        else:
            rc = self._rc.get(last.request_no, {})
            out["previous_request"] = {"age_s": round(v.now - last.t_state, 1), "t_state": round(last.t_state, 3),
                                       "command": rc.get("command", last.command), "segment": last.segment,
                                       "edit": rc.get("edit"),
                                       "reconcile": rc.get("reconcile")}
        return out

    def key(self, no: int) -> str:
        return f"e{self.episode}:{no}"

    def flag(self, name: str, now: float) -> None:
        """Edge-triggered with a per-name refractory window (plan Task 21 B6, couple_dry.md: b_contradict fired at
        every decision step). An EDGE = the first flag of a name, or a flag after its condition cleared: clear(name),
        or no flag of that name at all (not even a suppressed one) for longer than event_refractory_s (sources that
        never call clear). Only an edge refreshes the stream's pause clock (fix round 1, ruling F21). A persisting
        condition re-flags at most once per event_refractory_s: it rides the next request as a persisting note
        (Astra learns the condition still holds) but does not refresh the pause clock (summary events_persisting);
        the repeats in between are counted (events_suppressed)."""
        last, called = self._ev_last.get(name), self._ev_call.get(name)
        self._ev_call[name] = now
        edge = (last is None or name in self._ev_armed
                or (called is not None and now - called > self.p.event_refractory_s + 1e-9))
        if not edge and now - last < self.p.event_refractory_s - 1e-9:
            self.events_suppressed[name] += 1
            return
        self._ev_last[name] = now
        self._ev_armed.discard(name)
        if not edge:
            self.events_persisting[name] += 1
        self.stream.flag(name, now, refresh=edge)
        self.events.append({"t": round(now, 3), "event": name, "edge": edge})

    def clear(self, name: str) -> None:
        """The condition behind `name` cleared: its next flag is a new edge and is not held by the refractory."""
        if name in self._ev_last:
            self._ev_armed.add(name)

    # ------------------------------------------------------------------ per tick
    def tick(self, v: TickView) -> TickOut:
        self.trace.add(v.now, v.tcp_p)
        if self._t0 is None:
            self._t0, self._tip0 = v.now, np.asarray(v.tcp_p, float).copy()
        # the tip of this tick reflects the offset applied BEFORE this tick's step (paired for the VLA-own motion)
        self._tip_now, self._applied_now = np.asarray(v.tcp_p, float).copy(), self.offset.applied[:3].copy()
        gw = gripper_word(v.phase, v.t1)
        if self._grip_last is not None and gw != self._grip_last:
            self._grip_ev.append((v.now, gw))
        self._grip_last = gw
        if not self._phases or self._phases[-1][1] != v.phase:
            self._phases.append((v.now, v.phase))
            if self._vu_phase is not None and v.phase != self._vu_phase:  # valid_until segment_end (v2)
                self.offset.reset(v.now, "segment_end")
                cleared = self.layer.clear_edit()  # Task 18 fix M1: a repeat after the change starts at 50 % again
                self.log.append({"type": "segment_end", "t": round(v.now, 3), "from": self._vu_phase,
                                 "to": v.phase, "layer_cleared": cleared})
                self._vu_phase = None
        no = self.stream.timed_out(v.now)
        if no is not None:
            self.log.append({"type": "timeout", "no": no, "t": round(v.now, 3)})
        cams = [c for c in self.p.cameras if v.frames.get(c) is not None]
        est = self.ledger.prices.krw_upper(estimate_input_tokens(self.est_text_tokens, cams), self.p.max_output_tokens)
        ok, why = self.stream.next_send(v.now, bool(v.near or v.phase in CONTACT_PHASES), est)
        if ok:
            self._send(v, cams, est)
        elif why in ("budget", "pause", "fatal") and why != self._hold:
            self.log.append({"type": "hold_send", "why": why, "t": round(v.now, 3), "ledger": self.ledger.state()})
        if why == "budget":
            self.budget_hit = True
        self._hold = None if ok else why
        a = 1.0 if v.authority is None else min(1.0, max(0.0, float(v.authority)))
        self.a_now = a
        self._authority(v, a)
        step = self.offset.step(v.now, v.dt, authority=a)
        if self.stag.update(v.now, v.tcp_p, self.offset.applied[:3]):
            self.flag("no_progress", v.now)
        return TickOut(step, self.p.slow_factor if self.stream.slowed(v.now) else 1.0)

    def _authority(self, v: TickView, a: float) -> None:
        """Time share per stratum (a = 0 / 0 < a < 1 / a = 1) and a sparse log row when the stratum or the source
        changes (the value inside the band ramps every tick; the summary share carries it)."""
        st = "a0" if a <= 0.0 else "a1" if a >= 1.0 else "band"
        self.auth_s[st] += v.dt
        if (st, v.authority_src) != self._auth_last:
            self._auth_last = (st, v.authority_src)
            self.log.append({"type": "authority", "t": round(v.now, 3), "a": round(a, 4), "src": v.authority_src})

    def arrow(self, v: TickView):
        """(vector or None, source) of the committed arrow: v1 the decision-token centre; v2 committed_arrow."""
        if not self.v2:
            return next_motion_vec(v.committed), None
        return committed_arrow(self.chunk_vec_last, v.committed, v.phase, self.backend)

    def predict(self, v: TickView):
        """(predicted tip at arrival, method label) by CoupleParams.predict_mode (plan Task 19, ruling R19)."""
        rem = self.offset.rem[:3]
        if self.p.predict_mode == "extrapolate":
            return (predict_ee(self.trace.window(v.now, 0.5), self.stream.L_hat, self.p.predict_cap_m, rem),
                    "extrapolate: 0.5 s tip velocity x horizon (capped) + remaining correction")
        vec, src = committed_arrow(self.chunk_vec_last, v.committed, v.phase, self.backend)
        return (predict_chunk(v.tcp_p, vec, rem),
                f"chunk: tip now + executing chunk displacement ({src}) + remaining correction, no extrapolation")

    def request(self, v: TickView, no: int, events: list, cams: list) -> dict:
        nxt, src = self.arrow(v)
        pred, method = self.predict(v)
        req = {"schema": SCHEMA_IDS[self.p.prompt_version], "mode": self.p.request_mode, "request_no": no,
               "t_state": round(v.now, 3),
               "task": self.task, "active_arm": self.p.active_arm, "cameras": list(cams), "tip_now_m": _r(v.tcp_p),
               "vla_now": {"stage": v.stage, "phase": v.phase, "committed": dict(sorted(v.committed.items())),
                           "next_motion_m": None if nxt is None else _r(nxt), "motion": v.motion},
               "predicted_ee_at_arrival": {"pos_m": _r(pred), "horizon_s": round(self.stream.L_hat, 2),
                                           "gripper": gripper_word(v.phase, v.t1),
                                           "method": method},
               "events": list(events)}
        if self.p.request_mode == "F1":
            req["flow_state"] = {"last_command": self.layer.flow_last(), "task_progress": self.layer.progress,
                                 "active_offset": self.offset.state_json()}
        if self.v2:
            req["vla_now"]["arrow_src"] = src
            req["since_last_request"] = self._since(v)
        return req

    def _send(self, v: TickView, cams: list, est: float) -> None:
        no, events = self.stream.sent(v.now)
        req = self.request(v, no, events, cams)
        frames = {c: np.asarray(v.frames[c]).copy() for c in cams}
        raw = (v.cams() if callable(v.cams) else v.cams) if (self.p.overlay and cams) else None
        models = {c: CamModel.from_dict(raw[c]) for c in cams if raw and c in raw}
        pts = [q for _, q in self.trace.window(v.now, self.p.trace_s)]
        req["trace_uv"] = polylines(models, pts[::-1])
        tip, off = np.asarray(v.tcp_p, float).copy(), self.offset.rem[:3].copy()
        nxt = self.arrow(v)[0]
        self._tip_at[no] = tip
        self._sent_state[no] = {"tip": tip, "applied": self._applied_now.copy(), "grip": grip_state(v.t1),
                                "phase": v.phase, "pred": np.asarray(req["predicted_ee_at_arrival"]["pos_m"], float)}
        self.ledger.reserve(self.key(no), est)
        astra, p, ep = self.astra, self.p, self.episode
        axis, horizon = self.v2 and p.axis_guide, self.stream.L_hat

        def run():  # worker thread: overlay, JPEG, request hash, the call
            images, ax = {}, []
            for c, img in frames.items():
                if c in models:
                    img = draw_overlay(img, models[c], tip=tip, trace=pts, next_vec=nxt, offset_vec=off,
                                       wrist=c != "cam_head")
                    if axis and c == "cam_head":  # head only (E-ACC arm 'ax')
                        img, ok = draw_axisguide(img, models[c], tip)
                        if ok:
                            ax.append(c)
                images[c] = jpeg_bytes(img)
            drawn = drawn_elements(models, tip=tip, trace=pts, next_vec=nxt, offset_vec=off, axisguide=ax)
            inp = self._build(req, images, drawn, horizon)
            pid = self.prompt_id(axisguide=bool(ax))
            text_only = [{**m, "content": [x for x in m["content"] if x.get("type") != "input_image"]} for m in inp]
            h, ims, body = request_body({"api": "astra-couple", "model": getattr(astra, "model", ""),
                                         "effort": p.effort, "max_out": p.max_output_tokens, "prompt_id": pid,
                                         "input": text_only}, images)
            rec = astra.call(inp, p.effort, p.max_output_tokens, {"couple_no": no, "episode": ep, "prompt_id": pid})
            lat = getattr(astra, "synthetic_latency", None)
            return {"latency_s": lat if lat is not None else rec.t_done - rec.t_send, "rec": rec,
                    "req_hash": (h, ims), "req_body": body, "images_raw": images,
                    "text_chars": len(inp[0]["content"][0]["text"]), "prompt_id": pid}
        self.submit(v.now, run, getattr(astra, "synthetic_latency", None),
                    {"kind": "couple", "no": no, "episode": ep, "t_state": v.now, "cameras": list(cams)})
        self.log.append({"type": "send", "no": no, "t": round(v.now, 3), "events": list(events),
                         "cameras": list(cams), "est_krw": round(est, 4), "overlay": sorted(models)})

    # ------------------------------------------------------------------ deliveries
    def on_delivery(self, r: dict, now: float, t1: dict) -> None:
        m, rec = r["meta"], r["rec"]
        no = m["no"]
        api_error = bool(getattr(rec, "api_error", False))
        code = getattr(rec, "error_code", None) or rec.error
        cost = self.ledger.charge(self.key(no), rec.usage or None,
                                  {"no": no, "resp_model": rec.model_field, "error": rec.error,
                                   "error_message": getattr(rec, "error_message", None)}, api_error=api_error)
        if api_error and code in FATAL_ERRORS:  # D1: stop sending for the rest of the run (every ledger on the file)
            self.ledger.mark_fatal(code, getattr(rec, "error_message", None))
        h, ims = r["req_hash"]
        self.blobs[h] = ("json", r["req_body"])
        for c, b in (r.get("images_raw") or {}).items():
            self.blobs[ims[c]] = ("jpg", b)
        if r.get("text_chars"):
            self.est_text_tokens = max(1, int(r["text_chars"]) // 4)
        row = {"type": "answer", "no": no, "t_state": round(m["t_state"], 3), "t_deliver": round(r["t_deliver"], 3),
               "latency_s": round(float(r["latency_s"]), 3), "cost_krw": round(cost, 4), "usage": rec.usage,
               "error": rec.error, "model": rec.model_field, "effort": rec.effort, "request_sha256": h,
               "image_sha256": ims, "output_text": rec.output_text,
               "prompt_id": r.get("prompt_id") or self.prompt_id()}
        if api_error:
            row.update(error_code=getattr(rec, "error_code", None), error_message=getattr(rec, "error_message", None))
        if self.stream.is_late(no):
            row["late"] = True
            self.log.append(row)
            return
        a, ok = None, rec.error is None
        if ok:
            try:
                a = parse_answer(rec.output_text, self.p.request_mode, m["cameras"], no, m["t_state"],
                                 r["t_deliver"], version=self.p.prompt_version)
            except SchemaError as e:
                ok, row["schema_error"] = False, e.problems
        self.stream.delivered(no, now, ok, float(r["latency_s"]))
        if not ok:
            self.log.append(row)
            return
        rc = self._reconcile(a, no, now, t1)
        on = self.p.reconcile_apply  # False: verdict logged only, the pre-Task-19 path (gate incl. stale drop)
        a = gate_answer(a, self.p, t1, stale_ok=on and rc["verdict"] == "valid")
        rc["action"] = self._apply_verdict(a, rc) if on else "log_only"
        self._rc[no]["reconcile"]["action"] = rc["action"]
        res = self.layer.on_answer(a, authority=self.a_now)
        if res.action in ("apply", "confirm"):
            self.offset.command(res.key, res.edit.vec6(), res.weight, now, self.stream.L_hat)
            self._vu_phase = self._phases[-1][1] if a.valid_until == "segment_end" and self._phases else None
        elif res.action == "flip":
            self.offset.reset(now, "flip")
            self._vu_phase = None
        elif res.action == "stop_confirmed":
            self.stop_confirmed_t = now
            self.flag("astra_stop_confirmed", now)
        if a.info_request == "slow_down":
            self.stream.request_slow(now)
        self.last, self.last_t = a, now
        row.update(gate=a.gate, notes=list(a.notes), diff=a.diff, command=a.command, execution=a.execution,
                   intent=a.intent, confidence=a.confidence, claims=[list(c) for c in a.claims],
                   takeover_ok=a.takeover_ok, layer=res.action, weight=res.weight, age_s=round(a.age, 3),
                   info_request=a.info_request)
        if self.v2:  # Astra's raw plan (reference) + the layer's plan action; the agreed plan is layer.plan
            row.update(segment=a.segment, valid_until=a.valid_until, plan=res.plan, authority=round(self.a_now, 4))
        self.log.append(row)

    def _reconcile(self, a, no: int, now: float, t1: dict) -> dict:
        """canon §91 arrival reconciliation of one valid delivered answer (reconcile.classify, before the gate): the
        state at its t_state (saved at send) vs now, and its raw command vs the VLA's own motion since t_state (tip
        displacement minus the coupling offset applied in that time). Logs one `reconcile` row (E-AT label candidate
        flag on done / conflict, canon §88: joined to the episode outcome later by episode + no) and keeps the
        verdict for the next request's since_last_request."""
        st = self._sent_state.pop(no, None) or {"tip": self._tip_now, "applied": self._applied_now,
                                                 "grip": grip_state(t1), "phase": self._phases[-1][1], "pred": None}
        tip_now = self._tip_now if self._tip_now is not None else st["tip"]
        tip_d = tip_now - st["tip"]
        off_d = self._applied_now - st["applied"]
        vla = tip_d - off_d
        e = a.edit if a.command == "edit" else None
        phase_now, grip_now = self._phases[-1][1], grip_state(t1)
        c = classify(command=a.command, edit_dp=None if e is None else e.dp, edit_gripper=None if e is None
                     else e.gripper, plan_do=(a.segment or {}).get("do"), vla_motion=vla, phase0=st["phase"],
                     phase1=phase_now, grip0=st["grip"], grip1=grip_now, age=a.age, p=self.p)
        t0 = a.t_state - 1e-9
        row = {"type": "reconcile", "no": no, "episode": self.episode, "t": round(now, 3), **c,
               "age_s": round(a.age, 3), "command": a.command, "edit_dp": None if e is None else _r(e.dp),
               "vla_motion_m": _r(vla), "tip_moved_m": _r(tip_d), "offset_applied_m": _r(off_d),
               "seg_from": st["phase"], "seg_to": phase_now, "grip_from": st["grip"], "grip_to": grip_now,
               "steps": sum(1 for t, _ in self._exec if t >= t0),
               "chunks": sum(1 for t, ch in self._exec if ch and t >= t0),
               "gripper_events": [{"t": round(t, 3), "gripper": w} for t, w in self._grip_ev if t > t0 + 2e-9],
               "fast_contra": sum(1 for t in self._contra_t if t >= t0),
               "pred_err_m": None if st["pred"] is None else _r1(np.linalg.norm(tip_now - st["pred"])),
               "a": round(self.a_now, 4), "effective": round(c["factor"] * self.a_now, 6),
               "eat_candidate": c["verdict"] in ("done", "conflict"), "outcome": None}
        self.log.append(row)
        raw = None if e is None else {**e.to_json(), "valid_until": a.valid_until}
        self._rc[no] = {"command": a.command, "edit": raw,
                        "reconcile": {"verdict": c["verdict"], "reason": c["reason"],
                                      "vla_motion_m": row["vla_motion_m"], "cos": c["cos"],
                                      "frac_done": c["frac_done"], "age_s": round(a.age, 1)}}
        return row

    @staticmethod
    def _apply_verdict(a, rc: dict) -> str:
        """The verdict's effect on the GATED answer (what the layer then sees): changed -> an edit / stop becomes
        continue (assessment kept); conflict -> an edit is held (continue; the evidence rides the next request);
        done -> the edit translation x factor, skipped (continue) at factor 0; valid -> unchanged."""
        v = rc["verdict"]
        if a.command not in ("edit", "stop"):
            return "none"
        if v == "changed" or (v == "conflict" and a.command == "edit"):
            a.command, a.edit = "continue", None
            return "dropped" if v == "changed" else "held"
        if v == "done" and a.command == "edit":
            if rc["factor"] <= 0.0:
                a.command, a.edit = "continue", None
                return "skipped"
            a.edit.dp = np.asarray(a.edit.dp, float) * rc["factor"]
            return "shrunk"
        return "unchanged"

    # ------------------------------------------------------------------ per decision step / gate
    def on_step(self, committed: dict, outcome: str, now: float, chunk_vec=None) -> None:
        """chunk_vec: the executed motion of the current expert chunk (fused backend, a 3-vector); None on the
        modular backend. vla_vec drives the VLA fast check (canon §84 supplement 4: chunk-level adherence, not the
        decision token alone). An adherence row is logged whenever the offset is active or chunk_vec is given, even
        when the fast check itself is skipped (offset inactive)."""
        self.chunk_vec_last = None if chunk_vec is None else np.asarray(chunk_vec, float).copy()  # v2 arrow
        self._exec.append((now, chunk_vec is not None))  # the §91 execution trace (plan Task 19)
        dec_vec = committed_vector(committed)
        vla_vec = chunk_vec if chunk_vec is not None else dec_vec
        src = "chunk" if chunk_vec is not None else "decision"
        active = self.offset.active
        if not active:
            self.fast.reset()
        else:
            if self.fast.on_step(vla_vec, self.offset.direction()):
                self.offset.scale_remaining(self.p.contra_factor, now, "vla_contra")
                self._contra_t.append(now)
                self.flag("offset_contradicted", now)
            if outcome in ("DEVIATE", "CONTRADICT"):
                self.flag("offset_vs_b", now)
        if not active and chunk_vec is None:
            return
        off_dir = self.offset.direction()
        self.log.append({"type": "adherence", "t": round(now, 3), "src": src,
                         "cos_vs_offset": _r1(adherence_cos(vla_vec, off_dir)),
                         "cos_chunk_vs_decision": _r1(adherence_cos(chunk_vec, dec_vec)),
                         "follows_offset": follows(vla_vec, off_dir, self.p),
                         "follows_decision": follows(chunk_vec, dec_vec, self.p)})

    def irrev_allowed(self, kind: str, now: float, t1: dict, near: bool) -> bool:
        ok, _ = self.gate.allow(kind, now, self.last, self.last_t, t1, near)
        if not ok and self.gate.mismatch_due(kind, now):
            self.flag("layer_mismatch", now)
        return ok

    # ------------------------------------------------------------------ summary
    def summary(self) -> dict:
        ans = [r for r in self.log if r["type"] == "answer" and not r.get("late")]
        good = [r for r in ans if "gate" in r]
        lat = [r["latency_s"] for r in ans if r.get("error") is None]

        def pct(xs, q):
            return round(float(np.percentile(xs, q)), 3) if xs else None

        def rate(rows, field):
            xs = [r[field] for r in rows if r[field] is not None]
            return {"n": len(xs), "follow_rate": round(sum(xs) / len(xs), 4) if xs else None}
        adh = [r for r in self.log if r["type"] == "adherence"]
        rec = [r for r in self.log if r["type"] == "reconcile"]
        T =sum(self.auth_s.values())
        auth = {"share": {k: round(v / T, 4) if T > 0 else None for k, v in self.auth_s.items()},
                "seconds": round(T, 3)}
        return {"calls_sent": self.stream.n_sent, "answers": len(good),
                "schema_errors": sum(1 for r in ans if "schema_error" in r),
                "api_errors": sum(1 for r in ans if r.get("error")), "timeouts": self.stream.counts["timeouts"],
                "late": sum(1 for r in self.log if r.get("late")), "max_inflight": self.stream.max_inflight,
                "max_outstanding": self.stream.max_outstanding, "latency_s": {"p50": pct(lat, 50), "p95": pct(lat, 95)},
                "answer_age_s": {"p50": pct([r["age_s"] for r in good], 50)},
                "cost_krw": round(sum(r.get("cost_krw", 0.0) for r in self.log if r["type"] == "answer"), 4),
                "gates": dict(Counter(r["gate"] for r in good)), "layer": dict(self.layer.counts),
                "offset": self.offset.stats(), "irrev": dict(self.gate.counts),
                "events": dict(Counter(e["event"] for e in self.events)),
                "events_suppressed": dict(self.events_suppressed),
                "events_persisting": dict(self.events_persisting), "fatal": getattr(self.ledger, "fatal", None),
                "unanswered": self._unanswered(), "budget_excluded": self.budget_hit,
                "stop_confirmed_t": self.stop_confirmed_t, "prompt_id": self.prompt_id(),
                "schema": SCHEMA_IDS[self.p.prompt_version], "segment_plan": self.layer.plan,
                "adherence": {"chunk_vs_offset": rate(adh, "follows_offset"),
                             "chunk_vs_decision": rate(adh, "follows_decision")},
                "authority": auth,
                "reconcile": {"counts": dict(Counter(r["verdict"] for r in rec)),
                              "reasons": dict(Counter(r["reason"] for r in rec)),
                              "actions": dict(Counter(r.get("action") for r in rec)),
                              "eat_candidates": sum(1 for r in rec if r["eat_candidate"]),
                              "outcome_join": "episode+no"},
                "params": self.p.to_json(), "ledger": self.ledger.state()}

    def _unanswered(self) -> dict:
        """B7: this episode's never-answered requests -- still reserved (charged as unanswered at close) plus those
        already charged by close(); counted apart from the answered cost_krw."""
        pend = [v for k, v in self.ledger.reserved.items() if k.startswith(f"e{self.episode}:")]
        n, krw = self.unanswered_closed
        return {"n": n + len(pend), "krw": round(krw + sum(pend), 4)}

    def close(self) -> None:
        n, krw = self.ledger.finalize(prefix=f"e{self.episode}:")
        self.unanswered_closed = (self.unanswered_closed[0] + n, self.unanswered_closed[1] + krw)
