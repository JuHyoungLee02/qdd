"""(pod, cuRobo v0.8.0) Build the L9 v2 cuRobo robot configs: one yml per (robot, arm).

usage: run.sh build /data/harvest/l9v2robot/code/tools/l9/v2robot/build_curobo9.py <robot> [--out DIR] [--density D]

Per robot: copy the assets to ASSET_ROOT/<robot>, measure the TCP (robots_v2.measure_tcp), write the prepared URDF
with "<arm>_l9_tcp" links, fit collision spheres with cuRobo's RobotBuilder (MorphIt) on every link below the config
base (Franka: cuRobo's own franka.yml spheres), build the self-collision ignore list = parent/child neighbours +
gripper-internal pairs + pairs already touching in the nominal pose (both arms stowed, fingers open), and write
<out>/<robot>_<arm>.yml (kinematics: base, tool frame = TCP, lock_joints = everything except the 7 arm joints).
Then an IK smoke: FK of random arm configurations -> batched IK back (success rate, position error) and the
self-collision count of the stowed pose (must be 0)."""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import robots_v2 as RV  # noqa: E402
from urdf_fk import Urdf  # noqa: E402

OUT_DEFAULT = "/data/harvest/l9v2robot/out/curobo"


def subtree_links(u: Urdf, base: str) -> list:
    return u.descendants(base)


def actuated_in(u: Urdf, links: list) -> list:
    ls = set(links)
    return [n for n, j in u.joints.items() if j["child"] in ls and j["parent"] in ls
            and j["type"] in ("revolute", "continuous", "prismatic") and j["mimic"] is None]


def neighbours(u: Urdf, links: list, sph_links: set) -> dict:
    """Ignore pairs between each sphere link and its nearest sphere-carrying ancestor (through sphere-less links)."""
    ign = {}
    ls = set(links)
    for k in links:
        if k not in sph_links:
            continue
        p = k
        while p in u.child_joint:
            p = u.joints[u.child_joint[p]]["parent"]
            if p not in ls:
                break
            if p in sph_links:
                ign.setdefault(k, []).append(p)
                break
    return ign


def merge(ign: dict, pairs) -> dict:
    for a, b in pairs:
        if a == b:
            continue
        if b in ign.get(a, []) or a in ign.get(b, []):
            continue
        ign.setdefault(a, []).append(b)
    return ign


LIMIT_MARGIN = 0.03  # rad (m for prismatic): planned arm joints stay this far inside the sim joint limits


def kin_dict(robot: str, arm: str, spheres: dict, ignore: dict, lock: dict, cspace_names: list,
             cspace_default: list, buffer: dict) -> dict:
    s = RV.ROBOTS[robot]
    tcp = RV.tcp_link(arm)
    links = sorted(spheres)
    return {
        "format_version": 2.0,
        "base_link": s["base"],
        "tool_frames": [tcp],
        "urdf_path": RV.prepared_urdf(robot),
        "asset_root_path": RV.prepared_dir(robot),
        "collision_link_names": links + ["attached_object"],
        "collision_spheres": {k: spheres[k] for k in links},
        "collision_sphere_buffer": 0.0,
        "self_collision_buffer": buffer,
        "self_collision_ignore": ignore,
        "mesh_link_names": links,
        "grasp_contact_link_names": [s["arms"][arm]["parent"], *s["arms"][arm]["fingers"], "attached_object"],
        "lock_joints": lock,
        "extra_links": {"attached_object": {"parent_link_name": tcp, "link_name": "attached_object",
                                            "joint_name": "attach_joint", "joint_type": "FIXED",
                                            "fixed_transform": [0, 0, 0, 1, 0, 0, 0]}},
        "extra_collision_spheres": {"attached_object": 16},
        "cspace": {"joint_names": cspace_names, "default_joint_position": cspace_default,
                   "null_space_weight": [1.0] * len(cspace_names),
                   "cspace_distance_weight": [1.0] * len(cspace_names),
                   "max_acceleration": 15.0, "max_jerk": 500.0,
                   # sim limits (USD = URDF, checked) minus LIMIT_MARGIN on the planned arm joints (owner 10-02)
                   "position_limit_clip": LIMIT_MARGIN},  # scalar: applied to the active (unlocked) joints
    }


