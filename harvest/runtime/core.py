"""OursRuntime: the harness-neutral closed-loop policy core (canon §42 OursPolicy, §45, §58; D23 §2).

act(obs) is non-blocking (except the clock's simlat/sync rules): it returns the current executor output for one
100 Hz tick. Background work runs in a thread pool: (a) decision calls every T_c (staggered, up to N_max in flight,
M4 §4.3; the C2 baseline has no cap, canon §74), (b) the Astra heartbeat (§45). Delivery follows the injected clock
(sync / simlat / wall, clock.py).
Per tick, in this order: M1 observation -> schedule calls -> deliver answers (votes -> M4 ledger, prefix commit) ->
decision-step boundary ((b) check of the finished step, M4 signals, decisions of the new step) -> (C2 only: the
newest valid answer replaces the running step's decisions, canon §74) -> executor.
Back-ends (models.py): modular = decisions -> skill S (+ residual-R hook) -> IK; fused = decisions + action chunk,
the chunk is played only while its own decisions agree with the committed ones (else hold).

obs (dict, built by a harness adapter):
  sim_time, joint_pos (8), images {name: new frame} (only on new frames), m1 {"raw", "present"} (M1 observation,
  table frame; here the sim oracle = E0 oracle condition), kin (tcp_pose() -> (p, q) world; ik(p, q, max_dq) -> 7
  joints; optional fk_pos(q7) -> TCP position, read by the coupling's chunk-level adherence), table_z, low / high
  (action bounds), cams (optional, the coupling overlay's camera models).
"""
from __future__ import annotations

import math
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field

import numpy as np

from ..config import CFG
from ..predicates import PredicateState
from ..sim.planner import PHASE_TIMEOUT_S
from ..sim.snapshot import obs_from_json, pred_changes, text_state
from .astra_hb import EFFORT, HB_PROMPT_ID, MAX_OUT, HeartbeatScheduler, heartbeat_input, parse_decision_ex, prompt_for
from .clock import DeliveryQueue
from .confidence import conf_from_answers
from .m4 import CommitLedger, M4Params, Vote
from .measure import Critic, HardChannel, ProprioRules, VerifyCal, expected_check, measure, values
from .models import build_live_request, decision_questions, fused_state_text, jpeg_bytes
from .reqhash import json_blob, request_body, request_hash
from .skills import PickPlaceSkill, apply_residual, residual_hook_zero

FRAME_SAMPLE_S = 5.0  # sampled frames kept for inspection (plus one per phase change)
_PHASE_TARGET = {"approach": "o3", "descend": "o3", "close": "o3", "lift": "o3"}  # later phases: o5


def near_contact(raw: dict, phase: str) -> bool:
    """Canon §7 near/contact zone: the skill phase's target (o3 until lift, then o5) within CFG.near_in_m (5 cm) of
    the gripper finger midpoint, or a contact predicate with the target true (gripper-target, or the held o3 on o5).
    Used for the M4 ordinal tau 0 near contact (E §4.12 C5 setting, canon §73), read from the M1 observation at the
    current tick (the untrained residual-R gate in _execute keeps its distance-only test)."""
    tgt = _PHASE_TARGET.get(phase, "o5")
    if tgt not in raw["objs"]:
        return False
    g = np.asarray(raw["grip"]["pos"], float)
    if float(np.linalg.norm(np.asarray(raw["objs"][tgt]["pos"]) - g)) <= CFG.near_in_m:
        return True
    pairs = {frozenset(c) for c in raw.get("contacts", [])}
    return frozenset({"gripper", tgt}) in pairs or (tgt != "o3" and frozenset({"o3", tgt}) in pairs)


def stage_distance_m1(raw: dict, phase: str):
    """E-SR1c stage distance (sr1c_authority.stage_distance semantics) from the M1 observation: pick phases = gripper
    finger midpoint -> o3 (contact flag False); later phases = gripper -> o5 (the place), contact = o3 on o5 contact.
    (None, False) when the object is missing (Hysteresis -> a = 0)."""
    from ..train.sr1c_authority import PICK_PHASES
    tgt = "o3" if phase in PICK_PHASES else "o5"
    if tgt not in raw["objs"]:
        return None, False
    d = float(np.linalg.norm(np.asarray(raw["objs"][tgt]["pos"], float) - np.asarray(raw["grip"]["pos"], float)))
    pairs = {frozenset(c) for c in raw.get("contacts", [])}
    return d, tgt == "o5" and frozenset({"o3", "o5"}) in pairs


@dataclass
class RuntimeConfig:
    """Logged as EvalSpec.policy_config (canon §42 logging). The first three fields are inspect_robots
    PolicyConfig's (DefaultController(replan_interval=1): one action per act())."""
    action_horizon: int = 1
    replan_interval: int = 1
    temperature: float | None = None
    backend: str = "modular"  # modular (Jev-L -> M4 -> S + R) | fused (two calls per step: decide -> chunk, canon §67)
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
    hb_mode: str = "K2"  # E-M8c cadence (astra_hb.CADENCES): K0 events / K1 +T_sub / K2 +heartbeat N / K3 Gemini / K4
    hb_budget: int | None = None  # K4: matched call budget per episode (None = unlimited)
    k3_period_s: float = 1.0
    ik_max_dq: float = 0.02  # rad per 10 ms tick
    chunk_lead_s: float = 0.15  # fused: request the chunk of step k+1 this long before it starts (> chunk latency)
    residual_hook: str = "zero (R not trained)"
    # R6: M4 comparison condition (conditions.py; the m4 dict carries its overrides), C0 stop-while-waiting, and the
    # E1 calibration file (calibration.py) with the J5 gate at alpha j5_alpha (None = gate off, canon §6 before E1)
    condition: str = "C5"
    # M4 §4.2 :232 (b) -> decision-model input: the (b) category of the last finished step ends the next DecCall
    # state (`last_step: ...`, canon §77) when the condition has (b) (m4 feedback_b: C4 / C5 / C6); False = C5'
    # (:342 "(b) 범주를 Jev 입력에서 뺌": the line shows "none"; epoch / reopen / hold unchanged)
    b_to_model: bool = True
    stop_wait: bool = False
    calibration: str = ""
    j5_alpha: float | None = None
    j5_escalate_after: int = 2  # T_j5 repeat = 2 in a row (canon §31 bracket assumption)
    model_fingerprint: str | None = None
    # F19 (prompt_health.md, canon §59/§77): the checkpoint's current prompt_config sha (eval.common.
    # prompt_config_eval); None -> OursRuntime derives it from model_path (eval.common.training_prompt_config +
    # default_layout) when possible, else the check is skipped (no model_path: mock / zero-shot, as with fingerprint)
    prompt_config_sha: str | None = None
    # canon §61/§64 measure() source table (runtime/measure.py): verification-head calibration file (verify-cal-v1:
    # per-predicate temperature, conformal q-hat, critic threshold); "" = uncalibrated default (flagged in the logs)
    verify_cal: str = ""
    measure_source: str = ("canon §64: robot T1 (gripper_open, holding, lifted_holding) = proprio code rules (hard); "
                           "world + contact_stall = verification head V1h (conformal, empty/both = unknown, soft); "
                           "M7 critic alarm = V1h only")
    t2_check_max_age_s: float = 2.0  # a step's world-side check waits at most this long for a head output
    # canon §42 / §28 (R7 cycle-1 D2): the day's canary result id of the decision model (harvest.eval.canary, the
    # latest canary_<date>_<fingerprint>.json; "none" = no canary for this model) and of Astra ("none": the Astra
    # canary needs paid API calls and is not run; Astra is mock / scripted in these runs). Logged on every call row.
    canary_id: str = "none"
    astra_canary_id: str = "none"
    # spec 2026-09-26 Astra–VLA coupling: "off" = no stream (E-M8c heartbeat cadences as before); "serial" = one
    # general-control Astra request in flight (canon §84 supp 2), two-layer M4, smooth offset; the heartbeat is off
    # and the event calls mark the next stream request (plan ruling 9)
    couple: str = "off"
    couple_params: dict = field(default_factory=dict)  # CoupleParams overrides (logged in summary couple.params)
    couple_budget_krw: float = 0.0  # the experiment cap from its pre-registration (spec §15)
    couple_ledger: str = ""  # JSONL cost ledger under /data, shared by the workers of one experiment
    couple_prices: str = ""  # the run day's price table (required with the paid API)
    couple_run_id: str = ""
    motion_bins: dict | None = None  # checkpoint prompt_config["motion"] (canon §83); None = unknown line
    motion_window_s: float = 0.1  # 1 / the checkpoint data rate
    # plan 2026-09-26 Task 25 (E-VLA-solo Q3 deadlock, docs/stage3/results/vla_alone_diag.md / vla_solo.md):
    # T1 gripper_open hysteresis: once open (>= 80.5 mm) it stays open down to this width (None = the registered
    # E-M4b-meas rule); the stuck approach chunks sat at 77.1-80.2 mm, a held mug keeps the pads at ~64 mm
    grip_open_leave_m: float | None = 0.075
    # an M4 hold that has lasted this long is escaped: the next step runs its (fresh) decisions once, logged as a
    # hold_escape event (None = no escape). [가정] value (fix F25 M4): the committed records give no distribution of
    # self-resolved C5 hold lengths (dr dev1 resolved once and re-held 1.3 s later); 3.0 s > the planner's whole
    # approach (median 1.33 s, p90 1.67 s) and far below the permanent holds (36.6-56.4 s); pod Task 25 C measures it
    hold_timeout_s: float | None = 3.0
    hold_play_chunk: bool = True  # fused: while held (and in an escape step), play the step's chunk, not drop it
    # Task 25 fix F25 I2: this many escapes in a row (no non-hold step between) -> hold_stuck T_fail stand-in
    hold_escape_cap: int | None = 3
    # fused: per-tick arm joint rate limit from the last command at chunk transitions (rad / 10 ms tick; the user's
    # no-jump rule 0.04) + the gripper by the Task 17 catch rate; None = off (no gripper limit either)
    blend_max_dq: float | None = 0.04


