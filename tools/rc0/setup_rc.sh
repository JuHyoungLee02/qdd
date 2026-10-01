#!/bin/bash
# E-RC0 setup (RoboCasa365 + official pi05 checkpoint), everything under /data/harvest/rc:
#   openpi/      robocasa-benchmark/openpi @ ca4c6d7 (the leaderboard submission's code), its uv venv (server AND client)
#   robosuite/   ARISE-Initiative/robosuite master, robocasa/ robocasa/robocasa (installed -e into the same venv)
#   assets: robocasa download_kitchen_assets (~10 GB); checkpoint HF robocasa/robocasa365_checkpoints
#           pi05_pretrain_human300/multitask_learning/75000
set -e
R=/data/harvest/rc; UV=/data/harvest/lib0/bin/uv
export UV_CACHE_DIR=/data/harvest/lib0/cache/uv UV_PYTHON_INSTALL_DIR=/data/harvest/lib0/uvpython HOME=/data/harvest/home
export TMPDIR=/data/harvest/tmp UV_LINK_MODE=copy GIT_LFS_SKIP_SMUDGE=1 HF_HOME=/data/harvest/cache/hf
cd $R
[ -d robosuite/.git ] || git clone -q https://github.com/ARISE-Initiative/robosuite
[ -d robocasa/.git ] || git clone -q https://github.com/robocasa/robocasa
(cd robosuite && git rev-parse HEAD) > $R/commits.txt; (cd robocasa && git rev-parse HEAD) >> $R/commits.txt
cd $R/openpi
grep -q "evdev; sys_platform" pyproject.toml || sed -i 's/^override-dependencies = \[/override-dependencies = ["evdev; sys_platform == '"'"'never'"'"'", /' pyproject.toml
$UV sync || true
V=$R/openpi/.venv/bin/python
$UV pip install --python $V -e $R/robosuite
$UV pip install --python $V -e $R/robocasa
$UV pip install --python $V "opencv-python-headless" imageio[ffmpeg] httpx
$V -m robocasa.scripts.setup_macros || true
yes | $V -m robocasa.scripts.download_kitchen_assets
$V -c "from huggingface_hub import snapshot_download; print(snapshot_download('robocasa/robocasa365_checkpoints', allow_patterns=['pi05_pretrain_human300/multitask_learning/75000/*'], local_dir='$R/ckpt'))"
echo "$(date -u +%FT%TZ) DONE"
