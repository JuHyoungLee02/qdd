"""S-E2E temporal-context options (prereg_se2e_temporal): video2 past-frame rows, motion line, dropout, transition
stratum. Pure functions (no torch); the processor / model parts are in test_se2e_temporal_qwen.py (pod)."""
import json
import os

import numpy as np
import pytest

from harvest.train import se2e_data as S
from harvest.train import se2e_temporal as T
from harvest.train import stageb_data as D

from .test_se2e_data import _chain, _episode


def _rows(tmp_path, kind="RB1", stride=5):
    st, act = _episode()
    ref = lambda k: {"cam_head": f"img/k{k:04d}_h.jpg", "cam_wrist_left": f"img/k{k:04d}_l.jpg",  # noqa: E731
                     "cam_wrist_right": f"img/k{k:04d}_r.jpg"}
    rows = S.episode_rows(st, act, 10, {"right": _chain(), "left": _chain()}, 3, kind, "sort the coffee",
                          stride=stride, image_ref=ref)
    pref = lambda k: {c: f"img_prev/k{k:04d}_{c}.jpg" for c in ("cam_head", "cam_wrist_left",  # noqa: E731
                                                                 "cam_wrist_right")}
    aug = [{**r, **T.hist_fields(r, st, 10, S.FEATURE_NAMES_16, pref)} for r in rows]
    p = tmp_path / f"{kind}.stageb.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in aug), encoding="utf-8")
    return p, rows, aug, st


def test_prev_index_is_nearest_step_of_delta():
    assert T.prev_index(10, fps=10) == 7  # 0.3 s at 10 Hz = 3 steps
    assert T.prev_index(10, fps=30) == 1  # 9 steps, clamped at the episode start
    assert T.prev_index(2, fps=10) == 0 and T.prev_index(0, fps=10) == 0


def test_backward_velocity_is_causal():
    x = np.array([[0.0, 1.0], [0.1, 1.0], [0.3, 0.8], [5.0, 5.0]])
    np.testing.assert_allclose(T.backward_velocity(x, 0, 10), [0.0, 0.0])
    np.testing.assert_allclose(T.backward_velocity(x, 2, 10), [2.0, -2.0])  # uses k-1 and k only (not k+1)


def test_hist_fields_prev_frames_and_motion_source(tmp_path):
    _, rows, aug, st = _rows(tmp_path)
    for r, a in zip(rows, aug):
        assert a["k_prev"] == max(0, r["k"] - 3) and a["dt_prev_s"] == pytest.approx(0.1 * (r["k"] - a["k_prev"]))
        assert set(a["images_prev"]) == set(r["images"])  # the same cameras as the row
        assert a["images_prev"]["cam_head"] == f"img_prev/k{a['k_prev']:04d}_cam_head.jpg"
        ix = S.arm_index(S.FEATURE_NAMES_16, r["arm"])
        np.testing.assert_allclose(a["motion_src"]["qd_bwd"], T.backward_velocity(st[:, ix[:7]], r["k"], 10))
        assert a["motion_src"]["grip_rate_bwd"] == pytest.approx(float(T.backward_velocity(st[:, ix[7]], r["k"], 10)))


def test_option_off_gives_the_baseline_samples(tmp_path):
    p, _, _, _ = _rows(tmp_path)
    base = S.load_se2e(str(p), image_root="/root")
    assert T.load_se2e_t(str(p), image_root="/root", prev_root="/prev") == base


def test_video2_pairs_every_camera_with_the_past_frame(tmp_path):
    p, rows, aug, _ = _rows(tmp_path)
    smp = T.load_se2e_t(str(p), image_root="/root", prev_root="/prev", layout=T.LAYOUT_VIDEO2)
    base = S.load_se2e(str(p), image_root="/root")
    assert len(smp) == len(base)
    for s, b, a in zip(smp, base, aug):
        ims = s["context"]["images"]
        assert len(ims) == len(b["context"]["images"])
        for (lab, now, prev), (blab, bnow) in zip(ims, b["context"]["images"]):
            assert now == bnow  # the current frame is the baseline image
            cam = [c for c, x in a["images"].items() if os.path.join("/root", x) == now][0]
            assert prev == os.path.join("/prev", a["images_prev"][cam])
            assert lab == T.VIDEO_LABEL[cam] and lab != blab
        assert all(it["images"] == ims for it in s["items"])
        assert s["context"]["text"] == b["context"]["text"] and s["committed"] == b["committed"]
        assert [it["text"] for it in s["items"]] == [it["text"] for it in b["items"]]


