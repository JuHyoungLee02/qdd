"""E-JV1 arm B HTTP server: the same /act protocol as harvest.jcr.serve (client = harvest.jcr.serve.Client), so the
JCR executor runs arm B unchanged. Extra answer fields: c_hat (waypoint xyz), text, parse_ok; a malformed answer is
returned as {"error": "parse ..."} (the executor then holds still and counts it).
  python -m harvest.jv1.serve --ckpt /data/harvest/ckpt/jv1/b_P/last --port 8171"""
from __future__ import annotations

import argparse
import base64
import json
import os
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL_DIR = "/data/harvest/models/Qwen3-VL-4B-Instruct"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--port", type=int, default=8171)
    a = ap.parse_args(argv)
    from .model import load
    m, _ = load(a.ckpt, MODEL_DIR, "cuda")
    lock = threading.Lock()
    tmp = tempfile.mkdtemp(prefix="jv1_srv_", dir=os.environ.get("TMPDIR"))

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
            self._send({"ckpt": a.ckpt, "ok": True, "arm": "B"})

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
                    out = m.predict(None, ims, [req["sample"]], "cuda")[0]
                out["latency_s"] = time.perf_counter() - t0
                if not out.get("parse_ok"):
                    out["error"] = "parse " + out.get("text", "")[:80]
                self._send(out)
            except Exception as ex:  # noqa: BLE001
                self._send({"error": repr(ex)}, 500)

    print(f"SERVING {a.ckpt} :{a.port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", a.port), H).serve_forever()


if __name__ == "__main__":
    main()
