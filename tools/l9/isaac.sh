#!/bin/bash
# L9 Isaac job: one Isaac process on one GPU running a module. Render cards only: 7a2a GPU 0/1/3, x2 GPU 1.
# usage: isaac.sh <code dir> <gpu> <tag> <module> <args...>   log -> /data/harvest/logs/l9/<tag>.log
Q=/data/harvest
C=$1; G=$2; TAG=$3; MOD=$4; shift 4
case "$(hostname)-$G" in
  *7a2a-x2-1) ;;
  *7a2a-x2-*|*7a2a-x3-*) echo "refused: $(hostname) GPU $G is not an L9 render card"; exit 2;;
  *7a2a-0|*7a2a-1|*7a2a-3) ;;
  *q-fe08-0|*q-fe08-2|*q-fe08-3|*q-fe08-5) ;;  # fe08 (7 GPU pod) re-probe 10-02: GPU 1/4/6 DEVICE_LOST (never render)
  *q-e9f3b-[0-5]) ;;  # e9f3b (6 H200) render probe 10-02 PASS
  *q-e9f3-0|*q-e9f3-1) ;;  # e9f3 (2 H200) render probe 10-02 PASS
  *) echo "refused: $(hostname) GPU $G is not an L9 render card"; exit 2;;
esac
L=$Q/logs/l9
mkdir -p $L $C/tmp
ENVS="HOME=$Q/home TMPDIR=$C/tmp XDG_CACHE_HOME=$Q/cache HF_HOME=$Q/cache/hf TORCH_HOME=$Q/cache/torch PIP_CACHE_DIR=$Q/cache/pip WARP_CACHE_PATH=$Q/cache/warp MPLCONFIGDIR=$Q/cache/mpl PYTHONPATH=$C PYTHONPYCACHEPREFIX=$Q/cache/pyc_l9 OMP_WAIT_POLICY=PASSIVE OMP_NUM_THREADS=4${L9V2_DEBUG_DIR:+ L9V2_DEBUG_DIR=$L9V2_DEBUG_DIR}${L9V2_COLLIDERS:+ L9V2_COLLIDERS=$L9V2_COLLIDERS}"
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
