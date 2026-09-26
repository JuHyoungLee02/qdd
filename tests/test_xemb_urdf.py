"""tools/xemb/urdf_fk.py: generic URDF forward kinematics (revolute / prismatic / fixed, mimic joints), link poses
relative to a chosen base link, and visual mesh references."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from xemb import urdf_fk as U  # noqa: E402

URDF = """<robot name="t">
  <link name="world"/>
  <link name="base"/>
  <link name="l1"><visual><origin xyz="0 0 0.05" rpy="0 0 0"/><geometry><mesh filename="package://p/m1.stl" scale="0.001 0.001 0.001"/></geometry></visual></link>
  <link name="l2"/>
  <link name="f"/>
  <joint name="w" type="fixed"><parent link="world"/><child link="base"/><origin xyz="0 0 1"/></joint>
  <joint name="j1" type="revolute"><parent link="base"/><child link="l1"/><origin xyz="0 0 0.1"/><axis xyz="0 0 1"/></joint>
  <joint name="j2" type="prismatic"><parent link="l1"/><child link="l2"/><origin xyz="0.2 0 0"/><axis xyz="1 0 0"/></joint>
  <joint name="jm" type="revolute"><parent link="l2"/><child link="f"/><origin xyz="0.1 0 0"/><axis xyz="0 0 1"/><mimic joint="j1" multiplier="2"/></joint>
</robot>"""


def test_fk_revolute_prismatic_relative_to_base():
    m = U.Urdf(URDF)
    T = m.poses({"j1": np.pi / 2, "j2": 0.05}, base="base")
    assert np.allclose(T["base"], np.eye(4))
    assert np.allclose(T["l1"][:3, 3], [0, 0, 0.1])
    # l2 = l1 + R(90 deg about z) @ (0.2 + 0.05, 0, 0) -> (0, 0.25, 0.1)
    assert np.allclose(T["l2"][:3, 3], [0, 0.25, 0.1], atol=1e-9)


def test_mimic_joint_follows_its_leader():
    m = U.Urdf(URDF)
    T = m.poses({"j1": 0.3, "j2": 0.0}, base="base")
    ang = np.arctan2(T["f"][1, 0], T["f"][0, 0])
    assert np.isclose(ang, 0.3 + 2 * 0.3)


def test_visuals_listed_with_origin_and_scale():
    m = U.Urdf(URDF)
    v = m.visuals()
    assert v[0]["link"] == "l1" and v[0]["file"] == "package://p/m1.stl"
    assert np.allclose(v[0]["scale"], [0.001] * 3) and np.allclose(v[0]["T"][:3, 3], [0, 0, 0.05])
