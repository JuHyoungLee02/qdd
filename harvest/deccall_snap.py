"""DecCall for one pool/DEV snapshot line (Jev-L model selection, jevl_model_select.md prereg).

Six questions per snapshot: D-zoom dir_xy / dir_z / mag_coarse, H-plan target / phase, M7 mon.progress. Shown names
follow canon §27 R1 (jevcall option tables), NONE_ESCALATE last; answers are scored by option_key (R5).
"""
from .jevcall import DIR_XY, DIR_Z, GRIPPER, MAG, NE, PROGRESS, build_choice, build_request
from .options import Option, to_option_key
from .serialize import MOTION_UNKNOWN, with_intent_last_step
from .sim.snapshot import SPEC_NAMES, stage_of

QUESTIONS = ("dir_xy", "dir_z", "mag_coarse", "target", "phase", "progress")
# canon §87 (ser-A-min-3): the fused VLA's DecCall adds the gripper question right after `phase` (fused=True)
ORDER_WITH_GRIPPER = ("dir_xy", "dir_z", "mag_coarse", "target", "phase", "gripper", "progress")
_AXIS = {("x", 1): "+x (away from the robot)", ("x", -1): "-x (toward the robot)", ("y", 1): "+y (robot left)",
         ("y", -1): "-y (robot right)"}
ORACLE_FIELD = {"dir_xy": "dir_xy", "dir_z": "dir_z", "mag_coarse": "mag_coarse", "target": "target",
                "phase": "phase_choice", "progress": "progress"}
PHASE = [Option("continue", "continue", "Keep executing the current motion phase."),
         Option("next", "next", "Switch to the next motion phase now."),
         Option("hold", "hold", "Pause and keep the gripper still."), NE]


def _target_opts(present):
    out = []
    for k in sorted(present, key=lambda x: int(x[1:])):
        kind = SPEC_NAMES.get(k, k).split()
        desc = f"The {kind[1]} {kind[0]}." if len(kind) == 2 else f"Object {k}."
        out.append(Option(k, k, desc))
    return out + [NE]


# Controller ruling PH-A1 (ser-A-min-3; prompt_health.md F16 / F17): the FUSED VLA's dir_xy / mag_coarse wording states
# the labels_v2 definitions exactly (labels unchanged): the remaining displacement d = G - g from the gripper fingertip
# midpoint g to the current sub-goal G (table frame: +x away from the robot, +y robot left). dir_xy = per-axis sign
# pattern with the DEADBAND_M dead band (labels_v2.dir_xy_label); mag_coarse = |d| (3D) binned by MAG_EDGES_M
# (labels_v2.mag_label). Option keys / names (the decision tokens) are the same as the modular tables.
def _cm(m: float) -> str:
    return f"{m * 100:.2f} cm"


def fused_dir_xy_opts() -> list:
    from .labels_v2 import _XY, DEADBAND_M
    db = _cm(DEADBAND_M)

    def part(ax, s):
        return f"under {db} either way" if s == 0 else f"at least {db} toward {_AXIS[(ax, s)]}"
    signs = {k: s for s, k in _XY.items()}
    out = []
    for o in DIR_XY:  # the modular table's order and names
        if o.key == NE.key:
            continue
        sx, sy = signs[o.key]
        d = (f"|x| and |y| both under {db}" if (sx, sy) == (0, 0) else f"x {part('x', sx)}; y {part('y', sy)}")
        out.append(Option(o.key, o.name, f"Remaining offset to the sub-goal: {d}."))
    return out + [NE]


def fused_mag_opts() -> list:
    from .labels_v2 import MAG_EDGES_M
    from .sim.planner import MAG_BINS
    names, e = [n for n, _ in MAG_BINS], MAG_EDGES_M
    desc = [f"Remaining distance to the sub-goal under {_cm(e[0])}."]
    desc += [f"Remaining distance to the sub-goal from {_cm(a)} to under {_cm(b)}." for a, b in zip(e, e[1:])]
    desc += [f"Remaining distance to the sub-goal {_cm(e[-1])} or more."]
    return [Option(n, n, d) for n, d in zip(names, desc)] + [NE]


