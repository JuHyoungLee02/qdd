import importlib

import numpy as np
import pytest

from harvest.l9 import hcam9 as HC
from harvest.l9 import robot9 as R9

URDF = """<?xml version="1.0" ?>
<robot name="panda">
  <link name="panda_link7"><visual><geometry><mesh filename="package://franka_description/meshes/visual/link7.dae"/></geometry></visual></link>
  <link name="panda_link8"/>
  <joint name="panda_joint8" type="fixed"><parent link="panda_link7"/><child link="panda_link8"/></joint>
  <link name="panda_hand"/>
  <joint name="panda_finger_joint2" type="prismatic"><parent link="panda_hand"/><child link="f2"/>
    <mimic joint="panda_finger_joint1"/>
  </joint>
</robot>
"""


def test_urdf_text_adds_ee_frame_and_absolute_meshes():
    t = R9.franka_urdf_text(URDF, "/isaac/franka_description/")
    assert "package://" not in t and "/isaac/franka_description/meshes/visual/link7.dae" in t
    assert '<link name="panda_link8"><inertial>' in t
    assert f'<link name="{R9.EE_BODY}">' in t and f'<child link="{R9.EE_BODY}"/>' in t
    assert "<mimic" not in t
    assert 'rpy="3.141592654 0 0"' in t and t.rstrip().endswith("</robot>") and t.count("</robot>") == 1
    with pytest.raises(ValueError):
        R9.franka_urdf_text("<robot></robot>", "/x")


def test_finger_width_map():
    assert R9.franka_width_to_joint(0.08) == pytest.approx(0.04)
    assert R9.franka_width_to_joint(0.2) == pytest.approx(0.04)
    assert R9.franka_width_to_joint(-0.01) == 0.0
    assert R9.franka_joint_to_width(R9.franka_width_to_joint(0.05)) == pytest.approx(0.05)


def test_wrist_mount_looks_at_the_finger_tips():
    pos, q = R9.wrist_mount()
    R = HC.quat_to_R(q)
    f = np.asarray(R9.WRIST_LOOK_AT) - np.asarray(pos)
    assert np.allclose(R[:, 0], f / np.linalg.norm(f))
    assert np.linalg.det(R) == pytest.approx(1.0)


def test_head_mount_default_is_the_spec_default():
    pos, q = R9.head_mount_default()
    assert pos == pytest.approx((0.0, -0.48, 1.21))
    assert HC.pitch_pan(HC.quat_to_R(q)) == pytest.approx((68.0, 30.0))


def test_prompt_swaps_hit_every_request_once():
    from harvest.astra_solo import prompts as V2
    from harvest.astra_solo import pt_prompts as PT
    for text in (V2.STATIC, PT.STATIC):
        for a, b in R9.prompt_swaps("franka_mast")[:3]:
            assert text.count(a) == 1, a[:40]
        out = R9.swap_text(text, "franka_mast")
        assert "AI Worker" not in out and "10.7 cm" not in out and "Franka Emika Panda" in out
        assert "Fully open pad gap 8.0 cm" in out and "mast on the robot's stand" in out
    assert R9.prompt_swaps("ffw_sg2") == [] and R9.swap_text("x", "ffw_sg2") == "x"


def test_apply_prompts_rebinds_and_ffw_is_noop():
    from harvest.astra_solo import prompts as V2
    old = V2.STATIC
    try:
        assert R9.apply_prompts("ffw_sg2") == []
        done = R9.apply_prompts("franka_mast")
        assert "harvest.astra_solo.prompts" in done and "harvest.astra_solo.pt_prompts" in done
        assert "Franka" in V2.STATIC
    finally:
        for m in R9.PROMPT_MODULES:  # undo for the other tests (module reload restores STATIC)
            importlib.reload(importlib.import_module(m))
    assert V2.STATIC == old or "AI Worker" in importlib.import_module("harvest.astra_solo.prompts").STATIC


def test_combo_tag_and_ep_dir():
    from harvest.l9.collect9 import combo_tag
    from harvest.l9.run9 import ep_dir
    row = {"seed": 7, "arm": "right", "family": "shelf_front", "def": "d1", "split": "train"}
    assert combo_tag(row) == ""
    assert combo_tag(dict(row, hcam="rand")) == "ffw_sg2/rand"
    assert combo_tag(dict(row, robot="franka_mast")) == "franka_mast/std"
    assert combo_tag(dict(row, hcam="coin")) in ("", "ffw_sg2/rand")
    assert ep_dir("/o", row).endswith("d1_s7_right")
    assert ep_dir("/o", dict(row, robot="franka_mast")).endswith("d1_s7_right_franka_mast")
