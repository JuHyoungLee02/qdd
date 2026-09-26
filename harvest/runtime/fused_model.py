"""StageBFused: the runtime adapter of a REAL stage-B checkpoint (canon §58 FusedModel; R5 open item 7, R6 issue 1).

Checkpoint = harvest.train.stageb_train output dir: adapter/ (PEFT LoRA on Qwen3-VL-4B) + heads.pt (action expert,
aux geometry head, verification head) + stageb.json (config, normalization, vocabularies, prompt_config).
One model process, one backbone (R5 §5 "2순위": HF for both paths, the decision pass and the context hidden states
come from ONE forward):
  decide = the R3 shared-prefix forward (train.prefix_share.samples_forward): the context prompt (system -> head ->
      active wrist -> IMG state, §59) and the decision questions (5 + the canon §87 gripper question) share one
      prefix pass -> option-trie renormalized
      probabilities (what stage A/B trained, same prompt_config) + the context hidden states -> verification head
      logits (the 9 E-M4b test predicates; runtime.measure turns them into measurements); the context is cached.
  chunk = expert flow sampling (10 Euler steps) replayed from a CUDA graph (fused_action.GraphedSampler) on the
      newest cached context (<= max_ctx_age_s old, else a fresh context-only forward), conditioned on the M4-committed
      decisions (option NAMES = the decision tokens), proprio, skill and phase.
Processes: the Isaac worker renders on GPU 1, so the model runs in its own process on a model GPU (2 or 3) behind a
  small HTTP server (`serve`, like the vLLM server of the modular stack); FusedClient is the runtime model (decide /
  chunk interface of runtime.models). StageBFused.decide / .chunk also work in process (GPU tests).
Proprio mapping (the aiworker observation is joint_pos 8-D = 7 right-arm joints + pad gap): q = joint_pos[:7];
  qd = finite difference over the previous control tick; tau = not observed -> the right-arm training mean
  (normalized 0 = mean imputation); grip = [pad gap, its finite-difference rate], mapped to [0, 1] openness for a
  checkpoint with norm.grip_space open01@v1 (canon §63 (2)) and the chunk's gripper column mapped back to a pad gap
  in m. Frames: JPEG q90 (the pool images' encoding).

  python -m harvest.runtime.fused_model serve --ckpt DIR [--port 8150] [--device cuda]      (CUDA_VISIBLE_DEVICES=2)
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import threading
import time
import uuid

import numpy as np

from .models import WRIST_LABEL, ModelResult, jpeg_bytes

HEAD_LABEL = "head camera:"
CAMS = (("cam_head", HEAD_LABEL), ("cam_wrist_right", WRIST_LABEL["cam_wrist_right"]))


def proprio23(jp, jp_prev, dt, tau_fill) -> dict:
    """stage-B proprio dict from the 8-D aiworker joint_pos (see module doc)."""
    jp = np.asarray(jp, float)
    ok = jp_prev is not None and dt is not None and dt > 0
    rate = (jp - np.asarray(jp_prev, float)) / dt if ok else np.zeros(8)
    return {"q": jp[:7].tolist(), "qd": rate[:7].tolist(), "tau": [float(v) for v in tau_fill],
            "grip": [float(jp[7]), float(rate[7])]}


def _check_space(grip_space):
    from ..train.stageb_data import GRIP_SPACE
    if grip_space not in (None, GRIP_SPACE):
        raise ValueError(f"checkpoint gripper space {grip_space!r}: this runtime knows None (raw m) and {GRIP_SPACE}")


def grip_to_model(proprio: dict, grip_space) -> dict:
    """aiworker pad gap [m, m/s] -> the checkpoint's gripper space (canon §63 (2): open01@v1 = sim openness);
    None = a pre-§63 checkpoint trained on raw metres."""
    _check_space(grip_space)
    if grip_space is None:
        return proprio
    from ..train.stageb_data import grip_open01, grip_rate01
    g = proprio["grip"]
    return {**proprio, "grip": [grip_open01(g[0], "sim_width_m"), grip_rate01(g[1], "sim_width_m")]}


def grip_from_model(chunk, grip_space) -> np.ndarray:
    """Expert chunk gripper column (openness) -> pad gap target in m for the aiworker action (copy)."""
    _check_space(grip_space)
    c = np.array(chunk, float)
    if grip_space is not None:
        from ..train.stageb_data import grip_value
        c[:, 7] = grip_value(c[:, 7], "sim_width_m")
    return c


def names_of(committed: dict, key2name: dict) -> dict:
    """M4 commits option KEYS; the expert's decision tokens are the option NAMES shown in the DecCall."""
    return {q: key2name.get(q, {}).get(k, k) for q, k in committed.items() if k is not None}


