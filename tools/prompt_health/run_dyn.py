"""Dynamic prompt tests with a free local VLM (vLLM OpenAI chat server) for the prompt health check (user-log 96).
No simulator, no paid calls: fixed snapshot sets only.
  G set = probe G1 v2 grasp snapshots (40; head / left wrist / right wrist PNG + meta: sim holding truth, TCP, cameras)
  R set = R2 eval decision snapshots (E-MA2 view, data/ma2/eval_set.json; head + right wrist JPEG, stage-B aux truth)
Tests (one JSONL row per call, resumable by key):
  grasp     probe GRASP_Q (all three cameras, no overlay) x variants.GRASP_VARIANTS  -- G set
  couple_g  astra-couple@v1 F0 through the production LocalVLMAstra adapter x variants.COUPLE_VARIANTS, images with the
            production coupling overlay (tip ring, trace, axes) drawn from the snapshot's camera models -- G set
  couple_r  astra-couple@v1 F0, raw head + right-wrist images (the R set has no camera models) -- R set
  frame     variants.frame_prompt: direction toward the pick object, with / without the axis definition -- R set rows
            in the approach phase, object > 5 cm away in xy
Consistency: every test also runs the base variant again at temperature 0 (rep 1) and n_hot samples at 0.7 (seed=rep).
usage (pod): python tools/prompt_health/run_dyn.py --test grasp --url http://127.0.0.1:8361 --served qwen8b \
             --label qwen8b --out /data/harvest/logs/prompt_health/dyn.jsonl"""
from __future__ import annotations

import argparse
import base64
import json
import os
import random
import time

import httpx
import numpy as np

from harvest.astra_motion import prompts as PR
from harvest.astra_motion import schema as SC
from harvest.couple import prompt as CP
from harvest.couple import schema as CS
from harvest.couple.gate import gate_answer
from harvest.couple.local_vlm import LocalVLMAstra, to_chat
from harvest.couple.params import CoupleParams

try:  # run as a script (python tools/prompt_health/run_dyn.py) or as a module
    from tools.prompt_health import variants as V
except ImportError:  # pragma: no cover
    import variants as V  # type: ignore

G_SNAPS = "/data/harvest/out/astra_motion/grasp_snaps_v2"
R_ROOT = "/data/harvest/data/ma2"
R2_TRAIN = "/data/harvest/r2/train"
CAM_OF = {"head": "cam_head", "wrist_left": "cam_wrist_left", "wrist": "cam_wrist_right"}
G_LABEL = {"head": "head camera", "wrist_left": "left wrist camera", "wrist": "right wrist camera"}
PHASE_OF_STATE = {"pre": "descend", "closed": "close", "grasped": "lift", "miss": "lift"}
TGT_NAME = {"bottle_tray": "green bottle", "mug_tray": "red mug", "mug_marker": "red mug"}
MAX_OUT = {"grasp": 400, "couple_g": 1200, "couple_r": 1200, "frame": 200}  # couple = production max_output_tokens


# ----------------------------------------------------------------------------------------------- snapshot sets
def g_snaps(root: str = G_SNAPS) -> list:
    out = []
    for ep in sorted(os.listdir(root)):
        for st in ("pre", "closed", "grasped", "miss"):
            sd = os.path.join(root, ep, st)
            if os.path.isdir(sd):
                out.append((f"{ep}/{st}", sd, json.load(open(os.path.join(sd, "meta.json")))))
    return out


def _read_jsonl_k(path: str, ks: set) -> dict:
    out = {}
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            if r.get("k") in ks:
                out[r["k"]] = r
    return out


