"""E-VLA-solo (docs/stage3/prereg_vla_solo.md): episode metrics and the fixed verdict rules of
tools/vla_alone/analyze_vla.py, the speed hook arithmetic and argument split of tools/vla_alone/vla_closed.py."""
import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, *rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, *rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


V = _load("analyze_vla", "tools", "vla_alone", "analyze_vla.py")
C = _load("vla_closed", "tools", "vla_alone", "vla_closed.py")


def trace(reach=True, over=0.0, hold_from=None, n=300):
    rows = []
    for i in range(n):
        t = i * 0.01
        f = min(1.0, i / 100)
        x = 0.1 + (0.2 + over) * f if reach else 0.1
        g = [x, 0.0, 0.1]
        ph = "approach" if (not reach or i < 200) else "close"
        hold = hold_from is not None and i >= hold_from
        rows.append([t, g, g, [0.3, 0.0, 0.1], 0.1, ph, True, hold, [0.001 * i] * 7])
    return {"rows": rows}


def test_episode_metrics():
    e = V.episode(trace(reach=True, over=0.05), {"env_success": False})
    assert abs(e["overshoot_mm"] - 50.0) < 1.0 and e["min_d3_mm"] < 1.0 and e["phase_max"] == "close"
    e = V.episode(trace(reach=False, hold_from=100), {"env_success": False})
    assert e["perm_hold"] and abs(e["min_d3_mm"] - 200.0) < 1.0 and e["jump_ticks"] == 0


def _arm(success, d3, perm=0, rank=0, over=10.0):
    return {f"s/{i}": {"success": i < success, "min_d3_mm": d3, "min_xy_mm": d3, "phase_rank": rank,
                       "phase_max": V.PH[rank], "stuck_s": 1.0, "hold_s": 0.0, "perm_hold": i < perm,
                       "overshoot_mm": over, "t_end_s": 60.0, "jump_ticks": 0, "v_appr_mm_s": 50.0} for i in range(12)}


def test_rules():
    arms = {"A": _arm(0, 30, perm=8), "B": _arm(1, 30, rank=3), "C": _arm(3, 30, over=5.0), "D": _arm(2, 30),
            "E": _arm(0, 30), "F": _arm(12, 5), "G": _arm(0, 200)}
    r = V.verdict(arms)
    assert r["G_bench"] and r["Q1"] == "PROGRESS_ONLY" and r["Q2"] == "ADOPT_C" and r["Q3"] == "CONFIRMED"
    arms["C"] = _arm(5, 30)
    assert V.verdict(arms)["Q1"] == "TASK_MEANINGFUL"
    arms["F"] = _arm(9, 5)
    assert V.verdict(arms)["Q1"] == "NO_VERDICT_BENCH"


def test_no_progress():
    arms = {k: _arm(0, 190) for k in "ABCDE"}
    arms.update(F=_arm(12, 5), G=_arm(0, 200))
    assert V.verdict(arms)["Q1"] == "NOT_MEANINGFUL"


def test_speed_hook_and_args():
    class R:
        _play_prev_t, _play_lag = None, 0.0
    r = R()
    for k in range(101):
        C.advance(r, k * 0.01, 0.5)
    assert abs(r._play_lag - 0.5) < 1e-9
    rest, cfg = C.split_args(["--model", "x", "--vla-speed", "0.75", "--out", "o"])
    assert rest == ["--model", "x", "--out", "o"] and cfg["speed"] == 0.75
