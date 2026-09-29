"""E-Couple dry run (shakedown, no verdict; docs/stage3/prereg_couple_dry.md): `harvest.eval.closed` unchanged, plus
three TEST-ONLY hooks installed in the Isaac worker process (nothing under harvest/ is edited):

  1. PacedClient around the local VLM stream client (closed --couple-upper local): the answer is held back until an
     Astra-like latency has passed (lognormal, median 9.3 s = canon §86 F0 wall p50, sigma 0.25 -> p95 ~14 s,
     deterministic per (episode, request no)); fault injection: in EVEN episodes request no. FAULT_NO is held FAULT_S
     (25 s > timeout_s 20 s) -> exercises timeout -> slot freed -> late delivery. It also counts concurrent calls at the
     client (the in-flight-1 invariant measured outside the stream's own counters) and logs every call.
  2. act() trace: per tick TCP (world), phase, near flag, a privileged authority proxy a_priv (harvest.train.
     sr1c_authority.authority from the sim finger midpoint -> phase target distance; the value a Task-17-style gate
     would use, it is NOT applied here), coupling step (6-D), offset velocity / remaining, speed scale.
  3. video frames: cam_head + cam_wrist_right JPEG at VIDEO_HZ (sim s) per episode (both arms, same cost).

  outer:  python tools/couple_dry/dry_closed.py <closed args> [--dry-video-hz 3] [--dry-fault-no 3] [--dry-fault-s 25]
          [--dry-lat-median 9.3] [--dry-lat-sigma 0.25]
  worker: launched by closed.run() through the patched worker_cmd as `python.sh <this file> --worker <spec>`.
"""
from __future__ import annotations

import json
import math
import os
import sys
import threading
import time

import numpy as np

HERE = os.path.abspath(__file__)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

DRY_KEYS = {"--dry-video-hz": ("video_hz", 3.0), "--dry-fault-no": ("fault_no", 3), "--dry-fault-s": ("fault_s", 25.0),
            "--dry-lat-median": ("lat_median", 9.3), "--dry-lat-sigma": ("lat_sigma", 0.25)}
SALT = 0xC0D1


def split_args(argv: list) -> tuple[list, dict]:
    """(closed argv, dry config) -- the --dry-* options are removed from the closed argv."""
    cfg = {k: v for k, v in DRY_KEYS.values()}
    rest, i = [], 0
    while i < len(argv):
        a = argv[i]
        key = a.split("=", 1)[0]
        if key in DRY_KEYS:
            name, default = DRY_KEYS[key]
            val = a.split("=", 1)[1] if "=" in a else argv[i + 1]
            cfg[name] = type(default)(val)
            i += 1 if "=" in a else 2
            continue
        rest.append(a)
        i += 1
    return rest, cfg


def target_latency(episode: int, no: int, cfg: dict) -> tuple[float, bool]:
    """(padded latency s, fault) for coupling request `no` of `episode` (deterministic)."""
    if episode % 2 == 0 and no == int(cfg["fault_no"]):
        return float(cfg["fault_s"]), True
    rng = np.random.default_rng([SALT, int(episode), int(no)])
    return float(cfg["lat_median"] * math.exp(cfg["lat_sigma"] * rng.standard_normal())), False


class PacedClient:
    """Wraps a stream client (call(inp, effort, max_output_tokens, meta) -> AstraRecord); the model name is kept, so
    the runtime's paid guard sees the inner 'local:' client."""
    _lock = threading.Lock()
    _conc = 0

    def __init__(self, inner, cfg: dict, log_path: str, label: str, sleep=time.sleep):
        self.inner, self.cfg, self.log_path, self.label, self.sleep = inner, cfg, log_path, label, sleep
        self.model = getattr(inner, "model", "")
        self.max_conc = 0

    def call(self, inp, effort, max_output_tokens, meta):
        with PacedClient._lock:
            PacedClient._conc += 1
            conc = PacedClient._conc
            self.max_conc = max(self.max_conc, conc)
        w0 = time.time()
        try:
            rec = self.inner.call(inp, effort, max_output_tokens, meta)
            actual = float(rec.t_done - rec.t_send)
            ep, no = int(meta.get("episode", 0)), int(meta.get("couple_no", 0))
            tgt, fault = target_latency(ep, no, self.cfg)
            wait = max(0.0, tgt - actual)
            if wait > 0:
                self.sleep(wait)
            rec.t_done = rec.t_send + max(actual, tgt)
            rec.t_first_token = rec.t_done
            rec.meta = {**(rec.meta or {}), "dry_actual_s": round(actual, 4), "dry_target_s": round(tgt, 4),
                        "dry_fault": fault}
            row = {"label": self.label, "episode": ep, "no": no, "w_start": round(w0, 3), "actual_s": round(actual, 4),
                   "target_s": round(tgt, 4), "padded_s": round(rec.t_done - rec.t_send, 4), "fault": fault,
                   "conc_at_start": conc, "error": rec.error, "usage": rec.usage,
                   "out_chars": len(rec.output_text or "")}
            with PacedClient._lock:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(row) + "\n")
            return rec
        finally:
            with PacedClient._lock:
                PacedClient._conc -= 1

    def close(self):
        if hasattr(self.inner, "close"):
            self.inner.close()


