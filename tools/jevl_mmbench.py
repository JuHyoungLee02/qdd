"""D27 multi-image micro-benchmark for Jev-L (latency only, no accuracy). Runs on the pod next to vLLM.

Layouts (images per DecCall; all sequences of one call carry the same images):
  T     text only (reference)
  H     head 672x376                                  (current §44/§55 layout)
  HW    head 672x376 + wrist 424x240, 2 native images (§57 default)
  HWt   one tiled image 672x616: head on top, wrist 424x240 bottom-left, black pad
  HWh   head + wrist resized to 224x128 (needs the lowered min-pixels per request)
  HhW   head resized to 448x256 + wrist 424x240
Client modes:
  base     every sequence sends the image bytes (current client)
  uuid     every sequence sends bytes + a content uuid (server skips hashing)
  lead     send the first sequence alone, then the other sequences in parallel (prefix KV incl. images reused)
  leadref  lead, and followers send only the uuid (no bytes; processor-cache hit required)
  hstatic  like base but the head frame never changes across calls (upper bound of head reuse)
usage: python jevl_mmbench.py --port P --model NAME --imgdir DIR --out JSONL --layouts H,HW --modes base,lead --ns 1,4
"""
import argparse
import asyncio
import glob
import hashlib
import io
import json
import os
import random
import time

import httpx
from PIL import Image

from harvest.clients.jevl import JevLClient, option_probs, question_text, SYSTEM
from harvest.load.payloads import make

LOWMIN = {"size": {"shortest_edge": 16384, "longest_edge": 16777216}}  # lets 224x128 stay 28 tokens
PAD_LINE = "  aux_{k}: dx=+{a:.1f} cm, dy=-{b:.1f} cm, dz=+{c:.1f} cm, visible=true, grasped=false\n"


def jpeg(im, q=90):
    b = io.BytesIO()
    im.convert("RGB").save(b, "JPEG", quality=q)
    return b.getvalue()


def build_frames(imgdir, k, seed=0):
    heads = sorted(glob.glob(os.path.join(imgdir, "*", "*_cam_head.jpg")))
    random.Random(seed).shuffle(heads)
    out = []
    for h in heads[:k]:
        w = h.replace("_cam_head.jpg", "_cam_wrist_right.jpg")
        if not os.path.exists(w):
            continue
        hi, wi = Image.open(h).convert("RGB"), Image.open(w).convert("RGB")
        tile = Image.new("RGB", (hi.width, hi.height + wi.height))
        tile.paste(hi, (0, 0))
        tile.paste(wi, (0, hi.height))
        out.append({"head": open(h, "rb").read(), "wrist": open(w, "rb").read(), "tile": jpeg(tile),
                    "wrist_h": jpeg(wi.resize((224, 128), Image.BICUBIC)),
                    "head_h": jpeg(hi.resize((448, 256), Image.BICUBIC))})
    return out


LAYOUT = {"T": [], "H": ["head"], "HW": ["head", "wrist"], "HWt": ["tile"], "HWh": ["head", "wrist_h"],
          "HhW": ["head_h", "wrist"]}


