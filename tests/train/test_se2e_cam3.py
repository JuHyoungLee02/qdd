"""E-CAM3 (docs/stage3/prereg_cam3.md): OPT-IN head + BOTH wrists input on S-E2E samples (pure part, no torch)."""
import os

import pytest

from harvest.train import se2e_cam3 as C


def _sample(arm="right", both=False, key="RB2_ep7_k30"):
    ims = [["head camera:", "/r/img/RB2/ep000007/k0030_cam_head.jpg"]]
    if both:
        ims += [["right wrist camera (active arm):", "/r/w_r.jpg"], ["left wrist camera (active arm):", "/r/w_l.jpg"]]
    else:
        ims += [[f"{arm} wrist camera (active arm):", f"/r/img/RB2/ep000007/k0030_cam_wrist_{arm}.jpg"]]
    its = [{"question": q, "text": "ctx\n" + q, "images": ims} for q in ("dir_xy", "dir_z", "mag_coarse")]
    return {"key": key, "arm": arm, "context": {"text": "ctx", "images": ims}, "items": its}


def test_frame_rel_path_layout():
    assert C.frame_rel("RB1", 12, 5, "cam_wrist_left") == "img_cam3/RB1/ep000012/k0005_cam_wrist_left.jpg"


def test_other_wrist_of_a_single_arm_sample_and_none_for_bimanual():
    assert C.other_wrist(_sample("right")) == "cam_wrist_left"
    assert C.other_wrist(_sample("left")) == "cam_wrist_right"
    assert C.other_wrist(_sample(both=True)) is None


def test_key_parts():
    assert C.key_parts("RB1_ep12_k305") == ("RB1", 12, 305)


def test_apply_appends_the_other_wrist_after_the_unchanged_head_and_active_wrist(tmp_path):
    s = _sample("right")
    before = [list(x) for x in s["context"]["images"]]
    p = tmp_path / C.frame_rel("RB2", 7, 30, "cam_wrist_left")
    os.makedirs(p.parent)
    p.write_bytes(b"x")
    st = C.apply_cam3([s], str(tmp_path))
    ims = s["context"]["images"]
    assert ims[:2] == before
    assert ims[2][0] == "left wrist camera (other arm):" and os.path.normpath(ims[2][1]) == os.path.normpath(str(p))
    assert all(it["images"] == ims for it in s["items"])
    assert st == {"n": 1, "added": 1, "bimanual_unchanged": 0}


def test_apply_leaves_bimanual_samples_unchanged(tmp_path):
    s = _sample(both=True)
    before = [list(x) for x in s["context"]["images"]]
    st = C.apply_cam3([s], str(tmp_path))
    assert s["context"]["images"] == before and st["bimanual_unchanged"] == 1


def test_apply_refuses_a_missing_frame(tmp_path):
    with pytest.raises(FileNotFoundError):
        C.apply_cam3([_sample("left")], str(tmp_path))


def test_apply_refuses_when_the_active_wrist_label_disagrees_with_the_arm(tmp_path):
    s = _sample("right")
    s["arm"] = "left"
    with pytest.raises(ValueError):
        C.apply_cam3([s], str(tmp_path))


def test_mark_prompt_config_adds_the_marker_and_changes_the_sha():
    cfg = {"camera": ["D27v1:head camera:"], "state": "IMG", "sha": "abc"}
    m = C.mark_prompt_config(cfg)
    assert m["cam3"] == C.CAM3_VER and m["layout3"] == C.LAYOUT_CAM3 and "harvest/train/se2e_cam3.py" in m["cam3_files_sha"]
    assert m["sha"] != cfg["sha"] and cfg == {"camera": ["D27v1:head camera:"], "state": "IMG", "sha": "abc"}
