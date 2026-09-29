"""tools/se2e/se2e_verdict.py (S-E2E pre-registered criteria, docs/stage3/prereg_se2e.md): float-boundary "<=" and the
criterion (a) rc check (R7 cycle 13 N3); input checks (R7 cycle 14 N1): (e) compares exactly steps mid+1..mid+50,
(b) "first" / "last 3" are exactly the pre-registered eval steps (every 500 + final: 0 and 4000, 4500, 4686), and the
drivers folder (criterion (a) rc 0) is mandatory."""
import json
import os
import subprocess
import sys

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "tools", "se2e", "se2e_verdict.py")
TOTAL, MID = 4686, 2000  # prereg_se2e.md §3


def _schedule(total=TOTAL):
    return list(range(0, total, 500)) + [total]


def _run_dir(root, name, dec_last, evs=None, resume=None):
    d = os.path.join(root, name)
    os.makedirs(os.path.join(d, "last"))
    open(os.path.join(d, "last", "heads.pt"), "w").close()
    rows = [{"event": "train", "step": s, "fm": 1.0, "dec": 1.0, "total": 2.0, "grad_norm": 1.0, "lr_heads": 1e-4,
             "idx": [s]} for s in range(1, TOTAL + 1)]
    if evs is None:
        sch = _schedule()
        evs = [(s, 1.0 if s == 0 else 0.9) for s in sch[:-3]] + list(zip(sch[-3:], dec_last))
    rows += [{"event": "eval", "step": s, "dec": v, "fm": 1.0 * v, "sample_mse_norm": v} for s, v in evs]
    rows += [{"event": "ckpt", "step": TOTAL}, {"event": "save_load", "max_abs_action_diff": 0.0, "eval_equal": True}]
    with open(os.path.join(d, "log.jsonl"), "w") as f:
        f.write("\n".join(json.dumps(r) for r in rows) + "\n")
    with open(os.path.join(d, "evalck.jsonl"), "w") as f:
        f.write(json.dumps({"step": MID, "equal": True, "max_abs_diff": 0.0}) + "\n")
    rd = os.path.join(root, name + "_resume")
    os.makedirs(rd)
    lo, hi = resume or (MID + 1, MID + 50)
    with open(os.path.join(rd, "log.jsonl"), "w") as f:
        f.write("\n".join(json.dumps(r) for r in rows if r["event"] == "train" and lo <= r["step"] <= hi) + "\n")


def _drivers(tmp_path, b_evalck_rc=0):
    drv = tmp_path / "drv"
    drv.mkdir()
    (drv / "driver_A.out").write_text("main rc=0\nevalck rc=0\nresume rc=0\n")
    (drv / "driver_B.out").write_text(f"main rc=0\nevalck rc={b_evalck_rc}\nresume rc=0\n")
    return str(drv)


def _call(tmp_path, drivers):
    args = [sys.executable, SCRIPT, str(tmp_path), "A", "B", str(TOTAL), str(MID)] + ([drivers] if drivers else [])
    return subprocess.run(args, capture_output=True, text=True)


def _verdict(tmp_path, dec_last=(0.5, 0.5, 0.5), b_evalck_rc=0, evs=None, resume=None):
    _run_dir(str(tmp_path), "A", dec_last, evs, resume)
    _run_dir(str(tmp_path), "B", dec_last)
    p = _call(tmp_path, _drivers(tmp_path, b_evalck_rc))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


def test_well_formed_logs_pass(tmp_path):
    out = _verdict(tmp_path)
    a = out["runs"][0]
    assert out["d_both_seeds_abc"] is True and out["e_resume"] == ["bit", "bit"]
    assert a["b"]["last3_steps"] == [4000, 4500, 4686] and a["b"]["steps_ok"] is True
    assert a["e"]["steps"] == [2001, 2050] and a["e"]["window_ok"] is True


def test_threshold_equal_up_to_float_rounding_passes(tmp_path):
    # last-3 mean 0.65, 0.65, 0.80 -> 0.7000000000000001 in float; pre-registered "<= 0.70 x step 0" must pass
    out = _verdict(tmp_path, (0.65, 0.65, 0.80))
    assert sum((0.65, 0.65, 0.80)) / 3 > 0.70
    assert out["runs"][0]["b"]["b1"] is True


def test_rc_lines_are_checked(tmp_path):
    out = _verdict(tmp_path, b_evalck_rc=1)
    assert out["runs"][0]["a"]["pass"] is True
    assert out["runs"][1]["a"]["rc_all_zero"] is False and out["runs"][1]["a"]["pass"] is False


def test_drivers_dir_is_mandatory(tmp_path):
    _run_dir(str(tmp_path), "A", (0.5, 0.5, 0.5))
    _run_dir(str(tmp_path), "B", (0.5, 0.5, 0.5))
    p = _call(tmp_path, None)
    assert p.returncode != 0 and "drivers" in p.stderr and not p.stdout.strip()
    p = _call(tmp_path, str(tmp_path / "no_such_drv"))
    assert p.returncode != 0 and "drivers" in p.stderr and not p.stdout.strip()


def test_resume_window_must_be_mid_plus_1_to_mid_plus_50(tmp_path):
    # 50 steps identical to the original run, but not the pre-registered window 2001-2050
    out = _verdict(tmp_path, resume=(1, 50))
    e = out["runs"][0]["e"]
    assert e["n"] == 50 and e["bit_identical_all"] is True
    assert e["window_ok"] is False and e["grade"] == "fail" and e["pass"] is False
    assert out["e_resume"] == ["fail", "bit"]


def test_resume_window_later_than_mid_fails(tmp_path, ):
    out = _verdict(tmp_path, resume=(3001, 3050))
    assert out["runs"][0]["e"]["window_ok"] is False and out["runs"][0]["e"]["grade"] == "fail"


def test_last3_missing_4500_eval_fails_b(tmp_path):
    sch = [s for s in _schedule() if s != 4500]
    out = _verdict(tmp_path, evs=[(s, 1.0 if s == 0 else 0.5) for s in sch])
    b = out["runs"][0]["b"]
    assert b["last3_steps"] == [3500, 4000, 4686] and b["b1"] is True
    assert b["steps_ok"] is False and b["pass"] is False and out["d_both_seeds_abc"] is False


def test_last3_duplicated_final_eval_fails_b(tmp_path):
    sch = _schedule() + [TOTAL]
    out = _verdict(tmp_path, evs=[(s, 1.0 if s == 0 else 0.5) for s in sch])
    b = out["runs"][0]["b"]
    assert b["last3_steps"] == [4500, 4686, 4686] and b["steps_ok"] is False and b["pass"] is False


def test_first_eval_must_be_step_0(tmp_path):
    sch = _schedule()[1:]
    out = _verdict(tmp_path, evs=[(s, 1.0 if s == 500 else 0.5) for s in sch])
    assert out["runs"][0]["b"]["steps_ok"] is False and out["runs"][0]["b"]["pass"] is False