def fused_texts(ds: str, sid: str) -> dict:
    """The fused DecCall's dir_xy / mag_coarse question texts (ruling PH-A1)."""
    from .labels_v2 import DEADBAND_M
    return {"dir_xy": f"During step {ds}, what is the sign pattern of the remaining horizontal offset (x, y) from the "
                      f"gripper fingertip midpoint to the current sub-goal of stage {sid}? An axis counts only beyond "
                      f"{_cm(DEADBAND_M)} (+x = away from the robot, +y = robot left).",
            "mag_coarse": f"During step {ds}, how far (3D distance) is the gripper fingertip midpoint from the current "
                          f"sub-goal of stage {sid}?"}


_T1 = ("gripper_open", "holding_t", "lifted_holding")  # = runtime.measure.T1 (robot side, hard channel)


def category_of_check(phase_prev: str, phase_now: str, violations) -> str:
    """M4 (b) category of a finished step from its post-step expectation check, the runtime rule
    (core._boundary + measure.expected_check): the step changed phase -> no expectation check -> OK; a robot-side
    (T1) expectation false -> CONTRADICT; a world-side (T2) one -> DEVIATE; else OK. An OR entry ("a|b") is T1 only
    if all its members are."""
    if phase_prev != phase_now:
        return "OK"
    tiers = [all(x in _T1 for x in v.split("|")) for v in violations or ()]
    return "CONTRADICT" if any(tiers) else ("DEVIATE" if tiers else "OK")


def last_step_of(line: dict) -> str:
    """The (b) line value of a snapshot line (canon §77): an explicit `last_step` (annotate_last_step, runtime);
    else the recorded post-step check of an R2 line (`verify.prev_step`, datagen.episode); else "none"."""
    if line.get("last_step") is not None:
        return line["last_step"]
    pv = (line.get("verify") or {}).get("prev_step")
    if pv is None:
        return "none"
    return category_of_check(pv["phase"], line["phase"], pv.get("violations"))


def annotate_last_step(lines: list) -> list:
    """Set `last_step` on the lines of one episode (in file order). R2 lines use their recorded `verify.prev_step`;
    cli_pool lines (0.33 s snapshots, no `verify`) are judged like datagen.rows.verify_prev_step: the previous
    snapshot's phase expectations (m4b.spec.EXPECT) on this snapshot's recorded predicates (truth9 of the task's
    target / place, contact_stall unknown). The first snapshot (no finished step) -> "none"."""
    from .datagen.rows import truth9
    from .m4b.spec import violations
    from .sim import tasks as TK
    for i, ln in enumerate(lines):
        if ln.get("last_step") is not None:
            continue
        if "verify" in ln:
            ln["last_step"] = last_step_of(ln)
            continue
        prev = lines[i - 1] if i else None
        if prev is None or prev.get("k") != ln.get("k", 0) - 1 or prev.get("seed") != ln.get("seed") \
                or "pred" not in ln or "phase" not in prev:
            ln["last_step"] = "none"
            continue
        spec = TK.TASKS.get(ln.get("task") or "mug_tray", TK.TASKS["mug_tray"])
        tr = {**truth9(ln["pred"], spec.target, spec.place, False), "contact_stall": None}
        ln["last_step"] = category_of_check(prev["phase"], ln["phase"], violations(prev["phase"], tr))
    return lines


def motion_of(line: dict) -> str:
    """The motion line of a snapshot line (canon §83): the runtime / datagen value, else the trained 'unknown'."""
    return line.get("motion") or MOTION_UNKNOWN


def segment_of(line: dict) -> str:
    """The segment-intent line of a snapshot line (canon §90): an explicit value (runtime: Astra's agreed plan, unknown
    until set), else the training rule from the recorded planner phase (harvest.intent.segment_from_phase)."""
    if line.get("segment"):
        return line["segment"]
    from .intent import segment_from_phase
    return segment_from_phase(line.get("phase"))


