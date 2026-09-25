"""Env.reset recreates the PhysX scene (physx_hard_reset.md) + the determinism tool's trace comparison. No Isaac:
the Isaac objects are small stand-ins that record what is called on them. The real check runs on the pod
(tests/sim/test_determinism_isaac.py, python -m harvest.sim.determinism)."""
import numpy as np
import pytest

from harvest.sim import scene
from harvest.sim.determinism import compare_traces


# ------------------------------------------------------------------------------------------ compare_traces
def _trace(n=10, seed=0):
    r = np.random.default_rng(seed)
    return {"joint_pos": r.normal(size=(n, 30)).astype(np.float32), "joint_vel": r.normal(size=(n, 30)).astype(
        np.float32), "obj_pose": r.normal(size=(n, 5, 7)).astype(np.float32),
        "obj_vel": r.normal(size=(n, 5, 6)).astype(np.float32)}


def test_compare_identical():
    c = compare_traces(_trace(), _trace())
    assert c["identical"] and c["first_diff_tick"] is None and c["len"] == [10, 10]


def test_compare_one_ulp_at_tick_7_is_a_difference():
    a, b = _trace(), _trace()
    b["obj_pose"][7, 2, 0] = np.nextafter(b["obj_pose"][7, 2, 0], np.float32(np.inf))
    c = compare_traces(a, b)
    assert not c["identical"] and c["first_diff_tick"] == 7 and 0 < c["max_abs"]["obj_pose"] < 1e-6


def test_compare_different_length_is_a_difference():
    a, b = _trace(10), _trace(10)
    b = {k: v[:8] for k, v in b.items()}
    c = compare_traces(a, b)
    assert not c["identical"] and c["first_diff_tick"] == 8 and c["len"] == [10, 8]


# ------------------------------------------------------------------------------------------ hard reset
@pytest.fixture(autouse=True)
def _no_usd(monkeypatch):
    if hasattr(scene, "_author_usd_pose"):
        monkeypatch.setattr(scene, "_author_usd_pose", lambda path, pos, quat: None)


class _Timeline:
    """Stands in for the Isaac Lab SimulationContext: stop() fires STOP, reset(soft=False) fires STOP (if still
    playing) then PLAY on every subscriber -- as the Kit timeline does."""

    def __init__(self, log):
        self.log, self.subs, self.playing = log, [], True
        self._disable_app_control_on_stop_handle = False

    def stop(self):
        self.log.append(("sim.stop", self._disable_app_control_on_stop_handle))
        self._stop()

    def _stop(self):
        if self.playing:
            for s in self.subs:
                s._invalidate_initialize_callback("STOP")
        self.playing = False

    def reset(self, soft=False):
        self.log.append(("sim.reset", soft))
        if not soft:
            self._stop()
            for s in self.subs:
                s._initialize_callback("PLAY")
            self.playing = True


class _Camera:
    """Isaac Lab Camera: STOP drops its view, PLAY builds new render products (one more per hard reset)."""

    def __init__(self):
        self.render_products, self.view = ["rp0"], "view"

    def _invalidate_initialize_callback(self, event):
        self.view = None

    def _initialize_callback(self, event):
        self.render_products.append(f"rp{len(self.render_products)}")
        self.view = "view"


class _Asset:
    def __init__(self):
        self.inits = 0

    def _invalidate_initialize_callback(self, event):
        pass

    def _initialize_callback(self, event):
        self.inits += 1


class _IsaacEnv:
    def __init__(self, log, sim):
        self.log, self.sim, self._sim_step_counter = log, sim, 1234

    def reset(self, seed=None):
        self.log.append(("env.reset", seed))


class _T:
    def __init__(self, a):
        self.a = np.asarray(a)

    def __getitem__(self, i):
        return _T(self.a[i])

    def cpu(self):
        return self

    def numpy(self):
        return self.a


def _env(cameras=("cam_head",)):
    log = []
    sim = _Timeline(log)
    e = scene.Env.__new__(scene.Env)
    e.env = _IsaacEnv(log, sim)
    e.cameras, e.seed, e.variant = tuple(cameras), 7, "standard"
    e.layout, e.randomization = scene.sample_layout(7), None
    e.robot = type("R", (), {"data": type("D", (), {"joint_pos": _T(np.zeros((1, 30)))})()})()
    e.arm_ids, e.step_dt = list(range(7)), 0.05
    e.objects = {k: None for k in ("o3", "o5", "o8", "o9", "o10")}
    e._place_marker = lambda: log.append(("marker",))
    cams = {n: _Camera() for n in cameras}
    rob = _Asset()
    sim.subs = [rob, *cams.values()]
    e.scene = {**cams, "robot": rob}
    return e, log, cams, rob


def test_reset_recreates_physx_scene_before_the_episode_reset():
    e, log, _, _ = _env()
    e.reset(settle_s=0.0)
    assert ("sim.reset", False) in log
    assert log.index(("sim.reset", False)) < log.index(("env.reset", 7))
    e.reset(settle_s=0.0)  # every reset, not only the first
    assert log.count(("sim.reset", False)) == 2


def test_hard_reset_reinitializes_physics_assets_but_keeps_camera_render_products():
    e, log, cams, rob = _env(("cam_head", "cam_wrist_right"))
    for _ in range(3):
        e.reset(settle_s=0.0)
    assert rob.inits == 3  # articulation / objects / contact sensors get new PhysX views
    for c in cams.values():
        assert c.render_products == ["rp0"] and c.view == "view"  # no render product per episode
        assert "_initialize_callback" not in vars(c)  # the class callbacks are back after the reset


def test_new_scene_is_built_with_the_seeds_object_poses(monkeypatch):
    """The PhysX scene is built from the USD poses. Those are the make_env seed's layout, so a process made with
    another seed built a different scene (measured: DEV 11 after make_env(5), o8 on the table instead of parked,
    mug 10 mm off). The seed's reset poses are authored while the timeline is stopped, before PLAY."""
    e, log, _, _ = _env(())
    e.layout = scene.sample_layout(11)  # o8 / o9 parked
    wrote = {}

    def author(path, pos, quat):
        assert not e.env.sim.playing  # between STOP and PLAY
        assert e.env.sim._disable_app_control_on_stop_handle  # else Isaac Lab spins inside the STOP event
        wrote[path] = (tuple(pos), tuple(quat))
    monkeypatch.setattr(scene, "_author_usd_pose", author)
    e.reset(settle_s=0.0)
    assert log.index(("sim.stop", True)) < log.index(("sim.reset", False))
    assert set(wrote) == {f"/World/envs/env_0/{k.upper()}" for k in ("o3", "o5", "o8", "o9", "o10")}
    for k in ("o3", "o5", "o8", "o9", "o10"):
        assert wrote[f"/World/envs/env_0/{k.upper()}"] == tuple(map(tuple, scene._object_reset_pose(k, e.layout)))
    assert not e.env.sim._disable_app_control_on_stop_handle  # back to Isaac Lab's default


def test_hard_reset_restarts_the_render_step_counter():
    e, _, _, _ = _env(())
    e.reset(settle_s=0.0)
    assert e.env._sim_step_counter == 0  # render phase at episode start no longer depends on earlier episodes


def test_soft_reset_opt_out():
    e, log, _, _ = _env()
    e.hard_reset = False  # make_env(..., hard_reset=False): old pool replays (history-dependent physics)
    e.reset(settle_s=0.0)
    assert ("sim.reset", False) not in log and ("env.reset", 7) in log
