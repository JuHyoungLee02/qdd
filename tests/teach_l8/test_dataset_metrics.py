"""Dataset build (control + perception QA, repeats, per-bucket counts, split guard) and offline metrics (validity,
action accuracy, approach-target xy error), and the training message layout = the runtime LocalVLM request layout."""
import json
import os

import httpx
import numpy as np
import pytest

from harvest.astra_motion.models import LocalVLM
from harvest.teach_l8 import collect as C
from harvest.teach_l8 import dataset as DS
from harvest.teach_l8 import metrics as M

from astra_motion.fakeworld import FakeWorld


@pytest.fixture(scope="module")
def eps(tmp_path_factory):
    root = tmp_path_factory.mktemp("col")
    for s in (10010, 10011, 10012):
        C.collect_episode(FakeWorld(), seed=s, task="mug_tray", variant="standard",
                          out_dir=str(root / "train" / "standard" / f"mug_tray_s{s}"), p=0.5, stop_calls=20)
    C.collect_episode(FakeWorld(), seed=3, task="mug_tray", variant="standard",
                      out_dir=str(root / "dev" / "standard" / "mug_tray_s3"), p=0.5, stop_calls=20)
    return str(root)


def test_build_train(eps, tmp_path):
    out = str(tmp_path / "train.jsonl")
    counts = DS.build(os.path.join(eps, "train"), out, split="train", seed=0)
    rows = [json.loads(x) for x in open(out)]
    ctrl = [r for r in rows if r["kind"] == "control"]
    aux = [r for r in rows if r["kind"] == "aux"]
    n_lab = sum(1 for d in DS.episode_dirs(os.path.join(eps, "train"))
                for x in open(os.path.join(d, "labels.jsonl")) if json.loads(x)["drop"] is None)
    assert counts["control_unique"] == n_lab == len({r["id"] for r in ctrl})
    assert counts["control_rows"] == len(ctrl) == sum(DS.repeat_of(r) for r in DS.dedup(ctrl))
    assert counts["aux_rows"] == len(aux) == n_lab
    for r in aux:
        a = json.loads(r["answer"])
        assert len(a["xy"]) == 2 and len(r["images"]) == 1 and r["images"][0].endswith("img1_head_camera.png")
    for r in ctrl:
        assert len(r["images"]) == 2 and os.path.exists(r["prompt_path"])
        assert DS.repeat_of(r) >= 1
    assert sum(counts["by_step"].values()) == n_lab
    with pytest.raises(ValueError):
        DS.build(os.path.join(eps, "dev"), str(tmp_path / "x.jsonl"), split="train", seed=0)


def test_repeat_rule():
    assert DS.repeat_of({"step": "above_target", "prev_kind": "start"}) == 2
    assert DS.repeat_of({"step": "descend_close", "prev_kind": "noise"}) == 3
    assert DS.repeat_of({"step": "carry_over", "prev_kind": "clean"}) == 1
    assert DS.repeat_of({"step": "reopen", "prev_kind": "empty_close"}) == 2


def test_messages_match_runtime_request(eps, tmp_path):
    DS.build(os.path.join(eps, "dev"), str(tmp_path / "dev.jsonl"), split="dev", seed=0)
    r = next(json.loads(x) for x in open(tmp_path / "dev.jsonl") if json.loads(x)["kind"] == "control")
    sent = {}

    def handler(req):
        sent["body"] = json.loads(req.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}], "model": "m"})

    vlm = LocalVLM("http://x", "m", "t", transport=httpx.MockTransport(handler))
    text = open(r["prompt_path"], encoding="utf-8").read()
    ims = [(lab, open(p, "rb").read()) for lab, p in zip(DS.IMAGE_LABELS, r["images"])]
    vlm.ask(text, ims, {})
    got = sent["body"]["messages"][0]["content"]
    want = DS.user_content(text, len(ims))
    assert [c["type"] for c in got] == [("image_url" if c["type"] == "image" else c["type"]) for c in want]
    assert [c.get("text") for c in got if c["type"] == "text"] == [c["text"] for c in want if c["type"] == "text"]


def _row(step="above_target", phase="approach"):
    return {"step": step, "phase": phase, "gt": {"tgt": [0.42, -0.2, 0.9], "place": [0.44, -0.38, 0.86],
                                                 "tcp": [0.34, -0.25, 1.1]},
            "ex_target": [0.34, -0.25, 1.1],
            "answer": json.dumps({"command": {"mode": "eef", "position_m": [0.42, -0.2, 1.0], "gripper": "keep"}})}


def _reply(cmd):
    return json.dumps({"assessment": {"task_progress": {"verified_completed": [], "currently_attempting": "x",
                                                        "remaining": []}, "execution_status": "progressing",
                                      "evidence": "", "evidence_view": "both", "confidence": "high"},
                       "command": cmd, "reason": ""})


def test_scores():
    s = M.score(_row(), _reply({"mode": "eef", "position_m": [0.45, -0.16, 1.0], "gripper": "keep"}))
    assert s["valid"] and s["action_ok"] and abs(s["approach_xy_mm"] - 50.0) < 0.1
    e = M.score(_row(), _reply({"mode": "edit", "delta_m": [0.08, 0.05, 0.0], "gripper": "close"}))
    assert not e["action_ok"] and abs(e["approach_xy_mm"] - 0.0) < 0.1
    bad = M.score(_row(), "no json here")
    assert not bad["valid"] and bad["approach_xy_mm"] is None and not bad["action_ok"]
    c = M.score(_row("carry_over", "carry"), _reply({"mode": "eef", "position_m": [0.42, -0.2, 1.0],
                                                     "gripper": "keep"}))
    assert c["approach_xy_mm"] is None and c["carry_xy_mm"] is not None
    g = M.score(_row(), _reply({"mode": "gripper", "gripper": "close"}))
    assert g["approach_xy_mm"] is None and g["approach_move"] is False


def test_summary():
    sc = [{"valid": True, "action_ok": True, "approach_xy_mm": v, "approach_move": True, "episode": "a",
           "carry_xy_mm": None, "goal_err_mm": 1.0} for v in (10, 20, 30, 40)]
    sc.append({"valid": False, "action_ok": False, "approach_xy_mm": None, "approach_move": False, "episode": "a",
               "carry_xy_mm": None, "goal_err_mm": None, "approach_row": True})
    for x in sc[:4]:
        x["approach_row"] = True
    s = M.summarize(sc)
    assert s["n"] == 5 and s["valid_rate"] == 0.8 and s["action_acc"] == 0.8
    assert s["approach_xy_median_mm"] == 25.0 and s["approach_move_share"] == 0.8
    assert s["approach_xy_p90_mm"] == pytest.approx(np.percentile([10, 20, 30, 40], 90))


def test_aux_score():
    assert M.aux_score({"answer": json.dumps({"xy": [0.4, -0.2]})}, '{"xy": [0.43, -0.16]}') == pytest.approx(50.0)
    assert M.aux_score({"answer": json.dumps({"xy": [0.4, -0.2]})}, "garbage") is None
