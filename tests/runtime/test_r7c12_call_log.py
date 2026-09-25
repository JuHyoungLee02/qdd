"""R7 cycle 12 D4: call rows carry the E §1.6 / canon §28 A6 fields -- per-question option probabilities, the raw
request and raw response (content-addressed blobs: the request blob is exactly the body `request_sha256` hashes),
Astra request text + raw output_text + max tokens + effort, the Astra image original. Canon §77."""
import hashlib
import json

import numpy as np

from harvest.runtime.astra_hb import EFFORT, MAX_OUT, MockAstra
from harvest.runtime.core import OursRuntime, RuntimeConfig
from harvest.runtime.models import MockFusedModel, MockSelector

from .fakeworld import FakeWorld


def _run(backend, model, ticks=400):
    cfg = RuntimeConfig(backend=backend, clock="simlat", astra_mode="mock", hb_N_s=1.0)
    rt = OursRuntime(cfg, model, astra=MockAstra(1.0))
    rt.reset()
    w = FakeWorld()
    for i in range(ticks):
        o = w.obs()
        if i % 10 == 0:
            o["images"] = {"cam_head": np.full((8, 8, 3), i % 251, np.uint8)}
        a, _ = rt.act(o)
        w.step(a)
    rt.close()
    return rt


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def test_decision_rows_log_probabilities_and_raw_request_response_blobs():
    for backend, model in (("modular", MockSelector(latency_s=0.30)), ("fused", MockFusedModel(latency_s=0.30))):
        rt = _run(backend, model)
        assert rt.calls
        for c in rt.calls:
            assert set(c["probs"]) == set(c["answers"])
            for q, p in c["probs"].items():
                assert isinstance(p, dict) and abs(sum(p.values()) - 1.0) < 1e-6 and c["answers"][q][0] in p
            ext, body = rt.blobs[c["request_sha256"]]
            assert ext == "json" and _sha(body) == c["request_sha256"] == c["request_blob"]
            req = json.loads(body)
            assert req["payload"]["req"]["state"].split("\n")[-1].startswith("last_step: ")
            assert set(req["images"]) == set(c["image_sha256"])
            ext, rb = rt.blobs[c["response_blob"]]
            assert ext == "json" and _sha(rb) == c["response_blob"] and json.loads(rb)


def test_astra_rows_log_request_text_raw_output_max_tokens_and_the_image():
    rt = _run("modular", MockSelector(latency_s=0.30))
    rows = [a for a in rt.astra_log if "decision" in a]
    assert rows
    for a in rows:
        assert a["max_output_tokens"] == MAX_OUT and a["effort"] == EFFORT
        assert isinstance(a["output_text"], str) and a["output_text"]
        ext, body = rt.blobs[a["request_blob"]]
        assert _sha(body) == a["request_sha256"] == a["request_blob"]
        texts = [c["text"] for m in json.loads(body)["payload"]["input"] for c in m["content"]
                 if c.get("type") == "input_text"]
        assert texts and "premise_epoch" in texts[0]
        for cam, h in a["image_sha256"].items():
            ext, img = rt.blobs[h]
            assert ext == "jpg" and _sha(img) == h


def test_blobs_are_written_once_by_content_hash(tmp_path):
    from harvest.runtime.ir_policy import write_blobs
    blobs = {_sha(b"x"): ("json", b"x"), _sha(b"y"): ("jpg", b"y")}
    n = write_blobs(str(tmp_path), blobs)
    assert n == 2 and (tmp_path / "blobs" / f"{_sha(b'x')}.json").read_bytes() == b"x"
    assert write_blobs(str(tmp_path), blobs) == 0  # already there
