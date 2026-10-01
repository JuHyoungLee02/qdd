#!/bin/bash
# L9 v2 grasp test loop (one Isaac process at a time, 7a2a GPU 1): next chunk (tools/l9/grasp_test_queue.py, priority
# targets -> hollow -> rest, only objects whose candidates exist) -> tools.l9.grasp_test -> repeat. Ends when nothing is
# left and the candidate generation of the gripper is done (grasps_done.log "DONE <grip>"); stop file:
# /data/harvest/l9v2gt/stop_<grip>.
# usage: gtest_loop.sh <code dir> <grip> <objects per chunk> <envs> [extra grasp_test args]
C=$1; G=$2; M=$3; N=$4; shift 4
W=/data/harvest/l9v2gt
mkdir -p $W
cd /data/harvest/ir
T0=$(date -u +%FT%TZ)  # only a generation DONE line written after this counts (older lines are from earlier runs)
while true; do
  [ -f $W/stop_$G ] && { echo "STOP $(date -u +%FT%TZ)"; break; }
  IR_ROOT=cyclo IR_INST=l9v2gt_q ./ir_run.sh env HOME=/data/harvest/home PYTHONPATH=$C CUDA_VISIBLE_DEVICES= \
    /isaac-sim/python.sh $C/tools/l9/grasp_test_queue.py --grip $G --n $M --out $W/ids_$G.txt > $W/q_$G.log 2>&1
  echo "QUEUE $(date -u +%FT%TZ) $(tail -1 $W/q_$G.log)"
  if [ ! -s $W/ids_$G.txt ]; then
    awk -v g=$G -v t=$T0 '$1 == "DONE" && $2 == g && $3 > t {f = 1} END {exit !f}' /data/harvest/l9v2/grasps_done.log 2>/dev/null \
      && { echo "ALL DONE $(date -u +%FT%TZ)"; break; }
    sleep 120
    continue
  fi
  bash $C/tools/l9/isaac.sh $C 1 l9v2gt_$G tools.l9.grasp_test --grip $G --ids $W/ids_$G.txt --envs $N "$@"
  tail -2 /data/harvest/logs/l9/l9v2gt_$G.log | head -1
  grep -a "\[gtest\] DONE" /data/harvest/logs/l9/l9v2gt_$G.log | tail -1
done