def softmax_names(lp: dict) -> dict:
    names = list(lp)
    v = np.array([float(lp[n]) for n in names])
    p = np.exp(v - v.max())
    return dict(zip(names, (p / p.sum()).tolist()))


def answers_from(probs_by_qid: dict, shown: dict) -> dict:
    """{question: {choice, p_chosen, p_second, probs (option keys), qid}} from option-name probabilities."""
    from ..options import to_option_key
    out = {}
    for qid, pn in probs_by_qid.items():
        q, opts = shown[qid]
        probs = {to_option_key(opts, n): float(p) for n, p in pn.items()}
        order = sorted(probs, key=probs.get, reverse=True)
        out[q] = {"choice": order[0], "p_chosen": probs[order[0]],
                  "p_second": probs[order[1]] if len(order) > 1 else 0.0, "probs": probs, "qid": qid}
    return out


# ------------------------------------------------------------------------------------------ engine (model process)
class StageBFused:
    kind, name = "fused", "stageb_fused"
    synthetic_latency = None
    synthetic_chunk_latency = None

    def __init__(self, ckpt: str, device: str = "cuda", base_model: str | None = None, steps: int = 10,
                 T_max: int = 1024, graph: bool = True, max_ctx_age_s: float = 0.7, frame_dir: str | None = None,
                 strict_prompt: bool = True, seed: int = 0, dtype: str = "bfloat16"):
        import torch

        from ..train import stageb_data as D
        from ..train.stageb_model import HFEncoder, load_heads
        from ..train.stageb_train import MODEL_DIR, load_backbone
        from .fused_action import GraphedSampler
        self.torch, self.D = torch, D
        self.ckpt = ckpt
        self.cfg = json.load(open(os.path.join(ckpt, "stageb.json"), encoding="utf-8"))
        pc = self.cfg.get("prompt_config") or {}
        if pc.get("state", "IMG") != "IMG":
            raise ValueError(f"{ckpt}: prompt state {pc.get('state')!r}; the fused runtime feeds IMG (canon §58)")
        if self.cfg["norm"]["mode"] != "absolute":
            raise ValueError("residual-mode checkpoints need the scripted chunk at runtime (not wired)")
        if self.cfg.get("verify") is None:
            raise ValueError(f"{ckpt}: no verification head (canon §64 needs V1h for M4 (b) / M7)")
        self.prompt_config = pc
        self.prompt_check = check_prompt(pc, strict_prompt)
        self.device = torch.device(device)
        base = base_model or self.cfg.get("base_model") or MODEL_DIR
        bb, proc, _ = load_backbone("qwen", base, self.device, adapter=os.path.join(ckpt, "adapter"),
                                    dtype=getattr(torch, dtype))
        bb.eval()
        self.m = load_heads(ckpt, bb, self.device).eval()
        self.enc = HFEncoder(proc)
        self.sampler = GraphedSampler(self.m.expert, T_max, steps) if graph else None
        self.steps, self.max_ctx_age_s = steps, max_ctx_age_s
        self.hz = int(self.cfg.get("hz", D.HZ))
        self._cv, self._busy, self._chunk_waiting = threading.Condition(), False, 0
        self.cache = None  # (t_state, ctx [1, T, D], mask [1, T])
        self.key2name: dict = {}
        self.gen = torch.Generator(device="cpu").manual_seed(seed)
        self.frame_dir = frame_dir or os.path.join("/data/harvest/tmp/fused_frames", str(os.getpid()))
        os.makedirs(self.frame_dir, exist_ok=True)
        # the aiworker task is one right arm: right-arm statistics (§63 (1)); tau not observed -> its training mean
        self.arm = "right"
        self.tau_fill = [float(v) for v in self.m.norm.stats(self.arm)["p_mean"][14:21]]
        self.grip_space = self.m.norm.grip_space  # §63 (2): open01@v1 -> pad gap mapped in / chunk mapped back
        _check_space(self.grip_space)
        self.model_id = f"stageb:{os.path.abspath(ckpt)}"
        self.verify_preds = list(self.cfg["verify"].get("preds", D.VERIFY_PREDS))

    def info(self) -> dict:
        return {"model_id": self.model_id, "tau_fill": self.tau_fill, "hz": self.hz, "verify_preds": self.verify_preds,
                "grip_space": self.grip_space, "arm": self.arm,
                "prompt_config": self.prompt_config, "prompt_check": self.prompt_check,
                "graph": self.sampler is not None and self.sampler.use_graph, "steps": self.steps,
                "max_ctx_age_s": self.max_ctx_age_s}

    # ---- frames: JPEG q90 bytes -> files (the encoder opens image paths, like the training data)
    def _files(self, jpegs: dict, tag: str) -> list:
        out = []
        for cam, label in CAMS:
            b = jpegs.get(cam)
            if b is None:
                raise ValueError(f"no {cam} frame (the fused model needs head + active wrist)")
            p = os.path.join(self.frame_dir, f"{tag}_{cam}.jpg")
            with open(p, "wb") as f:
                f.write(b)
            out.append([label, p])
        return out

    @staticmethod
    def _rm(frames):
        for _, p in frames:
            try:
                os.remove(p)
            except OSError:
                pass

    def _sync(self):
        if self.device.type == "cuda":
            self.torch.cuda.synchronize()

    def _gpu(self, chunk: bool):
        """One GPU job at a time; a waiting chunk (time-critical: it must land before its step starts) goes before
        waiting decide calls (pre-R7 smoke: FIFO made chunks wait p50 0.55 s behind overlapping decides)."""
        eng = self

        class _G:
            def __enter__(self):
                with eng._cv:
                    if chunk:
                        eng._chunk_waiting += 1
                    while eng._busy or (not chunk and eng._chunk_waiting > 0):
                        eng._cv.wait()
                    if chunk:
                        eng._chunk_waiting -= 1
                    eng._busy = True

            def __exit__(self, *exc):
                with eng._cv:
                    eng._busy = False
                    eng._cv.notify_all()
                return False
        return _G()

    def decide_raw(self, t_state: float, ctx_text: str, req: dict, jpegs: dict) -> dict:
        """{"probs": {qid: {option name: p}}, "verify": {pred: logit}, "meta": {...}}."""
        torch = self.torch
        from ..clients.jevl import question_text
        from ..train.prefix_share import samples_forward
        t0 = time.perf_counter()
        tag = f"d{uuid.uuid4().hex[:10]}"
        frames = self._files(jpegs, tag)
        try:
            items = [{"key": tag, "question": qid, "qid": qid, "names": list(spec["criteria"]),
                      "text": question_text(req["state"], qid, spec), "images": frames}
                     for qid, spec in req["questions"].items()]
            sample = {"key": tag, "context": {"text": ctx_text, "images": frames}, "items": items}
            with self._gpu(chunk=False):
                t_lock = time.perf_counter()
                with torch.no_grad():
                    hs, lps = samples_forward(self.m.backbone, self.enc, [sample], self.device, self.m.layer)
                    self._sync()
                    t_dec = time.perf_counter()
                    h = hs[0][None]
                    mask = torch.ones(1, h.shape[1], dtype=torch.long, device=self.device)
                    vl = self.m.verify_logits(h, mask)[0].float().cpu().numpy()
                    self._sync()
                    t_ver = time.perf_counter()
                if self.cache is None or float(t_state) >= self.cache[0]:  # newest observation wins
                    self.cache = (float(t_state), h.detach(), mask)
        finally:
            self._rm(frames)
        return {"probs": {it["qid"]: softmax_names(lp) for it, lp in zip(items, lps[0])},
                "verify": {p: float(x) for p, x in zip(self.verify_preds, vl)},
                "meta": {"t_wait_s": round(t_lock - t0, 5), "t_decide_s": round(t_dec - t_lock, 5),
                         "t_verify_s": round(t_ver - t_dec, 5), "ctx_tokens": int(h.shape[1]),
                         "prompt_sha": self.prompt_config.get("sha")}}

    def _context(self, t_state, ctx_text, jpegs):
        torch = self.torch
        c = self.cache
        if c is not None and t_state - c[0] <= self.max_ctx_age_s + 1e-9:
            return c[1], c[2], t_state - c[0], False
        frames = self._files(jpegs, f"c{uuid.uuid4().hex[:10]}")
        try:
            with torch.no_grad():
                h = self.m.context(self.enc.inputs(ctx_text, frames, self.device), grad=False)[None]
        finally:
            self._rm(frames)
        return h, torch.ones(1, h.shape[1], dtype=torch.long, device=self.device), 0.0, True

    def chunk_raw(self, t_state: float, ctx_text: str, jpegs: dict, proprio: dict, phase: str,
                  committed_names: dict) -> dict:
        """{"chunk": [H][8] absolute targets, "chunk_dt", "meta"}."""
        torch = self.torch
        from ..datagen.rows import skill_of
        t0 = time.perf_counter()
        s = {"proprio": grip_to_model(proprio, self.grip_space), "skill_id": skill_of(phase), "phase_id": phase,
             "committed": dict(committed_names), "arm": self.arm}
        with self._gpu(chunk=True):
            t_lock = time.perf_counter()
            h, mask, age, fresh = self._context(float(t_state), ctx_text, jpegs)
            self._sync()
            t_ctx = time.perf_counter()
            with torch.no_grad():
                cond = self.m.cond([s], h, mask, self.device)
                noise = torch.randn(1, self.m.expert.cfg.horizon, self.m.expert.cfg.act_dim,
                                    generator=self.gen).to(self.device)
                if self.sampler is not None:
                    z = self.sampler(cond, noise)
                else:
                    from ..train.stageb_expert import sample_actions
                    z = sample_actions(self.m.expert, cond, self.steps, noise)
                self._sync()
            t_exp = time.perf_counter()
        act = grip_from_model(self.m.norm.action(z[0].float().cpu().numpy(), arm=self.arm), self.grip_space)
        return {"chunk": np.asarray(act, float).tolist(), "chunk_dt": 1.0 / self.hz,
                "meta": {"t_wait_s": round(t_lock - t0, 5), "t_ctx_s": round(t_ctx - t_lock, 5),
                         "t_expert_s": round(t_exp - t_ctx, 5), "ctx_age_s": round(age, 4), "ctx_fresh": fresh,
                         "committed_names": dict(committed_names),
                         "graph": self.sampler is not None and self.sampler.use_graph}}

    # ---- in-process runtime-model interface (GPU tests)
    def decide(self, ctx: dict) -> ModelResult:
        t0 = time.perf_counter()
        try:
            for qid, (q, opts) in ctx["shown"].items():
                self.key2name[q] = {o.key: o.name for o in opts}
            r = self.decide_raw(ctx["t_state"], ctx["ctx_text"], ctx["req"], _jpegs(ctx["images"]))
            return ModelResult(answers_from(r["probs"], ctx["shown"]), time.perf_counter() - t0,
                               call_id=uuid.uuid4().hex, verify=r["verify"], meta=r["meta"], raw=r)
        except Exception as e:  # noqa: BLE001
            return ModelResult({}, time.perf_counter() - t0, error=f"{type(e).__name__}: {e}")

    def chunk(self, ctx: dict, committed: dict) -> ModelResult:
        t0 = time.perf_counter()
        try:
            pro = proprio23(ctx["joint_pos"], ctx.get("joint_pos_prev"), ctx.get("dt_prev"), self.tau_fill)
            r = self.chunk_raw(ctx["t_state"], ctx["ctx_text"], _jpegs(ctx["images"]), pro, ctx["phase"],
                               names_of(committed, self.key2name))
            return ModelResult({}, time.perf_counter() - t0, call_id=uuid.uuid4().hex,
                               chunk=np.asarray(r["chunk"], float), chunk_dt=r["chunk_dt"], meta=r["meta"])
        except Exception as e:  # noqa: BLE001
            return ModelResult({}, time.perf_counter() - t0, error=f"{type(e).__name__}: {e}")

    def close(self):
        pass


