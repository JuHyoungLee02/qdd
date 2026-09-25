"""R7 cycle 9 (canon §74): D1 gamma "3표 중 2" = exactly 2/3 (E §4.12 :487, M4 §4.4 :276, §3 #2 :147), shared with the
E0.5 replay; D2 C2 = Slow Brain VLM Stream as pre-registered (E §4.12 D9 :495, canon §20 :179, M4 §5 :332): no
in-flight cap, the newest valid answer by request time applied every tick, 5 s timeout -> default action."""
import math
from dataclasses import asdict

from harvest.runtime.conditions import condition
from harvest.runtime.core import OursRuntime, RuntimeConfig
from harvest.runtime.m4 import CommitLedger, M4Params, Vote
from harvest.runtime.models import MockSelector

from .fakeworld import FakeWorld


def _v(ds, choice, t_state, call="c", q="dir_xy"):
    return Vote(ds=ds, question=q, choice=choice, p_chosen=None, call_id=call, t_send=t_state, t_recv=t_state + 0.3,
                t_state=t_state, premise_epoch=0)


def _votes(L, choices, ds=30):
    for i, c in enumerate(choices):
        L.on_vote(_v(ds, c, 0.1 * i, f"c{i}"), now=0.4 + 0.1 * i)
    return L.try_commit_prefix("dir_xy", now=0.4 + 0.1 * len(choices))


# ------------------------------------------------------------------------------------------ D1 gamma = 2/3 exactly
def test_share_at_least_is_exact():
    from harvest.runtime.m4 import GAMMA, share_at_least
    assert share_at_least(2, 3, GAMMA) and not share_at_least(2, 4, GAMMA)
    assert share_at_least(4, 6, GAMMA) and not share_at_least(1332, 2000, GAMMA)  # 0.666 < 2/3 (no epsilon)
    assert share_at_least(3, 3, 1.0) and not share_at_least(2, 3, 1.0)
    assert not share_at_least(2, 3, 0.67)  # an explicit decimal 0.67 is taken literally (canon §74)


def test_runtime_two_of_three_commits_at_default_gamma():
    """Reviewer gamma_check.py: votes a, b, a (LA-2 fails) -> the gamma rule commits a (was CONTESTED)."""
    L = CommitLedger(M4Params(), questions=("dir_xy",))
    assert _votes(L, ["plus_x", "plus_y", "plus_x"]) == [30]
    assert L.decision("dir_xy", 30) == ("plus_x", "COMMITTED")
    L9 = CommitLedger(M4Params(n_la=9), questions=("dir_xy",))  # gamma alone
    assert _votes(L9, ["plus_x", "plus_y", "plus_x"]) == [30]


def test_runtime_two_of_four_does_not_commit():
    L = CommitLedger(M4Params(n_la=9), questions=("dir_xy",))
    assert _votes(L, ["plus_x", "plus_y", "minus_x", "plus_x"]) == []
    assert L.slot("dir_xy", 30).status != "COMMITTED"


def test_gamma_one_is_unanimity():
    L = CommitLedger(M4Params(n_la=9, gamma=1.0), questions=("dir_xy",))
    assert _votes(L, ["plus_x", "plus_y", "plus_x"]) == []
    L2 = CommitLedger(M4Params(n_la=9, gamma=1.0), questions=("dir_xy",))
    assert _votes(L2, ["plus_x", "plus_x", "plus_x"]) == [30]


def test_replay_uses_the_same_rule():
    from harvest.analysis import replay
    from harvest.eval import e05
    from harvest.runtime import m4
    assert replay.share_at_least is m4.share_at_least and e05.share_at_least is m4.share_at_least
    v = [{"t_req": -0.3, "key": "a"}, {"t_req": -0.6, "key": "b"}, {"t_req": -0.9, "key": "a"}]
    assert replay.la2(v) == "a" and e05.apply_rules(v)["la2_confirmed"] is True
    w = [{"t_req": -0.1 * i, "key": k} for i, k in enumerate("abca")]
    assert e05.apply_rules(w)["la2_confirmed"] is False
    big = [{"t_req": -i, "key": "a" if i < 1332 else "b"} for i in range(2000)]  # 0.666: exact rule refuses
    assert e05.apply_rules(big)["la2_confirmed"] is False


# ------------------------------------------------------------------------------------------ D2 C2 = VLM Stream
_A9B = {"C0": ({"max_inflight": 1, "agree": "newest", "feedback_b": False}, {"stop_wait": True}),
        "C1": ({"max_inflight": 1, "agree": "newest", "feedback_b": False}, {}),
        "C3": ({"feedback_b": False}, {}), "C4": ({"agree": "newest"}, {}), "C5": ({}, {}),
        "C6": ({"max_inflight": 1}, {})}


