"""Canonical setting table (00-interfaces §7). Change only via canon."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    T_c: float = 0.33
    near_in_m: float = 0.05
    near_out_m: float = 0.06
    h_lift_m: float = 0.03
    tilt_max_deg: float = 30.0
    success_hold_s: float = 1.0
    episode_limit_s: float = 60.0
    snapshot_dt_s: float = 0.33
    sim_dt: float = 0.01
    decimation: int = 5
    jev_model: str = "jev-1.13.0"  # Jev is unusable (user-log 46, canon §44): frozen E0 tools only
    jev_url: str = "https://api.typesafe.ai/v1/systemone"
    timeout_s: float = 2.0


CFG = Config()