def _jpegs(images: dict) -> dict:
    return {cam: jpeg_bytes(images[cam]) for cam, _ in CAMS if images.get(cam) is not None}


def check_prompt(pc: dict, strict: bool = True) -> dict:
    """The checkpoint's training prompt_config against what this runtime feeds (§59 camera layout, IMG state,
    system prompt, state serializer version (canon §77 / §83 / §87 / §90 ser-A-min-3: segment + motion + `last_step:`
    lines, fused gripper question; the recorded `last_step` categories, controller ruling PH-A 2), prompt-building
    source files). A checkpoint trained with the motion line (prompt_config_t: "motion" bins, TEMPORAL_FILES in
    files_sha) is accepted in the default layout; a video2 layout (not adopted, canon §83) is refused."""
    import hashlib

    from ..clients.jevl import SYSTEM
    from ..serialize import SERIALIZER_VERSION
    from ..train import stageb_data as D
    from ..train.stagea_train import PROMPT_FILES, file_sha, format_checks, serializer_of
    from ..train.stageb_train import PROMPT_FILES_B, TEMPORAL_FILES
    cam = D.CAMERA_LAYOUT + ":" + "|".join(lab for _, lab in CAMS)
    ser = serializer_of(pc)
    files = PROMPT_FILES + PROMPT_FILES_B + (TEMPORAL_FILES if pc.get("motion") else ())
    now = {"camera_ok": cam in (pc.get("camera") or []), "state_ok": pc.get("state") == "IMG",
           "layout_ok": pc.get("layout", D.CAMERA_LAYOUT) == D.CAMERA_LAYOUT,
           "system_ok": pc.get("system_sha") == hashlib.sha256(SYSTEM.encode()).hexdigest()[:12],
           **format_checks(pc),  # serializer_ok, last_step_ok
           "files_ok": pc.get("files_sha") == file_sha(files), "sha": pc.get("sha"), "serializer": ser}
    now["mismatch"] = [k for k, v in now.items() if k.endswith("_ok") and not v]
    if now["mismatch"] and strict:
        extra = "" if now["serializer_ok"] else (f"; state serializer {ser!r} != runtime {SERIALIZER_VERSION!r} "
                                                 f"(canon §77 / §83 / §87 / §90: the DecCall state ends with the "
                                                 f"segment, motion and M4 (b) 'last_step:' lines and the fused "
                                                 f"model decides the gripper; older checkpoints are invalid -- "
                                                 f"retrain)")
        raise ValueError(f"prompt_config mismatch between training and runtime: {now['mismatch']} (camera {cam!r}, "
                         f"trained {pc.get('camera')}){extra}")
    return now


