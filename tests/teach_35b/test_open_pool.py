"""open_pool.py source list (controller 09-29 after E-POOLV8 / -FIX WORSE): old verified sets + AgiBot v3 final."""
import importlib.util
import os

_P = os.path.join(os.path.dirname(__file__), "..", "..", "tools", "final35", "open_pool.py")


def _mod():
    spec = importlib.util.spec_from_file_location("open_pool", _P)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_sources_old_verified_plus_agibot_v3_final():
    s = _mod().SOURCES
    assert set(s) == {"rb2", "behavior", "rb3", "molmobot_rby1", "maniskill", "agibot_v3"}
    assert s["rb2"].endswith("/rb2/records_verified_v2.jsonl")
    assert s["rb3"].endswith("/rb3/records_verified.jsonl")
    assert s["molmobot_rby1"].endswith("/molmobot_rby1/records_verified.jsonl")
    assert s["agibot_v3"].endswith("/agibot_v3_verified/final_all.jsonl")
    assert not any("agibot_p0" in p or "_verified/records.jsonl" in p or "_fix/" in p for p in s.values())
