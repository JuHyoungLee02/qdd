"""R7 cycle 7 fixes: the evaluation statistics follow the pre-registration (E-first §1.7, §2A.6-10, §3.4, EVAL §4.2)."""
import inspect
import json
import os

import pytest

from harvest.eval import closed, e05


# ------------------------------------------------------------------------------------------ E1: 10,000 draws
def test_bootstrap_defaults_are_the_preregistered_10000():
    from harvest import canary
    from harvest.eval import calib, rd
    from harvest.runtime import calibration as K
    libs = [(e05.mean_ci, "n"), (e05.diff_ci, "n"), (e05.block_diff_lo, "n"), (e05.analyze, "n_boot"),
            (rd.majority, "n_boot"), (rd.offline_rd, "n_boot"), (rd.drd, "n_boot"), (K.evaluate, "n_boot"),
            (closed.aggregate, "n_boot"), (canary.canary_compare, "n_boot")]
    for f, arg in libs:
        assert inspect.signature(f).parameters[arg].default == 10000, f.__qualname__
    assert e05._args(["--model", "m", "--out", "o", "--data", "d", "--split", "dev"]).n_boot == 10000
    assert rd._args(["--model", "m", "--out", "o", "--variants", "standard=x"]).n_boot == 10000
    assert calib._args(["--model", "m", "--out", "o", "--fit-data", "f", "--fit-split", "pool", "--heldout", "h",
                        "--heldout-split", "dev"]).n_boot == 10000
    assert closed._args(["--model", "m", "--out", "o"]).n_boot == 10000


def test_outputs_record_bootstrap_meta(dev_dirs, tmp_path, monkeypatch):
    from harvest.eval import calib, rd
    out = str(tmp_path / "e")
    e05.main(["--model", "mock", "--out", out, "--data", dev_dirs["P0"], "--split", "dev", "--blocks", "2",
              "--n-boot", "50"])
    b = json.load(open(os.path.join(out, "e05.json")))["meta"]["bootstrap"]
    assert b["n_boot"] == 50 and b["seed"] == 0 and b["level"] == 0.95 and "episode" in b["unit"]
    monkeypatch.setenv("HARVEST_QID_REGISTRY", str(tmp_path / "reg.json"))
    out = str(tmp_path / "c")
    calib.main(["--model", "mock", "--out", out, "--fit-data", dev_dirs["P0"], "--fit-split", "dev",
                "--heldout", dev_dirs["P1"], "--heldout-split", "dev", "--n-boot", "40"])
    assert json.load(open(os.path.join(out, "calib.json")))["meta"]["bootstrap"]["n_boot"] == 40
    out = str(tmp_path / "r")
    rd.main(["--model", "mock", "--out", out, "--variants", f"standard={dev_dirs['root']}", "--split", "dev",
             "--n-boot", "30"])
    assert json.load(open(os.path.join(out, "rd.json")))["meta"]["bootstrap"]["n_boot"] == 30


def test_closed_aggregate_and_canary_record_n_boot():
    from harvest.canary import canary_compare
    tr = [{"variant": "standard", "condition": "C5", "seed": s, "epoch": 0, "success": True, "sim_time": 1.0,
           "termination": "success", "summary": {}} for s in range(3)]
    b = closed.aggregate(tr, n_boot=30)["bootstrap"]
    assert b["n_boot"] == 30 and b["seed"] == 0 and "layout seed" in b["unit"]
    c = canary_compare({"q": ["a", "a"]}, {"q": ["a", "b"]}, floor=0.0, n_boot=30)
    assert c["n_boot"] == 30


# ------------------------------------------------------------------------------------------ N3: Holm step-down
def _stub_ci(pvals):
    """A CI at level L excludes 0 exactly when p <= 1 - L (the CI-inversion p-value)."""
    return lambda k, level: (0.1, 0.2) if pvals[k] <= 1 - level + 1e-12 else (-0.1, 0.2)


def test_holm_on_intervals_differs_from_bonferroni():
    from harvest.analysis.stats import holm, holm_ci
    p = {"a": 0.001, "b": 0.02, "c": 0.5}
    r = holm_ci(_stub_ci(p), list(p), alpha=0.05)
    # Holm: 0.001 <= 0.05/3, 0.02 <= 0.05/2, 0.5 > 0.05 -> a, b rejected; Bonferroni (0.05/3) would keep b
    assert {k: v["reject"] for k, v in r.items()} == {"a": True, "b": True, "c": False}
    assert {k: v for k, v in holm(p).items()} == {"a": True, "b": True, "c": False}
    assert not (p["b"] <= 0.05 / 3)  # the Bonferroni decision for b is different
    q = {"a": 0.03, "b": 0.04}
    assert not any(v["reject"] for v in holm_ci(_stub_ci(q), list(q)).values())  # step 1 fails -> stop


