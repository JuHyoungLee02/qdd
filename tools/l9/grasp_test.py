"""L9 v2 grasp candidate lift + shake test (spec §12.4 step 2, §12.12), Isaac Lab, headless, no rendering.

One process = one chunk of objects. Every env holds one object (its own USD, catalog mass and friction, upright on
the ground, turned about z so the candidate's approach has no world-x part: harvest/l9/gtest9) and one floating
gripper (assets9/grippers/<name>.urdf: 6 virtual joints + the real hand, gravity off). Envs of the same object test
different candidates; rounds repeat until every picked candidate (<= --per-obj, spread over family x width:
gtest9.pick) was tested. Per test (gtest9.PHASES, dt 0.01): settle 0.2 s at the pre-grasp (6 cm back along the
approach, fingers at pre_open) -> straight approach 0.5 s -> close (all finger drives to their closed limit,
effort-capped) 1.1 s -> lift 10 cm 0.5 s -> hold 2 s -> shake +-15 deg about world x then y (2 cycles each, 1.5 s).
Pass rules (gtest9.verdict): lift_ok after the hold and shake_ok after the shake = grasp centre still between the
fingers, object >= 5 cm higher than at rest, pad gap >= 3 mm, and (shake) grasp-centre drift in the TCP frame < 1 cm.
--lowfric repeats the shake-passing candidates with object and finger friction 0.4 (finger material combine max).

  isaac.sh <code> 1 <tag> tools.l9.grasp_test --grip ffw_sg2 --ids ids.txt --envs 1024 [--per-obj 48] [--lowfric]
Writes /data/harvest/l9v2/tested/<grip>/<id>.npz (idx into the candidate npz, lift_ok, shake_ok, lowfric_ok
(-1 = not run), final_gap (after close), gap_hold, gap_end, slip_mm, rise_end) and a json line per object in
tested/<grip>/_log.jsonl."""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

import numpy as np

ROOT = "/data/harvest/l9v2"
GRIP_FILES = {"ffw_sg2": "ffw_sg2_right", "franka": "franka_hand", "r1pro": "r1pro_right", "g1": "g1_right"}
SYNERGY = {"g1": "g1_hand_synergy.json"}
# finger joints that copy the measured position of another (emulates the hand's linkage / mimic)
FOLLOW = {"ffw_sg2": {"gripper_r_joint2": "gripper_r_joint1", "gripper_r_joint4": "gripper_r_joint3"}}
VIRT = ("vx", "vy", "vz", "vr", "vp", "vyaw")
DT = 0.01
PALM_Z = 0.03  # the proximal links / palm close the space between the fingers above +3 cm (gtest_fingerprobe)


