from tools.xemb.src_rig_t4 import parse_task


def test_parse_rb3_task():
    assert parse_task("Pick up the tube with the left gripper and place it into the box below.") == \
        ("tube", "box", "left")
    assert parse_task("Pick up the yellow paintbrush with the right gripper and place it into the box below.") == \
        ("yellow paintbrush", "box", "right")


def test_parse_rejects_other():
    assert parse_task("Place bottles in color-matching boxes: red->top left") is None
