"""E3-lite (docs/stage3/results/e3lite.md prereg): state S0/S1/S2 x input x model x option order on DEV snapshots.

usage (pod, next to vLLM):
  python jevl_e3lite.py ub  --dev DIR --out JSON                         code-rule upper bound + majority baseline
  python jevl_e3lite.py acc --dev DIR --model M --port P --outdir D --conds S0:img:fixed,S1:txt:rot,...
  python jevl_e3lite.py lat --dev DIR --model M --port P --out JSONL --states S0,S1,S2 [--n 4 --calls 200]
One acc row per (snapshot, question), file <outdir>/acc_<model>_<S>_<img|txt>_<fixed|rot>.jsonl (resumable).
"""
import argparse
import asyncio
import json
import os
import random
import sys
import time
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jevl_acc import snapshots  # noqa: E402

from harvest.clients.jevl import JevLClient  # noqa: E402
from harvest.deccall_snap import QUESTIONS, ORACLE_FIELD, build_snapshot_request, score  # noqa: E402
from harvest.e3lite import code_rule, state_text  # noqa: E402


def key(s):
    return f"{s['kind']}_s{s['seed']}_k{s['k']}"


def ub(a):
    snaps = snapshots(a.dev)
    ok = {m: defaultdict(list) for m in ("UB", "UB_raw", "majority")}
    items = defaultdict(list)
    for s in snaps:
        for q in QUESTIONS:
            items[q].append(s["oracle"][ORACLE_FIELD[q]])
    maj = {q: Counter(v).most_common(1)[0][0] for q, v in items.items()}
    rows = []
    for s in snaps:
        t = state_text(s, "S1")
        r1, r2 = code_rule(t), code_rule(t, raw=s["state"])
        for q in QUESTIONS:
            o, f = s["oracle"][ORACLE_FIELD[q]], ORACLE_FIELD[q]
            ok["UB"][q].append(r1[f] == o)
            ok["UB_raw"][q].append(r2[f] == o)
            ok["majority"][q].append(maj[q] == o)
            rows.append({"snap": key(s), "kind": s["kind"], "seed": s["seed"], "phase": s["phase"], "question": q,
                         "oracle": o, "ub": r1[f], "ub_raw": r2[f]})
    out = {"n_snap": len(snaps), "majority_key": maj}
    for m, d in ok.items():
        out[m] = {q: sum(v) / len(v) for q, v in d.items()}
        allv = [x for v in d.values() for x in v]
        out[m]["pooled"] = sum(allv) / len(allv)
    json.dump(out, open(a.out, "w"), indent=1)
    with open(a.out.replace(".json", "_rows.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(json.dumps(out, indent=1))


async def acc(a):
    snaps = snapshots(a.dev)
    idx = {key(s): i for i, s in enumerate(snaps)}
    c = JevLClient(f"http://127.0.0.1:{a.port}", a.model, end_token=a.end_token, image_mime="image/jpeg")
    for cond in a.conds.split(","):
        S, inp, order = cond.split(":")
        g = "" if a.step_cm == 1 else f"_g{a.step_cm:g}"
        out = f"{a.outdir}/acc_{a.model}_{S}{g}_{inp}_{order}.jsonl"
        done = set()
        if os.path.exists(out):
            done = {json.loads(x)["snap"] for x in open(out, encoding="utf-8")}
        q = asyncio.Queue()
        for s in snaps:
            if key(s) not in done:
                q.put_nowait(s)
        print(cond, "todo", q.qsize(), "of", len(snaps), time.strftime("%H:%M:%S", time.gmtime()), flush=True)
        f = open(out, "a", encoding="utf-8")

        async def worker():
            while not q.empty():
                s = q.get_nowait()
                i = idx[key(s)]
                req, oracle, shown = build_snapshot_request(s, text_state=state_text(s, S, step_cm=a.step_cm),
                                                            shift=i if order == "rot" else 0)
                img = open(f"{s['_dir']}/{s['images']['cam_head']}", "rb").read() if inp == "img" else None
                rec, tries = None, 0
                while tries < 4:
                    tries += 1
                    rec = await c.acall(req, {"experiment": "e3lite", "seed": s["seed"]}, image=img)
                    if rec.error is None:
                        break
                for r in score(rec.answers if rec.error is None else {}, oracle, shown):
                    ans = rec.answers.get(r["qid"]) if rec.error is None else None
                    opts = shown[r["qid"]][1]
                    r.update(snap=key(s), idx=i, model=a.model, S=S, step_cm=a.step_cm, inp=inp, order=order,
                             seed=s["seed"],
                             kind=s["kind"], k=s["k"], phase=s["phase"], error=rec.error, tries=tries,
                             lat=round(rec.t_done - rec.t_send, 4), input_tokens=rec.input_tokens,
                             first=opts[0].key, probs=ans["probabilities"] if ans else None)
                    f.write(json.dumps(r) + "\n")
                f.flush()

        await asyncio.gather(*(worker() for _ in range(a.conc)))
        f.close()
    await c.aclose()
    print("done", time.strftime("%H:%M:%S", time.gmtime()), flush=True)


async def lat(a):
    snaps = snapshots(a.dev)
    order = list(range(len(snaps)))
    random.Random(0).shuffle(order)
    c = JevLClient(f"http://127.0.0.1:{a.port}", a.model, end_token=a.end_token, image_mime="image/jpeg")
    f = open(a.out, "a", encoding="utf-8")
    n = a.n
    per = a.calls // n
    for S in a.states.split(","):
        for mode in ("text", "image"):
            ctr = iter(order)

            async def worker(w, k, keep):
                out = []
                for _ in range(k):
                    s = snaps[next(ctr)]
                    req, _, _ = build_snapshot_request(s, text_state=state_text(s, S, step_cm=a.step_cm))
                    img = open(f"{s['_dir']}/{s['images']['cam_head']}", "rb").read() if mode == "image" else None
                    r = await c.acall(req, {}, image=img)
                    if keep:
                        ok = r.error is None and r.http_status == 200
                        L = r.t_done - r.t_send
                        out.append({"test": "L1", "model": a.model, "S": S, "mode": mode, "N": n, "worker": w,
                                    "step_cm": a.step_cm, "ok": ok, "lat": round(L, 6) if ok and L <= 2.0 else None,
                                    "lat_raw": round(L, 6), "error": r.error, "input_tokens": r.input_tokens,
                                    "n_seq": (r.raw_response or {}).get("n_seq"),
                                    "load1": float(open("/proc/loadavg").read().split()[0])})
                return out
            await asyncio.gather(*(worker(w, 10, False) for w in range(n)))  # per-N warm-up, discarded
            for rs in await asyncio.gather(*(worker(w, per, True) for w in range(n))):
                for r in rs:
                    f.write(json.dumps(r) + "\n")
            f.flush()
            print(S, mode, "done", flush=True)
    await c.aclose()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what")
    ap.add_argument("--dev", required=True)
    ap.add_argument("--model")
    ap.add_argument("--port", type=int)
    ap.add_argument("--out")
    ap.add_argument("--outdir")
    ap.add_argument("--conds")
    ap.add_argument("--states", default="S0,S1,S2")
    ap.add_argument("--end-token", default="<|im_end|>")
    ap.add_argument("--conc", type=int, default=8)
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--calls", type=int, default=200)
    ap.add_argument("--step-cm", type=float, default=1, help="S1/S2 print grid (E3-lite runs: 1; canon §54: 0.1)")
    a = ap.parse_args()
    if a.what == "ub":
        ub(a)
    elif a.what == "acc":
        asyncio.run(acc(a))
    elif a.what == "lat":
        asyncio.run(lat(a))
    else:
        raise SystemExit(a.what)


if __name__ == "__main__":
    main()
