"""L9 v2 cuRobo configs by robot profile (spec §12.1/§12.5; cuRobo v0.8.0 ONLY, Apache-2.0 -- v0.7.8 and older are NC).

Pure path / lookup logic + one pod function `make_ik`. Planning and execution live in the owner's motion code.

Frames (all configs):
- base_link(profile, arm): the link the arm chain hangs from, after every per-episode joint (AI Worker lift, R1 Pro
  torso 1-4, G1 waist): ffw_sg2 arm_base_link, franka_mast panda_link0, r1pro torso_link4, g1 torso_link. Put the
  world (obstacles) into this frame from the sim link pose each episode.
- tool_frame(profile, arm) = "<arm>_l9_tcp", a fixed link in the prepared URDF: origin = the pad centre the L9
  executor targets, z = -approach (points from the fingers back to the wrist), y = finger closing axis. This IS the
  grasp frame G of world9/OraclePlanner (top-down grasp at yaw 0 = identity in the base frame): T_tool_G = I.
- Only the 7 arm joints (arm_joints(), cuRobo order) are planned; everything else below the base (other arm stowed,
  head, fingers open) is in lock_joints.

Configs: assets9/curobo/<robot>_<arm>.yml (built by tools/l9/v2robot/build_curobo9.py). They name the prepared URDF
under /data/harvest/assets_l9v2/robots (pod); env L9V2_ASSET_ROOT moves that root.
Reach maps: assets9/reach_v2/<profile>_<arm>.json (tools/l9/v2robot/reach_v2.py), looked up by reach_ok()."""
from __future__ import annotations

import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CFG_DIR = os.path.join(HERE, "assets9", "curobo")
REACH_DIR = os.path.join(HERE, "assets9", "reach_v2")
ASSET_ROOT = "/data/harvest/assets_l9v2/robots"
CUROBO_VERSION = "0.8.0"

# robot9 profile name -> (config robot name, arms)
PROFILES = {"ffw_sg2": ("ffw_sg2", ("right", "left")), "franka_mast": ("franka", ("right",)),
            "r1pro": ("r1pro", ("right", "left")), "g1": ("g1", ("right", "left"))}
APPROACHES = ("top", "oblique", "front", "side")
TOP_MAX_DEG, OBLIQUE_MAX_DEG, FRONT_MAX_DEG = 25.0, 65.0, 45.0  # spec §12.8 approach classes
T_TOOL_G = np.eye(4)  # tool frame == the executor grasp frame G


def check(profile: str, arm: str) -> tuple:
    if profile not in PROFILES:
        raise ValueError(f"profile {profile!r}: one of {tuple(PROFILES)}")
    robot, arms = PROFILES[profile]
    if arm not in arms:
        raise ValueError(f"{profile}: arm {arm!r} not in {arms}")
    return robot, arm


def config_path(profile: str, arm: str) -> str:
    robot, arm = check(profile, arm)
    return os.path.join(CFG_DIR, f"{robot}_{arm}.yml")


def load_config(profile: str, arm: str) -> dict:
    """The cuRobo robot dict {"robot_cfg": {"kinematics": ...}} with the asset root resolved (L9V2_ASSET_ROOT)."""
    import yaml
    d = yaml.safe_load(open(config_path(profile, arm)))
    k = d["robot_cfg"]["kinematics"]
    root = os.environ.get("L9V2_ASSET_ROOT")
    if root:
        for key in ("urdf_path", "asset_root_path"):
            k[key] = k[key].replace(ASSET_ROOT, root.rstrip("/"))
    if os.environ.get("L9_CSPACE_READY") == "1":
        cspace_ready(profile, arm, k)
    return d


def cspace_ready(profile: str, arm: str, k: dict) -> None:
    """Opt-in L9_CSPACE_READY=1, every robot with a measured ready / stow pose (robot9.V2_READY / V2_STOW, robot
    data): cuRobo's cspace.default_joint_position (the IK null-space / retract bias) = the arm's ready pose and the
    other arm's stow pose, instead of the all-zero straight-arm singular posture the G1 / R1 Pro configs were built
    with (AI Worker / Franka configs already carry a bent ready pose). Joints without data keep their value."""
    from . import robot9 as RB
    ready, stow = getattr(RB, "V2_READY", {}).get(profile), getattr(RB, "V2_STOW", {}).get(profile)
    arms = (getattr(RB, "V2", {}).get(profile) or {}).get("arms")
    if not ready or not arms:
        return
    want = {}
    for s, a in arms.items():
        q = ready.get(s) if s == arm else (stow or {}).get(s)
        if q:
            want.update(zip(a["joints"], q))
    cs = k.get("cspace") or {}
    names, dflt = cs.get("joint_names") or [], list(cs.get("default_joint_position") or [])
    if len(names) == len(dflt):
        cs["default_joint_position"] = [float(want.get(n, v)) for n, v in zip(names, dflt)]


def base_link(profile: str, arm: str) -> str:
    return load_config(profile, arm)["robot_cfg"]["kinematics"]["base_link"]


def tool_frame(profile: str, arm: str) -> str:
    return load_config(profile, arm)["robot_cfg"]["kinematics"]["tool_frames"][0]


