import copy

import pytest

from harvest.clients.jevl import question_text
from harvest.sim import labeler as L
from harvest.sim.snapshot import PHASE_ORDER
from harvest.train import stagea_data as D

NE = "NONE_ESCALATE"


def _line(seed=2000, k=21, split="fit", present=("o3", "o5")):
    return {"seed": seed, "kind": "P0", "split": split, "k": k, "ds_id": "ds21", "phase": "carry", "decision": True,
            "text_state": "t_state: f1\nrobot: x", "state": {"present": list(present)},
            "images": {"cam_head": f"img/ep{seed}/k{k:03d}_cam_head.jpg"},
            "oracle": {"dir_xy": "plus_y", "dir_z": "none_z", "mag_coarse": "large", "target": "o5",
                       "phase_choice": "continue", "progress": "valid_progress"}}


def _out(success=False, fail=False, phase="carry", dist=0.1, t_success=None):
    cps = {f"{h:g}": {"phase": phase, "dist_m": dist, "d_start": 0.2} for h in L.CHECKPOINTS_S}
    return {"success": success, "fail": fail, "t_success": t_success, "t_fail": None, "phase": phase, "dist_m": dist,
            "checkpoints": cps, "sim_s": 1.0, "fail_stage": None}


def _row(q, outs, seed=2000, k=21, split="fit", rule="plan"):
    by_rule = {ru: sorted(L.rule_best(outs, ru, PHASE_ORDER)) for ru in L.RULES}
    return {"key": f"ep{seed}_k{k}", "question": q, "rule": rule, "best": by_rule[rule], "best_by_rule": by_rule,
            "outcomes": outs, "seed": seed, "k": k, "split": split}


def _rows(seed=2000, k=21, split="fit", fail_all=None):
    rows = []
    for q in ("dir_xy", "dir_z", "mag_coarse", "target", "phase"):
        keys = L.option_keys(q, ("o3", "o5"))
        outs = {kk: _out(dist=0.05 + 0.01 * i) for i, kk in enumerate(keys)}  # first key is the unique best
        if q == fail_all:
            outs = {kk: _out(fail=True) for kk in keys}
        rows.append(_row(q, outs, seed, k, split))
    rows.append(_row("fine_dir", {kk: _out() for kk in L.option_keys("fine_dir")}, seed, k, split))
    return rows


def test_rule_scores_match_labeler_scores():
    outs = {"a": _out(success=True, t_success=2.0), "b": _out(fail=True), "c": _out(dist=0.1)}
    s = D.rule_scores(outs, "plan", PHASE_ORDER)
    assert s == {k: L.score_outcome(o, PHASE_ORDER) for k, o in outs.items()}
    s2 = D.rule_scores(outs, "short2", PHASE_ORDER)
    assert s2 == {k: L.short_score(o, 2.0, PHASE_ORDER) for k, o in outs.items()}
    assert D.rule_scores(outs, "time0.33", PHASE_ORDER) == s  # D-time zero-ness = D-plan fallback score
    with pytest.raises(ValueError):
        D.rule_scores(outs, "bogus", PHASE_ORDER)


def test_target_keys_best_set_and_ne_only_when_all_zero():
    row = _row("dir_z", {"up": _out(dist=0.05), "down": _out(dist=0.05), "none_z": _out(dist=0.2)})
    assert D.target_keys(row, "plan") == ({"up", "down"}, False)
    row = _row("dir_z", {k: _out(fail=True) for k in ("up", "down", "none_z")})
    assert D.target_keys(row, "plan") == ({NE}, True)
    # one survivor -> no NE even if its score is tiny
    row = _row("dir_z", {"up": _out(fail=True), "down": _out(fail=True), "none_z": _out(dist=0.29)})
    assert D.target_keys(row, "plan") == ({"none_z"}, False)


def test_target_keys_uses_requested_rule_and_rejects_conflicting_finalized_rule():
    row = _row("dir_z", {"up": _out(dist=0.05), "down": _out(dist=0.06), "none_z": _out(dist=0.2)}, rule="plan")
    assert D.target_keys(row, "plan")[0] == set(row["best_by_rule"]["plan"])
    with pytest.raises(ValueError):
        D.target_keys(row, "short2")  # row finalized with another rule
    row["rule"], row["best"] = None, None  # not finalized: the requested rule's best set is used
    assert D.target_keys(row, "short2")[0] == set(row["best_by_rule"]["short2"])


def test_split_by_episode_flag_and_cal_test_rejected():
    assert D.split_of({"seed": 2000, "split": "fit"}) == "train"
    assert D.split_of({"seed": 2000, "split": "eval"}) == "val"
    for bad in ("dev", "cal", "test", None):
        with pytest.raises(ValueError):
            D.split_of({"seed": 0, "split": bad})