def r_rows(root: str = R_ROOT) -> list:
    """All R-set eval ids joined with their view row (images, phase, instruction) and stage-B row (aux truth)."""
    ids = json.load(open(os.path.join(root, "eval_set.json")))["ids"]
    by_file: dict = {}
    for i in ids:
        v, task, kind, ep, k = i.split("/")
        by_file.setdefault((v, task, kind, ep), set()).add(int(k[1:]))
    stageb: dict = {}
    out = []
    for (v, task, kind, ep), ks in sorted(by_file.items()):
        view = _read_jsonl_k(os.path.join(root, "view", v, task, kind, f"{ep}.jsonl"), ks)
        sk = (v, task, kind)
        if sk not in stageb:
            stageb[sk] = {}
            with open(os.path.join(root, "view", v, task, f"{kind}.eval.stageb.jsonl")) as f:
                for line in f:
                    r = json.loads(line)
                    stageb[sk][(r["seed"], r["k"])] = r
        seed = int(ep[2:])
        for k in sorted(ks):
            vr, sb = view.get(k), stageb[sk].get((seed, k))
            if vr is None or sb is None:
                continue
            out.append({"id": f"{v}/{task}/{kind}/{ep}/k{k}", "variant": v, "task": task, "kind": kind, "seed": seed,
                        "k": k, "phase": vr["phase"], "instruction": vr["instruction"], "images": vr["images"],
                        "img_dir": os.path.join(R2_TRAIN, v, task, kind), "grip_pos": vr["state"]["obs"]["raw"]["grip"]["pos"],
                        "grip_w": vr["state"]["obs"]["raw"]["grip"]["w"], "reg": sb["aux"]["reg"],
                        "holding": bool(sb["aux"]["cls"]["holding_tgt"]), "phase_id": sb.get("phase_id")})
    return out


def sample_r(rows: list, n: int, seed: int = 96) -> list:
    """Stratified: n rows spread evenly over (variant, task), holding true / false balanced within each cell."""
    rng = random.Random(seed)
    cells: dict = {}
    for r in rows:
        cells.setdefault((r["variant"], r["task"], r["holding"]), []).append(r)
    keys = sorted(cells)
    for k in keys:
        rng.shuffle(cells[k])
    out, i = [], 0
    while len(out) < n and any(cells[k] for k in keys):
        k = keys[i % len(keys)]
        if cells[k]:
            out.append(cells[k].pop())
        i += 1
    return sorted(out, key=lambda r: r["id"])


def frame_rows(rows: list, n: int, seed: int = 96) -> list:
    ok = [r for r in rows if r["phase"] == "approach" and not r["holding"]
          and float(np.hypot(r["reg"]["g2tgt_dx"], r["reg"]["g2tgt_dy"])) > 0.05]
    random.Random(seed).shuffle(ok)
    return sorted(ok[:n], key=lambda r: r["id"])


def r_head_overlay(r: dict) -> bytes:
    """Production coupling overlay (tip ring + robot-frame axes; no trace / arrows: the R set has no history or
    decision here) on the R2 head image, from the fixed R2 head camera (harvest/train/r2_ma2.py, Isaac convention
    +X optical / +Y left / +Z up -> the overlay's OpenCV convention) and the grip position (table frame + table top)."""
    import io

    from PIL import Image

    from harvest.couple.overlay import CamModel, draw_overlay
    from harvest.runtime.models import jpeg_bytes
    from harvest.train import r2_ma2 as M
    R = np.asarray(M.HEAD_R, float)
    R_cv = np.stack([-R[:, 1], -R[:, 2], R[:, 0]], 1)
    K = [[M.HEAD_K["fx"], 0, M.HEAD_K["cx"]], [0, M.HEAD_K["fy"], M.HEAD_K["cy"]], [0, 0, 1]]
    cam = CamModel.from_dict({"K": K, "R": R_cv.tolist(), "t": M.HEAD_POS.tolist(), "W": M.HEAD_K["width"],
                              "H": M.HEAD_K["height"]})
    img = np.asarray(Image.open(io.BytesIO(r_image(r, "cam_head"))).convert("RGB"))
    tip = np.asarray(r["grip_pos"], float) + np.array([0.0, 0.0, M.TABLE_TOP_Z])
    return jpeg_bytes(draw_overlay(img, cam, tip=tip, trace=[], next_vec=None, offset_vec=None, wrist=False))


def r_image(r: dict, cam: str) -> bytes:
    rel = r["images"][cam]
    for base in (os.path.join(R_ROOT, "view", r["variant"], r["task"], r["kind"]), r["img_dir"]):
        p = os.path.join(base, rel)
        if os.path.exists(p):
            return open(p, "rb").read()
    raise FileNotFoundError(rel)


# ----------------------------------------------------------------------------------------------- images
def g_png(sd: str, k: str) -> bytes:
    return open(os.path.join(sd, f"{k}.png"), "rb").read()


