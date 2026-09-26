"""Fetch single packages out of a MolmoSpaces shard by HTTP range (no full-shard download), then unpack them.
arrow_table.json rows: {path, shard_id, offset, size}; the package is the tar member's data at [offset, offset+size).
usage: python tools/l8x_assets/range_fetch.py --base HF_DIR_URL --arrow arrow_table.json --names n1,n2 | --list FILE
       --out DIR [--unpack]
Token: /data/.hf_token (never printed). Packages are .tar.zst; --unpack extracts each into DIR/<name>/."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import urllib.request


def fetch(url: str, offset: int, size: int, token: str | None, tries: int = 4) -> bytes:
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"Range": f"bytes={offset}-{offset + size - 1}",
                                                       **({"Authorization": f"Bearer {token}"} if token else {})})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            if len(data) == size:
                return data
            raise IOError(f"got {len(data)} of {size} bytes")
        except Exception:  # noqa: BLE001
            if k == tries - 1:
                raise
            time.sleep(2 * (k + 1))
    raise AssertionError


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help=".../resolve/main/isaac/objects/objaverse/20260128")
    ap.add_argument("--arrow", required=True)
    ap.add_argument("--names", default=None)
    ap.add_argument("--list", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--unpack", action="store_true")
    a = ap.parse_args(argv)
    rows = {r["path"]: r for r in json.load(open(a.arrow))}
    names = a.names.split(",") if a.names else [ln.strip() for ln in open(a.list) if ln.strip()]
    tok = open("/data/.hf_token").read().strip() if os.path.exists("/data/.hf_token") else None
    os.makedirs(a.out, exist_ok=True)
    n_ok = 0
    for n in names:
        r = rows[n]
        dst = os.path.join(a.out, n)
        if not os.path.exists(dst):
            data = fetch(f"{a.base}/shards/{int(r['shard_id']):05d}.tar", int(r["offset"]), int(r["size"]), tok)
            with open(dst + ".part", "wb") as f:
                f.write(data)
            os.replace(dst + ".part", dst)
        if a.unpack:
            d = os.path.join(a.out, n.replace(".tar.zst", ""))
            if not os.path.isdir(d):
                os.makedirs(d)
                subprocess.run(f"zstd -dc '{dst}' | tar xf - -C '{d}'", shell=True, check=True)
        n_ok += 1
    print("fetched", n_ok, "->", a.out)


if __name__ == "__main__":
    main()
