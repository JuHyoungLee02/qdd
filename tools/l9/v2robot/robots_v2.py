"""L9 v2 robot build specs (spec §12.2) + URDF preparation and TCP / pad measurement (pod: needs trimesh).

Every robot gets a prepared URDF under ASSET_ROOT/<robot>/ with an added fixed TCP link per arm ("<arm>_l9_tcp"):
origin = the pad centre the L9 executor targets, orientation = the AI Worker link7 convention (z axis points from the
fingers back to the wrist, i.e. z = -approach; y = the finger closing axis), so a top-down grasp is a pure-yaw TCP
quaternion on every robot. cuRobo configs (build_curobo9.py), reach maps and the Isaac USDs all read this URDF.

Licences (spec §9.2 / §12.10): FFW-SG2 = ROBOTIS ffw_description Apache-2.0 (URDF exported from the cyclo_lab USD the
sim uses); Franka = franka_ros 0.7.0 Apache-2.0 (cuRobo v0.8.0 bundled copy, LICENSE_ASSETS); R1 Pro = OpenGalaxea/
GalaxeaManipSim Apache-2.0 (galaxea_sim/assets/r1_pro/robot.urdf, commit abe7f51); G1 = unitree_ros g1_description
BSD-3-Clause (cuRobo v0.8.0 bundled copy g1_29dof_with_hand_rev_1_0.urdf, Dex3-1 hands)."""
from __future__ import annotations

import os
import re
import shutil

import numpy as np

ASSET_ROOT = "/data/harvest/assets_l9v2/robots"
CUROBO_ASSETS = "/data/harvest/l9v2/pylib/curobo/content/assets/robot"

_R7 = [f"arm_r_joint{i}" for i in range(1, 8)]
_L7 = [f"arm_l_joint{i}" for i in range(1, 8)]

ROBOTS = {
    "ffw_sg2": {
        "src_dir": "/data/newproj/rep_v3test/.urdf_export", "src_urdf": "ffw_sg2.urdf", "mesh_subdir": "meshes",
        "base": "arm_base_link",  # above lift_joint: the reach map is lift-invariant (world z = base z + lift)
        "lock_common": {"head_joint1": 0.69, "head_joint2": 0.0},
        "arms": {
            "right": {"joints": _R7, "parent": "ffw_sg2_follower_arm_r_link7", "approach": (0, 0, -1),
                      "tcp_rpy": (0.0, 0.0, 0.0), "fingers": ("gripper_r_rh_p12_rn_l2", "gripper_r_rh_p12_rn_r2"),
                      "grip_lock": {f"gripper_r_joint{i}": 0.0 for i in range(1, 5)},
                      "stow": {"arm_r_joint1": 0.75, "arm_r_joint4": -2.30},
                      "init": (-1.0511, -1.0975, 1.2281, -2.3934, 0.4838, 1.2356, 1.78)},  # scene.INIT_R_ARM, j7 inside the 0.03 margin
            "left": {"joints": _L7, "parent": "ffw_sg2_follower_arm_l_link7", "approach": (0, 0, -1),
                     "tcp_rpy": (0.0, 0.0, 0.0), "fingers": ("gripper_l_rh_p12_rn_l2", "gripper_l_rh_p12_rn_r2"),
                     "grip_lock": {f"gripper_l_joint{i}": 0.0 for i in range(1, 5)},
                     "stow": {"arm_l_joint1": 0.75, "arm_l_joint4": -2.30},
                     "init": (-1.0511, 1.0975, -1.2281, -2.3934, -0.4838, 1.2356, -1.78)}},  # arm.INIT_L_ARM (j7 margin)
        "tcp_rule": "ffw",  # = harvest.sim.scene._measure_finger_offsets: (tip + base) / 2 of the finger link2 bboxes
    },
    "franka": {
        "src_dir": f"{CUROBO_ASSETS}/franka_description", "src_urdf": "franka_panda.urdf", "mesh_subdir": "meshes",
        "base": "panda_link0", "lock_common": {},
        "arms": {
            "right": {"joints": [f"panda_joint{i}" for i in range(1, 8)], "parent": "panda_hand",
                      "approach": (0, 0, 1), "tcp_rpy": (np.pi, 0.0, 0.0),  # = robot9 panda_ee (pi about x)
                      "fingers": ("panda_leftfinger", "panda_rightfinger"),
                      "grip_lock": {"panda_finger_joint1": 0.04, "panda_finger_joint2": 0.04}, "stow": {},
                      "init": (0.0, -0.785, 0.0, -2.356, 0.0, 1.571, 0.785)}},  # robot9.INIT_Q
        "tcp_rule": "franka",  # = scene._measure_finger_offsets(robot=...): tip - robot9.PAD_LEN_M / 2
        "mesh_kind": "collision",  # the visual meshes are .dae (no collada in the Isaac python)
    },
    "r1pro": {
        "src_dir": f"{ASSET_ROOT}/src/gms/galaxea_sim/assets/r1_pro", "src_urdf": "robot.urdf", "mesh_subdir": "meshes",
        "base": "torso_link4",  # above the 4 torso joints: arms + ZED head camera are rigid on torso_link4
        "lock_common": {},
        "arms": {
            "right": {"joints": [f"right_arm_joint{i}" for i in range(1, 8)], "parent": "right_gripper_link",
                      "approach": (0, 0, -1), "tcp_rpy": (0.0, 0.0, 0.0),
                      "fingers": ("right_gripper_finger_link1", "right_gripper_finger_link2"),
                      "grip_lock": {"right_gripper_finger_joint1": None, "right_gripper_finger_joint2": None},
                      "stow": {}},
            "left": {"joints": [f"left_arm_joint{i}" for i in range(1, 8)], "parent": "left_gripper_link",
                     "approach": (0, 0, -1), "tcp_rpy": (0.0, 0.0, 0.0),
                     "fingers": ("left_gripper_finger_link1", "left_gripper_finger_link2"),
                     "grip_lock": {"left_gripper_finger_joint1": None, "left_gripper_finger_joint2": None},
                     "stow": {}}},
        "tcp_rule": "pad",  # pad centre: middle of the inner finger faces along the approach axis
        # finger prismatic axes are 0.45 deg off y in the source; cuRobo only takes axis-aligned joints
        "axis_fix": {"-0.0077873 0.99997 0": "0 1 0", "0.0077873 -0.99997 0": "0 -1 0"},
    },
    "g1": {
        "src_dir": f"{CUROBO_ASSETS}/g1", "src_urdf": "g1_29dof_with_hand_rev_1_0.urdf", "mesh_subdir": "meshes",
        "base": "torso_link",  # above the 3 waist joints (owner 10-02: base = link the arm hangs from)
        "lock_common": {},
        "arms": {
            "right": {"joints": [f"right_{n}_joint" for n in ("shoulder_pitch", "shoulder_roll", "shoulder_yaw",
                                                                 "elbow", "wrist_roll", "wrist_pitch", "wrist_yaw")],
                      "parent": "right_hand_palm_link", "approach": (1, 0, 0), "tcp_rpy": (0.0, -np.pi / 2, 0.0),
                      "fingers": ("right_hand_thumb_2_link", "right_hand_index_1_link", "right_hand_middle_1_link"),
                      "grip_lock": None, "stow": {}},
            "left": {"joints": [f"left_{n}_joint" for n in ("shoulder_pitch", "shoulder_roll", "shoulder_yaw",
                                                               "elbow", "wrist_roll", "wrist_pitch", "wrist_yaw")],
                     "parent": "left_hand_palm_link", "approach": (1, 0, 0), "tcp_rpy": (0.0, -np.pi / 2, 0.0),
                     "fingers": ("left_hand_thumb_2_link", "left_hand_index_1_link", "left_hand_middle_1_link"),
                     "grip_lock": None, "stow": {}}},
        "tcp_rule": "g1",  # Dex3-1 pinch synergy (hands_v2.py): TCP = pinch point at the synergy's open posture
    },
}


