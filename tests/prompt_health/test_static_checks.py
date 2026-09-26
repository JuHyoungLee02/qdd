"""Prompt health check static checks (tools/prompt_health/static_checks.py): runs on the live code, every check gives a
bool flag and a file:line evidence string; the probe grasp rows now log their prompt version."""
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


S = _load("ph_static", ("tools", "prompt_health", "static_checks.py"))


def test_all_checks_return_flag_and_evidence():
    res = S.run()
    assert len(res) >= 12
    for k, (flag, ev) in res.items():
        assert isinstance(flag, bool) and isinstance(ev, str) and ev, k


def test_probe_grasp_rows_log_prompt_version():
    assert S.run()["P1_grasp_rows_log_prompt_version"][0] is False


def test_line_finder():
    assert S._line("harvest/couple/prompt.py", r"^REQ_OPEN").startswith("harvest/couple/prompt.py:")
