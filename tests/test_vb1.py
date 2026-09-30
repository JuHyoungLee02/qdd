"""E-VB1 helpers: GPU_WANTED card parsing, selection split, lane smoke gating."""
import json
import os

from tools.vb1 import card as CD
from tools.vb1 import eps as E


def _w(tmp_path, txt):
    p = tmp_path / "GPU_WANTED"
    p.write_text(txt)
    return str(p)


def test_card_wanted(tmp_path):
    p = _w(tmp_path, "7a2a:0,1,3\n")
    assert CD.card_wanted("7a2a:1", p) and CD.card_wanted("7a2a:3", p)
    assert not CD.card_wanted("7a2a:2", p) and not CD.card_wanted("x2:1", p)
    p = _w(tmp_path, "7a2a-x2:1")
    assert CD.card_wanted("x2:1", p) and not CD.card_wanted("7a2a:1", p)
    p = _w(tmp_path, "x2:1 7a2a:0")
    assert CD.card_wanted("x2:1", p) and CD.card_wanted("7a2a:0", p) and not CD.card_wanted("7a2a:3", p)
    assert CD.card_wanted("7a2a:3", _w(tmp_path, ""))  # empty file = every card
    assert CD.card_wanted("x2:1", _w(tmp_path, "all"))
    assert not CD.card_wanted("7a2a:1", str(tmp_path / "missing"))


def test_sel_split_rate():
    n = sum(E.is_sel(s) for s in range(40000, 50000))
    assert 200 < n < 400  # ~3 %


def test_next_group_waits_for_smoke(tmp_path, monkeypatch):
    monkeypatch.setattr(E, "ROOT", str(tmp_path))
    os.makedirs(tmp_path / "eps")
    groups = [{"id": "g0000", "job": "j", "n": 1, "smoke": True}, {"id": "g0001", "job": "j", "n": 1}]
    json.dump({"groups": groups}, open(tmp_path / "groups.json", "w"))
    for g, s in (("g0000", 1), ("g0001", 2)):
        json.dump([{"vdir": "v", "task": "t", "seed": s}], open(tmp_path / "eps" / f"{g}.json", "w"))
    assert E.next_group("a") == "g0000"
    assert E.next_group("b") == "WAIT"  # g0000 locked, smoke not checked
    (tmp_path / "SMOKE_OK").write_text("{}")
    assert E.next_group("b") == "g0001"
    assert E.next_group("c") == "WAIT"  # unfinished groups all locked: wait (a yielding lane releases its group)
    (tmp_path / "SMOKE_FAIL").write_text("{}")
    assert E.next_group("d").startswith("ALERT")
