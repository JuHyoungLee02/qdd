"""Synchronous Astra-solo episode on the kinematic fake world: the ground-truth model succeeds through the eef interface,
garbage ends as a schema failure, the prompt carries the v2 content (definitions, axis line, camera poses, legend of
the drawn elements only) and never object ground truth, and every call is saved with its scoring truth."""
import json

import numpy as np

from harvest.astra_solo import episode as E
from harvest.astra_solo import prompts as PR
from harvest.astra_solo.truth import SoloTruth

from astra_motion.fakeworld import FakeWorld, GarbageModel


def test_small_shortfall_is_load_sag_not_blocked():
    """P107: a move that ends ~1 cm short while carrying (load sag) is not reported as BLOCKED."""
    for kind in ("timeout", "settled"):
        s = E.outcome({"event": kind, "err_mm": 10.8})
        assert "BLOCKED" not in s and "sag" in s and "11 mm" in s
    assert E.outcome({"event": "timeout", "err_mm": 40.0}).startswith("BLOCKED")
    assert E.outcome({"event": "settled", "err_mm": 22.0}).startswith("stopped 22 mm short")


class ErrModel:
    name = "err"

    def __init__(self, error, status=None):
        self.error, self.status, self.n = error, status, 0

    def ask(self, text, images, meta):
        from harvest.astra_motion.truth import Rep
        self.n += 1
        r = Rep("")
        r.error, r.status = self.error, self.status
        return r


def test_insufficient_quota_is_fatal_at_once():
    import pytest
    w = FakeWorld()
    m = ErrModel("http_429", '{"error": {"code": "insufficient_quota"}}')
    with pytest.raises(E.ApiStop):
        E.run_episode(w, m, seed=1, task="mug_tray")
    assert m.n == 1


def test_three_empty_or_error_answers_stop_the_run():
    import pytest
    w = FakeWorld()
    m = ErrModel("timeout")
    with pytest.raises(E.ApiStop):
        E.run_episode(w, m, seed=1, task="mug_tray")
    assert m.n == E.MAX_API_ERR_RUN


def test_stage_caps_end_early_without_changing_the_prompt():
    """Prereg change 3: the runner ends an episode after stop_calls call sites or stop_motion_s of motion, while the
    prompt still states the registered 40 calls / 180 s (so earlier episodes stay comparable)."""
    w = FakeWorld()
    cap = Capture(SoloTruth(w))
    res = E.run_episode(w, cap, seed=3, task="mug_tray", stop_calls=2)
    assert res["end_reason"] == "stage_cap_calls" and res["n_sites"] == 2
    assert "Call 1 of at most 40" in cap.sent[0][0] and "of 180 s" in cap.sent[0][0]
    w2 = FakeWorld()
    res2 = E.run_episode(w2, SoloTruth(w2), seed=3, task="mug_tray", stop_motion_s=3.0)
    assert res2["end_reason"] == "stage_cap_motion" and 3.0 <= res2["sim_t"] < 4.0


class Capture:
    """Wraps a model and keeps what it was sent."""

    def __init__(self, m):
        self.m, self.name, self.sent = m, m.name, []

    def ask(self, text, images, meta):
        self.sent.append((text, [lab for lab, _ in images], meta))
        return self.m.ask(text, images, meta)


def test_truth_model_succeeds_with_few_calls(tmp_path):
    w = FakeWorld()
    res = E.run_episode(w, SoloTruth(w), seed=3, task="mug_tray", out_dir=str(tmp_path / "ep"))
    assert res["success"], (res["end_reason"], res["fail_stage"], res["history"][-3:])
    assert res["n_calls"] <= 10 and res["n_invalid"] == 0 and res["fail_stage"] is None
    assert res["first_close"]["err_mm"] < 6.0
    saved = json.load(open(tmp_path / "ep" / "result.json"))
    assert saved["success"] and saved["prompt_id"] == PR.PROMPT_ID
    c0 = sorted((tmp_path / "ep" / "calls").glob("c000*"))[0]
    assert (c0 / "prompt.txt").exists() and len(list(c0.glob("img*.png"))) == 2
    assert "truth" in saved["calls"][0] and "tgt_xyz" in saved["calls"][0]["truth"]


def test_garbage_model_ends_as_schema_failure():
    w = FakeWorld()
    res = E.run_episode(w, GarbageModel(), seed=1, task="mug_tray")
    assert res["end_reason"] == "schema" and not res["success"]
    assert res["n_invalid"] == res["n_calls"] == 2 * E.MAX_INVALID_RUN  # one repair per call site


def test_prompt_has_v2_content_and_no_object_truth():
    w = FakeWorld()
    cap = Capture(SoloTruth(w))
    E.run_episode(w, cap, seed=3, task="mug_tray", max_calls=2)
    text, labels, meta = cap.sent[0]
    assert labels == ["head camera", "right wrist camera"]
    for must in ("x forward", "y to the robot's left", "z up", "grasped =", "released =", "placed =",
                 "looking along", "image right", "WHITE GRID", "DROP LINE", "waits for your answer"):
        assert must in text, must
    assert "arrow" not in text.lower()  # no arrows are drawn, so the legend must not describe any
    st = w.status()
    for k, c in st["obj"].items():  # object ground-truth coordinates never reach the prompt
        assert f"{c[0]:.3f}" not in text and f"{c[0]:.2f}, {c[1]:.2f}" not in text


def test_history_reports_measured_results():
    w = FakeWorld()
    cap = Capture(SoloTruth(w))
    E.run_episode(w, cap, seed=3, task="mug_tray", max_calls=3)
    text = cap.sent[2][0]
    assert "YOUR COMMANDS SO FAR" in text and "eef" in text and "pad gap" in text
    assert "reached the target (error" in text


def test_call_truth_scores_the_approach_target():
    w = FakeWorld()
    res = E.run_episode(w, SoloTruth(w), seed=3, task="mug_tray")
    first = res["calls"][0]
    assert first["phase_truth"] == "approach"
    assert first["score"]["xy_err_mm"] < 1.0  # truth commands the object's own x, y


def test_motion_limit_ends_the_episode(monkeypatch):
    w = FakeWorld()

    class Hover:
        name = "hover"

        def ask(self, text, images, meta):
            from harvest.astra_motion.truth import Rep
            a = {"task_progress": {"verified_completed": [], "currently_attempting": "wait", "remaining": []},
                 "execution_status": "progressing", "evidence": "x", "evidence_view": "head", "confidence": "high"}
            z = 1.05 if meta["call"] % 2 else 1.10
            return Rep(json.dumps({"assessment": a, "command": {"mode": "eef", "position_m": [0.4, -0.25, z],
                                                                 "gripper": "keep"}, "reason": "r"}))
    res = E.run_episode(w, Hover(), seed=3, task="mug_tray", max_calls=100, motion_limit_s=5.0)
    assert res["end_reason"] == "motion_limit" and res["sim_t"] >= 5.0 and np.isfinite(res["sim_t"])
