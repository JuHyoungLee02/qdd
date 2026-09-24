"""T13 snapshots: full sim state save / one-shot restore / restore drift check, plus the pure pool helpers.

Continuous snapshots sit on the exact T_c grid (t_k = k * 0.33 s = 33 k physics substeps of 10 ms). An env step is
5 substeps, so when a grid time falls inside an env step that step is split in two (same target on every substep,
so the physics is the same as one unsplit step) — see step_partial.

Restore rule (Review Focus #5, past lesson "진단 쓰기가 컵을 흔들었다"): the state is written ONCE (joints, joint
targets, every rigid body pose + velocity, episode counters), then the sim steps without any further writes.
Contact sensors and applied torques are only refreshed by a physics step, so a restored planner starts from the
observation stored with the snapshot instead of re-reading the stale sensors.

Pure parts (no Isaac) are unit-tested in tests/sim/test_snapshot_logic.py.
"""
from __future__ import annotations

import copy

import numpy as np

from ..config import CFG

SNAP_DT = CFG.snapshot_dt_s  # 0.33 s (= T_c)
PHYS_DT = CFG.sim_dt  # 0.01 s
DECIM = CFG.decimation  # 5
SUB_PER_SNAP = int(round(SNAP_DT / PHYS_DT))  # 33
assert abs(SUB_PER_SNAP * PHYS_DT - SNAP_DT) < 1e-12

DEV_SEEDS = range(0, 30)
POOL_SEEDS = range(2000, 2120)
N_DECISION = 10  # decision snapshots per episode (E §1.5: 120 x 10 = 1,200)
OVERSAMPLE_FRAC = 0.30  # boundary (ambiguous) share of the decision snapshots (E §1.5)
POOL_KINDS = ("P0", "P1", "P2")  # DEV-public perturbations only; P3/P4 stay TEST-only
ROBOT_ARRAYS = ("joint_pos", "joint_vel", "joint_pos_target", "joint_vel_target", "joint_effort_target")


# --------------------------------------------------------------------------------------------- seeds (pure)
def check_seed(seed: int) -> int:
    """Only DEV (0-29) and POOL (2000-2119) seeds may be generated here. TEST / TEST-P5 / CAL are refused."""
    s = int(seed)
    if s not in DEV_SEEDS and s not in POOL_SEEDS:
        raise ValueError(f"seed {s}: only DEV 0-29 and POOL 2000-2119 (TEST 1000-1149 / TEST-P5 1300-1329 are "
                         f"never generated in this plan)")
    return s


def pool_kind(seed: int) -> str:
    """Seed-determined perturbation for a POOL episode: a fixed permutation of 40 x P0/P1/P2 over 2000-2119."""
    s = check_seed(seed)
    if s not in POOL_SEEDS:
        raise ValueError(f"{s} is not a POOL seed")
    perm = np.random.default_rng([2000, 13]).permutation(np.repeat(np.arange(3), 40))
    return POOL_KINDS[int(perm[s - POOL_SEEDS.start])]


def pool_split(seed: int) -> str:
    """Episode-level split (E §1.5: all snapshots of one episode on one side): 60 'fit' / 60 'eval', balanced
    within each perturbation kind (20 + 20 per kind)."""
    s = check_seed(seed)
    if s not in POOL_SEEDS:
        return "dev"
    same = [x for x in POOL_SEEDS if pool_kind(x) == pool_kind(s)]
    order = np.random.default_rng([2000, 17, POOL_KINDS.index(pool_kind(s))]).permutation(len(same))
    rank = int(order[same.index(s)])
    return "fit" if rank < len(same) // 2 else "eval"


# ------------------------------------------------------------------------------------------- grid (pure)
def snap_sub(k: int) -> int:
    """Physics substep index of continuous snapshot k (t_k = k * SNAP_DT)."""
    return k * SUB_PER_SNAP


def chunks_to(sub_now: int, sub_target: int, decim: int = DECIM) -> list[int]:
    """Substep chunks for the next env step so that sub_target (if it falls inside the step) is hit exactly."""
    d = sub_target - sub_now
    if 0 < d < decim:
        return [d, decim - d]
    return [decim]


def interval_stats(times) -> dict:
    dt = np.diff(np.asarray(times, float))
    if dt.size == 0:
        return {"n": 0}
    return {"n": int(dt.size), "mean": float(dt.mean()), "min": float(dt.min()), "max": float(dt.max())}