def tcp_link(arm: str) -> str:
    return f"{arm}_l9_tcp"


def prepared_dir(robot: str) -> str:
    return os.path.join(ASSET_ROOT, robot)


def prepared_urdf(robot: str) -> str:
    return os.path.join(prepared_dir(robot), f"{robot}_l9v2.urdf")


def copy_assets(robot: str) -> str:
    """Copy the source URDF dir (meshes + licence files) once into ASSET_ROOT/<robot>/ (a pinned copy)."""
    s = ROBOTS[robot]
    dst = prepared_dir(robot)
    os.makedirs(dst, exist_ok=True)
    md = os.path.join(dst, s["mesh_subdir"])
    if not os.path.isdir(md):
        shutil.copytree(os.path.join(s["src_dir"], s["mesh_subdir"]), md + ".tmp")
        os.replace(md + ".tmp", md)
    for f in os.listdir(s["src_dir"]):
        if f.upper().startswith(("LICENSE", "NOTICE", "PACKAGE")):
            shutil.copy(os.path.join(s["src_dir"], f), dst)
    return dst


def add_links(urdf_text: str, links: dict) -> str:
    """links: name -> (parent, xyz, rpy). Appends fixed child links (tiny inertial) before </robot>."""
    tiny = ('<inertial><origin rpy="0 0 0" xyz="0 0 0"/><mass value="0.001"/>'
            '<inertia ixx="1e-7" ixy="0" ixz="0" iyy="1e-7" iyz="0" izz="1e-7"/></inertial>')
    add = ""
    for name, (parent, xyz, rpy) in links.items():
        add += (f'  <link name="{name}">{tiny}</link>\n'
                f'  <joint name="{name}_joint" type="fixed"><parent link="{parent}"/><child link="{name}"/>'
                f'<origin xyz="{xyz[0]:.6f} {xyz[1]:.6f} {xyz[2]:.6f}" rpy="{rpy[0]:.9f} {rpy[1]:.9f} {rpy[2]:.9f}"/>'
                f'</joint>\n')
    i = urdf_text.rindex("</robot>")
    return urdf_text[:i] + add + urdf_text[i:]


