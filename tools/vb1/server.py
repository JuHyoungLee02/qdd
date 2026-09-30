"""E-VB1 pi0.5 policy server (GARO lerobot venv; one GPU, not a render card). Internal baseline only (user-log 227).
POST /act  body = npz {head: uint8 JPEG bytes, wrist: uint8 JPEG bytes, state: float32[11], task: str}
           -> npz {action: float32[50, 8] absolute (arm joint commands 7 + gripper width), ckpt: str}
GET  /info -> JSON {ckpt, model_path, n}
Pre / post processing = the checkpoint's own saved pipelines (normaliser with the training-set stats, relative ->
absolute actions, tokeniser; feedback_eval_norm_stats_trainset): make_pre_post_processors(pretrained_path=...).
Images are decoded from the same JPEG the recorder wrote (head half resolution, q90), channels-first in [0, 1].
  python server.py --model-path <ckpt>/pretrained_model --ckpt 20000 --port 8151"""
import argparse
import io
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np
import torch
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("--model-path", required=True)
ap.add_argument("--ckpt", required=True)
ap.add_argument("--port", type=int, default=8161)
ap.add_argument("--seed", type=int, default=1000)
a = ap.parse_args()

from lerobot.policies.factory import make_pre_post_processors  # noqa: E402
from lerobot.policies.pi05.modeling_pi05 import PI05Policy  # noqa: E402

torch.manual_seed(a.seed)
torch.cuda.manual_seed_all(a.seed)
pol = PI05Policy.from_pretrained(a.model_path)
pol.config.device = "cuda"
pol.to("cuda")
pol.eval()
pre, post = make_pre_post_processors(policy_cfg=pol.config, pretrained_path=a.model_path,
                                     preprocessor_overrides={"device_processor": {"device": "cuda"}})
LOCK = threading.Lock()
N = [0]


def _img(b: np.ndarray) -> torch.Tensor:
    x = np.asarray(Image.open(io.BytesIO(b.tobytes())).convert("RGB"))
    return torch.from_numpy(np.ascontiguousarray(x)).permute(2, 0, 1).float() / 255.0


def infer(head, wrist, state, task) -> np.ndarray:
    d = {"observation.images.top": _img(head), "observation.images.wrist_right": _img(wrist),
         "observation.state": torch.as_tensor(np.asarray(state, np.float32)), "task": str(task)}
    with LOCK:
        b = pre(d)
        with torch.no_grad():
            pred = pol.predict_action_chunk(b)
        out = post(pred)
    out = out[0] if out.dim() == 3 else out
    return out.float().cpu().numpy().astype(np.float32)


class H(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, body: bytes, ctype="application/octet-stream"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send(200, json.dumps({"ckpt": a.ckpt, "model_path": a.model_path, "n": N[0]}).encode(),
                   "application/json")

    def do_POST(self):
        try:
            z = np.load(io.BytesIO(self.rfile.read(int(self.headers["Content-Length"]))))
            t0 = time.time()
            act = infer(z["head"], z["wrist"], z["state"], str(z["task"]))
            N[0] += 1
            if N[0] % 50 == 1:
                print(f"[server] #{N[0]} {1000 * (time.time() - t0):.0f} ms act0={act[0].round(3).tolist()}", flush=True)
            b = io.BytesIO()
            np.savez(b, action=act, ckpt=np.array(a.ckpt))
            self._send(200, b.getvalue())
        except Exception as ex:  # noqa: BLE001
            self._send(500, repr(ex).encode(), "text/plain")


if __name__ == "__main__":
    h0 = io.BytesIO()
    Image.fromarray(np.zeros((188, 336, 3), np.uint8)).save(h0, "JPEG")
    w0 = io.BytesIO()
    Image.fromarray(np.zeros((240, 424, 3), np.uint8)).save(w0, "JPEG")
    t0 = time.time()
    act = infer(np.frombuffer(h0.getvalue(), np.uint8), np.frombuffer(w0.getvalue(), np.uint8), np.zeros(11), "warmup")
    print(f"[server] warmup {time.time() - t0:.1f} s action {act.shape}", flush=True)
    srv = ThreadingHTTPServer(("0.0.0.0", a.port), H)
    print(f"[server] READY port {a.port} ckpt {a.ckpt}", flush=True)
    srv.serve_forever()
