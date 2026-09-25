"""Stage-A SFT items from the POOL + a pluggable target source (canon §51-§53, D26 §1.4).

One item = (decision snapshot, DecCall question). The item carries exactly what Jev-L sends at inference
(jevl.JevLClient._body): the DecCall text built by deccall_snap.build_snapshot_request, rendered by
jevl.question_text, plus the head-camera image path. State text default = E3-lite S1 (canon §53).

Targets come from a *source*: source(line, question, option_keys) -> (set of option_keys, is_NONE_ESCALATE) or
None (no label -> no item). The line handed to a source has no `oracle` field, and build_snapshot_request gets a
dummy oracle, so no target and no prompt can depend on the pool's `oracle` (canon §50: ill-posed).
- OutcomeLabels: the labeler's best set under the pre-registered score rule (prereg_labeler.md); NONE_ESCALATE
  only when every labelled option scores 0 (§52 decision 1).
- LabelsV2 (canon §54, primary SFT target): harvest/labels_v2.py answers (remaining displacement from the actual
  finger midpoint to the sub-phase goal, sign / bin with a 1 cm dead band; target / phase from stage + facts),
  file <episode folder>.labels_v2.jsonl (e.g. jsel_dev/P0.labels_v2.jsonl next to jsel_dev/P0/). Its `progress`
  is the old oracle value and is never served.
- FnSource: any function (source_factory plug-in).
Questions: those both asked by DecCall and labelled (dir_xy, dir_z, mag_coarse, target, phase); `progress` has no
label yet and `fine_dir` is not a DecCall question.
Split: the POOL episode flag (fit -> train, eval -> val). DEV episodes only with an explicit dev_val_seeds split
(smoke); CAL/TEST (and anything else) are always refused.
"""
from __future__ import annotations

import glob
import json
import os
from collections import defaultdict

from ..clients.jevl import question_text
from ..deccall_snap import annotate_last_step, build_snapshot_request
from ..sim import labeler as L
from ..sim.snapshot import PHASE_ORDER

NE = "NONE_ESCALATE"
QUESTIONS = ("dir_xy", "dir_z", "mag_coarse", "target", "phase")
SPLIT = {"fit": "train", "eval": "val"}
_NO_ORACLE = defaultdict(lambda: None)  # what build_snapshot_request sees instead of line["oracle"]


def rule_scores(outs: dict, rule: str, phases=PHASE_ORDER) -> dict:
    """Per-option score under a prereg candidate rule (D-time ranks by success time, its score is D-plan's)."""
    if rule == "plan" or (rule.startswith("time") and rule in L.RULES):
        return {k: L.score_outcome(o, phases) for k, o in outs.items()}
    if rule.startswith("short") and rule in L.RULES:
        return {k: L.short_score(o, float(rule[5:]), phases) for k, o in outs.items()}
    raise ValueError(rule)


def target_keys(row: dict, rule: str) -> tuple[set, bool]:
    """(target option_keys, is_NONE_ESCALATE) of one label row under `rule`."""
    if row.get("rule") and row["rule"] != rule:
        raise ValueError(f"{row['key']} {row['question']}: finalized with rule {row['rule']}, asked {rule}")
    if max(rule_scores(row["outcomes"], rule).values()) <= 0.0:
        return {NE}, True
    return set(row["best_by_rule"][rule]), False


class OutcomeLabels:
    name = "outcome"

    def __init__(self, labels: dict, rule: str):
        """labels: {snapshot key 'ep<seed>_k<k>': [label rows of cli_label]}."""
        if rule not in L.RULES:
            raise ValueError(f"rule must be one of {L.RULES}")
        self.labels, self.rule = labels, rule

    def __call__(self, line, question, keys):
        rows = [r for r in self.labels.get(f"ep{line['seed']}_k{line['k']}", []) if r["question"] == question]
        if not rows:
            return None
        row = rows[0]
        if set(row["outcomes"]) != set(keys):
            raise ValueError(f"ep{line['seed']}_k{line['k']} {question}: labelled options {sorted(row['outcomes'])}"
                             f" != shown {keys}")
        return target_keys(row, self.rule)


