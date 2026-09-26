"""Controller ruling PH-A 2 (ser-A-min-3, plan 2026-09-26 Task 12): every checkpoint prompt_config records the DecCall
format -- serializer version and the (b) `last_step` categories -- and the runtime check verifies both."""
from types import SimpleNamespace

import pytest

from harvest.serialize import LAST_STEP_VALUES, SERIALIZER_VERSION, format_record
from harvest.train.stagea_train import format_checks, prompt_config


def test_format_record_and_stage_a_prompt_config():
    assert format_record() == {"serializer": "ser-A-min-3",
                               "last_step_values": ["none", "OK", "LAG", "DEVIATE", "CONTRADICT"]}
    pc = prompt_config([{"image": "x.jpg"}], SimpleNamespace(state="S1", step_cm=0.1))
    assert pc["serializer"] == SERIALIZER_VERSION and pc["last_step_values"] == list(LAST_STEP_VALUES)
    assert format_checks(pc) == {"serializer_ok": True, "last_step_ok": True}


def test_format_checks_refuse_missing_or_changed_categories_and_other_serializer():
    pc = format_record()
    assert format_checks({k: v for k, v in pc.items() if k != "last_step_values"})["last_step_ok"] is False
    assert format_checks({**pc, "last_step_values": ["none", "OK", "DEVIATE", "CONTRADICT"]})["last_step_ok"] is False
    assert format_checks({**pc, "last_step_values": list(reversed(LAST_STEP_VALUES))})["last_step_ok"] is False
    assert format_checks({**pc, "serializer": "ser-A-min-2"}) == {"serializer_ok": False, "last_step_ok": True}


def test_stage_b_prompt_configs_record_the_format_and_check_prompt_verifies_it():
    pytest.importorskip("torch")  # stageb_train / check_prompt import torch
    from harvest.runtime.fused_model import CAMS, check_prompt
    from harvest.train import stageb_data as D
    from harvest.train.stageb_train import prompt_config as pc_b, prompt_config_t
    ims = [[lab, f"{c}.jpg"] for c, lab in CAMS]
    smp = [{"context": {"text": "x", "images": ims}}]
    for pc in (pc_b(smp, "IMG"), prompt_config_t(smp, "IMG", D.CAMERA_LAYOUT,
                                                 bins={"version": "se2e-motion@v1", "arm_speed": [0.2, 0.6],
                                                       "grip_rate": 0.176})):
        assert pc["serializer"] == SERIALIZER_VERSION and pc["last_step_values"] == list(LAST_STEP_VALUES)
        assert check_prompt(pc, strict=True)["mismatch"] == []
        bad = {**pc, "last_step_values": ["none", "OK"]}
        with pytest.raises(ValueError, match="last_step_ok"):
            check_prompt(bad, strict=True)
