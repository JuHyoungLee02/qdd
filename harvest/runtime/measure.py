"""M4 (b)(2) `measure()` source table and the M7 critic (canon §61, §64; D28 §3.1; e_m4b_meas.md).

Replaces the old `holds(expected_after, measured)` path (privileged predicate state) with a per-predicate source:
  - robot side T1 (hard channel allowed): gripper_open, holding_t, lifted_holding <- proprioceptive code rules
    (gripper width, |gripper effort|, TCP height above the table from FK); thresholds = the E-M4b-meas P rule fit
    on FI-DEV calibration seeds 0-14 (PC2 passed: BA 0.998 / 0.992 / 0.992, nominal false alarms 0).
  - world side T2 (soft only): on_tp, contact_tp, lifted_t, near_tp, above_tp and contact_stall <- the verification
    head V1h of the same backbone (per-predicate temperature + split conformal alpha 0.1). A conformal set with both
    values OR the empty set (9 % in E-M4b-meas) = `unknown` (canon §64 decision: withhold, never a contradiction).
    Robot-side predicates are never read from the head for M4 (b) (T1 = proprio code).
  - M7 critic alarm = V1h alone over the 9 test predicates (PC3: V1h+P recall 0.786 < V1h alone 0.871): per snapshot
    score = max over the phase's expected predicates of P(value != expected) (m4b.analyze.viol_prob), persistence 2
    snapshots (min), alarm when score > the episode-level FWER threshold (0.947 for the E-M4b-meas V1h heads). The T1
    rules are a separate HARD channel (2 consecutive violations), never summed into the alarm.
Expectations per phase = m4b.spec.EXPECT (the E-M4b-meas phase table). Pure numpy, harness neutral.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field

from ..m4b import spec as FS

PREDS = FS.PREDS  # 5 world + 4 robot test predicates (the V1h head's output order)
T1 = ("gripper_open", "holding_t", "lifted_holding")
SOURCE_TABLE = {**{p: ("proprio", "T1") for p in T1},
                **{p: ("v1h", "T2") for p in FS.WORLD + ("contact_stall",)}}
ALPHA_SET, PERSIST = 0.1, 2
UNCAL_QHAT = 0.5  # uncalibrated head: the argmax singleton (flagged calibrated = False in every log)


@dataclass
class ProprioRules:
    """E-M4b-meas P rule (m4b.prules) with the registered thresholds (results.json m4b.P_params, e_m4b_meas.md §4.2):
    open = width >= 80.5 mm; holding = 50.1 mm < width < 80 mm and |grip effort| >= 1.14; lifted_holding = holding and
    TCP z (table frame) >= 12.4 cm."""
    th_w: float = 0.08050180748425541
    th_lo: float = 0.050083791321819116
    th_hi: float = 0.08
    th_I: float = 1.1361367473628952
    th_z: float = 0.12399572093997799

    def eval(self, width: float, grip_effort: float, tcp_z: float) -> dict:
        hold = self.th_lo < width < self.th_hi and abs(grip_effort) >= self.th_I
        return {"gripper_open": bool(width >= self.th_w), "holding_t": bool(hold),
                "lifted_holding": bool(hold and tcp_z >= self.th_z)}

    @classmethod
    def from_m4b_results(cls, path: str) -> "ProprioRules":
        p = json.load(open(path, encoding="utf-8"))["m4b"]["P_params"]
        return cls(**{k: float(p[k]) for k in ("th_w", "th_lo", "th_hi", "th_I", "th_z")})


@dataclass
class VerifyCal:
    """Per-predicate temperature T and conformal q-hat of one verification head + the critic threshold."""
    T: dict
    qhat: dict
    critic_thr: float | None
    alpha: float = ALPHA_SET
    calibrated: bool = True
    head: str = ""
    source: str = ""
    persist: int = PERSIST
    extra: dict = field(default_factory=dict)

    def check(self) -> "VerifyCal":
        miss = [p for p in PREDS if p not in self.T or p not in self.qhat]
        if miss:
            raise ValueError(f"verify calibration misses {miss}")
        return self

    @classmethod
    def default(cls) -> "VerifyCal":
        return cls({p: 1.0 for p in PREDS}, {p: UNCAL_QHAT for p in PREDS}, None, calibrated=False,
                   source="uncalibrated default (T = 1, argmax singleton, no critic threshold)")

    @classmethod
    def from_m4b_results(cls, path: str, head: str = "") -> "VerifyCal":
        r = json.load(open(path, encoding="utf-8"))
        T = {p: float(r["m4b"]["V1h_temperature"][p]) for p in PREDS}
        q = {p: float(r["m4b"]["V1h"]["per_pred"][p]["qhat"]) for p in PREDS}
        c = r["critic"]["V1h"]
        return cls(T, q, float(c["thr"]["v1h"]), alpha=ALPHA_SET, head=head, source=f"e_m4b_meas {path}",
                   extra={"critic_alpha": c.get("alpha_per_channel")}).check()

    def save(self, path: str) -> None:
        json.dump({"format": "verify-cal-v1", **asdict(self)}, open(path, "w", encoding="utf-8"), indent=1)

    @classmethod
    def load(cls, path: str) -> "VerifyCal":
        d = json.load(open(path, encoding="utf-8"))
        if d.pop("format", None) != "verify-cal-v1":
            raise ValueError(f"{path}: not a verify-cal-v1 file")
        return cls(**d).check()


def _sig(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, z))))


def v1h_probs(logits: dict, cal: VerifyCal) -> dict:
    """Calibrated P(predicate true) = sigmoid(logit / T)."""
    return {p: _sig(float(z) / cal.T.get(p, 1.0)) for p, z in logits.items() if z is not None}


def conformal_value(p_true: float, qhat: float):
    """Split conformal (nonconformity 1 - p(label)): {True} -> True, {False} -> False, both or empty -> None."""
    has1, has0 = (1.0 - p_true) <= qhat, p_true <= qhat
    if has1 == has0:
        return None
    return bool(has1)


def measure(proprio: dict | None, v1h_logits: dict | None, cal: VerifyCal, rules: ProprioRules | None = None) -> dict:
    """{predicate: {value (True/False/None = unknown), p, source, tier}} from the source table.
    proprio = {"width": m, "grip_effort": joint effort, "tcp_z": m above the table top (FK)} (None = not available)."""
    rules = rules or ProprioRules()
    robot = rules.eval(proprio["width"], proprio["grip_effort"], proprio["tcp_z"]) if proprio else {}
    prob = v1h_probs(v1h_logits, cal) if v1h_logits else {}
    out = {}
    for p in PREDS:
        src, tier = SOURCE_TABLE.get(p, ("v1h", "T2"))
        if src == "proprio":
            out[p] = {"value": robot.get(p), "p": prob.get(p), "source": src, "tier": tier}
        else:
            pp = prob.get(p)
            v = None if pp is None else conformal_value(pp, cal.qhat.get(p, UNCAL_QHAT))
            out[p] = {"value": v, "p": pp, "source": src, "tier": tier}
    return out


def values(meas: dict) -> dict:
    return {p: m["value"] for p, m in meas.items()}


def expected_check(phase: str, meas: dict) -> dict:
    """(b)(2) of the step that ran in `phase`, judged on this measurement: T1 false -> CONTRADICT (hard channel);
    T2 conformal {False} -> DEVIATE (soft, M7 C_m4); unknown -> no verdict. OR entries: false only if every member
    is measured false; an OR entry counts as T1 only if all members are T1."""
    t1f, t2f, unk = [], [], []
    for name, want in FS.EXPECT.get(phase, ()):
        names = name if isinstance(name, tuple) else (name,)
        if any(x not in meas for x in names):  # outside the given scope (e.g. a T1-only or T2-only check)
            continue
        vals = [meas[x]["value"] for x in names]
        label = FS.exp_name(name)
        if any(v is None for v in vals) and not (want and any(vals)):
            unk.append(label)
            continue
        got = any(vals) if isinstance(name, tuple) else bool(vals[0])
        if got == want:
            continue
        (t1f if all(meas[x]["tier"] == "T1" for x in names) else t2f).append(label)
    out = "CONTRADICT" if t1f else ("DEVIATE" if t2f else "OK")
    return {"outcome": out, "hard": bool(t1f), "t1_false": t1f, "t2_false": t2f, "unknown": unk}


def viol_prob(phase: str, p: dict) -> float:
    """m4b.analyze.viol_prob (all 9 predicates in scope): max over the phase's expected predicates of P(!= expected)."""
    out = 0.0
    for name, want in FS.EXPECT.get(phase, ()):
        names = name if isinstance(name, tuple) else (name,)
        vals = [p.get(x) for x in names]
        if any(v is None for v in vals):
            continue
        q = max(vals)
        out = max(out, 1.0 - q if want else q)
    return float(out)


