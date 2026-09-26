"""E-SR1c OPT-IN training options (docs/stage3/prereg_sr1c.md; research doc decision_adherence_0p8_2026-09-26.md
§6): far-segment counterfactual branch data and the authority-gated joystick adaLN expert. Nothing here is read by the
default training / runtime path; the baseline files (stageb_*, prefix_share, r2_ma2, sr1b) are not modified.

  --cf-branch DIR   branch rows (tools/sr1c/gen_branches.py: <DIR>/<variant>_<task>_<kind>.jsonl), joined to their
                    source snapshot by sample id (same frames / text / proprio; forced joystick decision + the
                    source's target / phase labels; target chunk = the forced-direction IK chunk; no decision items,
                    no aux / verification targets). Sources must be FIT-split (stage-B train) snapshots with privileged
                    authority 1.
  --cf-frac f       share of the expert flow-matching batch made of branch samples: per training step
                    round(n_real f / (1 - f)) branch samples drawn uniformly with replacement (numpy RNG (seed, SALT),
                    independent of the torch stream), their context from a no-grad shared-prefix pass (KI stop: the
                    expert loss never reaches the backbone); L_fm = (1 - f) L_fm(real) + f L_fm(branch). The real part
                    (decision, aux, verification losses) is the baseline's.
  --dec-cond adaln@v1   C2: sr1c_film.AdaLNExpert gated by the estimated authority (sr1c_authority.estimated).
Composes with r2_ma2 (--ma2 c0 = the E-MA2 C0 recipe and marker). All options off -> r2_ma2.main unchanged (test).

  python -m harvest.train.sr1c train --data r2 --pool <views> --ma2 c0 --cf-branch DIR --cf-frac 0.5 \
      [--dec-cond adaln@v1] --batch 8 --max-steps 2000 --eval-every 500 --val-per-kind 50 --run c1 ...
"""
from __future__ import annotations

import glob
import hashlib
import json
import os

import numpy as np

SR1C_VER = "sr1c@v1"
SR1C_FILES = ("harvest/train/sr1c.py", "harvest/train/sr1c_authority.py", "harvest/train/sr1c_film.py")
SALT = 0x5121C
DEC_CONDS = ("none", "adaln@v1")


# ------------------------------------------------------------------------------------------ branch samples
def sid_of(variant, task, kind, seed, k) -> str:
    return f"{variant}/{task}/{kind}/ep{int(seed)}/k{int(k)}"


def branch_sample(src: dict, br: dict, j: int) -> dict:
    """The stage-B sample of branch row `br` on its source sample `src` (not modified)."""
    from . import sr1c_authority as A
    from . import stageb_data as D
    if src.get("split") != "train":
        raise ValueError(f"{src['key']}: branch source split {src.get('split')!r} (fit / train only)")
    if A.privileged(src["aux"], src["phase_id"]) != 1.0:
        raise ValueError(f"{src['key']}: branch source authority != 1")
    acts = []
    for key in ("action_exec", "action_script"):
        a = np.array(br[key], np.float64)
        a[:, 7] = D.grip_open01(a[:, 7], src.get("grip_src", "sim_width_m"))
        acts.append(a.tolist())
    return {**src, "key": f"{src['key']}_br{j}", "items": [], "committed": {**src["committed"], **br["committed"]},
            "action_exec": acts[0], "action_script": acts[1], "valid": list(br["valid"]),
            "aux": {"reg": {}, "cls": {}}, "verify": None, "branch": True}


def join_branches(by_id: dict, rows) -> tuple:
    """([branch samples], stats) for branch rows joined to {sample id: source sample}."""
    out, st, nj = [], {"n_rows": 0, "joined": 0, "missing": 0}, {}
    for br in rows:
        st["n_rows"] += 1
        sid = sid_of(br["variant"], br["task"], br["kind"], br["seed"], br["k"])
        src = by_id.get(sid)
        if src is None:
            st["missing"] += 1
            continue
        j = nj.get(sid, 0)
        nj[sid] = j + 1
        out.append(branch_sample(src, br, j))
        st["joined"] += 1
    if out:
        st["sources"] = len(nj)
    return out, st


def read_branch_rows(root: str):
    for p in sorted(glob.glob(os.path.join(root, "*.jsonl"))):
        for x in open(p, encoding="utf-8"):
            yield json.loads(x)


# ------------------------------------------------------------------------------------------ loss mixing
def n_branch(n_real: int, frac: float) -> int:
    return int(round(n_real * frac / (1.0 - frac)))


def fm_branch_default(model, bs, enc, device):
    """Flow-matching loss of branch samples (no-grad shared-prefix context; KI stop keeps the backbone out)."""
    from .stageb_expert import fm_loss
    ctx, mask, _ = model.forward_shared(bs, enc, device, grad=False)
    a, valid, _ = model.targets(bs, device)
    return fm_loss(model.expert, model.cond(bs, ctx, mask, device), a, valid)


