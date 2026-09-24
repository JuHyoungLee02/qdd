"""OursRuntime: the harness-neutral closed-loop policy core (canon §42 OursPolicy, §45, §58; D23 §2).

act(obs) is non-blocking (except the clock's simlat/sync rules): it returns the current executor output for one
100 Hz tick. Background work runs in a thread pool: (a) decision calls every T_c (staggered, up to N_max in flight,
M4 §4.3), (b) the Astra heartbeat (§45). Delivery follows the injected clock (sync / simlat / wall, clock.py).
Per tick, in this order: M1 observation -> schedule calls -> deliver answers (votes -> M4 ledger, prefix commit) ->
decision-step boundary ((b) check of the finished step, M4 signals, decisions of the new step) -> executor.
Back-ends (models.py): modular = decisions -> skill S (+ residual-R hook) -> IK; fused = decisions + action chunk,
the chunk is played only while its own decisions agree with the committed ones (else hold).

obs (dict, built by a harness adapter):
  sim_time, joint_pos (8), images {name: new frame} (only on new frames), m1 {"raw", "present"} (M1 observation,
  table frame; here the sim oracle = E0 oracle condition), kin (tcp_pose() -> (p, q) world; ik(p, q, max_dq) -> 7
  joints), table_z, low / high (action bounds).
"""
from __future__ import annotations

import math
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field

import numpy as np

from ..config import CFG
from ..predicates import PredicateState
from ..sim.planner import PHASE_TIMEOUT_S
from ..sim.snapshot import obs_from_json, pred_changes, text_state
from .astra_hb import EFFORT, HB_PROMPT_ID, MAX_OUT, HeartbeatScheduler, heartbeat_input, parse_decision
from .clock import DeliveryQueue
from .m4 import CommitLedger, M4Params, Vote
from .models import DECISION_QUESTIONS, build_live_request, fused_state_text, jpeg_bytes
from .skills import PickPlaceSkill, apply_residual, residual_hook_zero

FRAME_SAMPLE_S = 5.0  # sampled frames kept for inspection (plus one per phase change)


@dataclass
class RuntimeConfig:
    """Logged as EvalSpec.policy_config (canon §42 logging). The first three fields are inspect_robots
    PolicyConfig's (DefaultController(replan_interval=1): one action per act())."""
    action_horizon: int = 1
    replan_interval: int = 1
    temperature: float | None = None
    backend: str = "modular"  # modular (Jev-L -> M4 -> S + R) | fused (one call: decisions + chunk)
    selector: str = "mock"  # jevl | mock | mock_fused
    model_id: str = ""
    model_path: str = ""
    layout: str = ""  # H | HW (canon §59) for jevl
    call_mode: str = ""  # lead | base
    clock: str = "simlat"
    T_c: float = 0.33
    control_hz: float = 100.0
    m4: dict = field(default_factory=lambda: asdict(M4Params()))
    question_ids: dict = field(default_factory=dict)
    state_repr: str = "S1 1 mm (e3lite.state_text, canon §54) from the M1 oracle observation (E0 oracle condition)"
    astra_model: str = "gpt-6-astra"
    astra_effort: str = EFFORT
    astra_prompt_id: str = HB_PROMPT_ID
    astra_mode: str = "mock"  # api | mock
    hb_N_s: float = 5.0
    hb_timeout_s: float = 15.0
    ik_max_dq: float = 0.02  # rad per 10 ms tick
    chunk_lead_s: float = 0.15  # fused: request the chunk of step k+1 this long before it starts (> chunk latency)
    residual_hook: str = "zero (R not trained)"


def _pct(xs, q):
    return float(np.percentile(xs, q)) if xs else None


