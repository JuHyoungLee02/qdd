# 과제 C 의 로봇 -- 학습 데이터(HF taskC/ 960편)와 동봉 시연을 찍을 때 쓴 FFW-SG2 설정 그대로.
#
# 이미지 안의 공용 `cyclo_lab/assets/robots/FFW_SG2.py` 는 과제 A·B 기준으로 조정된 판(팔 강성 6000, 리프트
# 300000, 리프트 초기값 -0.05, 그리퍼 마찰 4.0 등)이다. 과제 C 의 기록은 그보다 무른 팔·손목, 좌/우가 다른
# 그리퍼 강성(스캐너를 쥔 오른손 100, 상품을 쥐는 왼손 300), 마찰 2.0/1.8 위에서 만들어졌고, 재생기는 그 관절
# 명령을 물리로 다시 돌리므로 같은 로봇이어야 파지·스윕이 재현된다. 액추에이터만 바꿔 끼우는 것으로는 부족했다
# (스폰 함수 안의 그리퍼 재질·미믹 설정까지 달라 GT 재생에서 세 번째 상품 파지가 재현되지 않았다). 그래서
# 파일 전체를 과제 C 것으로 들고 다닌다. 공용 파일은 손대지 않는다.
#
#   from taskC.taskC_ffw_sg2 import FFW_SG2_MOBILE_CFG, SG2_SWERVE_STEERING_JOINTS, SG2_SWERVE_WHEEL_JOINTS
#
# 원본: cstore-challenge `task-c` 브랜치 source/cyclo_lab/cyclo_lab/assets/robots/FFW_SG2.py (데이터 수집 판).
# 아래는 그 파일을 그대로 옮긴 것이다.
#
# Copyright 2025 ROBOTIS CO., LTD.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: Taehyeong Kim

import re
from copy import deepcopy

from isaacsim.core.utils.stage import get_current_stage
from pxr import Sdf, Usd, UsdPhysics

from isaaclab.sim import (
    ArticulationRootPropertiesCfg,
    RigidBodyMaterialCfg,
    RigidBodyPropertiesCfg,
    UsdFileCfg,
)
from isaaclab.assets.articulation import ArticulationCfg
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.sim.spawners.from_files import from_files
from isaaclab.sim.utils import bind_physics_material, clone, make_uninstanceable

from cyclo_lab.assets.robots import CYCLO_LAB_ASSETS_DATA_DIR

# 로봇 USD -- 배포 이미지는 data/robot/ffw_sg2.usd, 개발 체크아웃은 data/robots/FFW/FFW_SG2.usd.
# 공용 FFW_SG2.py 는 빌드가 이 줄을 고쳐 쓰지만 이 사본은 그 패치를 거치지 않으므로 둘 다 본다.
_ROBOT_USD = next((p for p in (f"{CYCLO_LAB_ASSETS_DATA_DIR}/robot/ffw_sg2.usd",
                              f"{CYCLO_LAB_ASSETS_DATA_DIR}/robots/FFW/FFW_SG2.usd")
                   if __import__("os").path.isfile(p)),
                  f"{CYCLO_LAB_ASSETS_DATA_DIR}/robots/FFW/FFW_SG2.usd")

