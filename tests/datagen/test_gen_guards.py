"""R2 generator guards (pure): seeds, splits, the no-random rule."""
import pytest

from harvest.datagen import gen as G


def test_dev_seeds_only_unless_confirmed_train_range():
    assert G.parse_seeds("0-5") == [0, 1, 2, 3, 4, 5]
    for bad in ("30", "500", "1000", "1300", "2000", "10000"):
        with pytest.raises(ValueError):
            G.parse_seeds(bad)
    assert G.parse_seeds("10000-10001", allow_train=True) == [10000, 10001]
    for bad in ("500", "1149", "1329", "2119"):  # CAL / TEST / TEST-P5 / POOL stay refused even with the flag
        with pytest.raises(ValueError):
            G.parse_seeds(bad, allow_train=True)


def test_train_range_is_disjoint_from_reserved_ranges():
    r = set(G.R2_TRAIN_SEEDS)
    # DEV, 500-699 (a superset of CAL 500-549), TEST, TEST-P5, POOL
    for rng in (range(0, 30), range(500, 700), range(1000, 1150), range(1300, 1330), range(2000, 2120)):
        assert not r & set(rng)


def test_split_dev_and_fit_eval():
    assert G.split_of(3) == "dev"
    assert G.split_of(10000) == "eval" and G.split_of(10001) == "fit"
    s = [G.split_of(x) for x in range(10000, 12000)]
    assert s.count("eval") == 100  # 5 %


def test_random_variant_is_refused_before_anything_runs(tmp_path):
    with pytest.raises(ValueError, match="TEST pool"):
        G.gen(str(tmp_path / "o"), "random", ["mug_tray"], ["P0"], [0])
    with pytest.raises(SystemExit):
        G.gen(str(tmp_path / "o"), "dr", ["mug_tray"], ["P3"], [0])
