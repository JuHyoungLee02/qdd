"""R7 cycle 14 D1 (canon §78 (1), §80): an outcome label row is trusted only if its replay was bit-identical
(`replay_maxabs == 0`); a row without the field (or null / NaN) carries no evidence and is untrusted. Every reader of
the labeler's rows -- `--truth outcome:<rule>` (e05 / rd / calib via common.load_truth), stage-A OutcomeLabels
(stagea_data.outcome_factory) and the labels_v2 self-check comparison -- drops the others and reports how many."""
import importlib.util
import json
import os

import pytest

from harvest.eval import calib, common, e05, rd
from harvest.sim import labeler as L
from harvest.sim.snapshot import PHASE_ORDER
from harvest.train import stagea_data as D


def _out(dist):
    cps = {f"{h:g}": {"phase": "carry", "dist_m": dist, "d_start": 0.2} for h in L.CHECKPOINTS_S}
    return {"success": False, "fail": False, "t_success": None, "t_fail": None, "phase": "carry", "dist_m": dist,
            "checkpoints": cps, "sim_s": 1.0, "fail_stage": None}


def _row(q, seed, k, maxabs, kind="P0", best_first=True, split="fit"):
    """A cli_label row whose unique best (rule plan) is the first option key (or the last one)."""
    keys = L.option_keys(q, ("o3", "o5"))
    outs = {kk: _out(0.05 + 0.01 * i) for i, kk in enumerate(keys if best_first else keys[::-1])}
    by_rule = {ru: sorted(L.rule_best(outs, ru, PHASE_ORDER)) for ru in L.RULES}
    r = {"key": f"ep{seed}_k{k}", "question": q, "rule": "plan", "best": by_rule["plan"], "best_by_rule": by_rule,
         "outcomes": outs, "seed": seed, "k": k, "kind": kind, "split": split}
    if maxabs != "missing":
        r["replay_maxabs"] = maxabs
    return r