def build_snapshot_request(line, text_state=None, shift=0, fused=False):
    """line: one ep<seed>.jsonl row (cli_pool.write_episode). Returns (request, {qid: oracle key}, {qid: options}).
    text_state: state text to send instead of line["text_state"] (E3-lite S1/S2); shift: cyclic left shift of every
    option list, NONE_ESCALATE stays last (C3'' rotation, e3lite.md prereg). The state ends with the segment-intent
    line (segment_of, canon §90), the motion line (motion_of, canon §83) and the M4 (b) line `last_step: <category>`
    (last_step_of(line), canon §77), serializer ser-A-min-3. fused: the fused VLA's DecCall (stage B and the fused
    runtime) -- adds the canon §87 gripper decision question after `phase` (its oracle = the rule label of the line's
    phase, harvest.intent) and words dir_xy / mag_coarse as their labels_v2 definitions (ruling PH-A1:
    fused_texts / fused_dir_xy_opts / fused_mag_opts); the modular (Jev-L) DecCall is unchanged."""
    ds, sid = line["ds_id"], stage_of(line["phase"])
    q_dir = f"Which direction should the gripper move during step {ds} to make progress toward the exit of stage {sid}?"
    spec = {
        "dir_xy": (f"{ds}.dir_xy", q_dir, DIR_XY),
        "dir_z": (f"{ds}.dir_z", q_dir, DIR_Z),
        "mag_coarse": (f"{ds}.mag_coarse", f"How far should the gripper move during step {ds}?", MAG),
        "target": (f"{ds}.target", f"Which object is the robot's current motion about during step {ds}?",
                   _target_opts(line["state"]["present"])),
        "phase": (f"{ds}.phase", f"During step {ds}, should the robot keep its current motion phase, switch to the "
                                 f"next phase of stage {sid}, or pause?", PHASE),
        "progress": ("mon.progress", f"Considering the change since the last step, how is stage {sid} going?",
                     PROGRESS),
        "gripper": (f"{ds}.gripper", f"During step {ds}, should the gripper close (grasp), open (release), or keep "
                                     f"its current state?", GRIPPER),
    }
    if fused:
        ft = fused_texts(ds, sid)
        spec["dir_xy"] = (f"{ds}.dir_xy", ft["dir_xy"], fused_dir_xy_opts())
        spec["mag_coarse"] = (f"{ds}.mag_coarse", ft["mag_coarse"], fused_mag_opts())
    qs, oracle, shown = [], {}, {}
    for q in (ORDER_WITH_GRIPPER if fused else QUESTIONS):
        qid, text, opts = spec[q]
        if shift:
            opts = rotate(opts, shift)
        qs.append(build_choice(qid, text, opts))
        if q == "gripper":
            from .intent import from_phase
            oracle[qid] = from_phase(line.get("phase"))
        else:
            oracle[qid] = line["oracle"][ORACLE_FIELD[q]]
        shown[qid] = (q, opts)
    st = line["text_state"] if text_state is None else text_state
    return build_request(with_intent_last_step(st, segment_of(line), motion_of(line), last_step_of(line)), qs), \
        oracle, shown


def rotate(opts, i):
    """Cyclic left shift by i of the options other than NONE_ESCALATE; NONE_ESCALATE stays last."""
    body = [o for o in opts if o.key != NE.key]
    tail = [o for o in opts if o.key == NE.key]
    j = i % len(body)
    return body[j:] + body[:j] + tail


def score(answers, oracle, shown):
    """answers: CallRecord.answers ({qid: {choice (shown name), confidence}}). One row per question."""
    rows = []
    for qid, (q, opts) in shown.items():
        a = answers.get(qid)
        key = to_option_key(opts, a["choice"]) if a else None
        rows.append({"question": q, "qid": qid, "oracle": oracle[qid], "key": key,
                     "p_chosen": a["confidence"] if a else None, "correct": key is not None and key == oracle[qid],
                     "ne": key == NE.key})
    return rows
