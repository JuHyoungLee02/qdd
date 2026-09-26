"""F20 (prompt_health.md): parse_decision_ex records parse_mode and never hides a parse failure behind a default
answer -- a failure returns decision "invalid" (canon §77 raw text stays in the caller's log), not "ack"."""
from harvest.runtime.astra_hb import MockAstra, OURS_CHOICES, parse_decision, parse_decision_ex
from harvest.runtime.core import OursRuntime, RuntimeConfig
from harvest.runtime.models import MockSelector

from .fakeworld import FakeWorld


def test_bare_json_mode():
    assert parse_decision_ex('{"decision": "ack", "note": "ok"}') == ("ack", "ok", "json")


def test_fenced_json_mode():
    assert parse_decision_ex('```json\n{"decision":"replace","note":"x"}\n```') == ("replace", "x", "fenced_json")


def test_regex_fallback_mode():
    assert parse_decision_ex("I think we should patch the plan") == ("patch", "", "regex_fallback")


def test_failed_mode_is_not_a_default_ack():
    dec, note, mode = parse_decision_ex("")
    assert (dec, mode) == ("invalid", "failed") and dec not in OURS_CHOICES
    dec, note, mode = parse_decision_ex("the plan looks fine, no JSON here")
    assert (dec, mode) == ("invalid", "failed")


def test_parse_decision_wraps_parse_decision_ex_unchanged():
    for text in ('{"decision": "ack", "note": "ok"}', '```json\n{"decision":"replace","note":"x"}\n```',
                "I think we should patch the plan", ""):
        assert parse_decision(text) == parse_decision_ex(text)[:2]


def test_core_records_parse_mode_on_every_heartbeat_entry():
    """core._deliver_hb wires parse_decision_ex in (not just parse_decision): every delivered heartbeat entry in
    astra_log carries parse_mode, MockAstra's bare-JSON ack is "json"."""
    cfg = RuntimeConfig(backend="modular", clock="simlat", astra_mode="mock", hb_mode="K2", hb_N_s=5.0)
    rt = OursRuntime(cfg, MockSelector(latency_s=0.30), astra=MockAstra(1.0))
    rt.reset()
    w = FakeWorld()
    for _ in range(int(20.0 * 100)):
        a, _ = rt.act(w.obs())
        w.step(a)
    rt.close()
    delivered = [a for a in rt.astra_log if a.get("kind") == "hb"]
    assert delivered and all(a.get("parse_mode") == "json" for a in delivered)