FFW_SG2_CFG = ArticulationCfg(
    spawn=UsdFileCfg(
        usd_path=_ROBOT_USD,
        rigid_props=RigidBodyPropertiesCfg(
            disable_gravity=True,
            max_depenetration_velocity=5.0,
        ),
        articulation_props=ArticulationRootPropertiesCfg(
            enabled_self_collisions=True,
            solver_position_iteration_count=32,
            solver_velocity_iteration_count=1,
        ),
        activate_contact_sensors=False,
    ),
    init_state=ArticulationCfg.InitialStateCfg(
        joint_pos={
            # # Swerve base joints
            # "left_wheel_drive": 0.0, "left_wheel_steer": 0.0,
            # "right_wheel_drive": 0.0, "right_wheel_steer": 0.0,
            # "rear_wheel_drive": 0.0, "rear_wheel_steer": 0.0,

            # Left arm joints
            **{f"arm_l_joint{i + 1}": 0.0 for i in range(7)},
            # Right arm joints
            **{f"arm_r_joint{i + 1}": 0.0 for i in range(7)},

            # Left and right gripper joints
            **{f"gripper_l_joint{i + 1}": 0.0 for i in range(4)},
            **{f"gripper_r_joint{i + 1}": 0.0 for i in range(4)},

            # Head joints
            "head_joint1": 0.0,
            "head_joint2": 0.0,

            # Lift joint
            "lift_joint": 0.0,
        },
    ),
    actuators={
        # Actuators for swerve base
        # "base": ImplicitActuatorCfg(
        #     joint_names_expr=[
        #         "left_wheel_drive", "left_wheel_steer",
        #         "right_wheel_drive", "right_wheel_steer",
        #         "rear_wheel_drive", "rear_wheel_steer",
        #     ],
        #     velocity_limit_sim=30.0,
        #     effort_limit_sim=100000.0,
        #     stiffness=10000.0,
        #     damping=100.0,
        # ),

        # Actuator for vertical lift joint
        "lift": ImplicitActuatorCfg(
            joint_names_expr=["lift_joint"],
            velocity_limit_sim=0.2,
            effort_limit_sim=1000000.0,
            stiffness=10000.0,
            damping=100.0,
        ),

        # Actuators for both arms
        "DY_80": ImplicitActuatorCfg(
            joint_names_expr=[
                "arm_l_joint[1-2]",
                "arm_r_joint[1-2]",
            ],
            velocity_limit_sim=15.0,
            effort_limit_sim=61.4,
            stiffness=600.0,
            damping=30.0,
        ),
        "DY_70": ImplicitActuatorCfg(
            joint_names_expr=[
                "arm_l_joint[3-6]",
                "arm_r_joint[3-6]",
            ],
            velocity_limit_sim=15.0,
            effort_limit_sim=31.7,
            stiffness=600.0,
            damping=20.0,
        ),
        "DP-42" : ImplicitActuatorCfg(
            joint_names_expr=[
                "arm_l_joint7",
                "arm_r_joint7",
            ],
            velocity_limit_sim=6.0,
            effort_limit_sim=5.1,
            stiffness=200.0,
            damping=3.0,
        ),

        # Actuators for grippers
        # stiffness 300, was 100. These are position-controlled jaws: once they close onto an
        # object the joint stops at whatever angle the object allows, and the squeeze is
        # stiffness x (commanded - actual). Measured while carrying a coke can, that error settles
        # near 0.12 rad, so 100 gave only 10-12 N.m of a 30 N.m budget -- and the can rotated
        # 4.6 -> 44.5 deg in the jaws during the `present` leg, which turns the wrist hard.
        # 300 uses the effort limit that was already there rather than raising it.
        # SPLIT BY HAND, and the two want different numbers. These are position-controlled jaws:
        # once they close onto an object the joint stops where the object allows and the squeeze is
        # stiffness x (commanded - actual).
        #
        # LEFT (products) at 300. At 100 the error settled near 0.12 rad, giving only 10-12 N.m of
        # a 30 N.m budget, and a coke can rotated 4.6 -> 44.5 deg in the jaws during the `present`
        # leg. At 300 the same variant came out 48 mm from its slot and dead upright.
        #
        # RIGHT (scanner) stays at 100. 300 on both hands broke the scanner pickup outright --
        # "STILL ON THE COUNTER" -- because the handle is slim and a hard squeeze shoots it out.
        # The number that fits a 70 mm cylinder is not the number that fits a handle.
        "gripper_master_l": ImplicitActuatorCfg(
            joint_names_expr=["gripper_l_joint1"],
            velocity_limit_sim=2.2,
            effort_limit_sim=30.0,
            stiffness=300.0,
            damping=4.0,
        ),
        "gripper_master_r": ImplicitActuatorCfg(
            joint_names_expr=["gripper_r_joint1"],
            velocity_limit_sim=2.2,
            effort_limit_sim=30.0,
            stiffness=100.0,
            damping=4.0,
        ),
        "gripper_slave": ImplicitActuatorCfg(
            joint_names_expr=["gripper_l_joint[2-4]", "gripper_r_joint[2-4]"],
            effort_limit_sim=20.0,
            stiffness=2.0,
            damping=0.5,
        ),

        # Actuators for head joints
        "head": ImplicitActuatorCfg(
            joint_names_expr=["head_joint1", "head_joint2"],
            velocity_limit_sim=2.0,
            effort_limit_sim=30.0,
            stiffness=150.0,
            damping=3.0,
        ),
    }
)


