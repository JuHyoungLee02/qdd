"""prereg_se2e_temporal on the real Qwen3-VL processor (pod only): video2 pair packing = the Qwen3-VL video
processor on [t - 0.3 s, t] with the SAME visual token count as one still image; option off = the baseline encoder /
forward bit for bit; the shared (R3) path equals the old per-context path for pairs; stageb_train defaults unchanged.
"""
import math
import os

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")
pytest.importorskip("peft")

MODEL = os.environ.get("STAGEA_BASE", "/data/harvest/models/Qwen3-VL-4B-Instruct")
if not os.path.exists(os.path.join(MODEL, "preprocessor_config.json")):
    pytest.skip("Qwen3-VL processor files not present (pod only)", allow_module_level=True)

from harvest.train import prefix_share as P  # noqa: E402
from harvest.train import se2e_temporal as T  # noqa: E402
from harvest.train import se2e_temporal_model as TM  # noqa: E402
from harvest.train import stageb_data as D  # noqa: E402
from harvest.train.stageb_model import HFEncoder  # noqa: E402

REL = 1e-4


def _img(path, w, h, seed):
    from PIL import Image
    Image.fromarray((np.random.default_rng(seed).random((h, w, 3)) * 255).astype("uint8")).save(path, quality=90)
    return str(path)


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    from transformers import AutoProcessor
    d = tmp_path_factory.mktemp("se2e_t")
    proc = AutoProcessor.from_pretrained(MODEL)
    fr = {n: _img(d / f"{n}.jpg", *wh, s) for s, (n, wh) in enumerate(
        {"h0": (672, 376), "h1": (672, 376), "w0": (424, 240), "w1": (424, 240)}.items())}
    single = [["head camera:", fr["h1"]], ["right wrist camera (active arm):", fr["w1"]]]
    pair = [[T.VIDEO_LABEL["cam_head"], fr["h1"], fr["h0"]],
            [T.VIDEO_LABEL["cam_wrist_right"], fr["w1"], fr["w0"]]]
    return proc, fr, single, pair


def test_single_entries_encode_exactly_like_the_baseline(env):
    proc, fr, single, _ = env
    enc_b, enc_v = HFEncoder(proc), TM.VideoEncoder(proc)
    g0 = P.encode_group(enc_b, ["state\nq1", "state\nq2"], single)
    g1 = TM.encode_group_v(enc_v, ["state\nq1", "state\nq2"], single)
    assert g0["rows"] == g1["rows"]
    assert torch.equal(g0["pixel_values"], g1["pixel_values"]) and torch.equal(g0["image_grid_thw"],
                                                                                g1["image_grid_thw"])
    x0, x1 = enc_b.inputs("state", single, "cpu"), enc_v.inputs("state", single, "cpu")
    assert x0.keys() == x1.keys() and all(torch.equal(x0[k], x1[k]) for k in x0)


