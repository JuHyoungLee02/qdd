"""Tuning constants of the Astra–VLA coupling (spec 2026-09-26 §11-§16, canon §84 supplement 2). The whole dataclass
is logged with every run (RuntimeConfig.couple_params -> CoupleDriver.summary()["params"]). request_mode,
stale_edit_s, timeout_s, latency_init_s, est_text_tokens and overlay are now set from the E-Astra-motion probe
result (docs/stage3/results/astra_motion.md, canon §86 + supplement); probe_ref names that result. Remaining
fields marked PROBE are defaults until a later probe sets them."""
from __future__ import annotations

from dataclasses import asdict, dataclass

REQUEST_MODES = ("F0", "F1")
CAMERAS = ("cam_head", "cam_wrist_left", "cam_wrist_right")


@dataclass(frozen=True)
class CoupleParams:
    probe_ref: str = "docs/stage3/results/astra_motion.md"  # canon §86
    # stream: one request in flight (canon §84 supp 2); effort low only (canon §82 supp 2)
    request_mode: str = "F0"  # canon §86: F0 kept (results §5/§9 — F1 flip-rate drop 0.594->0.381 misses the 50% rule)
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
    predict_cap_m: float = 0.10
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
        if self.effort != "low":
            raise ValueError("the coupling stream runs effort low only (canon §82 supplement 2)")
        if not 0.0 <= self.single_weight <= 1.0:
            raise ValueError(f"single_weight {self.single_weight}: in [0, 1]")
        if self.phase_pause_s is not None and not self.phase_pause_s > 0:
            raise ValueError("phase_pause_s: None (off) or > 0")
        if self.active_arm not in ("right", "left"):
            raise ValueError(f"active_arm {self.active_arm!r}")
        if not set(self.cameras) <= set(CAMERAS):
            raise ValueError(f"cameras {self.cameras}: subset of {CAMERAS}")

    def to_json(self) -> dict:
        d = asdict(self)
        d["cameras"] = list(self.cameras)
        return d
