"""Jev-L pre-test (1) latency + determinism (canon §44, D24 §5). Runs on the pod next to vLLM.

usage: python jevl_bench.py l1|l2|sanity --model M --port P --bi 0|1 --image PNG --out JSONL
"""
import argparse
import asyncio
import json
import random
import time

from harvest.clients.jevl import JevLClient
from harvest.load.payloads import fixed, make

NS = (1, 2, 4, 8)


def row(rec, **kw):
    ok = rec.error is None and rec.http_status == 200
    lat = rec.t_done - rec.t_send
    return dict(kw, ok=ok, lat=round(lat, 6) if ok and lat <= 2.0 else None, lat_raw=round(lat, 6),
                error=rec.error, n_seq=(rec.raw_response or {}).get("n_seq"), input_tokens=rec.input_tokens,
                answers={q: {"choice": a["choice"], "p": a["confidence"], "p2": a["p_second"]}
                         for q, a in rec.answers.items()})


async def l1(c, img, a, f):
    for mode in ("text", "image"):
        im = img if mode == "image" else None
        for i in range(10):  # warm
            await c.acall(make("S1", 900000 + i), {}, image=im)
        for n in NS:
            per = max(a.calls // n, 25)
            ctr = iter(range(10 ** 6))

            async def worker(w, k, keep):
                out = []
                for _ in range(k):
                    i = next(ctr)
                    r = await c.acall(make("S1", 1000 * n + i), {"N": n}, image=im)
                    if keep:
                        out.append(row(r, test="L1", model=a.model, bi=a.bi, mode=mode, N=n, worker=w,
                                       warm="perN"))
                return out
            # per-N warm-up (new batch shapes JIT-compile on first use; "warm server" in the prereg)
            await asyncio.gather(*(worker(w, 10, False) for w in range(n)))
            for rs in await asyncio.gather(*(worker(w, per, True) for w in range(n))):
                for r in rs:
                    f.write(json.dumps(r) + "\n")
            f.flush()
            print(mode, n, "done", flush=True)


async def l2(c, img, a, f):
    stop = asyncio.Event()

    async def bg(w):
        k = 0
        while not stop.is_set():
            await c.acall(make("S1", 500000 + 1000 * w + k), {}, image=img)
            k += 1
    bgs = [asyncio.create_task(bg(w)) for w in range(4)]
    await asyncio.sleep(2.0)
    for rep in range(10):
        order = list(range(20))
        random.Random(rep).shuffle(order)
        for j in order:
            r = await c.acall(fixed(j), {}, image=img)
            f.write(json.dumps(row(r, test="L2", model=a.model, bi=a.bi, mode="image", payload=j, rep=rep,
                                   probs={q: x["probabilities"] for q, x in r.answers.items()})) + "\n")
        f.flush()
    stop.set()
    await asyncio.gather(*bgs)


async def sanity(c, img, a):
    """Check that a continued assistant prefix re-tokenizes to the option-trie prefix ids."""
    req = make("S1", 1)
    plans = await c.plan(req)
    for qid, (tok, trie, ptxt) in plans.items():
        print(qid, "tokens:", tok, "branching nodes:", len(trie))
        for pre, txt in ptxt.items():
            if not pre:
                continue
            body = c._body(req, qid, req["questions"][qid], txt, trie[pre], img)
            r = await c._c.post(f"{c.base}/tokenize", json={k: body[k] for k in
                                ("model", "messages", "continue_final_message", "add_generation_prompt")})
            ids = r.json()["tokens"]
            print("  prefix", repr(txt), list(pre), "tail", ids[-len(pre):], "OK" if ids[-len(pre):] == list(pre)
                  else "MISMATCH", "n_prompt", len(ids))
    t = time.monotonic()
    rec = await c.acall(req, {}, image=img)
    print("call", rec.error, round(rec.t_done - rec.t_send, 4), "s", rec.input_tokens,
          json.dumps({q: (x["choice"], round(x["confidence"], 3), round(x["p_second"], 3))
                      for q, x in rec.answers.items()}), round(time.monotonic() - t, 3))


async def main():
    p = argparse.ArgumentParser()
    p.add_argument("what")
    p.add_argument("--model", required=True)
    p.add_argument("--port", type=int, required=True)
    p.add_argument("--bi", type=int, required=True)
    p.add_argument("--image", required=True)
    p.add_argument("--out")
    p.add_argument("--calls", type=int, default=200)
    a = p.parse_args()
    img = open(a.image, "rb").read()
    c = JevLClient(f"http://127.0.0.1:{a.port}", a.model)
    if a.what == "sanity":
        await sanity(c, img, a)
    else:
        with open(a.out, "a", encoding="utf-8") as f:
            await (l1 if a.what == "l1" else l2)(c, img, a, f)
    await c.aclose()


if __name__ == "__main__":
    asyncio.run(main())
