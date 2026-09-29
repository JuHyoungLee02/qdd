"""Checks of the dry-run helpers (not collected by the repo suite: run explicitly,
python -m pytest tools/couple_dry/test_couple_dry.py -o addopts="" --basetemp=D:/tools/scratch_qdd/couple_dry/pt)."""
import json
import math
import os
import sys
import types

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import analyze as AN  # noqa: E402
import dry_closed as DC  # noqa: E402


def test_split_args_strips_dry_options():
    rest, cfg = DC.split_args(["--model", "m", "--dry-fault-no", "4", "--dry-video-hz=2", "--out", "o"])
    assert rest == ["--model", "m", "--out", "o"]
    assert cfg["fault_no"] == 4 and cfg["video_hz"] == 2.0 and cfg["lat_median"] == 9.3


def test_target_latency_fault_only_even_episode_and_deterministic():
    cfg = DC.split_args([])[1]
    assert DC.target_latency(2, 3, cfg) == (25.0, True)
    assert DC.target_latency(1, 3, cfg)[1] is False
    assert DC.target_latency(1, 5, cfg) == DC.target_latency(1, 5, cfg)
    xs = [DC.target_latency(1, n, cfg)[0] for n in range(1, 2001)]
    assert abs(np.median(xs) - 9.3) < 0.3
    assert 12.5 < np.percentile(xs, 95) < 15.5


class _Rec:
    def __init__(self):
        self.t_send, self.t_done, self.t_first_token = 100.0, 101.5, 101.5
        self.meta, self.error, self.usage, self.output_text = {}, None, {"input_tokens": 3}, "{}"


def test_paced_client_pads_latency_and_logs(tmp_path):
    inner = types.SimpleNamespace(model="local:q", call=lambda *a: _Rec())
    slept = []
    log = tmp_path / "calls.jsonl"
    c = DC.PacedClient(inner, DC.split_args([])[1], str(log), "standard", sleep=slept.append)
    assert c.model == "local:q"
    rec = c.call([], "low", 10, {"episode": 2, "couple_no": 3})
    assert math.isclose(rec.t_done - rec.t_send, 25.0) and math.isclose(slept[0], 23.5)
    row = json.loads(log.read_text().splitlines()[0])
    assert row["fault"] is True and row["conc_at_start"] == 1 and DC.PacedClient._conc == 0


def test_inflight_violations():
    ok = [{"couple_kind": "send", "t": 0.0, "no": 1}, {"couple_kind": "answer", "t_deliver": 9.0, "no": 1},
          {"couple_kind": "send", "t": 9.0, "no": 2}, {"couple_kind": "timeout", "t": 29.1, "no": 2},
          {"couple_kind": "send", "t": 29.1, "no": 3}, {"couple_kind": "answer", "t_deliver": 34.0, "no": 2,
                                                          "late": True}]
    r = AN.inflight_violations(ok)
    assert r == {"sends": 3, "violations": 0, "timeouts_seen": 1}
    bad = [{"couple_kind": "send", "t": 0.0, "no": 1}, {"couple_kind": "send", "t": 1.0, "no": 2}]
    assert AN.inflight_violations(bad)["violations"] == 1


def test_action_steps_and_path(tmp_path):
    p = tmp_path / "a.jsonl"
    rows = [{"kind": "header"}] + [{"t": i, "action": [0.0] * 7 + [0.10]} for i in range(5)]
    rows += [{"t": 5, "action": [0.05] + [0.0] * 6 + [0.09]}]
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    s = AN.action_steps(str(p))
    assert s["grip_steps_gt5mm"] == 1 and math.isclose(s["grip_step_max_m"], 0.01)
    assert s["joint_steps_gt0p04"] == 1 and s["grip_frozen_max_s"] == 0.04
    side = os.path.join("L", "ours", "RUN", "dev0-P0-standard-e0.jsonl")
    assert AN.actions_path(side) == os.path.join("L", "actions", "RUN", "dev0-P0-standard-e0.jsonl")


def test_a_priv_contact_and_far():
    raw = {"objs": {"o3": {"pos": [0.3, 0.0, 0.0]}, "o5": {"pos": [0.0, 0.0, 0.0]}}, "grip": {"pos": [0.0, 0.0, 0.0]}}
    assert DC.a_priv(raw, "approach", False)[0] == 1.0
    assert DC.a_priv(raw, "close", False)[0] == 0.0
    assert DC.a_priv(raw, "carry", False)[0] == 0.0  # gripper at the place object
