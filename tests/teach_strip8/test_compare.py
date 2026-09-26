"""E-STRIP8 paired comparison (prereg_strip8.md §4-5): snapshot-paired bootstrap of the per-snapshot difference,
pairs only where both arms have a value (the count of unpaired snapshots is reported), deterministic, and the
registered verdict rules at their boundaries."""
import numpy as np

from harvest.teach_strip8 import compare as C


def test_paired_bootstrap_ci_and_pairing():
    a = {f"s{i}": {"approach_3d_mm": 10.0 + i % 3} for i in range(200)}
    b = {f"s{i}": {"approach_3d_mm": 5.0 + i % 3} for i in range(200)}
    b["s0"]["approach_3d_mm"] = None
    r = C.paired(a, b, "approach_3d_mm", n_boot=2000, seed=0)
    assert r["n_pairs"] == 199 and r["n_unpaired"] == 1
    assert np.isclose(r["mean_diff"], 5.0) and r["ci95"][0] <= 5.0 <= r["ci95"][1]
    assert C.paired(a, b, "approach_3d_mm", n_boot=2000, seed=0) == r


def test_subset_filter_and_summary(tmp_path):
    import json
    rows = [{"id": f"standard_tz{z}_mug_tray_s0_c00{i}", "call": i, "step": "above_target", "valid": True,
             "action_ok": True, "approach_row": True, "approach_xy_mm": 1.0 + i, "carry_xy_mm": None,
             "approach_3d_mm": 2.0, "grasp_z_mm": None, "point_px": None, "episode": "e"}
            for z in ("0.82", "0.92") for i in range(3)]
    (tmp_path / "scores.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    sc = C.load_scores(str(tmp_path), ["tz0.82"])
    assert len(sc) == 3 and all("tz0.82" in k for k in sc)
    s = C.summary_of(sc)
    assert s["control_all"]["n"] == 3 and s["control_all"]["approach_xy_median_mm"] == 2.0
    assert s["control_first_call"]["n"] == 1


def test_verdict_rules_boundaries():
    dev_ok = {"xy_med": 7.0, "valid": 0.96, "action": 0.90}
    full = {"xy_med": 2.0, "valid": 1.0, "action": 0.95}
    # DEV non-inferior: xy <= full + 5 mm, valid >= 0.95, action >= full - 0.05
    assert C.dev_noninferior(dev_ok, full)
    assert not C.dev_noninferior(dict(dev_ok, xy_med=7.01), full)
    assert not C.dev_noninferior(dict(dev_ok, valid=0.949), full)
    assert not C.dev_noninferior(dict(dev_ok, action=0.899), full)
    # OOD-H vs a reference (paired CI of arm - ref, margin 5 mm)
    assert C.ood_call([-3.0, -0.1]) == "BETTER"
    assert C.ood_call([-3.0, 4.99]) == "NONINFERIOR"
    assert C.ood_call([-3.0, 5.0]) == "INCONCLUSIVE"
    assert C.ood_call([5.01, 9.0]) == "WORSE"
