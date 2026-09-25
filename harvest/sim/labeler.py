"""Outcome-based labeler (E §2A.3, D4 F5): options tied for the best rollout score are all correct.

label(env, snap, question, options): for every option, restore the snapshot state once, execute that option for
one decision step (T_c = 0.33 s), then let the oracle planner run for up to ROLLOUT_S of sim time (10 s from the
snapshot). Score: success (the 1 s success predicate) = 1, otherwise stage progress + normalized remaining distance
in [0, 1); a planner failure (fail phase, mug off the table) scores 0. The best set = options within tol of the top.

How an option is executed (code tables, the same for every option of a question — M3 §4.2, canon §35):
- dir_xy / dir_z / mag_coarse: the TCP command moves linearly by m_c * unit(u_xy + u_z) over the step, where the
  asked component comes from the option and the other two from the oracle answer (u_xy in {-1,0,1}^2, u_z in
  {-1,0,1}, m_c = the MAG bin value). All-zero direction = hold still. Gripper and FSM run as the planner's.
- target (H-plan Q_target): the planner's goal for the step uses the option object in place of the mug (pick
  phases) or the tray (place phases); phases whose goal does not depend on an object are unchanged.
- phase (Q_phase): continue = planner step; next = force the FSM into the next phase now; hold = keep the
  command still with the FSM paused.
- fine_dir (H-plan near contact): plus_x ... minus_z move 1 cm (in contact) or 2 cm along the axis; hold = still;
  done = next phase. rot+/rot- are not asked: the top-down yaw is fixed by the oracle planner (IK study, T12).
Options that execute identically share one rollout (cache per snapshot), so a label is computed once per
option_key regardless of the naming variant A0-A4 (E §2A.7).
"""
from __future__ import annotations

import numpy as np

ROLLOUT_S = 10.0
CHECKPOINTS_S = (1.0, 2.0, 3.0, 5.0)  # rollout progress also recorded here (offline shorter-horizon labels)
D_REF_M = 0.30  # remaining-distance normalizer for the progress score (about one table-top move)
FINE_MAG_M = {"contact": 0.01, "near": 0.02}  # M3 §4.4 "코드가 {1cm, 2cm} 중 거리 범주로 고른다"
NE = "NONE_ESCALATE"

XY_UNIT = {"plus_x": (1, 0), "plus_x_plus_y": (1, 1), "plus_y": (0, 1), "minus_x_plus_y": (-1, 1),
           "minus_x": (-1, 0), "minus_x_minus_y": (-1, -1), "minus_y": (0, -1), "plus_x_minus_y": (1, -1),
           "none_xy": (0, 0)}
Z_UNIT = {"up": 1, "down": -1, "none_z": 0}
MAG_M = {"tiny": 0.005, "small": 0.01, "medium": 0.02, "large": 0.04, "xlarge": 0.08}  # = planner.MAG_BINS
FINE_KEYS = ("plus_x", "minus_x", "plus_y", "minus_y", "plus_z", "minus_z", "hold", "done")
PHASE_KEYS = ("continue", "next", "hold")
QUESTIONS = ("dir_xy", "dir_z", "mag_coarse", "target", "phase", "fine_dir")


def best_set(scores: dict, tol: float = 1e-6) -> set:
    top = max(scores.values())
    return {k for k, v in scores.items() if top - v <= tol}


# ------------------------------------------------------------------------------------------------ pure
def option_keys(question: str, present=("o3", "o5")) -> list[str]:
    """Labelled option keys of a question (NONE_ESCALATE is never labelled: it has no motion to roll out)."""
    if question == "dir_xy":
        return list(XY_UNIT)
    if question == "dir_z":
        return list(Z_UNIT)
    if question == "mag_coarse":
        return list(MAG_M)
    if question == "target":
        return sorted(present, key=lambda k: int(k[1:]))
    if question == "phase":
        return list(PHASE_KEYS)
    if question == "fine_dir":
        return list(FINE_KEYS)
    raise ValueError(question)


def displacement(xy_key: str, z_key: str, mag_key: str) -> np.ndarray:
    u = np.array([*XY_UNIT[xy_key], Z_UNIT[z_key]], float)
    n = float(np.linalg.norm(u))
    return np.zeros(3) if n == 0 else MAG_M[mag_key] * u / n


