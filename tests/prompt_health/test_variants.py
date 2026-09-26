"""Prompt health check variants (tools/prompt_health/variants.py): base = production bytes, every other variant differs
from base in the intended way only, anchors exist in the live production text."""
import importlib.util
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from harvest.astra_motion import prompts as PR  # noqa: E402
from harvest.couple import prompt as CP  # noqa: E402
from harvest.couple.params import CoupleParams  # noqa: E402


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, *rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


V = _load("ph_variants", ("tools", "prompt_health", "variants.py"))

REQ = {"schema": "astra-couple@v1", "mode": "F0", "request_no": 1, "cameras": ["cam_head"], "tip_now_m": [0.4, -0.3, 1.0]}
IMGS = {"cam_head": b"H", "cam_wrist_left": b"L", "cam_wrist_right": b"R"}


def test_grasp_base_is_production_bytes():
    text, order = V.grasp_prompt("base", "red mug")
    assert text == PR.GRASP_Q.format(views=PR.GRASP_VIEWS["all3"], tgt_name="red mug")
    assert order == ("head", "wrist_left", "wrist")


@pytest.mark.parametrize("v", V.GRASP_VARIANTS[1:])
def test_grasp_variants_differ_and_keep_schema(v):
    base, _ = V.grasp_prompt("base", "red mug")
    text, order = V.grasp_prompt(v, "red mug")
    assert text != base or v == "camrev" and order != ("head", "wrist_left", "wrist")
    for word in ("grasp_state", "evidence_view", "confidence", "red mug", "RIGHT"):
        assert word in text
    assert sorted(order) == sorted(("head", "wrist_left", "wrist"))


def test_grasp_nodef_removes_only_the_definition():
    base, _ = V.grasp_prompt("base", "red mug")
    nodef, _ = V.grasp_prompt("nodef", "red mug")
    assert "DEFINITION" in base and "DEFINITION" not in nodef
    assert len(base) - len(nodef) == len(V.GRASP_DEF_LINE)


def test_grasp_paraphrases_keep_the_definition_content():
    for v in V.GRASP_PARAPHRASES:
        text, _ = V.grasp_prompt(v, "green bottle")
        assert "CLOSED" in text and "overlap" in text and "wrist" in text


def test_grasp_optrev_reverses_enum_order():
    text, _ = V.grasp_prompt("optrev", "red mug")
    assert '"uncertain"|"not_grasped"|"grasped"' in text


def test_grasp_camrev_changes_labels_and_order():
    text, order = V.grasp_prompt("camrev", "red mug")
    assert text.index("Image 1: RIGHT wrist camera") >= 0
    assert order[0] == "wrist"


def test_couple_base_is_production_build_input():
    p = CoupleParams()
    assert V.couple_input("base", REQ, IMGS, p, "Put the red mug on the blue tray.") == \
        CP.build_input(REQ, IMGS, p, "Put the red mug on the blue tray.")


@pytest.mark.parametrize("v", [v for v in V.COUPLE_VARIANTS if v not in ("base", "camrev")])
def test_couple_variants_change_text_keep_request(v):
    p = CoupleParams()
    base = CP.build_input(REQ, IMGS, p, "T")[0]["content"][0]["text"]
    text = V.couple_input(v, REQ, IMGS, p, "T")[0]["content"][0]["text"]
    assert text != base
    i = text.index(CP.REQ_OPEN) + len(CP.REQ_OPEN)
    assert json.loads(text[i:text.index(CP.REQ_CLOSE)]) == REQ
    for key in ('"assessment"', '"command"', '"claims"', "delta_position_m"):
        assert key in text


def test_couple_def_and_v2_add_text_only():
    p = CoupleParams()
    base = CP.build_input(REQ, IMGS, p, "T")[0]["content"][0]["text"]
    d = V.couple_input("def", REQ, IMGS, p, "T")[0]["content"][0]["text"]
    v2 = V.couple_input("v2", REQ, IMGS, p, "T")[0]["content"][0]["text"]
    assert d.replace(V.COUPLE_DEFS, "") == base
    assert v2.replace(V.COUPLE_DEFS + V.COUPLE_FRAME, "") == base


def test_couple_camrev_reverses_image_order_only():
    p = CoupleParams()
    base = CP.build_input(REQ, IMGS, p, "T")[0]["content"]
    rev = V.couple_input("camrev", REQ, IMGS, p, "T")[0]["content"]
    assert base[0] == rev[0]
    labels = [c["text"] for c in rev[1:] if c["type"] == "input_text"]
    assert labels == ["cam_wrist_right:", "cam_wrist_left:", "cam_head:"]


def test_couple_optrev_keeps_the_same_option_sets():
    t, _, af = V.couple_template("optrev")
    assert "recovered | uncertain | failed | progressing | not_started" in t
    assert '"stop|edit|continue"' in af and '"high|medium|low"' in af


def test_frame_prompts():
    base = V.frame_prompt("prod", "Put the red mug on the blue tray.", "red mug")
    assert "x forward" not in base and "robot frame" in base
    assert "x forward" in V.frame_prompt("frame", "T", "red mug")
    assert "+x points away" in V.frame_prompt("frame_para", "T", "red mug")


def test_sha12_is_stable():
    assert V.sha12("abc") == "ba7816bf8f01"
