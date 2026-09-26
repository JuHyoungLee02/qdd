"""E-SR1d OPT-IN training options (docs/stage3/prereg_sr1d.md): the adopted E-SR1c recipe (far-segment counterfactual
branch data, 50 % of the expert flow-matching batch) on the REAL S-E2E data (se2e_c1, motion line), canon §89. Nothing
here is read by the default training / runtime path; the baseline files (stageb_*, se2e_*, sr1c*) are not modified.

  --sr1d-branch DIR  branch rows (tools/sr1d/gen_branches.py: <DIR>/<kind>_<part>.jsonl), joined to their source
                     sample by key <kind>_ep<seed>_k<k> (same frames / text / motion line / proprio; forced joystick
                     decision; target chunk = the kinematic forced-direction chunk; no decision items). Sources must be
                     TRAIN-split samples; with --sr1d-mode far every branch row must carry stratum 'far' (a = 1).
  --sr1d-frac f      share of the expert FM batch made of branch samples (sr1c.with_branches: per step
                     round(n_real f / (1 - f)) branch samples, numpy RNG (seed, SALT), no-grad shared-prefix context,
                     L_fm = (1 - f) L_fm(real) + f L_fm(branch)). Branch samples keep their motion line (no motion
                     dropout: the evaluation never drops it); the real part (motion dropout, decision loss) is the
                     baseline's.
  --sr1d-mode far|all  registered primary (far) / fallback (all strata).
Composes with stageb_train --data se2e --motion-line se2e-motion@v1 (the motion_s1 / s2 recipe). Options off ->
stageb_train.main unchanged (test).

  python -m harvest.train.sr1d train --data se2e --se2e-root R --se2e-t-root R --motion-line se2e-motion@v1 \
      --motion-bins B --sr1d-branch DIR --sr1d-frac 0.5 --batch 8 --max-steps 2000 ... --seed {1,2}
"""
from __future__ import annotations

import glob
import hashlib
import json
import os

import numpy as np

SR1D_VER = "sr1d@v1"
SR1D_FILES = ("harvest/train/sr1d.py", "harvest/train/sr1d_kin.py", "harvest/train/sr1c.py")
MODES = ("far", "all")


def key_of(kind, seed, k) -> str:
    return f"{kind}_ep{int(seed)}_k{int(k)}"


def branch_sample(src: dict, br: dict, j: int, mode: str = "far") -> dict:
    """The stage-B sample of branch row `br` on its S-E2E source sample `src` (not modified)."""
    from . import stageb_data as D
    if src.get("split") != "train":
        raise ValueError(f"{src['key']}: branch source split {src.get('split')!r} (train only)")
    b = br.get("branch") or {}
    if not b.get("ok"):
        raise ValueError(f"{src['key']}: branch row without an accepted kinematic check")
    if mode == "far" and (b.get("stratum") != "far" or b.get("a") != 1.0):
        raise ValueError(f"{src['key']}: branch source stratum {b.get('stratum')!r} (far only)")
    acts = []
    for key in ("action_exec", "action_script"):
        a = np.array(br[key], np.float64)
        a[:, 7] = D.grip_open01(a[:, 7], src["grip_src"])
        acts.append(a.tolist())
    return {**src, "key": f"{src['key']}_br{j}", "items": [], "committed": {**src["committed"], **br["committed"]},
            "action_exec": acts[0], "action_script": acts[1], "valid": list(br["valid"]), "verify": None,
            "branch": True}


def join_branches(by_key: dict, rows, mode: str = "far") -> tuple:
    out, st, nj = [], {"n_rows": 0, "joined": 0, "missing": 0}, {}
    for br in rows:
        st["n_rows"] += 1
        key = key_of(br["kind"], br["seed"], br["k"])
        src = by_key.get(key)
        if src is None:
            st["missing"] += 1
            continue
        j = nj.get(key, 0)
        nj[key] = j + 1
        out.append(branch_sample(src, br, j, mode))
        st["joined"] += 1
    if out:
        st["sources"] = len(nj)
    return out, st


def read_branch_rows(root: str):
    for p in sorted(glob.glob(os.path.join(root, "*.jsonl"))):
        for x in open(p, encoding="utf-8"):
            yield json.loads(x)


def _file_sha(paths):
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return {p: hashlib.sha256(open(os.path.join(root, p), "rb").read()).hexdigest()[:12] for p in paths}


def mark_prompt_config(cfg: dict, a) -> dict:
    out = {k: v for k, v in cfg.items() if k != "sha"}
    out.update(sr1d=SR1D_VER, sr1d_frac=float(a.sr1d_frac), sr1d_branch=a.sr1d_branch, sr1d_mode=a.sr1d_mode,
               sr1d_files_sha=_file_sha(SR1D_FILES))
    out["sha"] = hashlib.sha256(json.dumps(out, sort_keys=True).encode()).hexdigest()[:12]
    return out


def build_parser():
    from . import stageb_train as TR
    ap = TR.build_parser()
    sub = next(x for x in ap._actions if x.__class__.__name__ == "_SubParsersAction")
    for name in ("train", "predict", "evalck"):
        p = sub.choices[name]
        p.add_argument("--sr1d-branch", default="", help="E-SR1d branch rows root (tools/sr1d/gen_branches.py)")
        p.add_argument("--sr1d-frac", type=float, default=0.0, help="E-SR1d branch share of the expert FM batch")
        p.add_argument("--sr1d-mode", default="far", choices=MODES, help="E-SR1d eligible strata (far / all)")
    return ap


def on(a) -> bool:
    return bool(getattr(a, "sr1d_branch", "")) or getattr(a, "sr1d_frac", 0.0) > 0


def install(TR, a) -> None:
    """Patch stageb_train for an E-SR1d run. Options off: nothing."""
    if not on(a):
        return
    if a.data != "se2e" or getattr(a, "motion_line", "none") == "none":
        raise SystemExit("--sr1d-*: --data se2e with the motion line only (the motion_s1 / s2 recipe)")
    if not 0.0 < a.sr1d_frac < 1.0 or not a.sr1d_branch:
        raise SystemExit("--sr1d-frac in (0, 1) together with --sr1d-branch")
    from .sr1c import with_branches
    load0, pct0, nm0 = TR._load_data, TR.prompt_config_t, TR.new_model
    holder = {"branches": []}

    def _load_data(args):
        samples, hz, tr, va = load0(args)
        by = {s["key"]: s for s in tr}
        bs, st = join_branches(by, read_branch_rows(args.sr1d_branch), args.sr1d_mode)
        if st["missing"]:
            raise SystemExit(f"--sr1d-branch: {st['missing']} branch rows without a train-split source")
        holder["branches"] = bs
        print(json.dumps({"event": "sr1d_branches", **st}), flush=True)
        return samples, hz, tr, va

    def prompt_config_t(*x, **kw):
        return mark_prompt_config(pct0(*x, **kw), a)

    def new_model(*x, **kw):
        return with_branches(nm0(*x, **kw), holder["branches"], a.sr1d_frac, a.seed)
    TR._load_data, TR.prompt_config_t, TR.new_model = _load_data, prompt_config_t, new_model


def main(argv=None):
    from . import stageb_train as TR
    a = build_parser().parse_args(argv)
    install(TR, a)
    {"smoke": TR.cmd_smoke, "train": TR.cmd_train, "evalck": TR.cmd_evalck, "predict": TR.cmd_predict}[a.cmd](a)


if __name__ == "__main__":
    main()
