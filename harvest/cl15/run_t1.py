"""E-CL15 T1 (docs/stage3/prereg_cl15.md): the E-M35CL runner (harvest.teach_pt.run_closed_l8s, unchanged) on L8S
held-out episodes, with the visual environment switched to the held-out ("ood") split of every appearance library
the L8S renders draw from: iTHOR room backgrounds (fx.room_split, 20 % by name hash), Poly Haven materials and
indoor HDRIs (materials.split_of, 20 % by id hash). L8S training renders only ever drew the "train" split
(run_collect: rooms "train" unless split ood_s, materials.pick default "train", hdr_paths(cat, "train")).
Scene geometry, objects, task and seed stay the L8S episode's. Same arguments as run_closed_l8s.
The patched draws are logged to <out>/env_used.jsonl (one line per process) for the overlap check."""
from __future__ import annotations

import json
import os
import sys

USED = {"rooms": set(), "hdr": set(), "materials": set()}


def patch(log_path: str | None = None) -> None:
    from ..sim.assets_x import materials as M
    from ..teach_l8d import fx
    rooms0, pick0, hdr0 = fx.rooms_of, M.pick, M.hdr_paths

    def rooms_ood(directory, split):
        r = rooms0(directory, "ood")
        USED["rooms"].update(r)
        return r

    def pick_ood(cat, role, seed, split="train"):
        rec = pick0(cat, role, seed, "ood")
        USED["materials"].add(rec.get("id") or rec.get("name") or str(rec.get("files", {}).get("diff")))
        return rec

    def hdr_ood(cat, split="train", root=M.ROOT):
        h = hdr0(cat, "ood", root)
        USED["hdr"].update(os.path.basename(p) for p in h)
        return h
    fx.rooms_of, M.pick, M.hdr_paths = rooms_ood, pick_ood, hdr_ood
    if log_path:
        import atexit

        def dump():
            with open(log_path, "a") as f:
                f.write(json.dumps({k: sorted(v) for k, v in USED.items()} | {"pid": os.getpid()}) + "\n")
        atexit.register(dump)


TOKEN = "/data/.openai_token"


def take(argv: list, flag: str, default=None, has_value: bool = True):
    """Remove `flag` (and its value) from argv -> its value (True for a bare flag), else default."""
    if flag not in argv:
        return default
    i = argv.index(flag)
    if not has_value:
        argv.pop(i)
        return True
    v = argv[i + 1]
    del argv[i:i + 2]
    return v


def stub_transport(answer: str):
    """Fake Responses-API stream (dry runs): every call returns `answer` with a fixed usage; no network, no cost."""
    import httpx

    def handler(req):
        ev = [{"type": "response.output_text.delta", "delta": answer},
              {"type": "response.completed", "response": {"model": "stub", "status": "completed",
                                                          "usage": {"input_tokens": 3000, "output_tokens": 1500}}}]
        body = "".join(f"data: {json.dumps(e)}\n\n" for e in ev).encode()
        return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})
    return httpx.MockTransport(handler)


STUB_ANSWER = json.dumps({"assessment": {"task_progress": {"verified_completed": [], "currently_attempting": "stub",
                                                           "remaining": []}, "execution_status": "progressing",
                                         "evidence": "stub", "evidence_view": "head", "confidence": "low"},
                          "command": {"mode": "point", "point_2d": [500, 600], "height": "above", "gripper": "keep"},
                          "reason": "stub"})


def astra_factory(effort: str, ledger_path: str, cap_krw: float, stop_file: str, tag: str, stub: bool):
    """-> a LocalVLM drop-in (same constructor arguments, ignored) that is the qdd Astra client
    (harvest.astra_solo.models.SoloAstra: Responses API, PNG detail high, shared cost ledger with a pre-call hard
    stop = cap_krw incl. calls in flight). BudgetStop -> touch stop_file (the lane stops between episodes), re-raise.
    Every ledger row carries tag (episode list) and the call's latency / tokens / cost (cost.Ledger)."""
    from ..astra_motion.cost import BudgetStop, Ledger
    from ..astra_solo.models import SoloAstra

    def make(*_a, **_k):
        tok = "stub" if stub else open(TOKEN).read().strip()
        m = SoloAstra(tok, effort, Ledger(ledger_path, hard_krw=cap_krw), transport=stub_transport(STUB_ANSWER)
                      if stub else None, cache_key="cl15c")
        ask0 = m.ask

        def ask(text, images, meta):
            try:
                return ask0(text, images, dict(meta or {}, cl15=tag))
            except BudgetStop:
                open(stop_file, "w").write(f"BudgetStop {tag}\n")
                raise
        m.ask = ask
        return m
    return make


def budget_gate(ledger_path: str, cap_krw: float, est_krw: float) -> str | None:
    """Before an episode (one process = one episode here): cum + 1.25 x (mean KRW of finished episodes in the
    ledger, else est_krw) must stay <= cap (the astra_solo gate) -> None, else the reason."""
    if not os.path.exists(ledger_path):
        return None
    rows = [json.loads(x) for x in open(ledger_path) if x.strip()]
    cum = sum(float(r["cost_krw"]) for r in rows)
    per = {}
    for r in rows:
        t = (r.get("meta") or {}).get("cl15")
        per[t] = per.get(t, 0.0) + float(r["cost_krw"])
    mean = sum(per.values()) / len(per) if per else est_krw
    nxt = 1.25 * max(mean, 1.0)
    return None if cum + nxt <= cap_krw else f"cum {cum:.0f} + 1.25 x mean {mean:.0f} KRW > cap {cap_krw:.0f}"


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    effort = take(argv, "--astra")  # E-CL15c: Astra arm (paid; started by the main session only)
    ledger = take(argv, "--ledger", "/data/harvest/out/cl15c/ledger.jsonl")
    cap = float(take(argv, "--cap-krw", "10000"))
    est = float(take(argv, "--est-krw", "2500"))
    stub = bool(take(argv, "--astra-stub", False, has_value=False))
    out = argv[argv.index("--out") + 1]
    os.makedirs(out, exist_ok=True)
    if effort:
        stop = [f for f in argv[argv.index("--yield-files") + 1].split(",") if f][0]
        why = budget_gate(ledger, cap, est)
        if why:
            open(stop, "w").write(f"budget gate: {why}\n")
            print("BUDGET_GATE " + why, flush=True)
            os._exit(3)
        tag = argv[argv.index("--episodes") + 1]
        from ..astra_solo import models as AM
        AM.LocalVLM = astra_factory(effort, ledger, cap, stop, tag, stub)
        print("ASTRA " + json.dumps({"effort": effort, "ledger": ledger, "cap_krw": cap, "stub": stub}), flush=True)
    patch(None)
    from ..teach_pt import run_closed_l8s as R
    _exit = os._exit

    def exit_dump(code):  # run_closed_l8s ends with os._exit (atexit would not run)
        with open(os.path.join(out, "env_used.jsonl"), "a") as f:
            f.write(json.dumps({k: sorted(v) for k, v in USED.items()} | {"pid": os.getpid()}) + "\n")
        _exit(code)
    os._exit = exit_dump
    R.main(argv)


if __name__ == "__main__":
    main()
