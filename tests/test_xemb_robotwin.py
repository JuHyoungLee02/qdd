"""tools/xemb/src_robotwin.py: world -> robot base transform (embodiments/aloha-agilex.yml robot_pose) and names."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from xemb import src_robotwin as R  # noqa: E402


def test_aloha_base_frame_is_forward_left_up():
    # the base sits at world (0, -0.65, 0) facing world +y
    assert np.allclose(R.world_to_base([0, -0.65, 0], "aloha-agilex"), [0, 0, 0], atol=1e-3)
    p = R.world_to_base([0, -0.35, 0.8], "aloha-agilex")  # 30 cm in front of the base, 0.8 m up
    assert np.allclose(p, [0.30, 0.0, 0.8], atol=2e-3)
    q = R.world_to_base([-0.2, -0.65, 0], "aloha-agilex")  # world -x = robot left
    assert np.allclose(q, [0.0, 0.2, 0.0], atol=2e-3)


def test_object_name_from_scene_info():
    assert R._obj_name("060_kitchenpot/base0") == "kitchenpot"
    assert R._obj_name("021_cup/base2") == "cup"
