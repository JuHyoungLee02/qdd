"""M4 overlap-commit ledger (design/M4-overlap-commit.md §4.1-§4.3, §4.6; canon §4-§6, §14-3, §58).

Pure Python, harness neutral. Consumed by both runtime back-ends (canon §58): the modular stack (Jev-L DecCall) and the
fused model (decision-token probabilities + action chunk) -- both deliver typed decisions per question from staggered
calls, and this ledger decides what is committed.

One slot per (decision step ds, question). A call sent at t_send votes for the H slots starting at the first slot with
t_start >= t_send + d_hat (§4.1: H future steps; the stage-A DecCall asks one question per decision family, so the one
answer is the vote for each of the H slots -- votes of one slot come from calls with different t_state, which is what
J3 requires of agreement votes). H = 1 (canon §2 :18, M4 §4.1 :188): the one answer is the early vote of every step
whose lead window [t_start - lead_max, t_start - d_hat] holds the send time (early_ask_steps; E §2.6 schedule, canon
§75), so a step still gets 2-3 votes from staggered calls. Votes are counted by option_key (§27 R5), never by
probability (§6: gates off before E1). What is kept from §4.2:
  - premise epoch: a vote whose premise_epoch < ledger epoch is dropped (#6); STALE_MAX drop;
  - FROZEN slots (already started) and COMMITTED slots are immutable (log only, #1);
  - challenger replaces the incumbent only after the defer window W (W+1 when either choice is irreversible, §4.6):
    W = further votes for the same challenger needed after the first challenging vote (§4.2 pseudocode; W = 0
    replaces at the first one, W = 1 at the second; canon §72), or at once when an expected-vs-measured check (b) != OK arrived after the incumbent was set (gate_hard);
  - prefix-only commit: LA-n (last n votes agree) or >= 3 votes with agreement share >= gamma (gamma 0.67 = 2/3
    exactly, share_at_least, canon §74); flip_score > FLIP_TH stops new commits (FLIP_TH off until E0.5 sets it);
  - ordinal agreement within tau bins, tau = 0 near contact (E §4.12 C5 setting "tau=1(접촉 근처 0)", M4 §4.4):
    the caller passes near (core.near_contact: target <= 5 cm or contact, canon §7) to on_vote and try_commit_prefix;
  - (b) outcome per executed step: DEVIATE -> epoch+1, future uncommitted slots reopened, early call;
    CONTRADICT -> same + hold (keep last committed action, slow down; never a stop -- M7 owns FAIL);
    LAG -> choices kept (retiming is left to the executor).
The C2 baseline (agree "stream", Slow Brain VLM Stream, M4 §5 :332, canon §74) bypasses the slots: the newest valid
answer by request time is the decision until a newer one arrives or it is older than 5 s (stale_max of C2).
Not implemented (logged as open items): C3' Beta stop rule, cumulative-expected-state agreement (agree_mode),
align_tol, CUSUM; M4 design extensions outside the pre-registered flat C5 setting (E §4.12 W=1, gamma=0.67; canon
§73 SCOPED, ablation candidates): boundary-adaptive W 2 / gamma 1.0 right after the frozen boundary (M4 §3 #5, §4.2
W(zone_dist) / gamma(zone_dist), §4.4 W and W_irrev), queue-threshold early call g 0.5 and scene-change early call
(§4.3, §3 #11), a one-step stricter (b) threshold for unconfirmed-executed steps (§4.2). The J5 conformal gate
is applied before this ledger in core.py (R6, canon §31; only with a calibration file and j5_alpha); the theta gate is only judged offline (calibration.py, E1 judgment 1), not applied
at runtime (canon §6: gates off before E1).
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from fractions import Fraction

MAG_ORDER = ("tiny", "small", "medium", "large", "xlarge")
# E §4.12 :487 / §2A.3 :240 "γ=0.67", M4 §4.4 :276 "0.67 (3표 중 2)", §3 #2 :147 "3표면 2표 = 0.67": the pre-registered
# 0.67 is exactly 2/3 (canon §74). Kept as the string "2/3" so the logged M4 parameters stay JSON.
GAMMA = "2/3"


# Time comparisons (canon §75, R7 cycle 10 N1): an age that equals a limit in exact tick arithmetic (e.g. 1.50 s or
# 5.00 s between two 100 Hz tick times) must land on the same side at every tick position; float subtraction of tick
# times is off by ~1e-14. 1e-9 s is the tolerance the ledger already uses for its slot-start boundaries (far below one
# 10 ms tick).
T_EPS = 1e-9


def older_than(age: float, limit: float) -> bool:
    """age > limit (boundary excluded: an age of exactly limit is kept), with the T_EPS time tolerance."""
    return age > limit + T_EPS


def early_ask_steps(t_send: float, d_hat: float, T_c: float, lead_max: float) -> list[int]:
    """H = 1 (canon §2 :18, M4 §4.1 :188 "호출 시각을 스텝 시작보다 앞당겨 같은 스텝을 2~3회 묻기"): every step is asked
    from lead_max before its start until d_hat before it, every T_c (E §2.6 :183, the schedule analysis.latency.
    votes_per_step counts offline). So the call sent at t_send is an ask of every step k with
    t_send + d_hat <= t_start(k) = k T_c <= t_send + lead_max (both ends included); when no step lies in that window
    (lead_max < d_hat + gap to the grid), the first step after d_hat (the M3 original "one call = one step")."""
    k0 = int(math.ceil((t_send + d_hat) / T_c - 1e-9))
    k1 = int(math.floor((t_send + lead_max) / T_c + 1e-9))
    return list(range(k0, max(k0, k1) + 1))


def share_at_least(n_agree: int, n_votes: int, gamma=GAMMA) -> bool:
    """n_agree / n_votes >= gamma, exact (integer cross-multiplication, no epsilon). gamma: anything Fraction() takes
    ("2/3", 1.0, Fraction); a decimal float is taken at its exact value (0.67 > 2/3). The one agreement-share rule of
    the runtime ledger and the E0.5 replay (canon §74)."""
    g = Fraction(gamma)
    return n_agree * g.denominator >= g.numerator * n_votes


@dataclass(frozen=True)
class M4Params:
    T_c: float = 0.33
    H: int = 3
    W: int = 1
    gamma: str | float = GAMMA  # 0.67 = 2/3 exactly (canon §74)
    n_la: int = 2
    tau: int = 1  # ordinal tolerance (bins) for ordinal questions
    stale_max: float = 1.5  # C5 STALE_MAX (E §4.12); agree "stream" (C2): the 5 s VLM Stream timeout instead
    flip_th: float | None = None  # off until E0.5 (M4 §4.4 FLIP_TH)
    flip_win: int = 4
    d_p95_init: float = 0.307  # stageA_sft.md (c): merged BF16 text+image N=4 p95
    d_window: int = 50
    ordinal: tuple = (("mag_coarse", MAG_ORDER),)
    # R6 comparison conditions (conditions.py, M4 §5): agree = consensus (a) | newest (C0/C1/C4: per slot, the vote
    # with the newest request time wins, no commit) | stream (C2 = Slow Brain VLM Stream, M4 §5 :332, canon §74: no
    # slots -- the newest valid answer by request time is the decision of every tick until one newer arrives or it is
    # older than stale_max = 5 s); feedback_b = the (b) epoch / reopen / hold signals; max_inflight caps N_max;
    # n_max_cap False = no in-flight cap at all (C2: "in-flight 상한 없음", the runtime reports the measured count)
    agree: str = "consensus"
    feedback_b: bool = True
    max_inflight: int | None = None
    n_max_cap: bool = True
    # H = 1 early re-asking (canon §2 :18, M4 §4.1 :188-189, E §2.6 :183 / §2.7-4 :197, canon §75): a step is asked
    # from lead_max before its start until d_hat before it, every T_c. Pre-registered candidates {1.0, 1.5} s, set
    # after E0; 1.0 = M4 §4.1 "2~3회" and the E0.5 replay's 3 asks (E §2A.3) at d_p95 0.307. Unused when H > 1.
    lead_max: float = 1.0

    def __post_init__(self):
        if self.W < 0:
            raise ValueError(f"M4 W = {self.W}: the defer window is a vote count >= 0 (canon §72)")
        if not self.lead_max > 0:
            raise ValueError(f"M4 lead_max = {self.lead_max}: the H = 1 early-ask window must be > 0 s (canon §75)")


@dataclass
class Vote:
    ds: int
    question: str
    choice: str  # option_key
    p_chosen: float | None
    call_id: str
    t_send: float
    t_recv: float
    t_state: float
    premise_epoch: int
    qid: str = ""
    perm_id: int = 0
    display_map: dict | None = None


@dataclass
class Slot:
    ds: int
    question: str
    t_start: float
    status: str = "OPEN"
    incumbent: str | None = None
    challenger: str | None = None
    defer_left: int = 0
    t_incumbent: float = -1.0
    votes: list = field(default_factory=list)
    outcome: str = "-"
    t_state_inc: float = -1e9


class CommitLedger:
    def __init__(self, params: M4Params = M4Params(), questions=("dir_xy", "dir_z", "mag_coarse", "target", "phase")):
        self.p = params
        self.questions = tuple(questions)
        self.slots: dict[tuple, Slot] = {}
        self.epoch = 0
        self.last_bad_t: float | None = None
        self.lat = deque(maxlen=params.d_window)
        self.flip_score = {q: 0.0 for q in self.questions}
        self._recent = {q: deque(maxlen=2 * params.flip_win) for q in self.questions}
        self._ord = {q: list(o) for q, o in params.ordinal}
        self.log: list[dict] = []  # epoch changes, commits, (b) outcomes
        self.counts = {"votes": 0, "dropped_epoch": 0, "dropped_stale": 0, "log_only": 0, "replaced": 0,
                       "commits": 0}
        self._exec = {q: {"executed": 0, "committed": 0, "unconfirmed": 0, "empty": 0} for q in self.questions}
        self._stream: dict[str, Vote] = {}  # agree "stream" (C2): newest valid answer per question

    # ------------------------------------------------------------------ time / latency
    def t_start(self, ds: int) -> float:
        return ds * self.p.T_c

    @property
    def d_hat(self) -> float:
        if not self.lat:
            return self.p.d_p95_init
        xs = sorted(self.lat)
        return xs[min(len(xs) - 1, int(math.ceil(0.95 * len(xs))) - 1)]

    def record_latency(self, s: float) -> None:
        self.lat.append(float(s))

    def n_max(self) -> int | float:
        if not self.p.n_max_cap:  # C2 VLM Stream: no in-flight cap (M4 §5 :332)
            return math.inf
        n = int(math.ceil(self.d_hat / self.p.T_c - 1e-9)) + 1
        return n if self.p.max_inflight is None else min(n, int(self.p.max_inflight))

    def target_slots(self, t_send: float) -> list[int]:
        """Slots the call sent at t_send votes for. H > 1: the H steps from the first one starting at or after
        t_send + d_hat (M4 §4.1). H = 1: early_ask_steps (the same step asked early, canon §2, canon §75)."""
        if self.p.H == 1:
            return early_ask_steps(t_send, self.d_hat, self.p.T_c, self.p.lead_max)
        k = int(math.ceil((t_send + self.d_hat) / self.p.T_c - 1e-9))
        return list(range(k, k + self.p.H))

    # ------------------------------------------------------------------ slots
    def slot(self, q: str, ds: int) -> Slot:
        key = (q, ds)
        if key not in self.slots:
            self.slots[key] = Slot(ds=ds, question=q, t_start=self.t_start(ds))
        return self.slots[key]

    def _agrees(self, q: str, a: str | None, b: str | None, near: bool = False) -> bool:
        if a is None or b is None:
            return False
        if a == b:
            return True
        order = self._ord.get(q)
        tau = 0 if near else self.p.tau
        if order and a in order and b in order:
            return abs(order.index(a) - order.index(b)) <= tau
        return False

    def on_vote(self, v: Vote, now: float, irreversible=None, near: bool = False) -> str:
        """Returns what happened to the vote (logged by the caller). irreversible(question, choice) -> bool (M6
        effect field); near: slot is in the near/contact zone (tau 0)."""
        self.counts["votes"] += 1
        if v.premise_epoch < self.epoch:
            self.counts["dropped_epoch"] += 1
            return "dropped_epoch"
        if older_than(now - v.t_state, self.p.stale_max):
            self.counts["dropped_stale"] += 1
            return "dropped_stale"
        if self.p.agree == "stream":  # C2 VLM Stream: no slots, no FROZEN log-only; newest by request time
            self._update_flip(v)
            cur = self._stream.get(v.question)
            if cur is None or v.t_state >= cur.t_state:
                self._stream[v.question] = v
                return "newest"
            return "older"
        s = self.slot(v.question, v.ds)
        if s.t_start <= now + 1e-9 or s.status == "COMMITTED":
            self.counts["log_only"] += 1
            return "log_only"
        self._update_flip(v)
        s.votes.append(v)
        if self.p.agree == "newest":  # C0 / C1 / C4: newest valid vote of the slot by request time, no agreement
            if v.t_state >= s.t_state_inc:
                s.incumbent, s.status, s.t_incumbent, s.t_state_inc = v.choice, "TENTATIVE", now, v.t_state
                return "newest"
            return "older"
        if s.status == "OPEN":
            s.incumbent, s.status, s.t_incumbent = v.choice, "TENTATIVE", now
            return "tentative"
        if self._agrees(v.question, v.choice, s.incumbent, near):
            return "agree"
        irr = bool(irreversible and (irreversible(v.question, v.choice) or irreversible(v.question, s.incumbent)))
        if self.last_bad_t is not None and self.last_bad_t > s.t_incumbent:
            return self._replace(s, v.choice, now)
        if s.challenger == v.choice:
            s.defer_left -= 1
            if s.defer_left <= 0:
                return self._replace(s, v.choice, now)
            return "defer"
        w = self.p.W + (1 if irr else 0)
        if w <= 0:  # W = 0: no defer window, the first challenging vote replaces (canon §72)
            return self._replace(s, v.choice, now)
        s.challenger, s.defer_left, s.status = v.choice, w, "CONTESTED"
        return "challenger"

    def _replace(self, s: Slot, choice: str, now: float) -> str:
        s.incumbent, s.challenger, s.defer_left, s.status, s.t_incumbent = choice, None, 0, "TENTATIVE", now
        self.counts["replaced"] += 1
        return "replaced"

    def _update_flip(self, v: Vote) -> None:
        r = self._recent[v.question]
        r.append(v.choice)
        w = self.p.flip_win
        if len(r) < 2 * w:
            return
        a, b = list(r)[:w], list(r)[w:]
        keys = set(a) | set(b)
        self.flip_score[v.question] = 0.5 * sum(abs(a.count(k) / w - b.count(k) / w) for k in keys)

    def try_commit_prefix(self, q: str, now: float, near: bool = False) -> list[int]:
        """Commit future slots of question q from the front only (#1); returns the newly committed ds. near: the
        near/contact zone (ordinal tau 0 in the agreement count, E §4.12 C5 setting)."""
        out = []
        if self.p.agree in ("newest", "stream"):
            return out
        if self.p.flip_th is not None and self.flip_score[q] > self.p.flip_th:
            return out
        for (qq, ds), s in sorted(self.slots.items(), key=lambda kv: kv[0][1]):
            if qq != q or s.t_start <= now + 1e-9 or s.status == "COMMITTED":
                continue
            if s.incumbent is None:
                break
            live = [x for x in s.votes if self._agrees(q, x.choice, s.incumbent, near)]
            tail = s.votes[-self.p.n_la:]
            la = len(tail) >= self.p.n_la and all(self._agrees(q, x.choice, s.incumbent, near) for x in tail)
            if la or (len(s.votes) >= 3 and share_at_least(len(live), len(s.votes), self.p.gamma)):
                s.status = "COMMITTED"
                self.counts["commits"] += 1
                out.append(ds)
            else:
                break
        return out

    def decision(self, q: str, ds: int, now: float | None = None):
        """(choice, status) the executor uses for step ds: committed choice, else the tentative incumbent
        (executed unconfirmed, §4.2), else (None, EMPTY). agree "stream" (C2): the newest valid answer whatever its
        target step, (None, EMPTY) once it is older than stale_max (5 s timeout -> default action) at time now."""
        if self.p.agree == "stream":
            v = self._stream.get(q)
            if v is None or (now is not None and older_than(now - v.t_state, self.p.stale_max)):
                return None, "EMPTY"
            return v.choice, "TENTATIVE"
        s = self.slots.get((q, ds))
        if s is None or s.incumbent is None:
            return None, "EMPTY"
        return s.incumbent, s.status if s.status == "COMMITTED" else "TENTATIVE"

    def mark_executed(self, ds: int, now: float) -> dict:
        out = {}
        for q in self.questions:
            c, st = self.decision(q, ds, now)
            e = self._exec[q]
            e["executed"] += 1
            key = {"COMMITTED": "committed", "TENTATIVE": "unconfirmed", "EMPTY": "empty"}[st]
            e[key] += 1
            out[q] = (c, st)
        return out

    # ------------------------------------------------------------------ (b) and epochs
    def bump_epoch(self, reason: str, now: float) -> int:
        self.epoch += 1
        self.log.append({"t": now, "event": "epoch", "epoch": self.epoch, "reason": reason})
        return self.epoch

    def _reopen_future(self, now: float) -> int:
        n = 0
        for s in self.slots.values():
            if s.t_start > now + 1e-9 and s.status != "COMMITTED":
                s.votes, s.incumbent, s.challenger, s.defer_left, s.status = [], None, None, 0, "OPEN"
                s.t_state_inc = -1e9
                n += 1
        return n

    def on_step_executed(self, ds: int, outcome: str, now: float) -> dict:
        """(b) result of step ds: OK / LAG / DEVIATE / CONTRADICT. Returns the signals for the caller:
        {epoch, early_call, hold, reopened}. Emitting to M7 is the caller's (M4 only signals, canon §4)."""
        if outcome not in ("OK", "LAG", "DEVIATE", "CONTRADICT"):
            raise ValueError(outcome)
        for q in self.questions:
            s = self.slots.get((q, ds))
            if s is not None:
                s.outcome = outcome
        res = {"epoch": self.epoch, "early_call": False, "hold": False, "reopened": 0}
        if not self.p.feedback_b:  # C2 / C3: outcome logged only
            return res
        if outcome != "OK":
            self.last_bad_t = now
        if outcome in ("DEVIATE", "CONTRADICT"):
            res["epoch"] = self.bump_epoch(f"b_{outcome.lower()}_ds{ds}", now)
            res["reopened"] = self._reopen_future(now)
            res["early_call"] = True
            res["hold"] = outcome == "CONTRADICT"
        return res

    def stats(self) -> dict:
        ex = {q: e["executed"] for q, e in self._exec.items()}
        return {"executed": ex,
                "committed_executed": {q: e["committed"] for q, e in self._exec.items()},
                "unconfirmed_executed": {q: e["unconfirmed"] for q, e in self._exec.items()},
                "empty_executed": {q: e["empty"] for q, e in self._exec.items()},
                "commit_ratio": {q: (e["committed"] / e["executed"] if e["executed"] else None)
                                 for q, e in self._exec.items()},
                "epoch": self.epoch, "d_hat": self.d_hat, "counts": dict(self.counts),
                "flip_score": dict(self.flip_score)}
