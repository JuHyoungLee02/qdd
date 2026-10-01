#!/bin/bash
# E-LIB0 (docs/stage3/prereg_lib0.md) one-time setup on the pod, everything under /data/harvest/lib0:
#   bin/uv                 uv (static binary)
#   openpi/                Physical-Intelligence/openpi clone (+ submodules: third_party/libero), commit -> openpi_commit.txt
#   openpi/.venv           policy-server env (uv sync, python 3.11, JAX) -- the official server path
#   venv_libero            LIBERO sim env shared by ALL arms (python 3.10: the qdd runner needs >= 3.10). Same robosuite
#                          1.4.1 / mujoco 3.2.3 / numpy 1.22.4 as openpi examples/libero/requirements.txt; numba 0.56.4
#                          (0.53.1 has no 3.10 wheel), torch 1.11.0 CPU (LIBERO only torch.load()s the init states)
#   openpi_data/           checkpoints gs://openpi-assets/checkpoints/{pi05_libero,pi05_base}
# usage: setup_env.sh <step: all|uv|openpi|libero|ckpt>   log -> /data/harvest/logs/lib0/setup.log
set -e
R=/data/harvest/lib0; L=/data/harvest/logs/lib0; mkdir -p $R/bin $R/cache $L /data/harvest/tmp
export UV_CACHE_DIR=$R/cache/uv UV_PYTHON_INSTALL_DIR=$R/uvpython XDG_CACHE_HOME=$R/cache HOME=/data/harvest/home
export TMPDIR=/data/harvest/tmp OPENPI_DATA_HOME=$R/openpi_data UV_LINK_MODE=copy GIT_LFS_SKIP_SMUDGE=1
UV=$R/bin/uv
step=${1:-all}
log() { echo "$(date -u +%FT%TZ) setup $*"; }
if [ $step = all ] || [ $step = uv ]; then
  [ -x $UV ] || curl -LsSf https://github.com/astral-sh/uv/releases/download/0.8.17/uv-x86_64-unknown-linux-gnu.tar.gz \
    | tar xz -C $R/bin --strip-components=1
  $UV --version; log "uv ok"
fi
if [ $step = all ] || [ $step = openpi ]; then
  [ -d $R/openpi/.git ] || git clone --recurse-submodules https://github.com/Physical-Intelligence/openpi.git $R/openpi
  cd $R/openpi && git rev-parse HEAD > $R/openpi_commit.txt && git submodule status >> $R/openpi_commit.txt
  # evdev (lerobot -> pynput -> evdev) builds from source and needs kernel headers the pod lacks; the policy server never
  # uses a keyboard -> drop it with a never-true marker (the only local change to openpi; recorded in openpi_commit.txt)
  grep -q '"evdev; sys_platform' pyproject.toml || sed -i 's/^override-dependencies = \["ml-dtypes==0.4.1", "tensorstore==0.1.74"\]/override-dependencies = ["ml-dtypes==0.4.1", "tensorstore==0.1.74", "evdev; sys_platform == '"'"'never'"'"'"]/' pyproject.toml
  grep -n override-dependencies pyproject.toml >> $R/openpi_commit.txt
  $UV sync; log "openpi venv ok $(cat $R/openpi_commit.txt | head -1)"
fi
if [ $step = all ] || [ $step = libero ]; then
  [ -x $R/venv_libero/bin/python ] || $UV venv --python 3.10 $R/venv_libero
  P="--python $R/venv_libero/bin/python"
  $UV pip install $P --index-strategy unsafe-best-match --extra-index-url https://download.pytorch.org/whl/cpu \
    "torch==1.11.0+cpu" "numpy==1.22.4" "mujoco==3.2.3" "termcolor==2.4.0" "numba==0.56.4" "llvmlite==0.39.1" \
    "scipy==1.10.1" "opencv-python-headless==4.6.0.66" "matplotlib==3.5.3" "imageio[ffmpeg]==2.35.1" "pyyaml" "tyro==0.9.2" \
    "tqdm" "bddl==1.0.1" "easydict==1.9" "hydra-core==1.2.0" "future==0.18.2" "cloudpickle==2.1.0" "gym==0.25.2" \
    "einops==0.4.1" "httpx" "pillow==10.4.0"
  $UV pip install $P --no-deps "robosuite==1.4.1"  # its pynput -> evdev needs kernel headers; keyboard device unused
  $UV pip install $P -e $R/openpi/packages/openpi-client
  $UV pip install $P --no-deps -e $R/openpi/third_party/libero
  mkdir -p $R/libero_cfg
  B=$R/openpi/third_party/libero/libero/libero
  printf "benchmark_root: $B\nbddl_files: $B/bddl_files\ninit_states: $B/init_files\ndatasets: $R/libero_datasets\nassets: $B/assets\n" \
    > $R/libero_cfg/config.yaml
  log "libero venv ok"
fi
if [ $step = all ] || [ $step = ckpt ]; then
  cd $R/openpi
  for c in pi05_libero pi05_base; do
    $UV run python -c "from openpi.shared import download; print(download.maybe_download('gs://openpi-assets/checkpoints/$c'))"
  done
  log "ckpt ok"; du -sh $OPENPI_DATA_HOME/* 2>/dev/null
fi
log "DONE step=$step"
# step mesa (run separately: setup_env.sh mesa): the pods have no OSMesa / libEGL loader (only the NVIDIA vendor EGL),
# and nothing may be installed outside /data -> conda-forge mesalib < 25 (llvmpipe OSMesa, CPU) into $R/mesa24 via micromamba.
# Runners: MUJOCO_GL=osmesa PYOPENGL_PLATFORM=osmesa LD_LIBRARY_PATH=$R/mesa24/lib LP_NUM_THREADS=1
if [ $step = mesa ]; then
  [ -x $R/bin/micromamba ] || curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xj -C $R bin/micromamba
  MAMBA_ROOT_PREFIX=$R/cache/mamba $R/bin/micromamba create -y -p $R/mesa24 -c conda-forge "mesalib<25"  # mesa 25+ dropped OSMesa
  ls $R/mesa24/lib | grep -i osmesa; log "mesa ok"
fi