def exec_spec(question: str, key: str, oracle: dict) -> tuple:
    """Hashable description of how option `key` is executed for one step (identical specs share a rollout)."""
    if key == NE:
        raise ValueError("NONE_ESCALATE is not executed")
    if question in ("dir_xy", "dir_z", "mag_coarse"):
        xy = key if question == "dir_xy" else oracle["dir_xy"]
        z = key if question == "dir_z" else oracle["dir_z"]
        m = key if question == "mag_coarse" else oracle["mag_coarse"]
        d = displacement(xy, z, m)
        return ("hold",) if not d.any() else ("disp", *(float(v) for v in np.round(d, 6)))
    if question == "target":
        return ("plan",) if key == oracle["target"] else ("target", key)
    if question == "phase":
        return {"continue": ("plan",), "next": ("next",), "hold": ("hold",)}[key]
    if question == "fine_dir":
        if key == "hold":
            return ("hold",)
        if key == "done":
            return ("next",)
        d = np.zeros(3)
        d["xyz".index(key[-1])] = (1 if key.startswith("plus") else -1) * oracle.get("fine_mag", FINE_MAG_M["near"])
        return ("disp", *(float(v) for v in np.round(d, 6)))
    raise ValueError(question)


RULES = ("plan", "short3", "short2", "short1", "time0.33", "time0.66")  # prereg_labeler.md candidates
SIMPLICITY = {"plan": 0, "time0.33": 1, "time0.66": 1, "short3": 2, "short2": 3, "short1": 4}  # lower = simpler
D_START_MIN_M = 0.005  # close / open phases hold still: their start distance is ~0


def short_score(o: dict, h: float, phases) -> float:
    """D-short(h): phase index + (1 - dist/d_start) at h s; a failure within the 10 s rollout vetoes (0);
    success before h ranks above every running option."""
    if o["fail"]:
        return 0.0
    if o["success"] and o["t_success"] is not None and o["t_success"] <= h + 1e-9:
        return float(len(phases) + 1)
    c = o["checkpoints"].get(f"{h:g}")
    if c is None:  # rollout ended before h without success or failure (cannot happen with a 10 s horizon)
        c = {"phase": o["phase"], "dist_m": o["dist_m"], "d_start": o.get("d_start", o["dist_m"])}
    i = phases.index(c["phase"]) if c["phase"] in phases else 0
    return 1.0 + i + 1.0 - min(float(c["dist_m"]) / max(float(c["d_start"]), D_START_MIN_M), 1.0)


def rule_best(outs: dict, rule: str, phases) -> set:
    """Best option set of one question under a prereg candidate rule (outs: {option_key: rollout outcome})."""
    if rule == "plan":
        return best_set({k: score_outcome(o, phases) for k, o in outs.items()})
    if rule.startswith("short"):
        h = float(rule[5:])
        return best_set({k: short_score(o, h, phases) for k, o in outs.items()})
    if rule.startswith("time"):
        tau = float(rule[4:])
        ok = {k: o["t_success"] for k, o in outs.items() if o["success"]}
        if ok:
            t_best = min(ok.values())
            return {k for k, t in ok.items() if t <= t_best + tau + 1e-9}
        return best_set({k: score_outcome(o, phases) for k, o in outs.items()})
    raise ValueError(rule)


def select_rule(stats: dict, min_oracle: float = 0.90, tie: float = 0.02):
    """prereg_labeler.md: eligible = oracle-in-best >= 90 %; among eligible the largest discrimination, ties
    within 0.02 go to the simpler rule (D-plan > D-time > D-short, longer h). stats: {rule: (oracle_rate, disc)}.
    Returns the rule or None (no eligible rule -> E0.5 outcome accuracy verdicts are held)."""
    elig = {r: v for r, v in stats.items() if v[0] >= min_oracle}
    if not elig:
        return None
    top = max(v[1] for v in elig.values())
    near = [r for r, v in elig.items() if top - v[1] <= tie + 1e-12]
    # within a family the longer h / larger tau is closer to D-plan, hence "simpler" (prereg: "h는 긴 쪽")
    return min(near, key=lambda r: (SIMPLICITY[r], -float(r[5:]) if r.startswith("short") else -float(
        r[4:]) if r.startswith("time") else 0.0))


def score_outcome(o: dict, phases) -> float:
    """success = 1; failure = 0; otherwise (phase index + 1 - min(dist/D_REF, 1)) / len(phases), in [0, 1)."""
    if o["success"]:
        return 1.0
    if o["fail"]:
        return 0.0
    i = phases.index(o["phase"]) if o["phase"] in phases else 0
    frac = 1.0 - min(float(o["dist_m"]) / D_REF_M, 1.0)
    return (i + frac) / len(phases) * (1 - 1e-9)


