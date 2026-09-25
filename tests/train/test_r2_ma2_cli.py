"""E-MA2 (prereg_ma2): CLI wrapper = stageb_train when the option is off; with --ma2 the r2 loader and prompt_config
are patched (torch needed: pod / torch environments)."""
import os

import pytest

torch = pytest.importorskip("torch")

from harvest.train import r2_ma2 as M  # noqa: E402
from harvest.train import stageb_train as T  # noqa: E402

OPT = ("ma2", "ma2_root")


def test_cli_without_the_option_is_stageb_train():
    for cmd in (["train", "--run", "a"], ["predict", "--ckpt", "c", "--out", "o"], ["evalck", "--ckpt", "c"]):
        a = M.build_parser().parse_args(cmd)
        b = T.build_parser().parse_args(cmd)
        assert a.ma2 == "off" and {k: v for k, v in vars(a).items() if k not in OPT} == vars(b)
    saved = (T._load_data, T.prompt_config)
    M.install(T, M.build_parser().parse_args(["train", "--run", "a"]))
    assert (T._load_data, T.prompt_config) == saved


def test_install_needs_r2(monkeypatch):
    monkeypatch.setattr(T, "_load_data", T._load_data)
    monkeypatch.setattr(T, "prompt_config", T.prompt_config)
    with pytest.raises(SystemExit):
        M.install(T, M.build_parser().parse_args(["train", "--run", "a", "--ma2", "c1", "--data", "se2e"]))


def test_install_patches_loader_and_prompt_config(monkeypatch, tmp_path):
    ims = [["head camera:", "/v/standard/mug_tray/P0/img/ep10001/f0030_cam_head.jpg"],
           ["right wrist camera (active arm):", "/v/standard/mug_tray/P0/img/ep10001/f0030_cam_wrist_right.jpg"]]
    s = {"key": "P0_ep10001_k30", "items": [{"question": "dir_xy", "text": "t\nQ", "images": ims, "target": ["plus_y"]}],
         "context": {"text": "t", "images": ims}, "committed": {"dir_xy": "plus_y"}}

    def fake_load(args):
        return [s], 30, [s], []
    monkeypatch.setattr(T, "_load_data", fake_load)
    monkeypatch.setattr(T, "prompt_config", lambda *x, **k: {"camera": ["x"], "sha": "old"})
    os.makedirs(tmp_path / "cmd")
    (tmp_path / "cmd" / "standard_mug_tray_P0.jsonl").write_text(
        '{"id": "standard/mug_tray/P0/ep10001/k30", "cmd": [0.03, 0.0, 0.0], "give": true}\n')
    a = M.build_parser().parse_args(["train", "--run", "a", "--ma2", "c1", "--data", "r2", "--pool",
                                     "/v/standard/mug_tray/P0", "--ma2-root", str(tmp_path)])
    M.install(T, a)
    ss, _, tr, va = T._load_data(a)
    assert ss[0]["context"]["text"].endswith(M.cmd_line([0.03, 0.0, 0.0])) and tr[0] is ss[0] and va == []
    assert ss[0]["items"][0]["target"] == ["plus_x"] and s["items"][0]["target"] == ["plus_y"]
    cfg = T.prompt_config()
    assert cfg["ma2"] == M.MA2_VER and cfg["ma2_cond"] == "c1" and cfg["sha"] != "old"


def test_ma2eval_parser():
    a = M.build_parser().parse_args(["ma2eval", "--ckpt", "c", "--ma2", "c2", "--eval-set", "e", "--out", "o",
                                     "--data", "r2", "--pool", "p"])
    assert a.cmd == "ma2eval" and a.steps == 10 and a.urdf == M.URDF
