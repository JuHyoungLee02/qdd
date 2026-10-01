#!/bin/bash
# E-LIBP setup: LIBERO-plus (sylvestf/LIBERO-plus, MIT per HF card; repo license field empty) in its own venv
# (= venv_libero package set + LIBERO-plus -e + Wand / scikit-image; ImageMagick from conda-forge under /data), assets
# from HF datasets/Sylvest/LIBERO-plus assets.zip -> libero/libero/assets. usage: setup_liberoplus.sh
set -e
R=/data/harvest/lib0; P=$R/LIBERO-plus; V=$R/venv_liberoplus
export UV_CACHE_DIR=$R/cache/uv UV_PYTHON_INSTALL_DIR=$R/uvpython HOME=/data/harvest/home TMPDIR=/data/harvest/tmp UV_LINK_MODE=copy
UV=$R/bin/uv
cd $P && git rev-parse HEAD > $R/liberoplus_commit.txt
[ -x $V/bin/python ] || $UV venv --python 3.10 $V
$UV pip install --python $V/bin/python --index-strategy unsafe-best-match --extra-index-url https://download.pytorch.org/whl/cpu \
  "torch==1.11.0+cpu" "numpy==1.22.4" "mujoco==3.2.3" "termcolor==2.4.0" "numba==0.56.4" "llvmlite==0.39.1" \
  "scipy==1.10.1" "opencv-python-headless==4.6.0.66" "matplotlib==3.5.3" "imageio[ffmpeg]==2.35.1" "pyyaml" "tyro==0.9.2" \
  "tqdm" "bddl==1.0.1" "easydict==1.9" "hydra-core==1.2.0" "future==0.18.2" "cloudpickle==2.1.0" "gym==0.25.2" \
  "einops==0.4.1" "httpx" "pillow==10.4.0" "Wand" "scikit-image<0.22"
$UV pip install --python $V/bin/python --no-deps "robosuite==1.4.1"
$UV pip install --python $V/bin/python -e $R/openpi/packages/openpi-client
$UV pip install --python $V/bin/python --no-deps -e $P
MAMBA_ROOT_PREFIX=$R/cache/mamba $R/bin/micromamba create -y -q -p $R/imagick -c conda-forge imagemagick
cd $P/libero/libero
[ -d assets/scenes ] && [ -f $R/liberoplus_assets.ok ] || {
  curl -sL -o /data/harvest/tmp/liberoplus_assets.zip https://huggingface.co/datasets/Sylvest/LIBERO-plus/resolve/main/assets.zip
  ls -la /data/harvest/tmp/liberoplus_assets.zip
  $V/bin/python -c "import zipfile; zipfile.ZipFile('/data/harvest/tmp/liberoplus_assets.zip').extractall('.')"
  touch $R/liberoplus_assets.ok; rm -f /data/harvest/tmp/liberoplus_assets.zip; }
mkdir -p $R/liberoplus_cfg; B=$P/libero/libero
printf "benchmark_root: $B\nbddl_files: $B/bddl_files\ninit_states: $B/init_files\ndatasets: $R/libero_datasets\nassets: $B/assets\n" > $R/liberoplus_cfg/config.yaml
echo "$(date -u +%FT%TZ) DONE"
