"""E-TP1 perspective hold-out items (tools/tp1/tp1_aux.py eval) -> a vLLM server, replies cached (resume), the same
client and content layout as harvest.teach_pt.evaluate (LocalVLM, greedy, IMAGE_LABELS).
usage (venv_vllm python, PYTHONPATH = code dir): tp1_persp_eval.py --data persp_eval.jsonl --url URL --name NAME --out DIR"""
import argparse
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    from harvest.astra_motion.models import LocalVLM
    from harvest.teach_l8.dataset import IMAGE_LABELS
    items = [json.loads(x) for x in open(a.data, encoding="utf-8")]
    os.makedirs(a.out, exist_ok=True)
    rp = os.path.join(a.out, "replies.jsonl")
    done = {json.loads(x)["id"] for x in open(rp)} if os.path.exists(rp) else set()
    vlm = LocalVLM(a.url, a.name, a.name, max_tokens=200)
    lock = threading.Lock()
    f = open(rp, "a")

    def one(it):
        imgs = [(IMAGE_LABELS[i], open(p, "rb").read()) for i, p in enumerate(it["images"])]
        rep = vlm.ask(it["prompt"], imgs, {})
        with lock:
            f.write(json.dumps({"id": it["id"], "text": rep.text, "error": rep.error}) + "\n")
            f.flush()
    with ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(one, [it for it in items if it["id"] not in done]))
    f.close()
    open(os.path.join(a.out, "DONE"), "w").write(str(len(items)))
    print("PERSP_EVAL_DONE", len(items), flush=True)


if __name__ == "__main__":
    main()