V2_FIELD = {"dir_xy": "dir_xy", "dir_z": "dir_z", "mag_coarse": "mag_coarse", "target": "target",
            "phase": "phase_choice"}  # no progress: labels_v2's progress is the old oracle value


class LabelsV2:
    name = "labels_v2"

    def __init__(self, labels: dict):
        """labels: {(seed, kind, k): labels_v2 dict}."""
        self.labels = labels

    def __call__(self, line, question, keys):
        lab = self.labels.get((line["seed"], line.get("kind"), line["k"]))
        if lab is None or question not in V2_FIELD or lab.get(V2_FIELD[question]) is None:
            return None
        v = lab[V2_FIELD[question]]
        if v not in keys:
            raise ValueError(f"ep{line['seed']}_k{line['k']} {question}: labels_v2 answer {v!r} not in {keys}")
        return {v}, False


def labels_v2_path(folder: str) -> str:
    return folder.rstrip("/\\") + ".labels_v2.jsonl"


def read_labels_v2(path: str) -> dict:
    out = {}
    for x in open(path, encoding="utf-8"):
        r = json.loads(x)
        out[(r["seed"], r["kind"], r["k"])] = r["labels_v2"]
    return out


def labels_v2_factory(path: str | None = None):
    """source_factory for LabelsV2; path None = the sibling file of each pool folder (labels_v2_path)."""
    cache: dict = {}

    def make(pool_dir, seed):
        p = path or labels_v2_path(pool_dir)
        if p not in cache:
            cache[p] = LabelsV2(read_labels_v2(p)) if os.path.exists(p) else None
        return cache[p]
    return make


class FnSource:
    name = "fn"

    def __init__(self, fn):
        self.fn = fn

    def __call__(self, line, question, keys):
        return self.fn(line, question, keys)


def split_of(line: dict, dev_val_seeds=None) -> str:
    sp = line.get("split")
    if sp == "dev" and dev_val_seeds is not None:  # smoke only: DEV episodes split by seed
        return "val" if line["seed"] in dev_val_seeds else "train"
    if sp not in SPLIT:
        raise ValueError(f"seed {line.get('seed')}: split {sp!r} is not a POOL fit/eval episode")
    return SPLIT[sp]


def build_items(lines, source, state_fn=None, shift: int = 0, dev_val_seeds=None) -> list[dict]:
    """lines: pool ep<seed>.jsonl rows; source: see module doc; state_fn(line) -> state text (None = the pool's
    text_state, i.e. E3-lite S0); shift: C3'' option rotation (0 = fixed order). The DecCall state ends with the M4
    (b) line of the snapshot (deccall_snap.annotate_last_step: the recorded post-step check, canon §77) -- pass the
    whole episode (a pre-annotated line keeps its value)."""
    items = []
    lines = annotate_last_step(list(lines))
    for line in lines:
        if not line.get("decision"):
            continue
        blind = {k: v for k, v in line.items() if k != "oracle"}
        split = split_of(line, dev_val_seeds)
        req, _, shown = build_snapshot_request({**blind, "oracle": _NO_ORACLE},
                                               text_state=None if state_fn is None else state_fn(blind), shift=shift)
        for qid, (q, opts) in shown.items():
            if q not in QUESTIONS:
                continue
            keys = [o.key for o in opts if o.key != NE]
            got = source(blind, q, keys)
            if got is None:
                continue
            tkeys, ne = got
            if not tkeys or not set(tkeys) <= set(keys) | {NE}:
                raise ValueError(f"ep{line['seed']}_k{line['k']} {q}: target {sorted(tkeys)} not in {keys}")
            spec = req["questions"][qid]
            items.append({"key": f"{line.get('kind')}_ep{line['seed']}_k{line['k']}", "seed": line["seed"], "kind": line.get("kind"),
                          "k": line["k"], "split": split, "question": q, "qid": qid,
                          "text": question_text(req["state"], qid, spec), "image": line["images"]["cam_head"],
                          "names": list(spec["criteria"]), "target": [o.name for o in opts if o.key in tkeys],
                          "ne": bool(ne), "source": getattr(source, "name", "custom")})
    return items


