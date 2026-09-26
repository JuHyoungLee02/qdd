#!/bin/bash
# E-TEACH-L8 collection (docs/stage3/prereg_teach_l8.md). One Isaac process on one GPU.
# usage: collect.sh <code dir> <gpu> <tag> <harvest.teach_l8.run_collect args...>   log -> /data/harvest/logs/teach_l8/<tag>.log
# Isaac rendering: never main-pod GPU 2 / 4 or x2 GPU 0 (DEVICE_LOST history). Stop: tools/teach_l8/stop.sh.
Q=/data/harvest
C=$1; G=$2; TAG=$3; shift 3
L=$Q/logs/teach_l8
mkdir -p $L $Q/out/teach_l8 $C/tmp
ENVS="HOME=$Q/home TMPDIR=$C/tmp XDG_CACHE_HOME=$Q/cache HF_HOME=$Q/cache/hf TORCH_HOME=$Q/cache/torch PIP_CACHE_DIR=$Q/cache/pip WARP_CACHE_PATH=$Q/cache/warp MPLCONFIGDIR=$Q/cache/mpl PYTHONPATH=$C PYTHONPYCACHEPREFIX=$Q/cache/pyc_teach_l8 OMP_WAIT_POLICY=PASSIVE OMP_NUM_THREADS=4"
cd $Q/ir
export CUDA_VISIBLE_DEVICES=$G
echo "START $(date -u +%FT%TZ) host=$(hostname) gpu=$G $*" >> $L/$TAG.log
IR_ROOT=cyclo IR_INST=teach_l8_$TAG timeout 21600 nice ./ir_run.sh env $ENVS /isaac-sim/python.sh -m harvest.teach_l8.run_collect "$@" >> $L/$TAG.log 2>&1
echo "EXIT $? $(date -u +%FT%TZ)" >> $L/$TAG.log
