"""Tuning constants of the Astra–VLA coupling (spec 2026-09-26 §11-§16, canon §84 supplement 2). The whole dataclass
is logged with every run (RuntimeConfig.couple_params -> CoupleDriver.summary()["params"]). request_mode,
stale_edit_s, timeout_s, latency_init_s, est_text_tokens and overlay are now set from the E-Astra-motion probe
result (docs/stage3/results/astra_motion.md, canon §86 + supplement); probe_ref names that result. Remaining
fields marked PROBE are defaults until a later probe sets them."""
from __future__ import annotations

from dataclasses import asdict, dataclass

REQUEST_MODES = ("F0", "F1")
PROMPT_VERSIONS = ("v1", "v2")
PREDICT_MODES = ("chunk", "extrapolate")
CAMERAS = ("cam_head", "cam_wrist_left", "cam_wrist_right")


@dataclass(frozen=True)
class CoupleParams:
    probe_ref: str = "docs/stage3/results/astra_motion.md"  # canon §86
    # stream: one request in flight (canon §84 supp 2); effort low only (canon §82 supp 2)
    request_mode: str = "F0"  # canon §86: F0 kept (results §5/§9 — F1 flip-rate drop 0.594->0.381 misses the 50% rule)
    # plan Task 18 (E-ACC R1 adopt, docs/stage3/results/eacc.md §5): astra-couple@v2 = harvest/couple/prompt_v2.py;
    # v1 stays selectable so recorded v1 runs are reproducible. The §86 constants below (latency_init_s,
    # est_text_tokens) were measured under v1 and are re-measured under v2 in E-Couple (canon §86 note)
    prompt_version: str = "v2"
    axis_guide: bool = False  # v2 only: AxisGuide head-image axes + legend line (E-ACC R2' undecided -> off)
    extra_instruction: str = ""  # v2 only: one extra sentence before the mode rule (e.g. the E-ACC stage-2 target
    # check); part of the prompt text and of the logged prompt id (+x<sha6>)
    effort: str = "low"
    max_output_tokens: int = 1200
    timeout_s: float = 20.0  # canon §86 supplement: probe runner value (probe's 20 s was measured in sim seconds;
    # re-measure wall-clock on the real robot); results §2 latency p95 range 12-16 s
    min_interval_s: float = 0.0  # E-Astra-necessity: pace a local model to Astra's latency p50
    phase_pause_s: float | None = None  # optional cost fallback (canon §84 supp 2); None = off
    event_window_s: float = 3.0  # spec §15: no pause for 3 s after an event
    event_refractory_s: float = 3.0  # plan Task 21 B6 (couple_dry.md): a name re-flags only after this long or on a
    # new edge (condition cleared, CoupleDriver.clear); = event_window_s (spec §15)
    fail_slow_after: int = 3  # spec §7: 3 failed calls in a row -> slow down
    slow_factor: float = 0.5
    slow_down_s: float = 2.0  # info_request slow_down (plan ruling 3)
    # answers
    stale_edit_s: float = 15.0  # canon §86: results §9 — 6 s discards 70-100% of answers, age p95 ~11-14 s
    latency_init_s: float = 9.3  # canon §86: results §2, F0 mean wall-clock latency p50
    single_weight: float = 0.5  # spec §11: one answer 50 %, two agreeing answers 100 %
    same_dir_deg: float = 35.0  # PROBE prereg §4.2
    flip_deg: float = 90.0  # PROBE prereg §4.2
    small_edit_m: float = 0.005
    small_rot_rad: float = 0.05
    # offset (spec §11; PROBE prereg §4.2 smooth executor limits)
    ramp_min_s: float = 1.0
    ramp_max_s: float = 3.0
    decay_s: float = 0.5
    v_max: float = 0.08
    a_max: float = 0.32
    w_max: float = 1.5
    alpha_max: float = 6.0  # [가정] rotation acceleration cap
    contra_steps: int = 3  # VLA fast check: committed direction opposite for 3 steps (1 s) -> shrink
    contra_factor: float = 0.5
    adhere_cos: float = 0.5  # canon §84 supplement 4: adherence = executed chunk displacement vs intended
    # direction, cos > adhere_cos (twolayer.adherence_cos / follows)
    stag_s: float = 2.0  # no progress along an active offset over this window
    stag_frac: float = 0.2
    # two layers (spec §5, §12; plan rulings 1-2)
    astra_fresh_s: float = 3.0
    mismatch_s: float = 1.0
    irrev_need_aligned: bool = False
    predict_cap_m: float = 0.10  # predict_mode "extrapolate" only
    # plan Task 19 (controller ruling R19; E-ACC stage 2 / B', book 02 P113): predicted_ee_at_arrival = tip now + the
    # executing chunk displacement (committed arrow) + remaining correction, no extrapolation; "extrapolate" = the
    # old 0.5 s velocity x latency (capped predict_cap_m), kept selectable
    predict_mode: str = "chunk"
    # canon §91 arrival reconciliation (plan Task 19, controller ruling N2; harvest/couple/reconcile.py)
    recon_done_frac: float = 0.8  # done: the VLA already moved >= this fraction of the edit translation (cos >
    # adhere_cos) -- brief value (ruling N2)
    reconcile_apply: bool = True  # False = verdicts logged only (the pre-Task-19 path, gate stale drop kept): the
    # with / without arm for canon §92 P7 ("네 판정이 ... 도움이 된다") and for offset-mechanics tests
    recon_still_m: float = 0.01  # valid-still: VLA motion below this (same phase and gripper); conflict needs at
    # least this much travel against the edit -- brief value (ruling N2), = NoProgress's 1 cm floor
    # cameras, overlay (spec §12-§13)
    cameras: tuple = CAMERAS
    active_arm: str = "right"
    overlay: bool = True  # canon §86: optional, default on (results §3 — no effect on grasp judgment, harmless)
    trace_s: float = 2.5
    est_text_tokens: int = 1601  # canon §86/results §2-§3: F0 mean input 2207 - TOK_HEAD 302 - 2*TOK_WRIST 152
    # (cost.TOK_HEAD / cost.TOK_WRIST live in harvest/couple/cost.py, Task 3)

    def __post_init__(self):
        if self.request_mode not in REQUEST_MODES:
            raise ValueError(f"request_mode {self.request_mode!r}: one of {REQUEST_MODES}")
        if self.prompt_version not in PROMPT_VERSIONS:
            raise ValueError(f"prompt_version {self.prompt_version!r}: one of {PROMPT_VERSIONS}")
        if self.prompt_version == "v1" and (self.axis_guide or self.extra_instruction.strip()):
            raise ValueError("axis_guide / extra_instruction exist in prompt_version v2 only")
        if self.effort != "low":
            raise ValueError("the coupling stream runs effort low only (canon §82 supplement 2)")
        if not 0.0 <= self.single_weight <= 1.0:
            raise ValueError(f"single_weight {self.single_weight}: in [0, 1]")
        if self.phase_pause_s is not None and not self.phase_pause_s > 0:
            raise ValueError("phase_pause_s: None (off) or > 0")
        if self.predict_mode not in PREDICT_MODES:
            raise ValueError(f"predict_mode {self.predict_mode!r}: one of {PREDICT_MODES}")
        if not 0.0 < self.recon_done_frac <= 1.0 or not self.recon_still_m > 0.0:
            raise ValueError("recon_done_frac in (0, 1], recon_still_m > 0")
        if self.active_arm not in ("right", "left"):
            raise ValueError(f"active_arm {self.active_arm!r}")
        if not set(self.cameras) <= set(CAMERAS):
            raise ValueError(f"cameras {self.cameras}: subset of {CAMERAS}")

    def to_json(self) -> dict:
        d = asdict(self)
        d["cameras"] = list(self.cameras)
        return d
