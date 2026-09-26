"""E-TEACH-35B data rows: the solo layout (teach_l8, 'Image k: <label>') and the coupled astra-couple@v2 layout
('cam_x:' label before each image, as harvest.couple.local_vlm.to_chat sends the production input), and the label
check with the runtime parsers (solo: astra_solo.schema.validate, couple: couple.schema.parse_answer version v2)."""
import json

from harvest.couple.local_vlm import to_chat
from harvest.teach_35b import data as DT

COUPLE_OK = {"assessment": {"task_progress": {"verified_completed": [], "currently_attempting": "approach",
                                              "remaining": ["grasp"]},
                            "execution": "progressing", "intent": "aligned", "confidence": "high",
                            "evidence": "tip 3 cm above the mug", "evidence_views": ["cam_head", "cam_wrist_right"],
                            "claims": [{"kind": "not_grasped", "view": "cam_wrist_right"}]},
             "segment": {"now": "approach", "do": "none", "next": "descend"}, "command": "continue", "edit": None,
             "info_request": "none"}


def _couple_row(tmp_path, answer):
    p = tmp_path / "prompt.txt"
    p.write_text("COUPLE REQ", encoding="utf-8")
    return {"id": "c1", "kind": "control", "format": "astra-couple@v2", "prompt_path": str(p),
            "images": ["h.png", "w.png"], "image_labels": ["cam_head:", "cam_wrist_right:"],
            "cameras": ["cam_head", "cam_wrist_right"], "answer": json.dumps(answer)}


def test_couple_layout_matches_production_chat(tmp_path):
    row = _couple_row(tmp_path, COUPLE_OK)
    m = DT.messages(row, False)
    prod = to_chat([{"role": "user", "content": [
        {"type": "input_text", "text": "COUPLE REQ"}, {"type": "input_text", "text": "cam_head:"},
        {"type": "input_image", "image_url": "x"}, {"type": "input_text", "text": "cam_wrist_right:"},
        {"type": "input_image", "image_url": "y"}]}])
    assert [c["type"] for c in m[0]["content"]] == ["text", "text", "image", "text", "image"]
    assert [c.get("text") for c in m[0]["content"]] == [c.get("text") for c in prod[0]["content"]]
    assert DT.messages(row, True)[1]["content"][0]["text"] == row["answer"]


def test_solo_layout_unchanged(tmp_path):
    from harvest.teach_l8 import train as L8
    p = tmp_path / "prompt.txt"
    p.write_text("REQ", encoding="utf-8")
    row = {"kind": "control", "prompt_path": str(p), "images": ["a", "b"], "answer": "{}"}
    assert DT.messages(row, True) == L8.messages(row, True)


def test_label_check(tmp_path):
    assert DT.label_problems(_couple_row(tmp_path, COUPLE_OK)) == []
    bad = dict(COUPLE_OK, segment={"now": "approach", "do": "none"})
    assert DT.label_problems(_couple_row(tmp_path, bad))
    assert DT.label_problems({"kind": "aux", "answer": "x"}) == []  # aux answers are not runtime commands
    solo_bad = {"kind": "control", "answer": "{}", "id": "s"}
    assert DT.label_problems(solo_bad)
    assert DT.row_format(solo_bad) == "astra-solo@v2"
