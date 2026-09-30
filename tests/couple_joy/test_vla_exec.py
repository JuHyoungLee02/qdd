import numpy as np

from harvest.couple_joy.vla_exec import GRIP_WAIT_S, VLAJoyExec


class Res:
    def __init__(self, chunk=None, error=None):
        self.chunk, self.chunk_dt, self.error, self.latency_s, self.meta = chunk, 1 / 30, error, 0.01, {}


class FakeClient:
    """Chunk = 15 rows moving every joint by +0.2 rad over the chunk, gripper column = self.w."""
    def __init__(self, w=0.107, error=None):
        self.calls, self.w, self.error = [], w, error

    def chunk(self, ctx, committed):
        self.calls.append((ctx, dict(committed)))
        if self.error:
            return Res(error=self.error)
        q = np.asarray(ctx["joint_pos"][:7], float)
        rows = [np.r_[q + 0.2 * k / 14, self.w] for k in range(15)]
        return Res(chunk=np.array(rows))


class FakeIO:
    def __init__(self):
        self.q, self.w = np.zeros(7), 0.107

    def frames(self):
        return {"cam_head": np.zeros((4, 4, 3), np.uint8), "cam_wrist_right": np.zeros((4, 4, 3), np.uint8)}

    def joint_pos(self):
        return np.r_[self.q, self.w]

    def ctx_text(self, phase, t):
        return f"ctx {phase}"


def make(client=None, holding=False):
    io = FakeIO()
    ex = VLAJoyExec(io, client or FakeClient(), dt=0.05, table_z=0.8, tcp0=[0.4, 0.0, 1.0], q0=np.zeros(7), w0=0.107,
                    w_open=0.107, w_close=0.0, quat0=(1, 0, 0, 0), tgt="o3", place="o5",
                    holding_fn=lambda: holding)
    return io, ex


def test_chunk_requested_once_per_decision_step_with_joystick_and_phase():
    io, ex = make()
    ex.set_intent({"mode": "point", "height": "above", "gripper": "keep"})
    ex.go_to([0.6, 0.0, 1.0], "keep", 0.0)
    for k in range(8):  # ticks at t = 0 .. 0.35 s -> a second step at t = 0.35 >= 0.33
        ex.tick_q(k * 0.05, [0.4, 0.0, 1.0])
    c = ex.client.calls
    assert len(c) == 2
    assert c[0][1] == {"dir_xy": "plus_x", "dir_z": "none_z", "mag_coarse": "xlarge", "target": "o3",
                       "phase": "continue"}
    assert c[0][0]["phase"] == "approach" and c[0][0]["ctx_text"] == "ctx approach"


def test_joint_command_is_clamped_to_004_per_tick():
    io, ex = make()
    ex.set_intent({"mode": "point", "height": "above", "gripper": "keep"})
    ex.go_to([0.6, 0.0, 1.0], "keep", 0.0)
    q, w, _ = ex.tick_q(0.0, [0.4, 0.0, 1.0])
    q, w, _ = ex.tick_q(1.0, [0.4, 0.0, 1.0])  # far into the chunk: target +0.2 rad, one tick allows 0.04
    assert np.all(np.abs(q) <= 0.08 + 1e-9) and w == 0.107


def test_reach_ends_the_move():
    io, ex = make()
    ex.set_intent({"mode": "point", "height": "above", "gripper": "keep"})
    ex.go_to([0.6, 0.0, 1.0], "keep", 0.0)
    ex.tick_q(0.0, [0.4, 0.0, 1.0])
    _, _, ev = ex.tick_q(0.05, [0.598, 0.0, 1.0])
    assert [e["event"] for e in ev] == ["reach"] and not ex.busy


def test_close_at_arrival_falls_back_to_code_when_vla_does_not_close():
    io, ex = make(FakeClient(w=0.107))  # the VLA never closes
    ex.set_intent({"mode": "point", "height": "grasp", "gripper": "close"})
    ex.go_to([0.6, 0.0, 0.9], "close", 0.0)
    ex.tick_q(0.0, [0.4, 0.0, 0.9])
    ex.tick_q(0.05, [0.6, 0.0, 0.9])  # reach -> close stage
    assert ex.busy and ex.phase == "close"
    evs, t = [], 0.1
    while ex.busy and t < 10:
        evs += [e["event"] for e in ex.tick_q(t, [0.6, 0.0, 0.9])[2]]
        t += 0.05
    assert "grip_fallback" in evs and "close" in evs and "gripper_done" in evs
    assert t >= GRIP_WAIT_S and ex.width == 0.0


def test_close_by_vla_counts_as_vla_close():
    io, ex = make(FakeClient(w=0.0))  # the VLA closes at once
    ex.set_intent({"mode": "gripper", "gripper": "close"})
    ex.grip("close", 0.0)
    evs, t = [], 0.0
    while ex.busy and t < 10:
        evs += [e["event"] for e in ex.tick_q(t, [0.6, 0.0, 0.9])[2]]
        t += 0.05
    assert "close" in evs and "grip_fallback" not in evs


def test_timeout_when_goal_never_reached():
    io, ex = make()
    ex.set_intent({"mode": "point", "height": "above", "gripper": "keep"})
    ex.go_to([0.6, 0.0, 1.0], "keep", 0.0)
    evs, t = [], 0.0
    while ex.busy and t < 60:
        evs += [e["event"] for e in ex.tick_q(t, [0.4 + 0.001 * (t < 1), 0.0, 1.0])[2]]
        t += 0.05
    assert evs[-1] == "timeout" and not ex.busy


def test_client_error_holds_the_arm_and_is_logged():
    io, ex = make(FakeClient(error="boom"))
    ex.set_intent({"mode": "point", "height": "above", "gripper": "keep"})
    ex.go_to([0.6, 0.0, 1.0], "keep", 0.0)
    q, w, ev = ex.tick_q(0.0, [0.4, 0.0, 1.0])
    assert np.allclose(q, 0.0) and any(e["event"] == "vla_error" for e in ev)
