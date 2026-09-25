"""DecCall for one pool/DEV snapshot line (Jev-L model selection, jevl_model_select.md prereg).

Six questions per snapshot: D-zoom dir_xy / dir_z / mag_coarse, H-plan target / phase, M7 mon.progress. Shown names
follow canon §27 R1 (jevcall option tables), NONE_ESCALATE last; answers are scored by option_key (R5).
"""
from .jevcall import DIR_XY, DIR_Z, MAG, NE, PROGRESS, build_choice, build_request
from .options import Option, to_option_key
from .serialize import with_last_step
from .sim.snapshot import SPEC_NAMES, stage_of

QUESTIONS = ("dir_xy", "dir_z", "mag_coarse", "target", "phase", "progress")
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


def build_snapshot_request(line, text_state=None, shift=0):
    """line: one ep<seed>.jsonl row (cli_pool.write_episode). Returns (request, {qid: oracle key}, {qid: options}).
    text_state: state text to send instead of line["text_state"] (E3-lite S1/S2); shift: cyclic left shift of every
    option list, NONE_ESCALATE stays last (C3'' rotation, e3lite.md prereg). The state ends with the M4 (b) line
    `last_step: <category>` (last_step_of(line), canon §77, serializer ser-A-min-2)."""
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
    }
    qs, oracle, shown = [], {}, {}
    for q in QUESTIONS:
        qid, text, opts = spec[q]
        if shift:
            opts = rotate(opts, shift)
        qs.append(build_choice(qid, text, opts))
        oracle[qid] = line["oracle"][ORACLE_FIELD[q]]
        shown[qid] = (q, opts)
    st = line["text_state"] if text_state is None else text_state
    return build_request(with_last_step(st, last_step_of(line)), qs), oracle, shown


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