# ------------------------------------------------------------------------------------ ambiguity (pure)
def ambiguous_predicates(pos: dict, band=(CFG.near_in_m, CFG.near_out_m)) -> list[str]:
    """Predicates whose quantity is inside a hysteresis band (M1 §4: only `near` has one, 5-6 cm): the value
    shown depends on history, so the snapshot is marked ambiguous. pos: {id: xyz} (table frame)."""
    out = []
    ids = sorted(pos)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            d = float(np.linalg.norm(np.asarray(pos[a], float) - np.asarray(pos[b], float)))
            if band[0] <= d <= band[1]:
                out += [f"near({a},{b})", f"near({b},{a})"]
    return out


def boundary_flags(preds, ambiguous) -> list[bool]:
    """Boundary stratum for the 30 % oversampling (E §1.5 "경계 사례"): the snapshot is inside a hysteresis band
    (`ambiguous`), or some registered predicate changes value between it and the next continuous snapshot (the
    decision step starting here crosses a predicate threshold). The near band alone is too rare to fill 30 %
    (v2 pool: 4.6 % of snapshots); with the previous snapshot counted as well the stratum was 35 % of all
    snapshots, so "30 %" would not have been oversampling."""
    out = []
    for i, p in enumerate(preds):
        b = bool(ambiguous[i])
        for j in (i + 1,):
            if not b and 0 <= j < len(preds):
                q = preds[j]
                b = any(k in q and q[k] != v for k, v in p.items())
        out.append(b)
    return out


def select_decision(ambiguous, n: int = N_DECISION, frac: float = OVERSAMPLE_FRAC, rng=None):
    """Pick n decision snapshots out of one episode's candidates, round(n * frac) from the boundary stratum
    (ambiguous) and the rest from the others (topped up from the other stratum when one is short).
    Returns [(idx, oversampled, w_natural)] sorted by idx. w_natural = inverse inclusion weight scaled so the
    episode's weights sum to n (reweights the pool back to the natural boundary share); w_oversample is 1."""
    rng = rng if rng is not None else np.random.default_rng(0)
    amb = np.asarray(ambiguous, bool)
    N = len(amb)
    n = min(n, N)  # a short (failed) episode contributes all its snapshots
    B, R = np.flatnonzero(amb), np.flatnonzero(~amb)
    nb = min(int(round(n * frac)), len(B))
    nr = min(n - nb, len(R))
    nb = n - nr  # top up from the boundary stratum when the rest is short
    pick_b = rng.choice(B, nb, replace=False) if nb else np.array([], int)
    pick_r = rng.choice(R, nr, replace=False) if nr else np.array([], int)
    out = [(int(i), True, (len(B) / nb) * (n / N)) for i in pick_b] + \
          [(int(i), False, (len(R) / nr) * (n / N)) for i in pick_r]
    return sorted(out)


# ------------------------------------------------------------------------- oracle labels per snapshot (pure)
PHASE_ORDER = ("approach", "descend", "close", "lift", "carry", "place_descend", "open", "retreat", "done")
PICK_PHASES = ("approach", "descend", "close")
NEAR_CONTACT_PHASES = ("descend", "close", "place_descend", "open")  # M3 §4.4 "정렬/삽입/놓기 단계"


def next_phase_name(phase: str) -> str | None:
    if phase not in PHASE_ORDER or phase == "done":
        return None
    return PHASE_ORDER[PHASE_ORDER.index(phase) + 1]


def oracle_target(phase: str) -> str:
    """H-plan Q_target: the object the current motion is about (pick = mug o3, then place = tray o5)."""
    return "o3" if phase in PICK_PHASES else "o5"


def oracle_phase_choice(phase_now: str, phase_after: str) -> str:
    """Q_phase keys (M3 §4.3 continue / next / hold): 'next' when the planner leaves the phase within the step."""
    return "next" if phase_after != phase_now else "continue"


def fine_axis(d, eps: float = 0.0025) -> str:
    """Q_fine_dir oracle: the dominant axis of the commanded displacement (keys plus_x ... minus_z), or hold."""
    d = np.asarray(d, float)
    if float(np.linalg.norm(d)) < eps:
        return "hold"
    i = int(np.argmax(np.abs(d)))
    return ("plus_" if d[i] > 0 else "minus_") + "xyz"[i]


