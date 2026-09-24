"""E-M4b-meas data table (numpy, no Isaac): FI-DEV episodes and POOL snapshots as flat snapshot records.

Snapshot record: key, src ("fi" | "pool"), cond, seed, kind, split ("fi_cal" | "fi_eval" | "pool_fit" | "pool_eval"),
fold (FI cal only), ep (episode key), t, phase, truth {9 test predicates}, images [[label, abs path], ...] (D27),
ctx (IMG prompt state, canonicalized), and for FI the P features (width, grip_tau (noisy), tcp_z, tau_res (noisy)).
The pool `oracle` field is never read.
"""
from __future__ import annotations

import glob
import json
import os
import zlib

import numpy as np

from . import spec as FS
from .prules import noisy

HEAD, WRIST = "cam_head", "cam_wrist_right"
LABEL = {HEAD: "head camera:", WRIST: "right wrist camera (active arm):"}


def ctx_text(text_state: str) -> str:
    from ..serialize import canonicalize
    from ..train.stageb_data import image_only_state
    return canonicalize(image_only_state(text_state))


def images(line: dict, folder: str) -> list:
    return [[LABEL[c], os.path.join(folder, line["images"][c])] for c in (HEAD, WRIST)]


def _ep_seed_noise(seed: int, cond: str) -> int:
    return zlib.crc32(f"{seed}:{cond}".encode()) & 0x7FFFFFFF


def fi_episodes(root: str, robot_meta: dict | None = None, conds=FS.CONDITIONS, with_lines: bool = True) -> list:
    meta = robot_meta or json.load(open(f"{root}/robot_meta.json"))
    lim = np.asarray(meta["effort_limits"], float)
    arm_lim, grip_lim = lim[meta["arm_ids"]], lim[meta["grip_id"]]
    eps = []
    for cond in conds:
        d = f"{root}/{cond}"
        for fp in sorted(glob.glob(f"{d}/ep*.fi.json"), key=lambda x: int(os.path.basename(x)[2:].split(".")[0])):
            fi = json.load(open(fp))
            seed = fi["seed"]
            st = np.load(fp.replace(".fi.json", ".fi.npz"))
            lines = [json.loads(x) for x in open(f"{d}/ep{seed}.jsonl")] if with_lines else None
            ns = _ep_seed_noise(seed, cond)
            snaps = fi["snaps"]
            tau = noisy(np.array([s["tau"] for s in snaps]), arm_lim, ns)
            gt = noisy(np.array([[s["grip_tau"]] for s in snaps]), [grip_lim], ns + 1)[:, 0]
            ts = st["t"]
            recs = []
            for i, s in enumerate(snaps):
                j = max(int(np.searchsorted(ts, s["t"] + 1e-9, side="right")) - 1, 0)
                tres = float(np.linalg.norm(tau[i] - st["tau_grav"][j]))
                r = {"key": f"fi/{cond}/{seed}/{s['k']}", "src": "fi", "cond": cond, "seed": seed, "kind": fi["kind"],
                     "split": "fi_" + fi["split"], "fold": fi["fold"], "ep": f"fi/{cond}/{seed}", "k": s["k"],
                     "t": s["t"], "phase": s["phase"], "truth": s["truth"], "occluded": s.get("occluded", False),
                     "width": s["width"], "grip_tau": float(abs(gt[i])), "tcp_z": s["tcp"][2], "tau_res": tres}
                if with_lines:
                    ln = lines[i]
                    assert ln["k"] == s["k"]
                    r["images"] = images(ln, d)
                    r["ctx"] = ctx_text(ln["text_state"])
                recs.append(r)
            eps.append({"ep": f"fi/{cond}/{seed}", "cond": cond, "seed": seed, "kind": fi["kind"],
                        "split": "fi_" + fi["split"], "fold": fi["fold"], "success": fi["success"],
                        "t_inject": fi["t_inject"], "onset": fi["onset"], "sim_time_s": fi["sim_time_s"],
                        "snaps": recs})
    return eps


def pool_truth(line: dict) -> dict:
    raw = line["state"]["obs"]["raw"]
    gc = {next(iter(set(c) - {"gripper"})) for c in raw["contacts"] if "gripper" in c and len(c) == 2}
    return FS.truth(line["pred"], FS.contact_open(raw["grip"]["w"], gc))


def pool_snaps(pool_dir: str) -> list:
    out = []
    for fp in sorted(glob.glob(f"{pool_dir}/ep*.jsonl"), key=lambda x: int(os.path.basename(x)[2:-6])):
        for ln in (json.loads(x) for x in open(fp)):
            sp = ln["split"]
            if sp not in ("fit", "eval"):
                continue
            out.append({"key": f"pool/{ln['seed']}/{ln['k']}", "src": "pool", "cond": "pool", "seed": ln["seed"],
                        "kind": ln["kind"], "split": "pool_" + sp, "fold": None, "ep": f"pool/{ln['seed']}",
                        "k": ln["k"], "t": ln["t"], "phase": ln["phase"], "truth": pool_truth(ln),
                        "images": images(ln, pool_dir), "ctx": ctx_text(ln["text_state"])})
    return out
