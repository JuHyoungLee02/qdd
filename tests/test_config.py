import dataclasses

import pytest

from harvest.config import CFG


def test_canonical_values():
    assert CFG.T_c == 0.33 and CFG.near_in_m == 0.05 and CFG.near_out_m == 0.06
    assert CFG.h_lift_m == 0.03 and CFG.tilt_max_deg == 30.0
    assert CFG.jev_model == "jev-1.13.0" and "latest" not in CFG.jev_model
    assert CFG.near_out_m > CFG.near_in_m


def test_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        CFG.T_c = 0.5
