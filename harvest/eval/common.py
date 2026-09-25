"""Shared parts of the R6 evaluation commands: model resolution / fingerprint / serving (vLLM, canon §59 flags, call
mode lead), the DecCall request of one snapshot with option-name variants (canon §27, §54), run metadata (git
commit, code hash, model and prompt-config hashes, seeds), and JSON + markdown outputs.

Everything a command writes goes under its --out; vLLM caches go under /data/harvest/cache (pod rule).
"""
from __future__ import annotations

import asyncio
import glob
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from collections import defaultdict

from ..deccall_snap import annotate_last_step, build_snapshot_request
from ..jevcall import build_choice
from ..options import variant as name_variant

QUESTIONS = ("dir_xy", "dir_z", "mag_coarse", "target", "phase")  # stage-A decision questions (progress untrained)
BASE_MODEL = "/data/harvest/models/Qwen3-VL-4B-Instruct"
VLLM_BIN = "/data/harvest/venv_vllm/bin/vllm"
TRAIN_PY = "/data/harvest/venv_train/bin/python"
STEP_CM = 0.1  # S1 1 mm (canon §54)
WRIST_LABEL = "right wrist camera (active arm):"  # POOL / DEV task is single-arm right (§57)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ------------------------------------------------------------------------------------------ requests
def _variant_seed(q: str) -> int:
    return int(hashlib.sha256(q.encode()).hexdigest()[:8], 16)


def build_request(line: dict, var: str = "A0", step_cm: float = STEP_CM):
    """DecCall of one snapshot exactly as the stage-A items / R5 runtime (S1 on a 1 mm grid, the 5 decision
    questions), with option-name variant `var` (A0 = the jevcall names). The pool `oracle` field never reaches the
    prompt (a dummy oracle is passed, as stagea_data does)."""
    from .. import e3lite
    ln = {**line, "oracle": defaultdict(lambda: None)}
    req, _, shown = build_snapshot_request(ln, text_state=e3lite.state_text(ln, "S1", step_cm=step_cm))
    qs, out = {}, {}
    for qid, (q, opts) in shown.items():
        if q not in QUESTIONS:
            continue
        o2 = opts if var == "A0" else name_variant(opts, var, _variant_seed(q))
        k, spec = build_choice(qid, req["questions"][qid]["instructions"], o2)
        qs[k], out[k] = spec, (q, o2)
    return {**req, "questions": qs}, out


def answers_to_keys(answers: dict, shown: dict) -> dict:
    """CallRecord.answers -> {question: {key, name, p, probs by option_key}} (canon §27 R5)."""
    out = {}
    for qid, (q, opts) in shown.items():
        a = answers.get(qid)
        if not a:
            continue
        by_name = {o.name: o.key for o in opts}
        out[q] = {"key": by_name.get(a["choice"]), "name": a["choice"], "p": a.get("confidence"),
                  "probs": {by_name[n]: p for n, p in a["probabilities"].items() if n in by_name}}
    return out


def images_for(line: dict, root: str, layout: str) -> list:
    """[(label, bytes)] in the §59 order; layout H = head only (stage-A training prompt), HW = head + active wrist."""
    ims = [("head camera:", open(os.path.join(root, line["images"]["cam_head"]), "rb").read())]
    if layout == "HW":
        ims.append((WRIST_LABEL, open(os.path.join(root, line["images"]["cam_wrist_right"]), "rb").read()))
    return ims


# ------------------------------------------------------------------------------------------ model
def resolve_model(spec: str) -> dict:
    """zero-shot | mock | a merged model dir (config.json + *.safetensors) | a LoRA adapter dir (adapter_config.json,
    merged on the fly by tools/stagea_merge.py)."""
    if spec in ("zero-shot", "zero", "base"):
        return {"kind": "zero-shot", "path": BASE_MODEL, "spec": spec}
    if spec == "mock":
        return {"kind": "mock", "path": None, "spec": spec}
    if os.path.isfile(os.path.join(spec, "stageb.json")) and os.path.isdir(os.path.join(spec, "adapter")):
        return {"kind": "stageb", "path": os.path.abspath(spec), "spec": spec}  # fused model (runtime.fused_model)
    if os.path.isfile(os.path.join(spec, "adapter_config.json")):
        return {"kind": "adapter", "path": os.path.abspath(spec), "spec": spec}
    if os.path.isfile(os.path.join(spec, "config.json")) and glob.glob(os.path.join(spec, "*.safetensors")):
        return {"kind": "merged", "path": os.path.abspath(spec), "spec": spec}
    raise SystemExit(f"--model {spec!r}: not zero-shot / mock / a merged model dir / a LoRA adapter dir")


