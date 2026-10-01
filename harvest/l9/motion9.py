"""L9 human-like motion (spec §10, user-approved 2026-10-01): an executor that moves between the SAME commanded points
as the L8S MinJerkExec (the truth labels / commands are unchanged), with a per-episode motion style:
  profile    the time profile of a move: min-jerk bell (Flash & Hogan 1985), or two-phase reaching -- a fast transport
             covering `split` of the distance, then a slow homing phase (Jeannerod 1984; Woodworth-style correction)
  speed      average transport speed (m/s) and a caution factor slowing the final phase
  curvature  transport moves (gripper keep, > 6 cm) bend through one via point: lifted by `arc` x distance and moved
             sideways by `side` x distance (bounded: <= 5 cm up, <= 3 cm sideways; grasp / release moves stay straight)
  preshape   during a descend-and-close move the pads close from fully open towards the object width + margin,
             reaching it at `preshape_at` (60-80 %) of the move (aperture scaled to the object, Jeannerod)
  pause      before a release the hand holds still for `pause_s` (a short check), after a grasp for `settle_s`
  elbow      a small null-space pull of the arm joints towards their range centres (comfortable posture; world9)
Safety stays the L8S rule: the world clamps every joint command step to ARM_DQ (<= 0.04 rad measured); the executor
only changes the Cartesian reference. Pure except nothing (numpy)."""
from __future__ import annotations

import hashlib

import numpy as np

from ..astra_solo.executor import EXTRA_S, MIN_T, MinJerkExec, min_jerk
from ..astra_motion.executor import BLOCKED_M, REACH_TOL_M, clip_box

MOTION_VERSION = "l9m-2"  # l9m-1 -> -2 (motion1 pilot, 127 eps: 64.6 % vs 73.6 % baseline): arc <= 0.12, wider pre-shape margin, gentler two-phase homing
PROFILES = ("minjerk", "two_phase")


def sample_style(seed: int) -> dict:
    """Per-episode motion style (seeded; recorded in meta.motion_style)."""
    rng = np.random.default_rng([int(seed), 1010])
    prof = PROFILES[int(rng.integers(len(PROFILES)))]
    return {"version": MOTION_VERSION, "profile": prof,
            "v_avg": round(float(rng.uniform(0.06, 0.11)), 4),
            "caution": round(float(rng.uniform(0.0, 0.5)), 3),
            "split": round(float(rng.uniform(0.70, 0.85)), 3),
            "arc": round(float(rng.uniform(0.0, 0.12)), 3),
            "side": round(float(rng.uniform(-0.12, 0.12)), 3),
            "preshape": bool(rng.random() < 0.8),
            "preshape_margin": round(float(rng.uniform(0.025, 0.04)), 4),
            "preshape_at": round(float(rng.uniform(0.6, 0.8)), 3),
            "pause_s": round(float(rng.uniform(0.15, 0.6)), 3),
            "settle_s": round(float(rng.uniform(0.0, 0.3)), 3),
            "elbow": round(float(rng.uniform(0.0, 0.02)), 4)}


def two_phase(s: float, split: float, caution: float) -> float:
    """Fraction of the path at normalised time s: a min-jerk transport to `split` of the path in the first part of
    the time, then a min-jerk homing over the rest; caution gives the homing more of the time (slower end)."""
    s = min(max(s, 0.0), 1.0)
    tf = 0.55 - 0.2 * caution  # time share of the transport phase
    if s <= tf:
        return split * min_jerk(s / tf)
    return split + (1.0 - split) * min_jerk((s - tf) / (1.0 - tf))


