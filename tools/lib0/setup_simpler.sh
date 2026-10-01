#!/bin/bash
# E-SIM0 setup (SimplerEnv Google Robot, prereg to follow): SimplerEnv + ManiSkill2_real2sim (SAPIEN 2.2.2) in their own
# venv under /data/harvest/simpler (python 3.10, numpy < 2). Policy-specific extras (tensorflow / RT-1, Octo) are NOT
# installed. usage: setup_simpler.sh   log -> /data/harvest/logs/simpler/setup.log
set -e
R=/data/harvest/simpler; L=/data/harvest/logs/simpler; mkdir -p $R $L /data/harvest/tmp
UV=/data/harvest/lib0/bin/uv
export UV_CACHE_DIR=/data/harvest/lib0/cache/uv UV_PYTHON_INSTALL_DIR=/data/harvest/lib0/uvpython HOME=/data/harvest/home
export TMPDIR=/data/harvest/tmp UV_LINK_MODE=copy XDG_CACHE_HOME=$R/cache
[ -d $R/SimplerEnv/.git ] || git clone --recurse-submodules https://github.com/simpler-env/SimplerEnv.git $R/SimplerEnv
cd $R/SimplerEnv && git rev-parse HEAD > $R/commit.txt && git submodule status >> $R/commit.txt
[ -x $R/venv/bin/python ] || $UV venv --python 3.10 $R/venv
P="--python $R/venv/bin/python"
$UV pip install $P "numpy<2" "sapien==2.2.2" "opencv-python-headless" "imageio[ffmpeg]" httpx pillow websockets msgpack
$UV pip install $P -e $R/SimplerEnv/ManiSkill2_real2sim
$UV pip install $P --no-deps -e $R/SimplerEnv
$UV pip install $P -e /data/harvest/lib0/openpi/packages/openpi-client
$R/venv/bin/python -c "import sapien, mani_skill2_real2sim, simpler_env; print('import ok', sapien.__version__)"
echo "$(date -u +%FT%TZ) DONE"
