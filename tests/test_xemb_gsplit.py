import pytest

from tools.xemb import gsplit as GS


def test_group_of_families():
    assert GS.group_of({"id": "molmobot_rby1_mb_RBY1_house_24655_b13o20_t0_70_place", "source": "molmobot/rby1"}) == \
        ("molmobot", "24655")
    assert GS.group_of({"id": "behavior_b1kdh_00100010_60_x_D", "source": "behavior1k/r1pro"}) == ("behavior", "00100010")
    assert GS.group_of({"id": "rb2_rb2_209_40_right_proj", "source": "robotis/ffw_bg2_rb2"}) == ("rb2", "209")
    assert GS.group_of({"id": "mf_x", "source": "oxe_maniskill/panda"}) is None


def test_split_is_about_ten_percent_and_guard_raises():
    rows = [{"id": f"behavior_b1k_{i:08d}_0", "source": "behavior1k/r1pro"} for i in range(2000)]
    tr, g = GS.split(rows)
    assert 150 < len(g) < 250 and len(tr) + len(g) == 2000
    GS.guard(tr)
    with pytest.raises(RuntimeError):
        GS.guard(g[:1])
