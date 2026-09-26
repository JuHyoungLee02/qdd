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
token is never assumed to steer the chunk on its own (canon §84 supplement 4-5, E-MA2/E-SR0)."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

import numpy as np

from ..runtime.models import jpeg_bytes
from ..runtime.reqhash import request_body
from .cost import estimate_input_tokens
from .gate import gate_answer
from .layer import AstraLayer
from .offset import OffsetApplier
from .overlay import CamModel, EETrace, draw_overlay, polylines
from .prompt import PROMPT_ID, build_input
from .schema import SCHEMA_ID, SchemaError, parse_answer
from .stream import SerialStream
from .twolayer import NoProgress, TwoLayerGate, VlaFastCheck, adherence_cos, committed_vector, follows

CONTACT_PHASES = ("descend", "close", "place_descend", "open")
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


def predict_ee(trace: list, horizon: float, cap: float, extra) -> np.ndarray:
    (t0, p0), (t1, p1) = trace[0], trace[-1]
    d = (p1 - p0) / (t1 - t0) * horizon if t1 > t0 else np.zeros(3)
    n = float(np.linalg.norm(d))
    if n > cap:
        d = d * (cap / n)
    return p1 + d + np.asarray(extra, float)


def gripper_word(phase: str, t1: dict) -> str:
    if phase == "close":
        return "closing"
    if phase == "open":
        return "opening"
    g = t1.get("gripper_open")
    return "open" if g is True else "closed" if g is False else "unknown"


