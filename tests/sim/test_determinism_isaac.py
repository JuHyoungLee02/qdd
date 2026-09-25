"""Pod-only (Isaac): the same DEV seed gives a bit-identical per-tick trace after different histories in one
process (first run after make_env, after another seed's partial episode, twice in a row). Skipped without Isaac Lab.
Run inside the Isaac python: /isaac-sim/python.sh -m pytest tests/sim/test_determinism_isaac.py (physx_hard_reset.md).
The full matrix (fresh process, full episodes, cameras) is python -m harvest.sim.determinism."""
import pytest

pytest.importorskip("isaaclab")


def test_same_seed_bit_identical_after_any_history():
    from harvest.sim.determinism import Tracer, _episode, compare_traces
    from harvest.sim.scene import make_env

    env = make_env(3, headless=True, cameras=(), depth=False)
    tr = Tracer(env)
    a, _ = _episode(env, tr, 3, (), cut_k=10)  # first run after make_env
    _episode(env, tr, 17, (), cut_k=14)  # another seed, cut mid-episode
    b, _ = _episode(env, tr, 3, (), cut_k=10)
    c, _ = _episode(env, tr, 3, (), cut_k=10)  # twice in a row
    for x in (b, c):
        r = compare_traces(a, x)
        assert r["identical"], r
