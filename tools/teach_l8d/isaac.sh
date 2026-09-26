#!/bin/bash
# L8-D Isaac job (docs/stage3/prereg_l8d.md): one Isaac process on one GPU running a harvest.teach_l8d module
# (run_collect or probe_reach). Isaac rendering: never main-pod GPU 2 / 4 or x2 GPU 0 (DEVICE_LOST history).
# usage: isaac.sh <code dir> <gpu> <tag> <module> <args...>   log -> /data/harvest/logs/teach_l8d/<tag>.log
# stop: tools/teach_l8d/stop.sh <tag>
Q=/data/harvest
C=$1; G=$2; TAG=$3; MOD=$4; shift 4
case "$(hostname)-$G" in
  *x2-0) echo "refused: x2 GPU 0 is not for Isaac rendering"; exit 2;;
  *7a2a-2|*7a2a-4) echo "refused: main GPU $G is not for Isaac rendering"; exit 2;;
esac
L=$Q/logs/teach_l8d
mkdir -p $L $Q/out/teach_l8d $C/tmp
ENVS="HOME=$Q/home TMPDIR=$C/tmp XDG_CACHE_HOME=$Q/cache HF_HOME=$Q/cache/hf TORCH_HOME=$Q/cache/torch PIP_CACHE_DIR=$Q/cache/pip WARP_CACHE_PATH=$Q/cache/warp MPLCONFIGDIR=$Q/cache/mpl PYTHONPATH=$C PYTHONPYCACHEPREFIX=$Q/cache/pyc_teach_l8d OMP_WAIT_POLICY=PASSIVE OMP_NUM_THREADS=4"
cd $Q/ir
export CUDA_VISIBLE_DEVICES=$G
echo "START $(date -u +%FT%TZ) host=$(hostname) gpu=$G $MOD $*" >> $L/$TAG.log
IR_ROOT=cyclo IR_INST=teach_l8d_$TAG timeout 21600 nice ./ir_run.sh env $ENVS /isaac-sim/python.sh -m $MOD "$@" >> $L/$TAG.log 2>&1
echo "EXIT $? $(date -u +%FT%TZ)" >> $L/$TAG.log