def log(*a):
    print("[gtest]", *a, flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--grip", required=True)
    ap.add_argument("--ids", required=True, help="text file, one object id per line")
    ap.add_argument("--rows", default=f"{ROOT}/rows_mesh.json")
    ap.add_argument("--grasps", default=f"{ROOT}/grasps")
    ap.add_argument("--out", default=f"{ROOT}/tested")
    ap.add_argument("--envs", type=int, default=1024)
    ap.add_argument("--per-obj", type=int, default=48)
    ap.add_argument("--lowfric", action="store_true")
    ap.add_argument("--neg", action="store_true", help="smoke: add 2 negatives per object (90 deg turn, 8 cm shift)")
    ap.add_argument("--spacing", type=float, default=1.2)
    ap.add_argument("--device", default="cuda:0", help="physics device (production L9 worlds run PhysX on cpu)")
    ap.add_argument("--no-pad-drop", dest="pad_drop", action="store_false",
                    help="command T as is (default: gtest9.exec_pose, raised only when the closed fingertips would hit the ground)")
    ap.add_argument("--collider", default="none", choices=("none", "sdf", "cd", "auto"),
                    help="object collider override (gtest9.apply_collider): render meshes as SDF / fine convex "
                         "decomposition; auto = per object from row['collider'] or --collider-map")
    ap.add_argument("--collider-map", default=f"{ROOT}/collider_override.json", help="{'objects': {id: mode}}")
    a = ap.parse_args(argv)
    code = 0
    try:
        run(a)
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    sys.stdout.flush()
    os._exit(code)


def load_tasks(a, gj):
    """[(object id, row, cand idx array, T (k,4,4), w, pre_open, a, neg flags)] for the chunk."""
    from harvest.l9 import gtest9 as GT
    rows = json.load(open(a.rows))
    ids = [s.strip() for s in open(a.ids) if s.strip()]
    out = []
    for k in ids:
        f = os.path.join(a.grasps, a.grip, k + ".npz")
        if k not in rows or not os.path.exists(f):
            continue
        C = np.load(f)
        if len(C["w"]) == 0:
            out.append((k, rows[k], np.zeros(0, int), np.zeros((0, 4, 4)), np.zeros(0), np.zeros(0), np.zeros((0, 3)),
                        np.zeros(0, bool), np.zeros(0, object)))
            continue
        part_all = GT.parts(rows[k], C["c1"], C["c2"], C["w"])
        idx = GT.pick(C["a"], C["w"], C["score"], a.per_obj, part=part_all, prefer=GT.natural_rank(rows[k]))
        T, w, pre, av, part = C["T"][idx], C["w"][idx], C["pre_open"][idx], C["a"][idx], part_all[idx]
        neg = np.zeros(len(idx), bool)
        if a.neg:  # best top candidate (else best) turned 90 deg about the approach, and the same shifted 8 cm along x_G
            top = np.array([GT.fam_obj(x) == "top" for x in av])
            sc = C["score"][idx] + 10.0 * top
            j = int(np.argmax(sc))
            part = np.concatenate([part, ["neg", "neg"]])
            T1 = T[j].copy()
            T1[:3, :3] = T1[:3, :3] @ GT.rz(math.pi / 2)
            T2 = T[j].copy()
            T2[:3, 3] = T2[:3, 3] + 0.08 * T2[:3, 0]
            T = np.concatenate([T, T1[None], T2[None]])
            w = np.concatenate([w, [w[j]] * 2])
            pre = np.concatenate([pre, [gj["max_opening_m"]] * 2])
            av = np.concatenate([av, [av[j]] * 2])
            idx = np.concatenate([idx, [-1, -2]])
            neg = np.concatenate([neg, [True, True]])
        out.append((k, rows[k], idx, T, w, np.minimum(pre, gj["max_opening_m"]), av, neg, part))
    return out


def run(a):
    t_boot = time.time()
    from isaaclab.app import AppLauncher
    app = AppLauncher(headless=True, device="cuda:0", enable_cameras=False).app  # noqa: F841

    import torch
    import isaaclab.sim as sim_utils
    import omni.usd
    from isaaclab.actuators import ImplicitActuatorCfg
    from isaaclab.assets import ArticulationCfg, AssetBaseCfg, RigidObject, RigidObjectCfg
    from isaaclab.scene import InteractiveScene, InteractiveSceneCfg
    from isaaclab.sim.converters import UrdfConverterCfg
    from isaaclab.utils import configclass

    from harvest.l9 import gtest9 as GT
    from harvest.l9.grasp9 import qmat

    gname = GRIP_FILES.get(a.grip, a.grip)
    gdir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "harvest", "l9", "assets9", "grippers")
    gj = json.load(open(os.path.join(gdir, gname + ".json")))
    urdf = os.path.join(gdir, gname + ".urdf")
    tasks = load_tasks(a, gj)
    od = os.path.join(a.out, a.grip)
    os.makedirs(od, exist_ok=True)
    for t in tasks:  # no candidates: an empty result (the queue must not pick the object again)
        if not len(t[2]):
            np.savez_compressed(os.path.join(od, t[0] + ".npz"), idx=np.zeros(0, int), **{"pass": np.zeros(0, bool)})
            with open(os.path.join(od, "_log.jsonl"), "a") as f:
                f.write(json.dumps({"id": t[0], "l9cat": t[1].get("l9cat"), "n": 0, "lift": 0, "shake": 0,
                                    "lowfric": 0, "lowfric_run": bool(a.lowfric)}) + "\n")
    tasks = [t for t in tasks if len(t[2])]
    if not tasks:
        log("nothing to test")
        return
    # env assignment: object m gets slots = min(E, its candidates); with --lowfric every slot is a pair of envs
    # (catalog friction, friction 0.4) testing the same candidate in the same round
    M = len(tasks)
    per = 2 if a.lowfric else 1
    E = max(1, a.envs // (M * per))
    owner, lowenv, slot = [], [], []
    for m, t in enumerate(tasks):
        for s_ in range(min(E, len(t[2]))):
            owner += [m] * per
            lowenv += [False, True][:per]
            slot += [s_] * per
    owner, lowenv, slot = np.asarray(owner), np.asarray(lowenv), np.asarray(slot)
    n_env = len(owner)
    log(f"objects {M}, envs {n_env}, slots/object <= {E}, lowfric pairs {bool(a.lowfric)}, "
        f"collider {a.collider}, boot {time.time() - t_boot:.0f}s")

    act = gj["actuation"]["sim"]
    if not act:  # no sim actuator in the json (R1 Pro, G1): the production profile's finger drive (robot9.V2)
        from harvest.l9 import robot9 as R9
        v = R9.V2[a.grip]
        act = {"finger_stiffness": v["finger_kp"], "finger_damping": v["finger_kd"], "finger_effort_limit_N": v["finger_effort"],
               "source": f"robot9.V2[{a.grip!r}]"}
    fj = gj["finger_joints"]
    follow = FOLLOW.get(a.grip, {})
    syn = json.load(open(os.path.join(gdir, SYNERGY[a.grip]))) if a.grip in SYNERGY else None
    fj0 = list(fj.get("drive", [])) + list(fj.get("followers", {}))
    hand = GT.Hand(gj, synergy=syn, ref=[j for j in fj0 if j not in follow] or None)
    fingers = hand.fingers
    q_closed = dict(zip(fingers, hand.q_closed.tolist()))
    tcp_in_base = np.asarray(gj["tcp_in_base"]["xyz"], float)
    R_tb = GT.rpy_R(gj["tcp_in_base"].get("rpy", (0.0, 0.0, 0.0)))
    # finger drive (json actuation.sim): FFW-SG2 revolute (N m, rad/s), Franka prismatic (N, no velocity cap)
    f_stiff = act.get("drive_stiffness", act.get("finger_stiffness"))
    f_stiff = float(f_stiff.get("right", 100.0)) if isinstance(f_stiff, dict) else float(f_stiff)
    f_damp = float(act.get("drive_damping", act.get("finger_damping", 4.0)))
    f_eff = float(act.get("drive_effort_limit_Nm", act.get("finger_effort_limit_N")))
    f_vel = act.get("drive_velocity_limit_rad_s")
    table = gj["width_to_joint"]
    pad_z = gj.get("pad_z_range_in_tcp", (-0.03, 0.02))
    pad_w, max_open = float(gj["pad_width_m"]), float(gj["max_opening_m"])

    @configclass
    class SceneCfg(InteractiveSceneCfg):
        ground = AssetBaseCfg(prim_path="/World/ground", spawn=sim_utils.GroundPlaneCfg(
            physics_material=sim_utils.RigidBodyMaterialCfg(static_friction=0.6, dynamic_friction=0.6)))
        grip = ArticulationCfg(
            prim_path="{ENV_REGEX_NS}/Grip",
            spawn=sim_utils.UrdfFileCfg(
                asset_path=urdf, usd_dir=f"{ROOT}/gtest_usd/{gname}_cd", force_usd_conversion=False,
                collider_type="convex_decomposition",  # convex hulls of the curved finger links touch ~5 mm early
                fix_base=True, merge_fixed_joints=False, make_instanceable=False,
                convert_mimic_joints_to_normal_joints=True,
                joint_drive=UrdfConverterCfg.JointDriveCfg(gains=UrdfConverterCfg.JointDriveCfg.PDGainsCfg(
                    stiffness=100.0, damping=4.0)),
                rigid_props=sim_utils.RigidBodyPropertiesCfg(disable_gravity=True, max_depenetration_velocity=5.0),
                articulation_props=sim_utils.ArticulationRootPropertiesCfg(
                    enabled_self_collisions=False, solver_position_iteration_count=32,
                    solver_velocity_iteration_count=1, fix_root_link=True)),
            init_state=ArticulationCfg.InitialStateCfg(pos=(0.0, 0.0, 0.0), joint_pos={"vz": 1.0}),
            actuators={
                "virt_lin": ImplicitActuatorCfg(joint_names_expr=["vx", "vy", "vz"], stiffness=1e5, damping=2e3,
                                                effort_limit_sim=1e4),
                "virt_rot": ImplicitActuatorCfg(joint_names_expr=["vr", "vp", "vyaw"], stiffness=1e4, damping=2e2,
                                                effort_limit_sim=1e4),
                "fingers": ImplicitActuatorCfg(joint_names_expr=fingers, stiffness=f_stiff, damping=f_damp,
                                               effort_limit_sim=f_eff,
                                               **({"velocity_limit_sim": float(f_vel)} if f_vel else {}))},
            soft_joint_pos_limit_factor=1.0)

    sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(
        dt=DT, device=a.device, render_interval=1000,
        physx=sim_utils.PhysxCfg(bounce_threshold_velocity=0.01, friction_correlation_distance=0.00625,
                                 gpu_max_rigid_contact_count=2 ** 24, gpu_max_rigid_patch_count=2 ** 22,
                                 gpu_found_lost_pairs_capacity=2 ** 24, gpu_found_lost_aggregate_pairs_capacity=2 ** 25,
                                 gpu_total_aggregate_pairs_capacity=2 ** 23, gpu_collision_stack_size=2 ** 28,
                                 gpu_heap_capacity=2 ** 27, gpu_temp_buffer_capacity=2 ** 25)))
    scene = InteractiveScene(SceneCfg(num_envs=n_env, env_spacing=a.spacing, replicate_physics=False))
    stage = omni.usd.get_context().get_stage()
    # finger material (production taskC_ffw_sg2.py _SG2_GRIPPER_MATERIAL: 2.0 / 1.8, combine max) on every gripper
    # collider; objects: catalog friction set after start through the physx view
    t_obj = time.time()
    cmap, obj_mode = {}, {}
    if a.collider == "auto" and os.path.exists(a.collider_map):
        cmap = json.load(open(a.collider_map)).get("objects", {})
    for i in range(n_env):
        k, row = tasks[owner[i]][0], tasks[owner[i]][1]
        pp = f"/World/envs/env_{i}/Obj"
        prim = stage.DefinePrim(pp, "Xform")
        prim.GetReferences().AddReference(row["usd_physics"])
        body = f"{pp}/{row['body_rel']}" if row.get("body_rel") else pp  # body_rel "" (e.g. GSO ood_o): rigid body is the reference root itself
        sim_utils.modify_rigid_body_properties(body, sim_utils.RigidBodyPropertiesCfg(max_depenetration_velocity=1.0))
        sim_utils.modify_mass_properties(body, sim_utils.MassPropertiesCfg(mass=float(row.get("mass", 0.3))))
        mode = (row.get("collider") or cmap.get(k)) if a.collider == "auto" else a.collider
        obj_mode[k] = mode or "none"
        if mode and mode != "none":
            GT.apply_collider(stage, pp, mode)
    # P164 regex: one physx view over every env's rigid body. Objaverse rows share "Geometry/obja_<uid>" (wildcard
    # over the uid); GSO ood_o rows have body_rel == "" (the body IS /Obj) -- no suffix. A chunk is one or the other
    # (load_tasks draws from one --ids file), never mixed.
    obj_suffix = "/Geometry/obja_.*" if any(t[1].get("body_rel") for t in tasks) else ""
    obj = RigidObject(RigidObjectCfg(prim_path=f"/World/envs/env_.*/Obj{obj_suffix}", spawn=None))
    log(f"authored {n_env} objects in {time.time() - t_obj:.0f}s")
    t_reset = time.time()
    sim.reset()
    scene.update(DT)
    obj.update(DT)
    log(f"sim.reset {time.time() - t_reset:.0f}s")
    paths = obj.root_physx_view.prim_paths
    bad = [i for i, pth in enumerate(paths) if not pth.startswith(f"/World/envs/env_{i}/")]
    if bad:
        raise RuntimeError(f"object view order != env order at {bad[:5]}: {[paths[i] for i in bad[:3]]}")
    rob = scene["grip"]
    dev = rob.device
    vids, _ = rob.find_joints(list(VIRT), preserve_order=True)
    fids, _ = rob.find_joints(fingers, preserve_order=True)
    fol = [(fingers.index(c), fingers.index(p)) for c, p in follow.items()]
    prox = [fingers.index(j) for j in fingers if j not in follow]
    log(f"hand {hand.kind}: fingers {fingers}, closed {[round(v, 3) for v in hand.q_closed]}, actuation {act}")
    tcp_b = rob.find_bodies([gj["tcp_link"]])[0][0]
    base_b = rob.find_bodies([gj["base_link"]])[0][0]
    origins = scene.env_origins.cpu().numpy().astype(float)
    # object friction (catalog), per env
    mats0 = obj.root_physx_view.get_material_properties()
    allidx = torch.arange(n_env, dtype=torch.int32)

    # friction. Production: finger material 2.0 / 1.8 with combine mode max (taskC_ffw_sg2.py _SG2_GRIPPER_MATERIAL)
    # -> effective = the finger value. The tensor API sets per-shape values only (combine mode stays average), so the
    # finger shapes get 2 * target - object value (average = target). Low friction: both 0.4.
    gm0 = rob.root_physx_view.get_material_properties()
    nsh = (mats0[:, :, 0] > 0).sum(1).numpy()
    obj_mu = np.array([tasks[owner[i]][1].get("friction", (0.8, 0.8)) for i in range(n_env)], float).reshape(n_env, -1)
    if obj_mu.shape[1] == 1:
        obj_mu = np.repeat(obj_mu, 2, 1)

    def set_fric():
        mo, mg = mats0.clone(), gm0.clone()
        for i in range(n_env):
            lowfric = bool(lowenv[i])
            fs, fd = (0.4, 0.4) if lowfric else (float(obj_mu[i, 0]), float(obj_mu[i, 1]))
            ts, td = (0.4, 0.4) if lowfric else (2.0, 1.8)
            mo[i, :, 0], mo[i, :, 1], mo[i, :, 2] = fs, fd, 0.0
            mg[i, :, 0], mg[i, :, 1], mg[i, :, 2] = 2 * ts - fs, 2 * td - fd, 0.0
        obj.root_physx_view.set_material_properties(mo, allidx)
        rob.root_physx_view.set_material_properties(mg, allidx)
        chk = rob.root_physx_view.get_material_properties()
        oc = obj.root_physx_view.get_material_properties()
        log(f"friction set: finger env0 {chk[0, 0, :2].tolist()} object env0 {oc[0, 0, :2].tolist()}"
            + (f" | low env1 finger {chk[1, 0, :2].tolist()} object {oc[1, 0, :2].tolist()}" if n_env > 1 else ""))

    set_fric()
    log(f"object shapes per env: max {int(nsh.max())}, per object " +
        str({tasks[m][0][-6:]: int(nsh[np.flatnonzero(owner == m)[0]]) for m in range(min(M, 12))}))

    # queue of (env-local) tests per object
    queues = {m: list(range(len(t[2]))) for m, t in enumerate(tasks)}
    res = {m: {"lift_ok": np.zeros(len(t[2]), bool), "shake_ok": np.zeros(len(t[2]), bool),
               "lowfric_ok": np.full(len(t[2]), -1, np.int8), "final_gap": np.full(len(t[2]), np.nan),
               "gap_hold": np.full(len(t[2]), np.nan), "gap_end": np.full(len(t[2]), np.nan),
               "slip_mm": np.full(len(t[2]), np.nan), "rise_end": np.full(len(t[2]), np.nan)}
           for m, t in enumerate(tasks)}
    q_open_cache = {}

    def width_q(w):
        if w not in q_open_cache:
            q_open_cache[w] = hand.q_open(w)
        return q_open_cache[w]

    def run_round(assign):
        """assign: list per env of (m, j) or None. Runs one test on every env, fills res."""
        n = n_env
        Tw = np.tile(np.eye(4), (n, 1, 1))
        root = np.zeros((n, 7))
        mloc = np.zeros((n, 3))  # grasp centre in the object body frame
        cloc = np.zeros((n, 3))  # canonical centre in the body frame
        c0z = np.zeros(n)
        qopen = np.zeros((n, len(fingers)))
        active = np.array([x is not None for x in assign])
        for i, x in enumerate(assign):
            m, j = x if x is not None else (owner[i], 0)
            k, row, idx, T, w, pre, av, neg, part = tasks[m]
            yaw = GT.yaw_for(av[j])
            c, q, rp, rq = GT.object_pose(row, yaw, origin=origins[i], lift=0.001)
            if x is None:  # idle env: object at rest, gripper parked 0.5 m above
                Tw[i] = GT.pose(np.eye(3), c + [0.0, 0.0, 0.5])
                mw = Tw[i, :3, 3].copy()
            else:
                Tg = GT.tcp_world(T[j], yaw, c)
                mw = Tg[:3, 3].copy()  # planned contact centre
                Tw[i] = GT.exec_pose(Tg, float(w[j]), a.grip, table, support_z=float(origins[i][2])) if a.pad_drop else Tg
            root[i, :3], root[i, 3:] = rp, rq
            Rb = qmat(rq)
            mloc[i] = Rb.T @ (mw - rp)
            cloc[i] = Rb.T @ (c - rp)
            c0z[i] = c[2]
            qopen[i] = width_q(float(pre[j]))
        traj, st = GT.plan_round(Tw, origins, tcp_in_base, DT, R_tb=R_tb)
        traj_t = torch.tensor(traj, dtype=torch.float32, device=dev)
        # reset states
        obj.write_root_pose_to_sim(torch.tensor(root, dtype=torch.float32,
                                                device=dev))
        obj.write_root_velocity_to_sim(torch.zeros((n, 6), device=dev))
        jp = rob.data.default_joint_pos.clone()
        jp[:, vids] = traj_t[0]
        qo = torch.tensor(qopen, dtype=torch.float32, device=dev)
        for c_ in range(len(fids)):
            jp[:, fids[c_]] = qo[:, c_]
        rob.write_joint_state_to_sim(jp, torch.zeros_like(jp))
        rob.set_joint_position_target(jp)
        mloc_t = torch.tensor(mloc, dtype=torch.float32, device=dev)
        cloc_t = torch.tensor(cloc, dtype=torch.float32, device=dev)
        from isaaclab.utils.math import quat_apply, quat_apply_inverse
        tgt = jp.clone()
        closed = torch.tensor([q_closed[j] for j in fingers], dtype=torch.float32, device=dev)
        rec = {}
        slip = torch.zeros(n, device=dev)
        ref = None
        fk_err = None

        def measure():
            op, oq = obj.data.root_pos_w, obj.data.root_quat_w
            tp, tq = rob.data.body_pos_w[:, tcp_b], rob.data.body_quat_w[:, tcp_b]
            mw = op + quat_apply(oq, mloc_t)
            cw = op + quat_apply(oq, cloc_t)
            mG = quat_apply_inverse(tq, mw - tp)
            fq = rob.data.joint_pos[:, fids]
            return mG, cw[:, 2], fq

        for kstep in range(st["end"]):
            tgt[:, vids] = traj_t[kstep]
            if kstep >= st["close"]:
                for c_ in prox:
                    tgt[:, fids[c_]] = closed[c_]
                for c_, p_ in fol:
                    tgt[:, fids[c_]] = rob.data.joint_pos[:, fids[p_]]
            rob.set_joint_position_target(tgt)
            scene.write_data_to_sim()
            obj.write_data_to_sim()
            sim.step(render=False)
            scene.update(DT)
            obj.update(DT)
            if kstep == 0 and fk_err is None:
                bp = rob.data.body_pos_w[:, base_b].cpu().numpy()
                qj = rob.data.joint_pos[:, vids].cpu().numpy()
                fk_err = float(np.abs(bp - (qj[:, :3] + origins)).max())
                bq = rob.data.body_quat_w[:, base_b].cpu().numpy()
                rerr = max(float(np.abs(qmat(bq[i]) - GT.rot_xyz(*qj[i, 3:])).max()) for i in range(min(n, 64)))
                rec["fk"] = (fk_err, rerr)
            if kstep == st["lift"] - 1:
                rec["close"] = measure()
            if kstep == st["shake"] - 1:
                rec["hold"] = measure()
                ref = rec["hold"][0]
            if kstep >= st["shake"] and ref is not None:
                mG, _, _ = measure()
                slip = torch.maximum(slip, torch.linalg.norm(mG - ref, dim=1))
        rec["end"] = measure()
        out = {}
        for key in ("close", "hold", "end"):
            mG, cz, fq = (v.cpu().numpy() for v in rec[key])
            out[key] = (mG, cz - c0z, hand.width(fq), GT.pad_drop_q(hand.drive_q(fq), a.grip))
        sl = slip.cpu().numpy()
        for i, x in enumerate(assign):
            if x is None:
                continue
            m, j = x
            # between the fingers: from the (arc-lowered) pad bottom up to the palm (PALM_Z above the TCP)
            ins = lambda key: GT.inside(out[key][0][i], pad_w, max_open, (pad_z[0] - out[key][3][i], max(PALM_Z, pad_z[1])))
            v = GT.verdict(out["hold"][1][i], ins("hold"), out["hold"][2][i], out["end"][1][i], ins("end"),
                           out["end"][2][i], sl[i])
            r = res[m]
            if lowenv[i]:
                r["lowfric_ok"][j] = int(v["shake_ok"])
            else:
                r["lift_ok"][j], r["shake_ok"][j] = v["lift_ok"], v["shake_ok"]
                r["final_gap"][j], r["gap_hold"][j], r["gap_end"][j] = out["close"][2][i], out["hold"][2][i], out["end"][2][i]
                r["slip_mm"][j], r["rise_end"][j] = sl[i] * 1000, out["end"][1][i]
        return rec["fk"], int(active.sum())

    def rounds():
        qs = {m: list(range(len(t[2]))) for m, t in enumerate(tasks)}
        r_i = 0
        while any(qs.values()):
            assign, took = [], {}
            for i in range(n_env):
                m, key = owner[i], (owner[i], slot[i])
                if key not in took:
                    took[key] = qs[m].pop(0) if qs[m] else None
                assign.append(None if took[key] is None else (m, took[key]))
            t0 = time.time()
            fk, na = run_round(assign)
            log(f"round {r_i}: {na} envs {time.time() - t0:.1f}s fk_pos_err {fk[0]:.2e} m rot_err {fk[1]:.2e}")
            r_i += 1

    t_run = time.time()
    rounds()
    dt_run = time.time() - t_run
    od = os.path.join(a.out, a.grip)
    os.makedirs(od, exist_ok=True)
    lg = open(os.path.join(od, "_log.jsonl"), "a")
    n_tests = 0
    for m, t in enumerate(tasks):
        k, row, idx, T, w, pre, av, neg, part = t
        r = res[m]
        n_tests += len(idx)
        fam = [GT.fam_obj(x) for x in av]
        if a.neg:
            for j in range(len(idx)):
                log(f"ROW {k[:22]:22s} {row.get('l9cat', ''):12s} j={j:2d} {'NEG' + str(-idx[j]) if neg[j] else fam[j]:10s} {part[j]:6s} "
                    f"w={w[j] * 100:5.1f}cm pre={pre[j] * 100:5.1f} gap_close={r['final_gap'][j] * 100:5.1f} "
                    f"gap_end={r['gap_end'][j] * 100:5.1f} rise={r['rise_end'][j] * 100:5.1f}cm slip={r['slip_mm'][j]:6.1f}mm "
                    f"lift={int(r['lift_ok'][j])} shake={int(r['shake_ok'][j])} lowfric={int(r['lowfric_ok'][j])}")
        keep = ~neg
        # 'pass' over ALL candidates of the grasps npz (its order): tested, shake ok at catalog friction and (when
        # the low-friction pair ran) shake ok at friction 0.4; untested candidates are False (rt9 reads it)
        K = int(np.load(os.path.join(a.grasps, a.grip, k + ".npz"))["w"].shape[0])
        ok = r["shake_ok"][keep] & (r["lowfric_ok"][keep] != 0)
        pas = np.zeros(K, bool)
        pas[idx[keep]] = ok
        tested = np.zeros(K, bool)
        tested[idx[keep]] = True
        pas_sh = np.zeros(K, bool)  # shake ok at catalog friction only (without the 0.4 pass)
        pas_sh[idx[keep]] = r["shake_ok"][keep]
        np.savez_compressed(os.path.join(od, k + ".npz"), idx=idx[keep], lift_ok=r["lift_ok"][keep],
                            **{"pass": pas}, pass_shake=pas_sh, tested=tested, pad_drop=bool(a.pad_drop), collider=str(obj_mode.get(k, "none")),
                            shake_ok=r["shake_ok"][keep], lowfric_ok=r["lowfric_ok"][keep],
                            final_gap=r["final_gap"][keep], gap_hold=r["gap_hold"][keep], gap_end=r["gap_end"][keep],
                            slip_mm=r["slip_mm"][keep], rise_end=r["rise_end"][keep], w=w[keep], pre_open=pre[keep],
                            family=np.array(fam)[keep].astype(str), part=part[keep].astype(str))
        s = {"id": k, "l9cat": row.get("l9cat"), "n": int(keep.sum()), "lift": int(r["lift_ok"][keep].sum()),
             "shake": int(r["shake_ok"][keep].sum()), "lowfric": int((r["lowfric_ok"][keep] == 1).sum()),
             "lowfric_run": bool(a.lowfric)}
        for f_ in GT.FAMS:
            mk = keep & (np.array(fam) == f_)
            s[f_] = [int(mk.sum()), int(r["shake_ok"][mk].sum())]
        s["by_fp"] = {}
        for j in np.flatnonzero(keep):
            e = s["by_fp"].setdefault(f"{fam[j]}|{part[j]}|{GT.width_class(w[j])}", [0, 0])
            e[0] += 1
            e[1] += int(r["shake_ok"][j])
        lg.write(json.dumps(s) + "\n")
    lg.close()
    log(f"DONE objects {M} tests {n_tests} run {dt_run:.0f}s total {time.time() - t_boot:.0f}s "
        f"({n_tests / max(dt_run, 1e-9):.1f} tests/s)")


if __name__ == "__main__":
    main()
