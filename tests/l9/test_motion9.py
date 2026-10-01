import numpy as np

from harvest.l9 import motion9 as M


def test_style_ranges_and_determinism():
    for s in range(50):
        st = M.sample_style(s)
        assert st["profile"] in M.PROFILES and 0.06 <= st["v_avg"] <= 0.11 and 0.6 <= st["preshape_at"] <= 0.8
        assert st == M.sample_style(s)
    assert len({M.style_hash(M.sample_style(s)) for s in range(50)}) == 50


def test_two_phase_monotone_ends():
    xs = [M.two_phase(s, 0.8, 0.5) for s in np.linspace(0, 1, 101)]
    assert xs[0] == 0.0 and abs(xs[-1] - 1.0) < 1e-9 and all(b >= a - 1e-12 for a, b in zip(xs, xs[1:]))


def test_via_point_bounded():
    p0, p1 = np.array([0.35, -0.3, 1.0]), np.array([0.55, -0.1, 1.0])
    v = M.via_point(p0, p1, 0.25, 0.12)
    m = (p0 + p1) / 2
    assert 0 <= v[2] - m[2] <= 0.05 + 1e-9 and np.hypot(*(v - m)[:2]) <= 0.03 + 1e-9


def _run(ex, n=4000, dt=0.05):
    tcp = ex.cmd.copy()
    out = []
    for i in range(n):
        p, w, ev = ex.tick(i * dt, tcp)
        tcp = p  # perfect tracking
        out.append((p.copy(), w, ev))
        if not ex.busy:
            break
    return out


def test_exec_reaches_target_and_steps_small():
    st = dict(M.sample_style(3), profile="two_phase", arc=0.2, side=0.1, pause_s=0.3)
    ex = M.HumanExec(0.05, 0.8, [0.34, -0.25, 1.05], 0.107, 0.04, st)
    ex.go_to([0.55, -0.10, 0.95], "keep", 0.0)
    tr = _run(ex)
    ps = np.array([p for p, _, _ in tr])
    assert np.linalg.norm(ps[-1] - [0.55, -0.10, 0.95]) < 1e-6
    assert np.abs(np.diff(ps, axis=0)).max() < 0.02  # the reference moves smoothly (<= 2 cm per 50 ms)
    straight = np.linspace(ps[0], ps[-1], len(ps))
    assert np.abs(ps - straight).max() > 0.005  # curved, not a straight line


def test_preshape_and_pause():
    st = dict(M.sample_style(5), preshape=True, preshape_at=0.7, pause_s=0.4, settle_s=0.0)
    ex = M.HumanExec(0.05, 0.8, [0.45, -0.2, 0.95], 0.107, 0.04, st)
    ex.go_to([0.45, -0.2, 0.86], "close", 0.0)
    tr = _run(ex)
    ws = [w for _, w, _ in tr]
    assert min(ws[:-5]) < 0.107 - 0.01 and ws[-1] == 0.04  # aperture narrowed before the close, then closed
    ex.go_to([0.45, -0.2, 0.95], "open", 10.0)
    t0 = None
    for i in range(400):
        p, w, ev = ex.tick(10.0 + i * 0.05, ex.cmd)
        if any(e["event"] == "reach" for e in ev):
            t0 = 10.0 + i * 0.05
        if any(e["event"] == "open" for e in ev):
            assert t0 is not None and 10.0 + i * 0.05 - t0 >= 0.4 - 1e-6
            break
    else:
        raise AssertionError("never opened")


def test_nullspace_keeps_tcp():
    rng = np.random.default_rng(0)
    J = rng.normal(size=(6, 7))
    dq = M.nullspace_pull(J, np.zeros(7), M.Q_MID, 0.02)
    assert np.abs(J @ dq).max() < 1e-9 and np.abs(dq).max() > 0
