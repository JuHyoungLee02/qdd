"""L8-D collection (fake world) -> dataset in every switchable format, with scene fields, tags and split guards."""
import json
import os

import pytest

from harvest.teach_l8d import collect as C
from harvest.teach_l8d import dataset as D
from harvest.teach_strip8 import strip as S

from astra_solo.test_pt_episode import PadWorld

TAGS = "source: qdd_sim/ffw_sg2\nframe: base_ffw_sg2\n"


@pytest.fixture(scope="module")
def root(tmp_path_factory):
    r = tmp_path_factory.mktemp("l8d")
    w = PadWorld()
    for s in (30001, 30002):
        m = C.collect_episode(w, s, "mug_tray", "standard", "train",
                              str(r / "collect" / "train" / "standard_tz0.850" / f"mug_tray_s{s}"), p=0.35)
        assert m["table_z"] == pytest.approx(w.table_z) and m["n_distractors"] >= 0
    return r


def _rows(p):
    return [json.loads(x) for x in open(p, encoding="utf-8")]


def test_scene_json_written(root):
    sc = json.load(open(root / "collect" / "train" / "standard_tz0.850" / "mug_tray_s30001" / "scene.json"))
    assert sc["schema"] == C.SCENE_SCHEMA and sc["split"] == "train" and sc["task"] == "mug_tray"
    assert "n" in sc["distractors"] and sc["table_z"] > 0


@pytest.mark.parametrize("fmt", D.FORMATS)
def test_every_format_builds_from_the_same_states(root, fmt):
    out = root / f"data_{fmt}"
    c = D.build(str(root / "collect" / "train"), str(out), "train", fmt)
    rows = _rows(out / f"train_{fmt}.jsonl")
    ctrl = [r for r in rows if r["kind"] == "control"]
    assert ctrl and c["control_unique"] > 0
    for r in ctrl:
        assert r["format"] == fmt and r["scene"]["table_z"] > 0 and "n_distractors" in r["scene"]
        assert os.path.exists(r["prompt_path"]) and all(os.path.exists(p) for p in r["images"])
        if fmt == "v2":
            assert r["prompt_path"].endswith("prompt_v2.txt") and r["images"][0].endswith("img1_head_camera.png")
        if fmt == "s-min":
            v2 = open(os.path.join(r["call_dir"], "prompt_v2.txt"), encoding="utf-8").read()
            assert open(r["prompt_path"], encoding="utf-8").read() == S.minimal(v2)
            assert r["images"][0].endswith("img1_head_ring.png")
    cnt = json.load(open(out / f"train_{fmt}.counts.json"))
    for k in ("by_task", "by_table_z", "by_height_bin", "by_dist_bin", "by_variant", "episodes_by_task_height"):
        assert k in cnt


def test_tags_prefix_every_request(root):
    plain = root / "data_plain"
    tagged = root / "data_tags"
    D.build(str(root / "collect" / "train"), str(plain), "train", "v2")
    D.build(str(root / "collect" / "train"), str(tagged), "train", "v2", tags=True)
    a, b = _rows(plain / "train_v2.jsonl"), _rows(tagged / "train_v2_tags.jsonl")
    assert len(a) == len(b)
    for x, y in zip(a, b):
        if x["kind"] == "control":
            tx = open(x["prompt_path"], encoding="utf-8").read()
            ty = open(y["prompt_path"], encoding="utf-8").read()
            assert ty == TAGS + tx and "frame" not in json.loads(y["answer"])
        else:
            assert y["prompt"] == TAGS + x["prompt"]
        assert y["tags"] is True


def test_noisy_depth_variant(root):
    import numpy as np
    out = root / "data_noise"
    c = D.build(str(root / "collect" / "train"), str(out), "train", "pt", depth_noise="zed_mini")
    assert c["depth_noise"] == "zed_mini"
    rows = [r for r in _rows(out / "train_pt_zed_mini.jsonl") if r["kind"] == "control"]
    assert rows
    for r in rows[:5]:
        assert "depth_zed_mini" in r["depth_path"] and r["depth_noise"]["preset"] == "zed_mini"
        a = np.load(r["depth_path"])["depth"]
        b = np.load(os.path.join(r["call_dir"], "head_depth.npz"))["depth"]
        assert a.shape == b.shape and not np.array_equal(np.nan_to_num(a), b)


def test_split_guards():
    with pytest.raises(ValueError):
        D.check_row({"seed": 70001, "variant": "standard"}, "train")
    with pytest.raises(ValueError):
        D.check_row({"seed": 30001, "variant": "randx"}, "train")
    with pytest.raises(ValueError):
        D.check_row({"seed": 5, "variant": "standard"}, "train")
    D.check_row({"seed": 70001, "variant": "drx"}, "ood_h")
    for t in ("smallcup_tray", "bluemug_bin", "bottle_stand"):
        with pytest.raises(ValueError):
            D.check_row({"seed": 31201, "variant": "drx", "task": t}, "train")
    D.check_row({"seed": 31201, "variant": "drx", "task": "mug_bin"}, "train")
    with pytest.raises(ValueError):
        D.check_row({"seed": 30001, "variant": "standard"}, "ood_h")
