"""E-SR1b OPT-IN training / sampling options: make the action expert follow the joystick decision it is conditioned on
(docs/stage3/prereg_sr1b.md; E-SR0 docs/stage3/results/sr0.md §5). Nothing here is read by the default training /
runtime path; the baseline files (stageb_*, prefix_share, r2_ma2) are not modified.

  --sr1b-drop p     decision dropout: in training mode each sample's joystick decision slots of the expert condition
                    (dir_xy, dir_z, mag_coarse) are replaced by id 0 (the vocabulary's unknown / none id) with
                    probability p, so one expert learns the conditional and the unconditional velocity; at inference
                    sample_actions_cfg guides with v = v_null + w * (v_dec - v_null) (classifier-free guidance on the
                    decision, pi*0.6 RECAP style). The draw uses its own numpy RNG (seed, salt): the torch RNG stream
                    (data order, flow t / noise) stays the baseline's.
  --sr1b-relabel    hindsight relabel: the expert's committed dir_xy / dir_z = the bins of the target chunk's OWN FK
                    fingertip displacement (FK(last) - FK(first) row of action_exec, the sr0 disp_gt definition):
                    nearest of the 8 directions by angle (none below XY_MIN_M), z up / down beyond +-Z_MIN_M. The
                    decision-layer targets (items), mag_coarse, target and phase keep labels_v2.
Composes with r2_ma2 (--ma2 c0 = the E-MA2 C0 recipe and marker). Both options off -> r2_ma2.main unchanged (test).

  python -m harvest.train.sr1b train --data r2 --pool <views> --ma2 c0 --sr1b-drop 0.3 [--sr1b-relabel] ...
"""
from __future__ import annotations

import hashlib
import json
import math

import numpy as np

SR1B_VER = "sr1b@v1"
SR1B_FILES = ("harvest/train/sr1b.py",)
JOY = ("dir_xy", "dir_z", "mag_coarse")
QUESTIONS = ("dir_xy", "dir_z", "mag_coarse", "target", "phase")  # = stageb_data.QUESTIONS (test)
JOY_SLOTS = tuple(QUESTIONS.index(q) for q in JOY)
DIR_XY8 = ("plus_x", "plus_x_plus_y", "plus_y", "minus_x_plus_y", "minus_x", "minus_x_minus_y", "minus_y",
           "plus_x_minus_y")  # counter-clockwise from +x in 45 deg steps (= sr0_eval.DIR_XY8, test)
XY_MIN_M = 0.002
Z_MIN_M = 0.002
DROP_SALT = 0x5121B
NEAR_M = 0.05  # = config.CFG.near_in_m (runtime.core.near_contact, canon §7; test)
PICK_PHASES = ("approach", "descend", "close", "lift")  # = datagen.rows.PICK_PHASES: target o3, later phases o5
URDF = "/data/harvest/data/se2e/urdf/ffw_bg2_rev4_follower.urdf"  # = sr0_eval.URDF


# ------------------------------------------------------------------------------------------ hindsight bins
def sector_xy(dx: float, dy: float, min_m: float = XY_MIN_M) -> str:
    if math.hypot(dx, dy) < min_m:
        return "none_xy"
    return DIR_XY8[int(round(math.atan2(dy, dx) / (math.pi / 4))) % 8]


def z_bin(dz: float, min_m: float = Z_MIN_M) -> str:
    return "up" if dz >= min_m else ("down" if dz <= -min_m else "none_z")


def hindsight_dirs(disp) -> dict:
    return {"dir_xy": sector_xy(float(disp[0]), float(disp[1])), "dir_z": z_bin(float(disp[2]))}


def chunk_disps(samples, fk_by_arm) -> np.ndarray:
    """(N, 3): FK(last action_exec row) - FK(first row) per sample, FK of the sample's arm (vectorized per arm)."""
    out = np.zeros((len(samples), 3))
    arms = {}
    for i, s in enumerate(samples):
        arms.setdefault(s.get("arm", "right"), []).append(i)
    for arm, idx in arms.items():
        first = np.stack([np.asarray(samples[i]["action_exec"], float)[0, :7] for i in idx])
        last = np.stack([np.asarray(samples[i]["action_exec"], float)[-1, :7] for i in idx])
        out[idx] = np.asarray(fk_by_arm[arm](last)) - np.asarray(fk_by_arm[arm](first))
    return out


