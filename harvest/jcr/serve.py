"""JCR HTTP server + client (one model per process, one request at a time). venv_train on a JCR card (x2 GPU0 / x3 GPU0).
  python -m harvest.jcr.serve --ckpt /data/harvest/ckpt/jcr/jcr1_0/last --port 8161
POST /act  {"sample": {features.cond_vec fields}, "head": <b64 jpeg>, "wrist": <b64 jpeg>, "seed": int}
     -> {"delta": [H][3] m, "event_p": [N_EVENT], "contact_p", "anomaly_p": [6], "latency_s"}
GET /health -> {"ckpt", "ok"}"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL_DIR = "/data/harvest/models/Qwen3-VL-4B-Instruct"


def jpeg_b64(img) -> str:
    from PIL import Image
    import numpy as np
    b = io.BytesIO()
    Image.fromarray(np.asarray(img)[..., :3].astype("uint8")).save(b, format="JPEG", quality=90)
    return base64.b64encode(b.getvalue()).decode()


class Client:
    def __init__(self, url: str, timeout_s: float = 30.0):
        self.url, self.timeout = url.rstrip("/"), timeout_s

    def act(self, sample: dict, head, wrist, seed: int = 0) -> dict:
        body = json.dumps({"sample": sample, "head": jpeg_b64(head), "wrist": jpeg_b64(wrist), "seed": seed}).encode()
        req = urllib.request.Request(self.url + "/act", data=body, headers={"Content-Type": "application/json"})
        t0 = time.perf_counter()
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            out = json.loads(r.read())
        out["rtt_s"] = time.perf_counter() - t0
        return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--port", type=int, default=8161)
    ap.add_argument("--steps", type=int, default=10)
    a = ap.parse_args(argv)
    import tempfile

    from .model import load
    m, enc = load(a.ckpt, MODEL_DIR, "cuda")
    lock = threading.Lock()
    tmp = tempfile.mkdtemp(prefix="jcr_srv_")

    class H(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, obj, code=200):
            b = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            self._send({"ckpt": a.ckpt, "ok": True})

        def do_POST(self):
            try:
                req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                t0 = time.perf_counter()
                with lock:
                    ims = []
                    for k, lab in (("head", "head camera"), ("wrist", "right wrist camera")):
                        p = os.path.join(tmp, f"{k}.jpg")
                        with open(p, "wb") as f:
                            f.write(base64.b64decode(req[k]))
                        ims.append([lab, p])
                    out = m.predict(enc, ims, [req["sample"]], "cuda", steps=a.steps, seed=int(req.get("seed", 0)))[0]
                out["latency_s"] = time.perf_counter() - t0
                self._send(out)
            except Exception as ex:  # noqa: BLE001
                self._send({"error": repr(ex)}, 500)

    print(f"SERVING {a.ckpt} :{a.port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", a.port), H).serve_forever()


if __name__ == "__main__":
    main()