def g_couple_images(sd: str, meta: dict) -> dict:
    """Production coupling overlay (couple/overlay.draw_overlay) on the G snapshot, JPEG q90 like the driver."""
    from PIL import Image

    from harvest.couple.overlay import CamModel, draw_overlay
    from harvest.runtime.models import jpeg_bytes
    out = {}
    tip = np.asarray(meta["tcp"], float)
    trace = [np.asarray(p, float) for p in meta["trace"]][-75:]  # 2.5 s at 30 Hz (trace_s)
    for k, cam_name in CAM_OF.items():
        c = meta["cams"][k]
        K = [[c["fx"], 0, c["cx"]], [0, c["fy"], c["cy"]], [0, 0, 1]]
        cam = CamModel.from_dict({"K": K, "R": c["R"], "t": c["t"], "W": c["W"], "H": c["H"]})
        img = np.asarray(Image.open(os.path.join(sd, f"{k}.png")).convert("RGB"))
        img = draw_overlay(img, cam, tip=tip, trace=trace, next_vec=None, offset_vec=None, wrist=cam_name != "cam_head")
        out[cam_name] = jpeg_bytes(img)
    return out


# ----------------------------------------------------------------------------------------------- requests
def g_request(meta: dict, cams: list) -> dict:
    tip = [round(float(v), 4) for v in meta["tcp"]]
    return {"schema": CS.SCHEMA_ID, "mode": "F0", "request_no": 1, "t_state": 0.0, "task": meta["gt"]["instruction"],
            "active_arm": "right", "cameras": list(cams), "tip_now_m": tip,
            "vla_now": {"stage": "S1", "phase": PHASE_OF_STATE[meta["gt"]["state"]], "committed": {},
                        "next_motion_m": None, "motion": None},
            "predicted_ee_at_arrival": {"pos_m": tip, "horizon_s": 9.3, "gripper": "unknown",
                                        "method": "0.5 s tip velocity x horizon (capped) + remaining correction"},
            "events": [], "trace_uv": {}}


def r_request(r: dict, cams: list) -> dict:
    tip = [round(float(v), 4) for v in r["grip_pos"]]
    return {"schema": CS.SCHEMA_ID, "mode": "F0", "request_no": 1, "t_state": 0.0, "task": r["instruction"],
            "active_arm": "right", "cameras": list(cams), "tip_now_m": tip,
            "vla_now": {"stage": "S1", "phase": r["phase"], "committed": {}, "next_motion_m": None, "motion": None},
            "predicted_ee_at_arrival": {"pos_m": tip, "horizon_s": 9.3,
                                        "gripper": "open" if r["grip_w"] > 0.08 else "closed",
                                        "method": "0.5 s tip velocity x horizon (capped) + remaining correction"},
            "events": [], "trace_uv": {}}


# ----------------------------------------------------------------------------------------------- model calls
class Chat:
    def __init__(self, url: str, served: str, timeout_s: float = 180.0):
        self.url, self.served = url.rstrip("/"), served
        self._c = httpx.Client(timeout=timeout_s)
        self.adapter = LocalVLMAstra(url, served, timeout_s=timeout_s)

    def ask(self, messages: list, max_tokens: int, temperature: float, seed: int) -> dict:
        body = {"model": self.served, "messages": messages, "max_tokens": max_tokens, "temperature": temperature,
                "seed": seed}
        t0 = time.monotonic()
        try:
            r = self._c.post(f"{self.url}/v1/chat/completions", json=body)
            if r.status_code != 200:
                return {"text": "", "error": f"http_{r.status_code}", "latency_s": time.monotonic() - t0}
            d = r.json()
            u = d.get("usage") or {}
            return {"text": d["choices"][0]["message"]["content"] or "", "error": None,
                    "latency_s": time.monotonic() - t0, "in_tok": u.get("prompt_tokens"),
                    "out_tok": u.get("completion_tokens"), "finish": d["choices"][0].get("finish_reason")}
        except httpx.HTTPError as e:
            return {"text": "", "error": type(e).__name__, "latency_s": time.monotonic() - t0}

    def couple(self, inp: list, max_tokens: int, temperature: float, seed: int) -> dict:
        if temperature == 0.0 and seed == 0:  # the production adapter path (temperature 0, seed 0)
            rec = self.adapter.call(inp, "low", max_tokens, {"prompt_health": True})
            return {"text": rec.output_text, "error": rec.error, "latency_s": rec.t_done - rec.t_send,
                    "in_tok": (rec.usage or {}).get("input_tokens"), "out_tok": (rec.usage or {}).get("output_tokens"),
                    "adapter": True}
        return self.ask(to_chat(inp), max_tokens, temperature, seed)


