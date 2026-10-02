"""L9 v2 bimanual (spec docs/superpowers/specs/2026-10-02-l9-bimanual.md; research
docs/research/bimanual_datagen_2026-10-02.md). Category A (handover) first, AI Worker first.

Design decision (see the spec note §1): do NOT write a second planner. `rt9.Runtime` is reused unmodified, one
instance per arm, against a dual `sim.scene.SimEnv` (dual=True, b2b8946). The handover zone is a robot-geometry
point (hypothesis, flagged), not a scene node, so it is NOT routed through task9's destination-spot sampler; task9 /
scene9 are only used (unmodified) to draw a valid scene and a start pose for the handed-over object.

Pure layer (this file's top half): no torch / curobo / isaaclab import, unit-tested on the laptop (tests/l9).
Impure layer (bottom half, `HandoverRuntime` / `run_smoke`): pod only, lazy imports."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

# ---------------------------------------------------------------------------------------------- pure: task defs
# category A (research doc table rows 1-12): 6 object groups x 2 directions. `cats` filters the AI Worker object
# catalog the same way task9v2's `T`/`hollow()` dicts do; `giver`/`receiver` are the arm roles.
BIM_A_OBJECTS = {
    "block": ("block",), "can": ("can",), "cup": ("cup", "mug"), "bottle": ("bottle",),
    "bowl": ("bowl",), "box": ("box",),
}
BIM_A_DEFS: dict = {}
for _name, _cats in BIM_A_OBJECTS.items():
    BIM_A_DEFS[f"handover_{_name}_lr"] = {"cats": _cats, "giver": "left", "receiver": "right", "family": "bim_a"}
    BIM_A_DEFS[f"handover_{_name}_rl"] = {"cats": _cats, "giver": "right", "receiver": "left", "family": "bim_a"}
assert len(BIM_A_DEFS) == 12, len(BIM_A_DEFS)

# category B (research doc table rows 13-18): two-hand lift/carry/place, symmetric, one object each (sync=True,
# role=lead for both -- no giver/receiver). G1 excluded (owner 10-02: payload; B is AI Worker + R1 Pro only).
# `cats` is a best-effort mapping onto the existing catalog (spec note: no two-handled-pot / long-bar assets
# confirmed in the catalog yet -- "no doors/drawers... existing assets only" per the owner's brief, so an item here
# with no matching pool row at draw time is simply never drawn, not a new asset).
BIM_B_DEFS = {
    "lift_tray": {"cats": ("tray",), "family": "bim_b"}, "lift_pot": {"cats": ("pot",), "family": "bim_b"},
    "lift_big_box": {"cats": ("box",), "family": "bim_b", "big": True},
    "lift_basket": {"cats": ("basket",), "family": "bim_b"}, "lift_crate": {"cats": ("crate", "bin"), "family": "bim_b"},
    "lift_bar": {"cats": ("bar", "rod"), "family": "bim_b"},
}
assert len(BIM_B_DEFS) == 6, len(BIM_B_DEFS)
# owner 10-03 00:xx: per-def train-catalog asset counts (exact category match, full 5356-item catalog, not one
# pool_for() window -- a pool draw returning 0 for a def with catalog_n>0 can still be a sampling miss on the
# RAW ASSET, separate from the bigger blocker below). lift_pot has NO matching catalog asset at all ("potted"/
# "pottery" entries are plants/decor, not a two-handled cooking pot).
#
# BIGGER FINDING (pod check, harvest/l9/rt9.has_candidates against /data/harvest/l9v2/grasps/ffw_sg2, 10-03 00:xx):
# raw asset existence is NOT the real blocker for most of these -- grasp-CANDIDATE cache coverage for ffw_sg2 is.
# tray/box/bin/rod have catalog assets but ZERO cached ffw_sg2 candidates (rt9.Runtime.choose() can never return
# anything for them no matter how many scenes are drawn); only basket has real coverage (15/39). This, not a pool
# sampling artifact, is why lift_tray and lift_big_box smoke draws both got "no scene / object draw" 3/3 (object9
# instantiate filters to targets with cached candidates, same filter bim_smoke_b.py applies explicitly). Generating
# the missing candidate caches is a production-pipeline prerequisite outside this review's scope -- flagged, not
# fixed here. lift_basket is the only B def currently smoke-testable for AI Worker until that coverage exists.
BIM_B_ASSET_COUNTS = {  # name -> (n_catalog_matches, n_with_ffw_sg2_candidates, note)
    "lift_tray": (10, 0, "자산은 있으나 ffw_sg2 잡기 후보 캐시 0 -- 생산 전처리 필요"),
    "lift_pot": (0, 0, "자산 없음(potted/pottery 류는 요리 냄비 아님)"),
    "lift_big_box": (58, 0, "자산은 있으나 ffw_sg2 잡기 후보 캐시 0 -- 생산 전처리 필요"),
    "lift_basket": (39, 15, "스모크 가능 (유일하게 후보 캐시 있음)"),
    "lift_crate": (41, 0, "자산은 있으나(bin 버킷) ffw_sg2 잡기 후보 캐시 0 -- 생산 전처리 필요"),
    "lift_bar": (5, 0, "자산 적음(rod 버킷)이고 ffw_sg2 잡기 후보 캐시도 0"),
}
assert set(BIM_B_ASSET_COUNTS) == set(BIM_B_DEFS)

# category C (research doc rows 19-24): one arm holds (role=support, gripper="hold", drift-bounded), the other
# manipulates (role=lead). All three robots (A/C/E/F per owner's brief).
BIM_C_DEFS = {
    "hold_bowl_fill": {"hold_cats": ("bowl",), "family": "bim_c"},
    "hold_basket_fill": {"hold_cats": ("basket",), "family": "bim_c"},
    "hold_openbox_fill": {"hold_cats": ("box",), "family": "bim_c"},  # open box (support kind "wide")
    "hold_tray_load": {"hold_cats": ("tray",), "family": "bim_c"},
    "hold_cup_pour": {"hold_cats": ("cup", "mug"), "pour_cats": ("bottle",), "family": "bim_c"},
    "hold_pot_lid": {"hold_cats": ("pot",), "lid_cats": ("lid",), "family": "bim_c"},
}
assert len(BIM_C_DEFS) == 6, len(BIM_C_DEFS)

# category D (research doc rows 25-30): two independent single-arm placements in the same scene, pre-filtered
# (design time, not labeling time: research doc §(d)) so the two targets' workspaces do not overlap.
BIM_D_DEFS = {
    "indep_cup_cup": {"cats_left": ("cup",), "cats_right": ("cup",), "family": "bim_d"},
    "indep_can_bottle": {"cats_left": ("can",), "cats_right": ("bottle",), "family": "bim_d"},
    "indep_block_block": {"cats_left": ("block",), "cats_right": ("block",), "family": "bim_d"},
    "indep_bottle_cup": {"cats_left": ("bottle",), "cats_right": ("cup", "mug"), "family": "bim_d"},
    "indep_box_box": {"cats_left": ("box",), "cats_right": ("box",), "family": "bim_d"},
    "indep_bowl_bowl": {"cats_left": ("bowl",), "cats_right": ("bowl",), "family": "bim_d"},
}
assert len(BIM_D_DEFS) == 6, len(BIM_D_DEFS)

# category E (research doc rows 31-34): handover + a regrasp/reorientation in the receiver's hand (quantised to the
# 15-deg wrist bin, same as the existing single-arm label resolution). A/C/E/F robots (no G1 payload concern: small
# objects only, matching the owner's "G1: A/C/E/F" brief).
BIM_E_DEFS = {
    "regrasp_box_face": {"cats": ("box",), "family": "bim_e"},
    "regrasp_cup_upright": {"cats": ("cup", "mug"), "family": "bim_e", "start": "lying"},
    "regrasp_bottle_cap": {"cats": ("bottle",), "family": "bim_e"},
    "regrasp_tray_level": {"cats": ("tray",), "family": "bim_e"},
}
assert len(BIM_E_DEFS) == 4, len(BIM_E_DEFS)

# category F (research doc rows 35-40): one arm aligns/holds a base, the other inserts/stacks into it.
BIM_F_DEFS = {
    "align_pot_lid": {"base_cats": ("pot",), "ins_cats": ("lid",), "family": "bim_f"},
    "align_bowl_nest": {"base_cats": ("bowl",), "ins_cats": ("bowl",), "family": "bim_f"},
    "align_cup_saucer": {"base_cats": ("tray",), "ins_cats": ("cup", "mug"), "family": "bim_f"},
    "align_bottle_rack": {"base_cats": ("holder",), "ins_cats": ("bottle",), "family": "bim_f"},
    "align_box_in_box": {"base_cats": ("box",), "ins_cats": ("box",), "family": "bim_f"},
    "align_crate_shelf": {"base_cats": ("crate", "bin"), "ins_cats": (), "family": "bim_f"},  # the shelf is a node
}
assert len(BIM_F_DEFS) == 6, len(BIM_F_DEFS)

ALL_BIM_DEFS = {**BIM_A_DEFS, **BIM_B_DEFS, **BIM_C_DEFS, **BIM_D_DEFS, **BIM_E_DEFS, **BIM_F_DEFS}
assert len(ALL_BIM_DEFS) == 40, len(ALL_BIM_DEFS)  # owner 10-02: 40 definitions total (research doc)
# robot x category eligibility (owner's brief, 2026-10-02): AI Worker / R1 Pro = all; G1 = A/C/E/F only (no B: payload)
ROBOT_CATEGORIES = {"ffw_sg2": "ABCDEF", "r1pro": "ABCDEF", "g1": "ACEF"}

# owner r3 (10-02 22:30): "한 팔로 될 일에 두 팔 금지" -- every B-F def reviewed for genuine two-arm necessity.
# Definitions are NOT deleted (kept/dropped marked here only); production/build must filter through kept_bim_defs().
# A (handover) is reviewed separately/restored by r3, not part of this B-F pass.
BIM_BF_REVIEW: dict = {
    # B: all 6 kept -- tray/pot/big_box/basket/crate/bar are literally the wide/large/long object class the
    # category is defined around; a long bar/rod carried one-handed is the textbook case FOR two-handed carry.
    "lift_tray": (True, "넓은 쟁반, 자연스러운 두 손 운반"),
    "lift_pot": (True, "양쪽 손잡이 냄비, 자연스러운 두 손"),
    "lift_big_box": (True, "큰 상자(big=True), 두 손 필요"),
    "lift_basket": (True, "넓은 바구니, 두 손 운반"),
    "lift_crate": (True, "양쪽 손잡이 crate/bin, 두 손 운반"),
    "lift_bar": (True, "길고 긴 막대, 양 끝을 두 손으로 드는 전형적 사례"),
    # C: all 6 kept -- canonical "hold steady with one hand, act with the other" real-world actions.
    "hold_bowl_fill": (True, "그릇을 손으로 받쳐 채우는 자연스러운 동작"),
    "hold_basket_fill": (True, "바구니를 받쳐 담는 자연스러운 동작"),
    "hold_openbox_fill": (True, "열린 상자를 받쳐 담는 자연스러운 동작(포장 작업과 동일)"),
    "hold_tray_load": (True, "쟁반을 받쳐 올리는 자연스러운 동작(서빙과 동일)"),
    "hold_cup_pour": (True, "컵을 쥐고 다른 손으로 따르는 전형적인 두 손 동작"),
    "hold_pot_lid": (True, "냄비를 받치고 뚜껑을 올리는 자연스러운 동작"),
    # D: all 6 dropped -- these are "two independent single-arm placements drawn into one scene", not a task
    # whose INSTRUCTION requires simultaneity. No such explicit-simultaneity instruction mechanism exists yet;
    # until one does, these are single-arm rows that happen to share a scene, not bimanual rows.
    "indep_cup_cup": (False, "지시가 동시 수행을 명시하지 않음 -- 단일팔 행 2개"),
    "indep_can_bottle": (False, "지시가 동시 수행을 명시하지 않음 -- 단일팔 행 2개"),
    "indep_block_block": (False, "지시가 동시 수행을 명시하지 않음 -- 단일팔 행 2개"),
    "indep_bottle_cup": (False, "지시가 동시 수행을 명시하지 않음 -- 단일팔 행 2개"),
    "indep_box_box": (False, "지시가 동시 수행을 명시하지 않음 -- 단일팔 행 2개"),
    "indep_bowl_bowl": (False, "지시가 동시 수행을 명시하지 않음 -- 단일팔 행 2개"),
    # E: 3 kept conditionally (runtime must gate on single-hand reachability -- only a TRUE regrasp-required case
    # should execute as bimanual; this is a per-episode check, not something this static mark alone settles).
    # tray_level dropped: leveling a tray is a small-angle correction well within a single wrist's range -- no
    # real regrasp/handoff is ever required for it.
    "regrasp_box_face": (True, "일부 목표 면은 한 손목 회전만으로 못 닿음(런타임 도달성 게이트 필요)"),
    "regrasp_cup_upright": (True, "누운 컵을 세우는 재정렬은 손목 범위를 넘을 수 있음(런타임 게이트 필요)"),
    "regrasp_bottle_cap": (True, "병 방향 전환이 손목 범위를 넘을 수 있음(런타임 게이트 필요)"),
    "regrasp_tray_level": (False, "수평 보정은 손목 회전 범위 내, 진짜 regrasp 불필요"),
    # F: pot_lid/bowl_nest/box_in_box kept -- the base is held steady during a precision insert (same structure
    # as C's container-holding tasks). cup_saucer/bottle_rack/crate_shelf dropped -- the base (tray/rack/shelf) is
    # a table-stable or fixed scene object; placing onto/into it needs no steadying hand, it's a single-arm task.
    "align_pot_lid": (True, "냄비를 받치고 뚜껑을 정렬하는 자연스러운 동작(C의 용기 받치기와 동일 구조)"),
    "align_bowl_nest": (True, "기준 그릇을 받치고 포개는 정밀 작업"),
    "align_cup_saucer": (False, "기준(tray)이 테이블에 안정적, 컵 놓기는 한 손으로 충분"),
    "align_bottle_rack": (False, "기준(holder/rack)이 고정 구조물, 한 손으로 충분"),
    "align_box_in_box": (True, "바깥 상자를 받치고 안쪽 상자를 끼우는 동작(열린 상자 받치기와 동일 구조)"),
    "align_crate_shelf": (False, "대상(shelf)이 장면 노드일 뿐 쥘 대상이 아님 -- 두 번째 역할이 없는 단일팔 행"),
}
assert set(BIM_BF_REVIEW) == set(BIM_B_DEFS) | set(BIM_C_DEFS) | set(BIM_D_DEFS) | set(BIM_E_DEFS) | set(BIM_F_DEFS)


def kept_bim_defs() -> dict:
    """-> {name: def_dict} for every B-F definition marked kept (True) in BIM_BF_REVIEW, plus all of BIM_A_DEFS
    (handover, reviewed/restored separately by owner r3 -- not part of the B-F two-arm-necessity pass)."""
    bf = {**BIM_B_DEFS, **BIM_C_DEFS, **BIM_D_DEFS, **BIM_E_DEFS, **BIM_F_DEFS}
    return {**BIM_A_DEFS, **{n: d for n, d in bf.items() if BIM_BF_REVIEW[n][0]}}

GRIPPERS = ("grasp", "release", "hold")  # research doc §(d): "hold" is new (role=support, contact maintained)
ROLES = ("lead", "support", "independent")

# ---------------------------------------------------------------------------------------------- pure: zone geometry
# R4 fix (2026-10-02, owner directive): a SINGLE fixed handover point was wrong twice over -- (a) two guessed points
# both turned out unreachable by one arm (pod smoke #2-5; ik_ok=0), and (b) the owner separately asked that the
# same definition draw a different robot-object geometry every episode, not one fixed spot. Both are fixed the same
# way: `assets9/bim_zone/<profile>.json` holds every (x, y, dz_table) cell where >= 1 cuRobo approach class is
# reachable by BOTH arms at once (computed offline, laptop, pure: `curobo9.reach_ok` on the existing per-arm
# `assets9/reach_v2/<profile>_<arm>.json` maps -- no torch/Isaac needed for this step -- converted into world frame
# by a per-arm shoulder offset: scene.py's measured AI Worker shoulder xyz, mirrored in y for the left arm, same
# convention as `arm.py`'s mirror_y/side). Finding: no cell in the probed box has "top" reachable by both arms at
# once (only front/oblique/side) -- a handover near the body midline is just not a top-down-friendly reach for
# either arm; this matches the owner's brief treating the zone as a hypothesis to validate, not assume.
ZONE_CACHE: dict = {}  # profile -> loaded json (lazy, process-local)


def _zone_cells(profile: str) -> dict:
    if profile not in ZONE_CACHE:
        import json
        import os
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets9", "bim_zone", f"{profile}.json")
        ZONE_CACHE[profile] = json.load(open(p))
    return ZONE_CACHE[profile]


def sample_zone_cell(profile: str, table_z: float, seed: int, episode_idx: int = 0) -> dict:
    """The cell drawn for an episode (see `sample_handover_zone`) + its xyz and reachable approach classes, so a
    caller can pick a release yaw the receiver can actually use at that point (owner 2026-10-02, R4 follow-up:
    the zone cell knows which approach direction works, but a candidate grasp only matches it if the object's
    yaw when released puts a graspable face that way)."""
    d = _zone_cells(profile)
    cells = d["cells"]
    rng = np.random.default_rng([int(seed), 2026_10_02, int(episode_idx)])
    c = cells[int(rng.integers(len(cells)))]
    step = 0.0125  # half of the 0.025 m grid step the cells were computed at
    jit = rng.uniform(-step, step, size=3)
    xyz = np.array([c["x"] + jit[0], c["y"] + jit[1], table_z + c["dz_table"] + jit[2]], float)
    return {"xyz": xyz, "classes": tuple(c["classes"]), "shoulder_right": tuple(d["shoulder_right"]),
            "shoulder_left": tuple(d["shoulder_left"])}


def sample_handover_zone(profile: str, table_z: float, seed: int, episode_idx: int = 0) -> np.ndarray:
    """A handover-zone point drawn uniformly from the precomputed common-reach cells (both arms, >= 1 approach
    class), jittered within its own cell (+/- half the grid step) so repeated draws are not snapped to the same few
    points -- seeded per (seed, episode_idx), so the SAME definition gives a different robot-object geometry every
    episode (owner 2026-10-02) while staying reproducible."""
    return sample_zone_cell(profile, table_z, seed, episode_idx)["xyz"]


def best_release_yaw(cand_a_local: np.ndarray, zone_classes, shoulder_receiver, zone_xy: tuple,
                     n_steps: int = 16) -> tuple:
    """Owner 2026-10-02 (R4 follow-up): the zone cell's `classes` say which approach direction the RECEIVER can
    reach there, but the receiver's actual grasp candidates are the object's cached candidate set carried over to
    wherever the giver releases it -- if the giver releases it at some arbitrary yaw, none of those candidates may
    point the right way even though the cell itself is reachable (pod smoke #6-9: ik_ok=0 despite free_ok > 0).
    Searches `n_steps` world yaw values (about world z, object otherwise kept upright) for the one under which the
    most of `cand_a_local` (the object's RAW, object-frame cached approach vectors, i.e. `grasp9` npz "a" before
    `to_world`) classify (`curobo9.approach_class`) into `zone_classes` as seen from the receiver's shoulder.
    -> (best_yaw_rad, n_matching, n_total)."""
    from . import curobo9 as C
    zxy_base = (zone_xy[0] - shoulder_receiver[0], zone_xy[1] - shoulder_receiver[1])
    best_yaw, best_n = 0.0, -1
    for k in range(n_steps):
        yaw = 2 * math.pi * k / n_steps
        cz, sz = math.cos(yaw), math.sin(yaw)
        Rz = np.array([[cz, -sz, 0.0], [sz, cz, 0.0], [0.0, 0.0, 1.0]])
        a_world = cand_a_local @ Rz.T
        n = sum(1 for a in a_world if C.approach_class(a, zxy_base) in zone_classes)
        if n > best_n:
            best_yaw, best_n = yaw, n
    return best_yaw, best_n, len(cand_a_local)


# R1 Pro / G1: no reach-map-verified zone yet (category A ships AI Worker first, owner's plan step 3); kept as the
# old single-point hypothesis until the same reach-sweep + cell file is built for them.
ZONE_X_V2 = {"r1pro": 0.45, "g1": 0.30}
ZONE_Z_ABOVE_TABLE_V2 = {"r1pro": 0.22, "g1": 0.18}


def handover_zone_xyz(profile: str, table_z: float, seed: int = 0, episode_idx: int = 0) -> np.ndarray:
    if profile == "ffw_sg2":
        return sample_handover_zone(profile, table_z, seed, episode_idx)
    return np.array([ZONE_X_V2[profile], 0.0, table_z + ZONE_Z_ABOVE_TABLE_V2[profile]], float)


def final_spot_xyz(zone: np.ndarray, receiver_arm: str, reach: float = 0.14) -> np.ndarray:
    """Where the receiver finally sets the object down: `reach` further into the receiver's own half of the table
    (right arm = -y, left arm = +y; harvest.l9.arm.side), same height band as the zone minus a few cm (object comes
    to rest, not held mid-air)."""
    from .arm import side
    y = zone[1] - side(receiver_arm) * reach  # side(+1)=right (y<0): final spot moves further -y = deeper right
    return np.array([zone[0], y, zone[2] - 0.08], float)


# ---------------------------------------------------------------------------------------------- pure: command schema
def bim_command(arm: str, role: str, position_m, gripper: str, quat_wxyz=None, sync: bool = False, point_px=None,
                 height=None, approach=None, wrist_bin=None) -> dict:
    """The research doc §(d) schema: the existing v2plan per-arm command (mode/position_m/gripper[/quat_wxyz]) plus
    `arm`, `role` (lead|support|independent) and `sync`; `gripper` additionally allows "hold" (role=support: keep the
    current contact, no new grasp attempt)."""
    if role not in ROLES:
        raise ValueError(f"role {role!r}: one of {ROLES}")
    if gripper not in GRIPPERS and gripper != "keep":
        raise ValueError(f"gripper {gripper!r}: one of {GRIPPERS + ('keep',)}")
    cmd = {"mode": "eef", "arm": arm, "role": role, "sync": bool(sync),
           "position_m": [round(float(v), 4) for v in position_m], "gripper": gripper}
    if quat_wxyz is not None:
        cmd["quat_wxyz"] = [round(float(v), 5) for v in quat_wxyz]
    if point_px is not None:
        cmd["point_px"] = list(point_px)
    if height is not None:
        cmd["height"] = height
    if approach is not None:
        cmd["approach"] = approach
    if wrist_bin is not None:
        cmd["wrist_bin"] = int(wrist_bin)
    return cmd


def pair_commands(a: dict, b: dict) -> dict:
    """One call's "commands" list (views9.ARM_NOTE format: one per arm)."""
    return {"commands": [a, b]}


DIRECTIONS = ("lr", "rl")


def handover_direction(giver_arm: str) -> str:
    return "lr" if giver_arm == "left" else "rl"


def handover_rows(direction: str, giver_point_px, giver_height, giver_approach, giver_rot_bin,
                  handover_point_px, handover_height,
                  receiver_point_px, receiver_approach, receiver_rot_bin, receiver_source: str = "graspgenx",
                  release_sync: bool = True) -> list:
    """The handover call sequence's label rows (owner 2026-10-02, L9_PRINCIPLES.md §2/new order: "핸드오버는 VLM에
    완전히 결합" -- every field below must be WRITTEN into the row as a command, not left live-only in code):
      - direction ("lr"|"rl": which arm gives) on every row;
      - the giver's own grasp point (point_px/height/approach/wrist_bin), giver_pick row;
      - the HANDOVER POINT as a commanded target (point_px + height) on the giver_carry / receiver_pick rows --
        `sample_handover_zone`/`sample_zone_cell` draw it, but the draw must be projected to a head pixel + height
        and placed here, not just used internally to steer cuRobo;
      - the receiver's grasp point/approach/rotation (receiver_pick row) -- `receiver_source` names which generator
        chose it ("graspgenx" or "rule", owner's A/B requirement) so the label says which, never silently;
      - release timing as a sync flag (giver_release row, `release_sync`: True = the receiver's contact was
        confirmed before the giver's gripper opened, the category-A gate itself).
    -> one dict per call: {"phase", "direction", "commands": [bim_command, ...]}."""
    if direction not in DIRECTIONS:
        raise ValueError(f"direction {direction!r}: one of {DIRECTIONS}")
    giver_arm, receiver_arm = ("left", "right") if direction == "lr" else ("right", "left")
    rows = [
        {"phase": "giver_pick", "direction": direction,
         "commands": [bim_command(giver_arm, "lead", [0.0, 0.0, 0.0], "grasp", point_px=giver_point_px,
                                  height=giver_height, approach=giver_approach, wrist_bin=giver_rot_bin)]},
        {"phase": "giver_carry", "direction": direction,
         "commands": [bim_command(giver_arm, "lead", [0.0, 0.0, 0.0], "hold", point_px=handover_point_px,
                                  height=handover_height)]},
        {"phase": "receiver_pick", "direction": direction,
         "commands": [bim_command(giver_arm, "support", [0.0, 0.0, 0.0], "hold", point_px=handover_point_px,
                                  height=handover_height, sync=True),
                      bim_command(receiver_arm, "lead", [0.0, 0.0, 0.0], "grasp", point_px=receiver_point_px,
                                  approach=receiver_approach, wrist_bin=receiver_rot_bin, sync=True)]},
        {"phase": "giver_release", "direction": direction,
         "commands": [bim_command(giver_arm, "support", [0.0, 0.0, 0.0], "release", sync=release_sync)]},
    ]
    rows[2]["commands"][1]["source"] = receiver_source  # which generator chose the receiver's grasp (owner's A/B)
    return rows


# ---------------------------------------------------------------------------------------------- pure: direction choice
# Owner 2026-10-02 (further refinement): the giver/receiver direction is NOT a coin flip or a hand rule -- cheap IK
# first, full cuRobo only for the direction(s) that clear it, then path cost, then joint margin, label the better
# direction; 50/50 must come from symmetric object placement (scene9 draw), not from forcing the label. This is the
# pure scoring half; the live IK/path-cost/margin numbers come from a HandoverRuntime method (impure, pod only,
# mirrors `_live_best_yaw`'s probe pattern) and get handed to `choose_direction` below.
def direction_score(giver_ik_ok: bool, receiver_ik_ok: bool, path_cost: float, joint_margin: float) -> float:
    """Higher is better; -inf if either arm cannot even reach (ik_ok gates before cost/margin matter)."""
    if not (giver_ik_ok and receiver_ik_ok):
        return float("-inf")
    return float(joint_margin) - float(path_cost)


def choose_direction(scores: dict) -> str:
    """scores: {"lr": {"giver_ik_ok", "receiver_ik_ok", "path_cost", "joint_margin"}, "rl": {...}} (both directions
    evaluated, or just one if the instruction names the giving arm -- the caller decides which directions to
    probe). -> the better direction; raises if neither direction reaches."""
    ranked = sorted(scores, key=lambda d: direction_score(**scores[d]), reverse=True)
    if direction_score(**scores[ranked[0]]) == float("-inf"):
        raise ValueError(f"no direction reaches: {scores}")
    return ranked[0]


# ---------------------------------------------------------------------------------------------- pure: phase FSM
PHASES = ("giver_pick", "giver_carry", "giver_hold", "receiver_pick", "giver_release", "receiver_carry", "done")


def handover_phase(phase: str, giver_holding: bool, giver_at_zone: bool, receiver_contacted: bool,
                    giver_opened: bool, receiver_at_final: bool) -> str:
    """Next phase (pure state machine, research doc §(c)/(d)): the giver carries to the zone and HOLDS (closed,
    stationary) until the receiver's grip reads CONTACT (both closed at once = the required overlap window); only
    then does the giver open, and only then does the receiver carry on. One phase advances per call; callers re-call
    with the same phase until a condition flips (no-op safe)."""
    if phase not in PHASES:
        raise ValueError(f"phase {phase!r}: one of {PHASES}")
    if phase == "giver_pick":
        return "giver_carry" if giver_holding else phase
    if phase == "giver_carry":
        return "giver_hold" if giver_at_zone else phase
    if phase == "giver_hold":
        return "receiver_pick"  # receiver starts approaching while the giver holds (doc §(d).3: two-stage choreo)
    if phase == "receiver_pick":
        return "giver_release" if receiver_contacted else phase
    if phase == "giver_release":
        return "receiver_carry" if giver_opened else phase
    if phase == "receiver_carry":
        return "done" if receiver_at_final else phase
    return "done"


# ---------------------------------------------------------------------------------------------- pure: success gate
def success_a(final_xy, target_xy, tol: float = 0.03, floor_touched: bool = False, overlap_ticks: int = 0) -> dict:
    """Research doc §(c) category-A gate (xy part only; pose-angle <= 15 deg is checked in sim, not here)."""
    err = float(math.hypot(final_xy[0] - target_xy[0], final_xy[1] - target_xy[1]))
    ok = (err <= tol) and (not floor_touched) and (overlap_ticks >= 1)
    return {"ok": bool(ok), "place_err_m": round(err, 4), "floor_touched": bool(floor_touched),
            "overlap_ticks": int(overlap_ticks)}


# ---------------------------------------------------------------------------------------------- pure: category B
# (two-hand lift) phase FSM. Mirror image of A's gate: here BOTH grippers must close before EITHER lifts (research
# doc §(c): "두 그리퍼 모두 닫힌 뒤에만 상승 시작"), then both carry together (common time axis, doc §(d).2 -- checked
# post hoc in sim, not solved for jointly), then both release only once the object rests on the target surface.
LIFT_PHASES = ("approach", "close_gate", "lift", "carry", "place_gate", "done")


def lift_phase(phase: str, left_closed: bool, right_closed: bool, lifted: bool, at_target: bool,
               left_rest: bool, right_rest: bool) -> str:
    if phase not in LIFT_PHASES:
        raise ValueError(f"phase {phase!r}: one of {LIFT_PHASES}")
    if phase == "approach":
        return "close_gate" if (left_closed or right_closed) else phase
    if phase == "close_gate":  # the sync gate: neither arm lifts until the OTHER has closed too
        return "lift" if (left_closed and right_closed) else phase
    if phase == "lift":
        return "carry" if lifted else phase
    if phase == "carry":
        return "place_gate" if at_target else phase
    if phase == "place_gate":
        return "done" if (left_rest and right_rest) else phase
    return "done"


def success_b(final_xy, target_xy, tol: float = 0.03, both_closed_before_lift: bool = False,
              min_table_gap_m: float = 0.0) -> dict:
    """Research doc §(c) category-B gate: the sync-close gate was honoured, the carried object kept clearance over
    the table (never dragged / dropped mid-carry), and the final drop point is within tolerance."""
    err = float(math.hypot(final_xy[0] - target_xy[0], final_xy[1] - target_xy[1]))
    ok = both_closed_before_lift and min_table_gap_m > 0.0 and err <= tol
    return {"ok": bool(ok), "place_err_m": round(err, 4), "both_closed_before_lift": bool(both_closed_before_lift),
            "min_table_gap_m": round(float(min_table_gap_m), 4)}


# ---------------------------------------------------------------------------------------------- pure: category D
# (simultaneous independent placement) success gate -- no new phase FSM needed: each arm runs its OWN ordinary
# single-arm pick-place (task9/rt9.Runtime, unmodified), concurrently, with `other_arm_boxes` (see the impure
# section) as the only cross-arm coupling. The only bimanual-specific check is here: both placed within tolerance,
# zero self-collision events logged (research doc §(c): "자가충돌 0회").
def success_d(final_xy_left, target_xy_left, final_xy_right, target_xy_right, tol: float = 0.03,
              self_collisions: int = 0) -> dict:
    el = float(math.hypot(final_xy_left[0] - target_xy_left[0], final_xy_left[1] - target_xy_left[1]))
    er = float(math.hypot(final_xy_right[0] - target_xy_right[0], final_xy_right[1] - target_xy_right[1]))
    ok = el <= tol and er <= tol and self_collisions == 0
    return {"ok": bool(ok), "place_err_left_m": round(el, 4), "place_err_right_m": round(er, 4),
            "self_collisions": int(self_collisions)}


# ---------------------------------------------------------------------------------------------- impure: runtime
# Deliberately NOT built on rt9.TrajExec / rt9.Runtime.motion_for: both are tightly coupled to the single-arm step
# name machinery (Runtime.plan / v2plan.plan), which needs a task9-style "place" object in the scene. The handover
# zone is not a scene object (spec note §1), so this orchestrator drives joint trajectories itself -- a self
# contained "trajectory player" per arm -- and reuses only the self-contained pieces of Runtime: `choose()` (grasp
# candidate selection), `_approach_plan()` (pre-grasp transit + straight approach + lift, already its own function),
# `planner.pose()/line()` + `_resample()` for the carry / zone / final moves, and `refresh_world()` for obstacles.
GRAVITY_BOX_HALF = (0.025, 0.025, 0.03)  # m, coarse stand-in for the other arm's gripper (spec note R1). First pod
# smoke (2026-10-02, seed 3950010): the original (0.07, 0.07, 0.09) box (18 cm tall) centred on the giver's TCP --
# itself placed at/above the held object's top (a "top" family grasp) -- extended far enough past the object that
# `choose()` found 0 reachable candidates for the receiver in EVERY approach family, not just the ones that would
# really collide. Shrunk once to (0.045, 0.045, 0.05) for that. Shrunk again 2026-10-03 (1hr checkpoint): category
# B's choose_b (arm B choosing while avoiding arm A's box on the SAME object, much smaller than a handover zone)
# was the #1 real B failure (6/7 executed-episode failures) -- same root cause, smaller object this time. Still a
# box, not the real links (R1 stands); if real collisions start showing up in frame review, grow this back up.
SETTLE_TICKS = 30  # ~0.6 s at 20 Hz / dt: gripper close/open settle wait


@dataclass
class _ArmSlot:
    arm: str
    rt: object  # rt9.Runtime
    traj: object = None  # np.ndarray (T, 7) or None (= hold the current q_target)
    traj_i: int = 0
    width: float = 0.0
    held_obj: str | None = None


# ---------------------------------------------------------------------------------------------- impure: direction probe
# Owner 2026-10-02 (further refinement): outcome-based direction choice, not a coin or a hand rule. Contributed by
# the arm-choice agent (ae975e701b01078f9), targeting `direction_score`/`choose_direction` above unchanged. Cheap
# stage 1 (rt.choose() for the giver side -- already what _grasp() would redo, so no extra cost; _batched_zone_ik
# for the receiver side, a generalisation of HandoverRuntime._live_best_yaw onto a bare Runtime before a giver/
# receiver role is fixed, since the object's yaw at the zone isn't decided yet) runs for BOTH directions; full
# cuRobo path cost / joint margin (stage 2) only for whichever direction(s) stage 1 says both arms reach.
def zone_point(profile: str, table_z: float, seed: int, episode_idx: int):
    """-> (xyz, cell_or_None). Single source of truth for the per-episode handover draw, shared by
    `HandoverRuntime._run_episode` and `probe_direction` callers (owner's outcome-based-direction order: probe
    and the real run MUST use the SAME zone point, never a per-direction redraw, so symmetry comes only from the
    scene draw as required)."""
    if profile == "ffw_sg2":
        cell = sample_zone_cell(profile, table_z, seed, episode_idx)
        return cell["xyz"], cell
    return handover_zone_xyz(profile, table_z, seed, episode_idx), None


def _batched_zone_ik(rt, obj_key: str, zone_xyz, n_yaw: int = 8, standoff: float = 0.11) -> tuple:
    """-> (n_ok, n_tested, best_yaw_rad, mean_margin_at_best_yaw); (0, 0, 0.0, 0.0) if no tested candidates."""
    C = rt._load(obj_key)
    if C is None or not len(C.get("w", ())):
        return 0, 0, 0.0, 0.0
    ok0 = np.asarray(C["test_ok"], bool) if "test_ok" in C else np.ones(len(C["w"]), bool)
    idx = np.flatnonzero(ok0)
    if not len(idx):
        return 0, 0, 0.0, 0.0
    rt.refresh_world()
    best = (0, 0.0, 0.0)
    for k in range(n_yaw):
        yaw = 2 * math.pi * k / n_yaw
        cz, sz = math.cos(yaw), math.sin(yaw)
        Robj = np.array([[cz, -sz, 0.0], [sz, cz, 0.0], [0.0, 0.0, 1.0]])
        T_obj = np.eye(4)
        T_obj[:3, :3], T_obj[:3, 3] = Robj, np.asarray(zone_xyz, float)
        Tg, Tp = [], []
        for i in idx:
            Tw = T_obj @ C["T"][i]
            a_world = Robj @ np.asarray(C["a"][i], float)
            Twp = Tw.copy()
            Twp[:3, 3] = Tw[:3, 3] - a_world * standoff
            Tg.append(rt.to_base(Tw))
            Tp.append(rt.to_base(Twp))
        ok_g, _, mg = rt.planner.ik(np.stack(Tg))
        ok_p, _, mp = rt.planner.ik(np.stack(Tp), contact_links_off=False)
        both = np.asarray(ok_g, bool) & np.asarray(ok_p, bool)
        n = int(np.sum(both))
        m = float(np.mean(np.minimum(mg, mp)[both])) if n else 0.0
        if n > best[0]:
            best = (n, yaw, m)
    n_ok, best_yaw, margin = best
    return n_ok, len(idx), best_yaw, margin


def probe_direction(world, profile: str, obj_key: str, zone_xyz, device: str = "cuda:0",
                    allow_untested: bool = False, n_yaw: int = 8) -> tuple:
    """Decide giver/receiver direction from measured reach/cost/margin -- call once per episode, before
    install_handover commits a direction. zone_xyz: the already-drawn handover point, the SAME for both
    directions (symmetry comes from the scene draw, never from branching this probe on direction).
    -> (scores, rts): scores is choose_direction's input shape; rts is {"left": Runtime, "right": Runtime}."""
    from . import rt9 as RT
    env = world.env
    rts = {}
    for arm in ("left", "right"):
        env.use_arm(arm)
        rts[arm] = RT.Runtime(world, profile, arm, device=device, allow_untested=allow_untested)
    gcs, pick_margin, zone_probe = {}, {}, {}
    for arm, rt in rts.items():
        env.use_arm(arm)
        gc = rt.choose(obj_key, {"tgt": obj_key})
        gcs[arm] = gc
        pick_margin[arm] = float(rt._margin[gc.idx]) if gc is not None else 0.0
        zone_probe[arm] = _batched_zone_ik(rt, obj_key, zone_xyz, n_yaw=n_yaw)

    def _cheap(giver_arm, receiver_arm):
        n_ok = zone_probe[receiver_arm][0]
        ok_both = n_ok > 0 and gcs[giver_arm] is not None
        return {"giver_ik_ok": gcs[giver_arm] is not None, "receiver_ik_ok": n_ok > 0, "path_cost": 0.0,
                "joint_margin": min(pick_margin[giver_arm], zone_probe[receiver_arm][3]) if ok_both else 0.0}

    scores = {"lr": _cheap("left", "right"), "rl": _cheap("right", "left")}
    for d in [x for x in DIRECTIONS if scores[x]["giver_ik_ok"] and scores[x]["receiver_ik_ok"]]:
        giver_arm = "left" if d == "lr" else "right"
        env.use_arm(giver_arm)
        rt, gc = rts[giver_arm], gcs[giver_arm]
        r = rt._approach_plan(rt.plan_start(), gc, obj_key)
        if not r["ok"]:
            scores[d]["giver_ik_ok"] = False
            continue
        parts = [q for q in (r.get("approach"), r.get("grasp"), r.get("lift")) if q is not None]  # lift can be
        Q = np.concatenate(parts)  # None after ok=True (bimanual9._grasp hit this once already) -- skip, not crash
        scores[d]["path_cost"] = float(np.sum(np.linalg.norm(np.diff(Q, axis=0), axis=1)))
        lo, hi = rt.planner._limits()
        m = np.minimum(Q - lo, hi - Q).min(1) / max(float((hi - lo).min()), 1e-6)
        scores[d]["joint_margin"] = float(m.min())
    return scores, rts


class HandoverRuntime:
    """Category-A orchestrator: two `rt9.Runtime` (one per arm) against one dual SimEnv, driven by `handover_phase`.
    Not wired into `collect9.run_episode` / `teach_l8d.collect.collect_episode` yet (spec note §3): `run_episode`
    below is a standalone loop for the pilot's smoke episodes, not the production label/build pipeline."""

    def __init__(self, world, profile: str, giver_arm: str, receiver_arm: str, device: str = "cuda:0",
                 allow_untested: bool = False, receiver_source: str = "rule"):
        from . import rt9 as RT
        env = world.env
        if not getattr(env, "dual", False):
            raise ValueError("HandoverRuntime needs world.env built with dual=True (world9.make_world9(dual=True))")
        if env.primary not in (giver_arm, receiver_arm):
            raise ValueError(f"env.primary={env.primary!r} must be the giver or the receiver arm")
        if receiver_source not in ("rule", "graspgenx"):
            raise ValueError(f"receiver_source={receiver_source!r}: must be 'rule' or 'graspgenx'")
        self.world, self.profile, self.receiver_source = world, profile, receiver_source
        env.use_arm(giver_arm)
        giver_rt = RT.Runtime(world, profile, giver_arm, device=device, allow_untested=allow_untested)
        env.use_arm(receiver_arm)
        receiver_rt = RT.Runtime(world, profile, receiver_arm, device=device, allow_untested=allow_untested)
        self.giver = _ArmSlot(giver_arm, giver_rt, width=float(giver_rt.w.w_open))
        self.receiver = _ArmSlot(receiver_arm, receiver_rt, width=float(receiver_rt.w.w_open))
        self.phase = "giver_pick"
        self.overlap_ticks = 0
        self.events = []
        env.use_arm(env.primary)
        self._freeze(self.giver)
        self._freeze(self.receiver)

    def slot_of(self, arm: str) -> "_ArmSlot":
        return self.giver if arm == self.giver.arm else self.receiver

    def other_of(self, slot: "_ArmSlot") -> "_ArmSlot":
        return self.receiver if slot is self.giver else self.giver

    # -------------------------------------------------------------- per-tick stepping
    def _freeze(self, slot: "_ArmSlot") -> None:
        """This arm's target becomes its current measured joints (held stationary)."""
        env = self.world.env
        env.use_arm(slot.arm)
        slot.rt.q_target = env.arm_q().astype(np.float32)
        slot.traj = None

    def _gravity_target(self, slot: "_ArmSlot") -> np.ndarray:
        env = self.world.env
        env.use_arm(slot.arm)  # context-dependent gravity query; the index arrays below are not (rt's own snapshot)
        g = self.world.pl._gravity_offset()[0].cpu().numpy()
        rt = slot.rt
        q = env.robot.data.joint_pos[0, rt.arm_ids].cpu().numpy().copy()
        if rt.q_target is not None:
            for j, sid in enumerate(rt.sim_ids):
                q[rt.arm_ids.index(sid)] = rt.q_target[j]
        return (q + g).astype(np.float32)

    def tick(self) -> None:
        """One physics step. Each slot with a live `traj` advances one waypoint into `rt.q_target` first; a slot
        with `traj=None` keeps stepping its last-frozen `q_target` (held)."""
        for slot in (self.giver, self.receiver):
            if slot.traj is not None:
                if slot.traj_i < len(slot.traj):
                    slot.rt.q_target = slot.traj[slot.traj_i]
                    slot.traj_i += 1
                if slot.traj_i >= len(slot.traj):
                    slot.traj = None  # arrived: hold this last waypoint from now on
        env = self.world.env
        primary = self.slot_of(env.primary)
        other = self.other_of(primary)
        q_other = self._gravity_target(other)
        env.use_arm(other.arm)
        env.set_arm2_target(q_other, other.width)
        q_prim = self._gravity_target(primary)
        env.use_arm(primary.arm)
        env.step(np.concatenate([q_prim, [primary.width]]).astype(np.float32))
        self._update_overlap()

    def run_ticks(self, n: int) -> None:
        for _ in range(n):
            self.tick()

    def _update_overlap(self) -> None:
        env = self.world.env
        env.use_arm(self.giver.arm)
        gw = env.gripper_width()
        env.use_arm(self.receiver.arm)
        rw = env.gripper_width()
        env.use_arm(env.primary)
        if self.phase == "receiver_pick" and gw < 0.01 and rw < 0.01:
            self.overlap_ticks += 1

    # -------------------------------------------------------------- motion primitives (self-contained Runtime bits)
    def other_arm_boxes(self, slot: "_ArmSlot") -> dict:
        """A coarse box around the OTHER arm's current TCP, to pass as `extra_boxes=` into `slot.rt.choose()` /
        `refresh_world()` (rt9.Runtime, extended for this: both now accept `extra_boxes` and merge it in after their
        own obstacle scan, so it survives their internal `refresh_world` calls instead of being overwritten by the
        next one -- spec note R1b). Spec note R1: a box, not the other arm's real links -- no true dual-arm
        self-collision check."""
        env = self.world.env
        other = self.other_of(slot)
        env.use_arm(other.arm)
        p_other, _ = self.world.pl.tcp_pose()
        env.use_arm(slot.arm)
        return {"other_arm": (np.asarray(p_other, float), [2 * h for h in GRAVITY_BOX_HALF],
                              np.array([1.0, 0.0, 0.0, 0.0]))}

    def _grasp(self, slot: "_ArmSlot", obj_key: str) -> dict:
        """Choose + transit + straight approach + lift (rt9.Runtime._approach_plan, self-contained), then close.
        -> {"ok", "status"}. The receiver, when `self.receiver_source == "graspgenx"`, tries
        `_receiver_grasp_graspgenx` first and falls back to the rule path (rt.choose()) if it returns None --
        never worse than the rule path, only possibly better."""
        env = self.world.env
        env.use_arm(slot.arm)
        rt = slot.rt
        gc = None
        if slot is self.receiver and self.receiver_source == "graspgenx":
            gc = self._receiver_grasp_graspgenx(obj_key)
        if gc is None:
            gc = rt.choose(obj_key, {"tgt": obj_key}, extra_boxes=self.other_arm_boxes(slot))
        if gc is None:
            diag = rt.picks[-1] if rt.picks else {}
            return {"ok": False, "status": "no valid grasp", "choice_fail": diag.get("choice_fail"),
                    "valid_stats": diag.get("valid_stats")}
        r = rt._approach_plan(rt.plan_start(), gc, obj_key, extra_boxes=self.other_arm_boxes(slot))
        if not r["ok"]:
            return {"ok": False, "status": r["status"]}
        slot.traj, slot.traj_i = rt._resample(r["approach"]), 0
        self.run_ticks(len(slot.traj) + 5)
        slot.traj, slot.traj_i = rt._resample(r["grasp"]), 0
        self.run_ticks(len(slot.traj) + 5)
        slot.width = 0.0  # close
        self.run_ticks(SETTLE_TICKS)
        env.use_arm(slot.arm)
        gap = float(env.gripper_width())
        from . import rt9 as RT
        if RT.classify_close(gap, gc.w) == "EMPTY":
            return {"ok": False, "status": f"EMPTY close (gap {gap * 100:.1f} cm)"}
        slot.held_obj = obj_key  # attached before the lift line so refresh_world/choose see it held if that line
        T_obj_pick = RT.T_of(*env.object_pose(obj_key))  # the rigid grip (object <-> gripper), while it holds, is
        if r.get("lift") is not None:  # needs replanning (rt9.Runtime._approach_plan can return ok=True with a
            slot.traj, slot.traj_i = rt._resample(r["lift"]), 0  # None lift -- pod smoke #6 crashed here, bare
            self.run_ticks(len(slot.traj) + 5)  # TypeError from P9.resample(None, ...); the straight-line micro-lift
        return {"ok": True, "status": "ok", "gc": gc, "T_obj_pick": T_obj_pick}  # an optimization, skip if None

    def _receiver_grasp_graspgenx(self, obj_key: str, n_surface: int = 2000):
        """Receiver grasp via the SAME pod-A/B-validated GraspGenX pipeline the live executor uses
        (harvest.l9.live9.choose_live + harvest.l9.ggx_refine, LIVE_REFINER=ggx won the 2026-10-02 A/B), fed a
        PRIVILEGED mesh-sampled point cloud instead of an observed depth cloud -- this is the offline label
        generator (L9_PRINCIPLES.md §2: the generator is privileged/offline, unlike the live executor it backs).
        Tries approach families in order (filter_candidates' family check is unconditional, so the family must be
        picked before calling, unlike cam=None which cleanly skips the rot_bin check -- see live9.sample_grasps_cloud's
        own docstring on this) and returns the FIRST one whose grasp pose solves cuRobo IK (owner 2026-10-03: not
        best-of-4 by score -- that made the pod A/B ~1.6x slower per episode than the rule path for no fairness
        benefit, since rule's rt.choose() itself is also a first-good-enough pick, not an exhaustive best-of search).
        Does NOT pass
        extra_obstacles (live9's own (C,H,R) cuboid convention, different from this file's extra_boxes dict) --
        the subsequent `_approach_plan(..., extra_boxes=...)` call in `_grasp` still re-checks the giver's gripper
        box, same as it always does, so a colliding pick is still rejected, just one step later than the rule
        path's rt.choose() would reject it. -> v2plan.GraspChoice | None."""
        import os as _os
        from . import grasp9 as G
        from . import live9 as L
        from . import rt9 as RT
        from ..sim.scene import OBJ_GEOM
        env = self.world.env
        env.use_arm(self.receiver.arm)
        rt = self.receiver.rt
        oid = OBJ_GEOM.get(obj_key, {}).get("catalog_id") or obj_key
        mesh_path = _os.path.join("/data/harvest/l9v2/meshes", oid + ".npz")
        if not _os.path.exists(mesh_path):
            return None
        m = np.load(mesh_path)
        V, F = m["v"], m["f"]
        rng = np.random.default_rng(0)
        P_local, N_local, _ = G.sample_surface(V, F, n_surface, rng)
        c, q = env.object_pose(obj_key)
        Robj = RT.G.qmat(np.asarray(q, float))
        P = (P_local @ Robj.T) + np.asarray(c, float)
        N = N_local @ Robj.T
        point3d = np.asarray(c, float)
        base_xy = rt.T_world_base()[:2, 3]
        f_dir = point3d[:2] - base_xy
        for fam in ("front", "oblique", "side", "top"):
            gc = L.choose_live(P, N, self.profile, fam, rot_bin=0, point3d=point3d,
                               support_z=self.world.table_z, f_dir=f_dir, cam=None, category="", obj_h=0.0,
                               extra_obstacles=None, seed=0, k=0, use_refiner=True)
            if gc is None:
                continue
            ok, _, _ = rt.planner.ik(rt.to_base(gc.T)[None])
            if bool(ok[0]):
                return gc
        return None

    def _live_best_yaw(self, obj_key: str, zone_xyz, n_yaw: int = 8) -> tuple:
        """Owner 2026-10-02 (R4 follow-up to `best_release_yaw`'s static approach-class proxy, which matched the
        broad direction but still left the receiver at ik_ok=0 in every pod attempt that reached it -- pod smoke
        #10): the SAME two-stage batched cuRobo IK check `rt9.Runtime._valid` makes (the grasp pose itself, then
        the retracted pre-grasp standoff pose, both with self-collision on and the giver's TCP box as an obstacle)
        run directly against the receiver's own test-passing candidates, for `n_yaw` candidate world yaws of the
        object placed at `zone_xyz` -- picks the yaw with the most candidates where BOTH poses solve. A real IK
        probe, not a proxy, at a real (if slightly cheaper -- a single fixed standoff, not the per-pick random
        draw) version of what `choose()` will check for real right after. -> (best_yaw_rad, n_ok, n_tested)."""
        env = self.world.env
        env.use_arm(self.receiver.arm)
        rt = self.receiver.rt
        C = rt._load(obj_key)
        if C is None or not len(C.get("w", ())):
            return 0.0, 0, 0
        ok0 = np.asarray(C["test_ok"], bool) if "test_ok" in C else np.ones(len(C["w"]), bool)
        idx = np.flatnonzero(ok0)
        if not len(idx):
            return 0.0, 0, 0
        STANDOFF_PROBE = 0.11  # m, the midpoint of v2plan.STANDOFF (0.08, 0.14) -- a fixed probe value; the real
        rt.refresh_world(extra_boxes=self.other_arm_boxes(self.receiver))  # per-pick draw happens in choose() itself
        best_yaw, best_n = 0.0, -1
        for k in range(n_yaw):
            yaw = 2 * math.pi * k / n_yaw
            cz, sz = math.cos(yaw), math.sin(yaw)
            Robj = np.array([[cz, -sz, 0.0], [sz, cz, 0.0], [0.0, 0.0, 1.0]])
            T_obj = np.eye(4)
            T_obj[:3, :3] = Robj
            T_obj[:3, 3] = zone_xyz
            Tg, Tp = [], []
            for i in idx:
                Tw = T_obj @ C["T"][i]
                a_world = Robj @ np.asarray(C["a"][i], float)
                Twp = Tw.copy()
                Twp[:3, 3] = Tw[:3, 3] - a_world * STANDOFF_PROBE
                Tg.append(rt.to_base(Tw))
                Tp.append(rt.to_base(Twp))
            ok_g, _, _ = rt.planner.ik(np.stack(Tg))
            ok_p, _, _ = rt.planner.ik(np.stack(Tp))
            n = int(np.sum(np.asarray(ok_g, bool) & np.asarray(ok_p, bool)))
            if n > best_n:
                best_yaw, best_n = yaw, n
        return best_yaw, best_n, len(idx)

    def _move_to(self, slot: "_ArmSlot", target_xyz, quat_wxyz=None) -> dict:
        """A straight / planned cuRobo move to a world TCP pose, holding `slot.held_obj` attached if set."""
        from . import rt9 as RT
        env = self.world.env
        env.use_arm(slot.arm)
        rt = slot.rt
        rt.refresh_world(holding=slot.held_obj or None, extra_boxes=self.other_arm_boxes(slot))
        q = env.arm_q() if rt.q_target is None else np.asarray(rt.q_target, float)
        quat = np.asarray(quat_wxyz, float) if quat_wxyz is not None else np.asarray(rt.tcp_T()[:3, :3], float)
        T = RT.T_of(target_xyz, RT.G.mat_quat(quat) if quat.shape == (3, 3) else quat)
        Tb = rt.to_base(T)
        Q = rt.planner.line(q, rt.to_base(rt.tcp_T()), Tb) or rt.planner.pose(q, Tb)
        if Q is None:
            return {"ok": False, "status": "no collision-free path"}
        slot.traj, slot.traj_i = rt._resample(np.asarray(Q, float)), 0
        self.run_ticks(len(slot.traj) + 5)
        return {"ok": True, "status": "ok"}

    def _gripper(self, slot: "_ArmSlot", action: str) -> None:
        slot.width = 0.0 if action == "close" else float(slot.rt.w.w_open)
        self.run_ticks(SETTLE_TICKS)
        if action == "open":
            slot.held_obj = None

    # -------------------------------------------------------------- episode
    def run_episode(self, obj_key: str, table_z: float, seed: int = 0, episode_idx: int = 0, final_xy=None,
                    max_phase_ticks: int = 400) -> dict:
        """Category-A smoke episode: giver picks `obj_key`, carries to the handover zone and holds; the receiver
        approaches and closes on it (while the giver holds), the giver opens once the receiver has it, the receiver
        carries to `final_xy` (default: `final_spot_xyz`). Not the production collection loop (spec note §3): no
        labels.jsonl / build9 row here, see tools/l9/bim_smoke.py for that wiring. `seed`/`episode_idx` draw the
        zone from the reach-verified common cells (owner 2026-10-02: a different robot-object geometry every
        episode, not one fixed point -- see `sample_handover_zone`). Every return path goes through `finally`:
        env.use_arm(env.primary) (bug found in the first pod smoke run -- an early return left the dual env's
        "current arm" context on the receiver, and the NEXT episode's world.reset() -> env.reset() -> its own
        settle-step env.step() call raised "step() takes the primary arm's targets" because of it)."""
        env = self.world.env
        try:
            return self._run_episode(obj_key, table_z, seed, episode_idx, final_xy)
        finally:
            env.use_arm(env.primary)

    def _run_episode(self, obj_key: str, table_z: float, seed: int, episode_idx: int, final_xy=None) -> dict:
        zone, cell = zone_point(self.profile, table_z, seed, episode_idx)
        if final_xy is None:
            final_xy = final_spot_xyz(zone, self.receiver.arm)[:2]
        log = []
        r = self._grasp(self.giver, obj_key)
        log.append({"phase": "giver_pick", **r})
        if not r["ok"]:
            return {"ok": False, "log": log}
        carry_pos, carry_quat = zone, None
        if cell is not None:  # owner 2026-10-02 (R4 follow-up): release at a yaw whose candidates actually point
            yaw, n_ok, n_tot = self._live_best_yaw(obj_key, zone)  # the direction the zone is reachable from
            log[-1]["release_yaw_ik"] = f"{n_ok}/{n_tot}"
            T_obj_pick = r.get("T_obj_pick")
            if T_obj_pick is not None:
                from . import plan9 as P9
                from . import rt9 as RT
                T_obj_G = P9.inv_T(T_obj_pick) @ r["gc"].T  # the rigid grip, constant while held
                cz, sz = math.cos(yaw), math.sin(yaw)
                T_obj_desired = np.eye(4)
                T_obj_desired[:3, :3] = np.array([[cz, -sz, 0.0], [sz, cz, 0.0], [0.0, 0.0, 1.0]])
                T_obj_desired[:3, 3] = zone
                T_grip_desired = T_obj_desired @ T_obj_G
                carry_pos = T_grip_desired[:3, 3]
                carry_quat = RT.G.mat_quat(T_grip_desired[:3, :3])
        # owner 2026-10-03 (1hr checkpoint, "no collision-free path" was the #1 real giver_carry failure, 7/9
        # executed-episode failures across every smoke run so far): the direct, single _move_to from the
        # just-picked pose straight to carry_pos/carry_quat often combines a large translation AND rotation
        # through cluttered table-level space in one cuRobo call. Same fix as category B's LiftRuntime already
        # uses successfully (a plain straight-up waypoint before the real move): lift to a clear height, SAME
        # orientation as just-picked (quat_wxyz=None keeps current), THEN do the full carry move from up there.
        env2b = self.world.env
        env2b.use_arm(self.giver.arm)
        lift_xyz = np.asarray(self.giver.rt.tcp_T()[:3, 3], float).copy()
        lift_xyz[2] = max(lift_xyz[2], float(carry_pos[2])) + 0.08
        r = self._move_to(self.giver, lift_xyz)
        log.append({"phase": "giver_lift_waypoint", **r})
        if not r["ok"]:
            return {"ok": False, "log": log}
        r = self._move_to(self.giver, carry_pos, quat_wxyz=carry_quat)
        log.append({"phase": "giver_carry", **r})
        if not r["ok"]:
            return {"ok": False, "log": log}
        if cell is not None and carry_quat is not None:
            # smoke12 confirmed it (2.8cm/4.9deg, seed 3950165): the open-loop carry (_move_to plans once, no
            # closed-loop re-measurement the way rt9.Runtime.plan()'s single-arm loop does every call) lands off
            # the yaw-chosen T_obj_desired by enough to flip the live-IK probe's passing candidates back to failing.
            # One corrective move, targeting T_obj_desired again from the FRESHLY measured grip (a small motion
            # should track much more accurately than the long initial carry).
            env2 = self.world.env
            env2.use_arm(self.giver.arm)
            p_act, q_act = env2.object_pose(obj_key)
            from . import grasp9 as G
            p_des = T_obj_desired[:3, 3]
            err_m = float(np.linalg.norm(np.asarray(p_act, float) - p_des))
            R_act, R_des = G.qmat(np.asarray(q_act, float)), T_obj_desired[:3, :3]
            err_deg = math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(R_act.T @ R_des) - 1) / 2))))
            log[-1]["carry_pose_err"] = f"{err_m * 100:.1f}cm/{err_deg:.1f}deg"
            if err_m > 0.01 or err_deg > 2.0:
                T_obj_actual = RT.T_of(p_act, q_act)
                T_obj_G2 = P9.inv_T(T_obj_actual) @ self.giver.rt.tcp_T()
                T_grip_corr = T_obj_desired @ T_obj_G2
                r2 = self._move_to(self.giver, T_grip_corr[:3, 3], quat_wxyz=RT.G.mat_quat(T_grip_corr[:3, :3]))
                log.append({"phase": "giver_carry_correct", **r2})
                if r2["ok"]:
                    p_act2, q_act2 = env2.object_pose(obj_key)
                    err_m2 = float(np.linalg.norm(np.asarray(p_act2, float) - p_des))
                    R_act2 = G.qmat(np.asarray(q_act2, float))
                    err_deg2 = math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(R_act2.T @ R_des) - 1) / 2))))
                    log[-1]["carry_pose_err"] = f"{err_m2 * 100:.1f}cm/{err_deg2:.1f}deg"
        self.phase = "receiver_pick"
        self.overlap_ticks = 0
        r = self._grasp(self.receiver, obj_key)
        log.append({"phase": "receiver_pick", **r})
        if not r["ok"]:
            return {"ok": False, "log": log}
        self._gripper(self.giver, "open")
        log.append({"phase": "giver_release", "ok": True})
        r = self._move_to(self.giver, np.asarray(zone, float) + np.array([-0.08, 0.0, 0.05]))  # retreat, clear of
        log.append({"phase": "giver_retreat", **r})  # the receiver's incoming carry path
        r = self._move_to(self.receiver, np.array([final_xy[0], final_xy[1], zone[2]]))
        log.append({"phase": "receiver_carry", **r})
        if not r["ok"]:
            return {"ok": False, "log": log}
        self._gripper(self.receiver, "open")
        env = self.world.env
        env.use_arm(self.receiver.arm)
        final_obj_xy = np.asarray(env.object_pose(obj_key)[0], float)[:2]
        gate = success_a(final_obj_xy, final_xy, overlap_ticks=self.overlap_ticks)
        return {"ok": gate["ok"], "gate": gate, "log": log}


