"""E-OPRATIO8 G scoring: point parsing (0-1000 JSON, benchmark tuple, 0-1 answers), label hit = 3 % of the diagonal,
mask hit."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "teach_pt"))
import geval as GE  # noqa: E402


def test_parse():
    assert GE.parse_point('{"point": [500, 250]}') == [500.0, 250.0]
    assert GE.parse_point('{"point_2d": [10, 20]}') == [10.0, 20.0]
    assert GE.parse_point("[(0.5, 0.25)]") == [500.0, 250.0]
    assert GE.parse_point("no idea") is None


def test_score(tmp_path):
    img = tmp_path / "i.png"
    Image.fromarray(np.zeros((100, 200, 3), np.uint8)).save(img)
    mk = np.zeros((100, 200), np.uint8)
    mk[40:60, 90:110] = 255
    Image.fromarray(mk).save(tmp_path / "m.png")
    lab = {"id": "a", "gset": "s", "images": [str(img)], "answer": json.dumps({"point": [500, 500]}), "score": "label"}
    s = GE.score_row(lab, '{"point": [505, 505]}')
    assert s["valid"] and s["hit"] and s["px_err"] < 2
    s = GE.score_row(lab, '{"point": [700, 500]}')
    assert not s["hit"] and s["px_err"] == 40.0
    msk = {"id": "b", "gset": "w", "images": [str(img)], "mask": str(tmp_path / "m.png"), "score": "mask"}
    assert GE.score_row(msk, '{"point": [500, 500]}')["hit"]
    assert not GE.score_row(msk, '{"point": [100, 100]}')["hit"]
    jm = mk.copy()
    jm[jm > 0] = 200  # a JPEG-like soft mask with a .jpg file only
    Image.fromarray(jm).save(tmp_path / "j.jpg", quality=90)
    jr = dict(msk, mask=str(tmp_path / "j.png"))
    assert GE.score_row(jr, '{"point": [500, 500]}')["hit"]
    assert not GE.score_row(jr, '{"point": [100, 100]}')["hit"]
    summ = GE.summarize([GE.score_row(msk, '{"point": [500, 500]}'), GE.score_row(msk, "x")])
    assert summ["ALL"]["hit"] == 0.5 and summ["ALL"]["valid"] == 0.5