##
# The MOBILE AI Worker.
#
# FFW-SG2 is the mobile AI Worker: ffw_sg2_follower.urdf puts it on a 3-wheel swerve base.
#
# FFW_SG2_CFG above parks the robot: the USD carries a FixedJoint to the world and the wheels
# are unactuated, which is what the real-world teleop task wants.
#
# Everything below follows ROBOTIS's own reference implementation for the other mobile AI
# Worker, FFW_SH5.py (author: Howon Kim) -- the physics material is bound and the collision
# filters are applied inside a custom spawn function, so the shipped USD is never modified.
##

# ROBOTIS's fingertip material, verbatim from FFW_SH5.py. FFW_SG2.usd carries no UsdPhysics
# material at all, so without this every contact runs on PhysX's default and the hand slips.
_SG2_GRIPPER_MATERIAL = RigidBodyMaterialCfg(
    friction_combine_mode="max",
    restitution_combine_mode="min",
    static_friction=2.0,
    dynamic_friction=1.8,
    restitution=0.0,
)

_SG2_WHEEL_DRIVE_LINKS = ("left_wheel_drive_link", "right_wheel_drive_link", "rear_wheel_drive_link")

# Swerve geometry. FFW_SH5.py declares the same module offsets and wheel radius, and they
# match what FFW_SG2.usd measures out to.
SG2_SWERVE_STEERING_JOINTS = ("left_wheel_steer", "right_wheel_steer", "rear_wheel_steer")
SG2_SWERVE_WHEEL_JOINTS = ("left_wheel_drive", "right_wheel_drive", "rear_wheel_drive")
SG2_SWERVE_MODULE_X_OFFSETS = (0.1371, 0.1374, -0.289)
SG2_SWERVE_MODULE_Y_OFFSETS = (0.2554, -0.2554, 0.0)
SG2_SWERVE_MODULE_ANGLE_OFFSETS = (0.0, 0.0, 0.0)
SG2_SWERVE_WHEEL_RADIUS = 0.0865
# How far a swerve module can actually steer, from FFW_SH5.usd's *_wheel_steer_joint limits.
SG2_SWERVE_STEER_LIMIT_DEG = 90.52732849121094

# 2026-09-11: 머리 피치의 하향 상한.
#
# ffw_sg2_follower.urdf 는 head_joint1 을 lower=-0.2317 upper=+0.6951 (-13.3 ~ +39.8 도)로
# 적는다. 그런데 ROBOTIS 하드웨어 사양표(Joint Configuration and Nomenclature)는 같은 관절을
# -50 ~ 30 도로 적고, ffw_teleop/keyboard_control.py 는 +/-1.0 rad(+/-57.3 도)까지 명령을
# 허용한다. 세 값이 다르고 사양표에는 부호 방향이 적혀 있지 않다. 확정되기 전까지 45 도를
# 쓴다 -- 어느 읽기에서도 종전 조합(관절 39.8 + 카메라 30 = 69.8 도)보다 실기에 가깝다.
SG2_HEAD_PITCH_LIMIT_DEG = 45.0

