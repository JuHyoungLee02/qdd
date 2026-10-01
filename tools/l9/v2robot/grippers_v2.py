"""(pod) Floating-gripper URDF + facts json per L9 v2 gripper (spec §12.4 step 2: Isaac lift + shake test).

usage: run.sh grip /data/harvest/l9v2robot/code/tools/l9/v2robot/grippers_v2.py <name> [--out DIR]

URDF: world -> prismatic vx, vy, vz -> revolute vr, vp, vyaw (about x, y, z) -> the gripper base link -> the real
gripper links / joints / meshes of the prepared robot URDF (robots_v2; absolute mesh paths on /data). The virtual
links carry 0.05 kg so PhysX stays stable; the TCP link ("<arm>_l9_tcp", = the executor grasp frame G) is kept.
JSON (all lengths m, frame = TCP frame G unless named): max opening, pad length / width, finger depth (TCP -> finger
tip along the approach), TCP pose in the gripper base link, finger joints + the width <-> joint table, and a coarse
box model (palm box; finger boxes at several widths) for a pure gripper-object collision check."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import robots_v2 as RV  # noqa: E402
from urdf_fk import R_rpy, Urdf  # noqa: E402

OUT_DEFAULT = "/data/harvest/l9v2robot/out/grippers"
VIRT = (("vx", "prismatic", (1, 0, 0)), ("vy", "prismatic", (0, 1, 0)), ("vz", "prismatic", (0, 0, 1)),
        ("vr", "revolute", (1, 0, 0)), ("vp", "revolute", (0, 1, 0)), ("vyaw", "revolute", (0, 0, 1)))

# FFW-SG2 RH-P12-RN: harvest.sim.scene _GQ / _GW (inner pad gap measured in sim, probe2 2026-09-24)
FFW_GQ = [0.0, 0.2, 0.4, 0.6, 0.8, 0.9, 1.0, 1.1]
FFW_GW = [round(w - 0.0077, 4) for w in (0.1147, 0.1014, 0.0847, 0.0653, 0.0439, 0.0327, 0.0214, 0.0100)]

ACTUATION = {  # spec §12.4 / grip_aperture_2026-10-02.md §6.2: force cap, close speed, real-robot control mode
    "ffw_sg2": {
        "sim": {"drive_effort_limit_Nm": 30.0, "drive_stiffness": {"right": 100.0, "left": 300.0}, "drive_damping": 4.0,
                "drive_velocity_limit_rad_s": 2.2, "full_close_s_at_vel_limit": round(1.1 / 2.2, 2),
                "followers": {"effort_limit_Nm": 20.0, "stiffness": 2.0, "damping": 0.5},
                "source": "third_party/humanoid_challenge_env/scripts/taskC/taskC_ffw_sg2.py gripper_master_r/l, "
                          "gripper_slave (the L9 sim's actuators)"},
        "real": {"servo": "Dynamixel ID 8 (right) / 38 (left)", "operating_mode": 5,
                 "operating_mode_name": "current-based position control", "profile_velocity": 0,
                 "goal_current": None,
                 "note": "Goal Current / Current Limit are not set in ros2_control (device default; value not in the "
                         "repo -> unknown here). Stroke 0-107.6 mm, payload 5 kg (ROBOTIS spec page, docs/design/D21)",
                 "source": "ROBOTIS-GIT/ai_worker 9bc7f7b ffw_description/ros2_control/ffw_sg2_rev1_follower/"
                           "ffw_sg2_follower.ros2_control.xacro (Apache-2.0)"}},
    "franka": {
        "sim": {"finger_effort_limit_N": 70.0, "finger_stiffness": 2.0e3, "finger_damping": 1.0e2,
                "source": "harvest/l9/robot9.py FINGER_KP/KD/EFFORT (Franka Hand continuous grasp force 70 N)"},
        "real": {"grasp_action": "franka_gripper Grasp(width, epsilon_inner, epsilon_outer, speed, force)",
                 "epsilon_default_m": 0.005, "continuous_force_N": 70.0,
                 "source": "Franka Hand / franka_gripper docs as cited in docs/research/grip_aperture_2026-10-02.md "
                           "§3.1 (not re-checked here)"}},
    "r1pro": {"sim": None, "real": None,
              "note": "no L9 sim actuator yet; URDF limits below (GalaxeaManipSim robot.urdf) are the only source"},
    "g1": {"sim": None, "real": None,
           "note": "no L9 sim actuator yet; URDF limits below (unitree_ros g1_description) are the only source"},
}


GRIPPERS = {
    "ffw_sg2_right": {"robot": "ffw_sg2", "arm": "right", "base": "ffw_sg2_follower_arm_r_link7",
                      "drive": ["gripper_r_joint1"], "followers": {f"gripper_r_joint{i}": 1.0 for i in (2, 3, 4)},
                      "fingers": [["gripper_r_rh_p12_rn_l1", "gripper_r_rh_p12_rn_l2"],
                                  ["gripper_r_rh_p12_rn_r1", "gripper_r_rh_p12_rn_r2"]],
                      "pads": ["gripper_r_rh_p12_rn_l2", "gripper_r_rh_p12_rn_r2"],
                      "table": (FFW_GQ, FFW_GW), "table_src": "harvest/sim/scene.py _GQ/_GW (sim probe2)"},
    "ffw_sg2_left": {"robot": "ffw_sg2", "arm": "left", "base": "ffw_sg2_follower_arm_l_link7",
                     "drive": ["gripper_l_joint1"], "followers": {f"gripper_l_joint{i}": 1.0 for i in (2, 3, 4)},
                     "fingers": [["gripper_l_rh_p12_rn_l1", "gripper_l_rh_p12_rn_l2"],
                                 ["gripper_l_rh_p12_rn_r1", "gripper_l_rh_p12_rn_r2"]],
                     "pads": ["gripper_l_rh_p12_rn_l2", "gripper_l_rh_p12_rn_r2"],
                     "table": (FFW_GQ, FFW_GW), "table_src": "harvest/sim/scene.py _GQ/_GW (sim probe2)"},
    "franka_hand": {"robot": "franka", "arm": "right", "base": "panda_hand",
                    "drive": ["panda_finger_joint1"], "followers": {"panda_finger_joint2": 1.0},
                    "fingers": [["panda_leftfinger"], ["panda_rightfinger"]],
                    "pads": ["panda_leftfinger", "panda_rightfinger"], "table": "fk", "q_range": (0.0, 0.04),
                    "mesh_kind": "collision"},
    "r1pro_right": {"robot": "r1pro", "arm": "right", "base": "right_gripper_link",
                    "drive": ["right_gripper_finger_joint1"], "followers": {"right_gripper_finger_joint2": 1.0},
                    "fingers": [["right_gripper_finger_link1"], ["right_gripper_finger_link2"]],
                    "pads": ["right_gripper_finger_link1", "right_gripper_finger_link2"], "table": "fk",
                    "q_range": (0.0, 0.05), "distal": 0.5, "pad_rule": "slab"},  # gap: distal half (wide carriage)
    "r1pro_left": {"robot": "r1pro", "arm": "left", "base": "left_gripper_link",
                   "drive": ["left_gripper_finger_joint1"], "followers": {"left_gripper_finger_joint2": 1.0},
                   "fingers": [["left_gripper_finger_link1"], ["left_gripper_finger_link2"]],
                   "pads": ["left_gripper_finger_link1", "left_gripper_finger_link2"], "table": "fk",
                   "q_range": (0.0, 0.05), "distal": 0.5, "pad_rule": "slab"},
    "g1_right": {"robot": "g1", "arm": "right", "base": "right_hand_palm_link",
                 "synergy": "/data/harvest/l9v2robot/out/g1_hand.json",
                 "fingers": [["right_hand_thumb_0_link", "right_hand_thumb_1_link", "right_hand_thumb_2_link"],
                             ["right_hand_index_0_link", "right_hand_index_1_link"],
                             ["right_hand_middle_0_link", "right_hand_middle_1_link"]],
                 "pads": ["right_hand_thumb_2_link", "right_hand_index_1_link"], "pad_rule": "slab"},
    "g1_left": {"robot": "g1", "arm": "left", "base": "left_hand_palm_link",
                "synergy": "/data/harvest/l9v2robot/out/g1_hand.json",
                "fingers": [["left_hand_thumb_0_link", "left_hand_thumb_1_link", "left_hand_thumb_2_link"],
                            ["left_hand_index_0_link", "left_hand_index_1_link"],
                            ["left_hand_middle_0_link", "left_hand_middle_1_link"]],
                "pads": ["left_hand_thumb_2_link", "left_hand_index_1_link"], "pad_rule": "slab"},
}


def floating_urdf(g: dict, name: str) -> str:
    """Text of the floating-gripper URDF (see module doc)."""
    path = RV.prepared_urdf(g["robot"])
    root = ET.parse(path).getroot()
    u = Urdf(path)
    keep = set(u.descendants(g["base"]))
    d = RV.prepared_dir(g["robot"])
    out = [f'<?xml version="1.0"?>\n<robot name="{name}_floating">']
    inert = ('<inertial><origin xyz="0 0 0" rpy="0 0 0"/><mass value="0.05"/>'
             '<inertia ixx="1e-4" ixy="0" ixz="0" iyy="1e-4" iyz="0" izz="1e-4"/></inertial>')
    out.append('  <link name="world"/>')
    prev = "world"
    for i, (jn, jt, ax) in enumerate(VIRT):
        child = g["base"] if i == len(VIRT) - 1 else f"{jn}_link"
        if child != g["base"]:
            out.append(f'  <link name="{child}">{inert}</link>')
        lim = '<limit lower="-3.0" upper="3.0" effort="1000" velocity="5"/>' if jt == "prismatic" else \
            '<limit lower="-6.2832" upper="6.2832" effort="1000" velocity="10"/>'
        out.append(f'  <joint name="{jn}" type="{jt}"><parent link="{prev}"/><child link="{child}"/>'
                   f'<origin xyz="0 0 0" rpy="0 0 0"/><axis xyz="{ax[0]} {ax[1]} {ax[2]}"/>{lim}</joint>')
        prev = child
    for el in root.findall("link"):
        if el.get("name") in keep:
            for m in el.iter("mesh"):
                fn = m.get("filename")
                if not os.path.isabs(fn):
                    m.set("filename", os.path.join(d, fn))
            out.append("  " + ET.tostring(el, encoding="unicode").strip())
    for el in root.findall("joint"):
        if el.find("parent").get("link") in keep and el.find("child").get("link") in keep:
            out.append("  " + ET.tostring(el, encoding="unicode").strip())
    out.append("</robot>\n")
    txt = "\n".join(out)
    return re.sub(r"\s*<mimic[^>]*/>", "", txt)  # followers are listed in the json; drive every finger joint


def pts(u: Urdf, links, frame: str, q: dict, kind: str) -> np.ndarray:
    return np.concatenate([u.link_points(k, frame, q, kind) for k in links])


def box(p: np.ndarray) -> dict:
    lo, hi = p.min(0), p.max(0)
    return {"center": [round(float(v), 4) for v in (lo + hi) / 2], "size": [round(float(v), 4) for v in hi - lo]}


def limits(u: Urdf, j: str) -> dict:
    el = [e for e in u.root_el.findall("joint") if e.get("name") == j][0].find("limit")
    return {k: float(el.get(k)) for k in ("effort", "velocity") if el is not None and el.get(k) is not None}


_SYN = {}


def synergy(g: dict) -> dict:
    """G1 Dex3-1 thumb-index pinch table (hands_v2.py): usable band rows only, ascending width."""
    if g["synergy"] not in _SYN:
        d = json.load(open(g["synergy"]))[g["arm"]]
        lo, hi = d["min_opening_parallel_m"], d["max_opening_parallel_m"]
        rows = sorted([r for r in d["table"] if lo - 1e-9 <= r["width"] <= hi + 1e-9], key=lambda r: r["width"])
        _SYN[g["synergy"]] = {"joints": d["joints"], "w": [r["width"] for r in rows],
                              "q": np.array([r["q"] for r in rows]), "d": d}
    return _SYN[g["synergy"]]


def qmap(g: dict, qd: float) -> dict:
    if g.get("synergy"):  # qd = the pinch width (m)
        s = synergy(g)
        return {j: float(np.interp(qd, s["w"], s["q"][:, i])) for i, j in enumerate(s["joints"])}
    q = {j: qd for j in g["drive"]}
    q.update({j: m * qd for j, m in g["followers"].items()})
    return q


def pad_gap_tcp(u: Urdf, g: dict, tcp: str, q: dict, kind: str) -> float:
    a = RV.distal(u.link_points(g["pads"][0], tcp, q, kind), (0, 0, -1), g.get("distal", 1.0))
    b = RV.distal(u.link_points(g["pads"][1], tcp, q, kind), (0, 0, -1), g.get("distal", 1.0))
    if a[:, 1].mean() > b[:, 1].mean():
        a, b = b, a
    return float(b[:, 1].min() - a[:, 1].max())


def facts(g: dict, name: str) -> dict:
    u = Urdf(RV.prepared_urdf(g["robot"]))
    tcp = RV.tcp_link(g["arm"])
    kind = g.get("mesh_kind", "visual")
    T_base_tcp = u.T_rel(tcp, g["base"])
    if g.get("synergy"):
        s = synergy(g)
        qs, ws = list(s["w"]), [round(float(w), 4) for w in s["w"]]
        src = "tools/l9/v2robot/hands_v2.py thumb-index pinch synergy (usable band: axis < 10 deg, drift < 1 cm)"
    elif g["table"] == "fk":
        lo, hi = g["q_range"]
        qs = list(np.linspace(lo, hi, 9))
        ws = [pad_gap_tcp(u, g, tcp, qmap(g, q), kind) for q in qs]
        order = np.argsort(ws)
        qs, ws = [float(qs[i]) for i in order], [round(float(ws[i]), 4) for i in order]
        src = "FK of the URDF finger meshes (inner pad gap along the TCP y axis)"
    else:
        qs, ws = g["table"]
        src = g["table_src"]
        qs, ws = list(qs)[::-1], list(ws)[::-1]  # ascending width
    q_open = qs[int(np.argmax(ws))]
    qo = qmap(g, q_open)
    # pad facts at the open posture, in the TCP frame (z = -approach, so the approach coordinate is -z)
    pad = {}
    for k in g["pads"]:
        if g.get("pad_rule") == "slab":  # flat inner face walked from the tip (robots_v2.pad_extent)
            e = RV.pad_extent(u.link_points(k, tcp, qo, kind, sample=20000), (0, 0, -1))
            pad[k] = {"len": e["to"] - e["from"], "wid": e["width"], "z_from": -e["to"], "z_to": -e["from"]}
            continue
        p = RV.distal(u.link_points(k, tcp, qo, kind), (0, 0, -1), g.get("distal", 1.0))
        side = np.sign(p[:, 1].mean())
        inner = p[np.abs(p[:, 1] - (p[:, 1].min() if side > 0 else p[:, 1].max())) < 0.003]
        pad[k] = {"len": float(inner[:, 2].max() - inner[:, 2].min()), "wid": float(np.ptp(inner[:, 0])),
                  "z_from": float(inner[:, 2].min()), "z_to": float(inner[:, 2].max())}
    allf = pts(u, [x for f in g["fingers"] for x in f], tcp, qo, kind)
    tip_depth = float(-allf[:, 2].min())  # TCP -> finger tip along the approach
    palm_links = [k for k in u.descendants(g["base"]) if k not in {x for f in g["fingers"] for x in f} and
                  u.geoms(k, "visual")]
    palm = pts(u, palm_links, tcp, qo, "visual" if kind == "visual" else kind)
    boxes = []
    for w_t in sorted(set([ws[-1], ws[len(ws) // 2], ws[0]]), reverse=True):
        qd = float(np.interp(w_t, ws, qs))
        qq = qmap(g, qd)
        boxes.append({"width": round(float(w_t), 4), "q": round(qd, 4),
                      "fingers": [box(pts(u, f, tcp, qq, kind)) for f in g["fingers"]]})
    return {
        "name": name, "robot": g["robot"], "arm": g["arm"], "base_link": g["base"], "tcp_link": tcp,
        "frame": "TCP frame G: origin pad centre, z = -approach, y = closing axis, x = y cross z",
        "tcp_in_base": {"xyz": [round(float(v), 5) for v in T_base_tcp[:3, 3]],
                        "rpy": [round(float(v), 6) for v in R_rpy(T_base_tcp[:3, :3])]},
        "max_opening_m": round(float(max(ws)), 4), "min_opening_m": round(float(min(ws)), 4),
        "pad_length_m": round(float(np.mean([v["len"] for v in pad.values()])), 4),
        "pad_width_m": round(float(np.mean([v["wid"] for v in pad.values()])), 4),
        "pad_z_range_in_tcp": [round(float(np.mean([v["z_from"] for v in pad.values()])), 4),
                               round(float(np.mean([v["z_to"] for v in pad.values()])), 4)],
        "finger_depth_m": round(tip_depth, 4),
        "finger_joints": {"synergy": synergy(g)["joints"], "note": "each joint interpolated from width_to_joint "
                          "(width = the pinch gap); drive all"} if g.get("synergy") else {"drive": g["drive"], "followers": g["followers"],
                          "note": "follower q = multiplier * drive q; the floating URDF has no <mimic>: drive all"},
        "width_to_joint": ({"width_m": ws, "q_by_joint": {j: [round(float(v), 4) for v in synergy(g)["q"][:, i]] for i, j in
                                                           enumerate(synergy(g)["joints"])}, "source": src}
                           if g.get("synergy") else {"width_m": ws, "drive_q": [round(float(q), 4) for q in qs], "source": src}),
        "synergy_facts": ({k: synergy(g)["d"][k] for k in ("closing_axis_palm", "approach_palm", "tcp_xyz", "tcp_rpy",
                                                           "pad_points_local", "criteria")} if g.get("synergy") else None),
        "boxes": {"palm": box(palm), "palm_links": palm_links, "by_width": boxes,
                  "note": "axis-aligned boxes in the TCP frame from the URDF meshes (coarse, conservative)"},
        "mesh_kind": kind,
        "actuation": {**ACTUATION[g["robot"]], "urdf_limits": {j: {"lower": u.joints[j]["lower"], "upper": u.joints[j]["upper"], **limits(u, j)} for j in (synergy(g)["joints"] if g.get("synergy") else [*g["drive"], *g["followers"]])}},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", choices=sorted(GRIPPERS))
    ap.add_argument("--out", default=OUT_DEFAULT)
    a = ap.parse_args()
    g = GRIPPERS[a.name]
    os.makedirs(a.out, exist_ok=True)
    txt = floating_urdf(g, a.name)
    up = os.path.join(a.out, f"{a.name}.urdf")
    open(up, "w").write(txt)
    Urdf(up)  # parses
    f = facts(g, a.name)
    f["urdf"] = up
    f["virtual_joints"] = [v[0] for v in VIRT]
    json.dump(f, open(os.path.join(a.out, f"{a.name}.json"), "w"), indent=1)
    print(json.dumps({k: f[k] for k in ("max_opening_m", "pad_length_m", "pad_width_m", "finger_depth_m",
                                        "tcp_in_base", "width_to_joint")}, indent=None))


if __name__ == "__main__":
    main()