def _write(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


@pytest.mark.parametrize("v,ok", [(0.0, True), (0, True), (0.37, False), (1e-300, False), (None, False),
                                  ("missing", False), (float("nan"), False)])
def test_replay_bit_identical(v, ok):
    r = _row("dir_z", 2027, 3, v)
    assert D.replay_bit_identical(r) is ok


def test_load_truth_outcome_drops_rows_whose_replay_was_not_bit_identical(tmp_path):
    lab = tmp_path / "labels"
    lab.mkdir()
    _write(lab / "ep2027.jsonl", [_row("dir_z", 2027, 3, 0.0), _row("dir_z", 2027, 4, 0.37),
                                  _row("target", 2027, 4, 0.0), _row("target", 2027, 5, "missing")])
    eps = [{"kind": "P0", "seed": 2027}]
    stats = {}
    t = common.load_truth(eps, "outcome:plan", [str(lab)], stats=stats)
    assert ("P0", 2027, 3) in t and "dir_z" in t[("P0", 2027, 3)]
    assert "dir_z" not in t.get(("P0", 2027, 4), {})  # replay_maxabs 0.37: not a truth
    assert t[("P0", 2027, 4)] == {"target": {L.option_keys("target", ("o3", "o5"))[0]}}  # same snapshot, bit-exact
    assert ("P0", 2027, 5) not in t  # no replay evidence
    assert stats == {"rule": "plan", "rows_kept": 2, "rows_excluded_replay_not_bit_identical": 2}


def test_load_truth_stats_accumulate_and_labels_v2_is_untouched(tmp_path, dev_dirs):
    lab = tmp_path / "labels"
    lab.mkdir()
    _write(lab / "a.jsonl", [_row("dir_z", 1, 0, 0.0, kind="P1"), _row("dir_z", 2, 0, 0.5, kind="P1")])
    stats = {}
    common.load_truth([{"kind": "P1", "seed": 1}], "outcome:plan", [str(lab)], stats=stats)
    common.load_truth([{"kind": "P1", "seed": 2}], "outcome:plan", [str(lab)], stats=stats)
    assert stats["rows_kept"] == 1 and stats["rows_excluded_replay_not_bit_identical"] == 1
    eps = common.load_episodes([dev_dirs["P0"]], "dev")
    s2 = {}
    assert common.load_truth(eps, "labels_v2", stats=s2) and s2 == {}


def _dev_outcome_rows(d, eps, bad_seed):
    rows = []
    for e in eps:
        for ln in e["lines"]:
            if ln["decision"]:
                for q in common.QUESTIONS:
                    rows.append(_row(q, e["seed"], ln["k"], 0.37 if e["seed"] == bad_seed else 0.0, kind=e["kind"],
                                     split="dev"))
    _write(os.path.join(d, "dev_P0.jsonl"), rows)
    return sum(1 for r in rows if r["replay_maxabs"] > 0), len(rows)


def test_e05_outcome_truth_excludes_untrusted_rows_and_reports_the_count(dev_dirs, tmp_path, monkeypatch):
    monkeypatch.setenv("HARVEST_QID_REGISTRY", str(tmp_path / "qid.json"))
    od = tmp_path / "sc"
    od.mkdir()
    bad, n = _dev_outcome_rows(str(od), common.load_episodes([dev_dirs["P0"]], "dev"), bad_seed=1)
    out = str(tmp_path / "o")
    e05.main(["--model", "mock", "--out", out, "--data", dev_dirs["P0"], "--split", "dev", "--n-boot", "50",
              "--truth", "outcome:plan", "--outcome-dirs", str(od)])
    meta = json.load(open(os.path.join(out, "e05.json"), encoding="utf-8"))["meta"]
    assert bad > 0 and meta["truth_label_trust"] == {"rule": "plan", "rows_kept": n - bad,
                                                     "rows_excluded_replay_not_bit_identical": bad}


def test_rd_and_calib_report_the_excluded_count(dev_dirs, tmp_path, monkeypatch):
    monkeypatch.setenv("HARVEST_QID_REGISTRY", str(tmp_path / "qid.json"))
    od = tmp_path / "sc"
    od.mkdir()
    eps = common.load_episodes([dev_dirs["P0"]], "dev")
    bad, n = _dev_outcome_rows(str(od), eps, bad_seed=2)
    out = str(tmp_path / "rd")
    rd.main(["--model", "mock", "--out", out, "--variants", f"standard={dev_dirs['P0']}", "--split", "dev",
             "--n-boot", "50", "--truth", "outcome:plan", "--outcome-dirs", str(od)])
    meta = json.load(open(os.path.join(out, "rd.json"), encoding="utf-8"))["meta"]
    assert meta["truth_label_trust"] == {"standard": {"rule": "plan", "rows_kept": n - bad,
                                                      "rows_excluded_replay_not_bit_identical": bad}}
    out = str(tmp_path / "cal")
    calib.main(["--model", "mock", "--out", out, "--fit-data", dev_dirs["P0"], "--fit-split", "dev",
                "--heldout", dev_dirs["P1"], "--heldout-split", "dev", "--n-boot", "50",
                "--truth", "outcome:plan", "--outcome-dirs", str(od)])
    meta = json.load(open(os.path.join(out, "calib.json"), encoding="utf-8"))["meta"]
    assert meta["truth_label_trust"] == {"rule": "plan", "rows_kept": n - bad,
                                         "rows_excluded_replay_not_bit_identical": bad}


# ------------------------------------------------------------------------------------------ stage A
def _line(seed, k):
    return {"seed": seed, "kind": "P0", "split": "fit", "k": k, "ds_id": f"ds{k}", "phase": "carry",
            "decision": True, "text_state": "t_state: f1\nrobot: x", "state": {"present": ["o3", "o5"]},
            "images": {"cam_head": f"img/ep{seed}/k{k:03d}_cam_head.jpg"}, "oracle": {"dir_xy": "SECRET"}}


def _snapshot_rows(seed, k, bad_q=()):
    return [_row(q, seed, k, 0.37 if q in bad_q else 0.0) for q in D.QUESTIONS]


def test_stagea_outcome_labels_drop_untrusted_rows():
    src = D.OutcomeLabels({"ep2027_k3": _snapshot_rows(2027, 3, bad_q=("dir_z",))}, "plan")
    items = D.build_items([_line(2027, 3)], src)
    assert sorted(it["question"] for it in items) == sorted(q for q in D.QUESTIONS if q != "dir_z")
    assert src.n_excluded == 1 and src.n_kept == len(D.QUESTIONS) - 1


def test_stagea_load_pool_reports_excluded_rows(tmp_path):
    (tmp_path / "labels").mkdir()
    for seed, bad in ((2027, ("dir_z", "target")), (2028, ())):
        _write(tmp_path / f"ep{seed}.jsonl", [_line(seed, 3)])
        _write(tmp_path / "labels" / f"ep{seed}.jsonl", _snapshot_rows(seed, 3, bad_q=bad))
        (tmp_path / "labels" / f"ep{seed}.jsonl.done").write_text("{}")
    stats = {}
    items = D.load_pool(str(tmp_path), state="S0", source_factory=D.outcome_factory("plan", stats=stats))
    assert len(items) == 2 * len(D.QUESTIONS) - 2
    assert not any(it["seed"] == 2027 and it["question"] in ("dir_z", "target") for it in items)
    assert stats == {"rule": "plan", "rows_kept": 2 * len(D.QUESTIONS) - 2, "rows_excluded_replay_not_bit_identical": 2}


def test_stagea_partial_file_completeness_is_judged_before_the_trust_filter(tmp_path):
    (tmp_path / "labels").mkdir()
    _write(tmp_path / "ep2027.jsonl", [_line(2027, 3)])
    _write(tmp_path / "labels" / "ep2027.jsonl", _snapshot_rows(2027, 3, bad_q=("phase",)))
    items = D.load_pool(str(tmp_path), "plan", state="S0", partial=True)
    assert len(items) == len(D.QUESTIONS) - 1


def test_stagea_train_records_the_excluded_count(tmp_path):
    from types import SimpleNamespace

    from harvest.train import stagea_train as T
    (tmp_path / "labels").mkdir()
    _write(tmp_path / "ep2027.jsonl", [_line(2027, 3)])
    _write(tmp_path / "labels" / "ep2027.jsonl", _snapshot_rows(2027, 3, bad_q=("dir_xy",)))
    (tmp_path / "labels" / "ep2027.jsonl.done").write_text("{}")
    a = SimpleNamespace(dev_val_seeds="", pool=str(tmp_path), state="S0", partial=False, step_cm=0.1,
                        target_source="outcome", rule="plan", labels_v2="", cameras="H")
    stats = {}
    items = T._items(a, stats)
    assert len(items) == len(D.QUESTIONS) - 1
    assert stats == {"rule": "plan", "rows_kept": len(D.QUESTIONS) - 1, "rows_excluded_replay_not_bit_identical": 1}


# ------------------------------------------------------------------------------------------ labels_v2 self-check
def test_labels_v2_selfcheck_reader_drops_untrusted_rows(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "labels_v2_eval", os.path.join(os.path.dirname(__file__), "..", "..", "tools", "labels_v2_eval.py"))
    E = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(E)
    _write(tmp_path / "dev0_P0.jsonl", [_row("dir_z", 0, 3, 0.0), _row("dir_z", 0, 6, 0.37)])
    with open(tmp_path / "dev0_P0.jsonl", "a", encoding="utf-8") as f:
        f.write('{"key": "ep0_k9", "quest')  # a file still being written
    rows, n_bad = E.selfcheck_rows(str(tmp_path))
    assert [r["k"] for r in rows] == [3] and n_bad == 1