def strip_links(urdf_text: str, names) -> str:
    for n in names:
        urdf_text = re.sub(rf'\s*<link name="{n}">.*?</link>', "", urdf_text, flags=re.S)
        urdf_text = re.sub(rf'\s*<link name="{n}"\s*/>', "", urdf_text)
        urdf_text = re.sub(rf'\s*<joint name="{n}_joint"[^>]*>.*?</joint>', "", urdf_text, flags=re.S)
    return urdf_text


def finger_open_q(u, arm_spec: dict) -> dict:
    """Open finger joint values: for joints given as None (R1 Pro) the limit with the larger pad gap."""
    gl = arm_spec["grip_lock"] or {}
    out = {k: v for k, v in gl.items() if v is not None}
    for k, v in gl.items():
        if v is None:
            j = u.joints[k]
            best = None
            for lim in (j["lower"], j["upper"]):
                g = pad_gap(u, arm_spec, {**out, **{kk: lim for kk in gl if gl[kk] is None}})
                if best is None or g > best[0]:
                    best = (g, lim)
            out[k] = best[1]
    return out


def distal(p: np.ndarray, ap, frac: float = 0.5) -> np.ndarray:
    """Points in the distal `frac` of a finger along the approach axis ap (the pad, not the carriage / knuckle)."""
    d = p @ np.asarray(ap, float)
    return p[d >= d.max() - frac * (d.max() - d.min())]


def pad_gap(u, arm_spec: dict, q: dict, kind: str = "visual") -> float:
    """Gap between the two fingers' distal inner faces along the parent's y axis (closing axis), m."""
    f = arm_spec["fingers"]
    a = distal(u.link_points(f[0], arm_spec["parent"], q, kind=kind), arm_spec["approach"])
    b = distal(u.link_points(f[1], arm_spec["parent"], q, kind=kind), arm_spec["approach"])
    if a[:, 1].mean() > b[:, 1].mean():
        a, b = b, a
    return float(b[:, 1].min() - a[:, 1].max())



def measure_tcp(u, robot: str, arm: str, q: dict | None = None) -> dict:
    """TCP distance along the approach axis from the parent link origin + pad facts, in the parent frame."""
    s = ROBOTS[robot]
    a_spec = s["arms"][arm]
    ap = np.asarray(a_spec["approach"], float)
    kind = s.get("mesh_kind", "visual")
    q = q or {}
    rule = s["tcp_rule"]
    if rule == "ffw":
        pts = np.concatenate([u.link_points(f, a_spec["parent"], q, kind) for f in a_spec["fingers"]])
        d = pts @ ap
        tip, base = float(d.max()), float(d.min())
        return {"tcp": (tip + base) / 2, "tip": tip, "finger_base": base}
    if rule == "franka":
        pts = np.concatenate([u.link_points(f, a_spec["parent"], q, kind) for f in a_spec["fingers"]])
        tip = float((pts @ ap).max())
        return {"tcp": tip - 0.010, "tip": tip, "pad_len_assumed": 0.020}
    if rule == "pad":
        out = {}
        for f in a_spec["fingers"]:
            p = distal(u.link_points(f, a_spec["parent"], q, kind), ap)
            side = np.sign(p[:, 1].mean())
            inner = p[np.abs(p[:, 1] - (p[:, 1].min() if side > 0 else p[:, 1].max())) < 0.003]
            out[f] = (float((inner @ ap).min()), float((inner @ ap).max()))
        lo = np.mean([v[0] for v in out.values()])
        hi = np.mean([v[1] for v in out.values()])
        allp = np.concatenate([u.link_points(f, a_spec["parent"], q, kind) for f in a_spec["fingers"]])
        return {"tcp": float((lo + hi) / 2), "tip": float((allp @ ap).max()), "pad_from": float(lo),
                "pad_to": float(hi)}
    raise ValueError(rule)


def tcp_xyz(robot: str, arm: str, dist: float) -> tuple:
    ap = np.asarray(ROBOTS[robot]["arms"][arm]["approach"], float)
    return tuple(float(v) for v in ap * dist)


def write_prepared(robot: str, tcps: dict, extra_links: dict | None = None) -> str:
    """Prepared URDF: source text with mesh paths kept relative (copied meshes next to it) + TCP links."""
    s = ROBOTS[robot]
    txt = open(os.path.join(s["src_dir"], s["src_urdf"])).read()
    txt = txt.replace("package://franka_description/", "")
    for a, b in s.get("axis_fix", {}).items():  # cuRobo needs axis-aligned joints (P156)
        txt = txt.replace(f'xyz="{a}"', f'xyz="{b}"')
    links = {tcp_link(arm): (s["arms"][arm]["parent"], tcp_xyz(robot, arm, d), s["arms"][arm]["tcp_rpy"])
             for arm, d in tcps.items()}
    links.update(extra_links or {})
    txt = strip_links(txt, list(links))
    txt = add_links(txt, links)
    dst = prepared_urdf(robot)
    open(dst + ".tmp", "w").write(txt)
    os.replace(dst + ".tmp", dst)
    return dst