def model_fingerprint(path: str) -> str:
    """Fast content fingerprint: every file's name + size, the full bytes of small files (<= 64 MB) and the first /
    last 16 MB of large ones (weights). Documented as a fingerprint, not a full sha256 of the weights."""
    h = hashlib.sha256()
    for f in sorted(os.listdir(path)):
        p = os.path.join(path, f)
        if not os.path.isfile(p):
            continue
        n = os.path.getsize(p)
        h.update(f"{f}:{n}".encode())
        with open(p, "rb") as fh:
            if n <= 64 << 20:
                h.update(fh.read())
            else:
                h.update(fh.read(16 << 20))
                fh.seek(-(16 << 20), 2)
                h.update(fh.read())
    return h.hexdigest()[:16]


def training_prompt_config(model_path: str | None) -> dict | None:
    """What the model was trained on (stagea_train prompt_config, or the older config.json args): camera layout,
    state mode, grid, prompt files sha. None for the base model. A checkpoint trained on another DecCall state
    format (serializer, canon §77) is refused (ValueError) -- every evaluation command reads this first."""
    from ..train.stagea_train import require_serializer
    pc = _training_prompt_config(model_path)
    require_serializer(pc, f"model {model_path}")
    return pc


def _training_prompt_config(model_path: str | None) -> dict | None:
    if not model_path:
        return None
    sb = os.path.join(model_path, "stageb.json")
    if os.path.isfile(sb):  # stage-B checkpoint (stageb_train.prompt_config)
        return json.load(open(sb, encoding="utf-8")).get("prompt_config")
    mi = os.path.join(model_path, "merge_info.json")
    run = None
    if os.path.isfile(mi):
        run = os.path.dirname(json.load(open(mi, encoding="utf-8")).get("adapter", "").rstrip("/"))
    elif os.path.isfile(os.path.join(model_path, "adapter_config.json")):
        run = os.path.dirname(model_path.rstrip("/"))
    if not run or not os.path.isfile(os.path.join(run, "config.json")):
        return None
    c = json.load(open(os.path.join(run, "config.json"), encoding="utf-8"))
    if "prompt_config" in c:
        return c["prompt_config"]
    a = c.get("args", {})
    return {"camera": ["H:cam_head"], "state": a.get("state"), "step_cm": a.get("step_cm"),
            "files_sha": c.get("prompt_files_sha"), "from": "config.json args (pre prompt_config runs)"}


def default_layout(pc: dict | None) -> str:
    """The layout the model was trained with; H (stage-A training prompt) when unknown or for the base model."""
    if not pc or not pc.get("camera"):
        return "H"
    cams = pc["camera"]
    return "HW" if any(c.startswith("HW") or "wrist" in c for c in cams) else "H"


def prompt_config_eval(layout: str, var: str = "A0") -> dict:
    """The inference-side prompt config of this evaluation (same fields as stagea_train.prompt_config) + sha."""
    from ..clients.jevl import SYSTEM
    from ..train.stagea_train import PROMPT_FILES, file_sha
    cfg = {"camera": layout, "state": "S1", "step_cm": STEP_CM, "names": var,
           "system_sha": hashlib.sha256(SYSTEM.encode()).hexdigest()[:12], "files_sha": file_sha(PROMPT_FILES)}
    cfg["sha"] = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    return cfg


