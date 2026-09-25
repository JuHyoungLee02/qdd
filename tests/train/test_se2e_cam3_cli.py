"""E-CAM3 (prereg_cam3): CLI wrapper = stageb_train when the option is off; with --cam3 the loader / prompt_config
are patched; three-image samples go through the shared (R3) prefix path exactly like the per-context path (tiny
Qwen3-VL, pod only for the last test)."""
import os

import pytest

torch = pytest.importorskip("torch")

from harvest.train import se2e_cam3 as C  # noqa: E402
from harvest.train import stageb_train as T  # noqa: E402

MODEL = os.environ.get("STAGEA_BASE", "/data/harvest/models/Qwen3-VL-4B-Instruct")


def test_cli_without_the_option_is_stageb_train():
    for cmd in (["train", "--run", "a"], ["predict", "--ckpt", "c", "--out", "o"], ["evalck", "--ckpt", "c"]):
        a = C.build_parser().parse_args(cmd)
        b = T.build_parser().parse_args(cmd)
        assert a.cam3 == "off" and {k: v for k, v in vars(a).items() if k not in ("cam3", "cam3_root")} == vars(b)
    saved = (T._load_data, T.prompt_config_t)
    C.install(T, C.build_parser().parse_args(["train", "--run", "a"]))
    assert (T._load_data, T.prompt_config_t) == saved


def test_install_needs_se2e_and_the_motion_line(monkeypatch):
    monkeypatch.setattr(T, "_load_data", T._load_data)
    monkeypatch.setattr(T, "prompt_config_t", T.prompt_config_t)
    with pytest.raises(SystemExit):
        C.install(T, C.build_parser().parse_args(["train", "--run", "a", "--cam3", "cam3@v1"]))
    with pytest.raises(SystemExit):
        C.install(T, C.build_parser().parse_args(["train", "--run", "a", "--cam3", "cam3@v1", "--data", "se2e"]))


def test_install_patches_loader_and_prompt_config(monkeypatch, tmp_path):
    calls = {}

    def fake_load(args):
        s = {"key": "RB1_ep1_k2", "arm": "right", "items": [],
             "context": {"text": "t", "images": [["head camera:", "h"], ["right wrist camera (active arm):", "w"]]}}
        calls["n"] = 1
        return [s], 10, [s], []
    monkeypatch.setattr(T, "_load_data", fake_load)
    monkeypatch.setattr(T, "prompt_config_t", lambda *x, **k: {"camera": ["x"], "sha": "old"})
    p = tmp_path / C.frame_rel("RB1", 1, 2, "cam_wrist_left")
    os.makedirs(p.parent)
    p.write_bytes(b"x")
    a = C.build_parser().parse_args(["train", "--run", "a", "--cam3", "cam3@v1", "--data", "se2e", "--motion-line",
                                     "se2e-motion@v1", "--cam3-root", str(tmp_path)])
    C.install(T, a)
    ss, _, _, _ = T._load_data(a)
    assert calls["n"] == 1 and len(ss[0]["context"]["images"]) == 3
    cfg = T.prompt_config_t()
    assert cfg["cam3"] == C.CAM3_VER and cfg["sha"] != "old"


@pytest.mark.skipif(not os.path.exists(os.path.join(MODEL, "preprocessor_config.json")), reason="pod only")
def test_three_images_shared_path_equals_per_context_path(tmp_path):
    pytest.importorskip("peft")
    from harvest.train import stageb_data as D
    from harvest.train import stageb_model as M
    ss = D.synthetic_rows(3, seed=1, img_dir=str(tmp_path / "img"))
    from PIL import Image
    import numpy as np
    for i, s in enumerate(ss):
        w = tmp_path / f"o{i}.jpg"
        Image.fromarray((np.random.default_rng(i).random((240, 424, 3)) * 255).astype("uint8")).save(w, quality=90)
        ims = [list(x) for x in s["context"]["images"]] + [["left wrist camera (other arm):", str(w)]]
        s["context"]["images"] = ims
        for it in s["items"]:
            it["images"] = ims
    bb, proc, hd = T.load_backbone("tiny", MODEL, torch.device("cpu"), lora={"r": 4, "alpha": 8, "dropout": 0.0})
    m = M.new_model(bb, ss, hd, expert_kw={"width": 32, "depth": 2, "heads": 4},
                    aux_kw={"width": 32, "heads": 4, "queries": 2}).eval()
    enc = M.HFEncoder(proc)
    with torch.no_grad():
        c0, k0 = m.contexts(ss, enc, "cpu", grad=False)
        c1, k1, _ = m.forward_shared(ss, enc, "cpu", grad=False)
    assert torch.equal(k0, k1)
    assert float((c0 - c1).abs().max()) <= 1e-4 * float(c0.abs().max())