def install_handover(world, profile: str, giver_arm: str, receiver_arm: str, device: str = "cuda:0",
                      allow_untested: bool = False, receiver_source: str = "rule") -> HandoverRuntime:
    return HandoverRuntime(world, profile, giver_arm, receiver_arm, device=device, allow_untested=allow_untested,
                           receiver_source=receiver_source)


# ================================================================================================= category B: lift
LIFT_HEIGHT_M = 0.08  # m, clearance lift before carrying -- a first guess (no tuned value exists yet for a dual
# rigid carry; single-arm micro-lifts elsewhere in rt9 are much smaller, that's a grasp-settle lift, not a carry).


class LiftRuntime:
    """Category-B orchestrator: two `rt9.Runtime` (one per arm) gripping the SAME object simultaneously, against
    one dual SimEnv -- choose split grasps (arm B's choose() sees arm A's gripper as an obstacle, same
    `extra_boxes` mechanism as HandoverRuntime, which naturally pushes the two picks to opposite sides of the
    object instead of needing an explicit left/right split heuristic), approach + close both (the sync-close gate
    in `lift_phase` is about CLOSE timing, not approach timing -- both arms simply reach `held` before `_move_both`
    is ever called), then lift/carry/place by moving BOTH arms to the TCP pose implied by one shared rigid object
    target pose (`_move_both`), using each arm's own grip transform captured at grasp time (same `T_obj_G` trick as
    HandoverRuntime's carry-correction step). KNOWN APPROXIMATION (flag, like HandoverRuntime's R1 other-arm-box):
    each arm's Cartesian path to its own endpoint is planned independently (`rt.planner.line`/`pose`), so the two
    grippers are only guaranteed object-consistent AT the keypoints this class calls `_move_both` for (lift /
    carry / place), not necessarily at every intermediate tick between them -- real contact friction + the dual
    SimEnv's physics resolve the rest, same as any real-world grasp compliance. If pod smoke shows this is too
    loose (object slips / arms fight each other), the fix is more keypoints (finer-grained `_move_both` calls), not
    a different architecture. Not wired into collect9/build9 yet, see tools/l9/bim_smoke_b.py for the smoke
    harness (spec note §3, same caveat as HandoverRuntime)."""

    def __init__(self, world, profile: str, arm_a: str, arm_b: str, device: str = "cuda:0",
                 allow_untested: bool = False):
        from . import rt9 as RT
        env = world.env
        if not getattr(env, "dual", False):
            raise ValueError("LiftRuntime needs world.env built with dual=True (world9.make_world9(dual=True))")
        if env.primary not in (arm_a, arm_b):
            raise ValueError(f"env.primary={env.primary!r} must be arm_a or arm_b")
        self.world, self.profile = world, profile
        env.use_arm(arm_a)
        rt_a = RT.Runtime(world, profile, arm_a, device=device, allow_untested=allow_untested)
        env.use_arm(arm_b)
        rt_b = RT.Runtime(world, profile, arm_b, device=device, allow_untested=allow_untested)
        self.a = _ArmSlot(arm_a, rt_a, width=float(rt_a.w.w_open))
        self.b = _ArmSlot(arm_b, rt_b, width=float(rt_b.w.w_open))
        self.slots = (self.a, self.b)
        self.phase = "approach"
        self.events = []
        env.use_arm(env.primary)
        self._freeze(self.a)
        self._freeze(self.b)

    def slot_of(self, arm: str) -> "_ArmSlot":
        return self.a if arm == self.a.arm else self.b

    def other_of(self, slot: "_ArmSlot") -> "_ArmSlot":
        return self.b if slot is self.a else self.a

    # -------------------------------------------------------------- per-tick stepping (identical pattern to
    # HandoverRuntime, generalized over self.slots instead of two named attributes)
    def _freeze(self, slot: "_ArmSlot") -> None:
        env = self.world.env
        env.use_arm(slot.arm)
        slot.rt.q_target = env.arm_q().astype(np.float32)
        slot.traj = None

    def _gravity_target(self, slot: "_ArmSlot") -> np.ndarray:
        env = self.world.env
        env.use_arm(slot.arm)
        g = self.world.pl._gravity_offset()[0].cpu().numpy()
        rt = slot.rt
        q = env.robot.data.joint_pos[0, rt.arm_ids].cpu().numpy().copy()
        if rt.q_target is not None:
            for j, sid in enumerate(rt.sim_ids):
                q[rt.arm_ids.index(sid)] = rt.q_target[j]
        return (q + g).astype(np.float32)

    def tick(self) -> None:
        for slot in self.slots:
            if slot.traj is not None:
                if slot.traj_i < len(slot.traj):
                    slot.rt.q_target = slot.traj[slot.traj_i]
                    slot.traj_i += 1
                if slot.traj_i >= len(slot.traj):
                    slot.traj = None
        env = self.world.env
        primary = self.slot_of(env.primary)
        other = self.other_of(primary)
        q_other = self._gravity_target(other)
        env.use_arm(other.arm)
        env.set_arm2_target(q_other, other.width)
        q_prim = self._gravity_target(primary)
        env.use_arm(primary.arm)
        env.step(np.concatenate([q_prim, [primary.width]]).astype(np.float32))

    def run_ticks(self, n: int) -> None:
        for _ in range(n):
            self.tick()

    def other_arm_boxes(self, slot: "_ArmSlot") -> dict:
        env = self.world.env
        other = self.other_of(slot)
        env.use_arm(other.arm)
        p_other, _ = self.world.pl.tcp_pose()
        env.use_arm(slot.arm)
        return {"other_arm": (np.asarray(p_other, float), [2 * h for h in GRAVITY_BOX_HALF],
                              np.array([1.0, 0.0, 0.0, 0.0]))}

    def _approach_and_close(self, slot: "_ArmSlot", obj_key: str, gc) -> dict:
        """Same body as HandoverRuntime._grasp, minus the choose() call (B picks both arms' candidates together,
        before either approaches, so arm B's choose() sees arm A's FINAL gripper box, not a mid-approach one)."""
        env = self.world.env
        env.use_arm(slot.arm)
        rt = slot.rt
        r = rt._approach_plan(rt.plan_start(), gc, obj_key, extra_boxes=self.other_arm_boxes(slot))
        if not r["ok"]:
            return {"ok": False, "status": r["status"]}
        slot.traj, slot.traj_i = rt._resample(r["approach"]), 0
        self.run_ticks(len(slot.traj) + 5)
        slot.traj, slot.traj_i = rt._resample(r["grasp"]), 0
        self.run_ticks(len(slot.traj) + 5)
        slot.width = 0.0
        self.run_ticks(SETTLE_TICKS)
        env.use_arm(slot.arm)
        gap = float(env.gripper_width())
        from . import rt9 as RT
        if RT.classify_close(gap, gc.w) == "EMPTY":
            return {"ok": False, "status": f"EMPTY close (gap {gap * 100:.1f} cm)"}
        slot.held_obj = obj_key
        if r.get("lift") is not None:
            slot.traj, slot.traj_i = rt._resample(r["lift"]), 0
            self.run_ticks(len(slot.traj) + 5)
        return {"ok": True, "status": "ok"}

    def _move_both(self, T_obj_target: np.ndarray, T_obj_G_a: np.ndarray, T_obj_G_b: np.ndarray) -> dict:
        """Plan each arm's own Cartesian path to the TCP pose implied by the SAME object target pose (via its own
        captured grip transform), then execute both simultaneously (shared tick loop, generic over self.slots --
        tick() already holds a slot at its last waypoint once its own traj is exhausted, so differing path
        lengths are handled for free)."""
        env = self.world.env
        plans = {}
        for slot, T_obj_G in ((self.a, T_obj_G_a), (self.b, T_obj_G_b)):
            env.use_arm(slot.arm)
            rt = slot.rt
            rt.refresh_world(holding=slot.held_obj or None, extra_boxes=self.other_arm_boxes(slot))
            T_tcp = T_obj_target @ T_obj_G
            q = env.arm_q() if rt.q_target is None else np.asarray(rt.q_target, float)
            Tb = rt.to_base(T_tcp)
            Q = rt.planner.line(q, rt.to_base(rt.tcp_T()), Tb) or rt.planner.pose(q, Tb)
            if Q is None:
                return {"ok": False, "status": f"no collision-free path for {slot.arm}"}
            plans[slot.arm] = rt._resample(np.asarray(Q, float))
        n = 0
        for slot in self.slots:
            slot.traj, slot.traj_i = plans[slot.arm], 0
            n = max(n, len(slot.traj))
        self.run_ticks(n + 5)
        return {"ok": True, "status": "ok"}

    def _gripper(self, slot: "_ArmSlot", action: str) -> None:
        slot.width = 0.0 if action == "close" else float(slot.rt.w.w_open)
        self.run_ticks(SETTLE_TICKS)
        if action == "open":
            slot.held_obj = None

    # -------------------------------------------------------------- episode
    def run_episode(self, obj_key: str, table_z: float, target_xy, seed: int = 0, episode_idx: int = 0) -> dict:
        """Category-B smoke episode: both arms choose a (mutually obstacle-aware) grasp on `obj_key`, approach and
        close together, lift `LIFT_HEIGHT_M`, carry to `target_xy`, place back at the pick height, open together.
        Not the production collection loop (spec note §3). Every return path restores env.primary (same bug class
        HandoverRuntime.run_episode fixed first)."""
        env = self.world.env
        try:
            return self._run_episode(obj_key, table_z, target_xy, seed, episode_idx)
        finally:
            env.use_arm(env.primary)

    def _run_episode(self, obj_key: str, table_z: float, target_xy, seed: int, episode_idx: int) -> dict:
        from . import plan9 as P9
        from . import rt9 as RT
        env = self.world.env
        log = []

        env.use_arm(self.a.arm)
        gc_a = self.a.rt.choose(obj_key, {"tgt": obj_key}, extra_boxes=self.other_arm_boxes(self.a))
        if gc_a is None:
            return {"ok": False, "log": [{"phase": "choose_a", "ok": False}]}
        env.use_arm(self.b.arm)
        gc_b = self.b.rt.choose(obj_key, {"tgt": obj_key}, extra_boxes=self.other_arm_boxes(self.b))
        if gc_b is None:
            return {"ok": False, "log": [{"phase": "choose_b", "ok": False}]}
        log.append({"phase": "choose", "ok": True})

        ra = self._approach_and_close(self.a, obj_key, gc_a)
        log.append({"phase": "grasp_a", **ra})
        if not ra["ok"]:
            return {"ok": False, "log": log}
        rb = self._approach_and_close(self.b, obj_key, gc_b)
        log.append({"phase": "grasp_b", **rb})
        if not rb["ok"]:
            return {"ok": False, "log": log}
        self.phase = "lift"

        T_obj_pick = RT.T_of(*env.object_pose(obj_key))
        T_obj_Ga = P9.inv_T(T_obj_pick) @ gc_a.T
        T_obj_Gb = P9.inv_T(T_obj_pick) @ gc_b.T

        T_obj_lift = T_obj_pick.copy()
        T_obj_lift[2, 3] += LIFT_HEIGHT_M
        r = self._move_both(T_obj_lift, T_obj_Ga, T_obj_Gb)
        log.append({"phase": "lift", **r})
        if not r["ok"]:
            return {"ok": False, "log": log}
        self.phase = "carry"

        T_obj_carry = T_obj_lift.copy()
        T_obj_carry[:2, 3] = np.asarray(target_xy, float)
        r = self._move_both(T_obj_carry, T_obj_Ga, T_obj_Gb)
        log.append({"phase": "carry", **r})
        if not r["ok"]:
            return {"ok": False, "log": log}
        self.phase = "place_gate"

        T_obj_place = T_obj_carry.copy()
        T_obj_place[2, 3] = T_obj_pick[2, 3]  # same table height assumed for pick and place spots
        r = self._move_both(T_obj_place, T_obj_Ga, T_obj_Gb)
        log.append({"phase": "place", **r})
        if not r["ok"]:
            return {"ok": False, "log": log}

        self._gripper(self.a, "open")
        self._gripper(self.b, "open")
        log.append({"phase": "release", "ok": True})
        self.phase = "done"

        env.use_arm(self.a.arm)
        final_xy = np.asarray(env.object_pose(obj_key)[0], float)[:2]
        gate = success_b(final_xy, target_xy, both_closed_before_lift=True, min_table_gap_m=LIFT_HEIGHT_M)
        return {"ok": gate["ok"], "gate": gate, "log": log}


def install_lift(world, profile: str, arm_a: str, arm_b: str, device: str = "cuda:0",
                  allow_untested: bool = False) -> LiftRuntime:
    return LiftRuntime(world, profile, arm_a, arm_b, device=device, allow_untested=allow_untested)