# FFW-SG2's base link is called `world` (FFW-SH5 calls its own `base_link`).
_SG2_BASE_LINK = "world"

# r2/l2 are two joints out from arm_?_link7, so PhysX does not auto-filter them against the
# gripper mount they fold into. SH5 has the same problem on its hand and solves it with
# _filter_sh5_base_finger_collisions().
_SG2_GRIPPER_JAW_RE = re.compile(r"(^|/)gripper_[lr]_rh_p12_rn_[lr][12](/|_|$)")
_SG2_HAND_BASE_RE = re.compile(r"(^|/)arm_[lr]_link7/collisions(/|_|$)")

# The head sits ON the trunk, so its restored collider is permanently inside the trunk's and
# head_joint1 jams short of every command (measured on the AI Worker's fixed-base variant:
# 0.4295 rad against a 0.695 command). Same mount-vs-mounted structure as the hand.
_SG2_HEAD_RE = re.compile(r"(^|/)head_link[12]/collisions(/|_|$)")
_SG2_TRUNK_RE = re.compile(r"(^|/)(world|arm_base_link)/collisions(/|_|$)")


def _iter_robot_prims(stage, prim_path: str):
    robot_prim = stage.GetPrimAtPath(prim_path)
    if not robot_prim.IsValid():
        return ()
    return Usd.PrimRange(robot_prim)


def _is_sg2_gripper_jaw_prim(prim_path: str) -> bool:
    """The jaws of each RH-P12-RN hand -- the links that actually touch an object."""
    return _SG2_GRIPPER_JAW_RE.search(prim_path.lower()) is not None


def _add_filtered_collision_pairs(stage, source_paths: list[str], target_paths: list[str]) -> None:
    for source_path in source_paths:
        source_prim = stage.GetPrimAtPath(source_path)
        filtered_pairs_api = UsdPhysics.FilteredPairsAPI.Apply(source_prim)
        filtered_pairs_rel = filtered_pairs_api.CreateFilteredPairsRel()
        for target_path in target_paths:
            filtered_pairs_rel.AddTarget(Sdf.Path(target_path))


def _restore_missing_colliders(stage, prim_path: str) -> None:
    """Give every link back a collider, which is the state FFW_SH5.usd ships in.

    SH5 -- the finished ROBOTIS asset -- has 67 colliders and not one disabled: exactly one
    live collider on every link. FFW_SG2.usd is halfway through the same authoring pass and
    stopped in the middle of it. Someone was replacing the imported mesh colliders with cheap
    primitive proxies (a Cube on the base, a Cylinder on arm links 1-5) and got as far as:

        base `world`      mesh off, 2 Cube proxies on      <- done
        arm_?_link1..5    mesh off, Cylinder proxy on      <- done
        rear wheel        mesh on                          <- untouched, fine
        arm_?_link6       mesh off, NO proxy               <- left with no collider
        head_link1/2      mesh off, NO proxy               <- left with no collider
        arm_base_link     mesh off, NO proxy               <- left with no collider
        left/right wheel  mesh off, NO proxy               <- left with no collider

    The wheels give it away: the REAR wheel still collides and the left and right ones do not.
    Nobody designs a three-wheel robot that rolls on one wheel -- the base drops through the
    floor onto whatever proxy still touches it. So these flags are an unfinished pass, not a
    design decision.

    This re-enables a collider only on links that would otherwise have NONE, and leaves every
    link that already has a live collider completely alone -- so the deliberate Cube/Cylinder
    proxies stay exactly as ROBOTIS authored them. On an asset finished like SH5 it is a no-op.
    """
    restored = []
    for body_prim in _iter_robot_prims(stage, prim_path):
        if not body_prim.HasAPI(UsdPhysics.RigidBodyAPI):
            continue
        colliders = [c for c in Usd.PrimRange(body_prim) if c.HasAPI(UsdPhysics.CollisionAPI)]
        if not colliders:
            continue

        def _enabled(prim) -> bool:
            attr = UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr()
            return attr.Get() if attr and attr.HasAuthoredValue() else True

        if any(_enabled(c) for c in colliders):
            continue  # link already collides -- ROBOTIS's authoring, do not touch it
        for collider in colliders:
            UsdPhysics.CollisionAPI(collider).CreateCollisionEnabledAttr().Set(True)
        restored.append(body_prim.GetName())

    if restored:
        print(f"[SG2 collider restore] re-enabled collision on {len(restored)} link(s) that had "
              f"none: {', '.join(sorted(restored))}")