class CoupleDriver:
    def __init__(self, p, astra, ledger, submit, task: str, episode: int = 1):
        self.p, self.astra, self.ledger, self.submit, self.task, self.episode = p, astra, ledger, submit, task, episode
        self.stream = SerialStream(p, ledger)
        self.layer, self.offset, self.gate = AstraLayer(p), OffsetApplier(p), TwoLayerGate(p)
        self.fast, self.stag = VlaFastCheck(p), NoProgress(p)
        self.trace = EETrace(keep_s=max(p.trace_s, 0.5) + 1.0)
        self.last, self.last_t = None, None
        self.log, self.events, self.blobs = [], [], {}
        self.est_text_tokens = p.est_text_tokens
        self.budget_hit, self.stop_confirmed_t, self._hold = False, None, None
        self.auth_s, self._auth_last = {"a0": 0.0, "band": 0.0, "a1": 0.0}, None

    def key(self, no: int) -> str:
        return f"e{self.episode}:{no}"

    def flag(self, name: str, now: float) -> None:
        self.stream.flag(name, now)
        self.events.append({"t": round(now, 3), "event": name})

    # ------------------------------------------------------------------ per tick
    def tick(self, v: TickView) -> TickOut:
        self.trace.add(v.now, v.tcp_p)
        no = self.stream.timed_out(v.now)
        if no is not None:
            self.log.append({"type": "timeout", "no": no, "t": round(v.now, 3)})
        cams = [c for c in self.p.cameras if v.frames.get(c) is not None]
        est = self.ledger.prices.krw_upper(estimate_input_tokens(self.est_text_tokens, cams), self.p.max_output_tokens)
        ok, why = self.stream.next_send(v.now, bool(v.near or v.phase in CONTACT_PHASES), est)
        if ok:
            self._send(v, cams, est)
        elif why in ("budget", "pause") and why != self._hold:
            self.log.append({"type": "hold_send", "why": why, "t": round(v.now, 3), "ledger": self.ledger.state()})
        if why == "budget":
            self.budget_hit = True
        self._hold = None if ok else why
        a = 1.0 if v.authority is None else min(1.0, max(0.0, float(v.authority)))
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

    def request(self, v: TickView, no: int, events: list, cams: list) -> dict:
        nxt = next_motion_vec(v.committed)
        pred = predict_ee(self.trace.window(v.now, 0.5), self.stream.L_hat, self.p.predict_cap_m, self.offset.rem[:3])
        req = {"schema": SCHEMA_ID, "mode": self.p.request_mode, "request_no": no, "t_state": round(v.now, 3),
               "task": self.task, "active_arm": self.p.active_arm, "cameras": list(cams), "tip_now_m": _r(v.tcp_p),
               "vla_now": {"stage": v.stage, "phase": v.phase, "committed": dict(sorted(v.committed.items())),
                           "next_motion_m": None if nxt is None else _r(nxt), "motion": v.motion},
               "predicted_ee_at_arrival": {"pos_m": _r(pred), "horizon_s": round(self.stream.L_hat, 2),
                                           "gripper": gripper_word(v.phase, v.t1),
                                           "method": "0.5 s tip velocity x horizon (capped) + remaining correction"},
               "events": list(events)}
        if self.p.request_mode == "F1":
            req["flow_state"] = {"last_command": self.layer.flow_last(), "task_progress": self.layer.progress,
                                 "active_offset": self.offset.state_json()}
        return req

    def _send(self, v: TickView, cams: list, est: float) -> None:
        no, events = self.stream.sent(v.now)
        req = self.request(v, no, events, cams)
        frames = {c: np.asarray(v.frames[c]).copy() for c in cams}
        raw = (v.cams() if callable(v.cams) else v.cams) if (self.p.overlay and cams) else None
        models = {c: CamModel.from_dict(raw[c]) for c in cams if raw and c in raw}
        pts = [q for _, q in self.trace.window(v.now, self.p.trace_s)]
        req["trace_uv"] = polylines(models, pts[::-1])
        tip, nxt, off = np.asarray(v.tcp_p, float).copy(), next_motion_vec(v.committed), self.offset.rem[:3].copy()
        self.ledger.reserve(self.key(no), est)
        astra, p, task, ep = self.astra, self.p, self.task, self.episode
        pid = PROMPT_ID[p.request_mode]

        def run():  # worker thread: overlay, JPEG, request hash, the call
            images = {}
            for c, img in frames.items():
                if c in models:
                    img = draw_overlay(img, models[c], tip=tip, trace=pts, next_vec=nxt, offset_vec=off,
                                       wrist=c != "cam_head")
                images[c] = jpeg_bytes(img)
            inp = build_input(req, images, p, task)
            text_only = [{**m, "content": [x for x in m["content"] if x.get("type") != "input_image"]} for m in inp]
            h, ims, body = request_body({"api": "astra-couple", "model": getattr(astra, "model", ""),
                                         "effort": p.effort, "max_out": p.max_output_tokens, "prompt_id": pid,
                                         "input": text_only}, images)
            rec = astra.call(inp, p.effort, p.max_output_tokens, {"couple_no": no, "episode": ep, "prompt_id": pid})
            lat = getattr(astra, "synthetic_latency", None)
            return {"latency_s": lat if lat is not None else rec.t_done - rec.t_send, "rec": rec,
                    "req_hash": (h, ims), "req_body": body, "images_raw": images,
                    "text_chars": len(inp[0]["content"][0]["text"])}
        self.submit(v.now, run, getattr(astra, "synthetic_latency", None),
                    {"kind": "couple", "no": no, "episode": ep, "t_state": v.now, "cameras": list(cams)})
        self.log.append({"type": "send", "no": no, "t": round(v.now, 3), "events": list(events),
                         "cameras": list(cams), "est_krw": round(est, 4), "overlay": sorted(models)})

    # ------------------------------------------------------------------ deliveries
    def on_delivery(self, r: dict, now: float, t1: dict) -> None:
        m, rec = r["meta"], r["rec"]
        no = m["no"]
        cost = self.ledger.charge(self.key(no), rec.usage or None,
                                  {"no": no, "resp_model": rec.model_field, "error": rec.error})
        h, ims = r["req_hash"]
        self.blobs[h] = ("json", r["req_body"])
        for c, b in (r.get("images_raw") or {}).items():
            self.blobs[ims[c]] = ("jpg", b)
        if r.get("text_chars"):
            self.est_text_tokens = max(1, int(r["text_chars"]) // 4)
        row = {"type": "answer", "no": no, "t_state": round(m["t_state"], 3), "t_deliver": round(r["t_deliver"], 3),
               "latency_s": round(float(r["latency_s"]), 3), "cost_krw": round(cost, 4), "usage": rec.usage,
               "error": rec.error, "model": rec.model_field, "effort": rec.effort, "request_sha256": h,
               "image_sha256": ims, "output_text": rec.output_text, "prompt_id": PROMPT_ID[self.p.request_mode]}
        if self.stream.is_late(no):
            row["late"] = True
            self.log.append(row)
            return
        a, ok = None, rec.error is None
        if ok:
            try:
                a = parse_answer(rec.output_text, self.p.request_mode, m["cameras"], no, m["t_state"],
                                 r["t_deliver"])
            except SchemaError as e:
                ok, row["schema_error"] = False, e.problems
        self.stream.delivered(no, now, ok, float(r["latency_s"]))
        if not ok:
            self.log.append(row)
            return
        a = gate_answer(a, self.p, t1)
        res = self.layer.on_answer(a)
        if res.action in ("apply", "confirm"):
            self.offset.command(res.key, res.edit.vec6(), res.weight, now, self.stream.L_hat)
        elif res.action == "flip":
            self.offset.reset(now, "flip")
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
        self.log.append(row)

    # ------------------------------------------------------------------ per decision step / gate
    def on_step(self, committed: dict, outcome: str, now: float, chunk_vec=None) -> None:
        """chunk_vec: the executed motion of the current expert chunk (fused backend, a 3-vector); None on the
        modular backend. vla_vec drives the VLA fast check (canon §84 supplement 4: chunk-level adherence, not the
        decision token alone). An adherence row is logged whenever the offset is active or chunk_vec is given, even
        when the fast check itself is skipped (offset inactive)."""
        dec_vec = committed_vector(committed)
        vla_vec = chunk_vec if chunk_vec is not None else dec_vec
        src = "chunk" if chunk_vec is not None else "decision"
        active = self.offset.active
        if not active:
            self.fast.reset()
        else:
            if self.fast.on_step(vla_vec, self.offset.direction()):
                self.offset.scale_remaining(self.p.contra_factor, now, "vla_contra")
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
        T = sum(self.auth_s.values())
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
                "events": dict(Counter(e["event"] for e in self.events)), "budget_excluded": self.budget_hit,
                "stop_confirmed_t": self.stop_confirmed_t, "prompt_id": PROMPT_ID[self.p.request_mode],
                "adherence": {"chunk_vs_offset": rate(adh, "follows_offset"),
                             "chunk_vs_decision": rate(adh, "follows_decision")},
                "authority": auth,
                "params": self.p.to_json(), "ledger": self.ledger.state()}

    def close(self) -> None:
        self.ledger.finalize(prefix=f"e{self.episode}:")
