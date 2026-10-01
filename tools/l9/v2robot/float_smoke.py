"""(pod, Isaac Lab app) Floating-gripper URDF import smoke: convert assets9/grippers/<name>.urdf, spawn it (gravity off,
fixed world root), drive vx..vyaw to a pose and the finger joints from the json width table (open -> closed), report
tracking errors and the TCP pose vs the commanded virtual joints. usage: float_smoke.py <name> <out dir>"""
import json
import os
import sys

from isaaclab.app import AppLauncher

NAME, OUT = sys.argv[1], sys.argv[2]
app = AppLauncher(headless=True).app

import numpy as np  # noqa: E402

import isaaclab.sim as sim_utils  # noqa: E402
from isaaclab.actuators import ImplicitActuatorCfg  # noqa: E402
from isaaclab.assets import AssetBaseCfg  # noqa: E402
from isaaclab.assets.articulation import ArticulationCfg  # noqa: E402
from isaaclab.scene import InteractiveScene, InteractiveSceneCfg  # noqa: E402
from isaaclab.sim.converters import UrdfConverterCfg  # noqa: E402

HERE = "/data/harvest/l9v2robot/code/harvest/l9/assets9/grippers"


def main():
    os.makedirs(OUT, exist_ok=True)
    g = json.load(open(os.path.join(HERE, f"{NAME}.json")))
    urdf = os.path.join(HERE, f"{NAME}.urdf")
    wt = g["width_to_joint"]
    if "q_by_joint" in wt:
        fj = list(wt["q_by_joint"])
        q_of = lambda w: {j: float(np.interp(w, wt["width_m"], wt["q_by_joint"][j])) for j in fj}  # noqa: E731
    else:
        fj = g["finger_joints"]["drive"] + list(g["finger_joints"]["followers"])
        mult = {**{j: 1.0 for j in g["finger_joints"]["drive"]}, **g["finger_joints"]["followers"]}
        q_of = lambda w: {j: mult[j] * float(np.interp(w, wt["width_m"], wt["drive_q"])) for j in fj}  # noqa: E731
    virt = ["vx", "vy", "vz", "vr", "vp", "vyaw"]
    cfg = InteractiveSceneCfg(num_envs=1, env_spacing=2.0)
    cfg.ground = AssetBaseCfg(prim_path="/World/ground", spawn=sim_utils.GroundPlaneCfg())
    cfg.light = AssetBaseCfg(prim_path="/World/light", spawn=sim_utils.DomeLightCfg(intensity=2000.0))
    cfg.grip = ArticulationCfg(
        prim_path="{ENV_REGEX_NS}/Grip",
        spawn=sim_utils.UrdfFileCfg(
            asset_path=urdf, usd_dir=f"/data/harvest/assets_l9v2/grippers_usd/{NAME}", force_usd_conversion=True,
            fix_base=True, merge_fixed_joints=False, make_instanceable=False,
            joint_drive=UrdfConverterCfg.JointDriveCfg(gains=UrdfConverterCfg.JointDriveCfg.PDGainsCfg(
                stiffness=2000.0, damping=100.0)),
            rigid_props=sim_utils.RigidBodyPropertiesCfg(disable_gravity=True),
            articulation_props=sim_utils.ArticulationRootPropertiesCfg(enabled_self_collisions=False,
                                                                       fix_root_link=True)),
        init_state=ArticulationCfg.InitialStateCfg(pos=(0.0, 0.0, 0.0), joint_pos={"vz": 0.4, **q_of(g["max_opening_m"])}),
        actuators={"virt": ImplicitActuatorCfg(joint_names_expr=virt, stiffness=1.0e4, damping=1.0e3),
                   "fingers": ImplicitActuatorCfg(joint_names_expr=fj, stiffness=2.0e3, damping=1.0e2,
                                                  effort_limit_sim=100.0)})
    sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(dt=0.01, device="cuda:0"))
    scene = InteractiveScene(cfg)
    sim.reset()
    rob = scene["grip"]
    jn = rob.joint_names
    rep = {"name": NAME, "joints": jn, "bodies": rob.body_names}
    tgt = rob.data.default_joint_pos.clone()
    vpose = {"vx": 0.1, "vy": -0.05, "vz": 0.35, "vr": 0.3, "vp": -0.2, "vyaw": 0.5}
    for k, v in vpose.items():
        tgt[0, jn.index(k)] = v
    traces = []
    for w in (g["max_opening_m"], 0.5 * (g["max_opening_m"] + g["min_opening_m"]), g["min_opening_m"]):
        for j, v in q_of(w).items():
            tgt[0, jn.index(j)] = v
        rob.set_joint_position_target(tgt)
        for _ in range(150):
            scene.write_data_to_sim()
            sim.step()
            scene.update(0.01)
        err = (rob.data.joint_pos - tgt).abs()[0]
        traces.append({"width": round(float(w), 4),
                       "finger_err_max": round(float(max(err[jn.index(j)] for j in fj)), 4),
                       "virt_err_max": round(float(max(err[jn.index(j)] for j in virt)), 4)})
    ti = rob.body_names.index(g["tcp_link"])
    rep["tcp_world"] = rob.data.body_pos_w[0, ti].cpu().numpy().round(4).tolist()
    rep["tcp_quat_w"] = rob.data.body_quat_w[0, ti].cpu().numpy().round(4).tolist()
    rep["tracks"] = traces

    def rot(axis, a):
        c, s = np.cos(a), np.sin(a)
        return {"x": np.array([[1, 0, 0], [0, c, -s], [0, s, c]]), "y": np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]),
                "z": np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])}[axis]
    R = rot("x", vpose["vr"]) @ rot("y", vpose["vp"]) @ rot("z", vpose["vyaw"])
    exp = np.array([vpose["vx"], vpose["vy"], vpose["vz"]]) + R @ np.array(g["tcp_in_base"]["xyz"])
    rep["tcp_expected_world"] = exp.round(4).tolist()
    rep["tcp_err_mm"] = round(float(np.linalg.norm(exp - np.array(rep["tcp_world"]) +
                                                   rob.data.root_pos_w[0].cpu().numpy() * 0)) * 1e3, 2)
    json.dump(rep, open(os.path.join(OUT, f"{NAME}_float.json"), "w"), indent=1)
    print("FLOAT", json.dumps({k: rep[k] for k in ("tcp_world", "tcp_expected_world", "tcp_err_mm", "tracks")}), flush=True)


if __name__ == "__main__":
    try:
        main()
        c = 0
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        c = 1
    # no app.close(): it hangs in the kit shutdown (smoke 10-02); os._exit like tools/l9r
    os._exit(c)
