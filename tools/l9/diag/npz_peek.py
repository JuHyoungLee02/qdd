"""L9 v2 diagnosis: keys / shapes / first values of an npz (numpy only).
usage: python tools/l9/diag/npz_peek.py <file.npz> [key ...]"""
import sys

import numpy as np


def main():
    d = np.load(sys.argv[1], allow_pickle=True)
    for k in d.files:
        v = d[k]
        print(k, v.shape, v.dtype, (v[:3] if v.ndim else v) if k in sys.argv[2:] or v.size < 40 else "")


if __name__ == "__main__":
    main()
