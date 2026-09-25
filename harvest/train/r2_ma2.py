"""E-MA2 OPT-IN input: an Astra `edit` command in the fused VLA input (docs/stage3/prereg_ma2.md; research
docs/research/molmoact_deepdive_2026-09-26.md §6.2; spec 2026-09-26-astra-vla-coupling-design §11, §14).
Nothing here is read by the default training / runtime path.

Conditions (R2_TRAIN decision snapshots, the stage-B r2 loader):
  c0  no command (reference; inputs = the baseline's)
  c1  text: one line `astra edit: move fingertip dx=.. dy=.. dz=.. cm (robot frame)` after the context state
      (context and every question text), the MolmoAct "language" form of the command
  c2  arrow: the head image with a 2-point arrow from the current fingertip to fingertip + command, projected with
      the (constant) sim head camera; code draws it, Astra only gives numbers (canon §84)
Training command = hindsight: the next 1.0 s fingertip (finger midpoint, table frame = robot x / y) displacement,
clipped to the edit range (5 cm per axis), given to a deterministic 50 % of the samples (`give`, MolmoAct: as many
trajectory-conditioned as plain samples). A given sample's dir_xy / dir_z targets become the command's bins
(labels_v2 rule, 1 cm dead band) -- the decision that follows the command; mag / target / phase keep labels_v2.
Evaluation commands (ma2eval): the true command's xy rotated by 0 / 90 / 180 deg, xy length capped at 2 cm, z clipped
to +-2 cm; the expert is conditioned on the model's own predicted decisions (decide -> chunk, as at runtime).

CLI (stageb_train commands plus --ma2 c0|c1|c2 --ma2-root DIR, and `ma2eval`):
  python -m harvest.train.r2_ma2 train --data r2 --pool <views> --ma2 c1 --ma2-root /data/harvest/data/ma2 ...
  python -m harvest.train.r2_ma2 ma2eval --data r2 --pool <views> --rows <eval rows> --ckpt DIR --ma2 c1 \
      --eval-set JSON --out JSONL
With --ma2 off (default) this is stageb_train.main unchanged (test).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re

import numpy as np

MA2_VER = "ma2@v1"
CONDS = ("c0", "c1", "c2")
MA2_FILES = ("harvest/train/r2_ma2.py",)
MA2_ROOT = "/data/harvest/data/ma2"
HZ = 30
CMD_HORIZON_S = 1.0
CMD_CLIP_M = 0.05     # Astra edit: <= 5 cm per axis (spec head revision)
EVAL_CAP_M = 0.02     # evaluation commands: xy length <= 2 cm, |z| <= 2 cm (research doc §6.2)
EVAL_ROT = {"e0": 0, "e90": 90, "e180": 180}
GIVE_FRAC, GIVE_SALT = 0.5, "ma2give@v1"
# head camera (sim, constant): R1-DEV link x mount median over 804 snapshots (max deviation 4.8 mm), world frame,
# Isaac camera convention (+X optical axis, +Y left, +Z up); table frame = world - (0, 0, TABLE_TOP_Z)
TABLE_TOP_Z = 0.85
HEAD_POS = np.array([0.1050633, 0.0249816, 1.4046419])
HEAD_R = np.array([[0.7702197, 0.0000124, 0.6377787],
                   [-0.0000159, 1.0, -0.0000001],
                   [-0.6377787, -0.0000101, 0.7702197]])
HEAD_K = {"fx": 367.0, "fy": 367.0, "cx": 336.0, "cy": 188.0, "width": 672, "height": 376}
ARROW_RGB = (0, 255, 255)  # not magenta: the mug_marker place marker is magenta (projection sheet)
ARROW_WIDTH_PX = 3
URDF = "/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf"  # FK gate: cos(FK, tcp) median 0.9999 on R2

_ID = re.compile(r"([^/\\]+)[/\\]([^/\\]+)[/\\](P\d+)[/\\]img[/\\]ep(\d+)[/\\]f(\d+)_cam_head\.jpg$")


# ------------------------------------------------------------------------------------------ commands
def hindsight_cmd(tcp, k: int, hz: int = HZ, horizon_s: float = CMD_HORIZON_S, clip_m: float = CMD_CLIP_M):
    """Fingertip displacement from frame k to k + horizon (last frame if the episode ends first), clipped per axis."""
    tcp = np.asarray(tcp, float)
    k2 = min(k + int(round(horizon_s * hz)), len(tcp) - 1)
    return np.clip(tcp[k2] - tcp[k], -clip_m, clip_m)


def give(sid: str, frac: float = GIVE_FRAC, salt: str = GIVE_SALT) -> bool:
    h = int(hashlib.sha256(f"{salt}|{sid}".encode()).hexdigest()[:8], 16)
    return h / 0x100000000 < frac


def eval_cmd(c, theta_deg: float, cap_m: float = EVAL_CAP_M):
    c = np.asarray(c, float)
    t = math.radians(theta_deg)
    xy = np.array([math.cos(t) * c[0] - math.sin(t) * c[1], math.sin(t) * c[0] + math.cos(t) * c[1]])
    n = float(np.linalg.norm(xy))
    if n > cap_m:
        xy = xy * (cap_m / n)
    return np.array([xy[0], xy[1], float(np.clip(c[2], -cap_m, cap_m))])


def cmd_line(c) -> str:
    d = [100.0 * float(v) for v in c]
    return "astra edit: move fingertip dx={:+.1f} dy={:+.1f} dz={:+.1f} cm (robot frame)".format(*d)


def cmd_bins(c) -> dict:
    from .. import labels_v2 as L2
    return {"dir_xy": L2.dir_xy_label(c), "dir_z": L2.dir_z_label(c)}


# ------------------------------------------------------------------------------------------ arrow
def project_head(p_table) -> np.ndarray:
    """(N, 2) pixel (u, v) of table-frame points in the head image (perception.geom convention)."""
    from ..perception.geom import Intr, project
    P = np.atleast_2d(np.asarray(p_table, float)) + np.array([0.0, 0.0, TABLE_TOP_Z])
    K = Intr(HEAD_K["fx"], HEAD_K["fy"], HEAD_K["cx"], HEAD_K["cy"], HEAD_K["width"], HEAD_K["height"])
    u, v, _ = project(P, K, HEAD_POS, HEAD_R)
    return np.stack([u, v], 1)


def draw_arrow(img, p0_table, c):
    """A copy of the head image with the command arrow: start dot (r 3 px) at the fingertip, line (3 px) to
    fingertip + c, arrow head (10 px) when the arrow is at least 4 px long."""
    from PIL import ImageDraw
    out = img.copy()
    (u0, v0), (u1, v1) = project_head(np.stack([np.asarray(p0_table, float), np.asarray(p0_table, float) + c]))
    d = ImageDraw.Draw(out)
    d.ellipse([u0 - 3, v0 - 3, u0 + 3, v0 + 3], fill=ARROW_RGB)
    d.line([(u0, v0), (u1, v1)], fill=ARROW_RGB, width=ARROW_WIDTH_PX)
    L = math.hypot(u1 - u0, v1 - v0)
    if L >= 4:
        ex, ey = (u1 - u0) / L, (v1 - v0) / L
        b = (u1 - 10 * ex, v1 - 10 * ey)
        d.polygon([(u1, v1), (b[0] - 5 * ey, b[1] + 5 * ex), (b[0] + 5 * ey, b[1] - 5 * ex)], fill=ARROW_RGB)
    return out


# ------------------------------------------------------------------------------------------ samples
def sample_id(head_path: str) -> str:
    m = _ID.search(head_path)
    if not m:
        raise ValueError(f"not an R2 head image path: {head_path}")
    v, t, kind, seed, k = m.groups()
    return f"{v}/{t}/{kind}/ep{int(seed)}/k{int(k)}"


def arrow_rel(sid: str, tag: str) -> str:
    v, t, kind, ep, k = sid.split("/")
    return f"arrow/{v}/{t}/{kind}/{ep}/k{int(k[1:]):04d}_{tag}.jpg"


def with_command(s: dict, cond: str, c, arrow_path: str | None = None, relabel: bool = True) -> dict:
    """A new sample with command c shown in form `cond` (c0: s itself). relabel: dir_xy / dir_z targets and
    committed decisions = the command's bins. The input sample is not modified."""
    if cond == "c0":
        return s
    ctx0, ims = s["context"]["text"], s["context"]["images"]
    ctx, new_ims = ctx0, ims
    if cond == "c1":
        ctx = ctx0 + "\n" + cmd_line(c)
    elif cond == "c2":
        if not arrow_path:
            raise ValueError("c2: arrow image path needed")
        new_ims = [[ims[0][0], arrow_path]] + [list(x) for x in ims[1:]]
    else:
        raise ValueError(f"cond {cond!r}")
    bins = cmd_bins(c) if relabel else {}
    items = []
    for it in s["items"]:
        if not it["text"].startswith(ctx0):
            raise ValueError(f"{s['key']}: question text does not start with the context")
        new = {**it, "text": ctx + it["text"][len(ctx0):], "images": new_ims}
        if it["question"] in bins:
            new["target"] = [bins[it["question"]]]
        items.append(new)
    committed = {**s["committed"], **{q: b for q, b in bins.items() if q in s["committed"]
                                      or any(it["question"] == q for it in s["items"])}}
    return {**s, "context": {**s["context"], "text": ctx, "images": new_ims}, "items": items, "committed": committed}


