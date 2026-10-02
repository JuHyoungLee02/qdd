"""qmon9 check 10 (ABA GT-label canary, place_oscillation fix): tools/l9/qmon9.aba_oscillations is pure file I/O
over one episode's labels.jsonl. qmon9.py is a tools/l9 sibling-import script (not a harvest package module), so
this test adds tools/l9 to sys.path the same way qmon9.py adds its own siblings, then imports it directly."""
import importlib
import json
import os
import sys

TOOLS_L9 = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tools", "l9")


def _load():
    if TOOLS_L9 not in sys.path:
        sys.path.insert(0, TOOLS_L9)
    import qmon9
    return importlib.reload(qmon9)


def _write_episode(tmp_path, steps):
    ep = tmp_path / "ep0"
    ep.mkdir()
    with open(ep / "labels.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for i, s in enumerate(steps):
            f.write(json.dumps({"call": i, "step": s}) + "\n")
    return str(ep)


def test_aba_oscillations_counts_round_trips(tmp_path):
    Q = _load()
    ep = _write_episode(tmp_path, ["above_target", "descend_close", "carry_up", "carry_over", "carry_up",
                                   "carry_over", "lower_open"])
    n, aba = Q.aba_oscillations(ep)
    assert n == 5  # carry_up, carry_over, carry_up, carry_over, lower_open
    assert aba == 2  # positions 2,3,4 and 3,4,5 (0-indexed within the 5) both round-trip


def test_aba_oscillations_zero_for_a_clean_single_pass(tmp_path):
    Q = _load()
    ep = _write_episode(tmp_path, ["above_target", "descend_close", "carry_up", "carry_over", "lower_open"])
    n, aba = Q.aba_oscillations(ep)
    assert n == 3 and aba == 0


def test_aba_oscillations_empty_episode(tmp_path):
    Q = _load()
    ep = tmp_path / "ep_empty"
    ep.mkdir()
    n, aba = Q.aba_oscillations(str(ep))
    assert (n, aba) == (0, 0)


def test_dropped_rows_excluded_from_aba():
    """_label_rows already drops rows with drop is not None; aba_oscillations must not count them."""
    Q = _load()
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        ep = os.path.join(d, "ep1")
        os.makedirs(ep)
        rows = [{"call": 0, "step": "carry_up"}, {"call": 1, "step": "carry_over", "drop": "tipped"},
                {"call": 2, "step": "carry_up"}]
        with open(os.path.join(ep, "labels.jsonl"), "w", encoding="utf-8", newline="\n") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        n, aba = Q.aba_oscillations(ep)
        assert n == 2 and aba == 0  # the dropped carry_over row is excluded, so no ABA (carry_up, carry_up only)
