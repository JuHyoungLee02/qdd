#!/bin/bash
# L9 Isaac job: one Isaac process on one GPU running a module. Render cards only: 7a2a GPU 0/1/3, x2 GPU 1.
# usage: isaac.sh <code dir> <gpu> <tag> <module> <args...>   log -> /data/harvest/logs/l9/<tag>.log
Q=/data/harvest
C=$1; G=$2; TAG=$3; MOD=$4; shift 4
case "$(hostname)-$G" in
  *7a2a-x2-1) ;;
  *7a2a-x2-*|*7a2a-x3-*) echo "refused: $(hostname) GPU $G is not an L9 render card"; exit 2;;
  *7a2a-0|*7a2a-1|*7a2a-3) ;;
  *q-fe08-[0-9]|*q-e9f3b-[0-9]) ;;  # render-OK by GPU UUID below (indices change when a pod is recreated)
  *q-e9f3-0|*q-e9f3-1) ;;  # e9f3 (2 H200) render probe 10-02 PASS
  *) echo "refused: $(hostname) GPU $G is not an L9 render card"; exit 2;;
esac
U=$(nvidia-smi --query-gpu=uuid --format=csv,noheader -i $G 2>/dev/null)
case "$U" in  # render probes 10-02: DEVICE_LOST cards (main), never render on them
  GPU-2f884eb2*|GPU-e3ba4da6*|GPU-d34a989d*|GPU-02f64a10*) echo "refused: GPU $G ($U) is a DEVICE_LOST card"; exit 2;;
esac
L=$Q/logs/l9
mkdir -p $L $C/tmp
ENVS="HOME=$Q/home TMPDIR=$C/tmp XDG_CACHE_HOME=$Q/cache HF_HOME=$Q/cache/hf TORCH_HOME=$Q/cache/torch PIP_CACHE_DIR=$Q/cache/pip WARP_CACHE_PATH=$Q/cache/warp MPLCONFIGDIR=$Q/cache/mpl PYTHONPATH=$C PYTHONPYCACHEPREFIX=$Q/cache/pyc_l9 OMP_WAIT_POLICY=PASSIVE OMP_NUM_THREADS=${L9_OMP:-4} MKL_NUM_THREADS=${L9_OMP:-4}${L9_KIT_THREADS:+ L9_KIT_THREADS=$L9_KIT_THREADS}${L9_PHYSX_THREADS:+ L9_PHYSX_THREADS=$L9_PHYSX_THREADS}${L9_PROFILE:+ L9_PROFILE=$L9_PROFILE}${L9_TIMING:+ L9_TIMING=$L9_TIMING}${L9_CUROBO:+ L9_CUROBO=$L9_CUROBO}${L9_PLANNER_GPUS:+ L9_PLANNER_GPUS=$L9_PLANNER_GPUS}${L9_ATTACH_FIT:+ L9_ATTACH_FIT=$L9_ATTACH_FIT}${L9V2_DEBUG_DIR:+ L9V2_DEBUG_DIR=$L9V2_DEBUG_DIR}${L9V2_COLLIDERS:+ L9V2_COLLIDERS=$L9V2_COLLIDERS}${LIVE_CMD_SOURCE:+ LIVE_CMD_SOURCE=$LIVE_CMD_SOURCE}${L9V2_GRASPS:+ L9V2_GRASPS=$L9V2_GRASPS}${L9V2_TESTED:+ L9V2_TESTED=$L9V2_TESTED}${LIVE_DEBUG:+ LIVE_DEBUG=$LIVE_DEBUG}${LIVE_REFINER:+ LIVE_REFINER=$LIVE_REFINER}${GGX_QUEUE:+ GGX_QUEUE=$GGX_QUEUE}"
cd $Q/ir
export CUDA_VISIBLE_DEVICES=$G
echo "START $(date -u +%FT%TZ) host=$(hostname) gpu=$G $MOD $*" >> $L/$TAG.log
N0=$(wc -l < $L/$TAG.log)
IR_ROOT=cyclo IR_INST=l9_$TAG timeout ${L9_TIMEOUT:-21600} nice ./ir_run.sh env $ENVS /isaac-sim/python.sh -m $MOD "$@" >> $L/$TAG.log 2>&1 &
P=$!
# watchdog (P190): run9 printed RUN_DONE and called os._exit, but the Isaac python stayed running (state R) for 1-2.5 h,
# holding its GPU memory and the lane; SIGTERM was ignored. 90 s after RUN_DONE the process tree is killed.
kill_tree() { local c; for c in $(ps -o pid= --ppid $1 2>/dev/null); do kill_tree $c; done; kill -KILL $1 2>/dev/null; }
TD=
while kill -0 $P 2>/dev/null; do
  sleep 15
  [ -z "$TD" ] && tail -n +$((N0 + 1)) $L/$TAG.log | grep -q '^RUN_DONE' && TD=$(date +%s)
  if [ -n "$TD" ] && [ $(( $(date +%s) - TD )) -ge 90 ] && kill -0 $P 2>/dev/null; then
    echo "WATCHDOG $(date -u +%FT%TZ): still running 90 s after RUN_DONE, killed" >> $L/$TAG.log
    kill_tree $P
  fi
done
wait $P
RC=$?
[ -n "$TD" ] && RC=0
echo "EXIT $RC $(date -u +%FT%TZ)" >> $L/$TAG.log
