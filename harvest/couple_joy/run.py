"""E-CJ closed-loop runner (docs/stage3/coupling_program.md; prereg_cj1.md): one Isaac process = one scene variant of
the E-Couple world (SoloWorld, mug -> tray on DEV layout seeds, head depth on), commander x executor arms on the same
seeds:
  ox = truth commands (PtTruth, the point-then-act interface's ceiling) + scripted executor (MinJerkExec)
  ov = truth commands + VLA joystick executor (couple_joy.vla_exec.VLAJoyExec, fused VLA over HTTP)
  px / pv = the D planner (LimitEpisode d-min, local vLLM) + scripted / VLA executor (E-CJ2, not in E-CJ1)
Episodes are claimed with mkdir (lanes share the list); between episodes the process exits 3 when a yield file exists
(L9 GPU_WANTED / the lane's own WANTED file). Every episode: result.json (the episode's own record), cj.json (one row),
vla_steps.jsonl (VLA arms: one row per decision step), 10 fps head | right wrist video (jpg + H.264 mp4), and one line
in <vid-root>/index.jsonl.
python -m harvest.couple_joy.run --arms ox,ov --variant standard --seeds 0-19 --vla-url http://x2:8151
  --out /data/harvest/out/couple/cj1 --vid-root /data/harvest/videos/couple_cj1 [--yield-files a,b] [--owner lane]"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

ARMS = {"ox": ("truth", "code"), "ov": ("truth", "vla"), "px": ("planner", "code"), "pv": ("planner", "vla")}
VID_EVERY = 2  # 20 Hz control ticks -> 10 fps


def seed_list(spec: str) -> list:
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out += list(range(int(a), int(b) + 1))
        elif part.strip():
            out.append(int(part))
    if any(not 0 <= s <= 19 for s in out):
        raise SystemExit("DEV layout seeds 0-19 only (never CAL / TEST)")
    return out


class WorldIO:
    """What the VLA executor reads from the robot: frames (rendered at most once per control tick), the 8-D
    joint_pos (7 right-arm joints + pad gap, the aiworker state the VLA was trained on) and the stage-B context text
    (image-only state + unknown segment / motion lines = what harvest.runtime.core feeds this checkpoint)."""

    def __init__(self, ep):
        self.ep = ep
        self.fr, self.fr_tick = None, -1
        self.phase, self.t_phase0 = None, 0.0
        self._tcp_prev = None

    def frame(self):
        k = getattr(self.ep, "_ntick", 0)
        if self.fr_tick != k:
            self.fr, self.fr_tick = self.ep.w.frame(), k
        return self.fr

    def frames(self) -> dict:
        fr = self.frame()
        return {"cam_head": fr["head"], "cam_wrist_right": fr["wrist"]}

    def joint_pos(self):
        env = self.ep.w.env
        return np.r_[np.asarray(env.arm_q(), float), float(env.gripper_width())]

    def ctx_text(self, phase: str, t: float) -> str:
        from ..serialize import MOTION_UNKNOWN, SEGMENT_UNKNOWN, canonicalize
        from ..sim.planner import PHASE_TIMEOUT_S
        from ..sim.snapshot import text_state
        from ..train.stageb_data import image_only_state
        if phase != self.phase:
            self.phase, self.t_phase0 = phase, float(t)
        st = self.ep.w.status()
        tgt = self.ep.info["tgt"]
        pred = st["pred"]
        tcp = np.asarray(st["tcp"], float)
        moving = self._tcp_prev is not None and float(np.linalg.norm(tcp - self._tcp_prev)) > 1e-4
        self._tcp_prev = tcp
        s = text_state(float(t), phase, float(t) - self.t_phase0, PHASE_TIMEOUT_S.get(phase, 60.0), pred,
                       list(st["obj"]), {}, bool(pred.get("gripper_open")), bool(pred.get(f"holding({tgt})")),
                       moving, [], tgt=tgt)
        return canonicalize(image_only_state(s) + "\n" + SEGMENT_UNKNOWN + "\n" + MOTION_UNKNOWN)


def joy_class(base):
    from .vla_exec import VLAJoyExec

    class JoyEpisode(base):
        """base episode + executor choice (exec_kind code | vla) + a 10 fps head | wrist frame dump."""
        exec_kind, vla, vid_dir = "code", None, None

        def make_exec(self, st):
            self._ntick, self._nv = 0, 0
            if self.exec_kind == "code":
                return super().make_exec(st)
            w = self.w
            self.io = WorldIO(self)
            return VLAJoyExec(self.io, self.vla, w.dt, w.table_z, st["tcp"], w.env.arm_q(), float(st["grip_w"]),
                              w.w_open, w.w_close, quat0=w.quat0, tgt=self.info["tgt"], place=self.info["place"],
                              holding_fn=lambda: self.holding(self.w.status()))

        def _execute(self, cmd):
            if getattr(self.ex, "joint_mode", False):
                self.ex.set_intent(cmd)
            return super()._execute(cmd)

        def _tick(self):
            self._ntick = getattr(self, "_ntick", 0) + 1
            if not getattr(self.ex, "joint_mode", False):
                super()._tick()
            else:
                st = self.w.status()
                q, width, ev = self.ex.tick_q(st["t"], st["tcp"])
                for e in ev:
                    self.events.append(e)
                    if e["event"] == "close":
                        self.mon.on_close(st["t"], st["tcp"])
                self.w.env.step(np.concatenate([q, [width]]).astype(np.float32))
                self.w._st = None
            if self.vid_dir and self._ntick % VID_EVERY == 0:
                self._dump()

        def _dump(self):
            from PIL import Image
            io = getattr(self, "io", None)
            fr = io.frame() if io is not None else self.w.frame()
            h, wr = np.asarray(fr["head"]), np.asarray(fr["wrist"])
            if wr.shape[0] != h.shape[0]:
                wr = np.asarray(Image.fromarray(wr).resize((int(wr.shape[1] * h.shape[0] / wr.shape[0]), h.shape[0])))
            Image.fromarray(np.concatenate([h[..., :3], wr[..., :3]], axis=1).astype(np.uint8)).save(
                os.path.join(self.vid_dir, f"{self._nv:05d}.jpg"), quality=85)
            self._nv += 1

    return JoyEpisode


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", required=True)
    ap.add_argument("--variant", default="standard", choices=["standard", "dr"])
    ap.add_argument("--seeds", default="0-19")
    ap.add_argument("--vla-url", default="")
    ap.add_argument("--planner-url", default="")
    ap.add_argument("--planner-name", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--vid-root", required=True)
    ap.add_argument("--yield-files", default="")
    ap.add_argument("--owner", default="")
    ap.add_argument("--stop-calls", type=int, default=30)
    ap.add_argument("--stop-motion", type=float, default=120.0)
    a = ap.parse_args(argv)
    arms = [x for x in a.arms.split(",") if x]
    if any(x not in ARMS for x in arms):
        raise SystemExit(f"--arms: from {sorted(ARMS)}")
    yf = [f for f in a.yield_files.split(",") if f]
    code = 0
    try:
        from ..astra_solo.pt_episode import PtEpisode
        from ..astra_solo.pt_truth import PtTruth
        from ..astra_solo.world import SoloWorld
        from ..teach_pt.run_closed_l8s import claim, make_mp4, yield_reason
        vla = planner = None
        if any(ARMS[x][1] == "vla" for x in arms):
            from ..runtime.fused_model import FusedClient
            vla = FusedClient(a.vla_url, timeout_s=60.0)
        if any(ARMS[x][0] == "planner" for x in arms):
            from ..astra_solo.models import LocalVLM
            planner = LocalVLM(a.planner_url, a.planner_name, "qwen8b")
        world = SoloWorld(a.variant, depth=True)
        print("WORLD " + json.dumps({"variant": a.variant, "table_z": world.table_z, "arms": arms,
                                     "vla": None if vla is None else vla.model_id}), flush=True)
        owner = f"{a.owner} pid={os.getpid()}"
        for s in seed_list(a.seeds):
            for arm in arms:
                why = yield_reason(yf)
                if why:
                    print("YIELD " + why, flush=True)
                    code = 3
                    raise StopIteration
                od = os.path.join(a.out, arm, a.variant, f"s{s}")
                if not claim(od, owner):
                    continue
                cmdr, exk = ARMS[arm]
                vd = os.path.join(od, "frames10")
                os.makedirs(vd, exist_ok=True)
                kw = dict(out_dir=od, video=False, variant=a.variant, stop_calls=a.stop_calls,
                          stop_motion_s=a.stop_motion)
                t0 = time.perf_counter()
                if cmdr == "truth":
                    m = PtTruth(world)
                    ep = joy_class(PtEpisode)(world, m, s, "mug_tray", iface="pt", **kw)
                    m.ep = ep
                else:
                    from ..teach_strip8.boost import LimitEpisode
                    ep = joy_class(LimitEpisode)(world, planner, s, "mug_tray", mem_points=True, fix_loop=True, **kw)
                ep.exec_kind, ep.vla, ep.vid_dir = exk, vla, vd
                try:
                    res = ep.run()
                except Exception as ex:  # noqa: BLE001 -- one bad episode must not end the lane
                    import traceback
                    json.dump({"error": repr(ex), "tb": traceback.format_exc()[-3000:]},
                              open(os.path.join(od, "error.json"), "w"))
                    print("EP_ERROR " + json.dumps({"arm": arm, "seed": s, "err": repr(ex)}), flush=True)
                    continue
                exs = ep.ex.summary() if getattr(ep.ex, "joint_mode", False) else None
                if exs is not None:
                    with open(os.path.join(od, "vla_steps.jsonl"), "w") as f:
                        for r in ep.ex.log:
                            f.write(json.dumps(r) + "\n")
                mp4 = os.path.join(a.vid_root, arm, a.variant, f"s{s}.mp4")
                ok = make_mp4(vd, mp4)
                row = {"arm": arm, "commander": cmdr, "executor": exk, "variant": a.variant, "seed": s,
                       "success": bool(res.get("success")), "grasp_lift": res.get("grasp_lift"),
                       "fail_stage": res.get("fail_stage"), "end_reason": res.get("end_reason"),
                       "n_calls": res.get("n_calls"), "sim_t": res.get("sim_t"),
                       "wall_s": round(time.perf_counter() - t0, 1), "exec": exs,
                       "events": {k: sum(e.get("event") == k for e in ep.events)
                                  for k in ("reach", "settled", "timeout", "clipped", "grip_fallback", "vla_error",
                                            "close", "open")},
                       "mp4": mp4 if ok else None, "n_frames": getattr(ep, "_nv", 0), "frames": vd}
                json.dump(row, open(os.path.join(od, "cj.json"), "w"))
                os.makedirs(a.vid_root, exist_ok=True)
                with open(os.path.join(a.vid_root, "index.jsonl"), "a") as f:
                    f.write(json.dumps(row) + "\n")
                print("EP " + json.dumps({k: row[k] for k in ("arm", "variant", "seed", "success", "fail_stage",
                                                              "end_reason", "n_calls", "wall_s")}), flush=True)
        print("RUN_DONE", flush=True)
    except StopIteration:
        pass
    except BaseException:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        code = 1
    os._exit(code)


if __name__ == "__main__":
    main()