def relabel(samples, fk_by_arm):
    """(new sample list, stats): committed dir_xy / dir_z = hindsight bins of each sample's own chunk; a sample without
    both committed directions is returned as it is (counted as missing). Inputs are not modified."""
    st = {"n": 0, "changed_xy": 0, "changed_z": 0, "missing": 0, "xy": {}, "z": {}}
    ok = [s for s in samples if s.get("committed", {}).get("dir_xy") is not None
          and s["committed"].get("dir_z") is not None]
    disp = dict(zip(map(id, ok), chunk_disps(ok, fk_by_arm))) if ok else {}
    out = []
    for s in samples:
        st["n"] += 1
        if id(s) not in disp:
            st["missing"] += 1
            out.append(s)
            continue
        h = hindsight_dirs(disp[id(s)])
        st["changed_xy"] += h["dir_xy"] != s["committed"]["dir_xy"]
        st["changed_z"] += h["dir_z"] != s["committed"]["dir_z"]
        st["xy"][h["dir_xy"]] = st["xy"].get(h["dir_xy"], 0) + 1
        st["z"][h["dir_z"]] = st["z"].get(h["dir_z"], 0) + 1
        out.append({**s, "committed": {**s["committed"], **h}})
    return out, st


def near_snap(aux: dict, phase: str):
    """(near, distance m) of a stage-B snapshot = runtime.core.near_contact from the row's privileged aux geometry:
    the phase's target (the stage target until lift, then the place object) within NEAR_M of the gripper finger
    midpoint, or (place stage) the held target in contact with the place object. Gripper -> place =
    g2tgt (tgt - g) - tgt2place (tgt - place). (None, None) when the needed values are missing."""
    reg, cls = (aux or {}).get("reg") or {}, (aux or {}).get("cls") or {}
    if phase in PICK_PHASES:
        d = reg.get("g2tgt_dist")
        return (None, None) if d is None else (bool(d <= NEAR_M), float(d))
    g = [reg.get(k) for k in ("g2tgt_dx", "g2tgt_dy", "g2tgt_dz")]
    p = [reg.get(k) for k in ("tgt2place_dx", "tgt2place_dy", "tgt2place_dz")]
    if None in g or None in p:
        return None, None
    d = float(np.linalg.norm(np.asarray(g, float) - np.asarray(p, float)))
    return bool(d <= NEAR_M or cls.get("contact_tgt_place") == 1), d


# ------------------------------------------------------------------------------------------ dropout / CFG
def drop_seed(seed: int) -> list:
    return [int(seed), DROP_SALT]


def drop_rows(n: int, p: float, rng) -> np.ndarray:
    return rng.random(n) < p if p > 0 else np.zeros(n, bool)


def with_dropout(model, p: float, seed: int, slots=JOY_SLOTS):
    """Install decision dropout on `model` (instance attribute over its cond method): in training mode each sample's
    `slots` of cond['dec'] become 0 with probability p. p = 0: nothing installed."""
    if p <= 0:
        return model
    import torch
    base, rng = model.cond, np.random.default_rng(drop_seed(seed))

    def cond(samples, ctx, mask, device):
        c = base(samples, ctx, mask, device)
        if model.training:
            rows = torch.as_tensor(drop_rows(len(samples), p, rng), device=c["dec"].device)
            if bool(rows.any()):
                d = c["dec"].clone()
                for j in slots:
                    d[:, j] = torch.where(rows, torch.zeros_like(d[:, j]), d[:, j])
                c = {**c, "dec": d}
        return c
    model.cond = cond
    return model


def null_cond(cond: dict, slots=JOY_SLOTS) -> dict:
    """A copy of an expert condition with the decision `slots` set to id 0 (the dropout token)."""
    d = cond["dec"].clone()
    d[:, list(slots)] = 0
    return {**cond, "dec": d}


def _cat(a: dict, b: dict) -> dict:
    import torch
    return {k: (torch.cat([v, b[k]], 0) if v is not None else None) for k, v in a.items()}


def sample_actions_cfg(expert, cond: dict, w: float, steps: int = 10, noise=None, slots=JOY_SLOTS):
    """Euler t = 1 -> 0 with decision CFG: v = v_null + w * (v_cond - v_null), conditional and null rows in one
    batched pass. w = 1: stageb_expert.sample_actions itself (the plain path, bit-identical)."""
    import torch

    from .stageb_expert import sample_actions
    if w == 1.0:
        return sample_actions(expert, cond, steps, noise)
    with torch.no_grad():
        B = cond["proprio"].shape[0]
        enc = expert.encode(_cat(cond, null_cond(cond, slots)))
        shape = (B, expert.cfg.horizon, expert.cfg.act_dim)
        x = torch.randn(shape, device=cond["proprio"].device) if noise is None else noise.float()
        dt = -1.0 / steps
        for i in range(steps):
            t = torch.full((2 * B,), 1.0 + i * dt, device=x.device)
            v = expert.velocity(enc, torch.cat([x, x], 0), t)
            vc, vn = v[:B], v[B:]
            x = x + dt * (vn + w * (vc - vn))
        return x


