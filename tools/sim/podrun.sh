#!/bin/bash
# usage: podrun.sh <logname> <timeout_s> <run_dev args...>   (all caches/tmp/home under /data/harvest)
LOG=$1; TO=$2; shift 2
[ -z "$NOSYNC" ] && (cd D:/qdd && bash tools/pod_sync.sh >/dev/null 2>&1)
Q=/data/harvest
ENVS="HOME=$Q/home TMPDIR=$Q/tmp XDG_CACHE_HOME=$Q/cache HF_HOME=$Q/cache/hf TORCH_HOME=$Q/cache/torch PIP_CACHE_DIR=$Q/cache/pip WARP_CACHE_PATH=$Q/cache/warp PYTHONPATH=$Q/code"
kubectl -n p-test2 exec juhyoung-native-7a2a -- bash -c "mkdir -p $Q/home $Q/tmp $Q/cache/hf $Q/cache/torch $Q/cache/pip $Q/cache/warp $Q/out/t11_12 && cd $Q/ir && IR_ROOT=cyclo IR_INST=${INST:-t11} timeout $TO ./ir_run.sh env $ENVS /isaac-sim/python.sh -m harvest.sim.run_dev $* > $Q/out/t11_12/$LOG.log 2>&1; grep -E 'BOOT_RESULT|^EP |Traceback|Error:|error:|^  File' $Q/out/t11_12/$LOG.log | head -40"