# ------------------------------------------------------------------------------------------ Isaac (pod)
class Labeler:
    """Holds one OraclePlanner per env and a rollout cache per snapshot key."""

    def __init__(self, env, horizon_s: float = ROLLOUT_S):
        from .planner import OraclePlanner
        self.env, self.horizon_s = env, horizon_s
        self.pl = OraclePlanner(env)
        self.cache: dict = {}
        self.n_rollouts = 0
        self.sim_s = 0.0

    def outcome(self, snap: dict, spec: tuple) -> dict:
        key = (snap["key"], spec)
        if key not in self.cache:
            if snap.get("replay"):
                self.cache[key] = self._replay_rollout(snap, spec)
            else:
                self.cache[key] = self._rollout(snap["state"], spec)
        return self.cache[key]

    def _replay_rollout(self, snap: dict, spec: tuple) -> dict:
        """Exact restore (T13 Step 1, v2): re-run the episode from its reset with the oracle planner (bit-exact
        after a process's first episode) up to snapshot k and branch there. No state write at all besides the
        episode's own reset — PhysX contact caches are then the original ones. The replayed state is compared
        with the stored one (replay_maxabs, expected 0)."""
        from ..cli_pool import canonical_prefix, run_snapshot_episode
        from .snapshot import obs_from_json, state_maxabs
        r, out = snap["replay"], {}

        def on(env_, pl, rec, s, imgs):
            if rec["k"] != r["k"]:
                return False
            if snap.get("state") is not None:
                ref = snap["state"]
                out["replay_maxabs"] = state_maxabs(s, ref)
                out["replay_obj_mm"] = round(max(float(np.linalg.norm(np.asarray(s["obj_pose"][o][:3], float)
                                                                     - np.asarray(ref["obj_pose"][o][:3], float)))
                                                 for o in s["obj_pose"]) * 1e3, 6)
                out["replay_jpos_rad"] = float(np.abs(np.asarray(s["joint_pos"], float)
                                                      - np.asarray(ref["joint_pos"], float)).max())
            o = s["obs"]
            pl.pred, pl.ps._near = dict(o["pred"]), {(a, b): v for a, b, v in o["near_hyst"]}
            pl.objs, pl.grip, pl.contacts, pl.support = obs_from_json(o["raw"])
            pl.near_target = bool(np.linalg.norm(pl.grip.pos - pl.objs["o3"].pos) <= 0.05)
            out.update(self._branch(pl, spec))
            raise _Branched

        canonical_prefix(self.env)
        try:
            run_snapshot_episode(self.env, r["seed"], r["kind"], on_snapshot=on)
        except _Branched:
            pass
        if "success" not in out:
            raise RuntimeError(f"replay never reached snapshot k={r['k']} (seed {r['seed']} {r['kind']})")
        return out

    def label(self, snap: dict, question: str, options) -> dict:
        from .snapshot import PHASE_ORDER
        keys = [k for k in (getattr(o, "key", o) for o in options) if k != NE]
        outs = {k: self.outcome(snap, exec_spec(question, k, snap["oracle"])) for k in keys}
        scores = {k: score_outcome(o, PHASE_ORDER) for k, o in outs.items()}
        return {"best": best_set(scores), "scores": scores, "outcomes": outs}

    def _rollout(self, state: dict, spec: tuple) -> dict:
        from .snapshot import restore_state

        restore_state(self.env, state, planner=self.pl)  # write-restore (inexact on v2: see pool.md)
        return self._branch(self.pl, spec)

    def _branch(self, pl, spec: tuple) -> dict:
        """Execute option `spec` for one decision step from the current state, then the oracle planner."""
        from .perturb import apply_pending
        from .planner import success_from_history
        from .snapshot import DECIM, PHYS_DT, SUB_PER_SNAP, step_partial

        env = self.env
        t0 = env.sim_time
        sub0 = int(round(t0 / PHYS_DT))
        win_end = sub0 + SUB_PER_SNAP
        p0 = pl.cmd_pos.copy()
        hist, first, hold_q = [], True, None
        out = {"success": False, "fail": False, "t_success": None, "t_fail": None, "checkpoints": {}}
        cps = list(CHECKPOINTS_S)
        if spec[0] == "next":
            _force_next(env, pl)
        undo_target = _swap_target(pl, spec[1]) if spec[0] == "target" else None
        cur_phase, d_start = pl.phase, _progress(pl)["dist_m"]  # D-short: distance when the phase was entered
        while True:
            t = env.sim_time
            sub = int(round(t / PHYS_DT))
            pred = pl.pred if first else pl.observe()  # sensors are stale right after the write
            first = False
            hist.append((t, pred))
            if pl.phase != cur_phase:
                cur_phase, d_start = pl.phase, _progress(pl)["dist_m"]
            while cps and t - t0 >= cps[0] - 1e-9:
                out["checkpoints"][f"{cps.pop(0):g}"] = dict(_progress(pl), d_start=d_start)
            if pl.objs["o3"].pos[2] < -0.05 or pl.phase == "fail":
                out.update(fail=True, t_fail=round(t - t0, 3))
                break
            if success_from_history(hist):
                out.update(success=True, t_success=round(t - t0, 3))
                break
            if t - t0 >= self.horizon_s - 1e-9:
                break
            in_win = sub < win_end
            if not in_win and undo_target is not None:
                undo_target()
                undo_target = None
            if not in_win and hold_q is not None:
                pl.t_phase0 += SUB_PER_SNAP * PHYS_DT  # the pause does not count as phase time
                hold_q = None
            if in_win and spec[0] == "hold":
                if hold_q is None:
                    hold_q = np.concatenate([pl._ik(pl.cmd_pos, pl.cmd_quat), [pl.cmd_w]]).astype(np.float32)
                q = hold_q
            else:
                q = pl.step()
                if in_win and spec[0] == "disp":
                    n = min(DECIM, win_end - sub)
                    pl.cmd_pos = p0 + np.array(spec[1:4]) * min(1.0, (sub + n - sub0) / SUB_PER_SNAP)
                    q = np.concatenate([pl._ik(pl.cmd_pos, pl.cmd_quat), [pl.cmd_w]]).astype(np.float32)
            apply_pending(env, t, pl.near_target, pl.phase)
            step_partial(env, q, min(DECIM, win_end - sub) if in_win else DECIM)
        if undo_target is not None:
            undo_target()
        out.update(**_progress(pl), sim_s=round(env.sim_time - t0, 3), fail_stage=pl.fail_stage)
        self.n_rollouts += 1
        self.sim_s += env.sim_time - t0
        return out