def test_video2_pair_equals_the_video_processor_and_keeps_the_token_count(env):
    from PIL import Image
    proc, fr, single, pair = env
    enc = TM.VideoEncoder(proc)
    ps, pp = enc.pixels(single), enc.pixels(pair)
    assert torch.equal(ps["image_grid_thw"], pp["image_grid_thw"])
    merge = proc.image_processor.merge_size
    assert [int(g.prod()) // merge ** 2 for g in pp["image_grid_thw"]] == [252, 104]  # §59 native sizes
    n0 = 0
    for cam, (now, prev) in (("h", (fr["h1"], fr["h0"])), ("w", (fr["w1"], fr["w0"]))):
        vid = np.stack([np.asarray(Image.open(prev).convert("RGB")), np.asarray(Image.open(now).convert("RGB"))])
        xv = proc.video_processor(videos=[vid], return_tensors="pt", do_sample_frames=False)
        n = xv["pixel_values_videos"].shape[0]
        assert torch.equal(xv["pixel_values_videos"], pp["pixel_values"][n0:n0 + n]), cam  # [prev, now] clip
        assert xv["video_grid_thw"].tolist()[0] == pp["image_grid_thw"][0 if cam == "h" else 1].tolist()
        n0 += n
    # still image = the current frame twice; the pair differs only in the first temporal slice
    tps, ps_ = proc.image_processor.temporal_patch_size, proc.image_processor.patch_size
    a = ps["pixel_values"].view(n0, -1, tps, ps_ * ps_)
    b = pp["pixel_values"].view(n0, -1, tps, ps_ * ps_)
    assert torch.equal(a[:, :, 1], b[:, :, 1]) and not torch.equal(a[:, :, 0], b[:, :, 0])
    img = P._image_id(enc)
    g_s = TM.encode_group_v(enc, ["s"], single)["rows"][0]
    g_p = TM.encode_group_v(enc, ["s"], pair)["rows"][0]
    assert g_s.count(img) == g_p.count(img) == 356  # LLM visual tokens unchanged (252 + 104)


@pytest.fixture(scope="module")
def tiny(env):
    from harvest.train import stageb_model as M
    from harvest.train import stageb_train as TR
    proc, fr, single, pair = env
    bb, proc, hd = TR.load_backbone("tiny", MODEL, torch.device("cpu"), lora={"r": 4, "alpha": 8, "dropout": 0.0})
    with torch.no_grad():
        for n, p in bb.named_parameters():
            if "lora_B" in n:
                p.normal_(0, 0.3)
    ss = D.synthetic_rows(3, seed=1)
    for s, ims in zip(ss, (single, pair, single)):
        s["context"] = {"text": s["context"]["text"], "images": ims}
        for it in s["items"]:
            it["images"] = ims
    m = M.new_model(bb, ss, hd, expert_kw={"width": 32, "depth": 2, "heads": 4},
                    aux_kw={"width": 32, "heads": 4, "queries": 2}).eval()
    return m, proc, ss


def test_as_temporal_forward_equals_baseline_on_single_images(tiny):
    m, proc, ss = tiny
    one = [ss[0], ss[2]]
    with torch.no_grad():
        c0, k0, l0 = m.forward_shared(one, HFEncoder(proc), "cpu", grad=False)
        TM.as_temporal(m)
        try:
            c1, k1, l1 = m.forward_shared(one, TM.VideoEncoder(proc), "cpu", grad=False)
        finally:
            m.__class__ = TM.StageB
    assert torch.equal(k0, k1) and torch.equal(c0, c1)
    assert all(float(l0[i][j][n]) == float(l1[i][j][n]) for i in range(2) for j in range(len(l0[i])) for n in l0[i][j])


def test_video2_shared_path_equals_old_path(tiny):
    m, proc, ss = tiny
    enc = TM.VideoEncoder(proc)
    TM.as_temporal(m)
    try:
        with torch.no_grad():
            m.shared = False
            c0, k0 = m.contexts([ss[1]], enc, "cpu", grad=False)
            lp0 = [enc.logprobs(m.backbone, it, "cpu") for it in ss[1]["items"]]
            m.shared = True
            c1, k1, lps = m.forward_shared([ss[1]], enc, "cpu", grad=False)
    finally:
        m.__class__ = TM.StageB
        m.shared = True
    assert torch.equal(k0, k1)
    assert float((c0 - c1).abs().max()) <= REL * float(c0.abs().max())
    for old, new in zip(lp0, lps[0]):
        for n in old:
            assert math.isclose(float(old[n]), float(new[n]), rel_tol=REL, abs_tol=1e-6)


def test_stageb_train_defaults_unchanged_and_variant_config():
    from harvest.train import stageb_train as TR
    a = TR.build_parser().parse_args(["train", "--data", "se2e", "--run", "x"])
    assert TR.temporal_on(a) is False
    assert a.camera_layout == T.LAYOUT_SINGLE and a.motion_line == "none"
    b = TR.build_parser().parse_args(["train", "--data", "se2e", "--run", "x", "--camera-layout", T.LAYOUT_VIDEO2,
                                      "--motion-line", T.MOTION_VER, "--motion-bins", "b.json"])
    assert TR.temporal_on(b) is True
    ss = [{"context": {"text": "t", "images": [[T.VIDEO_LABEL["cam_head"], "n", "p"]]}}]
    base = TR.prompt_config([{"context": {"text": "t", "images": [["head camera:", "n"]]}}], "IMG")
    cfg = TR.prompt_config_t(ss, "IMG", T.LAYOUT_VIDEO2, {"version": T.MOTION_VER, "arm_speed": [1, 2],
                                                            "grip_rate": 0.1})
    assert cfg["layout"] == T.LAYOUT_VIDEO2 and cfg["motion"]["version"] == T.MOTION_VER
    assert set(cfg["files_sha"]) == set(base["files_sha"]) | {"harvest/train/se2e_temporal.py",
                                                              "harvest/train/se2e_temporal_model.py",
                                                              "harvest/train/se2e_data.py"}
    assert cfg["sha"] != base["sha"] and "motion" not in base and base["layout"] == "D27v1"


def test_train_loop_batch_fn_default_is_identity():
    import inspect

    from harvest.train import stageb_train as TR
    assert inspect.signature(TR.train_loop).parameters["batch_fn"].default is None
