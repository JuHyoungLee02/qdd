"""Cost ledger (hard stop), the shared code executor (velocity-limited targets + gripper events, safety clip) and
the image overlay (TCP marker, pixel rulers)."""
import json

import numpy as np
import pytest

from harvest.astra_motion import cost as C
from harvest.astra_motion import executor as E
from harvest.astra_motion import overlay as O

from .test_geometry import HEAD, TZ


# ------------------------------------------------------------------ cost
def test_cost_usd_uses_cached_and_output_prices():
    u = {"input_tokens": 2000, "input_tokens_details": {"cached_tokens": 1000}, "output_tokens": 1000,
         "output_tokens_details": {"reasoning_tokens": 800}}
    usd = C.cost_usd("gpt-6-astra", u)
    assert abs(usd - (1000 * 10 + 1000 * 1 + 1000 * 50) / 1e6) < 1e-12
    assert C.cost_usd("local:qwen", u) == 0.0


def test_ledger_accumulates_resumes_and_hard_stops(tmp_path):
    p = tmp_path / "cost.jsonl"
    L = C.Ledger(str(p), hard_krw=100.0, krw_per_usd=1000.0)
    L.add({"usage": {"input_tokens": 1000, "output_tokens": 1000}, "model": "gpt-6-astra"})  # 0.06 USD = 60 KRW
    assert abs(L.total_krw - 60.0) < 1e-9
    L2 = C.Ledger(str(p), hard_krw=100.0, krw_per_usd=1000.0)  # a new process reads the file
    assert abs(L2.total_krw - 60.0) < 1e-9
    L2.check(next_call_max_usd=0.03)  # 60 + 30 <= 100
    with pytest.raises(C.BudgetStop):
        L2.check(next_call_max_usd=0.05)
    rows = [json.loads(x) for x in open(p)]
    assert rows[-1]["cum_krw"] == 60.0 and rows[-1]["cost_krw"] == 60.0


# ------------------------------------------------------------------ executor
def run(ex, tcp, T=20.0, lag=0.0):
    t, evs = 0.0, []
    while t < T:
        cmd, w, ev = ex.tick(t, tcp)
        evs += ev
        tcp = tcp + (cmd - tcp) * (1 - lag)
        t += ex.dt
        if not ex.busy:
            break
    return tcp, evs, t


def test_executor_velocity_and_gripper_events():
    tcp0 = np.array([0.34, -0.25, TZ + 0.25])
    ex = E.MotionExec(dt=0.05, table_z=TZ, tcp0=tcp0, w_open=0.107, w_close=0.050, v=0.08)
    ex.load([E.Target(np.array([0.42, -0.20, TZ + 0.10]), "keep"), E.Target(np.array([0.42, -0.20, TZ + 0.08]),
                                                                          "close")], t=0.0)
    cmd, _, _ = ex.tick(0.0, tcp0)
    assert np.linalg.norm(cmd - tcp0) <= 0.08 * 0.05 + 1e-9  # velocity limit per tick
    tcp, evs, t = run(ex, cmd)
    kinds = [e["event"] for e in evs]
    assert kinds.count("reach") == 2 and "close" in kinds and kinds[-1] == "gripper_done"
    assert ex.width == 0.050
    assert np.linalg.norm(tcp - [0.42, -0.20, TZ + 0.08]) < 1e-6


def test_executor_safety_clip_and_floor():
    ex = E.MotionExec(dt=0.05, table_z=TZ, tcp0=np.array([0.34, -0.25, TZ + 0.25]), w_open=0.107, w_close=0.05)
    p, clipped = ex.clip(np.array([0.90, -0.20, TZ - 0.10]))
    assert clipped and p[0] == E.SAFE_X[1] and abs(p[2] - (TZ + E.SAFE_DZ[0])) < 1e-12
    p, clipped = ex.clip(np.array([0.40, -0.20, TZ + 0.10]))
    assert not clipped


def test_executor_timeout_when_blocked():
    tcp0 = np.array([0.34, -0.25, TZ + 0.25])
    ex = E.MotionExec(dt=0.05, table_z=TZ, tcp0=tcp0, w_open=0.107, w_close=0.05, v=0.08, extra_s=1.0)
    ex.load([E.Target(np.array([0.34, -0.25, TZ + 0.05]), "open")], t=0.0)
    t, evs = 0.0, []
    while ex.busy and t < 10:
        _, _, ev = ex.tick(t, tcp0)  # the arm never moves
        evs += ev
        t += 0.05
    assert any(e["event"] == "timeout" for e in evs) and any(e["event"] == "open" for e in evs)