def apply_ma2(samples, cond: str, table: dict, root: str = MA2_ROOT):
    """(new sample list, stats): a sample whose table entry has give = True gets its hindsight command (with
    relabel); others are returned as they are. KeyError for a sample missing from the table."""
    out, st = [], {"n": 0, "given": 0, "missing": 0}
    for s in samples:
        st["n"] += 1
        sid = sample_id(s["context"]["images"][0][1])
        rec = table[sid]
        if cond == "c0" or not rec["give"]:
            out.append(s)
            continue
        ap = os.path.join(root, arrow_rel(sid, "true")) if cond == "c2" else None
        out.append(with_command(s, cond, np.asarray(rec["cmd"], float), ap, relabel=True))
        st["given"] += 1
    return out, st


def read_table(root: str, pool: str) -> dict:
    """{sample id: record} from <root>/cmd/<variant>_<task>_<kind>.jsonl of every --pool view folder."""
    out = {}
    for fo in [f for f in pool.split(",") if f]:
        v, t, kind = fo.rstrip("/").split("/")[-3:]
        for x in open(os.path.join(root, "cmd", f"{v}_{t}_{kind}.jsonl"), encoding="utf-8"):
            r = json.loads(x)
            out[r["id"]] = r
    return out


def _file_sha(paths):
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return {p: hashlib.sha256(open(os.path.join(root, p), "rb").read()).hexdigest()[:12] for p in paths}


