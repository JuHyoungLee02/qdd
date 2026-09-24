"""aiworker action space conformance + OursPolicy through inspect_robots.eval() on the kinematic fake world.

Needs inspect_robots v0.59.0 (pod: /data/harvest/ir/src/src on PYTHONPATH; local: INSPECT_ROBOTS_SRC=<clone>/src)."""
import json
import os
import sys

import numpy as np
import pytest

from harvest.runtime.aiworker import DIM_LABELS, MAX_STEP, clip_action

if os.environ.get("INSPECT_ROBOTS_SRC"):
    sys.path.insert(0, os.environ["INSPECT_ROBOTS_SRC"])

LOW = np.r_[np.full(7, -3.0), 0.0]
HIGH = np.r_[np.full(7, 3.0), 0.107]


def test_clip_action_bounds_and_shape():
    a = clip_action([9, -9, 0, 0, 0, 0, 0, 0.5], LOW, HIGH)
    assert a[0] == 3.0 and a[1] == -3.0 and a[7] == pytest.approx(0.107)
    with pytest.raises(ValueError):
        clip_action(np.zeros(7), LOW, HIGH)
    assert len(DIM_LABELS) == 8 and len(MAX_STEP) == 8 and DIM_LABELS[-1] == "gripper_r_width"


def test_aiworker_info_is_conformant():
    pytest.importorskip("inspect_robots")
    from inspect_robots.conformance import check_embodiment

    from harvest.runtime.aiworker import build_info
    info = build_info(LOW, HIGH)
    rep = check_embodiment(info)
    assert rep.ok, rep.summary()
    assert "self_paced" not in info.capabilities and info.control_hz == 100.0
    assert np.all(np.isfinite(info.action_space.low)) and info.action_space.semantics.gripper == "continuous"


def test_ours_policy_through_eval_fake_world(tmp_path):
    ir = pytest.importorskip("inspect_robots")
    from inspect_robots import Observation, Scene, StepResult, Task
    from inspect_robots.controller import DefaultController
    from inspect_robots.scorer import success_at_end

    from harvest.runtime.aiworker import build_info
    from harvest.runtime.astra_hb import MockAstra
    from harvest.runtime.core import OursRuntime, RuntimeConfig
    from harvest.runtime.ir_policy import OursPolicy
    from harvest.runtime.models import MockSelector
    from .fakeworld import FakeWorld

    class FakeEmb:
        def __init__(self):
            self.info = build_info(np.full(8, -10.0), np.full(8, 10.0))

        def _obs(self):
            o = self.w.obs()
            return Observation(state={"joint_pos": o["joint_pos"]}, state_time=o["sim_time"],
                               extra={k: o[k] for k in ("sim_time", "m1", "kin", "table_z")})

        def reset(self, scene, *, seed=None):
            self.w, self.on = FakeWorld(), 0
            return self._obs()

        def step(self, action):
            self.w.step(np.clip(action.data, -10, 10))
            m1 = self.w.m1()["raw"]
            on = not self.w.held and ["o3", "o5"] in m1["contacts"]
            self.on = self.on + 1 if on else 0
            ok = self.on >= 100
            return StepResult(observation=self._obs(), terminated=ok, termination_reason="success" if ok else None,
                              info={"sim_time": self.w.t, "success": ok})

        def close(self):
            pass

    rt = OursRuntime(RuntimeConfig(clock="simlat", astra_mode="mock"), MockSelector(0.3), astra=MockAstra(3.0))
    pol = OursPolicy(rt, name="ours-modular-mock")
    task = Task(name="r5-fake", scenes=[Scene(id="dev0-P0-fake", instruction="Put the red mug on the blue tray.",
                                              init_seed=0, metadata={"layout_seed": 0})],
                scorer=success_at_end(), max_seconds=40.0)
    log = ir.eval(task, pol, FakeEmb(), log_dir=str(tmp_path), seed=0, controller=DefaultController(1))[0]
    rt.close()
    assert log.status == "success", getattr(log, "error", None)
    assert log.results.metrics  # success_at_end reduced
    assert log.eval.policy_config["backend"] == "modular" and log.eval.policy_config["clock"] == "simlat"
    assert "m4" in log.eval.policy_config and log.eval.policy_config["astra_prompt_id"]
    tm = log.samples[0].trial_metadata[0]
    s = tm["ours_summary"]
    assert s["env_success"] is True and s["calls_delivered"] > 30 and s["commit_ratio_mean"] > 0.5
    rows = [json.loads(x) for x in open(tm["ours_sidecar"], encoding="utf-8")]
    kinds = {r["type"] for r in rows}
    assert {"call", "step", "astra", "event"} <= kinds
    call = next(r for r in rows if r["type"] == "call")
    assert {"t_state", "t_deliver", "latency_s", "slots", "epoch_sent", "answers", "votes"} <= set(call)
