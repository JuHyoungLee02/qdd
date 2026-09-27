"""E-DIST8 minimal-input R / D / H rows (harvest.teach_pt.min_format) on the fake world: the three requests share the
S-min body (R = strip.minimal of the v2 request, byte for byte); D swaps only the command bullet / point block / answer;
H = R + depth tag + hybrid answer; the truth answers score ~0 through the runtime scorers (xyz, pt with depth, h with
depth, h without depth -> xyz branch); D-noisy points at a stereo-noise copy."""
import json

import pytest

from harvest.astra_solo import hybrid as HY
from harvest.astra_solo import nd_prompts as NP
from harvest.astra_solo import prompts as V2P
from harvest.astra_solo import pt_prompts as PT
from harvest.teach_pt import collect as C
from harvest.teach_pt import metrics as M
from harvest.teach_pt import min_format as MF
from harvest.teach_strip8 import strip as S

from astra_solo.test_pt_episode import PadWorld

SCORER = {"r-min": "xyz", "d-min": "pt", "h-min": "h"}


@pytest.fixture(scope="module")
def roots(tmp_path_factory):
    root = tmp_path_factory.mktemp("ptmin")
    w = PadWorld()
    C.collect_episode(w, 3, "mug_tray", "standard", str(root / "dev" / "standard" / "mug_tray_s3"), p=0.35)
    C.collect_episode(w, 20100, "mug_tray", "standard", str(root / "train" / "standard" / "mug_tray_s20100"), p=0.35)
    return root


def _rows(p):
    return [json.loads(x) for x in open(p, encoding="utf-8")]


def test_texts_share_the_min_body(roots):
    v2 = open(roots / "dev" / "standard" / "mug_tray_s3" / "calls" / "c000" / "prompt_v2.txt", encoding="utf-8").read()
    r, d, h_on, h_off = MF.r_text(v2), MF.d_text(v2), MF.h_text(v2, True), MF.h_text(v2, False)
    assert r == S.minimal(v2) and "Table top surface" not in r and "WHITE GRID" not in r
    for t in (d, h_on, h_off):
        assert "Table top surface" not in t and "WHITE GRID" not in t and "Grasping an upright" not in t
    assert NP._EEF_V2 not in d and "POINT, THEN ACT" in d and d.endswith(r.split(V2P.ANSWER)[1])
    assert PT.ANSWER in d and r.split("FRAME AND UNITS")[1].split("COMMANDS")[0] in d
    assert HY.TAG_ON in h_on and HY.TAG_OFF in h_off and r.split(V2P.ANSWER)[0] in h_off


def test_eval_rows_score_zero(roots):
    out = roots / "data"
    out.mkdir(exist_ok=True)
    for track, modes in (("r-min", ("clean",)), ("d-min", ("clean", "noisy")), ("h-min", ("clean", "noisy", "off"))):
        for mode in modes:
            MF.build(str(roots / "dev"), str(out), "dev", track, mode)
            rows = _rows(out / f"dev_{track}_{mode}.jsonl")
            assert rows and all(r["images"][0].endswith("img1_head_ring.png") for r in rows)
            sc = [M.score(r, r["answer"], SCORER[track]) for r in rows if not r["label_missing"]]
            assert all(s["valid"] and s["action_ok"] for s in sc), (track, mode)
            xy = [s["approach_xy_mm"] for s in sc if s["approach_xy_mm"] is not None]
            if mode != "noisy":
                assert xy and max(xy) < 15, (track, mode, xy)
            if track == "h-min":
                summ = M.summarize(sc)
                assert (summ["h_branches"]["pt"] == 0) == (mode == "off")
    noisy = _rows(out / "dev_d-min_noisy.jsonl")
    assert all("depth_zed_mini" in r["depth_path"] for r in noisy)


def test_convert_matches_build(roots):
    """convert() of the E-PT arm files gives the same control rows as build() and keeps the aux answers."""
    from harvest.teach_pt import dataset as DS
    out = roots / "conv"
    out.mkdir(exist_ok=True)
    DS.build(str(roots / "train"), str(out), "train", arms=("pt", "nd-xyz"))
    for track, src in (("d-min", "train_pt.jsonl"), ("h-min", "train_nd-xyz.jsonl"), ("r-min", "train_nd-xyz.jsonl")):
        c = MF.convert(str(out / src), str(out), track, f"train_{track}_conv.jsonl")
        rows = _rows(out / f"train_{track}_conv.jsonl")
        srcr = _rows(out / src)
        assert len(rows) == len(srcr) and c["aux_rows"] > 0
        for a, b in zip(rows, srcr):
            assert a["id"] == b["id"] and a["images"][0].endswith("img1_head_ring.png")
            if a["kind"] == "aux":
                assert a["answer"] == b["answer"]
        ctrl = [r for r in rows if r["kind"] == "control"]
        sc = [M.score(r, r["answer"], SCORER[track]) for r in ctrl if not r["label_missing"]]
        assert all(s["valid"] and s["action_ok"] for s in sc)
        if track == "d-min":
            assert all(json.loads(r["answer"])["command"].get("mode") != "eef" for r in ctrl)


def test_min_episodes_closed_loop(tmp_path):
    """r-min / d-min / h-min through the runtime episode: the truth succeeds, the request is the S-min body."""
    from harvest.astra_solo.pt_episode import PtEpisode
    from harvest.astra_solo.pt_truth import HTruth, NdTruth, PtTruth
    for iface, mk in (("r-min", lambda w: NdTruth(w, "nd-xyz")), ("d-min", PtTruth), ("h-min", HTruth)):
        w = PadWorld()
        m = mk(w)
        ep = PtEpisode(w, m, 3, "mug_tray", str(tmp_path / iface), iface=iface)
        m.ep = ep
        res = ep.run()
        assert res["success"], (iface, res["end_reason"], res["history"])
        t = (tmp_path / iface / "calls" / "c000" / "prompt.txt").read_text(encoding="utf-8")
        assert "Table top surface" not in t and "Grasping an upright" not in t and "WHITE GRID" not in t
        assert ("POINT, THEN ACT" in t) == (iface == "d-min") and (HY.TAG_ON in t) == (iface == "h-min")


def test_train_rows(roots):
    out = roots / "data"
    out.mkdir(exist_ok=True)
    for track in MF.TRACKS:
        c = MF.build(str(roots / "train"), str(out), "train", track)
        assert c["aux_rows"] > 0 and c["control_rows"] >= c["states"] - c["label_missing"]
    aux = [r for r in _rows(out / "train_d-min.jsonl") if r["kind"] == "aux"]
    assert all(r["images"][0].endswith("img1_head_ring.png") and "white grid" not in r["prompt"] for r in aux)