# ------------------------------------------------------------------------------------------ HTTP (model process)
def make_handler(engine):
    from http.server import BaseHTTPRequestHandler

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, obj):
            b = json.dumps(obj).encode()
            try:
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)
            except (BrokenPipeError, ConnectionResetError):  # the client went away (worker exit mid-call)
                pass

        def do_GET(self):
            self._send(200, engine.info()) if self.path == "/info" else self._send(404, {"error": self.path})

        def do_POST(self):
            try:
                d = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                jp = {k: base64.b64decode(v) for k, v in (d.get("images") or {}).items()}
                if self.path == "/decide":
                    r = engine.decide_raw(d["t_state"], d["ctx_text"], d["req"], jp)
                elif self.path == "/chunk":
                    r = engine.chunk_raw(d["t_state"], d["ctx_text"], jp, d["proprio"], d["phase"], d["committed"])
                else:
                    return self._send(404, {"error": self.path})
                self._send(200, r)
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as e:  # noqa: BLE001
                self._send(500, {"error": f"{type(e).__name__}: {e}"})
    return H


def serve(a):
    from http.server import ThreadingHTTPServer
    eng = StageBFused(a.ckpt, device=a.device, graph=not a.no_graph, max_ctx_age_s=a.max_ctx_age)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(eng))
    print("FUSED_READY " + json.dumps({"port": a.port, **eng.info()}, default=str), flush=True)
    srv.serve_forever()


