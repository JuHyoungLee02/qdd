"""DecCall for one pool/DEV snapshot line (Jev-L model selection, jevl_model_select.md prereg).

Six questions per snapshot: D-zoom dir_xy / dir_z / mag_coarse, H-plan target / phase, M7 mon.progress. Shown names
follow canon §27 R1 (jevcall option tables), NONE_ESCALATE last; answers are scored by option_key (R5).
"""
from .jevcall import DIR_XY, DIR_Z, MAG, NE, PROGRESS, build_choice, build_request
from .options import Option, to_option_key
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


def build_snapshot_request(line):
    """line: one ep<seed>.jsonl row (cli_pool.write_episode). Returns (request, {qid: oracle key}, {qid: options})."""
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
        qs.append(build_choice(qid, text, opts))
        oracle[qid] = line["oracle"][ORACLE_FIELD[q]]
        shown[qid] = (q, opts)
    return build_request(line["text_state"], qs), oracle, shown


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
