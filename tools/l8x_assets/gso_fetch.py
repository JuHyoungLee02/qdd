"""Google Scanned Objects (Gazebo Fuel owner GoogleResearch): list every model with its licence and categories, and
download the chosen ones (zip: meshes/model.obj + materials/textures/texture.png + model.sdf).
Only CC BY 4.0 models are downloaded (the licence comes from the Fuel API per model).
usage: python tools/l8x_assets/gso_fetch.py list OUT.json
       python tools/l8x_assets/gso_fetch.py get LIST.json DIR [--categories a,b] [--max N]"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

API = "https://fuel.gazebosim.org/1.0/GoogleResearch/models"
CCBY = "Creative Commons Attribution 4.0 International"


def _get(url: str, tries: int = 4) -> bytes:
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "qdd-l8x"}),
                                        timeout=120) as r:
                return r.read()
        except Exception:  # noqa: BLE001
            if k == tries - 1:
                raise
            time.sleep(3 * (k + 1))
    raise AssertionError


def list_models() -> list:
    out, page = [], 1
    while True:
        try:
            rows = json.loads(_get(f"{API}?per_page=100&page={page}", tries=1))
        except urllib.error.HTTPError as e:  # Fuel answers 404 past the last page
            if e.code == 404:
                return out
            raise
        if not rows:
            return out
        out += [{"name": r["name"], "license": r.get("license_name"), "categories": r.get("categories") or [],
                 "description": r.get("description"), "filesize": r.get("filesize")} for r in rows]
        page += 1


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("list", "get"))
    ap.add_argument("a")
    ap.add_argument("b", nargs="?")
    ap.add_argument("--categories", default=None)
    ap.add_argument("--max", type=int, default=10000)
    ap.add_argument("--shard", default="0/1", help="k/n: this process takes every n-th model from k")
    a = ap.parse_args(argv)
    if a.cmd == "list":
        rows = list_models()
        with open(a.a, "w") as f:
            json.dump(rows, f, indent=1)
        cats = {}
        for r in rows:
            for c in r["categories"] or ["(none)"]:
                cats[c] = cats.get(c, 0) + 1
        print(len(rows), "models; licences", {l: sum(r["license"] == l for r in rows) for l in {r["license"] for r in rows}})
        print("categories", sorted(cats.items(), key=lambda kv: -kv[1]))
        return
    rows = json.load(open(a.a))
    k, nsh = (int(x) for x in a.shard.split("/"))
    rows = rows[k::nsh]
    want = set(a.categories.split(",")) if a.categories else None
    n = 0
    os.makedirs(a.b, exist_ok=True)
    for r in rows:
        if r["license"] != CCBY or (want and not (set(r["categories"] or ["(none)"]) & want)):
            continue
        d = os.path.join(a.b, r["name"])
        if not os.path.isdir(d):
            z = d + ".zip"
            with open(z + ".part", "wb") as f:
                f.write(_get(f"{API}/{urllib.parse.quote(r['name'])}.zip"))  # names can hold é
            os.replace(z + ".part", z)
            os.makedirs(d)
            zipfile.ZipFile(z).extractall(d)
            os.remove(z)
        n += 1
        if n >= a.max:
            break
    print("have", n, "->", a.b)


if __name__ == "__main__":
    main()