# ------------------------------------------------------------------------------------------ client (runtime side)
class FusedClient:
    """The runtime model for --backend fused with a real stage-B checkpoint: HTTP to the model process."""
    kind, name = "fused", "stageb_fused_http"
    synthetic_latency = None
    synthetic_chunk_latency = None

    def __init__(self, url: str, timeout_s: float = 10.0, transport=None):
        import httpx
        self.url, self.c = url.rstrip("/"), httpx.Client(timeout=timeout_s, transport=transport)
        self.info = self.c.get(self.url + "/info").json()
        self.model_id, self.tau_fill = self.info["model_id"], self.info["tau_fill"]
        self.key2name: dict = {}

    def _post(self, path, payload):
        r = self.c.post(self.url + path, json=payload)
        d = r.json()
        if r.status_code != 200:
            raise RuntimeError(d.get("error", r.status_code))
        return d

    @staticmethod
    def _b64(images):
        return {k: base64.b64encode(v).decode() for k, v in _jpegs(images).items()}

    def decide(self, ctx: dict) -> ModelResult:
        t0 = time.perf_counter()
        try:
            for qid, (q, opts) in ctx["shown"].items():
                self.key2name[q] = {o.key: o.name for o in opts}
            d = self._post("/decide", {"t_state": ctx["t_state"], "ctx_text": ctx["ctx_text"], "req": ctx["req"],
                                       "images": self._b64(ctx["images"])})
            lat = time.perf_counter() - t0
            return ModelResult(answers_from(d["probs"], ctx["shown"]), lat, call_id=uuid.uuid4().hex,
                               verify=d["verify"], meta={**d["meta"], "t_total_s": round(lat, 5)}, raw=d)
        except Exception as e:  # noqa: BLE001 -- logged as a call error; M4 keeps the last committed action
            return ModelResult({}, time.perf_counter() - t0, error=f"{type(e).__name__}: {e}")

    def chunk(self, ctx: dict, committed: dict) -> ModelResult:
        t0 = time.perf_counter()
        try:
            pro = proprio23(ctx["joint_pos"], ctx.get("joint_pos_prev"), ctx.get("dt_prev"), self.tau_fill)
            d = self._post("/chunk", {"t_state": ctx["t_state"], "ctx_text": ctx["ctx_text"],
                                      "images": self._b64(ctx["images"]), "proprio": pro, "phase": ctx["phase"],
                                      "committed": names_of(committed, self.key2name)})
            lat = time.perf_counter() - t0
            return ModelResult({}, lat, call_id=uuid.uuid4().hex, chunk=np.asarray(d["chunk"], float),
                               chunk_dt=d["chunk_dt"], meta={**d["meta"], "t_total_s": round(lat, 5),
                                                             "proprio_map": "q, qd finite diff, tau = train mean"})
        except Exception as e:  # noqa: BLE001
            return ModelResult({}, time.perf_counter() - t0, error=f"{type(e).__name__}: {e}")

    def close(self):
        self.c.close()