def test_build_items_matches_inference_prompt_and_maps_keys_to_shown_names():
    items = D.build_items([_line()], D.OutcomeLabels({"ep2000_k21": _rows()}, "plan"))
    assert [it["question"] for it in items] == ["dir_xy", "dir_z", "mag_coarse", "target", "phase"]  # no progress/fine
    from harvest.deccall_snap import build_snapshot_request
    req, _, _ = build_snapshot_request(_line())
    for it in items:
        q = req["questions"][it["qid"]]
        assert it["text"] == question_text(req["state"], it["qid"], q)  # byte-identical to jevl._body's text
        assert it["names"] == list(q["criteria"]) and it["names"][-1] == NE
        assert set(it["target"]) <= set(it["names"])
        assert it["split"] == "train" and it["image"] == "img/ep2000/k021_cam_head.jpg"
    by = {it["question"]: it for it in items}
    assert by["dir_xy"]["target"] == ["plus_x"] and by["target"]["target"] == ["o3"]
    assert not any(it["ne"] for it in items)


def test_build_items_ne_target_and_never_reads_oracle():
    line = _line()
    a = D.build_items([line], D.OutcomeLabels({"ep2000_k21": _rows(fail_all="phase")}, "plan"))
    line2 = copy.deepcopy(line)
    line2["oracle"] = {k: "garbage" for k in line["oracle"]}
    b = D.build_items([line2], D.OutcomeLabels({"ep2000_k21": _rows(fail_all="phase")}, "plan"))
    assert [(x["target"], x["ne"]) for x in a] == [(x["target"], x["ne"]) for x in b]
    ph = [x for x in a if x["question"] == "phase"][0]
    assert ph["target"] == [NE] and ph["ne"]


def test_build_items_skips_unlabelled_and_non_decision_and_checks_option_sets():
    nd = dict(_line(k=5), decision=False)
    assert D.build_items([nd, _line(k=7)], D.OutcomeLabels({"ep2000_k21": _rows()}, "plan")) == []
    rows = _rows()
    rows[0]["outcomes"].pop("plus_x")  # labelled option set != shown option set -> version drift
    with pytest.raises(ValueError):
        D.build_items([_line()], D.OutcomeLabels({"ep2000_k21": rows}, "plan"))


def test_build_items_state_representation_is_passed_through():
    line = _line()
    items = D.build_items([line], D.OutcomeLabels({"ep2000_k21": _rows()}, "plan"),
                          state_fn=lambda ln: ln["text_state"] + "\nX")
    assert items[0]["text"].startswith("t_state: f1\nrobot: x\nX\n")


def test_load_pool_reads_done_files_only_unless_partial(tmp_path):
    import json
    (tmp_path / "labels").mkdir()
    for seed, split, done in ((2000, "fit", True), (2007, "eval", False)):
        with open(tmp_path / f"ep{seed}.jsonl", "w") as f:
            f.write(json.dumps(_line(seed=seed, split=split)) + "\n")
        with open(tmp_path / "labels" / f"ep{seed}.jsonl", "w") as f:
            for r in _rows(seed=seed, split=split):
                f.write(json.dumps({**r, "best_by_rule": r["best_by_rule"]}) + "\n")
            if not done:
                f.write('{"key": "ep2007_k22", "quest')  # cut mid-line
        if done:
            (tmp_path / "labels" / f"ep{seed}.jsonl.done").write_text("{}")
    items = D.load_pool(str(tmp_path), "plan", state="S0")
    assert {it["split"] for it in items} == {"train"} and len(items) == 5
    items = D.load_pool(str(tmp_path), "plan", state="S0", partial=True)
    assert sorted({it["split"] for it in items}) == ["train", "val"] and len(items) == 10


def test_target_source_is_pluggable_and_never_sees_oracle():
    seen = []

    def observed(line, question, keys):
        seen.append((dict(line), question, list(keys)))
        if question == "dir_z":
            return {"down"}, False
        if question == "phase":
            return None  # unlabelled -> no item
        return {keys[-1]}, False

    items = D.build_items([_line()], D.FnSource(observed))
    assert [it["question"] for it in items] == ["dir_xy", "dir_z", "mag_coarse", "target"]
    by = {it["question"]: it for it in items}
    assert by["dir_z"]["target"] == ["down"] and by["target"]["target"] == ["o5"]
    assert all("oracle" not in ln for ln, _, _ in seen)
    from harvest.jevcall import DIR_XY
    assert seen[0][2] == [o.key for o in DIR_XY if o.key != NE]  # shown order, NONE_ESCALATE excluded


