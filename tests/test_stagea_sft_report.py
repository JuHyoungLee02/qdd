import importlib.util
import json
import os

spec = importlib.util.spec_from_file_location(
    "stagea_sft_report", os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools", "stagea_sft_report.py"))
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)


def _row(snap, q, key, oracle="x", p=0.9, kind="P0", seed=0):
    return {"snap": snap, "question": q, "qid": f"ds0.{q}", "key": key, "oracle": oracle, "p_chosen": p,
            "probs": {key or "a": p, "NONE_ESCALATE": 0.01}, "kind": kind, "seed": seed, "error": None}


def test_items_rescore_against_labels_v2_not_old_oracle():
    labels = {"P0_s0_k1": {"dir_xy": "plus_x", "phase_choice": "next"}}
    rows = [_row("P0_s0_k1", "dir_xy", "plus_x", oracle="minus_y"), _row("P0_s0_k1", "phase", "continue",
                                                                         oracle="continue"),
            _row("P0_s0_k1", "progress", "valid_progress")]
    it = R.items(rows, labels)
    assert set(it) == {("P0_s0_k1", "dir_xy"), ("P0_s0_k1", "phase")}
    assert it[("P0_s0_k1", "dir_xy")]["correct"] and not it[("P0_s0_k1", "phase")]["correct"]
    ne = R.items([_row("P0_s0_k1", "dir_xy", "NONE_ESCALATE")], labels)
    assert not ne[("P0_s0_k1", "dir_xy")]["correct"]


def test_main_end_to_end(tmp_path, monkeypatch):
    dev = tmp_path / "dev"
    dev.mkdir()
    zr, sr = [], []
    for kind in ("P0", "P1", "P2"):
        with open(dev / f"{kind}.labels_v2.jsonl", "w") as f:
            for seed in range(3):
                lab = {"dir_xy": "plus_x", "dir_z": "up", "mag_coarse": "large", "target": "o3",
                       "phase_choice": "continue"}
                f.write(json.dumps({"seed": seed, "kind": kind, "k": 0, "labels_v2": lab}) + "\n")
                snap = f"{kind}_s{seed}_k0"
                for q, y in (("dir_xy", "plus_x"), ("dir_z", "up"), ("mag_coarse", "large"), ("target", "o3"),
                             ("phase", "continue")):
                    zr.append({**_row(snap, q, "wrong", kind=kind, seed=seed), "model": "base"})
                    sr.append({**_row(snap, q, y, kind=kind, seed=seed), "model": "sft"})
                zr.append({**_row(snap, "progress", "valid_progress", kind=kind, seed=seed), "model": "base"})
                sr.append({**_row(snap, "progress", "valid_progress", kind=kind, seed=seed), "model": "sft"})
    for name, rows in (("z", zr), ("s", sr)):
        with open(tmp_path / f"{name}.jsonl", "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in rows)
    out = tmp_path / "o.json"
    monkeypatch.setattr("sys.argv", ["x", "--dev", str(dev), "--zero", str(tmp_path / "z.jsonl"), "--sft",
                                     str(tmp_path / "s.jsonl"), "--out", str(out)])
    R.main()
    res = json.load(open(out))
    assert res["n_items"] == 45 and res["pooled"]["sft"]["mean"] == 1.0 and res["pooled"]["zero"]["mean"] == 0.0
    assert res["pooled"]["majority"]["mean"] == 1.0 and res["criteria"]["a_sft_minus_zero_lower_gt_0"]
    assert not res["criteria"]["b_sft_minus_majority_lower_gt_0"] and res["criteria"]["d_questions_below_majority"] == []
    assert res["progress_drift"]["argmax_agree_zero_sft"] == 1.0
