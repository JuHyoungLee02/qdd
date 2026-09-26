"""Paid spot check runner (tools/prompt_health/astra_spot.py) with the mock client: G1 v2 input form, budget stop at
80 % of the cap, resumable rows. No network."""
import importlib.util
import json
import os
import sys
from types import SimpleNamespace

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools", "prompt_health"))


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, *rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


AS = _load("ph_astra_spot", ("tools", "prompt_health", "astra_spot.py"))


def _snap(tmp_path, holding):
    from PIL import Image
    sd = tmp_path / ("held" if holding else "free")
    sd.mkdir()
    for k in ("head", "wrist_left", "wrist"):
        Image.fromarray(np.zeros((8, 8, 3), np.uint8)).save(sd / f"{k}.png")
    meta = {"gt": {"tgt": "o3", "holding": holding, "state": "pre", "instruction": "Put the red mug on the blue tray."}}
    return str(sd), meta


def test_grasp_input_matches_g1_form(tmp_path):
    sd, meta = _snap(tmp_path, False)
    inp = AS.grasp_input(sd, meta, "base")
    c = inp[0]["content"]
    assert c[0]["type"] == "input_text" and "DEFINITION" in c[0]["text"]
    assert [x["text"] for x in c[1::2]] == ["Image 1: head camera", "Image 2: left wrist camera",
                                             "Image 3: right wrist camera"]
    assert all(x["detail"] == "high" and x["image_url"].startswith("data:image/png") for x in c[2::2])


def test_run_stops_at_80_percent_and_resumes(tmp_path, monkeypatch):
    sd, meta = _snap(tmp_path, False)
    items = [("grasp", f"s{i}", v, (sd, meta)) for i in range(20) for v in ("base", "para3")]
    monkeypatch.setattr(AS, "plan", lambda *a: items)
    prices = tmp_path / "p.json"
    prices.write_text(json.dumps({"model": "gpt-6-astra", "date": "2026-09-26", "usd_per_mtok_input": 10.0,
                                  "usd_per_mtok_cached_input": 1.0, "usd_per_mtok_output": 50.0, "krw_per_usd": 1450.0,
                                  "source": "test"}))
    a = SimpleNamespace(prices=str(prices), ledger=str(tmp_path / "l.jsonl"), out=str(tmp_path / "o.jsonl"),
                        cap_krw=200.0, n_frame=0, n_neg=0, n_pos=0, mock=True)
    res = AS.run(a)
    rows = [json.loads(x) for x in open(a.out)]
    assert res["stopped"] and res["ledger"]["spent_krw"] <= 160.0 + 1e-6
    assert rows and all(r["valid"] is False for r in rows)  # the mock answer is not a grasp JSON -> parse error path
    n = len(rows)
    a.cap_krw = 400.0
    AS.run(a)
    rows2 = [json.loads(x) for x in open(a.out)]
    assert len(rows2) > n and len({(r["snap"], r["variant"]) for r in rows2}) == len(rows2)
