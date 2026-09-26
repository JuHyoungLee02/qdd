"""astra-couple@v2 (plan 2026-09-26 Task 18, controller ruling T18b): the coupling's v2 prompt reproduces the E-ACC
adopted arm's bytes and id (tools/eacc/prompt_v2.py, PROMPT_ID 83fa03a5de19), options stay off by default, the id
covers every template part, and v1 stays selectable and unchanged."""
import hashlib
import importlib.util
import json
import os

import pytest

from harvest.couple import prompt as CP
from harvest.couple import prompt_v2 as V2
from harvest.couple.params import CoupleParams

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _eacc():
    spec = importlib.util.spec_from_file_location("eacc_prompt_v2_t18", os.path.join(ROOT, "tools", "eacc",
                                                                                     "prompt_v2.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


P2 = _eacc()
CAMS3 = ["cam_head", "cam_wrist_left", "cam_wrist_right"]
IMGS = {c: b"\xff\xd8" + c.encode() for c in CAMS3}
REQ = {"schema": "astra-couple@v2", "request_no": 4, "events": ["b_contradict", {"event": "m7_hard_t1"}, "zzz"],
       "since_last_request": {"previous_request": {"age_s": 9.3, "command": "continue",
                                                   "segment": {"now": "approach", "do": "none", "next": "descend"}},
                              "vla_tip_moved_m": [0.01, 0.0, -0.02], "vla_phases": ["approach", "descend"]}}
DRAWN = [None, {"head": {"ring", "trace", "next", "axes"}, "wrist": {"next"}, "axisguide": []},
         {"head": {"ring", "axes", "offset"}, "wrist": set(), "axisguide": []},
         {"head": set(), "wrist": None, "axisguide": []},
         {"head": {"ring", "next", "axes"}, "wrist": {"next", "offset"}, "axisguide": ["cam_head"]}]


def test_the_adopted_prompt_id_is_the_registered_one():
    assert P2.PROMPT_ID == "83fa03a5de19"
    assert V2.PROMPT_ID["F0"] == P2.PROMPT_ID == V2.variant_id("F0")
    assert V2.AXISGUIDE_ID == P2.AXISGUIDE_ID and V2.variant_id(axisguide=True) == P2.PROMPT_ID + "+ax" + P2.AXISGUIDE_ID


@pytest.mark.parametrize("drawn", DRAWN)
@pytest.mark.parametrize("cams", [CAMS3, ["cam_head", "cam_wrist_right"], ["cam_head"]])
@pytest.mark.parametrize("ctx", [True, False])
def test_v2_prompt_bytes_equal_the_registered_eacc_text(drawn, cams, ctx):
    req = dict(REQ) if ctx else {k: v for k, v in REQ.items() if k != "since_last_request"}
    imgs = {c: IMGS[c] for c in cams}
    a = V2.build(req, imgs, CAMS3, "Put the red mug on the blue tray.", horizon_s=9.34, drawn=drawn)
    b = P2.build_v2(req, imgs, CAMS3, "Put the red mug on the blue tray.", horizon_s=9.34, drawn=drawn)
    assert json.dumps(a).encode() == json.dumps(b).encode()


def test_options_campose_detail_and_extra_sentence_match_the_eacc_arms():
    cams = {c: {"R": [[0, -1, 0], [0, 0, -1], [1, 0, 0]], "t": [0.1, -0.2, 0.9]} for c in CAMS3}
    cp_a, cp_b = V2.campose_text(cams, CAMS3, 0.123), P2.campose_text(cams, CAMS3, 0.123)
    assert cp_a == cp_b
    kw = dict(horizon_s=9.3, drawn=DRAWN[1])
    a = V2.build(REQ, IMGS, CAMS3, "T", campose=cp_a, detail="low", extra=P2.GOALCHECK, **kw)
    b = P2.build_v2(REQ, IMGS, CAMS3, "T", campose=cp_b, detail="low", goalcheck=True, **kw)
    assert a == b
    assert V2.variant_id(extra=P2.GOALCHECK) == P2.PROMPT_ID + "+x" + P2.GOALCHECK_ID
    if hasattr(P2, "GOALCHECK2"):  # E-ACC prereg change 6 arm gc2 (47e6ff6): the same hook carries it
        assert (V2.build(REQ, IMGS, CAMS3, "T", extra=P2.GOALCHECK2, **kw)
                == P2.build_v2(REQ, IMGS, CAMS3, "T", goalcheck="gc2", **kw))
        assert V2.variant_id(extra=P2.GOALCHECK2) == P2.PROMPT_ID + "+x" + P2.GOALCHECK2_ID
    # default = no extra sentence, no detail field, no camera pose line
    txt = V2.build(REQ, IMGS, CAMS3, "T", **kw)[0]["content"]
    assert P2.GOALCHECK not in txt[0]["text"] and "Camera poses" not in txt[0]["text"]
    assert all("detail" not in c for c in txt)


def test_prompt_id_changes_when_any_part_changes():
    for mode in ("F0", "F1"):
        base = V2.parts(mode)
        assert V2.prompt_id_of(base, mode) == V2.PROMPT_ID[mode]
        seen = {V2.PROMPT_ID[mode]}
        for k, v in base.items():
            changed = dict(base)
            changed[k] = ({**v, "zz": "x"} if isinstance(v, dict) else v + "x")
            pid = V2.prompt_id_of(changed, mode)
            assert pid not in seen, k
            seen.add(pid)
    assert V2.PROMPT_ID["F0"] != V2.PROMPT_ID["F1"] and "+p" in V2.PROMPT_ID["F1"]
    assert V2.variant_id(extra="Check the target.") != V2.variant_id(extra="Check the place.")
    assert V2.variant_id(extra="") == V2.PROMPT_ID["F0"] and V2.extra_line("  ") == ""


def test_f1_template_names_six_keys_and_the_diff_form():
    t = V2.build({"request_no": 1}, {}, CAMS3, "T", mode="F1")[0]["content"][0]["text"]
    assert "six top-level keys" in t and '"diff": "keep|revise"' in t and CP.MODE_RULES["F1"] in t
    assert "No overlay is drawn" in t and "Cameras (each image is preceded by its name): ." in t


def test_v1_prompt_is_selectable_and_unchanged():
    # the v1 text / ids as committed before Task 18 (sha256 of the F0 / F1 builds pinned here)
    p = CoupleParams(prompt_version="v1")
    assert p.prompt_version == "v1" and CoupleParams().prompt_version == "v2"
    assert CP.PROMPT_ID == {"F0": hashlib.sha256((CP.TEMPLATE + CP.MODE_RULES["F0"] + CP.ANSWER_FORM["F0"])
                                                 .encode()).hexdigest()[:12],
                            "F1": hashlib.sha256((CP.TEMPLATE + CP.MODE_RULES["F1"] + CP.ANSWER_FORM["F1"])
                                                 .encode()).hexdigest()[:12]}
    assert CP.PROMPT_ID["F0"] == V1_ID_F0 and CP.PROMPT_ID["F1"] == V1_ID_F1
    t = CP.build_input({"request_no": 1}, IMGS, p, "T")[0]["content"][0]["text"]
    assert hashlib.sha256(t.encode()).hexdigest()[:12] == V1_TEXT_SHA


V1_ID_F0, V1_ID_F1, V1_TEXT_SHA = "18e9cc4ba239", "e0364b7fa0bc", "8fc6607f6c7e"  # computed at 0dd95ad


def test_params_prompt_version_guard():
    with pytest.raises(ValueError, match="prompt_version"):
        CoupleParams(prompt_version="v3")
    p = CoupleParams()
    assert p.axis_guide is False and p.extra_instruction == "" and p.to_json()["prompt_version"] == "v2"


def test_fix_m3_campose_and_detail_change_the_variant_id():
    base = V2.variant_id()
    ids = {base, V2.variant_id(campose=True), V2.variant_id(detail="low"), V2.variant_id(detail="high"),
           V2.variant_id(campose=True, detail="low")}
    assert len(ids) == 5 and V2.variant_id(campose=True) == base + "+cp"
    assert V2.variant_id(detail="low") == base + "+dlow" and V2.variant_id(detail=None) == base == "83fa03a5de19"
