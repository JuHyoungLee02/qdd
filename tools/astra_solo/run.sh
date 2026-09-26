#!/bin/bash
# Astra-solo runner on the main pod (docs/stage3/prereg_astra_solo.md). GPU 3 ONLY (Isaac render + the local Qwen).
# usage: run.sh <code dir> <tag> <harvest.astra_solo.run args...>   log -> /data/harvest/logs/astra_solo/<tag>.log
# Stop: tools/astra_solo/stop.sh (our processes only: IR_INST=astra_solo_* and the qwen8b_solo vLLM).
Q=/data/harvest
C=$1; TAG=$2; shift 2
L=$Q/logs/astra_solo
mkdir -p $L $Q/out/astra_solo $C/tmp
ENVS="HOME=$Q/home TMPDIR=$C/tmp XDG_CACHE_HOME=$Q/cache HF_HOME=$Q/cache/hf TORCH_HOME=$Q/cache/torch PIP_CACHE_DIR=$Q/cache/pip WARP_CACHE_PATH=$Q/cache/warp MPLCONFIGDIR=$Q/cache/mpl PYTHONPATH=$C PYTHONPYCACHEPREFIX=$Q/cache/pyc_astra_solo OMP_WAIT_POLICY=PASSIVE OMP_NUM_THREADS=8"
cd $Q/ir
export CUDA_VISIBLE_DEVICES=3
echo "START $(date -u +%FT%TZ) gpu=3 $*" >> $L/$TAG.log
IR_ROOT=cyclo IR_INST=astra_solo_$TAG timeout 43200 nice ./ir_run.sh env $ENVS /isaac-sim/python.sh -m harvest.astra_solo.run "$@" >> $L/$TAG.log 2>&1
echo "EXIT $? $(date -u +%FT%TZ)" >> $L/$TAG.log
