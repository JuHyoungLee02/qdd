"""tools/se2e/se2e_verdict.py (S-E2E pre-registered criteria, docs/stage3/prereg_se2e.md): float-boundary "<=" and the
criterion (a) rc check (R7 cycle 13 N3)."""
import json
import os
import subprocess
import sys

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "tools", "se2e", "se2e_verdict.py")
TOTAL, MID = 10, 4


def _run_dir(root, name, dec_last):
    d = os.path.join(root, name)
    os.makedirs(os.path.join(d, "last"))
    open(os.path.join(d, "last", "heads.pt"), "w").close()
    rows = [{"event": "train", "step": s, "fm": 1.0, "dec": 1.0, "total": 2.0, "grad_norm": 1.0, "lr_heads": 1e-4,
             "idx": [s]} for s in range(1, TOTAL + 1)]
    evs = [(0, 1.0), (5, 0.9), (8, dec_last[0]), (9, dec_last[1]), (TOTAL, dec_last[2])]
    rows += [{"event": "eval", "step": s, "dec": v, "fm": 1.0 * v, "sample_mse_norm": v} for s, v in evs]
    rows += [{"event": "ckpt", "step": TOTAL}, {"event": "save_load", "max_abs_action_diff": 0.0, "eval_equal": True}]
    with open(os.path.join(d, "log.jsonl"), "w") as f:
        f.write("\n".join(json.dumps(r) for r in rows) + "\n")
    with open(os.path.join(d, "evalck.jsonl"), "w") as f:
        f.write(json.dumps({"step": MID, "equal": True, "max_abs_diff": 0.0}) + "\n")
    rd = os.path.join(root, name + "_resume")
    os.makedirs(rd)
    with open(os.path.join(rd, "log.jsonl"), "w") as f:
        f.write("\n".join(json.dumps(r) for r in rows if r["event"] == "train" and MID < r["step"]) + "\n")


def _verdict(tmp_path, dec_last, drivers=None):
    root = str(tmp_path)
    _run_dir(root, "A", dec_last)
    _run_dir(root, "B", dec_last)
    args = [sys.executable, SCRIPT, root, "A", "B", str(TOTAL), str(MID)] + ([drivers] if drivers else [])
    return json.loads(subprocess.run(args, capture_output=True, text=True, check=True).stdout)


def test_threshold_equal_up_to_float_rounding_passes(tmp_path):
    # last-3 mean 0.65, 0.65, 0.80 -> 0.7000000000000001 in float; pre-registered "<= 0.70 x step 0" must pass
    out = _verdict(tmp_path, (0.65, 0.65, 0.80))
    assert sum((0.65, 0.65, 0.80)) / 3 > 0.70
    assert out["runs"][0]["b"]["b1"] is True


def test_rc_lines_are_checked_when_drivers_dir_given(tmp_path):
    drv = tmp_path / "drv"
    drv.mkdir()
    (drv / "driver_A.out").write_text("main rc=0\nevalck rc=0\nresume rc=0\n")
    (drv / "driver_B.out").write_text("main rc=0\nevalck rc=1\nresume rc=0\n")
    out = _verdict(tmp_path, (0.5, 0.5, 0.5), str(drv))
    assert out["runs"][0]["a"]["pass"] is True
    assert out["runs"][1]["a"]["rc_all_zero"] is False and out["runs"][1]["a"]["pass"] is False