def mark_prompt_config(cfg: dict, cond: str) -> dict:
    out = {k: v for k, v in cfg.items() if k != "sha"}
    out.update(ma2=MA2_VER, ma2_cond=cond, ma2_files_sha=_file_sha(MA2_FILES))
    out["sha"] = hashlib.sha256(json.dumps(out, sort_keys=True).encode()).hexdigest()[:12]
    return out


# ------------------------------------------------------------------------------------------ CLI wrapper
def build_parser():
    from . import stageb_train as TR
    ap = TR.build_parser()
    sub = next(x for x in ap._actions if x.__class__.__name__ == "_SubParsersAction")
    for name in ("train", "predict", "evalck"):
        p = sub.choices[name]
        p.add_argument("--ma2", default="off", choices=("off",) + CONDS, help="E-MA2 command form")
        p.add_argument("--ma2-root", default=MA2_ROOT, help="<root>/cmd/*.jsonl commands, <root>/arrow/ images")
    e = sub.add_parser("ma2eval", help="E-MA2: decisions + chunk under none / rotated commands")
    TR._common(e)
    TR._data(e)
    e.add_argument("--ckpt", required=True)
    e.add_argument("--ma2", required=True, choices=CONDS, help="the checkpoint's command form")
    e.add_argument("--ma2-root", default=MA2_ROOT)
    e.add_argument("--eval-set", required=True, help="json {'ids': [...]} fixed before training")
    e.add_argument("--out", required=True)
    e.add_argument("--urdf", default=URDF)
    e.add_argument("--steps", type=int, default=10)
    e.add_argument("--max-train", type=int, default=0)
    return ap


