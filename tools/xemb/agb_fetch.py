"""AgiBot World Beta (agibot-world/AgiBotWorld-Beta, CC BY-NC-SA 4.0, gated: the user accepted the terms; research
only, never sent to Astra). Token from /data/.hf_token (never printed).

DISK RULES (user, 2026-09-28) -- enforced here:
  * everything AgiBot lives under ROOT = /data/harvest/data/agibot; its total size must stay <= 3 TB.
  * AgiBot + RH20T share 3 TB; over 2 TB -> NOTIFY_2TB marker + log line (tell the coordinator, keep going).
  * before every download: if du(ROOT) + the file size > 2.7 TB -> do NOT download; write STOP_DISK and exit 3 (the
    coordinator is told; nothing is deleted to make room -- deleting anything else needs the user's approval).
  * the ONLY deletion allowed: a temporary tar downloaded by this pipeline, right after its needed members were
    extracted AND verified (release_tar). Extracted results, other data and other teams' files are never deleted.
usage: python -m xemb.agb_fetch list PREFIX
       python -m xemb.agb_fetch get PATH [SUBDIR]
"""
from __future__ import annotations

import os
import subprocess
import sys

REPO = "agibot-world/AgiBotWorld-Beta"
ROOT = "/data/harvest/data/agibot"
BUDGET, STOP_AT = 3.0e12, 2.7e12
LOG = os.path.join(ROOT, "disk.log")


def _api():
    from huggingface_hub import HfApi
    return HfApi(token=open("/data/.hf_token").read().strip())


def du(path=ROOT) -> int:
    out = subprocess.run(["du", "-sb", path], capture_output=True, text=True).stdout.split()
    return int(out[0]) if out else 0


def _log(msg):
    import time
    os.makedirs(ROOT, exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}\n")


def listing(prefix):
    from huggingface_hub.hf_api import RepoFile
    items = _api().list_repo_tree(REPO, path_in_repo=prefix, repo_type="dataset", recursive=True)
    return [(i.path, i.size) for i in items if isinstance(i, RepoFile)]


def get(path, subdir="raw", size=None):
    """Download one file into ROOT/subdir unless the disk rule forbids it. Returns the local path or None."""
    if size is None:
        size = dict(listing(os.path.dirname(path))).get(path, 0)
    used = du()
    if used + size > STOP_AT:
        _log(f"STOP_DISK used={used} need={size} path={path}")
        open(os.path.join(ROOT, "STOP_DISK"), "w").write(f"used {used} + {size} > {STOP_AT}\n")
        return None
    if used + size > 2.0e12 and not os.path.exists(os.path.join(ROOT, "NOTIFY_2TB")):  # notify only, keep going
        _log(f"NOTIFY_2TB used={used}")
        open(os.path.join(ROOT, "NOTIFY_2TB"), "w").write(f"{used}\n")
    from huggingface_hub import hf_hub_download
    dst = hf_hub_download(REPO, path, repo_type="dataset", local_dir=os.path.join(ROOT, subdir),
                          token=open("/data/.hf_token").read().strip())
    _log(f"GET {path} size={os.path.getsize(dst)} used_after={du()}")
    return dst


def release_tar(tar_path, verified: bool):
    """The one allowed deletion: a pipeline-downloaded tar, only after its members were extracted and verified."""
    if not verified:
        _log(f"KEEP {tar_path} (not verified)")
        return False
    if not (tar_path.startswith(os.path.join(ROOT, "raw")) and tar_path.endswith((".tar", ".tar.gz"))):
        raise ValueError(f"refusing to delete a non-pipeline file: {tar_path}")
    os.remove(tar_path)
    _log(f"DEL {tar_path} used_after={du()}")
    return True


if __name__ == "__main__":
    if sys.argv[1] == "list":
        fs = listing(sys.argv[2])
        for p, s in fs:
            print(p, s)
        print("TOTAL", len(fs), round(sum(s for _, s in fs) / 1e9, 2), "GB")
    elif sys.argv[1] == "get":
        r = get(sys.argv[2], *(sys.argv[3:4] or ["raw"]))
        print(r if r else "STOP_DISK")
        sys.exit(0 if r else 3)
