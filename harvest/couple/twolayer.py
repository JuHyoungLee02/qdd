"""Between the two layers (spec §5, §11, §12; canon §86, plan rulings 1, 2, 6; controller ruling P3 2026-09-26).
TwoLayerGate: an irreversible transition the VLA side wants (close = gripper close, stage = S1 -> S2, release =
gripper open at the place) is allowed only when
  (a) a fresh Astra answer (arrived <= astra_fresh_s ago) does not veto it (intent misaligned / execution failed with
      confidence not low, or an edit whose gripper opposes it; strict mode: intent must be aligned), and with no
      fresh answer the VLA carries the flow (spec §5 "> 3 s 무답"), and
  (b) there is evidence -- the T1 proprio premise ONLY (close: gripper open inside the near/contact zone; stage and
      release: holding). A gated active-wrist claim of the transition (grasp_ready / grasped / placed, SUPPORT[kind])
      is reference only (canon §86: "Astra의 잡음·놓음 주장은 참고용, 비가역 관문의 근거는 T1 전제와 V1h") -- it never
      opens the gate by itself; it is recorded (`wrist_claim`) but never changes the reason string.
Reasons: "no_evidence" when T1 fails; "t1_fresh" / "t1_astra_stale" when T1 evidence allows the transition (with /
without a fresh Astra answer, resp.), plus the veto reasons above.
A transition blocked for mismatch_s raises one layer_mismatch event. Only changes of the decision are logged (each
row also carries `wrist_claim`, the reference-only wrist-support flag).
VlaFastCheck: the VLA re-decides every 0.33 s; `vla_vec` must be the EXECUTED motion -- fused backend: the current
expert chunk's TCP displacement (FK chunk end - chunk start, coupling bias excluded); modular backend: the committed
decision vector (skills execute it directly). A committed direction opposite to the offset for contra_steps
consecutive steps (adherence_cos < 0) shrinks the offset (spec §11); a zero-norm vector is treated as no information
(the count resets, like the None branch). `adherence_cos` / `follows` (canon §84 supplement 4: adherence = executed
chunk displacement vs intended direction, cos > `p.adhere_cos`) are the chunk-level measure E-SR0/E-MA2 use instead
of assuming the decision token steers the chunk (canon §84 supplement 4-5).
NoProgress: the offset moved > 1 cm over stag_s but the tip followed < stag_frac."""
from __future__ import annotations

from collections import Counter, deque

import numpy as np

from ..runtime.skills import _XY_SIGN, _Z_SIGN

IRREV = ("close", "stage", "release")
SUPPORT = {"close": "grasp_ready", "stage": "grasped", "release": "placed"}
OPPOSE = {"close": "open", "release": "close"}


def t1_evidence(kind: str, t1: dict, near: bool) -> bool:
    if kind == "close":
        return t1.get("gripper_open") is True and bool(near)
    return t1.get("holding_t") is True


class TwoLayerGate:
    def __init__(self, p):
        self.p = p
        self.blocked_since, self._state, self._flagged = {}, {}, set()
        self.log, self.counts = [], Counter()

    def _decide(self, kind, now, last, last_t, t1, near):
        fresh = last is not None and last_t is not None and now - last_t <= self.p.astra_fresh_s + 1e-9
        if fresh:
            if last.edit is not None and last.edit.gripper == OPPOSE.get(kind):
                return False, "astra_gripper_opposes", False
            if last.intent == "misaligned" and last.confidence != "low":
                return False, "astra_misaligned", False
            if last.execution == "failed" and last.confidence != "low":
                return False, "astra_failed", False
            if self.p.irrev_need_aligned and last.intent != "aligned":
                return False, "astra_not_aligned", False
        wrist = fresh and any(k == SUPPORT[kind] for k, _ in last.claims)  # reference only (canon §86), never gates
        if not t1_evidence(kind, t1, near):
            return False, "no_evidence", wrist
        return True, ("t1_fresh" if fresh else "t1_astra_stale"), wrist

    def allow(self, kind, now, last, last_t, t1: dict, near: bool) -> tuple[bool, str]:
        if kind not in IRREV:
            raise ValueError(f"irreversible kind {kind!r}: one of {IRREV}")
        ok, why, wrist = self._decide(kind, now, last, last_t, t1, near)
        if self._state.get(kind) != (ok, why):
            self._state[kind] = (ok, why)
            self.counts[f"{'allow' if ok else 'deny'}:{why}"] += 1
            self.log.append({"t": round(now, 3), "kind": kind, "ok": ok, "why": why, "wrist_claim": wrist})
        if ok:
            self.blocked_since.pop(kind, None)
            self._flagged.discard(kind)
        else:
            self.blocked_since.setdefault(kind, now)
        return ok, why

    def mismatch_due(self, kind: str, now: float) -> bool:
        t0 = self.blocked_since.get(kind)
        if t0 is None or kind in self._flagged or now - t0 < self.p.mismatch_s - 1e-9:
            return False
        self._flagged.add(kind)
        return True


def committed_vector(committed: dict):
    xy, z = _XY_SIGN.get(committed.get("dir_xy")), _Z_SIGN.get(committed.get("dir_z"), 0)
    if xy is None:
        return None
    v = np.array([xy[0], xy[1], z], float)
    return v if np.any(v) else None


def adherence_cos(vec, ref) -> float | None:
    """Cosine of two 3-vectors; None if either is None or has norm < 1e-9 (canon §84 supplement 4)."""
    if vec is None or ref is None:
        return None
    v, r = np.asarray(vec, float), np.asarray(ref, float)
    nv, nr = float(np.linalg.norm(v)), float(np.linalg.norm(r))
    if nv < 1e-9 or nr < 1e-9:
        return None
    return float(v @ r) / (nv * nr)


def follows(vec, ref, p) -> bool | None:
    """True when the executed vector follows ref (cos > p.adhere_cos); None when undefined (a zero vector)."""
    c = adherence_cos(vec, ref)
    return None if c is None else c > p.adhere_cos


class VlaFastCheck:
    def __init__(self, p):
        self.p, self.n = p, 0

    def reset(self) -> None:
        self.n = 0

    def on_step(self, vla_vec, offset_dir) -> bool:
        c = adherence_cos(vla_vec, offset_dir)
        if c is None:
            self.n = 0
            return False
        self.n = self.n + 1 if c < 0 else 0
        if self.n >= self.p.contra_steps:
            self.n = 0
            return True
        return False


class NoProgress:
    def __init__(self, p):
        self.p, self.h = p, deque()

    def update(self, now: float, tcp, applied_trans) -> bool:
        self.h.append((now, np.asarray(tcp, float).copy(), np.asarray(applied_trans, float).copy()))
        while self.h and self.h[0][0] < now - self.p.stag_s - 1e-9:
            self.h.popleft()
        t0, p0, a0 = self.h[0]
        if now - t0 < self.p.stag_s - 0.02:
            return False
        cmd = self.h[-1][2] - a0
        n = float(np.linalg.norm(cmd))
        if n < 0.01:
            return False
        moved = float((self.h[-1][1] - p0) @ (cmd / n))
        if moved < self.p.stag_frac * n:
            self.h.clear()
            return True
        return False
