"""E-MA3 (prereg_ma3): tools/ma3/chunk_eval.evaluate_records == stageb_train.evaluate() (summary bit for bit, item
records as predict writes them) for a default and a kvcond@v1 model (tiny Qwen3-VL, pod only)."""
import os
import sys

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("peft")
MODEL = os.environ.get("STAGEA_BASE", "/data/harvest/models/Qwen3-VL-4B-Instruct")
if not os.path.exists(os.path.join(MODEL, "preprocessor_config.json")):
    pytest.skip("pod only", allow_module_level=True)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools", "ma3"))
import chunk_eval as CE  # noqa: E402

from harvest.train import se2e_kvcond as K  # noqa: E402
from harvest.train import stageb_data as D  # noqa: E402
from harvest.train import stageb_model as M  # noqa: E402
from harvest.train import stageb_train as T  # noqa: E402


@pytest.mark.parametrize("kv", [False, True])
def test_records_reproduce_evaluate(tmp_path, kv):
    ss = D.synthetic_rows(6, seed=2, img_dir=str(tmp_path / "img"))
    bb, proc, hd = T.load_backbone("tiny", MODEL, torch.device("cpu"), lora={"r": 4, "alpha": 8, "dropout": 0.0})
    torch.manual_seed(0)
    m = M.new_model(bb, ss, hd, expert_kw={"width": 32, "depth": 2, "heads": 4},
                    aux_kw={"width": 32, "heads": 4, "queries": 2})
    if kv:
        m = K.with_kvcond(m)
    m.shared = True
    enc = M.HFEncoder(proc)
    val = ss[:4]
    recs = []
    ev = T.evaluate(m, enc, val, torch.device("cpu"), 0, records=recs)
    summ, items, chunks = CE.evaluate_records(m, enc, val, torch.device("cpu"), 0)
    assert summ == ev
    assert items == recs
    assert [c["key"] for c in chunks] == [s["key"] for s in val]
    assert sum(c["mse_n"] for c in chunks) / len(chunks) == ev["sample_mse_norm"]
    assert all(c["mse_pred"] >= 0 for c in chunks)
