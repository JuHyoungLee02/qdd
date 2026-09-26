#!/bin/bash
# E-ACC bench capture (docs/stage3/prereg_eacc.md §2): main pod GPU 0 only (Isaac render), one Isaac process,
# every file under /data. usage: capture.sh <code dir> <out dir> [--only id,...]
C=$1; OUT=$2; shift 2
Q=/data/harvest; L=$Q/logs/eacc
mkdir -p $OUT $L $Q/home $Q/tmp $Q/cache/hf $Q/cache/torch $Q/cache/pip $Q/cache/warp
ENVS="HOME=$Q/home TMPDIR=$Q/tmp XDG_CACHE_HOME=$Q/cache HF_HOME=$Q/cache/hf TORCH_HOME=$Q/cache/torch PIP_CACHE_DIR=$Q/cache/pip WARP_CACHE_PATH=$Q/cache/warp PYTHONPYCACHEPREFIX=$Q/cache/pyc_eacc OMP_WAIT_POLICY=PASSIVE PYTHONPATH=$C:$Q/ir/pylib:$Q/ir/src/src"
cd $Q/ir && IR_ROOT=cyclo IR_INST=eacc0 CUDA_VISIBLE_DEVICES=0 timeout 7200 nice -n 10 ./ir_run.sh env $ENVS \
  /isaac-sim/python.sh $C/tools/eacc/capture.py --out $OUT "$@" >> $L/capture.log 2>&1
echo "EXIT $? $(date -u +%FT%TZ)" >> $L/capture.log
