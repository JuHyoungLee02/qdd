"""Falsify-first recovery reuse (canon §84 + supplement 1). A repeated diagnosis with the SAME failure signature
(stage + target object + failure type + detector evidence) first evaluates the stored lesson's falsify checks in code;
not falsified -> the stored recovery is reused without an Astra call, at most once per episode and signature; a
falsified / unevaluable lesson, a second repeat, a failed reuse, a partial signature match or a first-seen diagnosis
-> Astra J2. Every branch is appended to `audit` (J5 audit and J6 distillation input: Astra sees the reuses later).
Lessons are kept across episodes (runtime lifetime); the reuse cap is per episode."""
from __future__ import annotations

from dataclasses import asdict, astuple, dataclass

PREDS = ("holding_t", "gripper_open", "lifted_holding", "contact_tp", "on_tp", "lifted_t")


@dataclass(frozen=True)
class FailSig:
    stage: str
    target: str
    mode: str
    evidence: str

    def to_json(self) -> dict:
        return asdict(self)


@dataclass
class Lesson:
    sig: FailSig
    recovery: dict
    falsify: tuple
    falsify_text: str
    source: str
    t: float


def check_falsify(checks) -> tuple:
    out = []
    for c in checks:
        if not (isinstance(c, dict) and c.get("pred") in PREDS and isinstance(c.get("value"), bool)):
            raise ValueError(f"falsify check {c!r}: {{pred in {PREDS}, value: bool}}")
        out.append({"pred": c["pred"], "value": c["value"]})
    return tuple(out)


def falsified(checks, facts: dict) -> str:
    vals = [facts.get(c["pred"]) for c in checks]
    if any(v is not None and bool(v) == c["value"] for v, c in zip(vals, checks)):
        return "yes"
    return "unknown" if any(v is None for v in vals) else "no"


class RecoveryCache:
    def __init__(self):
        self.lessons, self.reuse, self.audit = {}, {}, []

    def remember(self, sig: FailSig, recovery: dict, falsify, falsify_text: str, source: str, now: float) -> None:
        self.lessons[sig] = Lesson(sig, dict(recovery), check_falsify(falsify), falsify_text, source, now)
        self.audit.append({"t": round(now, 3), "event": "remember", "sig": sig.to_json(), "source": source,
                           "recovery": dict(recovery), "falsify_text": falsify_text})

    def _log(self, now, episode, sig, decision, lesson, why):
        self.audit.append({"t": round(now, 3), "event": "decide", "episode": episode, "sig": sig.to_json(),
                           "decision": decision, "why": why, "source": lesson.source if lesson else None})
        return decision, lesson, why

    def decide(self, episode: int, sig: FailSig, facts: dict, now: float):
        e = self.lessons.get(sig)
        if e is None:
            partial = any(0 < sum(a == b for a, b in zip(astuple(s), astuple(sig))) < 4 for s in self.lessons)
            return self._log(now, episode, sig, "call_j2", None, "partial_match" if partial else "first_seen")
        st = self.reuse.get((episode, sig))
        if st is not None:
            return self._log(now, episode, sig, "call_j2", e, "reuse_failed" if st == "failed" else "reuse_cap")
        f = falsified(e.falsify, facts)
        if f != "no":
            return self._log(now, episode, sig, "call_j2", e, "falsified" if f == "yes" else "falsify_unknown")
        self.reuse[(episode, sig)] = "pending"
        return self._log(now, episode, sig, "reuse", e, "not_falsified")

    def report(self, episode: int, sig: FailSig, success: bool, now: float) -> None:
        if self.reuse.get((episode, sig)) == "pending":
            self.reuse[(episode, sig)] = "succeeded" if success else "failed"
            self.audit.append({"t": round(now, 3), "event": "reuse_outcome", "episode": episode,
                               "sig": sig.to_json(), "success": bool(success)})