def hull_urdf(robot: str, links: list) -> str:
    """A fitting-only copy of the prepared URDF whose meshes (links below the base) are replaced by the convex hull of
    each visual mesh (the FFW-SG2 export has 2-10 MB OBJ per link: MorphIt took 210 s per link). Spheres fitted to
    the hull are conservative (cover the concavities). The cuRobo config keeps the prepared URDF."""
    import trimesh
    u = Urdf(RV.prepared_urdf(robot))
    txt = open(RV.prepared_urdf(robot)).read()
    hd = os.path.join(RV.prepared_dir(robot), "hull")
    os.makedirs(hd, exist_ok=True)
    done = {}
    for k in u.links:
        for fn, sc, Tg, prim in u.geoms(k, "visual"):
            if fn is None or fn in done:
                continue
            out = os.path.join(hd, os.path.splitext(os.path.basename(fn))[0] + "_hull.stl")
            if not os.path.exists(out):
                m = trimesh.load(fn, force="mesh", process=False)
                m.convex_hull.export(out)
            done[fn] = out
    for fn, out in done.items():
        rel = os.path.relpath(fn, RV.prepared_dir(robot))
        hrel = os.path.relpath(out, RV.prepared_dir(robot))
        txt = txt.replace(f'filename="{rel}"', f'filename="{hrel}"').replace(f'filename="{fn}"', f'filename="{hrel}"')
    txt = re.sub(r"<collision.*?</collision>", "", txt, flags=re.S)  # fitting reads the visual hulls only
    path = RV.prepared_urdf(robot).replace(".urdf", "_hullfit.urdf")
    open(path, "w").write(txt)
    return path


def fit_spheres(robot: str, links: list, density: float, seed: int = 7) -> tuple:
    import types

    import torch
    if "curobo._src.util.viser_visualizer" not in sys.modules:  # viser (web viewer) is not installed; unused here
        stub = types.ModuleType("curobo._src.util.viser_visualizer")
        stub.ViserVisualizer = None
        sys.modules["curobo._src.util.viser_visualizer"] = stub
    from curobo.robot_builder import RobotBuilder
    np.random.seed(seed)
    torch.manual_seed(seed)
    s = RV.ROBOTS[robot]
    b = RobotBuilder(urdf_path=hull_urdf(robot, links), asset_path=RV.prepared_dir(robot),
                     tool_frames=[RV.tcp_link(a) for a in s["arms"]])
    b._mesh_link_names = [k for k in b._mesh_link_names if k in set(links)]  # only links below the config base
    sph = b.fit_collision_spheres(sphere_density=density, compute_metrics=True,
                                  use_collision_mesh=False)
    metrics = {k: {"n": m.num_spheres, "cover": round(m.coverage, 3), "protr": round(m.protrusion, 3),
                   "prot_mm": round(m.protrusion_dist_mean * 1e3, 2), "gap_mm": round(m.surface_gap_mean * 1e3, 2)}
               for k, m in b.link_metrics.items()}
    return {k: [{"center": [round(float(c), 5) for c in v["center"]], "radius": round(float(v["radius"]), 5)}
                for v in vv] for k, vv in sph.items()}, metrics


def franka_spheres() -> tuple:
    """cuRobo v0.8.0 franka.yml spheres (Apache-2.0, hand-tuned) for the panda links; its ignore list kept too."""
    import yaml
    d = yaml.safe_load(open("/data/harvest/l9v2/pylib/curobo/content/configs/robot/franka.yml"))["robot_cfg"]
    k = d["kinematics"]
    sph = {n: v for n, v in k["collision_spheres"].items() if n != "attached_object"}
    ign = {n: [x for x in v if x != "attached_object"] for n, v in k["self_collision_ignore"].items()
           if n != "attached_object"}
    buf = {n: v for n, v in k["self_collision_buffer"].items() if n != "attached_object"}
    return sph, ign, buf