def _filter_sg2_base_wheel_drive_collisions(stage, prim_path: str) -> None:
    """Disable collision checks between the base link and the swerve drive wheel links.

    Straight transcription of FFW_SH5.py's _filter_sh5_base_wheel_drive_collisions(); the base
    proxy overhangs the wheels it carries, so without this they are in permanent contact.
    """
    base_collision_paths = []
    wheel_drive_collision_paths = []
    wheel_drive_pattern = "|".join(re.escape(link) for link in _SG2_WHEEL_DRIVE_LINKS)

    for child_prim in _iter_robot_prims(stage, prim_path):
        child_path = str(child_prim.GetPath())
        if "/collisions/" not in child_path:
            continue
        lower_path = child_path.lower()
        if re.search(rf"(^|/){_SG2_BASE_LINK}/collisions(/|_|$)", lower_path):
            base_collision_paths.append(child_path)
        elif re.search(rf"(^|/)({wheel_drive_pattern})/collisions(/|_|$)", lower_path):
            wheel_drive_collision_paths.append(child_path)

    if not base_collision_paths or not wheel_drive_collision_paths:
        return

    _add_filtered_collision_pairs(stage, base_collision_paths, wheel_drive_collision_paths)
    _add_filtered_collision_pairs(stage, wheel_drive_collision_paths, base_collision_paths)
    print(f"[SG2 collision filter] disabled {_SG2_BASE_LINK} collision with the drive wheels.")


def _filter_sg2_hand_base_jaw_collisions(stage, prim_path: str) -> None:
    """Disable collision checks between each gripper mount (arm_?_link7) and its jaws.

    The direct analogue of FFW_SH5.py's _filter_sh5_base_finger_collisions().
    """
    hand_base_paths = []
    jaw_paths = []

    for child_prim in _iter_robot_prims(stage, prim_path):
        child_path = str(child_prim.GetPath())
        if "/collisions/" not in child_path:
            continue
        lower_path = child_path.lower()
        if _SG2_HAND_BASE_RE.search(lower_path):
            hand_base_paths.append(child_path)
        elif _SG2_GRIPPER_JAW_RE.search(lower_path):
            jaw_paths.append(child_path)

    if not hand_base_paths or not jaw_paths:
        return

    _add_filtered_collision_pairs(stage, hand_base_paths, jaw_paths)
    _add_filtered_collision_pairs(stage, jaw_paths, hand_base_paths)
    print("[SG2 collision filter] disabled arm_?_link7 collision with the RH-P12-RN jaws.")


def _filter_sg2_head_trunk_collisions(stage, prim_path: str) -> None:
    """Disable collision checks between the head links and the trunk they are mounted on.

    The head keeps its collider against everything else, which is the point: this robot drives
    down aisles and has to be able to bump its head on a shelf.
    """
    head_paths = []
    trunk_paths = []

    for child_prim in _iter_robot_prims(stage, prim_path):
        child_path = str(child_prim.GetPath())
        if "/collisions/" not in child_path:
            continue
        lower_path = child_path.lower()
        if _SG2_HEAD_RE.search(lower_path):
            head_paths.append(child_path)
        elif _SG2_TRUNK_RE.search(lower_path):
            trunk_paths.append(child_path)

    if not head_paths or not trunk_paths:
        return

    _add_filtered_collision_pairs(stage, head_paths, trunk_paths)
    _add_filtered_collision_pairs(stage, trunk_paths, head_paths)
    print("[SG2 collision filter] disabled head collision with the trunk (world, arm_base_link).")