class OursRuntime:
    def __init__(self, cfg: RuntimeConfig, model, astra=None, wall=time.monotonic, residual_hook=residual_hook_zero,
                 instruction: str = "Put the red mug on the blue tray.", workers: int = 6):
        self.cfg, self.model, self.astra, self.wall = cfg, model, astra, wall
        self.residual_hook, self.instruction = residual_hook, instruction
        self.pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="ours")
        self.dt = 1.0 / cfg.control_hz

    # ------------------------------------------------------------------ lifecycle
    def reset(self) -> None:
        p = M4Params(**self.cfg.m4)
        self.ledger = CommitLedger(p, DECISION_QUESTIONS)
        self.q = DeliveryQueue(self.cfg.clock, wall=self.wall)
        self.skill = PickPlaceSkill(dt=self.dt)
        self.hb = HeartbeatScheduler(self.cfg.hb_N_s, self.cfg.hb_timeout_s)
        self.ps = PredicateState()
        self.prev_pred, self.stream = {}, []
        self.frames, self.frame_t = {}, {}
        self.cur_k, self.next_call, self.early, self.hold_step = None, 0.0, False, False
        self.n_calls, self.n_hb, self.dropped_hb = 0, 0, set()
        self.calls, self.slots_log, self.astra_log, self.events, self.sampled = [], [], [], [], []
        self.chunks, self.chunk_req, self.chunk_log = {}, set(), []
        self.chunk_stats = {"played": 0, "held": 0, "requested": 0, "delivered": 0, "stale_dec": 0}
        self.last_a, self.prev_cmd, self.t0_wall, self.t_last, self.q_meas = None, None, None, 0.0, None
        self._last_sample, self._phase_seen = -1e9, None

    def close(self) -> None:
        self.pool.shutdown(wait=False, cancel_futures=True)
        if hasattr(self.model, "close"):
            self.model.close()

    # ------------------------------------------------------------------ helpers
    def _now(self, obs) -> float:
        if self.cfg.clock == "wall":
            return self.wall() - self.t0_wall
        return float(obs["sim_time"])

    def _m1(self, obs, now):
        raw, present = obs["m1"]["raw"], obs["m1"]["present"]
        objs, grip, contacts, support = obs_from_json(raw)
        pred = self.ps.update(objs, grip, contacts, support)
        self.stream += pred_changes(self.prev_pred, pred, now)
        self.stream = [c for c in self.stream if c[0] >= now - 3.0]
        self.prev_pred = pred
        return raw, present, pred, support

    def _decision_ctx(self, now, raw, present, pred, support, obs):
        slots = self.ledger.target_slots(now)
        sk = self.skill
        moving = self.prev_cmd is not None and float(np.linalg.norm(sk.cmd_pos - self.prev_cmd)) > 1e-5
        s0 = text_state(now, sk.phase, now - sk.t_phase0, PHASE_TIMEOUT_S.get(sk.phase, 60.0), pred, present,
                        support, bool(pred.get("gripper_open")), bool(pred.get("holding(o3)")), moving,
                        list(self.stream))
        req, shown = build_live_request(slots[0], sk.phase, s0, present, raw)
        ctx = {"t_state": now, "ds": slots[0], "slots": slots, "epoch": self.ledger.epoch, "phase": sk.phase,
               "req": req, "shown": shown, "images": {k: v.copy() for k, v in self.frames.items()},
               "joint_pos": np.asarray(obs["joint_pos"], float).copy()}
        if self.cfg.backend == "fused":  # canon §58: no S1 coordinates in the fused model's input
            ctx["privileged_s1"] = req["state"]  # used by the MOCK fused model only (flagged in its meta)
            ctx["req"] = {**req, "state": fused_state_text(self.instruction, sk.stage, sk.phase, obs["joint_pos"])}
        return ctx

    def _submit_decision(self, now, raw, present, pred, support, obs):
        ctx = self._decision_ctx(now, raw, present, pred, support, obs)
        self.n_calls += 1
        model = self.model

        def run():
            r = model.decide(ctx)
            return {"latency_s": r.latency_s, "res": r}
        meta = {"kind": "dec", "call_no": self.n_calls, "slots": ctx["slots"], "epoch": ctx["epoch"],
                "t_state": now, "phase": ctx["phase"], "anchor_g": list(raw["grip"]["pos"])}
        self.q.submit(now, self.pool.submit(run), fixed_latency=getattr(model, "synthetic_latency", None), meta=meta)

    def _submit_hb(self, now, pred):
        if self.astra is None:
            return
        self.n_hb += 1
        sk, L = self.skill, self.ledger
        dec = {k: L.decision(k, self.cur_k)[0] for k in DECISION_QUESTIONS} if self.cur_k is not None else {}
        outs = [s.get("outcome") for s in self.slots_log[-6:-1]]
        facts = {k: pred.get(k) for k in ("holding(o3)", "lifted(o3)", "on(o3,o5)", "upright(o3)")}
        summary = (f"t={now:.1f}s stage={sk.stage} phase={sk.phase} gripper_open={pred.get('gripper_open')}\n"
                   f"facts={facts}\ncurrent step decisions={dec}\nlast step checks={outs}\n"
                   f"premise_epoch={L.epoch} grasp_retries={sk.retries}")
        head = self.frames.get("cam_head")
        head = None if head is None else head.copy()
        astra, n = self.astra, self.n_hb

        def run():
            inp = heartbeat_input(summary, jpeg_bytes(head) if head is not None else None)
            rec = astra.call(inp, EFFORT, MAX_OUT, {"hb_no": n, "prompt_id": HB_PROMPT_ID})
            lat = getattr(astra, "synthetic_latency", None)
            return {"latency_s": lat if lat is not None else rec.t_done - rec.t_send, "rec": rec,
                    "summary": summary}
        self.hb.sent(now)
        self.q.submit(now, self.pool.submit(run), fixed_latency=getattr(astra, "synthetic_latency", None),
                      meta={"kind": "astra", "hb_no": n})

    # ------------------------------------------------------------------ deliveries
    def _deliver(self, r, now):
        m = r["meta"]
        if m["kind"] == "astra":
            return self._deliver_hb(r, now)
        if m["kind"] == "chunk":
            return self._deliver_chunk(r, now)
        res = r["res"]
        rec = {"call_no": m["call_no"], "t_state": round(m["t_state"], 4), "t_deliver": round(r["t_deliver"], 4),
               "latency_s": round(res.latency_s, 4), "slots": m["slots"], "epoch_sent": m["epoch"],
               "phase": m["phase"], "error": res.error, "call_id": res.call_id, "meta": res.meta,
               "answers": {q: [a["choice"], round(a["p_chosen"], 4) if a.get("p_chosen") is not None else None]
                           for q, a in res.answers.items()}, "votes": {}}
        if res.error is None:
            self.ledger.record_latency(res.latency_s)
            irr = self.skill.irreversible
            for q, a in res.answers.items():
                rec["votes"][q] = []
                for ds in m["slots"]:
                    v = Vote(ds=ds, question=q, choice=a["choice"], p_chosen=a.get("p_chosen"),
                             call_id=res.call_id, t_send=m["t_state"], t_recv=r["t_deliver"], t_state=m["t_state"],
                             premise_epoch=m["epoch"], qid=a.get("qid", ""))
                    rec["votes"][q].append(self.ledger.on_vote(v, now, irreversible=irr))
        self.calls.append(rec)

    def _deliver_hb(self, r, now):
        m = r["meta"]
        rec_ = r["rec"]
        if m["hb_no"] in self.dropped_hb:
            self.astra_log.append({"hb_no": m["hb_no"], "late_after_timeout": True, "t": round(now, 3)})
            return
        dec, note = parse_decision(rec_.output_text)
        self.hb.responded(now)
        entry = {"hb_no": m["hb_no"], "t_send": round(r["t_send"], 3), "t_deliver": round(r["t_deliver"], 3),
                 "latency_s": round(r["latency_s"], 3), "decision": dec, "note": note, "error": rec_.error,
                 "model": rec_.model_field, "usage": rec_.usage, "http": rec_.http_status,
                 "first_token_s": round(rec_.t_first_token - rec_.t_send, 3) if rec_.t_first_token else None}
        if dec in ("patch", "replace"):  # contract edit not implemented: premise epoch only (§45 합치기)
            entry["epoch"] = self.ledger.bump_epoch(f"astra_{dec}", now)
            self.early = True
        self.astra_log.append(entry)

    # ------------------------------------------------------------------ act
    def act(self, obs) -> tuple[np.ndarray, dict]:
        if self.t0_wall is None:
            self.t0_wall = self.wall()
        now = self._now(obs)
        self.t_last = now
        raw, present, pred, support = self._m1(obs, now)
        for name, img in (obs.get("images") or {}).items():
            self.frames[name], self.frame_t[name] = img, now
        kin, tz = obs["kin"], obs["table_z"]
        tcp_p, tcp_q = kin.tcp_pose()
        if self.cur_k is None and self.skill.__dict__.get("cmd_pos") is None:
            self.skill.reset(now, tcp_p, tcp_q)
        # (a) decision calls: staggered every T_c, <= N_max in flight; an early call pulls one periodic slot forward
        infl = sum(1 for it in self.q._items if it["meta"]["kind"] == "dec")
        if infl < self.ledger.n_max() and (now >= self.next_call - 1e-9 or self.early):
            self._submit_decision(now, raw, present, pred, support, obs)
            if self.early and now < self.next_call - 1e-9:
                self.next_call += self.cfg.T_c
            else:
                self.next_call = max(self.next_call + self.cfg.T_c, now)
            self.early = False
        # (c) Astra heartbeat
        if self.hb.timed_out(now):
            self.dropped_hb.add(self.n_hb)
            self.astra_log.append({"hb_no": self.n_hb, "timeout": True, "t": round(now, 3)})
            self.hb.drop_inflight(now)
        if self.astra is not None and self.hb.due(now):
            self._submit_hb(now, pred)
        # deliveries (clock) -> M4
        got = self.q.poll(now)
        for r in got:
            self._deliver(r, now)
        if got:
            for qq in DECISION_QUESTIONS:
                self.ledger.try_commit_prefix(qq, now)
        # decision-step boundary
        k = int(math.floor(now / self.cfg.T_c + 1e-9))
        if k != self.cur_k:
            self._boundary(k, now, tcp_p)
        if self.cfg.backend == "fused":
            self._maybe_request_chunk(now, obs)
        # executor
        a = self._execute(now, obs, raw, pred, tz, tcp_p)
        self._sample_frames(now)
        return a, {"ds": self.cur_k, "phase": self.skill.phase, "epoch": self.ledger.epoch}

    def _boundary(self, k, now, tcp_p):
        prev = self.cur_k
        entry = {"ds": k, "t": round(now, 4), "tcp": [round(float(v), 4) for v in tcp_p],
                 "cmd": [round(float(v), 4) for v in self.skill.cmd_pos]}
        if prev is not None:
            if self.cfg.backend == "fused":
                out, resid = self._joint_outcome()
            else:
                out, resid = self.skill.step_outcome(tcp_p)
            sig = self.ledger.on_step_executed(prev, out, now)
            entry.update(prev_outcome=out, prev_residual_mm=round(resid * 1e3, 1), signals=sig)
            self.hold_step = sig["hold"]
            if out in ("DEVIATE", "CONTRADICT") and self.cfg.backend != "fused":
                self.skill.reanchor(tcp_p)
            if sig["early_call"]:
                self.early = True
            for qq in DECISION_QUESTIONS:
                self.ledger.try_commit_prefix(qq, now)
        decs = self.ledger.mark_executed(k, now)
        dec = {} if self.hold_step else {q: c for q, (c, st) in decs.items() if c is not None}
        self.skill.begin_slot(k, dec)
        entry.update(decisions={q: list(v) for q, v in decs.items()}, hold=self.hold_step,
                     phase=self.skill.phase, stage=self.skill.stage)
        self.slots_log.append(entry)
        if self.slots_log and len(self.slots_log) >= 2:
            self.slots_log[-2]["outcome"] = entry.get("prev_outcome")
        self.cur_k = k

    def _joint_outcome(self):
        """Fused (b): measured arm joints vs the executed chunk target at the step end (the chunk is the fused
        path's ref(t)); gripper excluded (contact squeeze). Thresholds [가정] 0.05 / 0.15 rad."""
        if self.last_a is None or self.q_meas is None:
            return "OK", 0.0
        r = float(np.max(np.abs(np.asarray(self.last_a[:7]) - self.q_meas[:7])))
        return ("OK" if r <= 0.05 else "LAG" if r <= 0.15 else "DEVIATE"), r

    def _execute(self, now, obs, raw, pred, tz, tcp_p):
        kin = obs["kin"]
        q_meas = np.asarray(obs["joint_pos"], float)
        self.q_meas = q_meas
        cmd = self.skill.tick(now, raw, pred, tcp_p, tz)
        for e in cmd.events:
            self.events.append(e)
        self.prev_cmd = self.skill.cmd_pos.copy()
        if self.cfg.backend == "fused":
            a = self._play_chunk(now, q_meas)
        else:
            q7 = kin.ik(cmd.pos_w, cmd.quat_w, self.cfg.ik_max_dq)
            tgt = {"approach": "o3", "descend": "o3", "close": "o3", "lift": "o3"}.get(self.skill.phase, "o5")
            g = np.asarray(raw["grip"]["pos"], float)
            near = tgt in raw["objs"] and float(np.linalg.norm(np.asarray(raw["objs"][tgt]["pos"]) - g)) \
                <= CFG.near_in_m
            q7 = apply_residual(q7, self.residual_hook, {"obs": obs, "cmd": cmd, "dec": self.skill.dec}, near)
            a = np.concatenate([q7, [cmd.width]])
        lo, hi = obs["low"], obs["high"]
        a = np.clip(a, lo, hi)  # safety projection: action bounds
        self.last_a = a
        return a

    # ------------------------------------------------------------------ fused action path
    def _maybe_request_chunk(self, now, obs):
        """chunk(ctx, committed) for step k+1, chunk_lead_s before it starts, on the decisions M4 holds for it then
        (the stage-B expert is conditioned on committed decisions)."""
        kn = (self.cur_k or 0) + 1
        if kn in self.chunk_req or now < self.ledger.t_start(kn) - self.cfg.chunk_lead_s - 1e-9:
            return
        self.chunk_req.add(kn)
        dec = {q: self.ledger.decision(q, kn) for q in DECISION_QUESTIONS}
        committed = {q: c for q, (c, st) in dec.items() if c is not None}
        ctx = {"t_state": now, "ds": kn, "joint_pos": np.asarray(obs["joint_pos"], float).copy(),
               "images": {k: v.copy() for k, v in self.frames.items()},
               "text": fused_state_text(self.instruction, self.skill.stage, self.skill.phase, obs["joint_pos"])}
        model = self.model

        def run():
            r = model.chunk(ctx, committed)
            return {"latency_s": r.latency_s, "res": r}
        self.chunk_stats["requested"] += 1
        self.q.submit(now, self.pool.submit(run), fixed_latency=getattr(model, "synthetic_chunk_latency", None),
                      meta={"kind": "chunk", "ds": kn, "t_state": now, "dec": committed,
                            "status": {q: st for q, (c, st) in dec.items()}})

    def _deliver_chunk(self, r, now):
        m, res = r["meta"], r["res"]
        self.chunk_stats["delivered"] += 1
        self.chunk_log.append({"ds": m["ds"], "t_state": round(m["t_state"], 4), "t_deliver": round(r["t_deliver"], 4),
                               "latency_s": round(res.latency_s, 4), "dec": m["dec"], "status": m["status"],
                               "error": res.error})
        if res.error is None and res.chunk is not None:
            self.chunks[m["ds"]] = {"t_state": m["t_state"], "chunk": np.asarray(res.chunk, float),
                                    "dt": res.chunk_dt, "dec": m["dec"]}

    def _play_chunk(self, now, q_meas):
        """Play the chunk of the current step only if it was conditioned on the decisions being executed; else hold
        the last action (never a stop)."""
        from .fused_action import chunk_value
        c = self.chunks.get(self.cur_k)
        dec = {q: v for q, v in self.skill.dec.items() if v is not None}
        if c is not None and c["dec"] == dec and dec:
            self.chunk_stats["played"] += 1
            return chunk_value(c["chunk"], c["dt"], c["t_state"], now)
        if c is not None:
            self.chunk_stats["stale_dec"] += 1
        self.chunk_stats["held"] += 1
        return self.last_a if self.last_a is not None else q_meas

    def _sample_frames(self, now):
        ph = self.skill.phase
        if (now - self._last_sample >= FRAME_SAMPLE_S or ph != self._phase_seen) and self.frames \
                and len(self.sampled) < 40:
            for name, img in self.frames.items():
                self.sampled.append((round(now, 2), ph, name, img.copy()))
            self._last_sample, self._phase_seen = now, ph

    # ------------------------------------------------------------------ summary
    def summary(self) -> dict:
        lat = [c["latency_s"] for c in self.calls if c["error"] is None]
        wall = self.wall() - self.t0_wall if self.t0_wall is not None else None
        st = self.ledger.stats()
        cr = [v for v in st["commit_ratio"].values() if v is not None]
        hb_lat = [a["latency_s"] for a in self.astra_log if "latency_s" in a]
        T = max(self.t_last, 1e-9)
        return {"sim_time_s": round(self.t_last, 3), "policy_wall_s": round(wall, 2) if wall else None,
                "calls_sent": self.n_calls, "calls_delivered": len(self.calls),
                "call_errors": sum(1 for c in self.calls if c["error"]),
                "decisions_per_sim_s": round(len(self.calls) / T, 3),
                "decisions_per_wall_s": round(len(self.calls) / wall, 3) if wall else None,
                "latency_s": {"p50": _pct(lat, 50), "p95": _pct(lat, 95), "max": max(lat) if lat else None,
                              "n": len(lat)},
                "commit_ratio_mean": round(float(np.mean(cr)), 4) if cr else None, "m4": st,
                "blocked_s": round(self.q.blocked_s, 3), "astra_calls": len(self.astra_log),
                "astra_decisions": {d: sum(1 for a in self.astra_log if a.get("decision") == d)
                                    for d in ("ack", "patch", "replace", "invalid")},
                "astra_latency_s": {"p50": _pct(hb_lat, 50), "max": max(hb_lat) if hb_lat else None},
                "final_phase": self.skill.phase, "final_stage": self.skill.stage,
                "grasp_retries": self.skill.retries, "chunk": dict(self.chunk_stats)}