def ensure_merged(info: dict, out: str) -> dict:
    """Adapter -> merged model under <out>/merged_<adapter sha> (tools/stagea_merge.py, venv_train, CPU float32)."""
    if info["kind"] != "adapter":
        return info
    sha = hashlib.sha256(open(os.path.join(info["path"], "adapter_config.json"), "rb").read()).hexdigest()[:8]
    dst = os.path.join(out, f"merged_{sha}")
    if not os.path.isfile(os.path.join(dst, "merge_info.json")):
        subprocess.run([TRAIN_PY, os.path.join(REPO, "tools", "stagea_merge.py"), "--adapter", info["path"],
                        "--out", dst], check=True, env={**os.environ, "CUDA_VISIBLE_DEVICES": ""})
    return {**info, "kind": "merged", "path": dst, "adapter": info["path"]}


# ------------------------------------------------------------------------------------------ serving
def vllm_cmd(model_path: str, name: str, port: int, util: float = 0.30) -> list:
    """Same flags as tools/r5/serve.sh (canon §59: prefix cache + multimodal cache on, 2 images, raw logprobs,
    batch invariant via env)."""
    return [VLLM_BIN, "serve", model_path, "--served-model-name", name, "--host", "127.0.0.1", "--port", str(port),
            "--dtype", "bfloat16", "--max-model-len", "8192", "--gpu-memory-utilization", str(util),
            "--enable-prefix-caching", "--limit-mm-per-prompt", '{"image":2,"video":0,"audio":0}',
            "--logprobs-mode", "raw_logprobs", "--seed", "0"]


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class Server:
    """Context manager: an existing server (url + name) or our own vLLM on one GPU (only this process is stopped)."""

    def __init__(self, info: dict, gpu: str, out: str, url: str = "", name: str = "", util: float = 0.30):
        self.info, self.gpu, self.out, self.util = info, gpu, out, util
        self.url, self.name, self.proc = url.rstrip("/"), name, None

    def __enter__(self):
        if self.info["kind"] == "mock" or self.url:
            self.name = self.name or self.info.get("spec", "")
            return self
        if self.info["kind"] == "stageb":
            return self._enter_fused()
        self.name = self.name or ("zero-shot" if self.info["kind"] == "zero-shot" else "r6-model")
        port = _free_port()
        env = {**os.environ, "CUDA_VISIBLE_DEVICES": str(self.gpu), "VLLM_BATCH_INVARIANT": "1",
               "VLLM_CACHE_ROOT": "/data/harvest/cache/vllm", "TRITON_CACHE_DIR": "/data/harvest/cache/triton",
               "TORCHINDUCTOR_CACHE_DIR": "/data/harvest/cache/inductor", "CUDA_CACHE_PATH": "/data/harvest/cache/nv",
               "FLASHINFER_WORKSPACE_BASE": "/data/harvest/cache/flashinfer", "VLLM_NO_USAGE_STATS": "1",
               "DO_NOT_TRACK": "1", "VLLM_USE_FLASHINFER_SAMPLER": "0", "CC": "/data/harvest/jevl/bin/cc",
               "ZIG_GLOBAL_CACHE_DIR": "/data/harvest/cache/zig"}
        os.makedirs(self.out, exist_ok=True)
        self.log = open(os.path.join(self.out, "vllm.log"), "w")
        self.proc = subprocess.Popen(vllm_cmd(self.info["path"], self.name, port, self.util), env=env,
                                     stdout=self.log, stderr=subprocess.STDOUT, start_new_session=True)
        self.url = f"http://127.0.0.1:{port}"
        import httpx
        t0 = time.monotonic()
        while time.monotonic() - t0 < 900:
            if self.proc.poll() is not None:
                raise SystemExit(f"vLLM exited ({self.proc.returncode}), see {self.out}/vllm.log")
            try:
                if httpx.get(self.url + "/health", timeout=2).status_code == 200:
                    self.t_ready = time.monotonic() - t0
                    return self
            except httpx.HTTPError:
                pass
            time.sleep(3)
        raise SystemExit("vLLM did not become healthy in 900 s")

    def _enter_fused(self):
        """A stage-B checkpoint: the fused-model HTTP server (runtime.fused_model serve, venv_train, HF + CUDA-graph
        expert) on the model GPU -- never the Isaac render GPU."""
        import httpx
        self.name = "stageb-fused"
        port = _free_port()
        env = {**os.environ, "CUDA_VISIBLE_DEVICES": str(self.gpu), "PYTHONPATH": REPO,
               "TORCH_DISABLE_NATIVE_JIT": "1"}
        os.makedirs(self.out, exist_ok=True)
        self.log = open(os.path.join(self.out, "fused_server.log"), "w")
        self.proc = subprocess.Popen([TRAIN_PY, "-m", "harvest.runtime.fused_model", "serve", "--ckpt",
                                      self.info["path"], "--port", str(port)], env=env, cwd=REPO,
                                     stdout=self.log, stderr=subprocess.STDOUT, start_new_session=True)
        self.url = f"http://127.0.0.1:{port}"
        t0 = time.monotonic()
        while time.monotonic() - t0 < 900:
            if self.proc.poll() is not None:
                raise SystemExit(f"fused server exited ({self.proc.returncode}), see {self.out}/fused_server.log")
            try:
                if httpx.get(self.url + "/info", timeout=2).status_code == 200:
                    self.t_ready = time.monotonic() - t0
                    return self
            except httpx.HTTPError:
                pass
            time.sleep(3)
        raise SystemExit("fused server did not come up in 900 s")

    def __exit__(self, *exc):
        if self.proc is not None:
            import signal
            try:
                os.killpg(self.proc.pid, signal.SIGTERM)  # our own session only
                self.proc.wait(timeout=60)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                os.killpg(self.proc.pid, signal.SIGKILL)
            self.log.close()
        return False


