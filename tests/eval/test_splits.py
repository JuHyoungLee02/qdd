"""R6 split guard: CAL / TEST / TEST-P5 only behind --split + HARVEST_ALLOW_SPLIT (main session, pre-registered time)."""
import pytest

from harvest.eval.splits import check_seeds, check_split, split_of


def test_split_of_seed_ranges():
    assert split_of(0) == "dev" and split_of(29) == "dev"
    assert split_of(500) == "cal" and split_of(549) == "cal"
    assert split_of(1000) == "test" and split_of(1149) == "test"
    assert split_of(1300) == "test_p5" and split_of(1329) == "test_p5"
    assert split_of(2000) == "pool" and split_of(2119) == "pool"
    assert split_of(30) is None and split_of(1200) is None


@pytest.mark.parametrize("split", ["dev", "pool"])
def test_dev_and_pool_need_no_env(split):
    assert check_split(split, env={}) == split


@pytest.mark.parametrize("split", ["cal", "test", "test_p5"])
def test_protected_split_refused_without_env(split):
    with pytest.raises(SystemExit, match="HARVEST_ALLOW_SPLIT"):
        check_split(split, env={})


def test_protected_split_needs_the_matching_env_value():
    with pytest.raises(SystemExit):
        check_split("test", env={"HARVEST_ALLOW_SPLIT": "cal"})
    assert check_split("cal", env={"HARVEST_ALLOW_SPLIT": "cal"}) == "cal"
    assert check_split("test_p5", env={"HARVEST_ALLOW_SPLIT": "test_p5"}) == "test_p5"


def test_unknown_split_refused():
    with pytest.raises(SystemExit):
        check_split("train", env={})


def test_check_seeds_refuses_seeds_outside_the_declared_split():
    assert check_seeds([0, 5, 29], "dev") == [0, 5, 29]
    with pytest.raises(SystemExit, match="1000"):
        check_seeds([0, 1000], "dev")  # a TEST seed inside DEV data is refused (never opened)
    with pytest.raises(SystemExit, match="500"):
        check_seeds([2000, 500], "pool")


def test_check_seeds_for_protected_split_still_needs_env():
    with pytest.raises(SystemExit):
        check_seeds([500], "cal", env={})
    assert check_seeds([500, 549], "cal", env={"HARVEST_ALLOW_SPLIT": "cal"}) == [500, 549]
