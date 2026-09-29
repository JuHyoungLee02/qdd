"""Prompt health check reporting helpers: report_tables (markdown from analyze JSON) and day_consistency (same prompt,
two sessions)."""
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


A = _load("ph_analyze2", ("tools", "prompt_health", "analyze.py"))
RT = _load("ph_report", ("tools", "prompt_health", "report_tables.py"))
DC = _load("ph_day", ("tools", "prompt_health", "day_consistency.py"))


def _g(snap, variant, state, truth, temp=0.0, rep=0):
    return {"test": "grasp", "model": "m", "snap": snap, "variant": variant, "temp": temp, "rep": rep, "valid": True,
            "grasp_state": state, "truth": truth, "raw": state, "prompt_sha": "s"}


def test_grasp_table_rows_and_hot_row():
    rows = [_g("a", "base", "grasped", False), _g("a", "para1", "not_grasped", False),
            _g("a", "base", "not_grasped", False, temp=0.7, rep=0)]
    md = RT.grasp(A.score(rows))
    assert "| m | base | 0/1 | — | 1/1 |" in md
    assert "| m | para1 | 0/1 | 1/1 | 0/1 |" in md
    assert "| m | base@t0.7 × 3 | — | 1/1 |" in md


def test_couple_table_escapes_the_key_separator():
    r = {"test": "couple_r", "model": "m", "snap": "a", "variant": "base", "temp": 0.0, "rep": 0, "valid": True,
         "execution": "progressing", "intent": "aligned", "command": "continue", "command_raw": "continue",
         "claim_raw": "none", "claim_gated": "none", "gate": "ok", "truth": False, "state": "carry", "raw": "x",
         "prompt_sha": "s"}
    md = RT.couple(A.score([r]))
    assert "| couple_r · m | base |" in md and "couple_r|m" not in md


def test_day_consistency_pairs():
    today = [_g("a", "base", "grasped", True), _g("b", "base", "not_grasped", False)]
    g1 = [{"snap": "a", "views": "all3", "overlay": False, "rep": 0, "model": "m", "valid": True,
           "answer": {"grasp_state": "grasped"}},
          {"snap": "b", "views": "all3", "overlay": False, "rep": 0, "model": "m", "valid": True,
           "answer": {"grasp_state": "grasped"}},
          {"snap": "b", "views": "head", "overlay": False, "rep": 0, "model": "m", "valid": True,
           "answer": {"grasp_state": "uncertain"}}]
    res = DC.compare(today, g1, "m", "m")
    assert res["pairs"] == 2 and res["same"] == 1 and res["differ"] == [["b", "grasped", "not_grasped"]]