def via_point(p0, p1, arc: float, side: float):
    """Via point of a curved transport: the midpoint lifted by arc x distance (<= 5 cm) and moved sideways by
    side x distance (<= 3 cm, horizontal, perpendicular to the move)."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    L = float(np.linalg.norm(d))
    m = (p0 + p1) / 2
    up = min(arc * L, 0.05)
    h = np.array([-d[1], d[0], 0.0])
    hn = float(np.linalg.norm(h))
    lat = np.zeros(3) if hn < 1e-6 else h / hn * float(np.clip(side * L, -0.03, 0.03))
    return m + np.array([0.0, 0.0, up]) + lat


def bezier(p0, c, p1, u: float):
    return (1 - u) ** 2 * p0 + 2 * (1 - u) * u * c + u ** 2 * p1


class HumanExec(MinJerkExec):
    def __init__(self, dt, table_z, tcp0, w_open, w_close, style: dict, quat0=(1.0, 0.0, 0.0, 0.0)):
        super().__init__(dt, table_z, tcp0, w_open, w_close, v_avg=float(style["v_avg"]), quat0=quat0)
        self.style = dict(style)
        self.shape = None  # (via point or None, profile)
        self.hold_until = None  # pause before acting on the gripper
        self._held = None

    def go_to(self, pos, grip: str, t: float) -> list:
        q, c = clip_box(pos, self.table_z)
        ev = [{"t": round(t, 3), "event": "clipped", "want": np.round(np.asarray(pos, float), 4).tolist(),
               "got": np.round(q, 4).tolist()}] if c else []
        p0 = self.cmd.copy()
        d = float(np.linalg.norm(q - p0))
        st = self.style
        transport = grip == "keep" and d > 0.06
        via = via_point(p0, q, st["arc"], st["side"]) if transport else None
        if via is not None:  # keep the via point inside the box (and never below the start / end)
            via, _ = clip_box(np.maximum(via, [via[0], via[1], max(p0[2], q[2])]), self.table_z)
        L = d if via is None else float(np.linalg.norm(via - p0) + np.linalg.norm(q - via))
        T = max(L / self.v_avg, MIN_T)
        if st["profile"] == "two_phase":
            T *= 1.0 + 0.35 * st["caution"]
        self.target = q.copy()
        self.seg = (p0, q, t, T, grip)
        self.shape = (via, st["profile"] if grip != "open" else "minjerk")
        self._still = 0
        return ev

    def _path(self, s: float):
        p0, p1, _, _, _ = self.seg
        via, prof = self.shape
        u = two_phase(s, self.style["split"], self.style["caution"]) if prof == "two_phase" else min_jerk(s)
        if via is None:
            return p0 + (p1 - p0) * u
        return bezier(p0, via, p1, u)

    def tick(self, t: float, tcp):
        tcp = np.asarray(tcp, float)
        if self.hold_until is not None:  # a short pause before the gripper acts
            if t < self.hold_until - 1e-9:
                return self.cmd.copy(), self.width, []
            self.hold_until = None
            g = self._held
            self._held = None
            return self.cmd.copy(), self.width, self._act(g, t, tcp)
        if self.seg is None or self.wait_until is not None or self.pending_grip is not None:
            return super().tick(t, tcp)
        p0, p1, t0, T, g = self.seg
        s = (t + self.dt - t0) / T
        self.cmd = self._path(s)
        if g == "close" and self.style["preshape"]:  # pre-shape the aperture towards the object width
            a = min(max(s / float(self.style["preshape_at"]), 0.0), 1.0)
            goal = min(self.w_open, self.w_close + 0.014 + float(self.style["preshape_margin"]))
            self.width = self.w_open + (goal - self.w_open) * min_jerk(a)
        at_cmd = s >= 1.0
        err = float(np.linalg.norm(tcp - p1))
        from ..astra_motion.executor import SETTLE_M_PER_TICK, SETTLE_TICKS
        moved = float(np.linalg.norm(tcp - self._last_tcp)) if self._last_tcp is not None else 1.0
        self._last_tcp = tcp.copy()
        self._still = self._still + 1 if (at_cmd and moved < SETTLE_M_PER_TICK) else 0
        settled = self._still >= SETTLE_TICKS
        ev = []
        if at_cmd and (err < REACH_TOL_M or settled or t > t0 + T + EXTRA_S):
            kind = "reach" if err < REACH_TOL_M else ("settled" if settled and err <= BLOCKED_M else "timeout")
            ev.append({"t": round(t, 3), "event": kind, "err_mm": round(err * 1e3, 1)})
            self.seg = None
            if g in ("open", "close"):
                pause = float(self.style["pause_s"] if g == "open" else self.style["settle_s"])
                if pause > 0:
                    self.hold_until, self._held = t + pause, g
                else:
                    ev += self._act(g, t, tcp)
        return self.cmd.copy(), self.width, ev

    @property
    def busy(self) -> bool:
        return bool(super().busy or self.hold_until is not None)


def install() -> None:
    """Process-level opt-in (L9 runner only): Episode.make_exec returns a HumanExec when the world carries a motion
    style (world.motion); otherwise the original executor (L8S unchanged)."""
    from ..astra_solo import episode as E
    if getattr(E.Episode.make_exec, "_l9", False):
        return
    orig = E.Episode.make_exec

    def make_exec(self, st):
        style = getattr(self.w, "motion", None)
        if not style:
            return orig(self, st)
        w = self.w
        return HumanExec(w.dt, w.table_z, st["tcp"], w.w_open, w.w_close, style, quat0=w.quat0)

    make_exec._l9 = True
    E.Episode.make_exec = make_exec


Q_MID = (-0.9, -0.9, 1.2, -1.9, 0.5, 1.1, 1.5)  # typical right-arm work posture (L9 smoke / L8S); left = mirror


def nullspace_pull(J: np.ndarray, q: np.ndarray, q_mid, gain: float) -> np.ndarray:
    """Joint offset (7) in the null space of the 6 x 7 TCP jacobian pulling q towards q_mid (does not move the TCP to
    first order)."""
    if gain <= 0:
        return np.zeros(len(q))
    Jp = np.linalg.pinv(J)
    N = np.eye(J.shape[1]) - Jp @ J
    return gain * (N @ (np.asarray(q_mid, float) - np.asarray(q, float)))


def style_hash(style: dict) -> str:
    return hashlib.sha256(repr(sorted(style.items())).encode()).hexdigest()[:10]
