"""Jev-L model selection: accuracy vs oracle on DEV snapshots (docs/stage3/results/jevl_model_select.md prereg).

usage: python jevl_acc.py --dev DIR --model M --port P --out JSONL [--end-token T] [--conc 4] [--limit N]
DIR = cli_pool dev output (DIR/P0, P1, P2 with ep<seed>.jsonl + img/). Every snapshot with an oracle answer is asked
once (6 questions, text state + head-cam JPEG); one row per (snapshot, question). Resumable (skips done keys).
"""
import argparse
import asyncio
import glob
import json
import os

from harvest.clients.jevl import JevLClient
from harvest.deccall_snap import build_snapshot_request, score


def snapshots(dev):
    out = []
    for kind in ("P0", "P1", "P2"):
        for p in sorted(glob.glob(f"{dev}/{kind}/ep*.jsonl"), key=lambda x: int(os.path.basename(x)[2:-6])):
            for x in open(p, encoding="utf-8"):
                line = json.loads(x)
                if line["oracle"] is not None:
                    line["_dir"] = f"{dev}/{kind}"
                    out.append(line)
    return out


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--end-token", default="<|im_end|>")
    ap.add_argument("--conc", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    snaps = snapshots(a.dev)
    if a.limit:
        snaps = snaps[:a.limit]
    done = set()
    if os.path.exists(a.out):
        done = {json.loads(x)["snap"] for x in open(a.out, encoding="utf-8")}
    c = JevLClient(f"http://127.0.0.1:{a.port}", a.model, end_token=a.end_token, image_mime="image/jpeg")
    f = open(a.out, "a", encoding="utf-8")
    q = asyncio.Queue()
    for s in snaps:
        key = f"{s['kind']}_s{s['seed']}_k{s['k']}"
        if key not in done:
            q.put_nowait((key, s))
    print("todo", q.qsize(), "of", len(snaps), flush=True)

    async def worker():
        while not q.empty():
            key, s = q.get_nowait()
            req, oracle, shown = build_snapshot_request(s)
            img = open(f"{s['_dir']}/{s['images']['cam_head']}", "rb").read()
            rec, tries = None, 0
            while tries < 4:  # prereg: 3 retries, then the items count wrong
                tries += 1
                rec = await c.acall(req, {"experiment": "jevl_select", "seed": s["seed"]}, image=img)
                if rec.error is None:
                    break
            for r in score(rec.answers if rec.error is None else {}, oracle, shown):
                ans = rec.answers.get(r["qid"]) if rec.error is None else None
                r.update(snap=key, model=a.model, seed=s["seed"], kind=s["kind"], k=s["k"], phase=s["phase"],
                         error=rec.error, tries=tries, lat=round(rec.t_done - rec.t_send, 4),
                         input_tokens=rec.input_tokens,
                         probs=ans["probabilities"] if ans else None)
                f.write(json.dumps(r) + "\n")
            f.flush()

    await asyncio.gather(*(worker() for _ in range(a.conc)))
    await c.aclose()
    print("done", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
