"""Per-call command accuracy of logged probe answers (tools/prompt_health/probe_acc.py) on synthetic episodes."""
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, *rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


PA = _load("ph_probe_acc", ("tools", "prompt_health", "probe_acc.py"))
GP = [0.5, -0.3, 1.0]


def test_score_edit_direction_and_close():
    r = PA.score_edit([5.0, 0.0, 0.0], "keep", GP, [0.4, -0.3, 1.0], [0.4, -0.3, 1.0])
    assert r["ang_arr"] == 0.0 and r["dir_ok_arr"] and r["xy_ok_arr"] and not r["premature_close"]
    r = PA.score_edit([-5.0, 0.0, 0.0], "close", GP, [0.4, -0.3, 1.0], [0.4, -0.3, 1.0])
    assert r["ang_arr"] == 180.0 and not r["dir_ok_arr"] and r["premature_close"]
    near = PA.score_edit([0.0, 0.0, -1.0], "close", GP, [0.5, -0.3, 1.01], [0.5, -0.3, 1.01])
    assert not near["premature_close"] and near["xy_ok_arr"] is None


def test_stream_uses_send_and_arrival_states():
    res = {"tcp_path": [[0.0, 0.4, -0.3, 1.0], [5.0, 0.6, -0.3, 1.0]],
           "stream": {"answers": [{"send_t": 0.0, "arr_t": 5.0, "decision": "edit", "valid": True,
                                   "effective": {"decision": "edit", "edit": {"delta_position_cm": [5.0, 0, 0],
                                                                                "gripper": "keep"}}}]}}
    rows = PA.episode_rows(res, GP)
    assert rows[0]["dir_ok_send"] and not rows[0]["dir_ok_arr"]
    s = PA.summarize(rows)
    assert s["edits"] == 1 and s["dir_ok_arr"]["k"] == 0 and s["dir_ok_send"]["k"] == 1


def test_sync_calls_and_summary_counts():
    res = {"tcp_path": [[0.0, 0.4, -0.3, 1.0]], "calls": [
        {"t_sim": 0.0, "valid": True, "parsed": {"decision": "edit", "edit": {"delta_position_cm": [3, 0, 0],
                                                                              "gripper": "keep"}}},
        {"t_sim": 0.0, "valid": True, "parsed": {"decision": "stop"}},
        {"t_sim": 0.0, "valid": False, "parsed": None}]}
    s = PA.summarize(PA.episode_rows(res, GP))
    assert s["answers"] == 3 and s["stop"] == 1 and s["invalid"] == 1 and s["dir_ok_arr"]["k"] == 1