def test_smooth_exec_ramps_scales_decays_and_flips():
    tcp0 = np.array([0.40, -0.20, TZ + 0.20])
    ex = E.SmoothExec(dt=0.05, table_z=TZ, tcp0=tcp0, w_open=0.107, w_close=0.05, window=1.0, decay_s=0.5)
    ex.apply(np.array([0.04, 0.0, 0.0]), "keep", t=0.0, scale=0.5, flip=False)
    t, p = 0.0, tcp0.copy()
    for _ in range(20):  # the window: constant velocity 0.5 * 4 cm / 1 s
        p, _, _ = ex.tick(t, p)
        t += 0.05
    assert abs(p[0] - (0.40 + 0.02)) < 1e-3  # ~50 % of the edit over the window (ramped offset, accel-limited)
    for _ in range(11):  # decay 0.5 s: velocity falls linearly to 0 -> + half of 0.02 * 0.5
        p, _, _ = ex.tick(t, p)
        t += 0.05
    assert abs(p[0] - (0.42 + 0.02 * 0.5 / 2)) < 2e-3 and not ex.busy
    ex.apply(np.array([0.0, 0.04, 0.0]), "keep", t=t, scale=1.0, flip=False)
    for _ in range(6):
        q, _, _ = ex.tick(t, p)
        p, t = q, t + 0.05
    assert abs(ex.v[1] - 0.04) < 1e-9  # 100 %: 4 cm/s after the acceleration ramp
    ex.apply(np.array([0.0, -0.04, 0.0]), "keep", t=t, scale=0.5, flip=True)
    assert np.allclose(ex.v, 0)  # a direction flip resets before the new ramp
    q, _, _ = ex.tick(t, p)
    assert np.linalg.norm(ex.v) <= E.A_MAX * 0.05 + 1e-12  # and speeds up again gradually


def test_smooth_exec_gripper_at_window_end():
    ex = E.SmoothExec(dt=0.05, table_z=TZ, tcp0=np.array([0.40, -0.20, TZ + 0.08]), w_open=0.107, w_close=0.05)
    ex.apply(np.array([0.0, 0.0, -0.01]), "close", t=0.0, scale=1.0, flip=False)
    t, p, evs = 0.0, ex.cmd.copy(), []
    while t < 3.0:
        p, w, ev = ex.tick(t, p)
        evs += ev
        t += 0.05
    kinds = [e["event"] for e in evs]
    assert "close" in kinds and "gripper_done" in kinds and ex.width == 0.05


# ------------------------------------------------------------------ overlay
def test_overlay_marks_tcp_and_keeps_input():
    img = np.full((HEAD.H, HEAD.W, 3), 128, np.uint8)
    p = np.array([0.42, -0.18, TZ + 0.1])
    out = O.annotate(img, HEAD, tcp=p)
    assert (img == 128).all() and out.shape == img.shape
    from harvest.astra_motion.geometry import pixel_of
    iu, iv, inside = pixel_of(HEAD, p)
    assert inside and (out[iv - 8:iv + 9, iu - 8:iu + 9] != 128).any()
    assert (out[:6, 100] != 128).any()  # a ruler tick on the top border at u = 100


def test_motion_overlay_trace_arrows_and_wrist_inset():
    img = np.full((HEAD.H, HEAD.W, 3), 128, np.uint8)
    tcp = np.array([0.42, -0.18, TZ + 0.1])
    trace = [tcp + [-0.01 * k, 0.0, 0.0] for k in range(10, 0, -1)]
    out = O.annotate(img, HEAD, tcp, trace=trace, exec_dir=np.array([0.0, 0.05, 0.0]),
                     astra_dir=np.array([0.03, 0.0, -0.02]))
    from harvest.astra_motion.geometry import pixel_of
    iu, iv, _ = pixel_of(HEAD, trace[0])
    assert (out[iv - 2:iv + 3, iu - 2:iu + 3] != 128).any()  # the oldest trace point is drawn
    # wrist inset: nothing drawn at the TCP (grasp zone), arrows in the top-right corner box
    w = np.full((240, 424, 3), 128, np.uint8)
    from .test_geometry import WRIST
    o2 = O.annotate(w, WRIST, tcp, exec_dir=np.array([0.0, 0.05, 0.0]), astra_dir=np.array([0.03, 0, 0]),
                    wrist_inset=True, rulers=False)
    ju, jv, ins = pixel_of(WRIST, tcp)
    if ins:
        assert (o2[max(jv - 8, 0):jv + 9, max(ju - 8, 0):ju + 9] == 128).all()
    assert (o2[:O.INSET, -O.INSET:] != 128).any()


def test_png_bytes_round_trip():
    img = np.zeros((10, 12, 3), np.uint8)
    img[2, 3] = (255, 0, 0)
    b = O.png_bytes(img)
    from io import BytesIO

    from PIL import Image
    back = np.asarray(Image.open(BytesIO(b)).convert("RGB"))
    assert (back == img).all()