def test_e05_judgment10_reports_holm_per_block_pair():
    blocks = [{i: [0] * 10 for i in range(20)}, {i: [0] * 10 for i in range(20)},
              {i: [1] * 10 for i in range(20)}]
    r = e05.block_diff_holm(blocks, n=200)
    assert set(r["pairs"]) == {"0-1", "0-2", "1-2"}
    assert r["pairs"]["0-2"]["reject"] and r["pairs"]["1-2"]["reject"] and not r["pairs"]["0-1"]["reject"]
    assert r["any"] is True and (e05.block_diff_lo(blocks, n=200) > 0) is r["any"]


# ------------------------------------------------------------------------------------------ N4: equal-mass ECE
def test_ece_mass_hand_example():
    from harvest.analysis.stats import ece
    from harvest.runtime.calibration import ece_mass
    # sorted p: {0.1, 0.2} acc 0.5 conf 0.15 -> 0.35; {0.3, 0.9} acc 0.5 conf 0.6 -> 0.10; ECE = 0.225
    assert ece_mass([0.9, 0.1, 0.3, 0.2], [1, 0, 0, 1], bins=2) == pytest.approx(0.225)
    assert ece([0.9, 0.1, 0.3, 0.2], [1, 0, 0, 1], bins=2) == pytest.approx(0.125)  # equal width differs
    assert inspect.signature(ece_mass).parameters["bins"].default == 15


def _ev(width, mass, mass_hi):
    return {"ece_cal": width, "ece_cal_mass": mass, "ece_cal_mass_ci": [0.0, mass_hi],
            "auroc_cal": {"mean": 0.8, "ci": [0.72, 0.86]}, "wrong": 40,
            "theta": {"0.8": {"acc": {"mean": 0.85, "ci": [0.8, 0.9]}, "coverage": 0.4}}, "j5": {}}


def test_e1_judgment1_uses_equal_mass_ece():
    from harvest.runtime.calibration import judge_question
    assert judge_question(_ev(width=0.02, mass=0.07, mass_hi=0.09), 400, (0.8,))["ece_ok"] is False
    j = judge_question(_ev(width=0.07, mass=0.03, mass_hi=0.06), 400, (0.8,))
    assert j["ece_ok"] is True and j["theta_gate"]["0.8"] is True


def test_evaluate_bootstraps_the_equal_mass_ece():
    from harvest.runtime import calibration as K
    items = [{"cluster": (i % 7,), "probs": {"a": 0.5 + 0.4 * (i % 5) / 4, "b": 0.5 - 0.4 * (i % 5) / 4},
              "truth": {"a" if i % 3 else "b"}, "key": "a"} for i in range(60)]
    qc = {"T_used": 1.0, "j5": {}}
    ev = K.evaluate(items, qc, alphas=(), thetas=(), n_boot=50)
    lo, hi = ev["ece_cal_mass_ci"]
    assert lo <= ev["ece_cal_mass"] <= hi


def test_fit_question_raw_ece_is_equal_mass():
    from harvest.runtime import calibration as K
    fit = [{"probs": {"a": p, "b": 1 - p}, "truth": {t}, "key": "a"}
           for p, t in [(0.9, "a"), (0.6, "b"), (0.7, "a"), (0.55, "a")] * 5]
    qc = K.fit_question(fit, fit, alphas=(0.1,))
    raw = [max(x["probs"].values()) for x in fit]
    ok = [x["key"] in x["truth"] for x in fit]
    assert qc["fit_raw_ece"] == pytest.approx(round(K.ece_mass(raw, ok), 5))


# ------------------------------------------------------------------------------------------ N5: RD cluster unit
def _tr(variant, seed, epoch, ok):
    return {"variant": variant, "condition": "C5", "seed": seed, "epoch": epoch, "success": ok, "sim_time": 1.0,
            "termination": "x", "summary": {}}


def test_closed_rd_ci_resamples_layout_seeds_not_seed_epoch_pairs():
    tr = [_tr("standard", s, e, True) for s in (0, 1) for e in range(3)]
    tr += [_tr("random", 0, e, True) for e in range(3)] + [_tr("random", 1, e, False) for e in range(3)]
    rd = closed.aggregate(tr, n_boot=2000)["rd"]["C5/random"]
    assert rd["rd"] == pytest.approx(0.5)
    # seed clusters: a draw is {0,0} -> 0, {1,1} -> 1, {0,1} -> 0.5, so the 95% interval is [0, 1];
    # resampling the 6 (seed, epoch) pairs instead puts the lower bound at 1/6
    assert rd["rd_ci"] == [0.0, 1.0]
    assert rd["n_seeds"] == 2 and rd["n_pairs"] == 6


# ------------------------------------------------------------------------------------------ N7: fused prompt config
def test_fused_run_records_the_checkpoint_prompt_config():
    pc = {"camera": ["HW:cam_head|cam_wrist_left|cam_wrist_right"], "state": "IMG", "sha": "abc123"}
    got = closed.run_prompt_config("stageb", pc, "HW")
    assert got["sha"] == "abc123" and got["state"] == "IMG" and "checkpoint" in got["source"]
    mod = closed.run_prompt_config("jevl", None, "H")
    assert mod["state"] == "S1" and mod["camera"] == "H"