def touching_pairs(kd: dict, q_named: dict) -> list:
    """Link pairs whose spheres overlap at the joint configuration q_named (all active joints)."""
    import torch
    from curobo._src.robot.kinematics.kinematics import Kinematics
    from curobo._src.robot.kinematics.kinematics_cfg import KinematicsCfg
    from curobo._src.state.state_joint import JointState
    d = copy.deepcopy(kd)
    d["self_collision_ignore"] = {}
    cfg = KinematicsCfg.from_data_dict(d)
    kin = Kinematics(cfg)
    q = torch.tensor([[q_named.get(n, 0.0) for n in kin.joint_names]], device="cuda", dtype=torch.float32)
    st = kin.compute_kinematics(JointState.from_position(q, joint_names=kin.joint_names))
    sp = st.robot_spheres.view(-1, 4)
    kc = cfg.kinematics_config
    lidx = kc.link_sphere_idx_map.view(-1)
    names = {v: k for k, v in kc.link_name_to_idx_map.items()}
    ok = sp[:, 3] > 0
    c, r, li = sp[ok, :3], sp[ok, 3], lidx[ok]
    dist = torch.cdist(c, c) - r[:, None] - r[None, :]
    hit = (dist < 0) & (li[:, None] != li[None, :])
    ii, jj = torch.nonzero(hit, as_tuple=True)
    pairs = set()
    for a, b in zip(li[ii].tolist(), li[jj].tolist()):
        pairs.add(tuple(sorted((names[a], names[b]))))
    return sorted(pairs)




def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("robot", choices=sorted(RV.ROBOTS))
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--density", type=float, default=1.0)
    ap.add_argument("--reuse-spheres", action="store_true", help="take the spheres of the previous <out>/<robot>_<arm>.yml")
    ap.add_argument("--g1-tcp", default="", help="g1 only: json from hands_v2.py with per-arm TCP + open posture")
    a = ap.parse_args()
    robot = a.robot
    s = RV.ROBOTS[robot]
    os.makedirs(a.out, exist_ok=True)
    RV.copy_assets(robot)
    src = Urdf(os.path.join(s["src_dir"], s["src_urdf"]))
    report = {"robot": robot, "arms": {}}
    tcps, hand_open = {}, {}
    if s["tcp_rule"] == "g1":
        g = json.load(open(a.g1_tcp))
        for arm in s["arms"]:
            tcps[arm] = g[arm]["tcp_dist"]
            hand_open[arm] = g[arm]["open_q"]
            report["arms"][arm] = {"tcp": g[arm]}
    else:
        for arm, sa in s["arms"].items():
            q0 = RV.finger_open_q(src, sa) if sa["grip_lock"] else {}
            m = RV.measure_tcp(src, robot, arm, q0)
            tcps[arm] = m["tcp"]
            hand_open[arm] = q0
            report["arms"][arm] = {"tcp": m, "finger_open_q": q0,
                                   "pad_gap_open_m": RV.pad_gap(src, sa, q0, s.get("mesh_kind", "visual")) if sa["grip_lock"] else None}
    path = RV.write_prepared(robot, tcps)
    u = Urdf(path)
    links = subtree_links(u, s["base"])
    print("prepared", path, "links below base", len(links), "tcps", {k: round(v, 4) for k, v in tcps.items()})
    if robot == "franka":
        spheres, base_ign, buf = franka_spheres()
        metrics = {"source": "cuRobo v0.8.0 franka.yml"}
    else:
        prev = os.path.join(a.out, f"{robot}_{next(iter(s['arms']))}.yml")
        if a.reuse_spheres and os.path.exists(prev):
            import yaml
            spheres = yaml.safe_load(open(prev))["robot_cfg"]["kinematics"]["collision_spheres"]
            metrics = {"source": f"reused from {prev}"}
        else:
            spheres, metrics = fit_spheres(robot, links, a.density)
        base_ign, buf = {}, {}
    sph_links = set(spheres)
    act = actuated_in(u, links)
    for arm, sa in s["arms"].items():
        lock = dict(s["lock_common"])
        for oarm, osa in s["arms"].items():
            hq = hand_open[oarm]
            lock.update({k: float(v) for k, v in hq.items()})
            if oarm != arm:
                lock.update({j: float(osa["stow"].get(j, 0.0)) for j in osa["joints"]})
        for j in act:  # any other actuated joint below the base (none expected) is locked at 0
            if j not in sa["joints"] and j not in lock:
                lock[j] = 0.0
        names = list(sa["joints"]) + [j for j in act if j not in sa["joints"]]
        stow_q = {j: float(sa["stow"].get(j, 0.0)) for j in sa["joints"]}
        init_q = dict(zip(sa["joints"], sa["init"])) if sa.get("init") else stow_q  # retract / null-space pose
        default = [init_q.get(j, lock.get(j, 0.0)) for j in names]
        ign = merge(copy.deepcopy(base_ign) if base_ign else neighbours(u, links, sph_links), [])
        grip = [sa["parent"], *sa["fingers"]]
        for oarm, osa in s["arms"].items():
            g = [x for x in [osa["parent"], *osa["fingers"]] if x in sph_links]
            ign = merge(ign, [(x, y) for i, x in enumerate(g) for y in g[i + 1:]])
        kd = kin_dict(robot, arm, spheres, ign, lock, names, default, buf)
        touch = touching_pairs(kd, stow_q)
        ign = merge(ign, touch)
        kd["self_collision_ignore"] = ign
        still = touching_pairs({**kd, "self_collision_ignore": {}}, stow_q)
        out = os.path.join(a.out, f"{robot}_{arm}.yml")
        import yaml
        with open(out, "w") as f:
            f.write(f"# L9 v2 cuRobo v0.8.0 config: {robot} {arm} arm (tools/l9/v2robot/build_curobo9.py)\n"
                    f"# base {s['base']}, tool frame {RV.tcp_link(arm)} = executor TCP (pad centre, z = -approach,"
                    f" y = closing axis); gripper locked open\n")
            yaml.safe_dump({"robot_cfg": {"kinematics": kd}}, f, sort_keys=False, default_flow_style=None)
        n_sph = sum(len(v) for v in spheres.values())
        report["arms"][arm].update({"yml": out, "n_spheres": n_sph, "n_links": len(sph_links),
                                    "ignored_touching_at_stow": touch, "lock_joints": lock})
        print(arm, "spheres", n_sph, "links", len(sph_links), "touching at stow (ignored):", touch)
        sm = smoke(kd, sa["joints"], stow_q)
        report["arms"][arm]["ik_smoke"] = sm
        print(arm, "IK smoke", sm)
    report["sphere_metrics"] = metrics
    json.dump(report, open(os.path.join(a.out, f"{robot}_build.json"), "w"), indent=1, default=str)
    print("wrote", os.path.join(a.out, f"{robot}_build.json"))


