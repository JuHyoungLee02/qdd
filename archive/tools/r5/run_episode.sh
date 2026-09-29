#!/bin/bash
# R5 one DEV episode through Inspect Robots on the pod (Isaac cyclo rootfs, GPU 1 only, every file under /data/harvest).
# usage: run_episode.sh <tag> <timeout_s> <run_r5 args...>     (INST=<kit instance>, default r5a)
TAG=$1; TO=$2; shift 2
Q=/data/harvest; OUT=$Q/out/r5/$TAG; CODE=$Q/code_r5cl
mkdir -p $OUT $Q/home $Q/tmp $Q/cache/hf $Q/cache/torch $Q/cache/pip $Q/cache/warp
ENVS="HOME=$Q/home TMPDIR=$Q/tmp XDG_CACHE_HOME=$Q/cache HF_HOME=$Q/cache/hf TORCH_HOME=$Q/cache/torch PIP_CACHE_DIR=$Q/cache/pip WARP_CACHE_PATH=$Q/cache/warp PYTHONPYCACHEPREFIX=$Q/cache/pyc_r5 PYTHONPATH=$CODE:$Q/ir/pylib:$Q/ir/src/src"
cd $Q/ir && IR_ROOT=cyclo IR_INST=${INST:-r5a} CUDA_VISIBLE_DEVICES=1 timeout $TO ./ir_run.sh env $ENVS \
  /isaac-sim/python.sh -m harvest.runtime.run_r5 --out $OUT --tag $TAG "$@" > $OUT/run.log 2>&1
echo "exit=$?" >> $OUT/run.log
grep -E "R5_RESULT|Traceback|Error|error:" $OUT/run.log | head -20