def _b64(png: bytes, mime: str) -> str:
    return f"data:{mime};base64," + base64.b64encode(png).decode()


def grasp_messages(text: str, labelled: list) -> list:
    """Same layout as astra_motion.models.LocalVLM.ask: text, then 'Image i: label' + image."""
    content = [{"type": "text", "text": text}]
    for i, (label, png) in enumerate(labelled):
        content.append({"type": "text", "text": f"Image {i + 1}: {label}"})
        content.append({"type": "image_url", "image_url": {"url": _b64(png, "image/png")}})
    return [{"role": "user", "content": content}]


# ----------------------------------------------------------------------------------------------- parsing
def parse_grasp(text: str) -> dict:
    p, err = SC.validate("G", text)
    return {"valid": p is not None, "errors": err[:3], "grasp_state": (p or {}).get("grasp_state"),
            "evidence_view": (p or {}).get("evidence_view"), "confidence": (p or {}).get("confidence")}


def grasp_claim(claims) -> str:
    kinds = {k for k, _ in claims}
    if "grasped" in kinds:
        return "grasped"
    if "not_grasped" in kinds:
        return "not_grasped"
    return "none"


def parse_couple(text: str, cams: list, p) -> dict:
    try:
        a = CS.parse_answer(text, "F0", cams, 1, 0.0, 1.0)
    except CS.SchemaError as e:
        return {"valid": False, "errors": e.problems[:3]}
    raw_claims = [list(c) for c in a.claims]
    out = {"valid": True, "errors": [], "execution": a.execution, "intent": a.intent, "confidence": a.confidence,
           "command_raw": a.command, "claims_raw": raw_claims, "claim_raw": grasp_claim(a.claims),
           "edit_dp": None if a.edit is None else [round(float(v), 4) for v in a.edit.dp],
           "edit_gripper": None if a.edit is None else a.edit.gripper, "evidence_views": list(a.evidence_views),
           "info_request": a.info_request}
    g = gate_answer(a, p, {})
    out.update(gate=g.gate, command=g.command, claim_gated=grasp_claim(g.claims), notes=list(g.notes))
    return out


def parse_frame(text: str) -> dict:
    try:
        d = CS.extract_json(text)
    except CS.SchemaError as e:
        return {"valid": False, "errors": e.problems[:2]}
    v = d.get("delta_position_m")
    if not (isinstance(v, list) and len(v) == 3 and all(isinstance(x, (int, float)) and not isinstance(x, bool)
                                                        for x in v)):
        return {"valid": False, "errors": ["delta_position_m: 3 numbers"]}
    dp = [float(x) for x in v]
    return {"valid": True, "errors": [], "dp": dp,
            "over_limit": float(np.linalg.norm(dp)) > CS.EDIT_MAX_M + CS.TOL}  # production parse_answer rejects these


# ----------------------------------------------------------------------------------------------- runner
def plan(test: str, n_hot: int) -> list:
    vs = {"grasp": V.GRASP_VARIANTS, "couple_g": V.COUPLE_VARIANTS, "couple_r": V.COUPLE_VARIANTS,
          "frame": V.FRAME_VARIANTS}[test]
    out = [(v, 0.0, 0) for v in vs] + [("base" if test != "frame" else "prod", 0.0, 1)]
    out += [("base" if test != "frame" else "prod", 0.7, r) for r in range(n_hot)]
    return out