def test_motion_bins_from_train_quantiles_and_line():
    rows = [{"split": "train", "kind": "RB1", "motion_src": {"qd_bwd": [v, 0, 0, 0, 0, 0, 0], "grip_rate_bwd": g}}
            for v, g in zip(np.linspace(0, 3, 301), np.linspace(-1.1, 1.1, 301))]
    rows.append({"split": "val", "kind": "RB1", "motion_src": {"qd_bwd": [100.0] + [0] * 6, "grip_rate_bwd": 50.0}})
    b = T.fit_motion_bins(rows)
    assert b["version"] == T.MOTION_VER and b["n"] == 301  # val rows are not used
    assert b["arm_speed"] == pytest.approx([1.0, 2.0])  # tertiles
    rate = np.abs(np.linspace(-1.1, 1.1, 301) / -1.10)  # RB1 open01 rate (0 = open, 1.10 = closed)
    assert b["grip_rate"] == pytest.approx(float(np.quantile(rate, T.GRIP_Q)))
    line = lambda v, g: T.motion_line({"kind": "RB1", "motion_src": {"qd_bwd": [v] + [0] * 6,  # noqa: E731
                                                                      "grip_rate_bwd": g}}, b)
    assert line(0.5, 0.0) == "motion: arm=still gripper=still"
    assert line(1.5, -1.1) == "motion: arm=slow gripper=opening"  # joint value falls = gripper opens
    assert line(2.5, 1.1) == "motion: arm=fast gripper=closing"
    assert T.MOTION_UNKNOWN == "motion: arm=unknown gripper=unknown"


def test_motion_line_in_context_and_questions(tmp_path):
    p, rows, aug, _ = _rows(tmp_path)
    b = T.fit_motion_bins(aug)
    smp = T.load_se2e_t(str(p), image_root="/root", prev_root="/prev", bins=b)
    base = S.load_se2e(str(p), image_root="/root")
    for s, x, a in zip(smp, base, aug):
        line = T.motion_line(a, b)
        assert s["context"]["text"] == x["context"]["text"] + "\n" + line
        for it, bit in zip(s["items"], x["items"]):
            assert it["text"] == bit["text"].replace(x["context"]["text"], s["context"]["text"], 1)
        alt = s["motion_alt"]
        assert alt["context_text"] == x["context"]["text"] + "\n" + T.MOTION_UNKNOWN
        assert [t for t in alt["item_texts"]] == [it["text"].replace(line, T.MOTION_UNKNOWN) for it in s["items"]]
        assert s["context"]["images"] == x["context"]["images"]


def test_motion_dropout_is_seeded_and_train_only(tmp_path):
    p, _, aug, _ = _rows(tmp_path, stride=1)
    smp = T.load_se2e_t(str(p), bins=T.fit_motion_bins(aug))
    a = T.motion_dropout(smp, step=5, seed=0)
    assert [x["context"]["text"] for x in a] == [x["context"]["text"] for x in T.motion_dropout(smp, 5, 0)]
    assert [x["context"]["text"] for x in a] != [x["context"]["text"] for x in T.motion_dropout(smp, 6, 0)]
    dropped = [x["context"]["text"].endswith(T.MOTION_UNKNOWN) for x in a]
    assert 0 < sum(dropped) < len(a)
    for x, s in zip(a, smp):
        if x["context"]["text"].endswith(T.MOTION_UNKNOWN):
            assert [it["text"] for it in x["items"]] == s["motion_alt"]["item_texts"]
            assert x["context"]["images"] == s["context"]["images"] and x["key"] == s["key"]
        else:
            assert x is s
    assert not any(s["context"]["text"].endswith(T.MOTION_UNKNOWN) for s in smp)  # samples are not modified
    rate = np.mean([x["context"]["text"].endswith(T.MOTION_UNKNOWN) for st in range(200)
                    for x in T.motion_dropout(smp, st, 0)])
    assert abs(rate - T.MOTION_DROPOUT) < 0.03
    assert all(x is s for x, s in zip(T.motion_dropout(smp, 5, 0, p=0.0), smp))


def test_transition_flags_within_next_three_steps():
    lab = [{"dir_xy": "none_xy", "dir_z": "none_z", "mag_coarse": "tiny"}] * 6
    lab = [dict(x) for x in lab]
    lab[4]["dir_z"] = "up"
    snap, per_q = T.transition_flags(lab, 0)
    assert snap is False and per_q == {"dir_xy": False, "dir_z": False, "mag_coarse": False}
    snap, per_q = T.transition_flags(lab, 1)  # k+3 = 4 changes dir_z
    assert snap is True and per_q["dir_z"] is True and per_q["dir_xy"] is False
    assert T.transition_flags(lab, 4) == (True, {"dir_xy": False, "dir_z": True, "mag_coarse": False})
    assert T.transition_flags(lab, 5)[0] is False  # nothing after the last frame


def test_layout_ids_are_new_versions():
    assert T.LAYOUT_SINGLE == D.CAMERA_LAYOUT == "D27v1"
    assert T.LAYOUT_VIDEO2 == "D27v2-video2" and T.MOTION_VER == "se2e-motion@v1"
