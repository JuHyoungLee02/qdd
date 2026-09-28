"""Download the RefSpatial Simulator subset (Apache-2.0: metadata.json + image.tar.gz, about 6 GB) to /data and unpack
the images. usage: python refsp_get.py <out dir>"""
import os
import sys
import tarfile

from huggingface_hub import hf_hub_download

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
tok = open("/data/.hf_token").read().strip() if os.path.exists("/data/.hf_token") else None
for f in ("Simulator/metadata.json", "Simulator/image/image.tar.gz"):
    p = hf_hub_download("JingkunAn/RefSpatial", f, repo_type="dataset", local_dir=out, token=tok)
    print("GOT", p, os.path.getsize(p), flush=True)
tgz = os.path.join(out, "Simulator/image/image.tar.gz")
dst = os.path.join(out, "Simulator/image")
if not os.path.exists(os.path.join(dst, ".unpacked")):
    with tarfile.open(tgz) as t:
        t.extractall(dst)
    open(os.path.join(dst, ".unpacked"), "w").close()
print("UNPACKED", sum(len(fs) for _, _, fs in os.walk(dst)), flush=True)
