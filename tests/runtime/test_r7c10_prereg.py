"""R7 cycle 10 (canon §75): D1 H = 1 early re-asking (canon §2 :18 "H=1일 때 M4 (a)의 여러 표는 '같은 스텝을 시각을
당겨 여러 번 묻기'로 얻는다", M4 §4.1 :188-189, §4.4 :273, E §2.6 :183 / §2.7-4 :197 lead_max, E §2A.3 :236 replay);
N1 age comparisons at exact boundaries; behavioural checks of conformance rows that were only "parameter passed"."""
import statistics
from dataclasses import asdict

import pytest

from harvest.runtime.conditions import condition
from harvest.runtime.core import OursRuntime, RuntimeConfig
from harvest.runtime.m4 import CommitLedger, M4Params, Vote
from harvest.runtime.models import MockSelector

from .fakeworld import FakeWorld

T_C = 0.33


def _v(ds, choice, t_state, call="c", q="dir_xy"):
    return Vote(ds=ds, question=q, choice=choice, p_chosen=None, call_id=call, t_send=t_state, t_recv=t_state + 0.3,
                t_state=t_state, premise_epoch=0)


# ------------------------------------------------------------------------------------------ D1 ledger: lead window
def test_h1_call_asks_every_step_of_its_lead_window():
    """E §2.6 :183: a step is asked from lead_max before its start until d_p95 before it, every T_c. So the H = 1 call
    sent at t is an ask of every step whose start lies in [t + d_hat, t + lead_max]."""
    L = CommitLedger(M4Params(H=1))  # d_hat = d_p95_init 0.307, lead_max default 1.0
    assert L.p.lead_max == 1.0
    assert L.target_slots(0.0) == [1, 2, 3]  # offsets 0.33, 0.66, 0.99
    assert L.target_slots(0.1) == [2, 3]  # offsets 0.56, 0.89 (0.23 < d_hat, 1.22 > lead_max)
    assert CommitLedger(M4Params(H=1, lead_max=1.5)).target_slots(0.0) == [1, 2, 3, 4]
    assert CommitLedger(M4Params(H=1, lead_max=0.99)).target_slots(0.0) == [1, 2, 3]  # boundary included
    # no step inside the window (lead_max < d_hat): the first step after d_hat (the M3 original H = 1)
    assert CommitLedger(M4Params(H=1, lead_max=0.2)).target_slots(0.0) == [1]


@pytest.mark.parametrize("bad", [float("inf"), float("nan"), 0.0, -1.0])
def test_lead_max_must_be_finite_and_positive(bad):
    """R7 cycle 11 N4: lead_max = inf passed validation and crashed on the first call (OverflowError)."""
    with pytest.raises(ValueError):
        M4Params(H=1, lead_max=bad)


def test_h3_target_slots_ignore_lead_max():
    for lead in (0.2, 1.0, 1.5, 3.0):
        L = CommitLedger(M4Params(H=3, lead_max=lead))
        assert L.target_slots(0.0) == [1, 2, 3] and L.target_slots(0.1) == [2, 3, 4]


def test_lead_max_must_be_positive():
    with pytest.raises(ValueError):
        M4Params(H=1, lead_max=0.0)


# ------------------------------------------------------------------------------------------ D1 closed loop behaviour
def _run(cond, H, lat=0.30, ticks=2000, lead_max=None):
    m4o, rto = condition(cond)
    m4 = {**asdict(M4Params()), **m4o, "H": H}
    if lead_max is not None:
        m4["lead_max"] = lead_max
    cfg = RuntimeConfig(backend="modular", clock="simlat", astra_mode="none", condition=cond, m4=m4, **rto)
    rt = OursRuntime(cfg, MockSelector(latency_s=lat))
    rt.reset()
    w = FakeWorld()
    for _ in range(ticks):
        a, _ = rt.act(w.obs())
        w.step(a)
    rt.close()
    return rt