def a_priv(raw: dict, phase: str, near: bool):
    """Privileged authority proxy (sim truth, not applied): harvest.train.sr1c_authority.authority with the stage
    distance = |finger midpoint - phase target| (o3 in pick phases, else o5 = the place object)."""
    from harvest.train import sr1c_authority as A
    tgt = "o3" if phase in A.PICK_PHASES else "o5"
    objs = raw.get("objs") or {}
    if tgt not in objs:
        return None, None
    d = float(np.linalg.norm(np.asarray(objs[tgt]["pos"], float) - np.asarray(raw["grip"]["pos"], float)))
    return A.authority(d, phase, contact=bool(near)), d


def install_worker_hooks(spec_path: str) -> None:
    spec = json.load(open(spec_path, encoding="utf-8"))
    out, variant = spec["out"], spec["variant"]
    cfg = json.load(open(os.path.join(out, "dry_cfg.json"), encoding="utf-8"))
    from harvest.eval import couple as CP
    from harvest.runtime import core as CORE
    from harvest.runtime import ir_policy as IRP
    orig_stream = CP.stream_client

    def stream_client(sp):
        cl, mode = orig_stream(sp)
        if mode != "local":
            raise SystemExit(f"dry run: stream client {mode!r}, only the local VLM is allowed (no paid call)")
        return PacedClient(cl, cfg, os.path.join(out, f"dry_calls_{variant}.jsonl"), variant), mode
    CP.stream_client = stream_client

    orig_reset, orig_end = IRP.OursPolicy.reset, IRP.OursPolicy.on_trial_end

    def reset(self, scene):
        orig_reset(self, scene)
        rt = self.rt
        rt._dry = {"dir": os.path.join(out, "video", variant, self.info.name, str(scene.id)), "last_v": -1e9,
                   "rows": []}
        os.makedirs(rt._dry["dir"], exist_ok=True)

    def on_trial_end(self, record, log_dir, run_id):
        orig_end(self, record, log_dir, run_id)
        d = getattr(self.rt, "_dry", None)
        if d is None:
            return
        p = os.path.join(out, f"dry_trace_{variant}.jsonl")
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps({"policy": self.info.name, "scene": str(record.scene_id), "epoch": record.epoch,
                                "episode": self.rt.episode, "rows": d["rows"]}) + "\n")
        self.rt._dry = None
    IRP.OursPolicy.reset, IRP.OursPolicy.on_trial_end = reset, on_trial_end

    orig_act = CORE.OursRuntime.act
    vdt = 1.0 / float(cfg["video_hz"]) if cfg["video_hz"] > 0 else None

    def act(self, obs):
        a, meta = orig_act(self, obs)
        d = getattr(self, "_dry", None)
        if d is None:
            return a, meta
        now = float(self.t_last)
        tcp, _ = obs["kin"].tcp_pose()
        raw = getattr(self, "_raw_last", None) or {}
        ph = self.skill.phase
        ap, dist = a_priv(raw, ph, self.near_now) if raw else (None, None)
        co, drv = self.couple_out, self.driver
        row = [round(now, 4), [round(float(x), 5) for x in tcp], ph, bool(self.near_now),
               None if ap is None else round(ap, 3), None if dist is None else round(dist, 4)]
        if co is not None and drv is not None:
            row += [[round(float(x), 6) for x in co.step6], round(float(np.linalg.norm(drv.offset.v[:3])), 5),
                    round(float(np.linalg.norm(drv.offset.rem[:3])), 5), float(co.speed_scale)]
        d["rows"].append(row)
        if vdt is not None and now - d["last_v"] >= vdt - 1e-9:
            from PIL import Image
            for cam in ("cam_head", "cam_wrist_right"):
                img = self.frames.get(cam)
                if img is not None:
                    Image.fromarray(np.asarray(img)).save(os.path.join(d["dir"], f"{now:07.3f}_{ph}_{cam}.jpg"),
                                                          quality=85)
            d["last_v"] = now
        return a, meta
    CORE.OursRuntime.act = act


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    from harvest.eval import closed as CL
    if argv[:1] == ["--worker"]:
        install_worker_hooks(argv[1])
        return CL.run_worker(argv[1])
    rest, cfg = split_args(argv)
    a = CL._args(rest)
    if a.astra not in ("none", "mock") or a.couple_upper != "local":
        raise SystemExit("dry run: --astra none|mock and --couple-upper local only (no paid call)")
    os.makedirs(a.out, exist_ok=True)
    json.dump(cfg, open(os.path.join(a.out, "dry_cfg.json"), "w", encoding="utf-8"), indent=1)
    orig = CL.worker_cmd

    def worker_cmd(code, spec_path, gpu, inst, timeout_s):
        cmd = orig(code, spec_path, gpu, inst, timeout_s)
        i = cmd.index("-m")
        if cmd[i + 1] != "harvest.eval.closed":
            raise RuntimeError(f"unexpected worker command {cmd}")
        return cmd[:i] + [HERE] + cmd[i + 2:]
    CL.worker_cmd = worker_cmd
    return CL.run(a)


if __name__ == "__main__":
    main()
