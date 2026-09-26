"""E-SR1e OPT-IN training entry (docs/stage3/prereg_sr1e.md): the E-SR1d options (harvest/train/sr1d.py, unchanged)
plus one memory option. Nothing here is read by the default training / runtime path.

  --sr1e-branch-chunk n   compute the branch flow-matching loss (sr1c.with_branches' fm_branch) over consecutive
                          pieces of n branch samples: each piece gets its own no-grad shared-prefix context and expert
                          pass; the loss is the valid-count weighted mean over the pieces (= the one-pass loss up to
                          the flow-time / noise draws, which are made per piece). 0 = off (one pass, = E-SR1d).
                          Needed for --sr1d-frac 0.75 (24 branch samples per step: one pass peaks at about 83 GB).

  python -m harvest.train.sr1e train <harvest.train.sr1d train arguments> --sr1e-branch-chunk 8
"""
from __future__ import annotations

import functools

SR1E_VER = "sr1e@v1"


def fm_branch_chunked(model, bs, enc, device, size: int):
    from .stageb_expert import fm_loss
    num, den = 0.0, 0.0
    for i in range(0, len(bs), size):
        part = bs[i:i + size]
        ctx, mask, _ = model.forward_shared(part, enc, device, grad=False)
        a, valid, _ = model.targets(part, device)
        w = (valid.float().sum() * a.shape[-1]).clamp_min(1.0)
        num = num + fm_loss(model.expert, model.cond(part, ctx, mask, device), a, valid) * w
        den = den + w
    return num / den


def build_parser():
    from . import sr1d
    ap = sr1d.build_parser()
    sub = next(x for x in ap._actions if x.__class__.__name__ == "_SubParsersAction")
    for name in ("train", "predict", "evalck"):
        sub.choices[name].add_argument("--sr1e-branch-chunk", type=int, default=0,
                                       help="E-SR1e: branch FM loss over pieces of n samples (0 = one pass)")
    return ap


def install(TR, a) -> None:
    """E-SR1d install, with the chunked branch loss when --sr1e-branch-chunk > 0."""
    from . import sr1c, sr1d
    n = int(getattr(a, "sr1e_branch_chunk", 0) or 0)
    if n < 0:
        raise SystemExit("--sr1e-branch-chunk >= 0")
    if n and not sr1d.on(a):
        raise SystemExit("--sr1e-branch-chunk with the E-SR1d branch options only")
    if n:
        sr1c.with_branches = functools.partial(sr1c.with_branches,
                                               fm_branch=functools.partial(fm_branch_chunked, size=n))
    sr1d.install(TR, a)
    if n:
        pct = TR.prompt_config_t

        def prompt_config_t(*x, **kw):
            import hashlib
            import json
            out = {k: v for k, v in pct(*x, **kw).items() if k != "sha"}
            out.update(sr1e=SR1E_VER, sr1e_branch_chunk=n)
            out["sha"] = hashlib.sha256(json.dumps(out, sort_keys=True).encode()).hexdigest()[:12]
            return out
        TR.prompt_config_t = prompt_config_t


def main(argv=None):
    from . import stageb_train as TR
    a = build_parser().parse_args(argv)
    install(TR, a)
    {"smoke": TR.cmd_smoke, "train": TR.cmd_train, "evalck": TR.cmd_evalck, "predict": TR.cmd_predict}[a.cmd](a)


if __name__ == "__main__":
    main()
