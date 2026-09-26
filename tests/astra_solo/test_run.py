"""Runner guards: DEV layout seeds 0-19 only (pitfall P47: never CAL / TEST)."""
import pytest

from harvest.astra_solo.run import seeds_of


def test_dev_seeds_only():
    assert seeds_of("0,7,19") == [0, 7, 19]
    with pytest.raises(SystemExit):
        seeds_of("0,500")
