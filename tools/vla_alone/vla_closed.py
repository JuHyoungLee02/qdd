"""E-VLA-solo closed-loop runner (docs/stage3/prereg_vla_solo.md): `harvest.eval.closed` unchanged, plus TEST-ONLY hooks
in the Isaac worker (nothing under harvest/ is edited; code base = the E-Couple dry-run copy 9322853, whose runtime
accepts the 5-question E-SR1c C1 checkpoint).

  1. constant playback speed S (--vla-speed, default 1.0): fused backend = the chunk play clock of the runtime
     (core._advance_play_clock / _play_chunk lag, review T10 I1) advanced every tick with scale S also when coupling is
     off (the runtime only advances it with the coupling driver): chunk row k plays at t0 + k * dt / S (linear
     interpolation between rows, harvest.runtime.fused_action.chunk_value) -> per-tick joint deltas scale by S, the
     safety rule 0.04 rad / frame is only helped; modular backend = the scripted skill's speed_scale = S.
  2. per-tick trace: t, TCP (world), finger midpoint g and mug o3 (sim, privileged, analysis only), gripper width,
     phase, chunk played flag, M4 hold flag, commanded joint action.
  3. frames: cam_head + cam_wrist_right JPEG at --vla-video-hz (sim s).
Outer run: Isaac GPU '3' is added to closed.ISAAC_GPUS (GPU 3 renders; GPU 2 never does, memory rule), paid paths
refused (--astra none, --couple off only).

  python tools/vla_alone/vla_closed.py <closed args> --vla-speed 0.5 [--vla-video-hz 2]
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.abspath(__file__)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

KEYS = {"--vla-speed": ("speed", 1.0), "--vla-video-hz": ("video_hz", 2.0), "--vla-noop": ("noop", 0)}
EXTRA_GPUS = ("3",)


def split_args(argv: list) -> tuple[list, dict]:
    cfg = {k: v for k, v in KEYS.values()}
    rest, i = [], 0
    while i < len(argv):
        a = argv[i]
        key = a.split("=", 1)[0]
        if key in KEYS:
            name, default = KEYS[key]
            val = a.split("=", 1)[1] if "=" in a else argv[i + 1]
            cfg[name] = type(default)(val)
            i += 1 if "=" in a else 2
            continue
        rest.append(a)
        i += 1
    if not 0.1 <= cfg["speed"] <= 1.0:
        raise SystemExit("--vla-speed in [0.1, 1.0]")
    return rest, cfg


def advance(rt, now: float, speed: float) -> None:
    """The runtime's play clock with a constant scale (same arithmetic as core._advance_play_clock)."""
    if rt._play_prev_t is not None and speed != 1.0:
        rt._play_lag += (1.0 - speed) * (now - rt._play_prev_t)
    rt._play_prev_t = now


def install_worker_hooks(spec_path: str) -> None:
    spec = json.load(open(spec_path, encoding="utf-8"))
    out, variant = spec["out"], spec["variant"]
    cfg = json.load(open(os.path.join(out, "vla_cfg.json"), encoding="utf-8"))
    speed = float(cfg["speed"])
    from harvest.runtime import core as CORE
    from harvest.runtime import ir_policy as IRP

    orig_req = CORE.OursRuntime._maybe_request_chunk

    def _maybe_request_chunk(self, now, obs):
        if self.driver is None:
            advance(self, now, speed)  # before the request records the lag at its observation (as the driver path)
        return orig_req(self, now, obs)
    CORE.OursRuntime._maybe_request_chunk = _maybe_request_chunk

    if cfg.get("noop"):
        # no-op baseline (--vla-noop 1, mock_fused only): the chunk holds the joints measured at the FIRST chunk
        # request of the episode (the stock MockFusedModel re-anchors every chunk to the measured, gravity-sagged
        # joints and drifted 278 mm in 15 s in the dry run -- prereg 0.3)
        from harvest.runtime import models as MD

        def chunk(self_m, ctx, committed):
            if getattr(self_m, "_noop_pose", None) is None:
                self_m._noop_pose = np.asarray(ctx["joint_pos"], float).copy()
            c = np.tile(self_m._noop_pose, (self_m.H, 1))
            return MD.ModelResult({}, self_m.synthetic_chunk_latency, call_id="noop", chunk=c,
                                  chunk_dt=self_m.chunk_dt, meta={"mock": True, "noop": True})
        MD.MockFusedModel.chunk = chunk

    orig_reset, orig_end = IRP.OursPolicy.reset, IRP.OursPolicy.on_trial_end

    def reset(self, scene):
        orig_reset(self, scene)
        rt = self.rt
        if getattr(rt, "model", None) is not None:
            rt.model._noop_pose = None
        if rt.cfg.backend != "fused":
            rt.skill.speed_scale = speed
        rt._vla = {"dir": os.path.join(out, "video", variant, self.info.name, str(scene.id)), "last_v": -1e9,
                   "rows": []}
        os.makedirs(rt._vla["dir"], exist_ok=True)

    def on_trial_end(self, record, log_dir, run_id):
        orig_end(self, record, log_dir, run_id)
        d = getattr(self.rt, "_vla", None)
        if d is None:
            return
        with open(os.path.join(out, f"vla_trace_{variant}.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"policy": self.info.name, "scene": str(record.scene_id), "epoch": record.epoch,
                                "episode": self.rt.episode, "speed": speed,
                                "cols": ["t", "tcp", "g", "o3", "w", "phase", "played", "hold", "a"],
                                "rows": d["rows"]}) + "\n")
        self.rt._vla = None
    IRP.OursPolicy.reset, IRP.OursPolicy.on_trial_end = reset, on_trial_end

    orig_act = CORE.OursRuntime.act
    vdt = 1.0 / float(cfg["video_hz"]) if cfg["video_hz"] > 0 else None

    def act(self, obs):
        a, meta = orig_act(self, obs)
        d = getattr(self, "_vla", None)
        if d is None:
            return a, meta
        now = float(self.t_last)
        if self.cfg.backend != "fused":
            self.skill.speed_scale = speed
        tcp, _ = obs["kin"].tcp_pose()
        raw = getattr(self, "_raw_last", None) or {}
        g = (raw.get("grip") or {}).get("pos")
        o3 = ((raw.get("objs") or {}).get("o3") or {}).get("pos")
        r5 = lambda v: None if v is None else [round(float(x), 5) for x in v]  # noqa: E731
        d["rows"].append([round(now, 4), r5(tcp), r5(g), r5(o3), round(float(np.asarray(a)[7]), 5),
                          self.skill.phase, bool(getattr(self, "_chunk_played", False)), bool(self.hold_step),
                          r5(np.asarray(a)[:7])])
        if vdt is not None and now - d["last_v"] >= vdt - 1e-9:
            from PIL import Image
            ph = self.skill.phase
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
    CL.ISAAC_GPUS = tuple(CL.ISAAC_GPUS) + EXTRA_GPUS
    if argv[:1] == ["--worker"]:
        install_worker_hooks(argv[1])
        return CL.run_worker(argv[1])
    rest, cfg = split_args(argv)
    a = CL._args(rest)
    if a.astra != "none" or a.couple != "off":
        raise SystemExit("E-VLA-solo: --astra none --couple off only (VLA alone / baselines, no paid call)")
    os.makedirs(a.out, exist_ok=True)
    json.dump(cfg, open(os.path.join(a.out, "vla_cfg.json"), "w", encoding="utf-8"), indent=1)
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