class Asker:
    """Async DecCall runner on one vLLM server (clients/jevl.py acall_mm, call mode lead, §59)."""

    def __init__(self, url: str, name: str, layout: str, mode: str = "lead", timeout_s: float = 30.0):
        from ..clients.jevl import JevLClient
        self.layout, self.mode = layout, mode
        self.c = JevLClient(url, name, timeout_s=timeout_s, image_mime="image/jpeg")

    async def ask(self, line: dict, root: str, var: str = "A0", tries: int = 4) -> dict:
        req, shown = build_request(line, var)
        imgs = images_for(line, root, self.layout)
        rec, n = None, 0
        while n < tries:  # prereg (jevl_acc): 3 retries, then the items count as wrong / missing
            n += 1
            rec = await self.c.acall_mm(req, {"experiment": "R6"}, imgs, mode=self.mode, layout=self.layout)
            if rec.error is None:
                break
        ok = rec.error is None
        return {"answers": answers_to_keys(rec.answers, shown) if ok else {}, "error": rec.error, "tries": n,
                "lat": round(rec.t_done - rec.t_send, 4) if rec.t_done else None, "input_tokens": rec.input_tokens,
                "model": rec.model, "names": {q: {o.key: o.name for o in opts} for q, opts in shown.values()},
                "opts": {q: [o.key for o in opts] for q, opts in shown.values()}}

    async def close(self):
        await self.c.aclose()


class MockAsker:
    """No-GPU stand-in (plumbing checks only): answers = the labels_v2 S1 code rule, probability 1."""
    layout, mode = "H", "mock"

    async def ask(self, line: dict, root: str, var: str = "A0", tries: int = 1) -> dict:
        req, shown = build_request(line, var)
        rule = s1_rule(req["state"])
        ans = {}
        for qid, (q, opts) in shown.items():
            keys = [o.key for o in opts]
            k = rule.get(q) if rule.get(q) in keys else keys[-1]
            ans[q] = {"key": k, "name": next(o.name for o in opts if o.key == k), "p": 1.0, "probs": {k: 1.0}}
        return {"answers": ans, "error": None, "tries": 1, "lat": 0.0, "input_tokens": None, "model": "mock",
                "names": {q: {o.key: o.name for o in opts} for q, opts in shown.values()},
                "opts": {q: [o.key for o in opts] for q, opts in shown.values()}}

    async def close(self):
        pass


