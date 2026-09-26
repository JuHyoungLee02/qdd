"""Path-diversified episodes for MolmoAct on R2 (plan 2026-09-26-molmoact-r2-data, readiness M3; MolmoAct appendix D.7:
"exploring alternative paths towards the same target").

The oracle planner (planner.OraclePlanner) moves its TCP command in a straight line to each phase goal. With the
explicit generator option `--waypoints`, the two free-space phases (approach, carry) first go through one waypoint:
the midpoint of the phase's start command and its goal, shifted sideways (perpendicular in xy) by a signed offset of
5-9 cm drawn from (seed, task). Same goal, different path; every other phase, the grasp and the place are unchanged.

Pure geometry here (no Isaac); `waypoint_mixin(cls)` wraps a planner class so that `_goal()` returns the waypoint while
it is pending. The planner's phase switch compares the TCP with `_goal()`, so a pending waypoint can never count as
the phase goal: the waypoint is released as soon as the command comes within WP_PASS_R of it (the command then turns
towards the real goal, cutting the corner), before the command could stop on it.
"""
from __future__ import annotations

import numpy as np

WP_OFFSET_M = (0.05, 0.09)  # |sideways offset| (plan: readiness said 4-8 cm; 5-9 cm for >= 40 px image divergence)
WP_PHASES = ("approach", "carry")
WP_PASS_R = 0.02  # m: command within 2 cm of the waypoint -> head for the real goal
SAFE_X = (0.30, 0.52)  # world xy box the waypoint must stay in (reach; table / distractor band)
SAFE_Y = (-0.46, 0.02)
MIN_Z_TABLE = 0.18  # waypoint at least 18 cm above the table (distractors <= 10 cm)
MIN_MOVE_M = 0.01  # no waypoint for phases that move less than 1 cm in xy
_PHASE_CODE = {"approach": 0, "carry": 1}


def sample_offsets(seed: int, task: str) -> dict:
    """{phase: signed offset m} for (seed, task); independent of the variant (standard / dr share the path)."""
    from .tasks import TASK_CODE
    out = {}
    for ph in WP_PHASES:
        rng = np.random.default_rng([int(seed), 31, TASK_CODE[task], _PHASE_CODE[ph]])
        mag = float(rng.uniform(*WP_OFFSET_M))
        out[ph] = mag if rng.random() < 0.5 else -mag
    return out


def _inside(xy) -> bool:
    return SAFE_X[0] <= xy[0] <= SAFE_X[1] and SAFE_Y[0] <= xy[1] <= SAFE_Y[1]


def waypoint(start, goal, offset: float, table_z: float):
    """World waypoint: xy = midpoint + offset * left normal of the start->goal xy direction (flipped if outside the
    safe box, then clipped), z = midpoint z but >= table + MIN_Z_TABLE. None when the xy move is < MIN_MOVE_M."""
    s, g = np.asarray(start, float), np.asarray(goal, float)
    d = g[:2] - s[:2]
    n = float(np.linalg.norm(d))
    if n < MIN_MOVE_M:
        return None
    d = d / n
    left = np.array([-d[1], d[0]])
    mid = (s + g) / 2
    xy = mid[:2] + offset * left
    if not _inside(xy):
        xy = mid[:2] - offset * left
    xy = np.array([np.clip(xy[0], *SAFE_X), np.clip(xy[1], *SAFE_Y)])
    return np.array([xy[0], xy[1], max(mid[2], table_z + MIN_Z_TABLE)])


def wp_goal(wp, cmd_pos, real_goal, pass_r: float = WP_PASS_R):
    """(goal to command, passed): the waypoint while the command is farther than pass_r from it, else the real goal."""
    if wp is None or float(np.linalg.norm(np.asarray(wp) - np.asarray(cmd_pos))) <= pass_r:
        return real_goal, True
    return np.asarray(wp, float), False


def waypoint_mixin(base):
    """Planner subclass whose approach / carry goals go through one waypoint each (setup_waypoints(offsets) first)."""

    class WaypointPlanner(base):
        def setup_waypoints(self, offsets: dict):
            self.wp_offsets = dict(offsets)
            self.wp_state = {}

        def _goal(self):
            goal, v = super()._goal()
            ph = self.phase
            if ph not in getattr(self, "wp_offsets", {}):
                return goal, v
            st = self.wp_state.get(ph)
            if st is None:  # first goal query of this phase: fix the waypoint from the current command
                wp = waypoint(self.cmd_pos, goal, self.wp_offsets[ph], self.env.table_top_z)
                st = self.wp_state[ph] = {"wp": wp, "start": np.asarray(self.cmd_pos, float).copy(),
                                          "goal0": np.asarray(goal, float).copy(), "t_set": self.env.sim_time,
                                          "passed": wp is None, "t_pass": self.env.sim_time if wp is None else None}
            if st["passed"]:
                return goal, v
            g, passed = wp_goal(st["wp"], self.cmd_pos, goal)
            if passed:
                st["passed"], st["t_pass"] = True, self.env.sim_time
            return g, v

        def waypoint_log(self) -> dict:
            """Per phase: offset, waypoint / start / first goal (world m), times, passed."""
            def r(x):
                return None if x is None else [round(float(v), 6) for v in x]
            return {ph: {"offset_m": self.wp_offsets[ph], "wp": r(st["wp"]), "start": r(st["start"]),
                         "goal0": r(st["goal0"]), "t_set": round(float(st["t_set"]), 4),
                         "t_pass": None if st["t_pass"] is None else round(float(st["t_pass"]), 4),
                         "passed": bool(st["passed"])} for ph, st in self.wp_state.items()}

    return WaypointPlanner
