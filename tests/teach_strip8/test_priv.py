"""E-PRIV8 (prereg_priv8.md): M1 = the minimal request + a request for the model's own table_z / obj_h estimates
(truth-supervised, omitted on half of the training rows); M3 = hand information in the TRAINING input with probability
p falling 1 -> 0 (0 over the last 40 % of the steps), minimal input at inference."""
import json

import numpy as np
import pytest

from harvest.astra_solo import schema as V2S
from harvest.teach_strip8 import priv as P
from harvest.teach_strip8 import strip as S

from teach_strip8.test_dataset import src  # noqa: F401 (fixture)


def test_m1_text_and_answer(src):  # noqa: F811
    d, p, rows = src
    v2 = open(rows[0]["call_dir"] + "/prompt_v2.txt", encoding="utf-8").read()
    m = S.minimal(v2)
    t = P.m1_text(m)
    assert P.EST_REQUEST in t and '"estimates": {"table_z": number, "obj_h": number}' in t
    assert t.replace(P.EST_REQUEST, "").replace(P.EST_JSON, P.PLAIN_JSON) == m
    with pytest.raises(ValueError):
        P.m1_text("no answer form")
    a = {"assessment": {"x": 1}, "command": {"mode": "stop"}, "reason": "r"}
    out = json.loads(P.m1_answer(json.dumps(a), {"table_z": 0.8123, "target_height_m": 0.095}))
    assert list(out)[0] == "estimates" and out["estimates"] == {"table_z": 0.812, "obj_h": 0.095}
    assert {k: v for k, v in out.items() if k != "estimates"} == a


def test_m1_answer_passes_the_runtime_validator():
    from harvest.astra_solo.pt_truth import ASSESS  # a valid assessment block
    a = {"assessment": ASSESS, "command": {"mode": "eef", "position_m": [0.4, -0.3, 1.0], "gripper": "keep"},
         "reason": "r"}
    parsed, err = V2S.validate(P.m1_answer(json.dumps(a), {"table_z": 0.85, "target_height_m": 0.1}))
    assert parsed is not None and err == []


def test_build_m1_and_m3(src, tmp_path):  # noqa: F811
    d, p, rows = src
    rows2 = [dict(r, est={"table_z": 0.85, "target_height_m": 0.095}) if r["kind"] == "control" else r for r in rows]
    q = tmp_path / "train_nd-xyz.jsonl"
    q.write_text("".join(json.dumps(r) + "\n" for r in rows2), encoding="utf-8")
    c = P.build(str(q), str(tmp_path / "o"), "train", "m1", seed=0)
    out = [json.loads(x) for x in open(tmp_path / "o" / "train_m1.jsonl")]
    assert len(out) == len(rows2) and c["control_rows"] == sum(r["kind"] == "control" for r in rows2)
    for a, b in zip(rows2, out):
        if a["kind"] == "aux":
            assert a == b
            continue
        t = open(b["prompt_path"], encoding="utf-8").read()
        v2 = open(a["call_dir"] + "/prompt_v2.txt", encoding="utf-8").read()
        ans = json.loads(b["answer"])
        assert (P.EST_REQUEST in t) == ("estimates" in ans) == b["m1_est"]
        assert t == (P.m1_text(S.minimal(v2)) if b["m1_est"] else S.minimal(v2))
    ev = P.build(str(q), str(tmp_path / "e"), "dev", "m1", seed=0)
    assert ev["est_share"] == 1.0
    c3 = P.build(str(q), str(tmp_path / "o"), "train", "m3", seed=0)
    out3 = [json.loads(x) for x in open(tmp_path / "o" / "train_m3.jsonl")]
    for a, b in zip(rows2, out3):
        if a["kind"] == "control":
            assert open(b["prompt_path"], encoding="utf-8").read() == S.minimal(
                open(a["call_dir"] + "/prompt_v2.txt", encoding="utf-8").read())
            assert b["alt_prompt_path"].endswith("prompt_v2.txt") and b["alt_images"][0].endswith("img1_head_camera.png")
    assert c3["control_rows"] == c["control_rows"]
    with pytest.raises(ValueError):
        P.build(str(q), str(tmp_path / "x"), "dev", "m3")


def test_schedule_and_curriculum_choice():
    assert P.p_hand(0.0) == 1.0 and abs(P.p_hand(0.3) - 0.5) < 1e-9 and P.p_hand(0.6) == 0.0 and P.p_hand(0.95) == 0.0
    rows = [{"kind": "control", "prompt_path": "min", "images": ["r", "w"], "alt_prompt_path": "full",
             "alt_images": ["g", "w"]}] * 400 + [{"kind": "aux", "prompt": "q", "images": ["r"]}]
    early = [P.choose(rows[0], k=0, i=i, total=1000, seed=0)["prompt_path"] for i in range(400)]
    late = [P.choose(rows[0], k=800, i=i, total=1000, seed=0)["prompt_path"] for i in range(400)]
    mid = [P.choose(rows[0], k=300, i=i, total=1000, seed=0)["prompt_path"] for i in range(2000)]
    assert set(early) == {"full"} and set(late) == {"min"} and abs(np.mean([m == "full" for m in mid]) - 0.5) < 0.05
    assert P.choose(rows[-1], k=0, i=0, total=1000, seed=0) == rows[-1]
    assert P.choose(rows[0], 5, 7, 1000, 0) == P.choose(rows[0], 5, 7, 1000, 0)


def test_curriculum_dataset_uses_choose(monkeypatch):
    from harvest.teach_l8 import train as T
    from harvest.teach_strip8 import train_curr as TC
    monkeypatch.setattr(T, "collate", lambda items, pad: [x["p"] for x in items])
    row = {"kind": "control", "prompt_path": "min", "images": ["r"], "alt_prompt_path": "full", "alt_images": ["g"]}
    enc = lambda r: {"p": r["prompt_path"], "n_answer": 1}  # noqa: E731
    TC.CurrMBData.total, TC.CurrMBData.seed = 100, 0
    ds = TC.CurrMBData([row] * 8, [list(range(8))] * 100, enc, 0)
    assert ds[0][0] == ["full"] * 8 and ds[80][0] == ["min"] * 8 and ds[0][2] == 8
    with pytest.raises(SystemExit):
        TC.main(["--data", "x", "--out", "y"])


def test_est_errors():
    rows = [{"id": "a", "kind": "control", "est": {"table_z": 0.8, "target_height_m": 0.1}},
            {"id": "b", "kind": "control", "est": {"table_z": 0.9, "target_height_m": 0.1}}]
    rep = {"a": {"text": json.dumps({"estimates": {"table_z": 0.81, "obj_h": 0.1}})}, "b": {"text": "nonsense"}}
    e = P.est_errors(rows, rep)
    assert e["n"] == 2 and e["n_est"] == 1 and abs(e["table_z_abs_median_mm"] - 10.0) < 1e-6 and e["obj_h_abs_median_mm"] == 0.0