def s1_rule(state_text: str) -> dict:
    """The labels_v2 code rule on an S1 text, keyed by question (the fast layer's S1 score for C2', §2A.3)."""
    from ..labels_v2 import code_rule_v2
    r = code_rule_v2(state_text)
    return {"dir_xy": r.get("dir_xy"), "dir_z": r.get("dir_z"), "mag_coarse": r.get("mag_coarse"),
            "target": r.get("target"), "phase": r.get("phase_choice")}


async def run_pool(jobs, conc: int):
    """Run coroutine factories with at most `conc` in flight; returns results in job order."""
    sem = asyncio.Semaphore(conc)
    res = [None] * len(jobs)

    async def one(i, f):
        async with sem:
            res[i] = await f()
    await asyncio.gather(*(one(i, f) for i, f in enumerate(jobs)))
    return res


# ------------------------------------------------------------------------------------------ data
def load_episodes(dirs, split: str, episodes: int = 0, seeds=None) -> list:
    """Episode folders (ep<seed>.jsonl + ep<seed>.meta.json + img/) -> [{dir, seed, kind, lines, meta}]. Every
    seed is checked against the declared split (splits.check_seeds) BEFORE its file is opened."""
    from .splits import check_seeds
    out = []
    for d in dirs:
        files = sorted(glob.glob(os.path.join(d, "ep*.jsonl")), key=lambda p: int(os.path.basename(p)[2:-6]))
        cand = [int(os.path.basename(p)[2:-6]) for p in files]
        if seeds is not None:
            cand = [s for s in cand if s in seeds]
        if episodes:
            cand = cand[:episodes]
        check_seeds(cand, split)
        for s in cand:
            lines = [json.loads(x) for x in open(os.path.join(d, f"ep{s}.jsonl"), encoding="utf-8")]
            annotate_last_step(lines)  # the DecCall (b) line as in training (canon §77)
            mp = os.path.join(d, f"ep{s}.meta.json")
            meta = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {}
            out.append({"dir": d, "seed": s, "kind": lines[0].get("kind", "P0") if lines else "P0", "lines": lines,
                        "meta": meta})
    return out


def labels_v2_file(d: str) -> str:
    """POOL: <parent>/pool.labels_v2.jsonl; DEV kind folder (jsel_dev/P0): jsel_dev/P0.labels_v2.jsonl."""
    d = d.rstrip("/")
    return d + ".labels_v2.jsonl"


def load_truth(eps, truth: str, outcome_dirs=None) -> dict:
    """{(kind, seed, k): {question: set(keys)}}: labels_v2 (canon §54, primary) or outcome:<rule> (the labeler's best
    set under a pre-registered rule; NONE_ESCALATE when every option scores 0, §52 decision 1)."""
    from ..train.stagea_data import target_keys
    V2 = {"dir_xy": "dir_xy", "dir_z": "dir_z", "mag_coarse": "mag_coarse", "target": "target",
          "phase": "phase_choice"}
    want = {(e["kind"], e["seed"]) for e in eps}
    out = {}
    if truth == "labels_v2":
        for f in sorted({labels_v2_file(e["dir"]) for e in eps}):
            for x in open(f, encoding="utf-8"):
                r = json.loads(x)
                if (r["kind"], r["seed"]) in want:
                    out[(r["kind"], r["seed"], r["k"])] = {q: {r["labels_v2"][V2[q]]} for q in QUESTIONS}
        return out
    if not truth.startswith("outcome:"):
        raise SystemExit(f"--truth {truth!r}: labels_v2 | outcome:<rule>")
    rule = truth.split(":", 1)[1]
    for d in outcome_dirs or []:
        for f in glob.glob(os.path.join(d, "*.jsonl")):
            for x in open(f, encoding="utf-8"):
                r = json.loads(x)
                if (r["kind"], r["seed"]) in want and r["question"] in QUESTIONS:
                    keys, _ = target_keys(r, rule)
                    out.setdefault((r["kind"], r["seed"], r["k"]), {})[r["question"]] = set(keys)
    return out