def _raise_sg2_head_pitch_limit(stage, prim_path: str) -> None:
    """Let head_joint1 pitch down to SG2_HEAD_PITCH_LIMIT_DEG.

    The shipped URDF stops the head at +0.6951 rad (39.83 deg). Task C has to look further
    down than that to keep the counter's work area in frame. The old build made up the
    difference by rotating the camera prim 30 deg, but the real ZED is bolted to head_link2
    with rpy 0 0 0 -- that rotation does not exist on the robot. Moving it into the joint is
    the only version a real arm can reproduce.

    Applied at spawn rather than by editing the shipped USD, the same way the wheel joints
    are. Only the upper (downward) limit moves; the upward limit is left as authored.
    """
    for child_prim in _iter_robot_prims(stage, prim_path):
        if child_prim.GetName() != "head_joint1":
            continue
        if not child_prim.IsA(UsdPhysics.RevoluteJoint):
            continue
        joint = UsdPhysics.RevoluteJoint(child_prim)
        was = joint.GetUpperLimitAttr().Get()
        if was is not None and float(was) >= SG2_HEAD_PITCH_LIMIT_DEG:
            return
        joint.CreateUpperLimitAttr().Set(SG2_HEAD_PITCH_LIMIT_DEG)
        print(f"[SG2 head] head_joint1 down limit {was} -> {SG2_HEAD_PITCH_LIMIT_DEG} deg")
        return


def _align_sg2_wheel_joint_limits(stage, prim_path: str) -> None:
    """Give the swerve joints the travel FFW_SH5.usd gives them.

    All six of FFW_SG2.usd's wheel joints -- drive AND steer alike -- carry the same +/-1080 deg
    limit, which is the URDF importer's placeholder for "no limit given", not a measurement.
    FFW_SH5.usd, the finished asset, says what the hardware actually does:

        *_wheel_drive_joint   no limit authored   -- a drive wheel spins forever
        *_wheel_steer_joint   +/-90.53 deg        -- a cabled swerve module cannot do more

    The drive limit is not cosmetic. At 5.78 rad/s (the wheel speed for 0.5 m/s) 1080 deg is
    reached after 3.3 seconds, and the robot stops dead with its wheels locked and nothing
    touching it. And +/-1080 deg of steering -- three full turns of a cabled module -- is not
    something anyone designs.

    Applied at spawn rather than by editing the shipped USD.
    """
    freed, clamped = [], []
    for child_prim in _iter_robot_prims(stage, prim_path):
        name = child_prim.GetName()
        if not child_prim.IsA(UsdPhysics.RevoluteJoint):
            continue
        joint = UsdPhysics.RevoluteJoint(child_prim)

        if name in SG2_SWERVE_WHEEL_JOINTS:
            # NOT RemoveProperty(): the +/-1080 opinion is authored in the referenced USD layer,
            # and removing a property only drops opinions in the current edit target, so the
            # reference's value survives untouched. Author the override instead -- -inf/+inf is
            # what UsdPhysics means by "unlimited", and it is exactly the state SH5 gets by
            # leaving the attribute unauthored.
            joint.CreateLowerLimitAttr().Set(float("-inf"))
            joint.CreateUpperLimitAttr().Set(float("inf"))
            freed.append(name)
        elif name in SG2_SWERVE_STEERING_JOINTS:
            joint.CreateLowerLimitAttr().Set(-SG2_SWERVE_STEER_LIMIT_DEG)
            joint.CreateUpperLimitAttr().Set(SG2_SWERVE_STEER_LIMIT_DEG)
            clamped.append(name)

    if freed:
        print(f"[SG2 wheel joints] lifted the +/-1080 deg limit on the drive joints {freed}")
    if clamped:
        print(f"[SG2 wheel joints] set the steer joints {clamped} to SH5's "
              f"+/-{SG2_SWERVE_STEER_LIMIT_DEG:.2f} deg")


