"""E-MA1b (prereg_ma1b): stageb_train OPT-IN `--aux-extra a3d@v1` wiring -- parser, resume keys, prompt_config marker
(default runs unchanged), target attachment, head replacement in the model built for training."""
import json

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from harvest.train import se2e_trace_model as TM  # noqa: E402
from harvest.train import stageb_data as D  # noqa: E402
from harvest.train import stageb_model as M  # noqa: E402
from harvest.train import stageb_train as T  # noqa: E402

from .test_stageb_torch import AK, EK, HID, MockBackbone  # noqa: E402


def test_parser_defaults_and_options():
    for cmd in (["train", "--run", "a"], ["predict", "--ckpt", "c", "--out", "o"], ["evalck", "--ckpt", "c"]):
        a = T.build_parser().parse_args(cmd)
        assert a.aux_extra == "none"
        b = T.build_parser().parse_args(cmd + ["--aux-extra", "a3d@v1", "--a3d-root", "/x"])
        assert b.aux_extra == "a3d@v1" and b.a3d_root == "/x"
    with pytest.raises(SystemExit):
        T.build_parser().parse_args(["train", "--run", "a", "--aux-extra", "trace9"])


def test_resume_keys():
    assert "aux_extra" in T.RESUME_KEYS and "a3d_root" in T.RESUME_KEYS


def _samples():
    ss = D.synthetic_rows(4, seed=0)
    for s in ss:
        s["context"]["images"] = [["head camera:", "h.jpg"]]
    return ss


def test_prompt_config_unchanged_without_aux_and_marked_with_it():
    ss = _samples()
    base = T.prompt_config_t(ss, "IMG", "D27v1", {"version": "se2e-motion@v1"})
    again = T.prompt_config_t(ss, "IMG", "D27v1", {"version": "se2e-motion@v1"}, aux=None)
    assert base == again and "aux" not in base
    marked = T.prompt_config_t(ss, "IMG", "D27v1", {"version": "se2e-motion@v1"}, aux="a3d@v1")
    assert marked["aux"] == "a3d@v1" and marked["sha"] != base["sha"]
    assert set(T.AUX_FILES) <= set(marked["files_sha"]) and not set(T.AUX_FILES) & set(base["files_sha"])
    assert marked["camera"] == base["camera"] and marked["layout"] == base["layout"]


def test_attach_aux_targets(tmp_path):
    ss = [{"key": "RB1_ep0_k0"}, {"key": "RB2_ep3_k5"}]
    for kind, key in (("RB1", "RB1_ep0_k0"), ("RB2", "RB2_ep3_k5")):
        (tmp_path / f"{kind}.a3d.jsonl").write_text(json.dumps({"key": key, "d": [0.01] * 12, "mask": [1] * 4}) + "\n")
    a = T.build_parser().parse_args(["train", "--run", "a", "--aux-extra", "a3d@v1", "--a3d-root", str(tmp_path)])
    T.attach_aux_targets(a, ss)
    assert all(s["a3d"]["mask"] == [1] * 4 for s in ss)
    a0 = T.build_parser().parse_args(["train", "--run", "a"])
    s2 = [{"key": "RB1_ep0_k0"}]
    T.attach_aux_targets(a0, s2)
    assert "a3d" not in s2[0]


def test_aux_model_switch():
    ss = D.synthetic_rows(6, seed=0)
    for s in ss:
        s["aux"] = {"reg": {}, "cls": {}}
    torch.manual_seed(0)
    m = M.new_model(MockBackbone(0), ss, HID, expert_kw=EK, aux_kw=AK)
    a = T.build_parser().parse_args(["train", "--run", "a", "--aux-extra", "a3d@v1"])
    m = T.aux_model(a, m, new=True)
    assert isinstance(m, TM.StageBTrace) and m.aux.cfg.n_reg == len(D.AUX_REG) + 12
    a0 = T.build_parser().parse_args(["train", "--run", "a"])
    m0 = M.new_model(MockBackbone(0), ss, HID, expert_kw=EK, aux_kw=AK)
    assert T.aux_model(a0, m0, new=True) is m0 and type(m0) is M.StageB
    # a reloaded a3d checkpoint: predict in the trained view, or --aux-view base (runtime path)
    m2 = M.new_model(MockBackbone(0), ss, HID, expert_kw=EK, aux_kw={**AK})
    m2.aux = TM.TraceAuxHead(m.aux.cfg)
    m2 = T.aux_model(a, m2, new=False)
    assert isinstance(m2, TM.StageBTrace)
    assert np.array_equal(T.AUX_CHOICES, ("none", "a3d@v1"))
