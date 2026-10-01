"""E-LIB0: warm up an openpi policy server (the first infer JIT-compiles for minutes on the CPU-poor x3 pod, longer than
the websocket keepalive of the official client) with keepalive off and a dummy LIBERO observation; prints the time.
usage: warmup_pi.py <host> <port>"""
import sys
import time

import numpy as np
import websockets.sync.client
from openpi_client import msgpack_numpy

host, port = sys.argv[1], int(sys.argv[2])
t0 = time.time()
ws = websockets.sync.client.connect(f"ws://{host}:{port}", compression=None, max_size=None, ping_interval=None,
                                    open_timeout=600)
meta = msgpack_numpy.unpackb(ws.recv())
pk = msgpack_numpy.Packer()
obs = {"observation/image": np.zeros((224, 224, 3), np.uint8), "observation/wrist_image": np.zeros((224, 224, 3), np.uint8),
       "observation/state": np.zeros(8, np.float32), "prompt": "warm up"}
for i in range(2):
    t1 = time.time()
    ws.send(pk.pack(obs))
    r = ws.recv(timeout=3600)
    out = msgpack_numpy.unpackb(r) if isinstance(r, bytes) else r
    print("infer", i, round(time.time() - t1, 1), "s", np.asarray(out["actions"]).shape if isinstance(out, dict) else out[:200], flush=True)
ws.close()
print("WARM_OK", round(time.time() - t0, 1))
