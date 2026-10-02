#!/bin/bash
# E-LIBFT: official LIBERO training demos (HF yifengzhu-hf/LIBERO-datasets, Apache-2.0) for the 4 evaluated suites
# -> /data/harvest/lib0/libero_datasets/<suite>/*.hdf5 (libero_90 not fetched). usage: fetch_data.sh
set -e
R=/data/harvest/lib0; export HF_HOME=/data/harvest/cache/hf TMPDIR=/data/harvest/tmp HOME=/data/harvest/home
$R/openpi/.venv/bin/python - <<'PY'
from huggingface_hub import snapshot_download
p = snapshot_download("yifengzhu-hf/LIBERO-datasets", repo_type="dataset",
                      allow_patterns=["libero_spatial/*", "libero_object/*", "libero_goal/*", "libero_10/*", "README.md"],
                      local_dir="/data/harvest/lib0/libero_datasets")
print(p)
PY
du -sh $R/libero_datasets/*; echo "$(date -u +%FT%TZ) DONE"