class _Branched(Exception):
    pass


def _progress(pl) -> dict:
    goal = pl.cmd_pos if pl.phase == "fail" else pl._goal()[0]
    tcp, _ = pl.tcp_pose()
    return {"phase": pl.phase, "dist_m": round(float(np.linalg.norm(np.asarray(goal) - tcp)), 5)}


def _force_next(env, pl) -> None:
    """Move the FSM to the next phase now, with the planner's own transition side effects."""
    from .snapshot import next_phase_name
    new = next_phase_name(pl.phase)
    if new is None:
        return
    tcp, _ = pl.tcp_pose()
    if pl.phase == "close":
        pl.grasp_rel = (pl._mug() - tcp).tolist()
    if new == "retreat":
        pl.retreat_z = tcp[2] + 0.10
    if new == "carry":
        env.carry_start_xy = pl._mug()[:2].copy()
    pl.phase, pl.t_phase0 = new, env.sim_time
    pl.phase_log.append((env.sim_time, new))


def _swap_target(pl, k: str):
    """Point the planner's goal at object k for pick (approach/descend) or place (carry/place_descend) phases."""
    from .planner import APPROACH_ABOVE_TOP_M, CARRY_TCP_Z, GRASP_BELOW_TOP_M, PLACE_CLEAR_M
    from .scene import OBJ_GEOM
    orig, env = pl._goal, pl.env
    h = 2 * OBJ_GEOM[k]["half_extents"][2]

    def goal():
        z0 = env.table_top_z
        p = env.object_pose(k)[0]
        ph, v = pl.phase, orig()
        if ph == "approach" and k != "o3":
            return np.array([p[0], p[1], z0 + h + APPROACH_ABOVE_TOP_M]), v[1]
        if ph == "descend" and k != "o3":
            return np.array([p[0], p[1], z0 + h - GRASP_BELOW_TOP_M]), v[1]
        if ph == "carry" and k != "o5":
            return np.array([p[0], p[1], z0 + CARRY_TCP_Z]), v[1]
        if ph == "place_descend" and k != "o5":
            tcp, _ = pl.tcp_pose()
            mug = pl._mug()
            return np.array([p[0], p[1], tcp[2] - (mug[2] - pl.mug_h / 2 - (p[2] + h / 2)) + PLACE_CLEAR_M]), v[1]
        return v

    pl._goal = goal

    def undo():
        del pl._goal  # back to the class method

    return undo


def label(env, snap: dict, question: str, options) -> dict:
    """{"best": set of option_key, "scores": {option_key: float}} (+ raw rollout outcomes)."""
    lab = getattr(env, "_labeler", None)
    if lab is None:
        lab = env._labeler = Labeler(env)
    return lab.label(snap, question, options)