@pytest.mark.parametrize("cond", ["C5", "C3"])
def test_h1_gives_two_or_more_votes_per_step_and_commits(cond):
    """Reviewer h1_check.py (6522fda): H = 1 -> votes per step {1: 60}, commits 0. The pre-registered H = 1 gets its
    several votes by asking the same step early (median >= 2 votes per step, E §2.7-4), so (a) can commit."""
    rt = _run(cond, 1)
    nv = [len(s.votes) for (q, ds), s in rt.ledger.slots.items() if q == "dir_xy" and ds <= rt.cur_k]
    assert statistics.median(nv) >= 2, sorted(nv)
    st = rt.ledger.stats()
    assert rt.ledger.counts["commits"] > 0 and st["committed_executed"]["dir_xy"] > 0
    assert all(len(c["slots"]) >= 2 for c in rt.calls[5:])  # every call is an early ask of 2-3 steps


# ------------------------------------------------------------------------------------------ D1 replay agreement
def test_runtime_h1_asks_match_e05_replay_and_e0_count_on_a_grid_schedule():
    """Constructed schedule: calls every T_c on the step grid, latency = d_p95 = 0.307. The runtime's H = 1 votes of
    step k come from the same request times as the E0.5 replay's (E §2A.3: the 3 newest snapshots with
    t <= t_k - d_p95), and their number is the E0 offline count (analysis.latency.votes_per_step)."""
    from harvest.analysis.latency import votes_per_step
    from harvest.eval.e05 import vote_steps
    d = 0.307
    L = CommitLedger(M4Params(H=1, d_p95_init=d), questions=("dir_xy",))
    n = 40
    t_of = {j: round(j * T_C, 6) for j in range(n)}
    for j in range(n):
        for ds in L.target_slots(t_of[j]):
            L.on_vote(_v(ds, "plus_x", t_of[j], f"c{j}"), now=round(t_of[j] + d, 6))
    replay = dict(vote_steps(t_of, d))
    for k in range(5, n - 5):
        rt_off = sorted((round(v.t_state - L.t_start(k), 6) for v in L.slots[("dir_xy", k)].votes), reverse=True)
        rp_off = [off for _, off in replay[k]]
        assert rt_off == pytest.approx(rp_off, abs=1e-6), (k, rt_off, rp_off)
        assert len(rt_off) == votes_per_step(d, T_c=T_C, lead_max=L.p.lead_max) == 3


# ------------------------------------------------------------------------------------------ D1 CLI and meta
def test_closed_lead_max_argument_and_config():
    from harvest.eval import closed
    assert closed._args(["--model", "m", "--out", "o"]).m4_lead_max == 1.0
    assert closed._args(["--model", "m", "--out", "o", "--m4-lead-max", "1.5"]).m4_lead_max == 1.5
    assert closed.m4_config("C5", 3) == asdict(M4Params())  # default unchanged
    assert closed.m4_config("C5", 1, 1.5)["lead_max"] == 1.5 and closed.m4_config("C5", 1, 1.5)["H"] == 1
    with pytest.raises(ValueError):
        closed.m4_config("C5", 1, 0.0)


# ------------------------------------------------------------------------------------------ N1 exact age boundaries
def _ticks(n=6000):
    return [round(i * 0.01, 6) for i in range(n)]


def test_stale_max_boundary_is_tick_position_independent():
    """An age of exactly 1.50 s (C5) or 5.00 s (C2) is kept at every tick position; one tick more drops it."""
    for stale, extra in ((1.5, {}), (5.0, {"agree": "stream", "stale_max": 5.0, "n_max_cap": False})):
        bad = []
        for t in _ticks():
            L = CommitLedger(M4Params(**extra), questions=("dir_xy",))
            now = round(t + stale, 6)
            ds = int(now / T_C) + 5
            r = L.on_vote(_v(ds, "plus_x", t), now=now)
            late = L.on_vote(_v(ds, "plus_x", t, "c2"), now=round(now + 0.01, 6))
            if r == "dropped_stale" or late != "dropped_stale":
                bad.append(t)
        assert not bad, (stale, len(bad), bad[:5])