# ------------------------------------------------------------------------------------------ small parsers
def w_tag(w: float) -> str:
    return f"{w:g}"


def parse_ws(text: str) -> tuple:
    """Guidance grid '1,1.5,2': floats >= 0, no duplicates, 1 first (the no-CFG number is always reported)."""
    ws = tuple(float(x) for x in text.split(",") if x.strip() != "") if text else ()
    if not ws or ws[0] != 1.0 or len(set(ws)) != len(ws) or any(w < 0 for w in ws):
        raise ValueError(f"guidance grid {text!r}: needs 1 first, no duplicates, w >= 0")
    return ws


def slot_indices(names: str) -> tuple:
    qs = [q for q in names.split(",") if q]
    if not qs or len(set(qs)) != len(qs) or any(q not in QUESTIONS for q in qs):
        raise ValueError(f"null slots {names!r}: distinct names of {QUESTIONS}")
    return tuple(QUESTIONS.index(q) for q in qs)


# ------------------------------------------------------------------------------------------ marker / CLI
def _file_sha(paths):
    import os
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return {p: hashlib.sha256(open(os.path.join(root, p), "rb").read()).hexdigest()[:12] for p in paths}


def mark_prompt_config(cfg: dict, drop: float, relabel_on: bool) -> dict:
    out = {k: v for k, v in cfg.items() if k != "sha"}
    out.update(sr1b=SR1B_VER, sr1b_drop=float(drop), sr1b_relabel=bool(relabel_on), sr1b_files_sha=_file_sha(SR1B_FILES))
    out["sha"] = hashlib.sha256(json.dumps(out, sort_keys=True).encode()).hexdigest()[:12]
    return out


def build_parser():
    from . import r2_ma2 as M
    ap = M.build_parser()
    sub = next(x for x in ap._actions if x.__class__.__name__ == "_SubParsersAction")
    for name in ("train", "predict", "evalck"):
        p = sub.choices[name]
        p.add_argument("--sr1b-drop", type=float, default=0.0, help="E-SR1b decision dropout probability")
        p.add_argument("--sr1b-relabel", action="store_true", help="E-SR1b hindsight relabel of the expert decision")
        p.add_argument("--sr1b-urdf", default=URDF, help="arm URDF for the relabel FK")
    return ap


def _on(a) -> bool:
    return getattr(a, "sr1b_drop", 0.0) > 0 or getattr(a, "sr1b_relabel", False)


def install(TR, a, fk_by_arm=None) -> None:
    """Patch stageb_train for an E-SR1b run (after r2_ma2.install): relabelled samples, the prompt marker and decision
    dropout on the new model. Options off: nothing."""
    if not _on(a):
        return
    if a.data != "r2" or getattr(a, "ma2", "off") != "c0":
        raise SystemExit("--sr1b-*: --data r2 --ma2 c0 only (the E-MA2 C0 recipe)")
    if not 0.0 <= a.sr1b_drop < 1.0:
        raise SystemExit("--sr1b-drop: 0 <= p < 1")
    load0, pc0, nm0 = TR._load_data, TR.prompt_config, TR.new_model

    def _load_data(args):
        samples, hz, tr, va = load0(args)
        if not args.sr1b_relabel:
            return samples, hz, tr, va
        fk = fk_by_arm
        if fk is None:
            from .se2e_data import fk_ee, load_arm_chain
            chains = {arm: load_arm_chain(args.sr1b_urdf, arm) for arm in {s.get("arm", "right") for s in samples}}
            fk = {arm: (lambda q, c=c: fk_ee(c, q)) for arm, c in chains.items()}
        new, st = relabel(samples, fk)
        m = {id(s): n for s, n in zip(samples, new)}
        print(json.dumps({"event": "sr1b_relabel", **st}), flush=True)
        return new, hz, [m[id(s)] for s in tr], [m[id(s)] for s in va]

    def prompt_config(*x, **kw):
        return mark_prompt_config(pc0(*x, **kw), a.sr1b_drop, a.sr1b_relabel)

    def new_model(*x, **kw):
        return with_dropout(nm0(*x, **kw), a.sr1b_drop, a.seed)
    TR._load_data, TR.prompt_config, TR.new_model = _load_data, prompt_config, new_model


def main(argv=None):
    from . import r2_ma2 as M
    from . import stageb_train as TR
    a = build_parser().parse_args(argv)
    if a.cmd == "ma2eval":
        M.cmd_ma2eval(a)
        return
    M.install(TR, a)
    install(TR, a)
    {"smoke": TR.cmd_smoke, "train": TR.cmd_train, "evalck": TR.cmd_evalck, "predict": TR.cmd_predict}[a.cmd](a)


if __name__ == "__main__":
    main()
