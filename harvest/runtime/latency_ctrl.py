"""LatencyChargingController (canon §42 latency-faithful track for synchronous baselines agent / capx): time each
policy.act() call (L seconds) and put ceil(L * control_hz) "hold the last command" actions in front of the chunk --
the arm stands still while the model thinks, as on the real robot (agent README). STUB: not needed for R5 (our
policy is non-blocking under simlat); the baselines (P3) will implement it. See tests/runtime/test_latency_ctrl.py.
"""
from __future__ import annotations


class LatencyChargingController:
    def __init__(self, control_hz: float, clock=None):
        self.control_hz, self.clock = control_hz, clock

    def next_action(self, policy, observation, t, store):  # pragma: no cover - stub
        raise NotImplementedError("TODO(P3): latency-charging controller for the sync baselines (canon §42)")
