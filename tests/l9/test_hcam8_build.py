import importlib.util
import json
import os

import pytest

from harvest.teach_pt import dataset as DS

_P = os.path.join(os.path.dirname(__file__), "..", "..", "tools", "l9r", "hcam8_build.py")
_spec = importlib.util.spec_from_file_location("hcam8_build", _P)
HB = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(HB)


def test_l9_split_seed_check_and_old_splits_unchanged():
    DS._check(1_234_567, "l9train")
    DS._check(71_234_567, "l9eval_hold")
    with pytest.raises(ValueError):
        DS._check(12345, "l9train")
    DS._check(12345, "train")
    with pytest.raises(ValueError):
        DS._check(1_234_567, "train")


def test_add_line_once_after_the_cameras_header():
    t = "X\nCAMERAS (directions are unit vectors in the robot frame)\n- Image 1: head camera, ...\n"
    out = HB.add_line(t, "camera: head, unknown; source: x")
    assert out.splitlines()[2] == "- camera: head, unknown; source: x" and out.splitlines()[3].startswith("- Image 1")
    assert HB.add_line(out, "camera: head, unknown; source: x") == out
    with pytest.raises(ValueError):
        HB.add_line("no header", "camera: x")


def _ep(root, fam, name, **m):
    d = os.path.join(root, "train", fam, name)
    os.makedirs(d)
    meta = dict(gen="l9", success=True, max_dq_rad=0.02, motion_version="l9m-2", robot="ffw_sg2", env_family=fam)
    meta.update(m)
    json.dump(meta, open(os.path.join(d, "meta.json"), "w"))


def test_select_stratified_and_matched(tmp_path):
    r = str(tmp_path)
    for i in range(6):
        _ep(r, "shelf", f"a_s{i}_right", seed=100 + i, task_id="a", arm="right")
    for i in range(2):
        _ep(r, "shelf", f"b_s{i}_left", seed=200 + i, task_id="b", arm="left")
    _ep(r, "shelf", "b_s9_left", seed=209, task_id="b", arm="left", success=False)
    _ep(r, "shelf", "c_s1_right", seed=300, task_id="c", arm="right",
        head_cam={"draw": {"mode": "rand"}})
    eps, info = HB.select([r], "std", 6)
    assert info["n"] == 6 and Counter_of(eps) == {("a", "right"): 4, ("b", "left"): 2}
    rand, _ = HB.select([r], "rand", 6)
    assert [e["def"] for e in rand] == ["c"]
    none, info = HB.select([r], "rand", 6, match=eps)
    assert none is None and "a/right" in info["short_strata"]
    same, _ = HB.select([r], "std", 0, match=eps)
    assert Counter_of(same) == Counter_of(eps)


def Counter_of(eps):
    from collections import Counter
    return dict(Counter((e["def"], e["arm"]) for e in eps))
