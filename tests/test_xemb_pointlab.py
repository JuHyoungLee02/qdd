import json

from tools.xemb.pointlab import clean_name, is_nc, row


def test_clean_name_generic_and_articles():
    assert clean_name("the Red Mug.") == "red mug"
    assert clean_name("object") is None and clean_name("the object") is None and clean_name("a designated object") is None
    assert clean_name("goal position") is None and clean_name("table") is None
    assert clean_name("yellow_paint_brush") == "yellow paint brush"


def test_row_point_only_and_tags():
    r = row("agibot/g1", "CC BY-NC-SA 4.0", "head", "a.jpg", 640, 480, [320, 120], "the cucumber", "obj_point", "x")
    a = json.loads(r["answer"])
    assert a == {"point": [500, 250]} and set(a) == {"point"}
    assert r["nc"] and not r["astra_ok"] and r["view"] == "head" and r["name"] == "cucumber"
    assert row("s", "MIT", "third", "a.jpg", 100, 100, [150, 10], "cup", "obj_point", "y") is None
    assert row("s", "MIT", "head", "a.jpg", 100, 100, [50, 10], "object", "obj_point", "z") is None
    e = row("s", "MIT", "head", "a.jpg", 100, 100, [50, 10], None, "ee_point", "w", arm="right")
    assert e is not None and "right gripper" in e["prompt"] and not e["nc"]


def test_is_nc():
    assert is_nc("CC BY-NC-SA 4.0") and not is_nc("CC BY 4.0") and not is_nc("MIT")
