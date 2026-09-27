"""E-PRIV8 M3 training = harvest.teach_l8.train unchanged except the micro-batch dataset: each control row with an
alternative (v2, hand information) variant is encoded as that variant with p_hand(k / total), k = micro-batch index in
training order, total = --max-steps x --accum (the micro-batches actually used). Same CLI as teach_l8.train.
python -m harvest.teach_strip8.train_curr --data train_m3.jsonl --out <dir> --epochs 1 --max-steps 816 ..."""
from __future__ import annotations

import sys

from ..teach_l8 import train as T
from . import priv as P


class CurrMBData(T.MBData):
    total = 1
    seed = 0

    def __getitem__(self, k):
        items = [self.enc(P.choose(self.rows[i], k, j, self.total, self.seed)) for j, i in enumerate(self.mbs[k])]
        return T.collate(items, self.pad), sum(x["n_answer"] for x in items), len(items)


def _arg(argv, name, default):
    return type(default)(argv[argv.index(name) + 1]) if name in argv else default


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    steps, accum = _arg(argv, "--max-steps", 0), _arg(argv, "--accum", 4)
    if steps <= 0:
        raise SystemExit("train_curr needs --max-steps (the schedule is over the used micro-batches)")
    CurrMBData.total = steps * accum
    CurrMBData.seed = _arg(argv, "--seed", 0)
    T.MBData = CurrMBData
    T.main(argv)


if __name__ == "__main__":
    main()