class Critic:
    """M7 critic, V1h channel only (canon §64). update() once per verification-head output (snapshot)."""

    def __init__(self, cal: VerifyCal):
        self.cal, self.raw, self.alarms, self.log = cal, [], [], []

    def update(self, t: float, phase: str, v1h_logits: dict) -> dict:
        v = viol_prob(phase, v1h_probs(v1h_logits, self.cal))
        self.raw.append(v)
        k = max(1, int(self.cal.persist))
        score = min(self.raw[-k:]) if len(self.raw) >= k else 0.0
        thr = self.cal.critic_thr
        alarm = thr is not None and score > thr
        if alarm:
            self.alarms.append(round(float(t), 4))
        r = {"t": round(float(t), 4), "phase": phase, "raw": round(v, 5), "score": round(score, 5), "thr": thr,
             "alarm": bool(alarm)}
        self.log.append(r)
        return r


class HardChannel:
    """M7 hard channel from the T1 proprio rules: the phase expectation violated for `persist` consecutive checks ->
    one event (re-armed after a clean check)."""

    def __init__(self, persist: int = PERSIST):
        self.persist, self.streak, self.fired, self.events = persist, 0, False, []

    def update(self, t: float, phase: str, meas: dict):
        c = expected_check(phase, {p: m for p, m in meas.items()})
        bad = c["t1_false"]
        if not bad:
            self.streak, self.fired = 0, False
            return None
        self.streak += 1
        if self.streak >= self.persist and not self.fired:
            self.fired = True
            ev = {"t": round(float(t), 4), "phase": phase, "preds": bad}
            self.events.append(ev)
            return ev
        return None
