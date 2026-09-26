"""Paired effort comparison: re-ask saved call inputs (same prompt text and images) and score the new command against
the call's stored truth, next to the original answer's score."""
import json

from harvest.astra_motion.truth import Rep
from harvest.astra_solo import reask as RA
from harvest.astra_solo.truth import ASSESS


def _episode(tmp_path):
    ep = tmp_path / "s0"
    calls = [{"call": 0, "site": 1, "attempt": 0, "valid": True, "phase_truth": "approach",
              "truth": {"tgt_xyz": [0.45, -0.20, 0.90], "place_xyz": [0.45, -0.38, 0.86], "holding": False,
                        "tcp": [0.35, -0.25, 1.10], "grip_w": 0.107},
              "parsed": {"command": {"mode": "eef", "position_m": [0.48, -0.20, 1.0], "gripper": "keep"}},
              "score": {"xy_err_mm": 30.0}},
             {"call": 1, "site": 2, "attempt": 0, "valid": True, "phase_truth": "after", "truth": {}, "score": None}]
    (ep / "calls" / "c000").mkdir(parents=True)
    (ep / "calls" / "c000" / "prompt.txt").write_text("PROMPT", encoding="utf-8")
    (ep / "calls" / "c000" / "img1_head_camera.png").write_bytes(b"H")
    (ep / "calls" / "c000" / "img2_right_wrist_camera.png").write_bytes(b"W")
    (ep / "result.json").write_text(json.dumps({"seed": 0, "variant": "standard", "calls": calls}))
    return ep


class Fixed:
    name = "fixed"

    def __init__(self):
        self.seen = []

    def ask(self, text, images, meta):
        self.seen.append((text, images))
        return Rep(json.dumps({"assessment": ASSESS, "command": {"mode": "eef", "position_m": [0.455, -0.20, 1.0],
                                                                  "gripper": "keep"}, "reason": "x"}))


def test_reask_pairs_scored_calls_only(tmp_path):
    ep = _episode(tmp_path)
    m = Fixed()
    rows = RA.reask([str(ep)], m, max_calls=10)
    assert len(rows) == 1 and rows[0]["orig_xy_err_mm"] == 30.0 and abs(rows[0]["new_xy_err_mm"] - 5.0) < 1e-6
    assert m.seen[0][0] == "PROMPT" and [lab for lab, _ in m.seen[0][1]] == ["head camera", "right wrist camera"]


def test_edit_goal_is_measured_tcp_plus_delta(tmp_path):
    goal = RA.goal_of({"mode": "edit", "delta_m": [0.05, 0.0, 0.0]}, {"tcp": [0.40, -0.20, 1.0]})
    assert goal == [0.45, -0.20, 1.0]
