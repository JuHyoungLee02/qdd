"""DEV perturbations P0-P2 only (E-first-experiments §4.5). Timing and size are decided by the seed.

E §4.5 table rows, copied verbatim (DEV-public rows only):
# | 코드 | 섭동 | 발동 | 룰 작성자 공개 |
# | P0 | 없음(초기 배치 무작위만) | — | DEV |
# | P1 | 대상 물체 수평 2 cm 이동(방향 무작위) | 그리퍼가 대상에 `near` 처음 참일 때 | DEV |
# | P2 | 방해물이 경로 옆에 등장 | 운반 단계 시작 뒤 0.5 s | DEV |
P3·P4 (and P5) are held out for TEST only (E §1.5, §4.5; plan Global Constraints): not implemented here on
purpose, and PerturbState refuses them.

Interpretation notes (ours, recorded in planner_dev.md):
- P1 `near`: the gripper (finger midpoint) within near_in_m (5 cm) of the target centre, the M1 near band.
  The move is one pose write of the target (+2 cm in x-y, z and orientation kept), velocity zeroed.
- P2 "경로 옆": a parked object (o10) is placed on the table beside the straight carry line target->tray,
  7-13 cm off the line (side and offset from the seed), not overlapping anything, resting on the table.
"""
from __future__ import annotations

import math

import numpy as np

from ..config import CFG

DEV_KINDS = ("P0", "P1", "P2")
P1_SHIFT_M = 0.02
P2_DELAY_S = 0.5
P2_LATERAL_M = (0.07, 0.13)


def _rng(seed: int, tag: int):
    return np.random.default_rng([int(seed), 23, tag])


def p1_offset(seed: int) -> np.ndarray:
    a = _rng(seed, 1).uniform(-math.pi, math.pi)
    return P1_SHIFT_M * np.array([math.cos(a), math.sin(a)])


def p2_spawn_xy(seed: int, start_xy, goal_xy, obstacles: dict, radius: float,
                table_x=(0.20, 0.62), table_y=(-0.55, 0.15)) -> np.ndarray:
    """A point beside the straight path start->goal: lateral offset in P2_LATERAL_M, along the segment,
    clear of every obstacle {id: (xy, footprint_r)} by 1 cm."""
    a, b = np.asarray(start_xy, float), np.asarray(goal_xy, float)
    L = float(np.linalg.norm(b - a))
    u = (b - a) / L
    n = np.array([-u[1], u[0]])
    rng = _rng(seed, 2)
    side0 = 1.0 if rng.random() < 0.5 else -1.0
    for i in range(4000):
        side = side0 if i < 2000 else -side0
        p = a + u * rng.uniform(0.0, L) + n * side * rng.uniform(*P2_LATERAL_M)
        if not (table_x[0] <= p[0] <= table_x[1] and table_y[0] <= p[1] <= table_y[1]):
            continue
        if all(np.linalg.norm(p - np.asarray(c)) >= r + radius + 0.01 for c, r in obstacles.values()):
            return p
    raise RuntimeError("P2: no free spot beside the path")


class PerturbState:
    """Decides when a DEV perturbation fires. poll() is called once per env step with oracle signals."""

    def __init__(self, kind: str, seed: int):
        if kind not in DEV_KINDS:
            raise ValueError(f"{kind}: only DEV perturbations {DEV_KINDS} exist in this code (P3/P4 held out)")
        self.kind, self.seed = kind, int(seed)
        self.fired = False
        self.t_carry = None
        self.event = None

    def poll(self, t: float, near_target: bool, phase: str):
        if self.fired or self.kind == "P0":
            return None
        if self.kind == "P1" and near_target:
            self.fired = True
        elif self.kind == "P2":
            if phase == "carry" and self.t_carry is None:
                self.t_carry = t
            if self.t_carry is not None and t - self.t_carry >= P2_DELAY_S - 1e-9:
                self.fired = True
        if self.fired:
            self.event = {"kind": self.kind, "t": t}
            return self.event
        return None


def perturb(env, kind: str, seed: int) -> None:
    """Arm a DEV perturbation on env (P0 = none). The episode loop calls apply_pending(env, t, signals)."""
    env.perturb_state = PerturbState(kind, seed)


def apply_pending(env, t: float, near_target: bool, phase: str):
    """Fire the armed perturbation if its trigger holds now. One pose write, never repeated. Returns the event."""
    from .scene import OBJ_GEOM, SCENE_SPEC, TABLE_TOP_Z

    st = getattr(env, "perturb_state", None)
    if st is None:
        return None
    ev = st.poll(t, near_target, phase)
    if ev is None:
        return None
    if st.kind == "P1":
        p, q = env.object_pose("o3")
        d = p1_offset(st.seed)
        env.write_object_pose("o3", (p[0] + d[0], p[1] + d[1], p[2]), tuple(q))
        ev["dxy_m"] = d.tolist()
    elif st.kind == "P2":
        k = SCENE_SPEC["p2_object"]
        g = OBJ_GEOM[k]
        mug, _ = env.object_pose("o3")
        tray, _ = env.object_pose("o5")
        obst = {j: (env.object_pose(j)[0][:2], OBJ_GEOM[j]["footprint_r"]) for j in env.present}
        xy = p2_spawn_xy(st.seed, env.carry_start_xy if hasattr(env, "carry_start_xy") else mug[:2], tray[:2],
                         obst, g["footprint_r"])
        env.write_object_pose(k, (xy[0], xy[1], TABLE_TOP_Z + g["half_extents"][2] + 0.001))
        env.present.append(k)
        ev["xy"] = xy.tolist()
    return ev


assert CFG.near_in_m == 0.05  # P1 trigger uses the M1 near band
