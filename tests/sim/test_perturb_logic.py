"""Pure parts of harvest.sim.perturb: DEV perturbations P0-P2 only (E §4.5)."""
import numpy as np
import pytest

from harvest.sim.perturb import DEV_KINDS, PerturbState, p1_offset, p2_spawn_xy


def test_only_dev_kinds_exist():
    assert DEV_KINDS == ("P0", "P1", "P2")
    for k in ("P3", "P4", "P5"):
        with pytest.raises(ValueError):
            PerturbState(k, 0)


@pytest.mark.parametrize("seed", range(30))
def test_p1_is_2cm_horizontal_seeded(seed):
    d = p1_offset(seed)
    assert d.shape == (2,) and np.linalg.norm(d) == pytest.approx(0.02, abs=1e-9)
    assert np.allclose(d, p1_offset(seed))


def test_p1_directions_vary():
    angs = {round(float(np.arctan2(*p1_offset(s)[::-1])), 3) for s in range(30)}
    assert len(angs) > 20


def test_p1_triggers_once_on_first_near():
    st = PerturbState("P1", 5)
    assert st.poll(t=0.5, near_target=False, phase="approach") is None
    ev = st.poll(t=0.8, near_target=True, phase="descend")
    assert ev is not None and ev["kind"] == "P1" and ev["t"] == 0.8
    assert st.poll(t=0.9, near_target=True, phase="descend") is None  # only the first time


def test_p2_triggers_half_second_after_carry_start():
    st = PerturbState("P2", 5)
    assert st.poll(t=3.0, near_target=True, phase="lift") is None
    assert st.poll(t=3.2, near_target=False, phase="carry") is None  # carry starts at 3.2
    assert st.poll(t=3.65, near_target=False, phase="carry") is None
    ev = st.poll(t=3.7, near_target=False, phase="carry")
    assert ev is not None and ev["kind"] == "P2"
    assert st.poll(t=3.75, near_target=False, phase="carry") is None


def test_p0_never_triggers():
    st = PerturbState("P0", 1)
    for i in range(100):
        assert st.poll(t=i * 0.05, near_target=True, phase="carry") is None


@pytest.mark.parametrize("seed", range(30))
def test_p2_spawn_beside_path_not_on_it(seed):
    a, b = np.array([0.35, -0.10]), np.array([0.42, -0.35])
    obst = {"o3": (a, 0.032), "o5": (b, 0.114)}
    xy = p2_spawn_xy(seed, a, b, obst, radius=0.04)
    u = (b - a) / np.linalg.norm(b - a)
    rel = xy - a
    along = rel @ u
    lateral = abs(rel[0] * u[1] - rel[1] * u[0])
    assert 0.0 <= along <= np.linalg.norm(b - a)
    assert 0.07 <= lateral <= 0.13
    for c, r in obst.values():
        assert np.linalg.norm(xy - c) >= r + 0.04 + 0.01
