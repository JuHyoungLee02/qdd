#!/bin/bash
# E-OpenVLM-proxy runner (docs/stage3/prereg_open_vlm_solo.md): tools/astra_solo/run.sh with Isaac on GPU 1 and its own
# log / out / ledger. usage: run_proxy.sh <code dir> <tag> <harvest.astra_solo.run args...>
Q=/data/harvest
C=$1; TAG=$2; shift 2
L=$Q/logs/open_vlm_proxy
mkdir -p $L $Q/out/open_vlm_proxy $C/tmp
ENVS="HOME=$Q/home TMPDIR=$C/tmp XDG_CACHE_HOME=$Q/cache HF_HOME=$Q/cache/hf TORCH_HOME=$Q/cache/torch PIP_CACHE_DIR=$Q/cache/pip WARP_CACHE_PATH=$Q/cache/warp MPLCONFIGDIR=$Q/cache/mpl PYTHONPATH=$C PYTHONPYCACHEPREFIX=$Q/cache/pyc_open_vlm_proxy OMP_WAIT_POLICY=PASSIVE OMP_NUM_THREADS=8"
cd $Q/ir
export CUDA_VISIBLE_DEVICES=1
echo "START $(date -u +%FT%TZ) gpu=1 $*" >> $L/$TAG.log
IR_ROOT=cyclo IR_INST=open_vlm_proxy_$TAG timeout 7200 nice ./ir_run.sh env $ENVS /isaac-sim/python.sh -m harvest.astra_solo.run "$@" >> $L/$TAG.log 2>&1
echo "EXIT $? $(date -u +%FT%TZ)" >> $L/$TAG.log
