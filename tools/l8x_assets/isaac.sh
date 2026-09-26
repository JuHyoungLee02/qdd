#!/bin/bash
# L8X-assets Isaac job: one Isaac process on one GPU running a module (validate). Never main GPU 2 / 4 or x2 GPU 0.
# usage: isaac.sh <code dir> <gpu> <tag> <module> <args...>   log -> /data/harvest/logs/l8x_assets/<tag>.log
Q=/data/harvest
C=$1; G=$2; TAG=$3; MOD=$4; shift 4
case "$(hostname)-$G" in
  *x2-0) echo "refused: x2 GPU 0 is not for Isaac rendering"; exit 2;;
  *7a2a-2|*7a2a-4) echo "refused: main GPU $G is not for Isaac rendering"; exit 2;;
esac
L=$Q/logs/l8x_assets
mkdir -p $L $C/tmp
ENVS="HOME=$Q/home TMPDIR=$C/tmp XDG_CACHE_HOME=$Q/cache HF_HOME=$Q/cache/hf TORCH_HOME=$Q/cache/torch PIP_CACHE_DIR=$Q/cache/pip WARP_CACHE_PATH=$Q/cache/warp MPLCONFIGDIR=$Q/cache/mpl PYTHONPATH=$C PYTHONPYCACHEPREFIX=$Q/cache/pyc_l8x_assets OMP_WAIT_POLICY=PASSIVE OMP_NUM_THREADS=4"
cd $Q/ir
export CUDA_VISIBLE_DEVICES=$G
echo "START $(date -u +%FT%TZ) host=$(hostname) gpu=$G $MOD $*" >> $L/$TAG.log
IR_ROOT=cyclo IR_INST=l8x_assets_$TAG timeout 10800 nice ./ir_run.sh env $ENVS /isaac-sim/python.sh -m $MOD "$@" >> $L/$TAG.log 2>&1
echo "EXIT $? $(date -u +%FT%TZ)" >> $L/$TAG.log