def test_c2_timeout_boundary_is_tick_position_independent():
    """C2 decision(): the last valid answer at exactly 5.00 s is still applied; at 5.01 s -> default action."""
    bad = []
    for t in _ticks():
        L = CommitLedger(M4Params(agree="stream", stale_max=5.0, n_max_cap=False), questions=("dir_xy",))
        L.on_vote(_v(1, "plus_x", t), now=round(t + 0.3, 6))
        if L.decision("dir_xy", 0, now=round(t + 5.0, 6))[1] == "EMPTY" or \
                L.decision("dir_xy", 0, now=round(t + 5.01, 6))[1] != "EMPTY":
            bad.append(t)
    assert not bad, (len(bad), bad[:5])


# ------------------------------------------------------------------------------------------ behavioural rows (task 6)
def test_early_call_pulls_a_periodic_slot_forward_budget_unchanged():
    """M4 §4.3 :262 "early_call은 주기 슬롯 하나를 당겨 쓴다 (초당 호출 예산 고정)": an early call at an off-grid tick
    is sent at once and the next periodic call is skipped, so the calls per second stay the same."""
    def run(early_at):
        cfg = RuntimeConfig(backend="modular", clock="simlat", astra_mode="none")
        rt = OursRuntime(cfg, MockSelector(latency_s=0.30))
        rt.reset()
        w = FakeWorld()
        sends = []
        for i in range(600):
            if i == early_at:
                rt.early = True
            n0 = rt.n_calls
            a, _ = rt.act(w.obs())
            if rt.n_calls > n0:
                sends.append(i)
            w.step(a)
        rt.close()
        return sends
    base, pulled = run(None), run(350)
    assert 350 in pulled and 350 not in base
    assert len(pulled) == len(base)  # same budget over the run
    nxt = min(i for i in base if i > 350)
    assert nxt not in pulled  # the periodic slot after the early call was used by it


def test_flip_gate_off_before_e05_does_not_block_commits():
    """Canon §6 / M4 §4.4 FLIP_TH off until E0.5 (flip_th None): a high flip_score does not stop commits; with a
    threshold it does."""
    def feed(flip_th):
        L = CommitLedger(M4Params(flip_th=flip_th), questions=("dir_xy",))
        L.on_vote(_v(40, "plus_y", 0.1, "a"), now=0.5)  # two agreeing votes: LA-2 would commit slot 40
        L.on_vote(_v(40, "plus_y", 0.2, "b"), now=0.6)
        for i, c in enumerate(["plus_x"] * 4 + ["minus_x"] * 4):  # then the last 4 votes vs the 4 before: TV 1.0
            L.on_vote(_v(90 + i, c, 0.3 + 0.1 * i, f"f{i}"), now=1.2)
        assert L.flip_score["dir_xy"] == 1.0
        return L.try_commit_prefix("dir_xy", now=1.5)
    assert 40 in feed(None)
    assert feed(0.5) == []


@pytest.mark.parametrize("cond,n", [("C0", 1), ("C1", 1), ("C6", 1), ("C5", 2)])
def test_inflight_counts_follow_the_condition_table(cond, n):
    """M4 §5 :329-346: C0/C1/C6 one call in flight; C5 overlaps (0.6 s latency, a call every 0.33 s -> 2 in flight)
    within N_max = ceil(d_hat / T_c) + 1 = 3."""
    rt = _run(cond, 3, lat=0.6, ticks=1200)
    s = rt.summary()
    assert s["dec_inflight"]["max"] == n <= rt.ledger.n_max()
    if cond == "C0":
        assert s["stop_ticks"] > 0  # the arm waits while the answer is out
