#!/bin/bash
# L9v2-ROBOT pod job: ONE python process (cuRobo / Isaac) on 7a2a GPU 1 inside the cyclo chroot.
# usage: run.sh <tag> <python args...>   (code = /data/harvest/l9v2robot/code, log -> /data/harvest/l9v2robot/logs/<tag>.log)
# One process at a time: a flock on $W/run.lock refuses a second job. IR_INST=l9v2robot_<tag> identifies it.
Q=/data/harvest; W=$Q/l9v2robot; C=$W/code
TAG=$1; shift
case "$(hostname)" in *7a2a) ;; *) echo "refused: $(hostname) is not juhyoung-native-7a2a"; exit 2;; esac
mkdir -p $W/tmp $W/logs
exec 9>$W/run.lock
flock -n 9 || { echo "refused: another l9v2robot job holds $W/run.lock"; exit 3; }
ENVS="HOME=$Q/home TMPDIR=$W/tmp XDG_CACHE_HOME=$Q/cache WARP_CACHE_PATH=$Q/cache/warp MPLCONFIGDIR=$Q/cache/mpl PYTHONPATH=$C:$Q/l9v2/pylib PYTHONPYCACHEPREFIX=$Q/cache/pyc_l9v2robot OMP_NUM_THREADS=4 OMP_WAIT_POLICY=PASSIVE CUDA_VISIBLE_DEVICES=1"
cd $Q/ir
echo "START $(date -u +%FT%TZ) $*" >> $W/logs/$TAG.log
IR_ROOT=cyclo IR_INST=l9v2robot_$TAG timeout ${L9V2R_TIMEOUT:-7200} nice ./ir_run.sh env $ENVS /isaac-sim/python.sh "$@" >> $W/logs/$TAG.log 2>&1
echo "EXIT $? $(date -u +%FT%TZ)" >> $W/logs/$TAG.log
