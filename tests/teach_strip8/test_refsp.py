"""RefSpatial Simulator -> pointing rows (prereg_dround2.md §1 c): single-point human/gpt turns become an aux row with
the object-pointing pack's form (source / frame tags, 0-1000 answer); multi-point or non-point turns are skipped."""
import json

from harvest.teach_strip8 import refsp as R

REC = {"id": "ab", "image": ["ab.jpg"], "conversations": [
    {"from": "human", "value": "Locate a point on the soda can. Your answer should be formatted as a list of tuples, "
                                "i.e. [(x1, y1)], where each tuple contains ... between 0 and 1, indicating the "
                                "normalized pixel locations of the points in the image."},
    {"from": "gpt", "value": "[(0.275, 0.443)]"},
    {"from": "human", "value": "Point to two free spots. Your answer should be formatted as a list of tuples"},
    {"from": "gpt", "value": "[(0.1, 0.2), (0.3, 0.4)]"},
    {"from": "human", "value": "Which is taller?"}, {"from": "gpt", "value": "the can"}]}


def test_rows_from_record():
    rows = R.rows_of(REC, "/img", 640, 480)
    assert len(rows) == 1
    r = rows[0]
    assert r["kind"] == "aux" and r["images"] == ["/img/ab.jpg"]
    assert json.loads(r["answer"]) == {"point": [275, 443]}
    assert r["prompt"].startswith("source: refspatial/simulator\nframe: pixel\n")
    assert "Locate a point on the soda can." in r["prompt"] and "Your answer should be" not in r["prompt"]
    assert "0-1000" in r["prompt"]