def _read_labels(path):
    labels: dict = {}
    for x in open(path, encoding="utf-8"):
        try:
            r = json.loads(x)
        except json.JSONDecodeError:  # a partial file may end mid-line
            continue
        labels.setdefault(r["key"], []).append(r)
    return labels


def outcome_factory(rule: str, partial: bool = False):
    """source_factory for OutcomeLabels: pool_dir/labels/ep<seed>.jsonl (.done required unless partial)."""
    def make(pool_dir, seed):
        p = f"{pool_dir}/labels/ep{seed}.jsonl"
        if not os.path.exists(p) or (not partial and not os.path.exists(p + ".done")):
            return None
        labels = _read_labels(p)
        if partial:  # the last snapshot of an unfinished file may be cut
            labels = {k: v for k, v in labels.items() if len(v) >= len(QUESTIONS)}
        return OutcomeLabels(labels, rule)
    return make


def state_fn(state: str, step_cm: float):
    """Prompt state text: S0 = the pool text_state (None), S1/S2 = e3lite.state_text on a step_cm grid."""
    if state == "S0":
        return None
    from .. import e3lite
    return lambda ln: e3lite.state_text(ln, state, step_cm=step_cm)


def camera_of(item: dict) -> str:
    """Camera configuration string of an item's prompt (question_id hash input, canon §59): 'H:cam_head' = the
    legacy single head image without label (= jevl._body), else stageb_data.camera_config of its labelled list."""
    if item.get("images"):
        from .stageb_data import camera_config
        return camera_config(item["images"])
    return "H:cam_head" if item.get("image") else "T"


def load_pool(pool_dir: str, rule: str | None = None, state: str = "S1", shift: int = 0, partial: bool = False,
              source_factory=None, step_cm: float = 0.1, dev_val_seeds=None, cameras: str = "H",
              arm: str = "right") -> list[dict]:
    """All items of one episode folder. source_factory(pool_dir, seed) -> source or None (skip the episode);
    default = outcome labels under `rule`. S1 default grid 1 mm (canon §54).
    cameras: H = head image only, no label (the §55 smoke prompt, = jevl._body); HW = canon §59 layout (labelled
    head 672x376 + active-arm wrist 424x240, native, = jevl._body_mm layout HW); `arm` = the active arm (the
    POOL task is single-arm right; stageb rows carry their own)."""
    if cameras not in ("H", "HW"):
        raise ValueError(f"cameras {cameras!r}: H | HW")
    if source_factory is None:
        if rule is None:
            raise ValueError("rule is required for outcome labels")
        source_factory = outcome_factory(rule, partial)
    sfn = state_fn(state, step_cm)
    items = []
    for p in sorted(glob.glob(f"{pool_dir}/ep*.jsonl"), key=lambda x: int(os.path.basename(x)[2:-6])):
        seed = int(os.path.basename(p)[2:-6])
        src = source_factory(pool_dir, seed)
        if src is None:
            continue
        lines = [json.loads(x) for x in open(p, encoding="utf-8")]
        imgs = {}
        if cameras == "HW":
            from .stageb_data import images_of
            imgs = {(ln["seed"], ln.get("kind"), ln["k"]): images_of(ln, arm, True, pool_dir)
                    for ln in lines if ln.get("decision")}
        for it in build_items(lines, src, sfn, shift, dev_val_seeds):
            it["image"] = os.path.join(pool_dir, it["image"])  # folders may differ (DEV P0/P1/P2)
            if cameras == "HW":
                it["images"] = imgs[(it["seed"], it["kind"], it["k"])]
            items.append(it)
    return items
