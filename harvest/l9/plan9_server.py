"""L9 v2: cuRobo planner in its own process (pod).

Why: inside the Isaac Sim app the omni.warp.core extension loads warp 1.8.2 first; cuRobo v0.8.0 needs a newer warp
(wp.func(module=...) -> TypeError at import, smoke 10-02). One process cannot hold two warp versions, so the
collection process talks to a planner process that runs the plain Isaac python with /data/harvest/l9v2/pylib
(warp 1.14) over a multiprocessing.connection unix socket.

  server: /isaac-sim/python.sh -m harvest.l9.plan9_server <socket> <robot cfg json> <device>
  client: PlannerProxy(robot_cfg, device) -> same methods as plan9.Planner9 (world, grasp, pose, ik, line, attach,
          detach, joint_names, version)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

AUTH = b"l9v2-planner"
PYLIB = "/data/harvest/l9v2/pylib"


def serve(sock: str, cfg_path: str, device: str) -> None:
    from multiprocessing.connection import Listener
    from .plan9 import Planner9
    cfg = json.load(open(cfg_path))
    pl = Planner9(cfg, device=device)
    with Listener(sock, family="AF_UNIX", authkey=AUTH) as lst:
        print("PLANNER_READY", pl.version, flush=True)
        conn = lst.accept()
        while True:
            try:
                msg = conn.recv()
            except EOFError:
                break
            name, args, kw = msg
            if name == "_quit":
                conn.send(("ok", None))
                break
            try:
                if name in ("joint_names", "version"):
                    out = getattr(pl, name)
                else:
                    out = getattr(pl, name)(*args, **kw)
                conn.send(("ok", out))
            except Exception as e:  # noqa: BLE001  (reported to the client)
                import traceback
                conn.send(("err", f"{type(e).__name__}: {e}\n{traceback.format_exc()[-1500:]}"))


class PlannerProxy:
    def __init__(self, robot_cfg: dict, device: str = "cuda:0", code_dir: str | None = None,
                 log_dir: str = "/data/harvest/l9v2/tmp", timeout_s: float = 600.0):
        from multiprocessing.connection import Client
        os.makedirs(log_dir, exist_ok=True)
        tag = f"{os.getpid()}_{int(time.time())}"
        self.sock = os.path.join(log_dir, f"planner_{tag}.sock")
        cfg_path = os.path.join(log_dir, f"planner_{tag}.json")
        json.dump(robot_cfg, open(cfg_path, "w"))
        code = code_dir or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        env = {k: v for k, v in os.environ.items() if not k.startswith(("CARB_", "OMNI_", "EXP_", "ISAAC_PATH"))}
        env["PYTHONPATH"] = f"{code}:{PYLIB}"
        env.pop("LD_PRELOAD", None)
        self.log = open(os.path.join(log_dir, f"planner_{tag}.log"), "w")
        self.p = subprocess.Popen(["/isaac-sim/python.sh", "-m", "harvest.l9.plan9_server", self.sock, cfg_path,
                                   device], env=env, stdout=self.log, stderr=subprocess.STDOUT, cwd=code)
        t0 = time.time()
        while not os.path.exists(self.sock):
            if self.p.poll() is not None:
                raise RuntimeError(f"planner process exited ({self.p.returncode}); log {self.log.name}")
            if time.time() - t0 > timeout_s:
                raise RuntimeError("planner process did not start")
            time.sleep(0.5)
        self.c = Client(self.sock, family="AF_UNIX", authkey=AUTH)
        self.version = self._call("version")
        self.joint_names = self._call("joint_names")
        self.attached = None

    def _call(self, name, *args, **kw):
        self.c.send((name, args, kw))
        st, out = self.c.recv()
        if st != "ok":
            raise RuntimeError(f"planner {name}: {out}")
        return out

    def world(self, scene):
        self.attached = None
        return self._call("world", scene)

    def grasp(self, *a, **k):
        return self._call("grasp", *a, **k)

    def pose(self, *a, **k):
        return self._call("pose", *a, **k)

    def ik(self, *a, **k):
        return self._call("ik", *a, **k)

    def line(self, *a, **k):
        return self._call("line", *a, **k)

    def attach(self, q, names):
        self.attached = names
        return self._call("attach", q, names)

    def detach(self):
        self.attached = None
        return self._call("detach")

    def close(self):
        try:
            self._call("_quit")
        except Exception:  # noqa: BLE001
            pass
        self.p.terminate()


if __name__ == "__main__":
    serve(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "cuda:0")