def oracle_progress(t: float, fail_t, events, window_s: float = 1.0) -> str:
    """M7 progress keys: failure from the planner's fail time on, allowed_change within window_s after a DEV
    perturbation fired (the stage allows it; the oracle re-targets), otherwise valid_progress. The oracle
    planner has no recovery branch, so 'recovering' never occurs here."""
    if fail_t is not None and t >= fail_t - 1e-9:
        return "failure"
    if any(0.0 <= t - e["t"] < window_s for e in events or ()):
        return "allowed_change"
    return "valid_progress"


# ----------------------------------------------------------------------------- text state (pure, cand. A)
SPEC_NAMES = {"o3": "mug red", "o5": "tray blue", "o8": "bottle green", "o9": "box yellow", "o10": "box purple",
              "o11": "marker magenta"}
STAGES = {
    "S1": {"text": "pick up mug o3", "exit": "holding(o3) lifted(o3)", "invariants": []},
    "S2": {"text": "place mug o3 on tray o5", "exit": "on(o3,o5)", "invariants": ["holding(o3)"]},
}
_S1 = ("approach", "descend", "close", "lift")


def stage_of(phase: str) -> str:
    return "S1" if phase in _S1 else "S2"


def elapsed_cat(t_in_phase: float, timeout: float) -> str:
    return "normal" if t_in_phase <= 0.5 * timeout else ("long" if t_in_phase <= timeout else "overdue")


def _yn(v):
    return "unknown" if v is None else ("yes" if v else "no")


def text_state(t: float, phase: str, t_in_phase: float, timeout: float, pred: dict, present, support: dict,
               grip_open: bool, holding: bool, arm_moving: bool, changes, names=SPEC_NAMES, contract="c1",
               stages=None, tgt: str = "o3") -> str:
    """Minimal serialization (E §1.4 measurement format, candidate-A shape) of one oracle snapshot.
    stages / tgt: the task's contract stages and target (R2 tasks.stages; default = the mug -> tray STAGES)."""
    from ..serialize import serialize_state

    sid = stage_of(phase)
    st = dict((stages or STAGES)[sid], id=sid, elapsed=elapsed_cat(t_in_phase, timeout))
    gripper = "open" if grip_open else (f"closed_holding({tgt})" if holding else "closed_empty")
    robot = f"gripper={gripper} arm={'moving' if arm_moving else 'still'}"
    objs = []
    for k in sorted(present, key=lambda x: int(x[1:])):
        sup = support.get(k)
        where = "held_by_gripper" if pred.get(f"holding({k})") else (f"on({sup})" if sup else "in_air")
        objs.append((k, names.get(k, k), where, "upright" if pred.get(f"upright({k})") else "tipped"))
    named = set()
    for s in (st["exit"], *st["invariants"]):
        named.update(s.split())
    rel = [(tc - t, p, _yn(a), _yn(b)) for tc, p, a, b in changes if -3.0 <= tc - t <= 0.0]
    return serialize_state(f"f{int(round(t / (PHYS_DT * DECIM)))} (t={t:.2f}s)", contract, st, robot, objs,
                           pred, named, rel)


def pred_changes(prev: dict, now: dict, t: float) -> list:
    return [(t, k, prev.get(k), v) for k, v in now.items() if k in prev and prev[k] != v]


# ---------------------------------------------------------------------- planner / observation state (pure)
_PL_FIELDS = ("phase", "t_phase0", "cmd_w", "_not_hold", "fail_stage", "retreat_z", "near_target")
_PL_ARRAYS = ("cmd_pos", "cmd_quat")


def _jsonable(x):
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, (np.floating, np.integer, np.bool_)):
        return x.item()
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    return x


def obs_to_json(objs, grip, contacts, support) -> dict:
    return {"objs": {k: {"pos": _jsonable(o.pos), "quat": _jsonable(o.quat_wxyz), "he": _jsonable(o.half_extents)}
                     for k, o in objs.items()},
            "grip": {"w": float(grip.width_m), "effort": float(grip.effort), "pos": _jsonable(grip.pos)},
            "contacts": sorted(sorted(c) for c in contacts), "support": dict(support)}