def run(a) -> None:
    chat = Chat(a.url, a.served)
    p = CoupleParams()
    done = set()
    if os.path.exists(a.out):
        for line in open(a.out):
            r = json.loads(line)
            done.add((r["test"], r["snap"], r["variant"], r["temp"], r["rep"], r["model"]))
    if a.test in ("grasp", "couple_g"):
        items = [(k, (sd, meta)) for k, sd, meta in g_snaps(a.g_snaps)]
    else:
        rows = r_rows(a.r_root)
        sel = sample_r(rows, a.n_r) if a.test == "couple_r" else frame_rows(rows, a.n_r)
        items = [(r["id"], r) for r in sel]
    if a.limit:
        items = items[:a.limit]
    only = set(a.only.split(",")) if a.only else None
    cache: dict = {}
    for variant, temp, rep in plan(a.test, a.n_hot):
        if only and variant not in only:
            continue
        for key, obj in items:
            if (a.test, key, variant, temp, rep, a.label) in done:
                continue
            row = {"test": a.test, "snap": key, "variant": variant, "temp": temp, "rep": rep, "model": a.label}
            if a.test == "grasp":
                sd, meta = obj
                text, order = V.grasp_prompt(variant, PR.OBJ_NAME[meta["gt"]["tgt"]])
                labelled = [(G_LABEL[k], g_png(sd, k)) for k in order]
                res = chat.ask(grasp_messages(text, labelled), MAX_OUT["grasp"], temp, rep)
                row.update(truth=meta["gt"]["holding"], state=meta["gt"]["state"], **parse_grasp(res["text"]))
            elif a.test == "couple_g":
                sd, meta = obj
                if key not in cache:
                    cache.clear()
                    cache[key] = g_couple_images(sd, meta)
                images = cache[key]
                cams = list(p.cameras)
                req = g_request(meta, cams)
                inp = V.couple_input(variant, req, images, p, meta["gt"]["instruction"])
                text = inp[0]["content"][0]["text"]
                res = chat.couple(inp, MAX_OUT["couple_g"], temp, rep)
                row.update(truth=meta["gt"]["holding"], state=meta["gt"]["state"], **parse_couple(res["text"], cams, p))
            elif a.test == "couple_r":
                r = obj
                cams = [c for c in p.cameras if c in r["images"]]
                images = {c: r_image(r, c) for c in cams}
                req = r_request(r, cams)
                inp = V.couple_input(variant, req, images, p, r["instruction"])
                text = inp[0]["content"][0]["text"]
                res = chat.couple(inp, MAX_OUT["couple_r"], temp, rep)
                row.update(truth=r["holding"], state=r["phase"], **parse_couple(res["text"], cams, p))
            else:
                r = obj
                text = V.frame_prompt(variant, r["instruction"], TGT_NAME[r["task"]])
                content = [{"type": "input_text", "text": text}]
                for c in ("cam_head", "cam_wrist_right"):
                    b = r_head_overlay(r) if (c == "cam_head" and variant.endswith("_ov")) else r_image(r, c)
                    content.append({"type": "input_text", "text": f"{c}:"})
                    content.append({"type": "input_image", "image_url": _b64(b, "image/jpeg")})
                res = chat.ask(to_chat([{"role": "user", "content": content}]), MAX_OUT["frame"], temp, rep)
                truth = [r["reg"]["g2tgt_dx"], r["reg"]["g2tgt_dy"], r["reg"]["g2tgt_dz"]]
                row.update(truth=[round(float(x), 4) for x in truth], state=r["phase"], **parse_frame(res["text"]))
            if a.test == "grasp":
                row["prompt_sha"] = V.sha12(text)
            else:
                row["prompt_sha"] = V.sha12(text if a.test == "frame" else
                                            V.couple_template(variant)[0] + V.couple_template(variant)[2])
            row.update(raw=(res["text"] or "")[:1500], api_error=res["error"], latency_s=round(res["latency_s"], 3),
                       in_tok=res.get("in_tok"), out_tok=res.get("out_tok"))
            with open(a.out, "a") as f:
                f.write(json.dumps(row) + "\n")
        print(f"DONE {a.test} {variant} t{temp} r{rep}", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", required=True, choices=("grasp", "couple_g", "couple_r", "frame"))
    ap.add_argument("--url", required=True)
    ap.add_argument("--served", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--g-snaps", default=G_SNAPS)
    ap.add_argument("--r-root", default=R_ROOT)
    ap.add_argument("--n-r", type=int, default=60)
    ap.add_argument("--n-hot", type=int, default=3)
    ap.add_argument("--only", default="")
    ap.add_argument("--limit", type=int, default=0, help="first N snapshots only (smoke)")
    run(ap.parse_args(argv))


if __name__ == "__main__":
    main()