@clone
def spawn_sg2_mobile(prim_path, cfg, translation=None, orientation=None, **kwargs):
    """Spawn FFW-SG2 as a mobile base: grippy jaws, wheels that touch the floor, free wheels."""
    prim = from_files.spawn_from_usd(prim_path, cfg, translation, orientation, **kwargs)

    material_path = f"{prim_path}/gripperPhysicsMaterial"
    _SG2_GRIPPER_MATERIAL.func(material_path, _SG2_GRIPPER_MATERIAL)

    stage = get_current_stage()
    make_uninstanceable(prim_path, stage)

    friction_prim_paths = set()
    for child_prim in _iter_robot_prims(stage, prim_path):
        child_path = str(child_prim.GetPath())
        if "/collisions/" in child_path and _is_sg2_gripper_jaw_prim(child_path):
            friction_prim_paths.add(child_path)

    for friction_prim_path in friction_prim_paths:
        bind_physics_material(friction_prim_path, material_path)

    _restore_missing_colliders(stage, prim_path)
    _filter_sg2_base_wheel_drive_collisions(stage, prim_path)
    _filter_sg2_hand_base_jaw_collisions(stage, prim_path)
    _filter_sg2_head_trunk_collisions(stage, prim_path)
    _align_sg2_wheel_joint_limits(stage, prim_path)
    _raise_sg2_head_pitch_limit(stage, prim_path)

    return prim


FFW_SG2_MOBILE_CFG = deepcopy(FFW_SG2_CFG)
FFW_SG2_MOBILE_CFG.spawn.func = spawn_sg2_mobile

# Free the root. The USD welds the robot to the world with a FixedJoint (inherited from the
# URDF's `world_fixed`); fix_root_link=False finds that joint and disables it.
FFW_SG2_MOBILE_CFG.spawn.articulation_props.fix_root_link = False

# Let it have weight. FFW_SH5_CFG keeps disable_gravity=True, but SH5 is never actually driven
# in any Isaac Lab task -- and a swerve base without weight has no contact load, so the wheels
# spin free and the robot goes nowhere.
FFW_SG2_MOBILE_CFG.spawn.rigid_props.disable_gravity = False

# Swerve actuators, with FFW_SH5_CFG's gains. The drive joints are VELOCITY-controlled
# (stiffness 0) -- that is what lets a swerve action command wheel speeds.
FFW_SG2_MOBILE_CFG.actuators["base_steer"] = ImplicitActuatorCfg(
    joint_names_expr=list(SG2_SWERVE_STEERING_JOINTS),
    velocity_limit_sim=10.0,
    effort_limit_sim=100000.0,
    stiffness=10000.0,
    damping=100.0,
)
FFW_SG2_MOBILE_CFG.actuators["base_drive"] = ImplicitActuatorCfg(
    joint_names_expr=list(SG2_SWERVE_WHEEL_JOINTS),
    velocity_limit_sim=50.0,
    effort_limit_sim=100000.0,
    stiffness=0.0,
    damping=100.0,
)

FFW_SG2_MOBILE_CFG.init_state = ArticulationCfg.InitialStateCfg(
    pos=(0.0, 0.0, 0.0),  # the wheels already sit on z=0 in the USD's rest pose
    joint_pos={
        **{j: 0.0 for j in SG2_SWERVE_STEERING_JOINTS},
        **{j: 0.0 for j in SG2_SWERVE_WHEEL_JOINTS},
        **{f"arm_l_joint{i + 1}": 0.0 for i in range(7)},
        **{f"arm_r_joint{i + 1}": 0.0 for i in range(7)},
        **{f"gripper_l_joint{i + 1}": 0.0 for i in range(4)},
        **{f"gripper_r_joint{i + 1}": 0.0 for i in range(4)},
        "head_joint1": 0.0,
        "head_joint2": 0.0,
        "lift_joint": 0.0,
    },
)