def _pct(xs, q):
    return float(np.percentile(xs, q)) if xs else None


class OursRuntime:
    def __init__(self, cfg: RuntimeConfig, model, astra=None, wall=time.monotonic, residual_hook=residual_hook_zero,
                 instruction: str = "Put the red mug on the blue tray.", workers: int = 6):
        self.cfg, self.model, self.astra, self.wall = cfg, model, astra, wall
        self.residual_hook, self.instruction = residual_hook, instruction
        self.pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="ours")
        self.dt = 1.0 / cfg.control_hz
        self.cal = None
        if cfg.calibration:
            from .calibration import Calibration
            pcs = cfg.prompt_config_sha
            if pcs is None and cfg.model_path:  # F19: derive the checkpoint's current sha (eval/calib.py's writer)
                from ..eval.common import default_layout, prompt_config_eval, training_prompt_config
                # F20 fix (item 2): the served layout wins when the caller set one (cfg.layout, threaded by
                # eval/closed.py from its own --layout/auto resolution, canon §59) -- it is what calib.py's writer
                # actually hashed when given an explicit --layout, not necessarily the checkpoint's own default.
                layout = cfg.layout or default_layout(training_prompt_config(cfg.model_path))
                pcs = prompt_config_eval(layout)["sha"]
            self.cal = Calibration.load(cfg.calibration, fingerprint=cfg.model_fingerprint,
                                        question_ids=cfg.question_ids or None, prompt_config_sha=pcs)
        self.vcal = VerifyCal.load(cfg.verify_cal) if cfg.verify_cal else VerifyCal.default()
        self.rules = ProprioRules(th_w_leave=cfg.grip_open_leave_m)
        if cfg.couple not in ("off", "serial"):
            raise ValueError(f"couple {cfg.couple!r}: off | serial (spec 2026-09-26 §16)")
        self.couple_ledger, self.driver, self.episode = None, None, 0
        if cfg.couple == "serial":
            from ..couple.cost import CostLedger, PriceTable
            if cfg.hb_mode == "K3":
                raise ValueError("couple serial with hb_mode K3: the K3 stage gate waits for an Astra heartbeat, which "
                                 "is off in couple mode, so S1 -> S2 would never pass (use K0-K2 or K4)")
            # paid = the paid API, or any client that is not a known mock / local one (review T10 M6)
            model = str(getattr(astra, "model", "") or "")
            paid = cfg.astra_mode == "api" or (astra is not None and not model.startswith(("mock:", "local:")))
            if paid and not (cfg.couple_prices and cfg.couple_budget_krw > 0 and cfg.couple_ledger):
                raise ValueError("couple serial on the paid API needs couple_prices (the run day's price table), "
                                 "couple_budget_krw > 0 and couple_ledger (canon §82 supplement, spec §15); "
                                 f"client model {model!r} is not a mock: / local: client")
            prices = PriceTable.load(cfg.couple_prices) if cfg.couple_prices else PriceTable.free()
            self.couple_ledger = CostLedger(cfg.couple_ledger or None, cfg.couple_budget_krw, prices,
                                            run_id=cfg.couple_run_id)
        from ..couple.recovery_cache import RecoveryCache
        self.recovery = RecoveryCache()
        self.recovery_apply = lambda lesson: "m9_not_built"  # M9 recovery not built (canon §67 SCOPED)

    # ------------------------------------------------------------------ lifecycle
    def reset(self) -> None:
        p = M4Params(**self.cfg.m4)
        # canon §87: the fused backend also commits the gripper intent (close / open / keep); modular: 5 questions
        self.questions = decision_questions(self.cfg.backend)
        self.ledger = CommitLedger(p, self.questions)
        from ..serialize import SEGMENT_UNKNOWN
        from .motion import MotionTracker
        self.motion = MotionTracker(self.cfg.motion_bins, self.cfg.motion_window_s)  # canon §83
        # canon §90 segment-intent line: Astra's agreed segment plan (set by the coupling at each delivery, _deliver,
        # plan Task 18); unknown
        # until set -- never the skill's own phase (that would be a privileged input the VLA must not rely on)
        self.segment_intent = SEGMENT_UNKNOWN
        self.q = DeliveryQueue(self.cfg.clock, wall=self.wall)
        self.skill = PickPlaceSkill(dt=self.dt)
        self.skill.lost_w = self.rules.th_lo  # fix F25 I3: 'pads closed past the object' = the T1 holding band edge
        self.hb = HeartbeatScheduler(self.cfg.hb_N_s, self.cfg.hb_timeout_s, budget=self.cfg.hb_budget,
                                     mode=self.cfg.hb_mode, k3_period_s=self.cfg.k3_period_s)
        self.skill.stage_gate = "astra" if self.cfg.hb_mode == "K3" else "self"  # K3: Astra says when a step ends
        self._stage_seen, self._pred_exec_last = None, {}
        self.ps = PredicateState()
        self.prev_pred, self.stream = {}, []
        self.frames, self.frame_t = {}, {}
        self.cur_k, self.next_call, self.early, self.hold_step = None, 0.0, False, False
        self.near_now = False
        self.n_calls, self.n_hb, self.dropped_hb = 0, 0, set()
        self.calls, self.slots_log, self.astra_log, self.events, self.sampled = [], [], [], [], []
        self.chunks, self.chunk_req, self.chunk_log = {}, set(), []
        self.chunk_stats = {"played": 0, "held": 0, "requested": 0, "delivered": 0, "stale_dec": 0,
                            "hold_played": 0, "escape_played": 0, "blend_arm": 0, "blend_grip": 0}
        self._hold_since, self._grip_blend = None, None  # Task 25: start of the running M4 hold; gripper blend rate
        self.hold_stats = {"escapes": 0, "max_s": 0.0, "total_s": 0.0, "stuck": 0}
        self._escape_step, self._esc_streak, self._t_bprev = False, 0, None  # F25: escape step / streak / held time
        self.last_a, self.prev_cmd, self.t0_wall, self.t_last, self.q_meas = None, None, None, 0.0, None
        self._last_sample, self._phase_seen = -1e9, None
        self.j5_streak, self.j5_stats = {}, {"held": 0, "escalated": 0, "passed": 0}
        self.n_stop_ticks = 0
        self.inflight_at_send = []  # decision calls in flight right after each send (incl. that call)
        # canon §61/§64 measurement state
        self.critic, self.hard = Critic(self.vcal), HardChannel()
        self.v1h_last, self.meas_last, self.pending_t2, self.step_phase = None, None, [], {}
        self.b_last = None  # {"ds", "outcome"} of the last finished step ((b), canon §77)
        # E §1.6 / canon §28 A6 raw requests / responses and Astra images: {sha256: (ext, bytes)}, written by the
        # harness adapter as content-addressed files next to the sidecar (ir_policy.write_blobs, canon §77)
        self.blobs = {}
        self.measure_log = []
        self.measure_stats = {"t1_contradict": 0, "t2_deviate": 0, "t2_checked": 0, "t2_expired": 0,
                              "critic_alarms": 0, "hard_events": 0, "verify_outputs": 0}
        self._jp_prev, self._t_prev, self._jp_last, self._t_jp = None, None, None, None
        self._trace = deque(maxlen=40)
        if self.driver is not None:
            self.driver.close()  # the last episode's request in flight: charged as unanswered, never applied
        self.driver, self.couple_out, self._off_hist = None, None, []
        self._bias_q, self._chunk_played = np.zeros(7), False
        self._grip_lim = None  # B1: per-tick gripper limit while catching up from a gate-held value (None = off)
        # canon §84 supplement 8 authority a: newest aux-head output {"t_state", "reg", "cls"} and the hysteresis
        from ..train.sr1c_authority import Hysteresis
        self._aux_last, self._auth_h, self._auth_t = None, Hysteresis(dt=self.dt), None
        # chunk play clock (review T10 I1): lag accrues only while slowed; stays exactly 0.0 when the scale is 1
        self._play_lag, self._play_prev_t, self._played_t_state, self._chunk_vec_err = 0.0, None, None, False
        self.episode += 1
        if self.cfg.couple == "serial":
            from ..couple.driver import CoupleDriver
            from ..couple.params import CoupleParams
            if self.astra is None:
                raise ValueError("couple serial needs an Astra client (api, mock or local)")
            self.driver = CoupleDriver(CoupleParams(**self.cfg.couple_params), self.astra, self.couple_ledger,
                                       self._submit_couple, self.instruction, episode=self.episode,
                                       backend=self.cfg.backend)  # Task 18 fix I1: fused -> no arrow w/o a chunk
            self.hb = HeartbeatScheduler(self.cfg.hb_N_s, self.cfg.hb_timeout_s, mode="K0")
            self.skill.irrev_gate = self._irrev_gate

    def close(self) -> None:
        if getattr(self, "driver", None) is not None:
            self.driver.close()
        self.pool.shutdown(wait=False, cancel_futures=True)
        if hasattr(self.model, "close"):
            self.model.close()

    # ------------------------------------------------------------------ helpers
    def _now(self, obs) -> float:
        if self.cfg.clock == "wall":
            return self.wall() - self.t0_wall
        return float(obs["sim_time"])

    def _t1(self) -> dict:
        return values(self.meas_last) if self.meas_last is not None else {}

    def _submit_couple(self, now, fn, fixed_latency, meta):
        self.q.submit(now, self.pool.submit(fn), fixed_latency=fixed_latency, meta=meta)

    def _irrev_gate(self, kind: str, t: float) -> bool:
        return self.driver.irrev_allowed(kind, t, self._t1(), self.near_now)

    def _event(self, now: float, name: str) -> None:
        """An event call (canon §45): pulls the heartbeat forward (off in couple mode) and marks the next coupling
        request (spec §16: the request in flight is not cancelled)."""
        self.hb.advance(now)
        if self.driver is not None:
            self.driver.flag(name, now)

    def _fail_event(self, now: float, mode: str, evidence: str) -> None:
        """T_fail stand-in (M9 not built): falsify first (canon §84 + supplement 1) before the Astra call."""
        from ..couple.recovery_cache import FailSig
        sig = FailSig(stage=self.skill.stage, target=_PHASE_TARGET.get(self.skill.phase, "o5"), mode=mode,
                      evidence=evidence)
        dec, lesson, why = self.recovery.decide(self.episode, sig, self._t1(), now)
        self.events.append({"t": round(now, 4), "event": "fail_path", "sig": sig.to_json(), "decision": dec,
                            "why": why})
        if dec == "reuse":
            self.events.append({"t": round(now, 4), "event": "recovery_reuse", "recovery": lesson.recovery,
                                "source": lesson.source, "applied": self.recovery_apply(lesson)})
            return
        self._event(now, mode)

    def _chunk_vec(self, k, dec):
        """Chunk-level adherence input (canon §84 supplements 4-5, controller ruling C3): the executed motion of step
        k's expert chunk = TCP(last joint target) - TCP(first joint target), arm joints only, the raw chunk values
        (no coupling bias). None on the modular backend (skills execute the decision itself), when step k has no
        chunk that will be played (missing, or conditioned on other decisions -> held), when the kinematics service
        has no fk_pos (FK of an arbitrary joint vector), or when the displacement is below 0.1 mm."""
        if self.cfg.backend != "fused":
            return None
        c, kin = self.chunks.get(k), getattr(self, "_kin_last", None)
        fk = getattr(kin, "fk_pos", None)
        if c is None or not dec or c["dec"] != dec or fk is None:
            return None
        ch = np.asarray(c["chunk"], float)
        try:  # never stops a run (review T10 M3): an FK failure -> None (decision vector), logged once
            d = np.asarray(fk(ch[-1, :7]), float) - np.asarray(fk(ch[0, :7]), float)
        except Exception as e:  # noqa: BLE001
            if not self._chunk_vec_err:
                self._chunk_vec_err = True
                self.events.append({"t": round(self.t_last, 4), "event": "couple_chunk_vec_error", "error": repr(e)})
            return None
        return d if float(np.linalg.norm(d)) >= 1e-4 else None

    def _advance_play_clock(self, now: float) -> None:
        """Chunk play clock (review T10 I1): over each tick interval the chunk advances speed_scale x dt, i.e. the lag
        grows by (1 - scale) x dt. A chunk plays at now - (lag now - lag at its observation), so a scale switch (also
        across a chunk switch) never jumps; with scale 1 the lag is never touched (off path: t_play == now)."""
        scale = self.couple_out.speed_scale if self.couple_out is not None else 1.0
        if self._play_prev_t is not None and scale != 1.0:
            self._play_lag += (1.0 - scale) * (now - self._play_prev_t)
        self._play_prev_t = now

    def _authority(self, now: float, raw: dict, phase: str):
        """E-SR1c authority a on the coupling offset (canon §84 supplement 8, ADOPT_C1): (a, source). Source "aux" =
        sr1c_authority.estimated_distance from the newest aux-head output a decision response carried (ModelResult.
        raw["aux"] = {"reg": AUX_REG / AUX_REG_SCALE, "cls": AUX_CLS logits}; used while it is at most
        t2_check_max_age_s old). No back-end returns it yet (fused_model.decide_raw returns probs / verify / meta
        only; MockFusedModel neither), so the runtime falls back to "rule" = the stage distance from the M1
        observation (stage_distance_m1, the one near_contact reads). Always through sr1c_authority.Hysteresis
        (enter 5 cm / leave 6 cm, contact phase -> 0, decreases immediate, increases +0.5 per 0.33 s), stepped with
        the elapsed tick time. The §6 decision projection is not implemented (no task in this plan)."""
        from ..train.sr1c_authority import estimated_distance
        x = self._aux_last
        if x is not None and now - x["t_state"] <= self.cfg.t2_check_max_age_s + 1e-9:
            (d, c), src = estimated_distance(x["reg"], x["cls"], phase), "aux"
        else:
            (d, c), src = stage_distance_m1(raw, phase), "rule"
        self._auth_h.dt = self.dt if self._auth_t is None else max(now - self._auth_t, 0.0)
        self._auth_t = now
        return self._auth_h.step(d, phase, bool(c)), src

    def _couple_fused(self, a, now, kin, tcp_p):
        """Fused path: the offset moved since the current chunk's observation is added as a joint bias (IK difference
        at the measured tip; the chunk already contains earlier shifts, plan ruling 5). A held action (no chunk played
        this tick = last_a) already carries last tick's bias, so that bias is taken out first (no double count). A
        gripper transition in the chunk is held unless the two layers agree (spec §5); after the release the gripper
        target is rate-limited from the held value (_grip_catch_rate, dry-run B1)."""
        from ..couple.geom import quat_from_rotvec, quat_mul
        a = np.asarray(a, float).copy()
        if not self._chunk_played:
            a[:7] = a[:7] - self._bias_q
        st = self.couple_out.step6 if self.couple_out is not None else None
        if st is not None and np.any(st):
            self._off_hist.append((now, st.copy()))
        # prune by the observation time of the chunk actually PLAYED (a held action comes from it, not from the current
        # step's stale chunk; review T10 I2); the step applied at that very tick is not in its observation (>=)
        t0 = self._played_t_state if self._played_t_state is not None else -math.inf
        self._off_hist = [(t, s) for t, s in self._off_hist if t >= t0]
        self._bias_q = np.zeros(7)
        if self._off_hist:
            b = np.sum([s for _, s in self._off_hist], axis=0)
            p0, q0 = kin.tcp_pose()
            q_to = kin.ik(np.asarray(p0, float) + b[:3], quat_mul(quat_from_rotvec(b[3:]), q0), 0.2)
            q_at = kin.ik(np.asarray(p0, float), q0, 0.2)
            self._bias_q = (np.asarray(q_to, float) - np.asarray(q_at, float))[:7]
            a[:7] = a[:7] + self._bias_q
        w_prev = float(self.last_a[7]) if self.last_a is not None else float(a[7])
        t1 = self._t1()
        kind = ("close" if a[7] < w_prev - 0.005 and t1.get("gripper_open") else
                "release" if a[7] > w_prev + 0.005 and t1.get("holding_t") else None)
        if kind is not None and not self.driver.irrev_allowed(kind, now, t1, self.near_now):
            a[7] = w_prev
            self._grip_lim = -1.0  # held: catch up after the release
        elif self._grip_lim is not None and self._chunk_played:  # a held tick (a = last_a) keeps the limit pending
            gap = float(a[7] - w_prev)
            if self._grip_lim < 0:
                self._grip_lim = self._grip_catch_rate(abs(gap))
            if abs(gap) <= self._grip_lim:
                self._grip_lim = None
            else:
                a[7] = w_prev + math.copysign(self._grip_lim, gap)
        return a

    def _grip_catch_rate(self, gap: float) -> float:
        """Dry-run B1 (E-Couple, 0.10475 -> 0.0908 in one tick): after the gate releases a held gripper transition,
        the target moves from the held value at most (the played chunk's own max per-tick gripper rate + the gap at
        the release spread over one chunk horizon) per tick -- it keeps up with a still-moving chunk and closes the
        gap within one chunk horizon (15 rows at 30 Hz = 0.5 s for the stage-B expert). No gripper speed constant
        exists in the code base (skills.py commands the width as a step), hence the chunk-derived rate. Called only on
        a tick that played a chunk (a held tick, a = last_a, leaves the pending / running limit untouched)."""
        c = self.chunks.get(self.cur_k)
        if c is None or len(c["chunk"]) < 2 or not c.get("dt"):
            return gap  # a one-row chunk carries no rate: nothing to derive one from
        w = np.asarray(c["chunk"], float)[:, 7]
        horizon = len(w) * float(c["dt"])
        return float(np.max(np.abs(np.diff(w)))) * self.dt / float(c["dt"]) + gap * self.dt / horizon

    def _m1(self, obs, now):
        raw, present = obs["m1"]["raw"], obs["m1"]["present"]
        objs, grip, contacts, support = obs_from_json(raw)
        pred = self.ps.update(objs, grip, contacts, support)
        self.stream += pred_changes(self.prev_pred, pred, now)
        self.stream = [c for c in self.stream if c[0] >= now - 3.0]
        self.prev_pred = pred
        return raw, present, pred, support

    def _s0(self, now, pred, present, support):
        sk = self.skill
        moving = self.prev_cmd is not None and float(np.linalg.norm(sk.cmd_pos - self.prev_cmd)) > 1e-5
        return text_state(now, sk.phase, now - sk.t_phase0, PHASE_TIMEOUT_S.get(sk.phase, 60.0), pred, present,
                          support, bool(pred.get("gripper_open")), bool(pred.get("holding(o3)")), moving,
                          list(self.stream))

    def b_line(self) -> str:
        """The `last_step:` value of the next DecCall (M4 §4.2 :232, canon §77): the (b) category of the last
        finished step when the condition feeds (b) to the decision model (feedback_b and b_to_model: C4 / C5 / C6),
        else "none" (C5', C0-C3; also before the first step has finished)."""
        if not (self.cfg.b_to_model and self.ledger.p.feedback_b) or self.b_last is None:
            return "none"
        return self.b_last["outcome"]

    def _decision_ctx(self, now, raw, present, pred, support, obs, slots=None):
        slots = self.ledger.target_slots(now) if slots is None else slots
        sk = self.skill
        s0 = self._s0(now, pred, present, support)
        ls = self.b_line()
        mline, seg = self.motion.line(), self.segment_intent  # canon §83 / §90 (ser-A-min-3)
        req, shown = build_live_request(slots[0], sk.phase, s0, present, raw, last_step=ls, motion=mline,
                                        segment=seg, questions=self.questions)
        ctx = {"t_state": now, "ds": slots[0], "slots": slots, "epoch": self.ledger.epoch, "phase": sk.phase,
               "req": req, "shown": shown, "images": {k: v.copy() for k, v in self.frames.items()},
               "joint_pos": np.asarray(obs["joint_pos"], float).copy(), "last_step": ls, "motion": mline,
               "segment": seg}
        if self.cfg.backend == "fused":  # canon §58: no S1 coordinates in the fused model's input
            from ..serialize import canonicalize
            from ..train.stageb_data import image_only_state
            ctx["privileged_s1"] = req["state"]  # used by the MOCK fused model only (flagged in its meta)
            # the stage-B prompt_config state IMG: the DecCall items and the context prompt carry the same text
            ctx["req"], _ = build_live_request(slots[0], sk.phase, s0, present, raw, state="IMG", last_step=ls,
                                               motion=mline, segment=seg, questions=self.questions)
            ctx["ctx_text"] = canonicalize(image_only_state(s0) + "\n" + seg + "\n" + mline)
            ctx["proprio_text"] = fused_state_text(self.instruction, sk.stage, sk.phase, obs["joint_pos"])  # log only
        return ctx

    def _submit_decision(self, now, raw, present, pred, support, obs, slots=None):
        ctx = self._decision_ctx(now, raw, present, pred, support, obs, slots)
        self.n_calls += 1
        model, cfg = self.model, self.cfg

        def run():  # the request hash is computed in the worker thread (frame digests stay off the rollout thread)
            h, ims, body = request_body({"api": "decide", "model_id": cfg.model_id, "layout": cfg.layout,
                                         "call_mode": cfg.call_mode, "req": ctx["req"],
                                         "ctx_text": ctx.get("ctx_text")}, ctx["images"])
            r = model.decide(ctx)
            return {"latency_s": r.latency_s, "res": r, "req_hash": (h, ims), "req_body": body}
        meta = {"kind": "dec", "call_no": self.n_calls, "slots": ctx["slots"], "epoch": ctx["epoch"],
                "t_state": now, "phase": ctx["phase"], "anchor_g": list(raw["grip"]["pos"]),
                "last_step": ctx["last_step"]}
        self.q.submit(now, self.pool.submit(run), fixed_latency=getattr(model, "synthetic_latency", None), meta=meta)

    def _submit_hb(self, now, pred, kind: str = "hb"):
        if self.astra is None:
            return
        self.n_hb += 1
        template, allowed, pid = prompt_for(self.cfg.hb_mode, kind)
        sk, L = self.skill, self.ledger
        dec = {k: L.decision(k, self.cur_k, now)[0] for k in self.questions} if self.cur_k is not None else {}
        outs = [s.get("outcome") for s in self.slots_log[-6:-1]]
        mv = values(self.meas_last) if self.meas_last is not None else {}  # measured facts (canon §64), not oracle
        facts = {"holding(o3)": mv.get("holding_t"), "lifted_holding(o3)": mv.get("lifted_holding"),
                 "on(o3,o5)": mv.get("on_tp"), "lifted(o3)": mv.get("lifted_t")}
        summary = (f"t={now:.1f}s stage={sk.stage} phase={sk.phase} gripper_open={pred.get('gripper_open')}\n"
                   f"facts={facts}\ncurrent step decisions={dec}\nlast step checks={outs}\n"
                   f"premise_epoch={L.epoch} grasp_retries={sk.retries}")
        head = self.frames.get("cam_head")
        head = None if head is None else head.copy()
        astra, n = self.astra, self.n_hb

        def run():
            jpg = jpeg_bytes(head) if head is not None else None
            inp = heartbeat_input(summary, jpg, template=template)
            # the request without the base64 image (its sha256 goes in the image digests instead, canon §28 A6)
            text_only = [{**m, "content": [c for c in m["content"] if c.get("type") != "input_image"]} for m in inp]
            h, ims, body = request_body({"api": "astra", "model": self.cfg.astra_model, "effort": EFFORT,
                                         "max_out": MAX_OUT, "prompt_id": pid, "input": text_only},
                                        {"cam_head": jpg} if jpg is not None else {})
            rec = astra.call(inp, EFFORT, MAX_OUT, {"hb_no": n, "prompt_id": pid, "kind": kind,
                                                    "cadence": self.cfg.hb_mode})
            lat = getattr(astra, "synthetic_latency", None)
            return {"latency_s": lat if lat is not None else rec.t_done - rec.t_send, "rec": rec,
                    "summary": summary, "req_hash": (h, ims), "req_body": body,
                    "images_raw": {"cam_head": jpg} if jpg is not None else {}}
        self.hb.sent(now, kind)
        self.q.submit(now, self.pool.submit(run), fixed_latency=getattr(astra, "synthetic_latency", None),
                      meta={"kind": "astra", "hb_no": n, "call_kind": kind, "allowed": allowed, "prompt_id": pid})

    # ------------------------------------------------------------------ deliveries
    def _deliver(self, r, now):
        m = r["meta"]
        if m["kind"] == "couple":
            self.driver.on_delivery(r, now, self._t1())
            # canon §90 (plan Task 18): the VLA segment line follows Astra's AGREED plan, mapped to the line
            # vocabulary (driver.segment_intent: PLAN_TO_LINE + SEGMENT_PLAN); unknown until the first agreed plan
            self.segment_intent = self.driver.segment_intent()
            self.blobs.update(self.driver.blobs)
            self.driver.blobs.clear()
            return
        if m["kind"] == "astra":
            return self._deliver_hb(r, now)
        if m["kind"] == "chunk":
            return self._deliver_chunk(r, now)
        res = r["res"]
        rec = {"call_no": m["call_no"], "t_state": round(m["t_state"], 4), "t_deliver": round(r["t_deliver"], 4),
               "latency_s": round(res.latency_s, 4), "slots": m["slots"], "epoch_sent": m["epoch"],
               "phase": m["phase"], "error": res.error, "call_id": res.call_id, "meta": res.meta,
               "answers": {q: [a["choice"], round(a["p_chosen"], 4) if a.get("p_chosen") is not None else None]
                           for q, a in res.answers.items()}, "votes": {}, "canary_id": self.cfg.canary_id}
        rec["request_sha256"], rec["image_sha256"] = r.get("req_hash") or (None, {})
        rec["last_step"] = m.get("last_step")
        if r.get("req_body") is not None:  # E §1.6 "요청 원문": the exact body request_sha256 hashes (canon §77)
            self.blobs[rec["request_sha256"]] = ("json", r["req_body"])
            rec["request_blob"] = rec["request_sha256"]
        hb, bb = json_blob(res.raw if res.raw is not None else {"answers": res.answers, "error": res.error})
        self.blobs[hb] = ("json", bb)
        rec["response_blob"] = hb
        if res.error is None:
            self.ledger.record_latency(res.latency_s)
            aux = (res.raw or {}).get("aux") if isinstance(res.raw, dict) else None
            if aux and aux.get("reg") is not None and aux.get("cls") is not None and (
                    self._aux_last is None or m["t_state"] >= self._aux_last["t_state"]):
                self._aux_last = {"t_state": m["t_state"], "reg": aux["reg"], "cls": aux["cls"]}
            gate = self._j5(res, now) if self.cal is not None else {}
            irr = self.skill.irreversible
            for q, a in res.answers.items():
                rec["votes"][q] = []
                if q in gate:  # J5 set size != 1 (or NONE_ESCALATE in it): no vote, the slot keeps what it has
                    rec["votes"][q].append(f"j5_{gate[q]}")
                    continue
                for ds in m["slots"]:
                    v = Vote(ds=ds, question=q, choice=a["choice"], p_chosen=a.get("p_chosen"),
                             call_id=res.call_id, t_send=m["t_state"], t_recv=r["t_deliver"], t_state=m["t_state"],
                             premise_epoch=m["epoch"], qid=a.get("qid", ""))
                    rec["votes"][q].append(self.ledger.on_vote(v, now, irreversible=irr, near=self.near_now))
            if res.verify:
                rec["verify"] = {p: round(x, 3) for p, x in res.verify.items()}
                self._on_verify(res.verify, m["t_state"], m["phase"], now, rec)
        # E §1.6 "질문별 {choice, probabilities, ...}": the option distribution by option_key (+ calibrated, J5)
        rec["probs"] = {q: {k: round(float(p), 6) for k, p in (a.get("probs") or {}).items()}
                        for q, a in res.answers.items()}
        cal = {q: a["probs_cal"] for q, a in res.answers.items() if a.get("probs_cal")}
        if cal:
            rec["probs_cal"] = {q: {k: round(float(p), 6) for k, p in pc.items()} for q, pc in cal.items()}
        # E-CONF logging hook (conf-base@v1, canon §95, plan Task 22): "why this choice" record only, no gate --
        # never read back into any control path (§95 (a) stream-priority / (b) conservative-mode stay OFF).
        conf = conf_from_answers(res.answers) if res.error is None else None
        if conf is not None:
            rec["conf"] = conf
        self.calls.append(rec)

    def _on_verify(self, logits: dict, t_state: float, phase: str, now: float, rec: dict) -> None:
        """A verification-head output (observation at t_state): M7 critic (V1h only, canon §64) and the world-side
        (b)(2) check of every finished step whose end is <= t_state (D28 §3.1: the first head output after the step
        end judges it); T2 {False} -> DEVIATE for that step (soft, M7 C_m4); unknown -> no verdict."""
        self.measure_stats["verify_outputs"] += 1
        if self.v1h_last is None or t_state >= self.v1h_last["t_state"]:
            self.v1h_last = {"t_state": t_state, "logits": dict(logits)}
        cr = self.critic.update(t_state, phase, logits)
        rec["critic"] = cr
        if cr["alarm"]:  # M7 FAIL stand-in (M9 recovery not built): log + Astra heartbeat now (T_fail rule)
            self.measure_stats["critic_alarms"] += 1
            self.events.append({"t": round(now, 4), "event": "m7_critic_alarm", **cr})
            self._fail_event(now, "m7_critic_alarm", "v1h_critic")
        keep = []
        meas = measure(None, logits, self.vcal, self.rules)
        for p in self.pending_t2:
            if now - p["t_end"] > self.cfg.t2_check_max_age_s:
                self.measure_stats["t2_expired"] += 1
                continue
            if t_state + 1e-9 < p["t_end"]:
                keep.append(p)
                continue
            chk = expected_check(p["phase"], {k: v for k, v in meas.items() if v["tier"] == "T2"})
            self.measure_stats["t2_checked"] += 1
            self.measure_log.append({"ds": p["ds"], "phase": p["phase"], "t_state": round(t_state, 4),
                                     "t2_false": chk["t2_false"], "unknown": chk["unknown"]})
            if chk["outcome"] == "DEVIATE":
                self.measure_stats["t2_deviate"] += 1
                sig = self.ledger.on_step_executed(p["ds"], "DEVIATE", now)
                b = self.b_last  # the late world-side verdict of the last finished step raises its (b) line
                if b is not None and p["ds"] == b["ds"] and b["outcome"] in ("OK", "LAG"):
                    b["outcome"] = "DEVIATE"
                self.events.append({"t": round(now, 4), "event": "b2_world_deviate", "ds": p["ds"],
                                    "preds": chk["t2_false"], "epoch": sig["epoch"]})
                if sig["early_call"]:
                    self.early = True
        self.pending_t2 = keep

    def _j5(self, res, now) -> dict:
        """Calibrated probabilities (per-question temperature) and the J5 conformal gate (canon §31): a singleton
        set -> that option votes; a larger set or one holding NONE_ESCALATE -> no vote (M4 keeps the last committed
        action, never a stop), and after j5_escalate_after such answers in a row for a question the next Astra
        heartbeat is pulled forward (Trust-or-Escalate shape). Returns {question: "hold" | "escalate"}."""
        from .calibration import NE as NE_KEY
        out = {}
        for q, a in res.answers.items():
            if not a.get("probs"):
                continue
            pc = self.cal.apply(q, a["probs"])
            a["probs_cal"], a["p_chosen"] = pc, pc.get(a["choice"], a.get("p_chosen"))
            al = self.cfg.j5_alpha
            if al is None or not self.cal.j5_on(q, al):
                continue
            S = self.cal.set_for(q, pc, al)
            if len(S) == 1 and NE_KEY not in S:
                a["choice"] = next(iter(S))
                self.j5_streak[q] = 0
                self.j5_stats["passed"] += 1
                continue
            self.j5_stats["held"] += 1
            self.j5_streak[q] = self.j5_streak.get(q, 0) + 1
            if self.j5_streak[q] >= self.cfg.j5_escalate_after:
                self.j5_streak[q] = 0
                self.j5_stats["escalated"] += 1
                self._event(now, "j5_escalate")
                self.events.append({"t": round(now, 4), "event": "j5_escalate", "question": q, "set": sorted(S)})
                out[q] = "escalate"
            else:
                out[q] = "hold"
        return out

    def _deliver_hb(self, r, now):
        m = r["meta"]
        rec_ = r["rec"]
        if m["hb_no"] in self.dropped_hb:
            self.astra_log.append({"hb_no": m["hb_no"], "late_after_timeout": True, "t": round(now, 3)})
            return
        if rec_.error or rec_.incomplete:  # F20 fix (item 1): an errored/incomplete record is never parsed for a
            # decision -- regex_fallback could otherwise find an allowed word (e.g. "patch") inside truncated text
            dec, note, parse_mode = "invalid", "", "failed"
        else:
            dec, note, parse_mode = parse_decision_ex(rec_.output_text,
                                                      tuple(m.get("allowed") or ("ack", "patch", "replace")))
        self.hb.responded(now)
        entry = {"hb_no": m["hb_no"], "kind": m.get("call_kind", "hb"), "cadence": self.cfg.hb_mode,
                 "prompt_id": m.get("prompt_id"), "t_send": round(r["t_send"], 3),
                 "t_deliver": round(r["t_deliver"], 3),
                 "latency_s": round(r["latency_s"], 3), "decision": dec, "note": note, "parse_mode": parse_mode,
                 "error": rec_.error, "model": rec_.model_field, "usage": rec_.usage, "http": rec_.http_status,
                 "first_token_s": round(rec_.t_first_token - rec_.t_send, 3) if rec_.t_first_token else None,
                 "canary_id": self.cfg.astra_canary_id}
        entry["request_sha256"], entry["image_sha256"] = r.get("req_hash") or (None, {})
        # canon §28 A6: request text (blob = the body request_sha256 hashes; image original by its byte hash),
        # effort, max tokens, raw response (output_text) -- canon §77
        entry.update(effort=rec_.effort or EFFORT, max_output_tokens=MAX_OUT, output_text=rec_.output_text)
        if r.get("req_body") is not None:
            self.blobs[entry["request_sha256"]] = ("json", r["req_body"])
            entry["request_blob"] = entry["request_sha256"]
        for cam, b in (r.get("images_raw") or {}).items():
            self.blobs[entry["image_sha256"][cam]] = ("jpg", b)
        if dec in ("patch", "replace"):  # contract edit not implemented: premise epoch only (§45 합치기)
            entry["epoch"] = self.ledger.bump_epoch(f"astra_{dec}", now)
            self.early = True
        elif dec in ("run_instruction", "reset"):  # K3: Astra is the step-success detector (code safety still gates)
            res = self.skill.astra_advance(dec, now, self._pred_exec_last)
            entry["applied"] = res
            self.events.append({"t": round(now, 4), "event": "astra_gemini", "decision": dec, "result": res})
        self.astra_log.append(entry)

    # ------------------------------------------------------------------ act
    def act(self, obs) -> tuple[np.ndarray, dict]:
        if self.t0_wall is None:
            self.t0_wall = self.wall()
        now = self._now(obs)
        self.t_last = now
        raw, present, pred, support = self._m1(obs, now)
        self._raw_last = raw
        for name, img in (obs.get("images") or {}).items():
            self.frames[name], self.frame_t[name] = img, now
        kin, tz = obs["kin"], obs["table_z"]
        self._kin_last = kin  # _chunk_vec (decision-step boundary) reads its fk_pos
        tcp_p, tcp_q = kin.tcp_pose()
        self._m1_last = (raw, present, pred, support)
        if self.cur_k is None and self.skill.__dict__.get("cmd_pos") is None:
            self.skill.reset(now, tcp_p, tcp_q)
        # canon §61/§64 measure(): robot T1 from the proprio code rules every tick (pad gap, |gripper effort|, TCP
        # height from FK), world side from the newest verification-head output (none -> unknown)
        jp = np.asarray(obs["joint_pos"], float)
        if self._t_jp is not None and now > self._t_jp + 1e-12:
            self._jp_prev, self._t_prev = self._jp_last, self._t_jp
        self._jp_last, self._t_jp = jp.copy(), now
        self.motion.add(now, jp[:7], jp[7])
        proprio = {"width": float(jp[7]), "grip_effort": float(raw["grip"].get("effort", 0.0)),
                   "tcp_z": float(tcp_p[2] - tz),
                   "prev_open": bool(self.meas_last is not None and self.meas_last["gripper_open"]["value"])}
        v = self.v1h_last
        v1h = v["logits"] if v is not None and now - v["t_state"] <= self.cfg.t2_check_max_age_s else None
        self.meas_last = measure(proprio, v1h, self.vcal, self.rules)
        pred_exec = self._exec_pred(pred, self.meas_last)
        # (a) gate, target slots and early flag from the start of the tick (in-flight count, N_max and d_hat before
        # this tick's deliveries; an early call raised later in this tick goes out on the next tick -- all as before
        # canon §79); the call itself is built after the boundary check below
        infl = sum(1 for it in self.q._items if it["meta"]["kind"] == "dec")
        can_send, slots_send = infl < self.ledger.n_max(), self.ledger.target_slots(now)
        early_due, self.early = self.early, False
        # (c) Astra heartbeat
        if self.hb.timed_out(now):
            self.dropped_hb.add(self.n_hb)
            self.astra_log.append({"hb_no": self.n_hb, "timeout": True, "t": round(now, 3)})
            self.hb.drop_inflight(now)
        self._pred_exec_last = pred_exec
        st = (self.skill.stage, self.skill.phase == "done")
        old = self._stage_seen
        if old is not None and ((old[0], st[0]) == ("S1", "S2") or (st[1] and not old[1])):
            # a contract stage completed (forward only; a lost grasp going back to S1 is a T_fail event) -> T_sub
            self.hb.boundary(now)
            self.events.append({"t": round(now, 4), "event": "t_sub", "stage": self.skill.stage,
                                "done": self.skill.phase == "done"})
        self._stage_seen = st
        kind = self.hb.next_kind(now) if self.astra is not None and self.driver is None else None
        if kind is not None:
            self._submit_hb(now, pred_exec, kind)
        # deliveries (clock) -> M4 (near/contact zone now, canon §7: ordinal tau 0 near contact, E §4.12 C5)
        self.near_now = near_contact(raw, self.skill.phase)
        got = self.q.poll(now)
        for r in got:
            self._deliver(r, now)
        if got:
            for qq in self.questions:
                self.ledger.try_commit_prefix(qq, now, near=self.near_now)
        # decision-step boundary
        k = int(math.floor(now / self.cfg.T_c + 1e-9))
        if k != self.cur_k:
            self._boundary(k, now, tcp_p)
        # (a) decision calls: staggered every T_c, <= N_max in flight (C2: no cap); an early call pulls one periodic
        # slot forward. The in-flight count at each send is recorded (C2 "실측 in-flight 수 보고", M4 §5 :332).
        # Built after the boundary check (R7 cycle 13 N1, canon §79): a call of a boundary tick is the "next Jev
        # input" of the step just checked (M4 §4.2 :232) -- its last_step line, premise epoch and state are those
        # after the check, as in the training items (snapshot k carries the step that ended at k, canon §77 (iv))
        if can_send and (now >= self.next_call - 1e-9 or early_due):
            self.inflight_at_send.append(infl + 1)
            self._submit_decision(now, raw, present, pred, support, obs, slots_send)
            if early_due and now < self.next_call - 1e-9:
                self.next_call += self.cfg.T_c
            else:
                self.next_call = max(self.next_call + self.cfg.T_c, now)
            early_due = False
        self.early = self.early or early_due  # unsent early call kept; one raised in this tick waits for the next
        if self.ledger.p.agree == "stream" and not self.hold_step:
            # C2 VLM Stream (M4 §5 :332 "매 틱 … 가장 새 유효 응답 하나의 보기를 그대로 적용", canon §74): a newer
            # answer (or the 5 s timeout -> default action) changes the running step's decisions at this tick
            dec = {q: c for q in self.questions if (c := self.ledger.decision(q, self.cur_k, now)[0]) is not None}
            if dec != self.skill.dec:
                self.skill.redecide(dec)
        if self.driver is not None:
            from ..couple.driver import TickView
            auth, auth_src = self._authority(now, raw, self.skill.phase)
            self.couple_out = self.driver.tick(TickView(
                now=now, dt=self.dt, tcp_p=np.asarray(tcp_p, float), phase=self.skill.phase, stage=self.skill.stage,
                near=self.near_now, committed={q: c for q, c in self.skill.dec.items() if c is not None},
                frames=self.frames, cams=obs.get("cams"), t1=self._t1(), motion=self.motion.line(),
                authority=auth, authority_src=auth_src))
            self._advance_play_clock(now)  # before a chunk request of this tick records the lag at its observation
        if self.cfg.backend == "fused":
            self._maybe_request_chunk(now, obs)
        # executor (its expected_after checks read the measured predicates, not the privileged state)
        a = self._execute(now, obs, raw, pred_exec, tz, tcp_p)
        self._sample_frames(now)
        return a, {"ds": self.cur_k, "phase": self.skill.phase, "epoch": self.ledger.epoch}

    @staticmethod
    def _exec_pred(pred: dict, meas: dict) -> dict:
        """The executor's predicate view (replaces the privileged holds() path, canon §64): gripper / holding /
        lifted-while-holding from the T1 proprio rules; in_contact(o3,o5) and on(o3,o5) from the verification head
        (None = unknown -> the skill falls back to its geometric 'reached'). The M1 geometry keys the modular stack's
        DecCall text is built from stay the M1 observation."""
        v = values(meas)
        return {**pred, "gripper_open": v["gripper_open"], "holding(o3)": v["holding_t"],
                "lifted(o3)": v["lifted_holding"], "in_contact(o3,o5)": v["contact_tp"], "on(o3,o5)": v["on_tp"]}

    def _boundary(self, k, now, tcp_p):
        prev = self.cur_k
        entry = {"ds": k, "t": round(now, 4), "tcp": [round(float(v), 4) for v in tcp_p],
                 "cmd": [round(float(v), 4) for v in self.skill.cmd_pos]}
        raw = getattr(self, "_raw_last", None)
        if raw is not None:  # diagnostics (table frame): finger-link midpoint g and the target object centre
            entry["g_tbl"] = [round(float(v), 4) for v in raw["grip"]["pos"]]
            entry["w"] = round(float(raw["grip"]["w"]), 4)
            if "o3" in raw["objs"]:
                entry["o3_tbl"] = [round(float(v), 4) for v in raw["objs"]["o3"]["pos"]]
        if self._t_bprev is not None and self.hold_step:  # F25 I2: held time of the step that just ended
            self.hold_stats["total_s"] += now - self._t_bprev
        self._t_bprev, self._escape_step = now, False
        if prev is not None:
            if self.cfg.backend == "fused":
                out, resid = self._joint_outcome()
            else:
                out, resid = self.skill.step_outcome(tcp_p)
            # (b)(2) expected_after of the finished step, robot side T1 now (proprio); only when the step stayed in
            # one phase (a phase switch inside the step changes the expectation mid-step: transition, not a failure)
            ph0 = self.step_phase.get(prev)
            if ph0 is not None and ph0 == self.skill.phase and self.meas_last is not None:
                chk = expected_check(ph0, {p: m for p, m in self.meas_last.items() if m["tier"] == "T1"})
                entry["t1_check"] = chk["t1_false"]
                if chk["outcome"] == "CONTRADICT" and out != "CONTRADICT":
                    out = "CONTRADICT"
                    self.measure_stats["t1_contradict"] += 1
                self.pending_t2.append({"ds": prev, "phase": ph0, "t_end": now})
            hev = self.hard.update(now, self.skill.phase, self.meas_last) if self.meas_last is not None else None
            if hev is not None:  # M7 hard channel (T1 only): FAIL stand-in -> Astra now (M9 recovery not built)
                self.measure_stats["hard_events"] += 1
                self.events.append({"t": round(now, 4), "event": "m7_hard_t1", **hev})
                self._fail_event(now, "m7_hard_t1", "t1_hard")
            sig = self.ledger.on_step_executed(prev, out, now)
            self.b_last = {"ds": prev, "outcome": out}
            if out == "CONTRADICT":  # an existing event call (canon §45): pulls the next Astra call forward
                self._event(now, "b_contradict")
            elif self.driver is not None:  # plan Task 21 B6: the condition cleared -> its next flag is a new edge
                self.driver.clear("b_contradict")
            entry.update(prev_outcome=out, prev_residual_mm=round(resid * 1e3, 1), signals=sig)
            self.hold_step = sig["hold"]
            self._hold_escape(now, prev, entry)
            if out in ("DEVIATE", "CONTRADICT") and self.cfg.backend != "fused":
                self.skill.reanchor(tcp_p)
            if sig["early_call"]:
                self.early = True
            for qq in self.questions:
                self.ledger.try_commit_prefix(qq, now, near=self.near_now)
        decs = self.ledger.mark_executed(k, now)
        dec = {} if self.hold_step else {q: c for q, (c, st) in decs.items() if c is not None}
        self.skill.begin_slot(k, dec)
        if self.driver is not None:
            self.driver.on_step(dec, entry.get("prev_outcome", "OK"), now, chunk_vec=self._chunk_vec(k, dec))
        self.step_phase[k] = self.skill.phase
        entry.update(decisions={q: list(v) for q, v in decs.items()}, hold=self.hold_step,
                     phase=self.skill.phase, stage=self.skill.stage)
        self.slots_log.append(entry)
        if self.slots_log and len(self.slots_log) >= 2:
            self.slots_log[-2]["outcome"] = entry.get("prev_outcome")
        self.cur_k = k

    def _hold_escape(self, now: float, ds: int, entry: dict) -> None:
        """Hold escape (plan 2026-09-26 Task 25 item 2; canon §4: a hold is 'keep the last committed action', never a
        stop): a CONTRADICT hold that has run for hold_timeout_s since its first held step is lifted for this one step
        -- the step's decisions (the early call after each CONTRADICT re-asked them from the current observation) are
        executed as if the premise held; the skill's own code safety predicates and the coupling's two-layer gate
        still guard every irreversible event. Logged as a hold_escape event; the hold re-arms at the next CONTRADICT,
        so no hold lasts longer than hold_timeout_s + one step (E-VLA-solo: 8/12 C5 episodes never left the hold).
        Fix F25: the escape step plays its own chunk on the fused path (_play_chunk, `_escape_step`); hold_escape_cap
        escapes in a row with no non-hold step between -> a `hold_stuck` event and the T_fail stand-in
        (_fail_event mode hold_stuck, evidence m4_hold), then the count restarts."""
        if not self.hold_step:
            if self._hold_since is not None:
                self.hold_stats["max_s"] = max(self.hold_stats["max_s"], now - self._hold_since)
            self._hold_since, self._esc_streak = None, 0
            return
        if self._hold_since is None:
            self._hold_since = now
        to = self.cfg.hold_timeout_s
        if to is None or now - self._hold_since < to - 1e-9:
            return
        held = now - self._hold_since
        self.hold_stats["max_s"] = max(self.hold_stats["max_s"], held)
        self.hold_step, self._hold_since = False, None
        self.hold_stats["escapes"] += 1
        entry["hold_escape"] = True
        self._escape_step, self._esc_streak = True, self._esc_streak + 1
        self.events.append({"t": round(now, 4), "event": "hold_escape", "ds": ds, "held_s": round(held, 4),
                            "t1_false": list(entry.get("t1_check") or []), "phase": self.skill.phase,
                            "streak": self._esc_streak})
        cap = self.cfg.hold_escape_cap
        if cap is not None and self._esc_streak >= cap:
            self.hold_stats["stuck"] += 1
            self.events.append({"t": round(now, 4), "event": "hold_stuck", "ds": ds, "escapes": self._esc_streak,
                                "t1_false": list(entry.get("t1_check") or []), "phase": self.skill.phase})
            self._esc_streak = 0
            self._fail_event(now, "hold_stuck", "m4_hold")

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
        if self.cfg.stop_wait and any(it["meta"]["kind"] == "dec" for it in self.q._items):
            self.n_stop_ticks = getattr(self, "n_stop_ticks", 0) + 1  # C0: the arm waits for the answer
            a = self.last_a if self.last_a is not None else np.concatenate([q_meas[:7], [q_meas[7]]])
            return np.clip(a, obs["low"], obs["high"])
        if self.couple_out is not None:
            self.skill.speed_scale = self.couple_out.speed_scale
        cmd = self.skill.tick(now, raw, pred, tcp_p, tz)
        if self.couple_out is not None and self.cfg.backend != "fused" and np.any(self.couple_out.step6):
            cmd.pos_w, cmd.quat_w = self.skill.nudge(self.couple_out.step6, tz)
        gripped = any("gripper" in c and "o3" in c for c in raw.get("contacts", []))
        self._trace.append((round(now, 3), self.skill.phase, round(float(raw["grip"]["w"]), 4),
                            round(float(raw["grip"].get("effort", 0.0)), 3), bool(gripped),
                            pred.get("holding(o3)"), pred.get("gripper_open")))
        for e in cmd.events:
            if e.get("event") in ("object_lost", "grasp_miss"):  # diagnostics: the last 0.4 s of grip signals
                e["trace"] = [list(x) for x in self._trace]
                e["trace_cols"] = ["t", "phase", "w", "effort", "gripped", "holding", "gripper_open"]
                self._fail_event(now, e["event"], "t1_skill")  # T_fail stand-in (falsify first, canon §84 supp 1)
            self.events.append(e)
        self.prev_cmd = self.skill.cmd_pos.copy()
        if self.cfg.backend == "fused":
            a = self._play_chunk(now, q_meas)
            if self.driver is not None:
                a = self._couple_fused(a, now, kin, tcp_p)
            a = self._blend(a)
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
        dec = {q: self.ledger.decision(q, kn, now) for q in self.questions}
        committed = {q: c for q, (c, st) in dec.items() if c is not None}
        from ..serialize import canonicalize
        from ..train.stageb_data import image_only_state
        l1 = self._m1_last
        ctx = {"t_state": now, "ds": kn, "joint_pos": np.asarray(obs["joint_pos"], float).copy(),
               "joint_pos_prev": None if self._jp_prev is None else self._jp_prev.copy(),
               "dt_prev": None if self._t_prev is None else now - self._t_prev,
               "images": {k: v.copy() for k, v in self.frames.items()}, "phase": self.skill.phase,
               "ctx_text": canonicalize(image_only_state(self._s0(now, l1[2], l1[1], l1[3])) + "\n"
                                        + self.segment_intent + "\n" + self.motion.line()),
               "text": fused_state_text(self.instruction, self.skill.stage, self.skill.phase, obs["joint_pos"])}
        model, cfg = self.model, self.cfg

        def run():
            rh = request_hash({"api": "chunk", "model_id": cfg.model_id, "ctx_text": ctx["ctx_text"],
                               "phase": ctx["phase"], "committed": committed, "joint_pos": ctx["joint_pos"],
                               "joint_pos_prev": ctx["joint_pos_prev"], "dt_prev": ctx["dt_prev"]}, ctx["images"])
            r = model.chunk(ctx, committed)
            return {"latency_s": r.latency_s, "res": r, "req_hash": rh}
        self.chunk_stats["requested"] += 1
        self.q.submit(now, self.pool.submit(run), fixed_latency=getattr(model, "synthetic_chunk_latency", None),
                      meta={"kind": "chunk", "ds": kn, "t_state": now, "dec": committed, "lag": self._play_lag,
                            "status": {q: st for q, (c, st) in dec.items()}})

    def _deliver_chunk(self, r, now):
        m, res = r["meta"], r["res"]
        self.chunk_stats["delivered"] += 1
        self.chunk_log.append({"ds": m["ds"], "t_state": round(m["t_state"], 4), "t_deliver": round(r["t_deliver"], 4),
                               "latency_s": round(res.latency_s, 4), "dec": m["dec"], "status": m["status"],
                               "error": res.error, "meta": res.meta, "canary_id": self.cfg.canary_id})
        self.chunk_log[-1]["request_sha256"], self.chunk_log[-1]["image_sha256"] = r.get("req_hash") or (None, {})
        if res.error is None and res.chunk is not None:
            self.chunks[m["ds"]] = {"t_state": m["t_state"], "chunk": np.asarray(res.chunk, float),
                                    "dt": res.chunk_dt, "dec": m["dec"], "lag": m.get("lag", 0.0)}

    def _play_chunk(self, now, q_meas):
        """Play the chunk of the current step only if it was conditioned on the decisions being executed; else hold
        the last action (never a stop)."""
        from .fused_action import chunk_value
        self._chunk_played = False
        c = self.chunks.get(self.cur_k)
        dec = {q: v for q, v in self.skill.dec.items() if v is not None}
        if c is not None and c["dec"] == dec and dec:
            self.chunk_stats["played"] += 1
            self._chunk_played, self._played_t_state = True, c["t_state"]
            lag = self._play_lag - c.get("lag", 0.0)  # lag accrued since this chunk's observation (0.0 when off)
            return chunk_value(c["chunk"], c["dt"], c["t_state"], now - lag if lag else now)
        if c is not None and (self.hold_step or self._escape_step) and self.cfg.hold_play_chunk:
            # fix F25 I1: the escape step's chunk was requested during the hold (reopened slots -> committed {}),
            # its decisions never match the escape step's ones -> played by the same fallback (escape_played)
            if not self.hold_step:
                self.chunk_stats["escape_played"] += 1
            # Task 25 item 3: an M4 hold empties the step's decisions, so the step's chunk never matches them; dropping
            # it froze the arm on the action that produced the contradiction (vla_alone_diag.md: 99 % of the unplayed
            # ticks were stale_dec). While held, the step's chunk (the newest one, from an observation <= T_c +
            # chunk_lead_s old) is played; the skill runs no decisions ('next' events off) and the coupling's gripper
            # gate (_couple_fused) still applies. hold_play_chunk False = the old hold (last action, chunk dropped)
            else:
                self.chunk_stats["hold_played"] += 1
            self._chunk_played, self._played_t_state = True, c["t_state"]
            lag = self._play_lag - c.get("lag", 0.0)
            return chunk_value(c["chunk"], c["dt"], c["t_state"], now - lag if lag else now)
        if c is not None:
            self.chunk_stats["stale_dec"] += 1
        self.chunk_stats["held"] += 1
        return self.last_a if self.last_a is not None else q_meas

    def _blend(self, a):
        """Fused chunk-transition blending (plan 2026-09-26 Task 25 B; user rule: no jumps, joint speed <= 0.04 rad
        per tick): the arm joints move from the last command at most blend_max_dq x (1 - 1e-6) per tick (a hard
        per-joint clamp with a small margin so the logged step stays under the limit also in float32, fix F25 M7;
        a chunk switch with a 0.3 rad gap is reached in 8 ticks); the gripper, when a switch jumps by more than the
        played chunk's own per-tick rate, moves at the Task 17 catch rate (_grip_catch_rate: own rate + the gap over
        one chunk horizon) until it has caught up. A no-op (the same object returned) when every step is within the
        limit, so a smooth chunk sequence, the play clock and the coupling bias bookkeeping are untouched; the
        gripper is left to Task 17's limiter while that one is pending (couple gate catch-up)."""
        lim = self.cfg.blend_max_dq
        if lim is None or self.last_a is None:
            return a
        prev = np.asarray(self.last_a, float)
        a = np.asarray(a, float)
        d = a[:7] - prev[:7]
        if float(np.max(np.abs(d))) > lim:
            a = a.copy()
            m = lim * (1.0 - 1e-6)
            a[:7] = prev[:7] + np.clip(d, -m, m)
            self.chunk_stats["blend_arm"] += 1
        if self._grip_lim is not None:
            self._grip_blend = None
            return a
        gap = float(a[7] - prev[7])
        rate = self._grip_blend
        if rate is not None and not self._chunk_played:
            return a  # a held tick (a = last_a) keeps the running limit pending, as Task 17's limiter does
        if rate is None:
            if not self._chunk_played or abs(gap) <= self._chunk_grip_rate() + 1e-12:
                return a
            rate = self._grip_catch_rate(abs(gap))
        if abs(gap) <= rate + 1e-12:
            self._grip_blend = None
            return a
        self._grip_blend = rate
        a = a.copy()
        a[7] = prev[7] + math.copysign(rate, gap)
        self.chunk_stats["blend_grip"] += 1
        return a

    def _chunk_grip_rate(self) -> float:
        """The current step's chunk: its max per-tick gripper change at the control rate (0 without a usable one)."""
        c = self.chunks.get(self.cur_k)
        if c is None or len(c["chunk"]) < 2 or not c.get("dt"):
            return 0.0
        w = np.asarray(c["chunk"], float)[:, 7]
        return float(np.max(np.abs(np.diff(w)))) * self.dt / float(c["dt"])

    def _sample_frames(self, now):
        ph = self.skill.phase
        if (now - self._last_sample >= FRAME_SAMPLE_S or ph != self._phase_seen) and self.frames \
                and len(self.sampled) < 40:
            for name, img in self.frames.items():
                self.sampled.append((round(now, 2), ph, name, img.copy()))
            self._last_sample, self._phase_seen = now, ph

    # ------------------------------------------------------------------ summary
    def _hold_summary(self) -> dict:
        """M4 hold record (Task 25 + fix F25 I2): escapes, hold_stuck escalations, longest continuous hold, total held
        time and its share of the episode (the running step counted up to the last tick). A permanent hold cannot
        occur any more, so the pod analysis reads total_s / frac / stuck instead of 'held from first hold to the end'."""
        live = self.t_last - self._t_bprev if self._t_bprev is not None and self.hold_step else 0.0
        total = self.hold_stats["total_s"] + max(live, 0.0)
        run = self.t_last - self._hold_since if self._hold_since is not None else 0.0
        T = max(self.t_last, 1e-9)
        return {"escapes": self.hold_stats["escapes"], "stuck": self.hold_stats["stuck"],
                "timeout_s": self.cfg.hold_timeout_s, "escape_cap": self.cfg.hold_escape_cap,
                "max_s": round(max(self.hold_stats["max_s"], run), 4), "total_s": round(total, 4),
                "frac": round(total / T, 4)}

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
                                    for d in ("ack", "patch", "replace", "run_instruction", "reset", "invalid")},
                "hb_mode": self.cfg.hb_mode, "astra_budget": self.cfg.hb_budget,
                "astra_by_kind": dict(self.hb.n_by_kind),
                "astra_latency_s": {"p50": _pct(hb_lat, 50), "max": max(hb_lat) if hb_lat else None},
                "final_phase": self.skill.phase, "final_stage": self.skill.stage,
                "grasp_retries": self.skill.retries, "chunk": dict(self.chunk_stats),
                "hold": self._hold_summary(),
                "condition": self.cfg.condition, "stop_ticks": getattr(self, "n_stop_ticks", 0),
                "dec_inflight": {"max": max(self.inflight_at_send, default=None),
                                 "mean": round(float(np.mean(self.inflight_at_send)), 3)
                                 if self.inflight_at_send else None, "n_sends": len(self.inflight_at_send)},
                "j5": dict(self.j5_stats) if self.cal is not None else None,
                "measure": {**self.measure_stats, "verify_calibrated": self.vcal.calibrated,
                            "verify_cal": self.cfg.verify_cal or "default (uncalibrated)",
                            "critic_thr": self.vcal.critic_thr},
                "couple": self.driver.summary() if self.driver is not None else None}