def obs_from_json(d: dict):
    from ..predicates import Gripper, Obj
    objs = {k: Obj(id=k, pos=np.array(v["pos"]), quat_wxyz=np.array(v["quat"]), half_extents=np.array(v["he"]))
            for k, v in d["objs"].items()}
    g = d["grip"]
    grip = Gripper(width_m=g["w"], effort=g["effort"], pos=np.array(g["pos"]))
    return objs, grip, {frozenset(c) for c in d["contacts"]}, dict(d["support"])


def planner_state(pl) -> dict:
    """Everything the oracle planner carries between control steps (JSON-able)."""
    d = {f: _jsonable(getattr(pl, f)) for f in _PL_FIELDS}
    d.update({f: _jsonable(np.asarray(getattr(pl, f), float)) for f in _PL_ARRAYS})
    d["grasp_rel"] = _jsonable(pl.grasp_rel)
    d["fail_info"] = _jsonable(pl.fail_info)
    d["near_hyst"] = [[a, b, bool(v)] for (a, b), v in sorted(pl.ps._near.items())]
    d["pred"] = _jsonable(pl.pred)
    d["obs"] = obs_to_json(pl.objs, pl.grip, pl.contacts, getattr(pl, "support", {})) if pl.grip is not None else None
    d["phase_log"] = _jsonable(pl.phase_log)
    return d


def apply_planner_state(pl, d: dict) -> None:
    for f in _PL_FIELDS:
        setattr(pl, f, d[f])
    for f in _PL_ARRAYS:
        setattr(pl, f, np.array(d[f], float))
    pl.grasp_rel = d["grasp_rel"]
    pl.fail_info = copy.deepcopy(d["fail_info"])
    pl.ps._near = {(a, b): v for a, b, v in d["near_hyst"]}
    pl.pred = dict(d["pred"])
    if d.get("obs"):
        pl.objs, pl.grip, pl.contacts, pl.support = obs_from_json(d["obs"])
    pl.phase_log = [tuple(x) for x in d["phase_log"]]
    pl.history = []


# ------------------------------------------------------------------------------- storage (pure: npz + json)
_JSON_KEYS = ("t", "steps", "episode_length_buf", "present", "seed", "carry_start_xy", "perturb", "planner", "obs")


def pack_states(states: list, obj_ids) -> tuple[dict, list]:
    """Stack saved states into npz arrays (numbers) + one JSON dict per state (FSM, observation, counters)."""
    arrays = {k: np.stack([s[k] for s in states]) for k in ROBOT_ARRAYS}
    arrays["obj_pose"] = np.stack([np.stack([s["obj_pose"][o] for o in obj_ids]) for s in states])
    arrays["obj_vel"] = np.stack([np.stack([s["obj_vel"][o] for o in obj_ids]) for s in states])
    arrays["action"] = np.stack([np.zeros(8, np.float32) if s.get("action") is None else s["action"] for s in states])
    arrays["rng_np_keys"] = np.stack([s["rng_np"][1] for s in states])
    arrays["rng_torch"] = np.stack([s["rng_torch"] for s in states])
    arrays["obj_ids"] = np.array(list(obj_ids))
    js = []
    for s in states:
        j = {k: _jsonable(s.get(k)) for k in _JSON_KEYS}
        j["rng_np_meta"] = [s["rng_np"][0], int(s["rng_np"][2]), int(s["rng_np"][3]), float(s["rng_np"][4])]
        j["has_action"] = s.get("action") is not None
        js.append(j)
    return arrays, js


def unpack_state(arrays, i: int, j: dict) -> dict:
    ids = [str(x) for x in arrays["obj_ids"]]
    s = {k: j.get(k) for k in _JSON_KEYS}
    for k in ROBOT_ARRAYS:
        s[k] = np.array(arrays[k][i])
    s["obj_pose"] = {o: np.array(arrays["obj_pose"][i, n]) for n, o in enumerate(ids)}
    s["obj_vel"] = {o: np.array(arrays["obj_vel"][i, n]) for n, o in enumerate(ids)}
    s["action"] = np.array(arrays["action"][i]) if j.get("has_action", True) else None
    m = j["rng_np_meta"]
    s["rng_np"] = (m[0], np.array(arrays["rng_np_keys"][i], dtype=np.uint32), m[1], m[2], m[3])
    s["rng_torch"] = np.array(arrays["rng_torch"][i])
    return s