# ------------------------------------------------------------------------------------------ metadata / outputs
def git_commit() -> dict:
    """Local git HEAD (+ dirty flag) or, on the pod copy, the CODE_VERSION file written by tools/r6/sync.sh."""
    cv = os.path.join(REPO, "CODE_VERSION")
    if os.path.isfile(cv):
        return json.load(open(cv, encoding="utf-8"))
    try:
        h = subprocess.run(["git", "-c", f"safe.directory={REPO}", "-C", REPO, "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=10).stdout.strip()
        d = subprocess.run(["git", "-c", f"safe.directory={REPO}", "-C", REPO, "status", "--porcelain"],
                           capture_output=True, text=True, timeout=30).stdout.strip()
        return {"commit": h or None, "dirty": bool(d)}
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "dirty": None}


def code_sha() -> str:
    h = hashlib.sha256()
    for p in sorted(glob.glob(os.path.join(REPO, "harvest", "**", "*.py"), recursive=True)):
        h.update(os.path.relpath(p, REPO).replace("\\", "/").encode())
        h.update(open(p, "rb").read())
    return h.hexdigest()[:16]


def bootstrap_meta(n_boot: int, unit: str) -> dict:
    """How the 95% intervals of a run were made (E-first §1.7, EVAL §4.2; canon §72): cluster bootstrap, percentile
    interval, fixed seed 0 (analysis.stats), resampling unit."""
    return {"n_boot": int(n_boot), "seed": 0, "level": 0.95, "interval": "percentile", "unit": unit,
            "prereg": "E-first §1.7 / EVAL §4.2: cluster bootstrap 10,000"}


def prereg_meta() -> dict:
    """E-first §1.7 (:133): the judgment sections' SHA-256 + registration time (docs/stage3/prereg.json) in the run
    record, with a re-hash of the current E-first text (tools/prereg_hash.py); "unavailable" without the docs."""
    import importlib.util
    try:
        saved = json.load(open(os.path.join(REPO, "docs", "stage3", "prereg.json"), encoding="utf-8"))
        spec = importlib.util.spec_from_file_location("_prereg_hash", os.path.join(REPO, "tools", "prereg_hash.py"))
        ph = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ph)
        bad = [s for s, h in ph.current().items() if saved["hashes"].get(s) != h]
    except (OSError, KeyError, ValueError) as e:
        return {"check": f"unavailable ({type(e).__name__})"}
    return {"written_utc": saved["written_utc"], "hashes": saved["hashes"],
            "check": "OK" if not bad else f"CHANGED {bad}"}


def run_meta(cmd: str, info: dict, extra: dict | None = None) -> dict:
    m = {"command": cmd, "argv": sys.argv, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
         "prereg": prereg_meta(), "git": git_commit(), "code_sha": code_sha(), "host": socket.gethostname(),
         "model": {k: v for k, v in info.items() if k != "fingerprint"}}
    if info.get("path") and info["kind"] != "mock":
        m["model"]["fingerprint"] = model_fingerprint(info["path"])
        m["model"]["train_prompt_config"] = training_prompt_config(info["path"])
    # canon §28 / §42: the latest daily canary of this model (harvest.eval.canary), or an explicit "none"
    from .canary import latest_canary
    m["canary"] = latest_canary("mock" if info["kind"] == "mock" else m["model"].get("fingerprint"))
    m.update(extra or {})
    return m


def md_table(headers, rows) -> str:
    def f(x):
        if x is None:
            return "-"
        if isinstance(x, float):
            return f"{x:.4f}"
        return str(x)
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(f(x) for x in r) + " |" for r in rows]
    return "\n".join(lines)


def ci_str(m: dict | None) -> str:
    if not m or m.get("mean") is None:
        return "-"
    lo, hi = m["ci"]
    return f"{m['mean']:.4f} [{lo:.4f}, {hi:.4f}]" if lo is not None else f"{m['mean']:.4f}"


def write_outputs(out: str, name: str, result: dict, md: str) -> None:
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, name + ".json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1, default=str)
    with open(os.path.join(out, name + ".md"), "w", encoding="utf-8") as f:
        f.write(md + "\n")
