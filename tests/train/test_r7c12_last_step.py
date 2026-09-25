"""R7 cycle 12 D3 (canon §77): the M4 (b) category line `last_step: <category>` is part of the DecCall state in
training exactly as at runtime, derived in the training data from the recorded episode's own post-step check;
the prompt/state format version is bumped so an old checkpoint is refused."""
import json

import pytest

from harvest import deccall_snap as DS
from harvest.clients.jevl import question_text
from harvest.serialize import SERIALIZER_VERSION
from harvest.train import stagea_data as D


def _pool_line(k, phase, pred, seed=2000):
    """cli_pool format (0.33 s snapshots, no `verify`)."""
    return {"seed": seed, "kind": "P1", "split": "fit", "k": k, "ds_id": f"ds{k}", "phase": phase, "decision": True,
            "text_state": "t_state: f1\nrobot: x", "state": {"present": ["o3", "o5"]}, "pred": pred,
            "images": {"cam_head": f"img/ep{seed}/k{k:03d}_cam_head.jpg"}, "oracle": None}


HOLD = {"gripper_open": False, "holding(o3)": True, "lifted(o3)": True}
LOST = {"gripper_open": False, "holding(o3)": False, "lifted(o3)": False}  # T1 expectation of 'lift' broken


def test_format_version_bumped():
    assert SERIALIZER_VERSION == "ser-A-min-2"


def test_pool_lines_get_the_post_step_category_from_their_own_recorded_predicates():
    lines = [_pool_line(0, "lift", HOLD), _pool_line(1, "lift", HOLD), _pool_line(2, "lift", LOST),
             _pool_line(3, "carry", LOST)]
    DS.annotate_last_step(lines)
    # first step: nothing finished; k1: 'lift' expectations hold; k2: holding lost in 'lift' (T1) -> CONTRADICT;
    # k3: the step changed phase (lift -> carry): no expectation check, as the runtime (core._boundary)
    assert [ln["last_step"] for ln in lines] == ["none", "OK", "CONTRADICT", "OK"]


def test_r2_lines_use_the_recorded_verify_prev_step():
    ln = {"phase": "retreat", "verify": {"truth": {}, "prev_step": {
        "k0": 20, "phase": "retreat", "violations": ["on_tp"], "holds": {}, "expected_after": []}}}
    assert DS.last_step_of(ln) == "DEVIATE"  # world-side (T2) expectation false
    ln2 = {"phase": "carry", "verify": {"truth": {}, "prev_step": {
        "k0": 20, "phase": "carry", "violations": ["holding_t", "lifted_t"], "holds": {}, "expected_after": []}}}
    assert DS.last_step_of(ln2) == "CONTRADICT"  # a robot-side (T1) expectation false wins
    ln3 = {"phase": "carry", "verify": {"truth": {}}}  # first decision frame: no previous step
    assert DS.last_step_of(ln3) == "none"
    ln4 = {"phase": "carry", "verify": {"truth": {}, "prev_step": {"k0": 0, "phase": "lift",
                                                                    "violations": ["holding_t"]}}}
    assert DS.last_step_of(ln4) == "OK"  # phase changed inside the step


def test_training_items_carry_the_same_line_as_the_runtime_request():
    from harvest.runtime.models import build_live_request
    lines = [_pool_line(0, "lift", HOLD), _pool_line(1, "lift", LOST)]
    src = D.FnSource(lambda line, q, keys: ({keys[0]}, False))
    items = D.build_items(lines, src)
    by_k = {}
    for it in items:
        by_k.setdefault(it["k"], it)
    state1 = by_k[1]["text"].split("\n\nQuestion")[0]
    assert state1.split("\n")[-1] == "last_step: CONTRADICT"
    assert by_k[0]["text"].split("\n\nQuestion")[0].split("\n")[-1] == "last_step: none"
    raw = {"grip": {"pos": [0.3, -0.1, 0.25], "w": 0.07, "effort": 5.0},
           "objs": {k: {"pos": [0.4, -0.2, 0.05], "quat": [1, 0, 0, 0], "he": [0.03, 0.03, 0.05]} for k in ("o3", "o5")},
           "contacts": [], "support": {}}
    req, _ = build_live_request(1, "lift", "t_state: f1\nrobot: x", ["o3", "o5"], raw, state="IMG",
                                last_step="CONTRADICT")
    assert req["state"].split("\n")[-1] == "last_step: CONTRADICT"
    with pytest.raises(ValueError):
        build_live_request(1, "lift", "t", ["o3", "o5"], raw, last_step="WHATEVER")


def test_stage_a_prompt_config_records_the_format_and_old_runs_are_refused(tmp_path):
    from types import SimpleNamespace

    from harvest.eval import common as C
    from harvest.train.stagea_train import prompt_config
    pc = prompt_config([{"image": "x.jpg"}], SimpleNamespace(state="S1", step_cm=0.1))
    assert pc["serializer"] == "ser-A-min-2"
    run = tmp_path / "run"
    (run / "adapter").mkdir(parents=True)
    (run / "adapter" / "adapter_config.json").write_text("{}")
    old = {k: v for k, v in pc.items() if k != "serializer"}
    old["files_sha"] = {"harvest/deccall_snap.py": "000000000000"}
    (run / "config.json").write_text(json.dumps({"prompt_config": old}))
    with pytest.raises(ValueError, match="ser-A-min-2"):
        C.training_prompt_config(str(run / "adapter"))
    (run / "config.json").write_text(json.dumps({"prompt_config": pc}))
    assert C.training_prompt_config(str(run / "adapter"))["serializer"] == "ser-A-min-2"


def test_fused_check_prompt_refuses_an_old_stage_b_checkpoint_with_a_clear_message():
    pytest.importorskip("torch")  # check_prompt reads stageb_train.PROMPT_FILES (imports torch)
    from harvest.runtime.fused_model import check_prompt
    from harvest.train import stageb_data as SB
    from harvest.runtime.fused_model import CAMS
    cam = SB.CAMERA_LAYOUT + ":" + "|".join(lab for _, lab in CAMS)
    old = {"camera": [cam], "state": "IMG", "system_sha": "x", "files_sha": {"harvest/deccall_snap.py": "0" * 12}}
    with pytest.raises(ValueError, match="serializer"):
        check_prompt(old, strict=True)
    got = check_prompt(old, strict=False)
    assert "serializer_ok" in got["mismatch"]