def test_only_c2_changes():
    for c, v in _A9B.items():
        assert condition(c) == v
    m4, rt = condition("C2")
    assert rt == {} and m4["agree"] == "stream" and m4["feedback_b"] is False and m4["stale_max"] == 5.0
    assert m4["n_max_cap"] is False


def _c2():
    return CommitLedger(M4Params(**{**asdict(M4Params()), **condition("C2")[0]}), questions=("dir_xy",))


def test_c2_no_inflight_cap():
    L = _c2()
    L.record_latency(2.0)
    assert L.n_max() == math.inf
    assert CommitLedger(M4Params()).n_max() == 2  # C5 keeps N_max = ceil(d/T_c) + 1


def test_c2_keeps_answers_up_to_5s_and_times_out_after():
    L = _c2()
    assert L.on_vote(_v(3, "plus_x", 0.0), now=2.0) == "newest"  # 2 s old: kept (STALE_MAX 1.5 s is C5's)
    assert L.decision("dir_xy", 7, now=4.9) == ("plus_x", "TENTATIVE")
    assert L.decision("dir_xy", 7, now=5.01) == (None, "EMPTY")  # last valid answer older than 5 s -> default
    assert L.on_vote(_v(20, "plus_y", 0.0), now=5.2) == "dropped_stale"


def test_c2_late_answer_applied_not_log_only():
    """A late answer whose target slot already started is still the newest valid answer by request time."""
    L = _c2()
    L.on_vote(_v(2, "plus_x", 0.0), now=0.3)
    assert L.on_vote(_v(1, "minus_x", 0.1), now=1.5) == "newest"  # slot 1 started at 0.33
    assert L.decision("dir_xy", 4, now=1.5) == ("minus_x", "TENTATIVE")
    assert L.on_vote(_v(9, "plus_y", 0.05), now=1.6) == "older"  # older request time: not applied
    assert L.decision("dir_xy", 4, now=1.6) == ("minus_x", "TENTATIVE")
    assert L.try_commit_prefix("dir_xy", now=1.6) == [] and L.counts["log_only"] == 0


def _run(cond, lat, ticks=3000, check_every_tick=False):
    m4o, rto = condition(cond)
    cfg = RuntimeConfig(backend="modular", clock="simlat", astra_mode="none", condition=cond,
                        m4={**asdict(M4Params()), **m4o}, **rto)
    rt = OursRuntime(cfg, MockSelector(latency_s=lat))
    rt.reset()
    w = FakeWorld()
    mism = 0
    for _ in range(ticks):
        a, _ = rt.act(w.obs())
        if check_every_tick and rt.cur_k is not None:
            want = {q: c for q in ("dir_xy", "dir_z", "mag_coarse", "target", "phase")
                    if (c := rt.ledger.decision(q, rt.cur_k, now=rt.t_last)[0]) is not None}
            mism += int(want != rt.skill.dec)
        w.step(a)
    s = rt.summary()
    rt.close()
    return rt, s, mism


def test_c2_at_2s_latency_applies_answers():
    """Reviewer c2_stale.py: at a fixed 2.0 s latency (an E-M4-lat point) C2 dropped 1,230/1,230 votes."""
    rt, s, _ = _run("C2", 2.0)
    assert rt.ledger.counts["dropped_stale"] == 0 and rt.ledger.counts["log_only"] == 0
    assert sum(s["m4"]["unconfirmed_executed"].values()) > 0
    assert s["dec_inflight"]["max"] >= 6  # ~2.0 / 0.33 calls in flight, no N_max cap; measured and reported


def test_c2_newest_answer_applied_every_tick():
    rt, s, mism = _run("C2", 0.45, ticks=1500, check_every_tick=True)
    assert mism == 0
    assert s["dec_inflight"]["max"] >= 2


def test_c2_mid_step_keeps_one_step_budget():
    """redecide inside a step: the new option's magnitude cap minus what the step already moved."""
    from harvest.runtime.skills import MAG_CAP, PickPlaceSkill
    sk = PickPlaceSkill()
    sk.reset(0.0, [0.3, -0.2, 1.0], [1, 0, 0, 0])
    dec = {"dir_xy": "plus_x", "dir_z": "none_z", "mag_coarse": "small", "target": "o3", "phase": "stay"}
    sk.begin_slot(5, dec)
    assert sk.moved == 0.0 and sk.cap_left == MAG_CAP["small"]
    sk.moved, sk.cap_left = 0.004, MAG_CAP["small"] - 0.004
    sk.redecide({**dec, "mag_coarse": "medium"})
    assert abs(sk.cap_left - (MAG_CAP["medium"] - 0.004)) < 1e-12 and sk.dec["mag_coarse"] == "medium"
    sk.redecide({})  # timeout: default action (no decision -> no motion)
    assert sk.dec == {} and sk.cap_left == 0.0
