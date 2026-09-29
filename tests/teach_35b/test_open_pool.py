"""open_pool.py source list after the 2026-09-29 label audit: re-verified sets only, no old AgiBot rows_live."""
import importlib.util
import os

_P = os.path.join(os.path.dirname(__file__), "..", "..", "tools", "final35", "open_pool.py")


def _mod():
    spec = importlib.util.spec_from_file_location("open_pool", _P)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_sources_are_the_audited_sets():
    s = _mod().SOURCES
    assert set(s) == {"rb2", "behavior", "rb3", "molmobot_rby1", "maniskill", "agibot_v3"}
    assert s["rb2"].endswith("/rb2_verified/records.jsonl")
    assert s["rb3"].endswith("/rb3_verified/records.jsonl")
    assert s["molmobot_rby1"].endswith("/molmobot_rby1_verified/records.jsonl")
    assert s["agibot_v3"].endswith("/agibot_v3_verified/final_all.jsonl")
    assert not any("agibot_p0" in p or "rows_live" in p for p in s.values())