def smoke(kd: dict, arm_joints: list, stow_q: dict, n: int = 200, seed: int = 3) -> dict:
    """FK of random collision-free arm configurations -> IK back to the TCP pose (self-collision on)."""
    import torch
    from curobo.inverse_kinematics import InverseKinematics, InverseKinematicsCfg
    from curobo.types import GoalToolPose, JointState, Pose
    g = torch.Generator(device="cpu").manual_seed(seed)
    cfg = InverseKinematicsCfg.create(robot={"robot_cfg": {"kinematics": copy.deepcopy(kd)}}, num_seeds=32,
                                      self_collision_check=True, max_batch_size=n)
    ik = InverseKinematics(cfg)
    kin = ik.kinematics
    names = kin.joint_names
    lim = kin.get_joint_limits().position.cpu()  # 2 x dof
    q = lim[0] + (lim[1] - lim[0]) * torch.rand(n, len(names), generator=g)
    st = kin.compute_kinematics(JointState.from_position(q.cuda(), joint_names=names))
    tf = ik.tool_frames[0]
    pose = st.tool_poses.get_link_pose(tf)
    res = ik.solve_pose(GoalToolPose.from_poses({tf: Pose(position=pose.position.clone(),
                                                          quaternion=pose.quaternion.clone())}, num_goalset=1))
    ok = res.success.view(-1)
    pe = res.position_error.view(-1)[ok]
    qs = torch.tensor([[stow_q.get(j, 0.0) for j in names]], device="cuda", dtype=torch.float32)
    stow_pose = kin.compute_kinematics(JointState.from_position(qs, joint_names=names)).tool_poses.get_link_pose(tf)
    return {"dof": len(names), "joints": list(names), "n": n, "ik_success": int(ok.sum()),
            "pos_err_mm_mean": round(float(pe.mean()) * 1e3, 3) if len(pe) else None,
            "stow_tcp_xyz": [round(float(v), 4) for v in stow_pose.position.view(-1)],
            "stow_tcp_quat_wxyz": [round(float(v), 4) for v in stow_pose.quaternion.view(-1)]}


if __name__ == "__main__":
    main()
