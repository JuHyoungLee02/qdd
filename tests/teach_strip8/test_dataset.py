"""E-STRIP8 data (prereg_strip8.md §2): the arms reuse the E-PT nd-xyz rows (same states, same labels, same aux QA,
same repeats) and change only the control request: s-min = the minimal text on the ring-only image for every row;
s-drop (training only) = per row occurrence a dropout draw, text stripped by the draw, grid image when the overlay is
kept. The v2 -> nd-xyz identity is checked on every row (a mismatch stops the build)."""
import json
import os

import pytest

from harvest.astra_solo.pt_episode import PtEpisode
from harvest.astra_solo.pt_truth import PtTruth
from harvest.teach_strip8 import dataset as D
from harvest.teach_strip8 import strip as S

from astra_solo.test_pt_episode import PadWorld


@pytest.fixture(scope="module")
def src(tmp_path_factory):
    d = tmp_path_factory.mktemp("strip8ds")
    w = PadWorld()
    m = PtTruth(w)
    tcps = []
    ask = m.ask

    def ask_rec(text, images, meta):  # the TCP of each call (= the collector row's gt.tcp)
        tcps.append(list(map(float, w.status()["tcp"])))
        return ask(text, images, meta)

    m.ask = ask_rec
    ep = PtEpisode(w, m, 3, "mug_tray", str(d / "ep"), save_v2=True, save_nd=True)
    m.ep = ep
    ep.run()
    rows = []
    for k, c in enumerate(sorted((d / "ep" / "calls").iterdir())):
        if not (c / "prompt_v2.txt").exists():
            continue
        r = {"id": f"standard_mug_tray_s20100_c{k:03d}", "kind": "control", "call_dir": str(c), "seed": 20100,
             "gt": {"tcp": tcps[k]}, "cams_path": str(c / "cams.json"),
             "step": "above_target", "prompt_path": str(c / "prompt_nd-xyz@v1.txt"),
             "images": [str(c / "img1_head_ring.png"), str(c / "img2_right_wrist_camera.png")], "answer": "{}"}
        rows += [r, r]  # a repeated row (repeat_of = 2)
        rows.append({"id": r["id"] + "_aux_tgt", "kind": "aux", "prompt": "q", "images": r["images"][:1],
                     "answer": "{}", "seed": 20100})
    p = d / "train_nd-xyz.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return d, p, rows


def _read(p):
    return [json.loads(x) for x in open(p, encoding="utf-8")]


def test_s_min_rows(src):
    d, p, rows = src
    c = D.build(str(p), str(d / "out"), "train", "s-min")
    out = _read(d / "out" / "train_s-min.jsonl")
    assert len(out) == len(rows) and c["control_rows"] == 2 * c["aux_rows"]
    for a, b in zip(rows, out):
        if a["kind"] == "aux":
            assert a == b
            continue
        assert b["images"] == a["images"] and b["answer"] == a["answer"] and b["arm"] == "s-min"
        t = open(b["prompt_path"], encoding="utf-8").read()
        assert t == S.minimal(open(os.path.join(a["call_dir"], "prompt_v2.txt"), encoding="utf-8").read())
        assert b["drops"] == sorted(S.FIELDS)


def test_s_drop_rows(src):
    d, p, rows = src
    c = D.build(str(p), str(d / "out"), "train", "s-drop", seed=0)
    out = _read(d / "out" / "train_s-drop.jsonl")
    assert len(out) == len(rows) and sum(c["field_drop_counts"].values()) > 0
    for a, b in zip(rows, out):
        if a["kind"] == "aux":
            assert a == b
            continue
        drops = set(b["drops"])
        v2 = open(os.path.join(a["call_dir"], "prompt_v2.txt"), encoding="utf-8").read()
        assert open(b["prompt_path"], encoding="utf-8").read() == S.strip(v2, drops)
        want = "img1_head_ring.png" if "overlay" in drops else "img1_head_camera.png"
        assert os.path.basename(b["images"][0]) == want and b["images"][1] == a["images"][1]
    again = D.build(str(p), str(d / "out2"), "train", "s-drop", seed=0)
    assert again["drop_sets"] == c["drop_sets"]


def _px(p):
    from PIL import Image
    import numpy as np
    return np.asarray(Image.open(p).convert("RGB"))


def test_s_stale_rebuilds_v2_with_a_written_table_height(src, tmp_path):
    """s-stale = the v2 request with a hand-written table height: at the true height it is the saved v2 request
    (text and head pixels); at another height the table line and the grid / drop line move."""
    import numpy as np
    from astra_motion.fakeworld import TZ
    d, p, rows = src
    ctrl = [r for r in rows if r["kind"] == "control"]
    q = tmp_path / "ood_h_nd-xyz.jsonl"
    q.write_text("".join(json.dumps(dict(r, seed=3)) + "\n" for r in ctrl), encoding="utf-8")
    D.build(str(q), str(tmp_path / "same"), "ood_h", "s-stale", stale_z=TZ)
    for a, b in zip(ctrl, _read(tmp_path / "same" / "ood_h_s-stale.jsonl")):
        assert open(b["prompt_path"], encoding="utf-8").read() == open(
            os.path.join(a["call_dir"], "prompt_v2.txt"), encoding="utf-8").read()
        assert np.array_equal(_px(b["images"][0]), _px(os.path.join(a["call_dir"], "img1_head_camera.png")))
    D.build(str(q), str(tmp_path / "off"), "ood_h", "s-stale", stale_z=TZ + 0.03)
    for a, b in zip(ctrl, _read(tmp_path / "off" / "ood_h_s-stale.jsonl")):
        t = open(b["prompt_path"], encoding="utf-8").read()
        assert f"Table top surface: z = {TZ + 0.03:.3f} m" in t and b["stale_z"] == round(TZ + 0.03, 4)
        assert not np.array_equal(_px(b["images"][0]), _px(os.path.join(a["call_dir"], "img1_head_camera.png")))
    with pytest.raises(ValueError):
        D.build(str(q), str(tmp_path / "x"), "dev", "s-stale", stale_z=TZ)


def test_s_drop_is_training_only_and_mismatch_stops(src, tmp_path):
    d, p, rows = src
    with pytest.raises(ValueError):
        D.build(str(p), str(tmp_path / "o"), "dev", "s-drop")
    bad = dict(rows[0], prompt_path=str(tmp_path / "other.txt"))
    (tmp_path / "other.txt").write_text("not the nd request", encoding="utf-8")
    q = tmp_path / "bad.jsonl"
    q.write_text(json.dumps(bad) + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        D.build(str(q), str(tmp_path / "o"), "train", "s-min")
