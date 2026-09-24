"""D23 smoke: can inspect-robots v0.59.0 host a non-blocking policy with background
LLM-like calls, paired std/rnd scenes, and our own sidecar logs?

Three clock modes for the SAME policy code:
  sync     : act() blocks on every "LLM" call (world pauses) -> fairness twin of agent/capx
  wall     : embodiment self-paces to wall clock (SELF_PACED); act() never blocks
  simlat   : sim-time clock; a call issued at sim time t_s is delivered at t_s + measured
             wall latency (act() blocks only if the sim caught up with the deadline)
Fake LLM = sleep(U(0.2, 0.6)) s in a worker thread. No Isaac, no network.
"""

from __future__ import annotations

import json
import random
import sys
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

import numpy as np

from inspect_robots import (
    ActionChunk,
    ActionSemantics,
    Box,
    EmbodimentInfo,
    Observation,
    ObservationSpace,
    PolicyBase,
    PolicyInfo,
    Scene,
    Score,
    StateField,
    StateSpec,
    StepResult,
    Task,
    eval,
)
from inspect_robots.types import Action

DIM = 8
HZ = 100.0
LOW = -np.ones(DIM)
HIGH = np.ones(DIM)
LABELS = tuple([f"j{i}" for i in range(7)] + ["gripper"])


class ToyArm:
    """8-D joint_pos stand-in for one AI Worker arm + gripper."""

    def __init__(self, clock: str):
        self.clock = clock
        caps = {"seedable", "resettable", "privileged_success"}
        if clock == "wall":
            caps.add("self_paced")
        self.info = EmbodimentInfo(
            name=f"toyarm:{clock}",
            action_space=Box(
                shape=(DIM,), low=LOW, high=HIGH,
                semantics=ActionSemantics(control_mode="joint_pos", gripper="continuous",
                                          dim_labels=LABELS),
            ),
            observation_space=ObservationSpace(
                state=StateSpec(fields=(StateField("joint_pos", (DIM,), "rad"),))),
            control_hz=HZ,
            is_simulated=True,
            capabilities=frozenset(caps),
        )
        self.q = np.zeros(DIM)
        self.goal = np.zeros(DIM)
        self.t_sim = 0.0
        self._last = None

    def reset(self, scene: Scene, *, seed: int | None = None) -> Observation:
        md = dict(scene.metadata)
        layout_rng = np.random.default_rng(md["layout_seed"])  # layout fixed across epochs
        self.goal = layout_rng.uniform(-0.5, 0.5, DIM)
        self.variant = md["variant"]
        self.appearance = int(np.random.default_rng(seed).integers(1 << 30))  # epoch-varying
        self.q = np.zeros(DIM)
        self.t_sim = 0.0
        self._last = None
        return self._obs(scene.instruction)

    def _obs(self, instr=None) -> Observation:
        return Observation(state={"joint_pos": self.q.copy()}, instruction=instr,
                           state_time=self.t_sim,
                           extra={"sim_time": self.t_sim, "goal_hint": self.goal.copy()})

    def step(self, action: Action) -> StepResult:
        if self.clock == "wall":  # pace like inspect-robots-ros does
            now = time.monotonic()
            if self._last is not None:
                rem = self._last + 1.0 / HZ - now
                if rem > 0:
                    time.sleep(rem)
            self._last = time.monotonic()
        self.q = self.q + 0.2 * (np.asarray(action.data) - self.q)  # first-order servo
        self.t_sim += 1.0 / HZ
        err = float(np.max(np.abs(self.q - self.goal)))
        ok = err < 0.02
        return StepResult(observation=self._obs(), terminated=ok,
                          termination_reason="success" if ok else None,
                          info={"success": ok, "err": err, "sim_time": self.t_sim})

    def close(self) -> None:
        pass