def test_source_returning_unknown_key_is_rejected():
    with pytest.raises(ValueError):
        D.build_items([_line()], D.FnSource(lambda ln, q, keys: ({"sideways"}, False)))


def test_build_snapshot_request_cannot_leak_oracle_into_prompt():
    line = _line()
    line["oracle"] = {k: "LEAK_" + v for k, v in line["oracle"].items()}
    items = D.build_items([line], D.OutcomeLabels({"ep2000_k21": _rows()}, "plan"))
    assert items and not any("LEAK_" in it["text"] for it in items)


def test_load_pool_with_plugged_source_factory(tmp_path):
    import json
    for seed, split in ((2000, "fit"), (2007, "eval")):
        with open(tmp_path / f"ep{seed}.jsonl", "w") as f:
            f.write(json.dumps(_line(seed=seed, split=split)) + "\n")

    def factory(pool_dir, seed):
        return None if seed == 2007 else D.FnSource(lambda ln, q, keys: ({keys[0]}, False))

    items = D.load_pool(str(tmp_path), state="S0", source_factory=factory)
    assert len(items) == 5 and {it["split"] for it in items} == {"train"}
    assert all(it["source"] == "fn" for it in items)


def _v2(seed=2000, kind="P0", k=21, **kw):
    lab = {"dir_xy": "minus_y", "dir_z": "up", "mag_coarse": "small", "target": "o5", "phase_choice": "next",
           "motion_phase": "carry", "progress": "valid_progress", "delta_m": [0, -0.02, 0.012], "goal_m": [0, 0, 0]}
    lab.update(kw)
    return {"seed": seed, "kind": kind, "k": k, "labels_v2": lab}


def test_labels_v2_source_maps_phase_choice_and_never_serves_progress():
    src = D.LabelsV2({(2000, "P0", 21): _v2()["labels_v2"]})
    items = D.build_items([_line()], src)
    by = {it["question"]: it for it in items}
    assert sorted(by) == ["dir_xy", "dir_z", "mag_coarse", "phase", "target"]
    assert by["dir_xy"]["target"] == ["minus_y"] and by["dir_z"]["target"] == ["up"]
    assert by["phase"]["target"] == ["next"] and by["target"]["target"] == ["o5"]
    assert all(it["source"] == "labels_v2" and not it["ne"] for it in items)
    assert src(_line(), "progress", ["valid_progress"]) is None  # progress in labels_v2 is the old oracle value


def test_labels_v2_unknown_answer_is_rejected():
    src = D.LabelsV2({(2000, "P0", 21): _v2(dir_xy="sideways")["labels_v2"]})
    with pytest.raises(ValueError):
        D.build_items([_line()], src)


def test_labels_v2_file_is_the_sibling_of_the_episode_folder(tmp_path):
    import json
    folder = tmp_path / "P0"
    folder.mkdir()
    ln = dict(_line(seed=3, split="dev"), kind="P0")
    (folder / "ep3.jsonl").write_text(json.dumps(ln) + "\n")
    (tmp_path / "P0.labels_v2.jsonl").write_text(json.dumps(_v2(seed=3)) + "\n")
    assert D.labels_v2_path(str(folder)) == str(tmp_path / "P0.labels_v2.jsonl")
    items = D.load_pool(str(folder), state="S0", source_factory=D.labels_v2_factory(), dev_val_seeds={3})
    assert len(items) == 5 and {it["split"] for it in items} == {"val"}
    with pytest.raises(ValueError):  # DEV episodes only with an explicit smoke split
        D.load_pool(str(folder), state="S0", source_factory=D.labels_v2_factory())


def test_split_dev_override_only_for_dev_never_cal_test():
    assert D.split_of({"seed": 5, "split": "dev"}, dev_val_seeds={5}) == "val"
    assert D.split_of({"seed": 6, "split": "dev"}, dev_val_seeds={5}) == "train"
    assert D.split_of({"seed": 2000, "split": "fit"}, dev_val_seeds={2000}) == "train"
    for bad in ("cal", "test"):
        with pytest.raises(ValueError):
            D.split_of({"seed": 5, "split": bad}, dev_val_seeds={5})


def test_s1_state_uses_step_cm(monkeypatch):
    import harvest.e3lite as E
    seen = {}

    def fake(line, S, step_cm=1):
        seen["args"] = (S, step_cm)
        return line["text_state"]

    monkeypatch.setattr(E, "state_text", fake)
    fn = D.state_fn("S1", 0.1)
    fn(_line())
    assert seen["args"] == ("S1", 0.1) and D.state_fn("S0", 0.1) is None
