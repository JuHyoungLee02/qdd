"""E-NOV0 verdict (docs/stage3/prereg_nov0.md §5-§6): rule boundaries, input checks, metrics on planted data."""
import importlib.util
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools", "nov0"))


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, *rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


V = _load("nov0_verdict", ("tools", "nov0", "nov0_verdict.py"))
L = _load("nov0_lib_v", ("tools", "nov0", "nov0_lib.py"))

PASS = {"err_auroc": 0.80, "reduction90": 0.40, "xfit_recall": 0.90, "lat_gpu_p95_ms": 1.0,
        "dr_auroc": 0.90, "task_auroc_mean": 0.90, "fa95": 0.05, "real_auroc": 1.0}


# ------------------------------------------------------------------------------------------ rules
def test_rules_all_pass_is_gate_plus_nov():
    assert V.rules(PASS)["verdict"] == "GATE+NOV"


@pytest.mark.parametrize("key,val,expect", [
    ("err_auroc", 0.75, "GATE+NOV"), ("err_auroc", 0.7499, "NOV"),
    ("reduction90", 0.30, "GATE+NOV"), ("reduction90", 0.2999, "NOV"),
    ("xfit_recall", 0.85, "GATE+NOV"), ("xfit_recall", 0.8499, "NOV"),
    ("lat_gpu_p95_ms", 5.0, "GATE+NOV"), ("lat_gpu_p95_ms", 5.01, "NOV"),
    ("dr_auroc", 0.80, "GATE+NOV"), ("dr_auroc", 0.7999, "GATE"),
    ("task_auroc_mean", 0.7999, "GATE"), ("fa95", 0.07, "GATE+NOV"), ("fa95", 0.0701, "GATE"),
])
def test_rules_boundaries(key, val, expect):
    assert V.rules({**PASS, key: val})["verdict"] == expect


def test_rules_none_and_sanity_hold():
    bad = {**PASS, "err_auroc": 0.6, "dr_auroc": 0.6}
    assert V.rules(bad)["verdict"] == "NONE"
    assert V.rules({**PASS, "real_auroc": 0.89})["verdict"] == "HOLD_G5"


def test_rules_exact_threshold_uses_cmp_eps():
    assert V.rules({**PASS, "err_auroc": 0.3 + 0.45})["r1"]  # 0.75 up to float noise


# ------------------------------------------------------------------------------------------ planted data
def _meta(sid, s, part, mse=None, wrong=False):
    d = L.parse_id(sid)
    m = {"id": sid, "set": s, **d, "part": part,
         "correct": {"dir_xy": not wrong, "dir_z": True, "mag_coarse": True, "target": True, "phase_id": True},
         "margin": {"dir_xy": 0.1 if wrong else 3.0, "dir_z": 3.0, "mag_coarse": 3.0, "target": 5.0, "phase_id": 5.0}}
    if mse is not None:
        m["mse"] = mse
    return m


def _planted(seed=0, D=8):
    """mem / cal / eval over 2 variants x 3 tasks; dr and each task shift the features; eval errors sit where the
    feature is far from memory; se2e is far away."""
    rng = np.random.default_rng(seed)
    tasks = ("bottle_tray", "mug_marker", "mug_tray")
    shift = {("standard", t): np.eye(D)[i] * 4 for i, t in enumerate(tasks)}
    shift.update({("dr", t): np.eye(D)[i] * 4 + np.eye(D)[5] * 4 for i, t in enumerate(tasks)})
    data = {s: {"ids": [], "f": [], "meta": []} for s in ("mem", "cal", "eval", "se2e")}
    for (v, t), mu in shift.items():
        for s, n, seeds in (("mem", 60, [x for x in range(10001, 10080) if x % 20][:60]),
                            ("cal", 20, range(20001, 20021)), ("eval", 40, range(10000, 10800, 20))):
            for j, sd in enumerate(seeds):
                for k in (0, 10):
                    sid = f"{v}/{t}/P0/ep{sd}/k{k}"
                    x = mu + rng.normal(size=D) * 0.5
                    wrong = False
                    mse = float(rng.random())
                    if s == "eval" and j % 4 == 0:  # an unusual state -> far from memory, and an error
                        x = x + np.eye(D)[7] * 3
                        wrong = True
                    data[s]["ids"].append(sid)
                    data[s]["f"].append(x)
                    data[s]["meta"].append(_meta(sid, s, "eval" if s == "eval" else s, mse if s == "eval" else None,
                                                 wrong))
    for i in range(30):
        data["se2e"]["ids"].append(f"RB1_ep{i}_k0")
        data["se2e"]["f"].append(np.eye(D)[6] * 10 + rng.normal(size=D))
        data["se2e"]["meta"].append({"id": f"RB1_ep{i}_k0", "set": "se2e", "ep": f"RB1_ep{i}"})
    for s in data:
        F = np.stack(data[s]["f"])
        data[s]["feat"] = {"dec": F, "mean": F * 2, "vis": F[:, ::-1].copy()}
        del data[s]["f"]
    return data


def test_compute_on_planted_data_detects_shifts_and_errors():
    data = _planted()
    out = V.compute(data, boot_primary=50, boot_secondary=20, seed=0)
    p = out["features"][V.PRIMARY]
    assert p["shift_dr"]["auroc"] > 0.9
    assert p["shift_task"]["mean"] > 0.9 and len(p["shift_task"]["per_task"]) == 3
    assert p["shift_real"]["auroc"] > 0.99
    assert p["err"]["auroc_large"] > 0.8
    assert 0 < p["err"]["op90"]["call"] < 1 and p["err"]["op90"]["recall"] >= 0.9
    assert [r["q"] for r in p["err"]["fixed"]] == list(V.FIXED_Q)
    assert set(out["features"]) == set(V.VARIANTS)
    assert "auroc_large" in out["baseline_margin"]
    assert out["n"]["eval"] == len(data["eval"]["ids"])


def test_check_inputs_rejects_duplicates_and_seed_overlap():
    data = _planted()
    V.check_inputs(data, expect={"eval": len(data["eval"]["ids"])})
    with pytest.raises(SystemExit):
        V.check_inputs(data, expect={"eval": 5})
    d2 = _planted()
    d2["cal"]["ids"][0] = d2["mem"]["ids"][0]
    d2["cal"]["meta"][0] = dict(d2["mem"]["meta"][0])
    with pytest.raises(SystemExit):
        V.check_inputs(d2, expect={})
    d3 = _planted()
    d3["eval"]["feat"]["dec"][0, 0] = np.nan
    with pytest.raises(SystemExit):
        V.check_inputs(d3, expect={})