class AsyncOurPolicy(PolicyBase):
    """Stand-in for Astra/Jev/M4/skills: overlapping ~3 Hz calls, commit, 100 Hz skill."""

    def __init__(self, clock: str, t_c: float = 0.33, max_inflight: int = 3):
        self.clock = clock
        self.t_c = t_c
        self.max_inflight = max_inflight
        self.info = PolicyInfo(
            name=f"ours:{clock}",
            action_space=Box(shape=(DIM,), low=LOW, high=HIGH,
                             semantics=ActionSemantics(control_mode="joint_pos",
                                                       gripper="continuous", dim_labels=LABELS)),
            observation_space=ObservationSpace(state_keys=frozenset({"joint_pos"})),
            control_hz=HZ,
        )
        self.pool = ThreadPoolExecutor(max_workers=max_inflight)

    # ---- fake LLM call (runs in worker thread) ----
    def _llm(self, goal: np.ndarray, t_state: float) -> dict:
        t0 = time.monotonic()
        time.sleep(random.uniform(0.2, 0.6))
        noisy = goal + np.random.default_rng().normal(0, 0.01, DIM)
        return {"choice": noisy, "t_state": t_state, "wall_latency": time.monotonic() - t0}

    def reset(self, scene: Scene) -> None:
        self.inflight: list[tuple[float, Future]] = []  # (t_send in policy clock, future)
        self.committed = None
        self.votes: list[dict] = []
        self.next_call = 0.0
        self.blocked_s = 0.0
        self.t0_wall = time.monotonic()

    def _now(self, obs: Observation) -> float:
        if self.clock == "wall":
            return time.monotonic() - self.t0_wall
        return float(obs.extra["sim_time"])

    def act(self, observation: Observation) -> ActionChunk:
        now = self._now(observation)
        goal = observation.extra["goal_hint"]
        if self.clock == "sync":
            if now >= self.next_call:  # world pauses while the "LLM" thinks
                t0 = time.monotonic()
                res = self._llm(goal, now)
                self.blocked_s += time.monotonic() - t0
                self._accept(res, now)
                self.next_call = now + self.t_c
        else:
            if now >= self.next_call and len(self.inflight) < self.max_inflight:
                self.inflight.append((now, self.pool.submit(self._llm, goal, now)))
                self.next_call = now + self.t_c
            still = []
            for t_send, fut in self.inflight:
                if self.clock == "wall":
                    if fut.done():
                        self._accept(fut.result(), now)
                    else:
                        still.append((t_send, fut))
                else:  # simlat: deliver at t_send + measured wall latency (sim seconds)
                    if fut.done():
                        res = fut.result()
                        if now >= t_send + res["wall_latency"]:
                            self._accept(res, now)
                        else:
                            still.append((t_send, fut))
                    elif self.committed is None or now >= t_send + 0.6:  # deadline reached
                        t0 = time.monotonic()
                        res = fut.result()  # sim waits: it ran faster than the real call
                        self.blocked_s += time.monotonic() - t0
                        still.append((t_send, _done(res)))
                    else:
                        still.append((t_send, fut))
            self.inflight = still
        target = self.committed if self.committed is not None else observation.state["joint_pos"]
        # 100 Hz "skill": one action per step, never waits on the planner
        return ActionChunk(actions=[Action(data=np.clip(target, LOW, HIGH))], control_hz=HZ,
                           meta={"committed": self.committed is not None})

    def _accept(self, res: dict, now: float) -> None:
        self.votes.append({"t_state": res["t_state"], "t_recv": now,
                           "lat": res["wall_latency"], "option_key": "move_to_goal"})
        self.committed = res["choice"]  # stand-in for M4 commit

    def on_trial_end(self, record, log_dir: str, run_id: str) -> None:
        side = Path(log_dir) / "ours" / run_id / f"{record.scene_id}-e{record.epoch}.jsonl"
        side.parent.mkdir(parents=True, exist_ok=True)
        side.write_text("\n".join(json.dumps(v) for v in self.votes), encoding="utf-8")
        record.metadata["ours_sidecar"] = str(side)
        record.metadata["n_votes"] = len(self.votes)
        record.metadata["policy_blocked_s"] = round(self.blocked_s, 3)
        record.metadata["seed"] = record.seed
        last = record.steps[-1].result.info if record.steps else {}
        record.metadata["sim_time_end"] = last.get("sim_time")


def _done(res):
    f: Future = Future()
    f.set_result(res)
    return f


class PrivSuccess:
    name = "priv_success"

    def __call__(self, record, target) -> Score:
        ok = bool(record.steps and record.steps[-1].result.info.get("success"))
        return Score(value=ok)


def main(clock: str) -> None:
    scenes = []
    for layout in (3, 7):
        for variant in ("std", "rnd"):
            scenes.append(Scene(id=f"{variant}-L{layout}", instruction="put mug on tray",
                                init_seed=layout,
                                metadata={"variant": variant, "layout_seed": layout}))
    task = Task(name=f"d23-smoke-{clock}", scenes=scenes, scorer=PrivSuccess(),
                max_seconds=5.0, epochs=2)
    t0 = time.monotonic()
    log = eval(task, AsyncOurPolicy(clock), ToyArm(clock),
               log_dir="D:/tools/audit_d23/smoke/logs", seed=0)[0]
    wall = time.monotonic() - t0
    print(f"== clock={clock} status={log.status} wall={wall:.1f}s "
          f"max_steps={log.eval.max_steps} metrics={log.results.metrics}")
    for s in log.samples:
        print(" ", s.scene_id, s.epochs,
              [(m["seed"], m["n_votes"], m["policy_blocked_s"], m["sim_time_end"])
               for m in s.trial_metadata])


if __name__ == "__main__":
    main(sys.argv[1])
