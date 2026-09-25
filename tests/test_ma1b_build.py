"""tools/ma1/build_a3d.py summary (prereg_ma1b §2)."""
import importlib.util
import pathlib

spec = importlib.util.spec_from_file_location("b", pathlib.Path(__file__).parents[1] / "tools/ma1/build_a3d.py")
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


def test_summary_counts():
    rows = [{"span_s": 3.0, "mask": [1] * 4, "d": [0.0] * 9 + [0.03, 0.04, 0.0], "label_check_m": 1e-6},
            {"span_s": 0.0, "mask": [0] * 4, "d": [0.0] * 12, "label_check_m": 0.0},
            {"span_s": 1.0, "mask": [1] * 4, "d": [0.0] * 9 + [0.0, 0.0, 0.1], "label_check_m": 2e-6}]
    s = b.summarize(rows)
    assert s["rows"] == 3 and s["masked_rows"] == 1 and s["span_s_frac_cap3s"] == 1 / 3
    assert abs(s["end_disp_m_median"] - 0.075) < 1e-12 and s["label_check_max_m"] == 2e-6
    assert b.LABEL_TOL == 2e-5
