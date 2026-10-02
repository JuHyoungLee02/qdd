#!/bin/bash
# autotune pod runner: one python process in the cyclo chroot on a NON-RENDER card chosen by UUID prefix.
# usage: runat.sh <uuid-prefix> <tag> <code dir> <python args...>
Q=/data/harvest; W=$Q/autotune; UU=$1; TAG=$2; C=$3; shift 3
IDX=$(nvidia-smi --query-gpu=index,uuid --format=csv,noheader | grep -i "GPU-$UU" | cut -d, -f1)
[ -z "$IDX" ] && { echo "no GPU $UU on $(hostname)"; exit 2; }
mkdir -p $W/tmp $W/logs
ENVS="HOME=$Q/home TMPDIR=$W/tmp XDG_CACHE_HOME=$Q/cache WARP_CACHE_PATH=$Q/cache/warp MPLCONFIGDIR=$Q/cache/mpl PYTHONPATH=$C:$Q/l9v2/pylib PYTHONPYCACHEPREFIX=$Q/cache/pyc_autotune OMP_NUM_THREADS=4 OMP_WAIT_POLICY=PASSIVE CUDA_VISIBLE_DEVICES=$IDX L9V2_ASSET_ROOT=${L9V2_ASSET_ROOT:-/data/harvest/assets_l9v2/robots}"
cd $Q/ir
echo "START $(date -u +%FT%TZ) gpu $IDX($UU) $*" >> $W/logs/$TAG.log
IR_ROOT=cyclo IR_INST=autotune_$TAG timeout ${AT_TIMEOUT:-14400} nice ./ir_run.sh env $ENVS /isaac-sim/python.sh "$@" >> $W/logs/$TAG.log 2>&1
echo "EXIT $? $(date -u +%FT%TZ)" >> $W/logs/$TAG.log
