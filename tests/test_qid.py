from harvest.qid import question_id

DESC = {"a": "up", "b": "down"}


def test_same_content_same_id_whitespace_insensitive(tmp_path, monkeypatch):
    monkeypatch.setenv("HARVEST_QID_REGISTRY", str(tmp_path / "r.json"))
    a = question_id("Which dir?", ["a", "b"], DESC, {"a": "A", "b": "B"}, None)
    b = question_id("Which  dir? ", ["a", "b"], DESC, {"a": "A", "b": "B"}, None)
    assert a == b and a.endswith("@v1")


def test_display_change_changes_id(tmp_path, monkeypatch):
    monkeypatch.setenv("HARVEST_QID_REGISTRY", str(tmp_path / "r.json"))
    a = question_id("Q", ["a", "b"], DESC, {"a": "A", "b": "B"}, None)
    b = question_id("Q", ["a", "b"], DESC, {"a": "X", "b": "B"}, None)
    assert a != b and b.endswith("@v2")
