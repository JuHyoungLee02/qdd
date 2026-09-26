"""Daily canary (canon §28 "매일 카나리", E-first §1.8; R7 cycle-1 D2) -- minimal implementation.

  python -m harvest.eval.canary build-set --data DIR[,DIR] --seeds 0-2 --n 12 --name dev_v1
      fixed DEV snapshots (decision lines, evenly spaced) copied with their frames into
      <root>/sets/<name>/ (lines.jsonl + img/ + manifest.json with the set sha); DEV seeds only (splits guard), a set
      is never rewritten.
  python -m harvest.eval.canary --model M [--set dev_v1] [--repeats 2] [--gpu 3] [--layout auto] [--force]
      the set's snapshots x the 5 decision questions (question_id@vN recorded) on model M (zero-shot | merged |
      adapter via vLLM, lead; a stage-B checkpoint via the fused server's /decide with the fused runtime's DecCall =
      the 5 + the gripper question, fused wording and qids; mock = code rule); every DecCall shows the unknown
      segment line like the runtime without an Astra plan (ser-A-min-3 fix round 1), `repeats`
      times -> <root>/canary_<YYYYMMDD UTC>_<model fingerprint>.json with an id:
        answers {"<snapshot>|<question>": [option_key per repeat]}, probs (repeat 0), floor (test-retest mismatch
        of repeats 1.. vs repeat 0 = the day's floor), baseline = the earliest other canary of the same model
        fingerprint, set and question_id@vN set (a new version starts a new baseline day, canon §79), compare = harvest.canary.canary_compare (mismatch vs the baseline's mode minus the
        floor, episode-cluster bootstrap per question, Holm over the questions, drift = a rejection with lower > 0;
        drift_suspect -> report that day's results separately and redo E1, §28; canon §73).
The runtime / eval commands read latest_canary(fingerprint)["id"] (or an explicit "none") and log it: eval run_meta
"canary", closed-loop RuntimeConfig.canary_id on every decision / chunk call row. The Astra canary (fixed inputs at effort low, plan signature) needs paid calls and is not run
(RuntimeConfig.astra_canary_id = "none"). root = $HARVEST_CANARY_ROOT or /data/harvest/canary (pod rule: /data).
"""
from __future__ import annotations

import argparse
import asyncio
import glob
import hashlib
import json
import os
import shutil
import sys
import time

QUESTIONS = ("dir_xy", "dir_z", "mag_coarse", "target", "phase")
DEFAULT_ROOT = "/data/harvest/canary"


def canary_root() -> str:
    return os.environ.get("HARVEST_CANARY_ROOT", DEFAULT_ROOT)


def _utc_date() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def _sha_file(p: str) -> str:
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


