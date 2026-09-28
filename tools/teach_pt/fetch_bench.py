"""Download the two public pointing benchmarks of the G bundle (evaluation only; Apache-2.0, not gated) to /data and
list their files. usage: python fetch_bench.py <out dir>"""
import os
import sys

from huggingface_hub import snapshot_download

out = sys.argv[1]
for repo, name in (("wentao-yuan/where2place", "where2place"), ("BAAI/RefSpatial-Bench", "refspatial_bench")):
    d = snapshot_download(repo_id=repo, repo_type="dataset", local_dir=os.path.join(out, name))
    files = []
    for root, _, fs in os.walk(d):
        for f in fs:
            if ".cache" not in root:
                files.append(os.path.relpath(os.path.join(root, f), d))
    print(name, len(files), sorted(files)[:12])
