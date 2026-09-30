"""L9 diversity report (spec §0 G4, user rule 2026-09-30): SigLIP embeddings of each episode's first head frame
(the ring-only image the model sees, calls/c000/img1_head_ring.png) for L9 and L8S samples, then per dataset
  pair_dist     mean cosine distance of random episode pairs
  eff_clusters  exp(entropy) of k-means cluster sizes (k = 50)
  nn_dup        share of episodes whose nearest other episode has cosine similarity > 0.95 ("almost the same scene")
  pair_dup      share of random pairs with cosine similarity > 0.95
plus counts from meta (families, layouts, definitions, rooms, HDRIs, materials, lights, objects used, arm split,
head moved). usage (pod, venv with torch + transformers):
  python tools/l9/diversity.py --l9 <collect root> --l8s <collect root> --out report.json [--n 10000] [--device cuda]"""
import argparse
import glob
import json
import os
import random
from collections import Counter

import numpy as np

MODEL = "google/siglip-base-patch16-224"
DUP = 0.95


def firsts(root: str, n: int, seed: int, gen: str | None):
    eps = []
    for m in glob.glob(os.path.join(root, "**", "meta.json"), recursive=True):
        d = os.path.dirname(m)
        p = os.path.join(d, "calls", "c000", "img1_head_ring.png")
        if not os.path.exists(p):
            continue
        if gen is not None:
            try:
                if json.load(open(m)).get("gen") != gen:
                    continue
            except Exception:  # noqa: BLE001
                continue
        eps.append((d, p))
    random.Random(seed).shuffle(eps)
    return eps[:n]


def embed(paths, device: str, bs: int = 64) -> np.ndarray:
    import torch
    from PIL import Image
    from transformers import AutoImageProcessor, AutoModel
    proc = AutoImageProcessor.from_pretrained(MODEL)  # image side only (no sentencepiece on the pod)
    model = AutoModel.from_pretrained(MODEL).to(device).eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(paths), bs):
            ims = [Image.open(p).convert("RGB") for p in paths[i:i + bs]]
            x = proc(images=ims, return_tensors="pt").to(device)
            e = model.get_image_features(**x)
            if not torch.is_tensor(e):  # newer transformers return a model output
                e = e.pooler_output
            out.append(torch.nn.functional.normalize(e, dim=-1).float().cpu().numpy())
    return np.concatenate(out)


def kmeans(X: np.ndarray, k: int, seed: int, iters: int = 30) -> np.ndarray:
    """Plain Lloyd k-means (cosine on unit vectors), k-means++ init. -> labels."""
    rng = np.random.default_rng(seed)
    C = [X[rng.integers(len(X))]]
    for _ in range(1, k):
        d = 1 - np.max(X @ np.stack(C).T, axis=1)
        p = np.clip(d, 0, None) ** 2
        C.append(X[rng.choice(len(X), p=p / p.sum()) if p.sum() > 0 else rng.integers(len(X))])
    C = np.stack(C)
    for _ in range(iters):
        lab = np.argmax(X @ C.T, axis=1)
        for c in range(k):
            m = X[lab == c]
            if len(m):
                v = m.mean(0)
                C[c] = v / (np.linalg.norm(v) + 1e-9)
    return np.argmax(X @ C.T, axis=1)


def metrics(E: np.ndarray, seed: int = 0, k: int = 50) -> dict:
    rng = np.random.default_rng(seed)
    n = len(E)
    i, j = rng.integers(n, size=20000), rng.integers(n, size=20000)
    keep = i != j
    sims = (E[i[keep]] * E[j[keep]]).sum(1)
    S = E @ E.T
    np.fill_diagonal(S, -1.0)
    nn = S.max(1)
    lab = kmeans(E, min(k, n), seed)
    p = np.bincount(lab) / n
    p = p[p > 0]
    return {"n": int(n), "pair_dist": round(float(1 - sims.mean()), 4), "pair_dup": round(float((sims > DUP).mean()), 4),
            "nn_dup": round(float((nn > DUP).mean()), 4), "nn_sim_median": round(float(np.median(nn)), 4),
            "eff_clusters": round(float(np.exp(-(p * np.log(p)).sum())), 2)}


def meta_counts(dirs) -> dict:
    c = {k: Counter() for k in ("env_family", "layout", "task_id", "task_family", "room", "hdr", "light_family", "arm")}
    mats, objs, moved_head, decor = set(), set(), 0, set()
    for d in dirs:
        m = json.load(open(os.path.join(d, "meta.json")))
        if not m.get("success"):
            continue
        for k in c:
            if m.get(k) is not None:
                c[k][str(m[k])] += 1
        mats |= set(m.get("materials") or [])
        objs |= set((m.get("objects") or {})) | set(m.get("clutter") or [])
        decor |= {x["asset"] for x in (m.get("decor") or [])}
        hp = m.get("head_pose") or {}
        moved_head += bool(hp.get("random"))
    n = sum(c["arm"].values())
    out = {k: len(v) for k, v in c.items()}
    out.update(success=n, materials=len(mats), objects=len(objs), mesh_furniture=len(decor),
               head_moved_share=round(moved_head / max(n, 1), 3),
               arm_share={k: round(v / max(n, 1), 3) for k, v in c["arm"].items()})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--l9", required=True)
    ap.add_argument("--l8s", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=10000)
    ap.add_argument("--device", default="cuda")
    a = ap.parse_args()
    rep = {}
    n = min(a.n, len(firsts(a.l9, a.n, 0, "l9")))  # equal sample sizes (nearest-neighbour similarity grows with n)
    for name, root, gen in (("l9", a.l9, "l9"), ("l8s", a.l8s, None)):
        eps = firsts(root, n, 0, gen)
        E = embed([p for _, p in eps], a.device)
        rep[name] = metrics(E)
        if name == "l9":
            all_dirs = [os.path.dirname(m) for m in glob.glob(os.path.join(root, "**", "meta.json"), recursive=True)]
            rep["l9_counts"] = meta_counts(all_dirs)
    rep["pass_near_dup"] = (rep["l9"]["nn_dup"] < rep["l8s"]["nn_dup"]
                            or (rep["l9"]["nn_dup"] == rep["l8s"]["nn_dup"] == 0
                                and rep["l9"]["nn_sim_median"] < rep["l8s"]["nn_sim_median"]))
    rep["pass_spread"] = rep["l9"]["pair_dist"] > rep["l8s"]["pair_dist"]
    json.dump(rep, open(a.out, "w"), indent=1)
    print(json.dumps(rep))


if __name__ == "__main__":
    main()