# ------------------------------------------------------------------------------------------ set
def build_set(data: str, seeds: str, n: int, name: str, root: str | None = None) -> dict:
    from .common import load_episodes
    from .e05 import parse_seeds
    root = root or canary_root()
    d = os.path.join(root, "sets", name)
    if os.path.exists(os.path.join(d, "manifest.json")):
        raise SystemExit(f"canary set {name!r} exists at {d} (a set is fixed; use a new name)")
    eps = load_episodes([x for x in data.split(",") if x], "dev", seeds=parse_seeds(seeds))  # DEV only (guard)
    cand = sorted(((e["kind"], e["seed"], ln["k"], ln, e["dir"]) for e in eps for ln in e["lines"]
                   if ln.get("decision")), key=lambda x: x[:3])
    if len(cand) < n:
        raise SystemExit(f"only {len(cand)} decision snapshots in {data} seeds {seeds}")
    pick = [cand[round(i * (len(cand) - 1) / max(1, n - 1))] for i in range(n)] if n > 1 else cand[:1]
    os.makedirs(os.path.join(d, "img"), exist_ok=True)
    lines, digests = [], {}
    for kind, seed, k, ln, src in pick:
        ln = json.loads(json.dumps(ln))
        ln.pop("oracle", None)  # never read (build_request uses a dummy oracle); not copied into the set
        ims = {}
        for cam, rel in ln["images"].items():
            dst = f"img/{kind}_ep{seed}_k{k:04d}_{cam}{os.path.splitext(rel)[1]}"
            shutil.copyfile(os.path.join(src, rel), os.path.join(d, dst))
            ims[cam] = dst
            digests[dst] = _sha_file(os.path.join(d, dst))
        ln["images"] = ims
        ln["canary_key"] = f"{kind}_ep{seed}_k{k}"
        lines.append(ln)
    with open(os.path.join(d, "lines.jsonl"), "w", encoding="utf-8") as f:
        for ln in lines:
            f.write(json.dumps(ln, sort_keys=True) + "\n")
    set_sha = hashlib.sha256((_sha_file(os.path.join(d, "lines.jsonl")) + json.dumps(digests, sort_keys=True))
                             .encode()).hexdigest()[:16]
    m = {"name": name, "set_sha": set_sha, "n": len(lines), "split": "dev", "data": data, "seeds": seeds,
         "keys": [ln["canary_key"] for ln in lines], "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    json.dump(m, open(os.path.join(d, "manifest.json"), "w", encoding="utf-8"), indent=1)
    print("CANARY_SET " + json.dumps(m), flush=True)
    return m


def load_set(name: str, root: str | None = None):
    d = os.path.join(root or canary_root(), "sets", name)
    m = json.load(open(os.path.join(d, "manifest.json"), encoding="utf-8"))
    lines = [json.loads(x) for x in open(os.path.join(d, "lines.jsonl"), encoding="utf-8")]
    return d, m, lines


# ------------------------------------------------------------------------------------------ askers
class FusedAsker:
    """A stage-B checkpoint behind runtime.fused_model serve: the fused runtime's IMG DecCall (/decide) -- the fused
    question set and wording (FUSED_QUESTIONS: + the canon §87 gripper question, PH-A1 dir_xy / mag_coarse text) and
    the runtime's context (models.fused_ctx_text: IMG state + segment line + motion line). A canary snapshot has no
    Astra plan (the runtime's unknown segment) and the snapshot's motion line (unknown without a recorded one)."""
    layout, mode = "HW", "fused"

    def __init__(self, url: str, timeout_s: float = 60.0, transport=None):
        import httpx

        from ..runtime.models import FUSED_QUESTIONS
        self.url, self.c = url.rstrip("/"), httpx.Client(timeout=timeout_s, transport=transport)
        self.questions = FUSED_QUESTIONS

    async def ask(self, line: dict, root: str, var: str = "A0", tries: int = 1) -> dict:
        import base64

        from ..runtime.fused_model import answers_from
        from ..deccall_snap import last_step_of, motion_of
        from ..runtime.models import build_live_request, fused_ctx_text
        ds = int(str(line.get("ds_id", "ds0"))[2:] or 0)
        req, shown = build_live_request(ds, line["phase"], line["text_state"], line["state"]["present"],
                                        line["state"]["obs"]["raw"], state="IMG", last_step=last_step_of(line),
                                        motion=motion_of(line), questions=self.questions)
        ims = {cam: base64.b64encode(open(os.path.join(root, line["images"][cam]), "rb").read()).decode()
               for cam in ("cam_head", "cam_wrist_right")}
        r = self.c.post(self.url + "/decide", json={"t_state": line.get("t", 0.0),
                                                    "ctx_text": fused_ctx_text(line["text_state"],
                                                                               motion=motion_of(line)),
                                                    "req": req, "images": ims})
        d = r.json()
        if r.status_code != 200:
            return {"answers": {}, "error": d.get("error", r.status_code)}
        ans = answers_from(d["probs"], shown)
        return {"answers": {q: {"key": a["choice"], "p": a["p_chosen"], "probs": a["probs"]} for q, a in ans.items()},
                "error": None}

    async def close(self):
        self.c.close()


async def _ask_all(asker, lines, root, repeats):
    out = []
    for _ in range(repeats):  # sequential: a canary is small and must not race other GPU work
        out.append([await asker.ask(ln, root) for ln in lines])
    await asker.close()
    return out


# ------------------------------------------------------------------------------------------ run
def _tv(p: dict, q: dict) -> float:
    ks = set(p) | set(q)
    return 0.5 * sum(abs(float(p.get(k, 0.0)) - float(q.get(k, 0.0))) for k in ks)


def canary_files(fp: str, root: str | None = None) -> list:
    return sorted(glob.glob(os.path.join(root or canary_root(), f"canary_*_{fp}.json")))


def latest_canary(fp: str | None, root: str | None = None) -> dict:
    """{"id", "date_utc", "file", "drift_suspect", "stale"} of the newest canary of this model fingerprint, or
    {"id": "none", "reason"} (logged as such: the canon asks for the id, "none" says explicitly there was none)."""
    if not fp:
        return {"id": "none", "reason": "no model fingerprint"}
    fs = canary_files(fp, root)
    if not fs:
        return {"id": "none", "reason": f"no canary for model fingerprint {fp}"}
    d = json.load(open(fs[-1], encoding="utf-8"))  # canary_<YYYYMMDD>_<fp>.json: name order = date order
    last_drift = None  # the newest drift-suspect canary of this model (J5 stays off until a later E1 re-run)
    for f in reversed(fs):
        x = d if f == fs[-1] else json.load(open(f, encoding="utf-8"))
        if x.get("drift_suspect") is True:
            last_drift = {"id": x["id"], "date_utc": x["date_utc"], "file": f}
            break
    return {"id": d["id"], "date_utc": d["date_utc"], "file": fs[-1], "drift_suspect": d.get("drift_suspect"),
            "stale": d["date_utc"] != _utc_date(), "last_drift": last_drift}


def select_baseline(runs, set_sha: str, question_ids: dict):
    """The baseline day = the earliest canary (runs in date order) of the same fixed set AND the same
    question_id@vN set (E §1.8 :136-140 "고정 스냅샷 × 고정 question_id@vN", "기준일 = 카나리 세트를 처음 돌린 날";
    canon §77 "질문 id·프롬프트가 바뀜 → 새 기준일"). None -> this run is the first day of its version (canon §79)."""
    for d in runs:
        if d.get("set", {}).get("set_sha") == set_sha and d.get("question_ids") == question_ids:
            return d
    return None


def canary_id_for(model_path: str | None, mock: bool = False, root: str | None = None) -> str:
    """The canary id the runtime logs for a model dir (fingerprint as eval.common) or a mock model."""
    if mock:
        return latest_canary("mock", root)["id"]
    if not model_path or not os.path.isdir(model_path):
        return "none"
    from .common import model_fingerprint
    return latest_canary(model_fingerprint(model_path), root)["id"]


def run_canary(a) -> dict:
    from . import common as C
    from ..canary import canary_compare
    from ..runtime.run_r5 import question_ids
    root = canary_root()
    os.makedirs(root, exist_ok=True)
    os.environ.setdefault("HARVEST_QID_REGISTRY", os.path.join(root, "qid_registry.json"))
    sdir, man, lines = load_set(a.set, root)
    info = C.ensure_merged(C.resolve_model(a.model), os.path.join(root, "work"))
    fp = "mock" if info["kind"] == "mock" else C.model_fingerprint(info["path"])
    date = _utc_date()
    path = os.path.join(root, f"canary_{date.replace('-', '')}_{fp}.json")
    if os.path.exists(path) and not a.force:
        raise SystemExit(f"{path} exists (id {json.load(open(path, encoding='utf-8'))['id']}); --force to redo")
    pc = C.training_prompt_config(info["path"]) if info["kind"] != "mock" else None
    layout = "HW" if info["kind"] == "stageb" else (C.default_layout(pc) if a.layout == "auto" else a.layout)
    state = "IMG" if info["kind"] == "stageb" else "S1-1mm"
    from ..runtime.models import FUSED_QUESTIONS
    asked = FUSED_QUESTIONS if info["kind"] == "stageb" else QUESTIONS  # a stage-B model: the fused runtime DecCall
    qids = question_ids(layout if info["kind"] != "mock" else "H", state,
                        FUSED_QUESTIONS if info["kind"] == "stageb" else None)
    t0 = time.monotonic()
    with C.Server(info, a.gpu, os.path.join(root, "work", "server"), a.url, a.served_name, a.gpu_util) as srv:
        if info["kind"] == "mock":
            asker = C.MockAsker()
        elif info["kind"] == "stageb":
            asker = FusedAsker(srv.url)
        else:
            asker = C.Asker(srv.url, srv.name, layout, mode="lead")
        res = asyncio.run(_ask_all(asker, lines, sdir, a.repeats))
    answers, probs, errors = {}, {}, 0
    for rep in res:
        for ln, r in zip(lines, rep):
            errors += int(r.get("error") is not None)
            for q in asked:
                a_ = (r.get("answers") or {}).get(q)
                key = f"{ln['canary_key']}|{q}"
                answers.setdefault(key, []).append(a_["key"] if a_ else None)
                if a_ and key not in probs:
                    probs[key] = a_.get("probs") or {}
    later = [v != vs[0] for vs in answers.values() for v in vs[1:]]
    floor = sum(later) / len(later) if later else 0.0
    base = select_baseline((json.load(open(f, encoding="utf-8")) for f in canary_files(fp, root) if f != path),
                           man["set_sha"], qids)
    compare, tv = None, None
    if base is not None:
        common = sorted(set(base["answers"]) & set(answers))
        compare = canary_compare({k: base["answers"][k] for k in common}, {k: answers[k] for k in common}, floor)
        tvs = [_tv(base["probs"][k], probs[k]) for k in common if k in base.get("probs", {}) and k in probs]
        tv = sum(tvs) / len(tvs) if tvs else None
    body = {"answers": answers, "probs": probs}
    cid = f"cn{date.replace('-', '')}_{fp[:8]}_" + hashlib.sha256(
        (json.dumps(body, sort_keys=True) + time.strftime("%H%M%S", time.gmtime())).encode()).hexdigest()[:6]
    out = {"id": cid, "date_utc": date, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "model": {"spec": a.model, "kind": info["kind"], "path": info.get("path"), "fingerprint": fp},
           "set": {"name": a.set, "set_sha": man["set_sha"], "n": man["n"]}, "layout": layout, "state": state,
           "question_ids": qids, "repeats": a.repeats, "errors": errors, "floor": round(floor, 4),
           "baseline": None if base is None else {"id": base["id"], "date_utc": base["date_utc"]},
           "compare": compare, "prob_tv_mean": tv,
           "drift_suspect": None if compare is None else bool(compare["drift_suspect"]),
           "code_sha": C.code_sha(), "git": C.git_commit(), "runtime_s": round(time.monotonic() - t0, 1),
           **body}
    json.dump(out, open(path, "w", encoding="utf-8"), indent=1)
    print("CANARY " + json.dumps({k: out[k] for k in ("id", "date_utc", "floor", "baseline", "drift_suspect",
                                                         "errors", "runtime_s")}), flush=True)
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv[:1] == ["build-set"]:
        b = argparse.ArgumentParser(prog="python -m harvest.eval.canary build-set")
        b.add_argument("--data", required=True, help="DEV episode folder(s), comma separated")
        b.add_argument("--seeds", default="0-2")
        b.add_argument("--n", type=int, default=12)
        b.add_argument("--name", default="dev_v1")
        x = b.parse_args(argv[1:])
        return build_set(x.data, x.seeds, x.n, x.name)
    ap = argparse.ArgumentParser(prog="python -m harvest.eval.canary", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, help="zero-shot | merged | adapter | stage-B ckpt | mock")
    ap.add_argument("--set", default="dev_v1")
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--gpu", default="3", help="model GPU (vLLM / fused server; never an Isaac render GPU)")
    ap.add_argument("--gpu-util", type=float, default=0.30)
    ap.add_argument("--url", default="", help="an already running server (skips starting one)")
    ap.add_argument("--served-name", default="")
    ap.add_argument("--layout", default="auto")
    ap.add_argument("--force", action="store_true", help="redo today's canary of this model (new id)")
    return run_canary(ap.parse_args(argv))


if __name__ == "__main__":
    main()