def install(TR, a) -> None:
    """Patch stageb_train for a --ma2 run: loaded samples get their commands, prompt_config gets the marker."""
    if getattr(a, "ma2", "off") == "off":
        return
    if a.data != "r2":
        raise SystemExit("--ma2: --data r2 only")
    load0, pc0 = TR._load_data, TR.prompt_config

    def _load_data(args):
        samples, hz, tr, va = load0(args)
        if args.ma2 == "c0":
            print(json.dumps({"event": "ma2_apply", "cond": "c0", "n": len(samples), "given": 0}), flush=True)
            return samples, hz, tr, va
        table = read_table(args.ma2_root, args.pool)
        new, st = apply_ma2(samples, args.ma2, table, args.ma2_root)
        m = {id(s): n for s, n in zip(samples, new)}
        print(json.dumps({"event": "ma2_apply", "cond": args.ma2, **st}), flush=True)
        return new, hz, [m[id(s)] for s in tr], [m[id(s)] for s in va]

    def prompt_config(*x, **kw):
        return mark_prompt_config(pc0(*x, **kw), a.ma2)
    TR._load_data, TR.prompt_config = _load_data, prompt_config


def cmd_ma2eval(a) -> None:
    """Per eval snapshot: condition none (+ e0 / e90 / e180 for c1 / c2): option log-prob argmax per question, then
    the expert chunk conditioned on those predicted decisions (fixed noise per snapshot, same over conditions) and
    its FK fingertip displacement (arm base frame = table axes) from the first to the last chunk target."""
    import torch

    from . import stageb_train as TR
    from .se2e_data import fk_ee, load_arm_chain
    from .stageb_expert import sample_actions
    from .stageb_model import HFEncoder, load_heads
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ids = json.load(open(a.eval_set))["ids"]
    from . import stageb_data as D
    samples, _ = D.load_for_training("r2", pool=a.pool, rows=a.rows, state=a.state, wrist=not a.no_wrist)
    by = {}
    for s in samples:
        by.setdefault(sample_id(s["context"]["images"][0][1]), s)
    miss = [i for i in ids if i not in by]
    if miss or len(set(ids)) != len(ids):
        raise SystemExit(f"eval set: {len(miss)} ids not loaded, {len(ids) - len(set(ids))} duplicates")
    table = read_table(a.ma2_root, a.pool)
    chain = load_arm_chain(a.urdf, "right")
    bb, proc, _ = TR.load_backbone("qwen", a.model, dev, adapter=os.path.join(a.ckpt, "adapter"))
    m = load_heads(a.ckpt, bb, dev).eval()
    m.shared = True
    enc = HFEncoder(proc)
    conds = ["none"] + (list(EVAL_ROT) if a.ma2 in ("c1", "c2") else [])
    write = TR._writer(a.out)
    H, A = m.expert.cfg.horizon, m.expert.cfg.act_dim
    for i, sid in enumerate(ids):
        s = by[sid]
        c = np.asarray(table[sid]["cmd"], float)
        g = torch.Generator().manual_seed(a.seed * 1_000_003 + i)
        noise = torch.randn(1, H, A, generator=g).to(dev)
        for cn in conds:
            ce = None if cn == "none" else eval_cmd(c, EVAL_ROT[cn])
            s2 = s if ce is None else with_command(s, a.ma2, ce, os.path.join(a.ma2_root, arrow_rel(sid, cn)),
                                                  relabel=False)
            with torch.no_grad():
                ctx, mask, lps = m.forward_shared([s2], enc, dev, grad=False)
                preds = {it["question"]: max(lp, key=lambda n: float(lp[n])) for it, lp in zip(s2["items"], lps[0])}
                s3 = {**s2, "committed": {**s2["committed"], **preds}}
                z = sample_actions(m.expert, m.cond([s3], ctx, mask, dev), a.steps, noise)
            act = m.norm.action(z[0].cpu().numpy(), s3["action_script"], s3.get("arm", "right"))
            disp = fk_ee(chain, act[-1, :7]) - fk_ee(chain, act[0, :7])
            write({"event": "item", "i": i, "id": sid, "key": s["key"], "cond": cn,
                   "cmd": None if ce is None else [round(float(v), 6) for v in ce], "true_cmd": c.tolist(),
                   "preds": preds, "targets": {it["question"]: it["target"] for it in s["items"]},
                   "disp": [round(float(v), 6) for v in disp]})
    write({"event": "summary", "ckpt": a.ckpt, "ma2": a.ma2, "n": len(ids), "conds": conds})


def main(argv=None):
    from . import stageb_train as TR
    a = build_parser().parse_args(argv)
    if a.cmd == "ma2eval":
        cmd_ma2eval(a)
        return
    install(TR, a)
    {"smoke": TR.cmd_smoke, "train": TR.cmd_train, "evalck": TR.cmd_evalck, "predict": TR.cmd_predict}[a.cmd](a)


if __name__ == "__main__":
    main()
