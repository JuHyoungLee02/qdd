import numpy as np

from harvest.deploy import overlap as O


def test_schedules():
    assert O.ask_now("S0", 1, busy=False, pending=False, t_left=None, lat_est=2)
    assert not O.ask_now("S0", 1, busy=True, pending=False, t_left=0.5, lat_est=2)
    assert O.ask_now("S1", 1, busy=True, pending=False, t_left=5, lat_est=2)
    assert not O.ask_now("S1", 1, busy=True, pending=True, t_left=5, lat_est=2)
    assert O.ask_now("S2", 1.0, busy=True, pending=False, t_left=1.9, lat_est=2)
    assert not O.ask_now("S2", 0.5, busy=True, pending=False, t_left=1.9, lat_est=2)


def test_async_holds_answer_until_due():
    u = O.AsyncUpper(lambda req: (("ans", req), 1.5), lambda lat: lat)
    u.submit(10.0, "r", {})
    assert u.due(11.0) is None
    p = u.due(11.5)
    assert p.answer == ("ans", "r") and p.t_q == 10.0 and u.pending is None


def test_stale_check():
    pts = np.array([[0.4, 0.0, 0.9], [0.42, 0.0, 0.9]])
    keep, why, sh = O.stale_check({"region": pts, "holding": False}, {"region": pts + [0.01, 0, 0], "holding": False})
    assert keep and np.allclose(sh, [0.01, 0, 0])
    keep, why, _ = O.stale_check({"region": pts}, {"region": pts + [0.05, 0, 0]})
    assert not keep and why == "object_moved"
    keep, why, _ = O.stale_check({"holding": False}, {"holding": True})
    assert not keep and why == "holding_changed"


def test_continuity_counts_mid_episode_stops():
    dt = 0.05
    x = list(np.linspace(0, 0.1, 40)) + [0.1] * 20 + list(np.linspace(0.1, 0.2, 40))
    P = np.stack([x, np.zeros(len(x)), np.zeros(len(x))], 1)
    c = O.continuity(P, dt)
    assert c["stops"] == 1 and abs(c["stop_s"] - 1.0) < 0.11