def state_maxabs(a: dict, b: dict) -> float:
    """Largest absolute difference between two saved states (joints pos/vel, every body pose/vel)."""
    d = [float(np.abs(np.asarray(a[k], float) - np.asarray(b[k], float)).max()) for k in ("joint_pos", "joint_vel")]
    for grp in ("obj_pose", "obj_vel"):
        d += [float(np.abs(np.asarray(a[grp][o], float) - np.asarray(b[grp][o], float)).max()) for o in a[grp]]
    return max(d)


# ================================================================================ Isaac part (pod only)
def step_partial(env, q, n: int) -> None:
    """Run n (1..DECIM) physics substeps with target q, keeping the wrapper clock exact."""
    D = DECIM
    if n == D:
        env.step(q)
        return
    t0 = env.sim_time
    env.env.cfg.decimation = n  # ManagerBasedRLEnv.step reads cfg.decimation on every call
    try:
        env.step(q)
    finally:
        env.env.cfg.decimation = D
    env._steps += n / D - 1  # env.step advanced the clock by a whole env step
    assert abs(env.sim_time - (t0 + n * PHYS_DT)) < 1e-9, (env.sim_time, t0, n)


def capture(env, names=None) -> dict:
    """Render now and read the cameras (snapshots fall between env steps)."""
    env.env.sim.render()
    out = {}
    for n in (names or env.cameras):
        env.scene[n].update(0.0, force_recompute=True)
        out[n] = env.camera_rgb(n)
    return out


def _np(x):
    return x.detach().cpu().numpy().copy()


def save_state(env, planner=None, obs=None, action=None) -> dict:
    """Full sim state: joint pos / vel / all joint targets, every rigid body pose + velocity (parked ones too),
    episode counters, wrapper clock, perturbation state, RNG states, planner FSM state and the fresh observation."""
    import torch
    r = env.robot.data
    s = {"t": float(env.sim_time), "steps": float(env._steps),
         "episode_length_buf": int(env.env.episode_length_buf[0]),
         "present": list(env.present), "seed": int(env.seed),
         "carry_start_xy": _jsonable(getattr(env, "carry_start_xy", None)),
         "rng_np": np.random.get_state(), "rng_torch": torch.get_rng_state().numpy().copy()}
    for k in ROBOT_ARRAYS:
        s[k] = _np(getattr(r, k)[0])
    s["obj_pose"] = {k: _np(o.data.root_pose_w[0]) for k, o in env.objects.items()}
    s["obj_vel"] = {k: _np(o.data.root_vel_w[0]) for k, o in env.objects.items()}
    ps = getattr(env, "perturb_state", None)
    s["perturb"] = None if ps is None else {"kind": ps.kind, "seed": ps.seed, "fired": ps.fired,
                                            "t_carry": ps.t_carry, "event": _jsonable(ps.event)}
    s["action"] = None if action is None else np.asarray(action, np.float32).copy()
    if planner is not None:
        s["planner"] = planner_state(planner)
    if obs is not None:
        s["obs"] = obs  # {"pred", "near_hyst", "objs/grip/contacts/support" json}
    return s


PRIME_SUBSTEPS = 1  # see restore_state


def restore_state(env, s: dict, planner=None, prime: int | None = None) -> None:
    """Restore the saved state at restore time; afterwards the sim only steps (no per-step writes).

    prime (default PRIME_SUBSTEPS): PhysX keeps contact / friction-anchor caches that a state write cannot set, so
    the first steps after a plain write start from the caches of whatever was simulated last (v2, CPU PhysX, DEV 0:
    2.3 mm drift while the gripper squeezes the mug). With prime > 0 the state is written, `prime` physics substeps
    are run with the saved target (building caches for this very contact configuration), and the state is written
    again. Both writes happen once, at restore time."""
    _write_state(env, s)
    n = PRIME_SUBSTEPS if prime is None else int(prime)
    if n > 0 and s.get("action") is not None:
        step_partial(env, s["action"], n)
        _write_state(env, s)
    _restore_bookkeeping(env, s, planner)


