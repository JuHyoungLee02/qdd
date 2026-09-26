from harvest.couple.recovery_cache import FailSig
from harvest.runtime.core import OursRuntime, RuntimeConfig
from harvest.runtime.models import MockSelector

from .fakeworld import FakeWorld

SIG = FailSig("S1", "o3", "grasp_miss", "t1_skill")
REC = {"lever": "dp.approach_dir", "value": "side_front"}
FALS = [{"pred": "holding_t", "value": True}]


def test_runtime_fail_event_reuses_without_calling_astra():
    rt = OursRuntime(RuntimeConfig(clock="simlat"), MockSelector())
    rt.reset()
    w = FakeWorld()
    rt.act(w.obs())
    rt.recovery.remember(SIG, REC, FALS, "x", "j2:test", 0.0)
    before = rt.hb.next_t
    rt._fail_event(0.5, "grasp_miss", "t1_skill")
    ev = [e for e in rt.events if e["event"] in ("fail_path", "recovery_reuse")]
    assert [e["event"] for e in ev] == ["fail_path", "recovery_reuse"] and ev[1]["applied"] == "m9_not_built"
    assert rt.hb.next_t == before  # no Astra call pulled forward
    rt._fail_event(0.6, "grasp_miss", "t1_skill")
    assert rt.events[-1]["decision"] == "call_j2" and rt.events[-1]["why"] == "reuse_cap"
    rt.close()
