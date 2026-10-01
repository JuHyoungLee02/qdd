"""E-SIM0 (prereg_sim0.md change 1): measure the Google Robot gripper in SimplerEnv pick-coke-can (no model): links,
TCP pose (extra.tcp_pose) in the robot base frame, finger link positions open / after a close, closing axis, pad gap
from the finger-tip links, gripper qpos, fingertip lowest point below the TCP (collision geometry AABBs).
usage: robot_geom.py"""
import json

import numpy as np
import sapien.core as sapien

import simpler_env

env = simpler_env.make("google_robot_pick_coke_can")
obs, _ = env.reset(options={"obj_init_options": {"init_xy": [-0.235, 0.2]}})
u = env.unwrapped
robot = u.agent.robot
base = robot.get_pose()
inv = base.inv()
tcp = inv * u.tcp.pose if hasattr(u, "tcp") else None
print("controller", u._control_mode if hasattr(u, "_control_mode") else None)
print("base pose", base.p.round(4).tolist(), base.q.round(4).tolist())
print("tcp (base)", None if tcp is None else (tcp.p.round(4).tolist(), tcp.q.round(4).tolist()))
print("extra.tcp_pose", np.round(obs["extra"]["tcp_pose"], 4).tolist())
print("qpos", np.round(obs["agent"]["qpos"], 4).tolist())
print("joints", [j.name for j in robot.get_active_joints()])


def fingers():
    out = {}
    for l in robot.get_links():
        n = l.name
        if "finger" in n or "gripper" in n or n.endswith("link_camera") or "tcp" in n:
            out[n] = (inv * l.pose).p.round(4).tolist()
    return out


def lowest(prefix=("link_finger",)):
    zs = []
    for l in robot.get_links():
        if not l.name.startswith(prefix):
            continue
        for s in l.get_collision_shapes():
            g = s.geometry
            try:
                v = np.asarray(g.vertices) * np.asarray(g.scale)
            except Exception:
                continue
            T = (inv * l.pose * s.get_local_pose()).to_transformation_matrix()
            zs.append((v @ T[:3, :3].T + T[:3, 3])[:, 2].min())
    return min(zs) if zs else None


f0 = fingers()
print("open links", json.dumps(f0))
print("lowest finger point dz (m) open", None if lowest() is None or tcp is None else round(lowest() - tcp.p[2], 4))
a = np.zeros(7)
for i in range(6):
    a[-1] = 1.0
    obs, *_ = env.step(a)
print("qpos after close x6", np.round(obs["agent"]["qpos"], 4).tolist())
f1 = fingers()
print("closed links", json.dumps(f1))
for i in range(6):
    a[-1] = -1.0
    obs, *_ = env.step(a)
print("qpos after open x6", np.round(obs["agent"]["qpos"], 4).tolist())
print("objects", {a.name: (inv * a.pose).p.round(4).tolist() for a in u._scene.get_all_actors()[:20]})
