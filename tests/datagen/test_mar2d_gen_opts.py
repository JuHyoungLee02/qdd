"""MolmoAct R2 data (plan 2026-09-26-molmoact-r2-data Task 2): generator options --waypoints / --layout pair are
explicit, guarded, and leave the default path untouched."""
import pytest

from harvest.datagen import gen as G


def test_planner_cls_default_has_no_waypoints():
    base = G._planner_cls()
    assert base.__name__ == "RecPlanner" and not hasattr(base, "setup_waypoints")
    from harvest.sim.planner import OraclePlanner
    wp = G._planner_cls(waypoints=True)
    assert hasattr(wp, "setup_waypoints") and issubclass(wp, OraclePlanner)
    assert "RecPlanner" in [c.__name__ for c in wp.__mro__]


def test_check_molmo_opts_guards():
    G.check_molmo_opts(["P0"], ["mug_tray", "bottle_tray"], False, "task")
    G.check_molmo_opts(["P0", "P1", "P2"], ["mug_tray"], False, "task")  # default: no restriction
    G.check_molmo_opts(["P0"], ["mug_tray", "bottle_tray", "mug_marker"], True, "task")
    G.check_molmo_opts(["P0"], ["mug_tray", "bottle_tray"], False, "pair")
    with pytest.raises(SystemExit):
        G.check_molmo_opts(["P0", "P1"], ["mug_tray"], True, "task")  # waypoints: P0 only
    with pytest.raises(SystemExit):
        G.check_molmo_opts(["P2"], ["mug_tray"], False, "pair")
    with pytest.raises(SystemExit):
        G.check_molmo_opts(["P0"], ["mug_marker"], False, "pair")  # not a pair task
    with pytest.raises(SystemExit):
        G.check_molmo_opts(["P0"], ["mug_tray"], True, "pair")  # one option at a time
    with pytest.raises(SystemExit):
        G.check_molmo_opts(["P0"], ["mug_tray"], False, "grid")


class _Stop(Exception):
    pass


class _FakeEnv:
    def __init__(self):
        self.calls = []

    def set_seed(self, *a, **kw):
        self.calls.append((a, kw))

    def reset(self):
        raise _Stop


@pytest.mark.parametrize("layout,expect_kw", [("task", {}), ("pair", {"layout": "pair"})])
def test_record_episode_set_seed_call(tmp_path, layout, expect_kw):
    env = _FakeEnv()
    kw = {} if layout == "task" else {"layout": layout}
    with pytest.raises(_Stop):
        G.record_episode(env, 11001, "mug_tray", "P0", str(tmp_path), **kw)
    assert env.calls == [((11001, "mug_tray"), expect_kw)]


def test_cli_parses_new_options(monkeypatch):
    seen = {}

    def fake_gen(out, variant, tasks, kinds, seeds, stale_s, H, max_items, waypoints=False, layout="task"):
        seen.update(tasks=tasks, kinds=kinds, seeds=seeds, waypoints=waypoints, layout=layout)
        raise _Stop

    monkeypatch.setattr(G, "gen", fake_gen)
    with pytest.raises(_Stop):
        G.main(["gen", "--out", "x", "--tasks", "mug_tray,bottle_tray", "--kinds", "P0", "--seeds", "11001-11002",
                "--confirm-train", "--layout", "pair"])
    assert seen == dict(tasks=["mug_tray", "bottle_tray"], kinds=["P0"], seeds=[11001, 11002], waypoints=False,
                        layout="pair")
    with pytest.raises(_Stop):
        G.main(["gen", "--out", "x", "--tasks", "all", "--kinds", "P0", "--seeds", "10001", "--confirm-train",
                "--waypoints"])
    assert seen["waypoints"] is True and seen["layout"] == "task"
