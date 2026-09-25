"""R7 cycle 8 D4: C5 setting tau = 1 (near contact 0) (E §4.12 :487, M4 §4.4 :277, §4.6; canon §7 near/contact =
target <= 5 cm or contact predicate true; canon §73)."""
import numpy as np

from harvest.runtime.core import OursRuntime, RuntimeConfig
from harvest.runtime.m4 import CommitLedger, M4Params, Vote
from harvest.runtime.models import MockSelector

from .fakeworld import FakeWorld


def _run(near):
    L = CommitLedger(M4Params(), questions=("mag_coarse",))
    out = []
    for i, c in enumerate(["small", "tiny", "tiny"]):
        v = Vote(ds=20, question="mag_coarse", choice=c, p_chosen=None, call_id=str(i), t_send=0.1 * i,
                 t_recv=0.1 * i + 0.3, t_state=0.1 * i, premise_epoch=0)
        out.append(L.on_vote(v, now=0.4 + 0.1 * i, near=near))
        out.append(tuple(L.try_commit_prefix("mag_coarse", 0.4 + 0.1 * i, near=near)))
    return out, L.decision("mag_coarse", 20)


def test_prefix_commit_uses_tau_0_near_contact():
    """Reviewer tau_near.py: small, tiny, tiny. Far: tiny agrees with small (tau 1) -> LA-2 commits small. Near:
    tiny is a challenger, the commit must not count it as agreeing (tau 0) -> no commit at the second vote; the third
    vote passes the W = 1 window, replaces, and LA-2 then commits tiny."""
    far, dfar = _run(False)
    assert far[:4] == ["tentative", (), "agree", (20,)] and dfar == ("small", "COMMITTED")
    near, dnear = _run(True)
    assert near == ["tentative", (), "challenger", (), "replaced", (20,)] and dnear == ("tiny", "COMMITTED")


def _raw(g, o3=(0.40, -0.20, 0.05), o5=(0.45, -0.05, 0.01), contacts=()):
    return {"grip": {"pos": list(g), "w": 0.1}, "objs": {"o3": {"pos": list(o3)}, "o5": {"pos": list(o5)}},
            "contacts": [list(c) for c in contacts]}


def test_near_contact_is_the_canon_definition():
    from harvest.runtime.core import near_contact
    assert near_contact(_raw((0.40, -0.20, 0.099)), "approach") is True  # 4.9 cm from the target o3
    assert near_contact(_raw((0.40, -0.20, 0.11)), "approach") is False  # 6 cm
    assert near_contact(_raw((0.40, -0.20, 0.30), contacts=[("gripper", "o3")]), "lift") is True  # contact
    assert near_contact(_raw((0.40, -0.20, 0.06)), "carry") is False  # carry targets o5 (far)
    assert near_contact(_raw((0.45, -0.05, 0.30), contacts=[("o3", "o5")]), "place_descend") is True
    assert near_contact(_raw((0.40, -0.20, 0.30), contacts=[("o3", "table")]), "approach") is False


def test_runtime_passes_near_to_the_ledger():
    cfg = RuntimeConfig(backend="modular", clock="simlat", astra_mode="none")
    rt = OursRuntime(cfg, MockSelector(latency_s=0.30))
    rt.reset()
    seen = {"vote": set(), "commit": set()}
    ov, tc = rt.ledger.on_vote, rt.ledger.try_commit_prefix

    def on_vote(v, now, irreversible=None, near=False):
        seen["vote"].add(near)
        return ov(v, now, irreversible=irreversible, near=near)

    def try_commit(q, now, near=False):
        seen["commit"].add(near)
        return tc(q, now, near=near)
    rt.ledger.on_vote, rt.ledger.try_commit_prefix = on_vote, try_commit
    w = FakeWorld()
    for _ in range(1500):
        a, _ = rt.act(w.obs())
        w.step(a)
    rt.close()
    assert seen["vote"] == {False, True} and seen["commit"] == {False, True}
    assert np.isfinite(w.tcp).all()
