"""R6 common: DecCall request with option-name variants, model resolution / fingerprint, outputs, vLLM command."""
import json
import os

import pytest

from harvest.eval import common


def _line():
    raw = {"grip": {"pos": [0.30, -0.10, 0.25], "w": 0.107, "effort": 0.0},
           "objs": {"o3": {"pos": [0.42, -0.30, 0.05], "quat": [1, 0, 0, 0], "he": [0.03, 0.03, 0.05]},
                    "o5": {"pos": [0.45, 0.10, 0.01], "quat": [1, 0, 0, 0], "he": [0.1, 0.1, 0.01]}},
           "contacts": [], "support": {}}
    return {"seed": 3, "kind": "P0", "k": 4, "t": 1.32, "ds_id": "ds4", "phase": "approach",
            "text_state": "t_state: f1\nstage: S1\nfacts: gripper_open=yes holding(o3)=no lifted(o3)=no",
            "state": {"present": ["o3", "o5"], "obs": {"raw": raw}}, "oracle": {"dir_xy": "SECRET"},
            "images": {"cam_head": "img/ep3/k004_cam_head.jpg", "cam_wrist_right": "img/ep3/k004_cam_wrist_right.jpg"}}


def test_request_has_the_five_decision_questions_and_no_oracle():
    req, shown = common.build_request(_line(), "A0")
    assert sorted(q for q, _ in shown.values()) == sorted(common.QUESTIONS)
    assert "SECRET" not in json.dumps(req)
    assert "geometry (robot base frame" in req["state"]  # S1 text


def test_variant_changes_names_only_and_keys_map_back():
    r0, s0 = common.build_request(_line(), "A0")
    r1, s1 = common.build_request(_line(), "A1")
    assert r0["state"] == r1["state"]
    for qid in s0:
        k0 = [o.key for o in s0[qid][1]]
        k1 = [o.key for o in s1[qid][1]]
        assert k0 == k1 and k1[-1] == "NONE_ESCALATE"
        assert list(r1["questions"][qid]["criteria"])[0].startswith("opt_")
        assert list(r1["questions"][qid]["criteria"].values()) == list(r0["questions"][qid]["criteria"].values())


def test_a2_names_are_stable_across_calls():
    _, a = common.build_request(_line(), "A2")
    _, b = common.build_request(_line(), "A2")
    assert [o.name for q in a for o in a[q][1]] == [o.name for q in b for o in b[q][1]]


def test_answers_to_keys():
    _, shown = common.build_request(_line(), "A1")
    qid = next(q for q in shown if shown[q][0] == "dir_z")
    opts = shown[qid][1]
    ans = {qid: {"choice": opts[1].name, "probabilities": {o.name: (0.7 if i == 1 else 0.1) for i, o in
                                                                 enumerate(opts)}, "confidence": 0.7}}
    out = common.answers_to_keys(ans, shown)
    assert out["dir_z"]["key"] == opts[1].key and out["dir_z"]["name"] == opts[1].name
    assert out["dir_z"]["probs"][opts[1].key] == 0.7


def test_images_for_layouts(tmp_path):
    d = tmp_path / "img" / "ep3"
    d.mkdir(parents=True)
    (d / "k004_cam_head.jpg").write_bytes(b"H")
    (d / "k004_cam_wrist_right.jpg").write_bytes(b"W")
    h = common.images_for(_line(), str(tmp_path), "H")
    hw = common.images_for(_line(), str(tmp_path), "HW")
    assert [x[1] for x in h] == [b"H"]
    assert [x[0] for x in hw] == ["head camera:", "right wrist camera (active arm):"] and hw[1][1] == b"W"


def test_resolve_model_kinds(tmp_path):
    assert common.resolve_model("zero-shot")["kind"] == "zero-shot"
    assert common.resolve_model("mock")["kind"] == "mock"
    m = tmp_path / "merged"
    m.mkdir()
    (m / "config.json").write_text("{}")
    (m / "model.safetensors").write_bytes(b"x" * 10)
    assert common.resolve_model(str(m))["kind"] == "merged"
    a = tmp_path / "best"
    a.mkdir()
    (a / "adapter_config.json").write_text("{}")
    assert common.resolve_model(str(a))["kind"] == "adapter"
    with pytest.raises(SystemExit):
        common.resolve_model(str(tmp_path / "nothing"))


def test_fingerprint_changes_with_weights(tmp_path):
    m = tmp_path / "m"
    m.mkdir()
    (m / "config.json").write_text("{}")
    (m / "model.safetensors").write_bytes(b"a" * 100)
    f1 = common.model_fingerprint(str(m))
    assert f1 == common.model_fingerprint(str(m))
    (m / "model.safetensors").write_bytes(b"b" * 100)
    assert common.model_fingerprint(str(m)) != f1


def test_training_prompt_config_from_merged_dir(tmp_path):
    run = tmp_path / "run"
    (run / "best").mkdir(parents=True)
    (run / "merged").mkdir()
    (run / "config.json").write_text(json.dumps({"args": {"state": "S1", "step_cm": 0.1},
                                                 "prompt_files_sha": {"a.py": "123"}}))
    (run / "merged" / "merge_info.json").write_text(json.dumps({"adapter": str(run / "best")}))
    pc = common.training_prompt_config(str(run / "merged"))
    assert pc["state"] == "S1" and pc["camera"] == ["H:cam_head"] and pc["files_sha"] == {"a.py": "123"}
    assert common.default_layout(pc) == "H"
    assert common.default_layout({"camera": ["HW:head camera:|right wrist camera (active arm):"]}) == "HW"
    assert common.default_layout(None) == "H"


def test_md_table():
    t = common.md_table(["a", "b"], [[1, 0.12345], ["x", None]])
    assert t.splitlines()[0] == "| a | b |" and "0.1235" in t and "| x | - |" in t


def test_vllm_command_has_the_canon_flags():
    cmd = common.vllm_cmd("/m", "name", 8200, util=0.3)
    s = " ".join(cmd)
    for f in ("--enable-prefix-caching", "raw_logprobs", "--seed 0", "--max-model-len 8192", '"image":2'):
        assert f in s, f


def test_write_outputs(tmp_path):
    common.write_outputs(str(tmp_path), "x", {"a": 1}, "# md")
    assert json.load(open(os.path.join(tmp_path, "x.json")))["a"] == 1
    assert open(os.path.join(tmp_path, "x.md"), encoding="utf-8").read().startswith("# md")