def with_branches(model, branches, frac: float, seed: int, fm_branch=None):
    """Install the branch mix on model.losses (instance attribute; training mode only)."""
    if frac <= 0:
        return model
    if not branches:
        raise ValueError("--cf-frac > 0 without branch samples")
    base, rng = model.losses, np.random.default_rng([int(seed), SALT])
    fmb = fm_branch or fm_branch_default

    def losses(samples, enc, device, vqa=None, fm_t=None, fm_noise=None):
        if not model.training:
            return base(samples, enc, device, vqa=vqa, fm_t=fm_t, fm_noise=fm_noise)
        lam = model.lam["act"]
        model.lam["act"] = lam * (1.0 - frac)
        try:
            total, logs = base(samples, enc, device, vqa=vqa, fm_t=fm_t, fm_noise=fm_noise)
        finally:
            model.lam["act"] = lam
        nb = n_branch(len(samples), frac)
        bs = [branches[i] for i in rng.integers(0, len(branches), size=nb)]
        lb = fmb(model, bs, enc, device)
        total = total + lam * frac * lb
        logs = {**logs, "fm_branch": float(lb.detach()), "n_branch": nb, "total": float(total.detach())}
        return total, logs
    model.losses = losses
    return model


# ------------------------------------------------------------------------------------------ marker / CLI
def _file_sha(paths):
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return {p: hashlib.sha256(open(os.path.join(root, p), "rb").read()).hexdigest()[:12] for p in paths}


def mark_prompt_config(cfg: dict, a) -> dict:
    out = {k: v for k, v in cfg.items() if k != "sha"}
    out.update(sr1c=SR1C_VER, sr1c_cf_frac=float(a.cf_frac), sr1c_cf_branch=a.cf_branch, sr1c_dec_cond=a.dec_cond,
               sr1c_files_sha=_file_sha(SR1C_FILES))
    out["sha"] = hashlib.sha256(json.dumps(out, sort_keys=True).encode()).hexdigest()[:12]
    return out


def build_parser():
    from . import r2_ma2 as M
    ap = M.build_parser()
    sub = next(x for x in ap._actions if x.__class__.__name__ == "_SubParsersAction")
    for name in ("train", "predict", "evalck"):
        p = sub.choices[name]
        p.add_argument("--cf-branch", default="", help="E-SR1c branch rows root (tools/sr1c/gen_branches.py)")
        p.add_argument("--cf-frac", type=float, default=0.0, help="E-SR1c branch share of the expert FM batch")
        p.add_argument("--dec-cond", default="none", choices=DEC_CONDS, help="E-SR1c C2: authority-gated adaLN")
    return ap


def on(a) -> bool:
    return bool(getattr(a, "cf_branch", "")) or getattr(a, "cf_frac", 0.0) > 0 or getattr(a, "dec_cond",
                                                                                           "none") != "none"


def install(TR, a) -> None:
    """Patch stageb_train for an E-SR1c run (after r2_ma2.install). Options off: nothing."""
    if not on(a):
        return
    if a.data != "r2" or getattr(a, "ma2", "off") != "c0":
        raise SystemExit("--cf-* / --dec-cond: --data r2 --ma2 c0 only (the E-MA2 C0 recipe)")
    if not 0.0 <= a.cf_frac < 1.0 or (a.cf_frac > 0) != bool(a.cf_branch):
        raise SystemExit("--cf-frac in [0, 1) and > 0 exactly when --cf-branch is given")
    from .r2_ma2 import sample_id
    load0, pc0, nm0 = TR._load_data, TR.prompt_config, TR.new_model
    holder = {"branches": []}

    def _load_data(args):
        samples, hz, tr, va = load0(args)
        if args.cf_branch:
            by = {}
            for s in tr:
                by.setdefault(sample_id(s["context"]["images"][0][1]), s)
            bs, st = join_branches(by, read_branch_rows(args.cf_branch))
            if st["missing"]:
                raise SystemExit(f"--cf-branch: {st['missing']} branch rows without a train-split source")
            holder["branches"] = bs
            print(json.dumps({"event": "sr1c_branches", **st}), flush=True)
        return samples, hz, tr, va

    def prompt_config(*x, **kw):
        return mark_prompt_config(pc0(*x, **kw), a)

    def new_model(*x, **kw):
        from . import sr1c_film as F
        m = nm0(*x, **kw)
        if a.dec_cond == "adaln@v1":
            F.swap_expert(m)
            F.mark_heads(m)
            F.install_authority(m)
        return with_branches(m, holder["branches"], a.cf_frac, a.seed)
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