class MMClient(JevLClient):
    def __init__(self, *a, **kw):
        super().__init__(*a, image_mime="image/jpeg", **kw)

    def body(self, req, qid, q, prefix_text, kids, images, send_bytes, use_uuid, lowmin):
        user = []
        for data in images:
            u = hashlib.blake2b(data, digest_size=16).hexdigest()
            if send_bytes:
                part = {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," +
                                                           __import__("base64").b64encode(data).decode()}}
            else:
                part = {"type": "image_url", "image_url": None}
            if use_uuid or not send_bytes:
                part["uuid"] = u
            user.append(part)
        user.append({"type": "text", "text": question_text(req["state"], qid, q)})
        msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
        cont = prefix_text != ""
        if cont:
            msgs.append({"role": "assistant", "content": prefix_text})
        b = {"model": self.model, "messages": msgs, "max_tokens": 1, "temperature": 0.0, "logprobs": True,
             "logprob_token_ids": sorted(kids), "return_tokens_as_token_ids": True,
             "continue_final_message": cont, "add_generation_prompt": not cont}
        if lowmin:
            b["mm_processor_kwargs"] = LOWMIN
        return b

    async def call(self, req, images, mode, lowmin):
        plans = await self.plan(req)
        keys = [(qid, pre) for qid, (tok, trie, ptxt) in plans.items() for pre in trie]
        lead = mode in ("lead", "leadref")

        def mk(i, qid, pre):
            tok, trie, ptxt = plans[qid]
            send = not (mode == "leadref" and i > 0)
            return self.body(req, qid, req["questions"][qid], ptxt[pre], trie[pre], images, send,
                             mode in ("uuid", "leadref"), lowmin)
        bodies = [mk(i, q, p) for i, (q, p) in enumerate(keys)]
        post = lambda b: self._c.post(f"{self.base}/v1/chat/completions", json=b)
        t0 = time.monotonic()
        try:
            if lead:
                first = await post(bodies[0])
                rest = await asyncio.gather(*(post(b) for b in bodies[1:]))
                resps = [first] + list(rest)
            else:
                resps = await asyncio.gather(*(post(b) for b in bodies))
        except httpx.HTTPError as e:
            return {"ok": False, "lat_raw": time.monotonic() - t0, "error": type(e).__name__}
        lat = time.monotonic() - t0
        bad = [r for r in resps if r.status_code != 200]
        if bad:
            return {"ok": False, "lat_raw": lat, "error": f"http_{bad[0].status_code}", "body": bad[0].text[:300]}
        pt = [r.json().get("usage", {}).get("prompt_tokens") for r in resps]
        ans = {}
        node_lp = {q: {} for q in plans}
        for (q, p), r in zip(keys, resps):
            tops = r.json()["choices"][0]["logprobs"]["content"][0]["top_logprobs"]
            node_lp[q][p] = {int(t["token"].split(":", 1)[1]): t["logprob"] for t in tops}
        for q, (tok, trie, _) in plans.items():
            pr = option_probs(tok, trie, node_lp[q], self._end)
            ans[q] = max(pr, key=pr.get)
        return {"ok": True, "lat_raw": lat, "input_tokens": max(x for x in pt if x is not None), "n_seq": len(keys),
                "answers": ans}


def payload(i, pad):
    req = make("S1", i)
    if pad:
        rnd = random.Random(i)
        req = dict(req, state=req["state"] + "\n" + "".join(
            PAD_LINE.format(k=k, a=rnd.uniform(0, 30), b=rnd.uniform(0, 30), c=rnd.uniform(0, 10)) for k in range(pad)))
    return req


def loadavg():
    try:
        return float(open("/proc/loadavg").read().split()[0])
    except OSError:
        return None


async def run(a):
    frames = build_frames(a.imgdir, a.frames)
    print("frames", len(frames), {k: len(v) for k, v in frames[0].items()}, flush=True)
    c = MMClient(f"http://127.0.0.1:{a.port}", a.model, timeout_s=a.timeout)
    f = open(a.out, "a", encoding="utf-8")
    for lay in a.layouts.split(","):
        for mode in a.modes.split(","):
            if lay == "T" and mode != "base":
                continue
            lowmin = lay == "HWh"
            ctr = iter(range(10 ** 7))

            def imgs(i):
                fr = frames[i % len(frames)]
                ims = [fr[k] for k in LAYOUT[lay]]
                if mode == "hstatic" and ims:
                    ims[0] = frames[0][LAYOUT[lay][0]]
                return ims
            for n in [int(x) for x in a.ns.split(",")]:
                per = max(a.calls // n, 25)

                async def worker(w, k, keep, n=n):
                    rows = []
                    for _ in range(k):
                        i = next(ctr)
                        r = await c.call(payload(i, a.pad), imgs(i), "base" if mode == "hstatic" else mode, lowmin)
                        if keep:
                            r.update(layout=lay, mode=mode, N=n, worker=w, pad=a.pad, server=a.server,
                                     lat=round(r["lat_raw"], 6) if r["ok"] and r["lat_raw"] <= 2.0 else None)
                            rows.append(r)
                    return rows
                await asyncio.gather(*(worker(w, 10, False) for w in range(n)))  # per-N warm-up
                l0 = loadavg()
                t = time.time()
                for rs in await asyncio.gather(*(worker(w, per, True) for w in range(n))):
                    for r in rs:
                        r.update(load_start=l0, load_end=loadavg())
                        f.write(json.dumps(r) + "\n")
                f.flush()
                print(lay, mode, n, "done", round(time.time() - t, 1), "s load", l0, loadavg(), flush=True)
    f.close()
    await c.aclose()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--imgdir", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--server", default="on")
    p.add_argument("--layouts", default="T,H,HW,HWt,HWh,HhW")
    p.add_argument("--modes", default="base,uuid,lead,leadref")
    p.add_argument("--ns", default="1,4")
    p.add_argument("--calls", type=int, default=200)
    p.add_argument("--frames", type=int, default=400)
    p.add_argument("--pad", type=int, default=0, help="extra state lines (~30 tokens each) to mimic real prompts")
    p.add_argument("--timeout", type=float, default=5.0)
    asyncio.run(run(p.parse_args()))