def _write_state(env, s: dict) -> None:
    import torch
    dev = env.env.device
    rob = env.robot

    def T(x):
        return torch.as_tensor(np.asarray(x), dtype=torch.float32, device=dev).unsqueeze(0)

    rob.write_joint_state_to_sim(T(s["joint_pos"]), T(s["joint_vel"]))
    rob.set_joint_position_target(T(s["joint_pos_target"]))
    rob.set_joint_velocity_target(T(s["joint_vel_target"]))
    rob.set_joint_effort_target(T(s["joint_effort_target"]))
    for k, o in env.objects.items():
        o.write_root_pose_to_sim(T(s["obj_pose"][k]))
        o.write_root_velocity_to_sim(T(s["obj_vel"][k]))
    env.env.episode_length_buf[:] = int(s["episode_length_buf"])
    if s.get("action") is not None:
        env.env.action_manager.process_action(T(_full_action(env, s["action"])))
    sim = env.env.sim
    if sim.physics_sim_view is not None:
        sim.physics_sim_view.update_articulations_kinematic()
    env._steps = s["steps"]


def _restore_bookkeeping(env, s: dict, planner=None) -> None:
    import torch

    from .perturb import PerturbState
    env._steps = s["steps"]
    env.present = list(s["present"])
    if s.get("carry_start_xy") is not None:
        env.carry_start_xy = np.array(s["carry_start_xy"])
    elif hasattr(env, "carry_start_xy"):
        del env.carry_start_xy
    p = s.get("perturb")
    if p is None:
        env.perturb_state = None
    else:
        st = PerturbState(p["kind"], p["seed"])
        st.fired, st.t_carry, st.event = p["fired"], p["t_carry"], copy.deepcopy(p["event"])
        env.perturb_state = st
    np.random.set_state(s["rng_np"])
    torch.set_rng_state(torch.as_tensor(s["rng_torch"], dtype=torch.uint8))
    if planner is not None and s.get("planner") is not None:
        apply_planner_state(planner, s["planner"])
        if s.get("obs") is not None:  # fresh observation at the snapshot time (sensors are stale after a write)
            o = s["obs"]
            planner.pred = dict(o["pred"])
            planner.ps._near = {(a, b): v for a, b, v in o["near_hyst"]}
            planner.objs, planner.grip, planner.contacts, planner.support = obs_from_json(o["raw"])


def _full_action(env, q8):
    """8-D wrapper target -> the env action vector (7 arm + 4 gripper joints), as Env.step builds it."""
    from .scene import width_to_joint
    q8 = np.asarray(q8, np.float32)
    g = width_to_joint(float(q8[7]))
    return np.concatenate([q8[:7], [g, g, g, g]]).astype(np.float32)


def object_positions(env) -> dict:
    return {k: env.object_pose(k)[0].copy() for k in env.objects}


def hold_trace(env, q_hold, duration_s: float = 0.5, first_chunk: int | None = None) -> list:
    """Step with a constant target (no new command) for duration_s; object positions after every chunk."""
    n_total = int(round(duration_s / PHYS_DT))
    trace, done = [], 0
    while done < n_total:
        n = min(first_chunk or DECIM, DECIM, n_total - done) if done == 0 else min(DECIM, n_total - done)
        step_partial(env, q_hold, n)
        done += n
        trace.append((done, object_positions(env)))
    return trace


def restore_drift_check(env, s: dict, ref=None, duration_s: float = 0.5) -> float:
    """Restore s once, then hold the saved target (no command) for duration_s. Returns the max object position
    deviation (m) over the window: against the reference trace `ref` (same hold, run on the original
    un-restored state) when given, else against the snapshot pose for objects that were at rest
    (|v| < 1 cm/s). Must be <= 0.001 (Review Focus #5)."""
    restore_state(env, s)
    first = DECIM - (int(round(s["t"] / PHYS_DT)) % DECIM) or DECIM
    tr = hold_trace(env, s["action"], duration_s, first_chunk=first)
    dev = 0.0
    if ref is not None:
        for (n1, a), (n2, b) in zip(tr, ref):
            assert n1 == n2
            dev = max(dev, max(float(np.linalg.norm(a[k] - b[k])) for k in a))
        return dev
    rest = [k for k in env.objects if float(np.linalg.norm(s["obj_vel"][k][:3])) < 0.01]
    for _, a in tr:
        for k in rest:
            dev = max(dev, float(np.linalg.norm(a[k] - s["obj_pose"][k][:3])))
    return dev

