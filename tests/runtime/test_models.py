"""Model back-ends (canon §58): ModularStack selectors and the FusedModel contract, with mocks."""
import numpy as np
import pytest

from harvest.runtime.models import (DECISION_QUESTIONS, MockFusedModel, MockSelector, build_live_request,
                                    fused_state_text)

RAW = {"grip": {"pos": [0.30, -0.10, 0.25], "w": 0.107, "effort": 0.0},
       "objs": {"o3": {"pos": [0.40, -0.20, 0.0475], "quat": [1, 0, 0, 0], "he": [0.032, 0.032, 0.0475]},
                "o5": {"pos": [0.45, -0.05, 0.0075], "quat": [1, 0, 0, 0], "he": [0.09, 0.07, 0.0075]}},
       "contacts": [], "support": {"o3": "table", "o5": "table"}}
S0 = ("contract: c1\nstage: S1 pick up mug o3 (exit: holding(o3) lifted(o3)) elapsed=normal\n"
      "robot: gripper=open arm=still\nfacts: holding(o3)=no lifted(o3)=no")


def test_live_request_has_the_five_decision_questions_and_S1_geometry():
    req, shown = build_live_request(7, "approach", S0, ["o3", "o5"], RAW)
    assert sorted(q for q, _ in shown.values()) == sorted(DECISION_QUESTIONS)
    assert all(qid.startswith("ds7.") for qid in req["questions"])
    assert "geometry (robot base frame" in req["state"] and "o3 mug red: dx=+10.0 dy=-10.0" in req["state"]


def test_mock_selector_is_the_code_rule_and_deterministic():
    req, shown = build_live_request(7, "approach", S0, ["o3", "o5"], RAW)
    m = MockSelector(latency_s=0.3)
    ctx = {"req": req, "shown": shown}
    a, b = m.decide(ctx), m.decide(ctx)
    assert a.answers == b.answers and m.synthetic_latency == 0.3 and a.chunk is None
    assert a.answers["dir_xy"]["choice"] == "plus_x_minus_y" and a.answers["target"]["choice"] == "o3"
    assert a.answers["phase"]["choice"] == "continue" and a.answers["dir_z"]["choice"] == "down"


def test_mock_fused_decides_then_chunks_on_committed_decisions():
    req, shown = build_live_request(7, "approach", S0, ["o3", "o5"], RAW)
    m = MockFusedModel(latency_s=0.3, chunk_latency_s=0.12)
    q = np.arange(8, dtype=float)
    r = m.decide({"req": req, "shown": shown, "joint_pos": q, "privileged_s1": req["state"]})
    assert set(r.answers) == set(DECISION_QUESTIONS) and r.chunk is None
    c = m.chunk({"joint_pos": q}, {"dir_xy": "plus_x"})
    assert c.chunk.shape == (15, 8) and np.allclose(c.chunk[-1], q) and c.chunk_dt == pytest.approx(1 / 30)
    assert m.synthetic_chunk_latency == 0.12 and c.meta["committed"] == {"dir_xy": "plus_x"}


def test_fused_state_text_has_no_coordinates():
    t = fused_state_text("Put the red mug on the blue tray.", "S1", "approach", np.zeros(8))
    assert "geometry" not in t and "joint_pos" in t and "Put the red mug" in t
