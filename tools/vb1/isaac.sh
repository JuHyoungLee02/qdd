#!/bin/bash
# E-VB1 Isaac job (docs/stage3/prereg_vb1.md change 1): one Isaac process on one render card running tools.vb1.rec.
# Render cards only: main 7a2a GPU 0/1/3 and x2 GPU 1. Refused: main GPU 2/4 (DEVICE_LOST history), x2 GPU 0, x3, 78dc.
# usage: isaac.sh <code dir> <gpu> <tag> <args of tools.vb1.rec...>   log -> /data/harvest/logs/vb1/<tag>.log
Q=/data/harvest
C=$1; G=$2; TAG=$3; shift 3
case "$(hostname)-$G" in
  *7a2a-x2-1) ;;
  *7a2a-x2-*|*7a2a-x3-*|*78dc*) echo "refused: $(hostname) GPU $G is not a render card"; exit 2;;
  *7a2a-0|*7a2a-1|*7a2a-3) ;;
  *) echo "refused: $(hostname) GPU $G is not a render card"; exit 2;;
esac
L=$Q/logs/vb1
mkdir -p $L $C/tmp
ENVS="HOME=$Q/home TMPDIR=$C/tmp XDG_CACHE_HOME=$Q/cache HF_HOME=$Q/cache/hf TORCH_HOME=$Q/cache/torch PIP_CACHE_DIR=$Q/cache/pip WARP_CACHE_PATH=$Q/cache/warp MPLCONFIGDIR=$Q/cache/mpl PYTHONPATH=$C PYTHONPYCACHEPREFIX=$Q/cache/pyc_vb1 OMP_WAIT_POLICY=PASSIVE OMP_NUM_THREADS=4"
cd $Q/ir
export CUDA_VISIBLE_DEVICES=$G
echo "START $(date -u +%FT%TZ) host=$(hostname) gpu=$G $*" >> $L/$TAG.log
IR_ROOT=cyclo IR_INST=vb1_$TAG timeout 21600 nice ./ir_run.sh env $ENVS /isaac-sim/python.sh -m tools.vb1.rec "$@" >> $L/$TAG.log 2>&1
rc=$?
echo "EXIT $rc $(date -u +%FT%TZ)" >> $L/$TAG.log
exit $rc
