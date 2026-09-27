from tools.xemb.h2h_compare import verdict


def _sc(vals):
    return {f"s{i}": {"approach_3d_mm": v} for i, v in enumerate(vals)}


def test_verdict_better_same_worse():
    ref = _sc([50.0 + (i % 5) for i in range(60)])
    assert verdict(_sc([20.0 + (i % 5) for i in range(60)]), ref)["verdict"] == "BETTER"
    assert verdict(_sc([50.0 + ((i + 2) % 5) for i in range(60)]), ref)["verdict"] == "SAME"
    assert verdict(_sc([80.0 + (i % 5) for i in range(60)]), ref)["verdict"] == "WORSE"


def test_verdict_pairs_only_common_ids():
    a = {"x": {"approach_3d_mm": 1.0}, "y": {"approach_3d_mm": None}}
    b = {"x": {"approach_3d_mm": 2.0}, "y": {"approach_3d_mm": 3.0}}
    assert verdict(a, b)["n_pairs"] == 1
