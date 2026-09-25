"""E-MA2 (prereg_ma2) data tool: the fixed evaluation set selection."""
import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("build_ma2", os.path.join(ROOT, "tools", "ma2", "build_ma2.py"))
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)


def _recs():
    out = []
    for v in ("standard", "dr"):
        for t in ("mug_tray", "bottle_tray"):
            for s in range(10000, 10100, 20):
                for k in range(0, 60, 10):
                    out.append({"id": f"{v}/{t}/P0/ep{s}/k{k}", "split": "eval"})
            out.append({"id": f"{v}/{t}/P0/ep10001/k0", "split": "fit"})
    return out


def test_select_eval_is_stratified_seeded_and_eval_split_only():
    recs = _recs()
    ids = B.select_eval(recs, 7, seed=0)
    assert len(ids) == 4 * 7 and len(set(ids)) == len(ids)
    assert all("ep10001" not in i for i in ids)
    assert ids == B.select_eval(list(reversed(recs)), 7, seed=0)  # independent of the input order
    assert ids != B.select_eval(recs, 7, seed=1)
    for v in ("standard", "dr"):
        for t in ("mug_tray", "bottle_tray"):
            assert sum(i.startswith(f"{v}/{t}/") for i in ids) == 7


def test_select_eval_takes_all_of_a_small_stratum():
    recs = [{"id": "dr/mug_tray/P1/ep10620/k0", "split": "eval"}]
    assert B.select_eval(recs, 5) == ["dr/mug_tray/P1/ep10620/k0"]