def bench(a):
    """In-process check on POOL snapshots (pod, model GPU): decide / verify / chunk latency split, CUDA graph == eager,
    and decide() probabilities == the per-item full-row forward (stage-A/B training path, stagea_loss.item_logprobs)."""
    import glob

    from ..train.stagea_loss import item_logprobs
    from ..train.stageb_data import image_only_state
    from ..serialize import canonicalize
    from .models import build_live_request
    eng = StageBFused(a.ckpt, device=a.device, dtype=a.dtype)
    torch = eng.torch
    lines = []
    for p in sorted(glob.glob(os.path.join(a.pool, "ep*.jsonl")))[:3]:
        lines += [json.loads(x) for x in open(p, encoding="utf-8")]
    lines = lines[:a.n]
    rec = {"decide": [], "verify": [], "chunk_graph": [], "chunk_eager": [], "graph_vs_eager": [], "lp_diff": []}
    for i, ln in enumerate(lines):
        raw, present = ln["state"]["obs"]["raw"], ln["state"]["present"]
        from ..deccall_snap import last_step_of
        req, shown = build_live_request(i, ln["phase"], ln["text_state"], present, raw, state="IMG",
                                        last_step=last_step_of(ln))
        ctx_text = canonicalize(image_only_state(ln["text_state"]))
        jp = {cam: open(os.path.join(a.pool, ln["images"][cam]), "rb").read() for cam, _ in CAMS}
        r = eng.decide_raw(ln["t"], ctx_text, req, jp)
        rec["decide"].append(r["meta"]["t_decide_s"])
        rec["verify"].append(r["meta"]["t_verify_s"])
        pro = {"q": [0.0] * 7, "qd": [0.0] * 7, "tau": eng.tau_fill, "grip": [float(raw["grip"]["w"]), 0.0]}
        dec = {shown[q][0]: max(pn, key=pn.get) for q, pn in r["probs"].items()}
        s1 = eng.gen.get_state()
        c1 = eng.chunk_raw(ln["t"], ctx_text, jp, pro, ln["phase"], dec)
        rec["chunk_graph"].append(c1["meta"]["t_expert_s"])
        eng.gen.set_state(s1)
        smp, eng.sampler = eng.sampler, None
        c2 = eng.chunk_raw(ln["t"], ctx_text, jp, pro, ln["phase"], dec)
        eng.sampler = smp
        rec["chunk_eager"].append(c2["meta"]["t_expert_s"])
        rec["graph_vs_eager"].append(float(np.abs(np.asarray(c1["chunk"]) - np.asarray(c2["chunk"])).max()))
        if i < a.n_lp:  # training-path equality of the decision probabilities (full-row forward per item)
            fr = eng._files(jp, f"lp{i}")
            try:
                for qid, spec in req["questions"].items():
                    from ..clients.jevl import question_text
                    tok, trie = eng.enc.trie(list(spec["criteria"]))
                    with torch.no_grad():
                        lp = item_logprobs(eng.m.backbone, eng.enc.inputs(question_text(req["state"], qid, spec), fr,
                                                                          eng.device), tok, trie, eng.enc.end,
                                           eng.enc.pad)
                    p_full = softmax_names({n: float(v) for n, v in lp.items()})
                    rec["lp_diff"].append(max(abs(p_full[n] - r["probs"][qid][n]) for n in p_full))
            finally:
                eng._rm(fr)
    q = lambda v, p: round(float(np.quantile(v[3:] if len(v) > 5 else v, p)) * 1e3, 2)  # noqa: E731
    out = {"n": len(lines), "gpu": torch.cuda.get_device_name(0) if eng.device.type == "cuda" else "cpu",
           **{k + "_ms": {"p50": q(v, 0.5), "p95": q(v, 0.95)} for k, v in rec.items()
              if k in ("decide", "verify", "chunk_graph", "chunk_eager")},
           "graph_vs_eager_max_abs": max(rec["graph_vs_eager"]), "decide_vs_fullrow_prob_max_abs": max(rec["lp_diff"])
           if rec["lp_diff"] else None, "info": eng.info()}
    print("FUSED_BENCH " + json.dumps(out, default=str), flush=True)
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1, default=str)


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve")
    s.add_argument("--ckpt", required=True)
    s.add_argument("--port", type=int, default=8150)
    s.add_argument("--device", default="cuda")
    s.add_argument("--no-graph", action="store_true")
    s.add_argument("--max-ctx-age", type=float, default=0.7)
    b = sub.add_parser("bench")
    b.add_argument("--ckpt", required=True)
    b.add_argument("--pool", default="/data/harvest/data/pool")
    b.add_argument("--device", default="cuda")
    b.add_argument("--n", type=int, default=25)
    b.add_argument("--n-lp", type=int, default=3)
    b.add_argument("--dtype", default="bfloat16", help="bfloat16 (runtime) | float32 (equality check)")
    b.add_argument("--out", default="")
    a = ap.parse_args(argv)
    {"serve": serve, "bench": bench}[a.cmd](a)


if __name__ == "__main__":
    main()