def arm_joints(profile: str, arm: str) -> list:
    """The planned joints in cuRobo order (= cspace order minus the locked ones)."""
    k = load_config(profile, arm)["robot_cfg"]["kinematics"]
    lock = set(k.get("lock_joints") or {})
    return [j for j in k["cspace"]["joint_names"] if j not in lock]


def lock_joints(profile: str, arm: str) -> dict:
    return dict(load_config(profile, arm)["robot_cfg"]["kinematics"].get("lock_joints") or {})


def with_locks(cfg: dict, lock_overrides: dict | None) -> dict:
    """Config dict with some lock_joints values replaced (e.g. finger joints at a pre-open width). cuRobo v0.8.0 bakes
    locked joints into fixed transforms when the solver is built (kinematics_loader._build_kinematics_with_lock_joints),
    so a new value needs a new solver: keep a few solvers (e.g. 2-3 finger openings), do not rebuild per call."""
    if not lock_overrides:
        return cfg
    k = cfg["robot_cfg"]["kinematics"]
    bad = set(lock_overrides) - set(k["lock_joints"])
    if bad:
        raise ValueError(f"not locked joints: {sorted(bad)}")
    k["lock_joints"] = {**k["lock_joints"], **{j: float(v) for j, v in lock_overrides.items()}}
    return cfg


def make_ik(profile: str, arm: str, device: str = "cuda:0", num_seeds: int = 32, max_batch_size: int = 1,
            self_collision_check: bool = True, lock_overrides: dict | None = None, **kw):
    """(pod) cuRobo v0.8.0 InverseKinematics for (profile, arm); kw go to InverseKinematicsCfg.create (scene_model,
    collision_cache, max_goalset, position_tolerance ...). lock_overrides: see with_locks."""
    import curobo
    import torch
    from curobo.inverse_kinematics import InverseKinematics, InverseKinematicsCfg
    from curobo.types import DeviceCfg
    if not str(curobo.__version__).startswith(CUROBO_VERSION):
        raise RuntimeError(f"cuRobo {curobo.__version__}: L9 v2 uses {CUROBO_VERSION} only (older = NC licence)")
    cfg = InverseKinematicsCfg.create(robot=with_locks(load_config(profile, arm), lock_overrides), num_seeds=num_seeds,
                                      max_batch_size=max_batch_size, self_collision_check=self_collision_check,
                                      device_cfg=DeviceCfg(device=torch.device(device)), **kw)
    return InverseKinematics(cfg)


# ------------------------------------------------------------------------------------------------- approach classes
def approach_class(a, obj_xy_base=(1.0, 0.0)) -> str:
    """Spec §12.8 class of an approach vector a (direction the gripper moves, base frame; z up): angle to straight down
    < 25 deg top, 25-65 oblique, else front if the horizontal part is within 45 deg of the base -> object horizontal
    direction, else side."""
    a = np.asarray(a, float)
    a = a / np.linalg.norm(a)
    th = math.degrees(math.acos(max(-1.0, min(1.0, -a[2]))))
    if th < TOP_MAX_DEG:
        return "top"
    if th <= OBLIQUE_MAX_DEG:
        return "oblique"
    f = np.asarray(obj_xy_base[:2], float)
    h = a[:2]
    if np.linalg.norm(f) < 1e-9 or np.linalg.norm(h) < 1e-9:
        return "side"
    c = float(h @ f / (np.linalg.norm(h) * np.linalg.norm(f)))
    return "front" if math.degrees(math.acos(max(-1.0, min(1.0, c)))) < FRONT_MAX_DEG else "side"


# ------------------------------------------------------------------------------------------------- reach maps
_REACH = {}


def reach_path(profile: str, arm: str) -> str:
    check(profile, arm)
    return os.path.join(REACH_DIR, f"{profile}_{arm}.json")


def reach_map(profile: str, arm: str) -> dict:
    key = (profile, arm)
    if key not in _REACH:
        _REACH[key] = json.load(open(reach_path(profile, arm)))
    return _REACH[key]


def reach_ok(profile: str, arm: str, xyz_base, approach: str) -> bool:
    """True if the reach-map cell nearest to xyz_base (base_link frame, m) had at least one collision-free IK
    solution for that approach class (cuRobo batched IK, self-collision on, no world). Outside the grid -> False.
    Classes are taken in the cuRobo base frame: for R1 Pro the base (torso_link4) leans robot9.R1_LEAN forward, so
    classify the world approach after rotating it into that frame (the map was built at the R1_LEAN posture)."""
    if approach not in APPROACHES:
        raise ValueError(f"approach {approach!r}: one of {APPROACHES}")
    m = reach_map(profile, arm)
    g = m["grid"]
    idx = []
    for ax, v in zip("xyz", xyz_base):
        lo, step, n = g[ax]["lo"], g[ax]["step"], g[ax]["n"]
        i = int(round((float(v) - lo) / step))
        if i < 0 or i >= n:
            return False
        idx.append(i)
    flat = (idx[0] * g["y"]["n"] + idx[1]) * g["z"]["n"] + idx[2]
    return m["ok"][approach][flat] == "1"
